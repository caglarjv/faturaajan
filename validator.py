"""Yapay zekanın çıkardığı alanları normalleştirir ve muhasebesel kontrollerden geçirir.
Şüpheli kayıtlar Excel'e 'Kontrol Gerekli' durumuyla yazılır."""
import datetime
import re


def sayi(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    s = re.sub(r"[^\d,.\-]", "", str(v))
    if not s:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def tarih(v):
    if not v:
        return None
    s = str(v).strip()[:10]
    for f in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%y"):
        try:
            return datetime.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def _rakam(v):
    return re.sub(r"\D", "", str(v or ""))


def vkn_gecerli(v: str) -> bool:
    if len(v) != 10:
        return False
    d = [int(x) for x in v]
    toplam = 0
    for i in range(9):
        tmp = (d[i] + 9 - i) % 10
        p = (tmp * (2 ** (9 - i))) % 9
        if tmp != 0 and p == 0:
            p = 9
        toplam += p
    return (10 - toplam % 10) % 10 == d[9]


def tckn_gecerli(v: str) -> bool:
    if len(v) != 11 or v[0] == "0":
        return False
    d = [int(x) for x in v]
    if ((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10 != d[9]:
        return False
    return sum(d[:10]) % 10 == d[10]


def _kimlik(ham, etiket, notlar, zorunlu=False):
    n = _rakam(ham)
    if not n:
        if zorunlu:
            notlar.append(f"{etiket} bulunamadı")
        return ""
    if len(n) == 10 and not vkn_gecerli(n):
        notlar.append(f"{etiket} VKN doğrulaması geçersiz ({n})")
    elif len(n) == 11 and not tckn_gecerli(n):
        notlar.append(f"{etiket} TCKN doğrulaması geçersiz ({n})")
    elif len(n) not in (10, 11):
        notlar.append(f"{etiket} hane sayısı hatalı ({n})")
    return n


def _metin(v):
    s = re.sub(r"\s+", " ", str(v or "")).strip()
    return "" if s.lower() in ("null", "none") else s


def dogrula(ham: dict, kendi_vkn: str = "") -> dict:
    notlar = []
    k = {}

    t = tarih(ham.get("fatura_tarihi"))
    bugun = datetime.date.today()
    if t is None:
        notlar.append("Fatura tarihi okunamadı")
    elif t > bugun + datetime.timedelta(days=1) or t < bugun.replace(year=bugun.year - 6):
        notlar.append(f"Fatura tarihi şüpheli ({t:%d.%m.%Y})")
    k["fatura_tarihi"] = t
    k["donem"] = (t or bugun).strftime("%Y-%m")

    k["fatura_no"] = _metin(ham.get("fatura_no")).upper().replace(" ", "")
    if not k["fatura_no"]:
        notlar.append("Fatura no okunamadı")
    k["ettn"] = _metin(ham.get("ettn")).lower()

    k["satici_unvan"] = _metin(ham.get("satici_unvan"))
    if not k["satici_unvan"]:
        notlar.append("Satıcı unvanı okunamadı")
    k["satici_vkn"] = _kimlik(ham.get("satici_vkn"), "Satıcı VKN", notlar, zorunlu=True)
    k["satici_vd"] = _metin(ham.get("satici_vergi_dairesi"))
    k["alici_unvan"] = _metin(ham.get("alici_unvan"))
    k["alici_vkn"] = _kimlik(ham.get("alici_vkn"), "Alıcı VKN", notlar)
    k["alici_vd"] = _metin(ham.get("alici_vergi_dairesi"))

    pb = _metin(ham.get("para_birimi")).upper()
    k["para_birimi"] = "TRY" if pb in ("", "TL", "₺", "TRL") else pb

    m, kdv, g = sayi(ham.get("matrah")), sayi(ham.get("kdv_tutari")), sayi(ham.get("genel_toplam"))
    oran = sayi(ham.get("kdv_orani"))
    k.update(matrah=m, kdv_tutari=kdv, genel_toplam=g,
             kdv_orani=int(oran) if oran is not None and oran == int(oran) else oran)
    if g is None:
        notlar.append("Genel toplam okunamadı")
    if m is None and kdv is None:
        notlar.append("Matrah/KDV okunamadı")
    if None not in (m, kdv, g) and abs(m + kdv - g) > 0.10:
        notlar.append(f"Matrah+KDV ({m + kdv:.2f}) genel toplamla ({g:.2f}) uyuşmuyor "
                      "(tevkifat/iskonto olabilir)")
    if m and oran and kdv is not None:
        beklenen = m * oran / 100
        if abs(beklenen - kdv) > max(1.0, 0.01 * beklenen):
            notlar.append("KDV oranı/tutarı tutarsız (çok oranlı fatura olabilir)")

    k["odeme"] = _metin(ham.get("odeme_bilgisi"))

    if kendi_vkn:
        if k["satici_vkn"] == kendi_vkn:
            k["yon"] = "Satış"
        elif k["alici_vkn"] == kendi_vkn:
            k["yon"] = "Alış"
        else:
            k["yon"] = "Belirsiz"
            notlar.append("Kendi VKN'niz ne satıcıda ne alıcıda bulundu")
    else:
        k["yon"] = "Alış"

    k["durum"] = "Kontrol Gerekli" if notlar else "Tamam"
    k["not"] = "; ".join(notlar)
    return k
