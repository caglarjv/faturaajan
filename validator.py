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


def tevkifat_orani(v):
    """Tevkifat oranını anlar: '5/10', '%50', '50', '0.5', '0,5' -> ('5/10', 0.5).
    Okunamazsa ya da 0 ise ('', None) döndürür."""
    if v is None:
        return "", None
    s = str(v).strip().replace(" ", "")
    if not s or s.lower() in ("null", "none", "-"):
        return "", None
    m = re.fullmatch(r"(\d+)/(\d+)", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if b == 0 or a == 0 or a > b:
            return "", None
        return f"{a}/{b}", a / b
    n = sayi(s.replace("%", ""))
    if n is None:
        return "", None
    kesir = n / 100 if (n > 1 or "%" in s) else n
    if kesir <= 0 or kesir > 1:
        return "", None
    on = kesir * 10
    if abs(on - round(on)) < 1e-6:
        return f"{round(on)}/10", kesir
    return f"%{kesir * 100:g}", kesir


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


_TARAF_CIFTLERI = (
    ("satici_unvan", "alici_unvan"),
    ("satici_vkn", "alici_vkn"),
    ("satici_vergi_dairesi", "alici_vergi_dairesi"),
)

# Türkçe harfleri ve büyük/küçük harf farkını eşitler (İ, I, ı -> i; Ş -> s ...).
_TR_KATLA = str.maketrans("İIıÇçĞğÖöŞşÜüÂâÎîÛû", "iiiccggoossuuaaiiuu")


def _norm(v) -> str:
    return str(v or "").translate(_TR_KATLA).lower()


def kelime_var_mi(metin, kelimeler) -> bool:
    """Metinde anahtar kelimelerden biri TAM KELİME olarak geçiyor mu?
    (TONA, Tona, tona, T0NA hariç; 'Tonaj' veya 'Antonakis' içindeki 'tona' sayılmaz.)"""
    t = _norm(metin)
    for k in kelimeler or ():
        kn = _norm(k).strip()
        if kn and re.search(r"(?<![a-z0-9])" + re.escape(kn) + r"(?![a-z0-9])", t):
            return True
    return False


def taraf_belirle(ham: dict, kendi_vkn: str, anahtarlar):
    """Firmamız hangi tarafta? (sonuc, kaynak) döndürür.
    sonuc: 'dogru' (alıcıda), 'ters' (satıcıda), 'belirsiz'.  kaynak: 'vkn' | 'unvan' | None.
    Önce VKN (kesin), VKN hiçbirinde bulunamazsa unvandaki anahtar kelime karar verir."""
    s, a = _rakam(ham.get("satici_vkn")), _rakam(ham.get("alici_vkn"))
    vs = bool(kendi_vkn) and s == kendi_vkn
    va = bool(kendi_vkn) and a == kendi_vkn
    if vs or va:
        return ("ters" if vs and not va else "dogru"), "vkn"
    if anahtarlar:
        ks = kelime_var_mi(ham.get("satici_unvan"), anahtarlar)
        ka = kelime_var_mi(ham.get("alici_unvan"), anahtarlar)
        if ks and not ka:
            return "ters", "unvan"
        if ka:
            return "dogru", "unvan"
    return "belirsiz", None


def taraf_duzelt(ham: dict, kendi_vkn: str, anahtarlar=()):
    """Faturalar bu sisteme GELEN fatura olarak girer: firmamız her zaman ALICIDIR.
    Yapay zeka satıcı/alıcıyı ters doldurmuşsa taraflar yer değiştirilir.
    (ham_kopya, not) döndürür; not yoksa None."""
    ham = dict(ham)
    sonuc, kaynak = taraf_belirle(ham, kendi_vkn, anahtarlar)
    if sonuc == "ters":
        for x, y in _TARAF_CIFTLERI:
            ham[x], ham[y] = ham.get(y), ham.get(x)
        neyle = "vergi numarasından" if kaynak == "vkn" else "unvandaki anahtar kelimeden"
        return ham, (f"Firmanız satıcı alanında okunmuştu ({neyle} anlaşıldı); satıcı/alıcı "
                     "bilgileri yer değiştirilerek gelen fatura olarak kaydedildi. Faturayı kontrol edin")
    if sonuc == "belirsiz" and (kendi_vkn or anahtarlar):
        return ham, ("Firmanız (vergi no / unvan anahtar kelimesi) faturada alıcı olarak "
                     "bulunamadı (başka firmaya ait ya da yanlış okunmuş olabilir)")
    return ham, None


def dogrula(ham: dict, kendi_vkn: str = "", anahtarlar=()) -> dict:
    notlar = []
    k = {}

    kendi_vkn = _rakam(kendi_vkn)
    ham, taraf_notu = taraf_duzelt(ham, kendi_vkn, anahtarlar)

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

    m, kdv = sayi(ham.get("matrah")), sayi(ham.get("kdv_tutari"))   # kdv = tevkifat DÜŞÜLMEDEN tam KDV
    oran = sayi(ham.get("kdv_orani"))
    vd = sayi(ham.get("vergiler_dahil_toplam"))                    # matrah + KDV
    tev = sayi(ham.get("tevkifat_tutari"))                         # KDV tevkifat tutarı
    od = sayi(ham.get("odenecek_tutar"))                           # tevkifat düşüldükten sonra ödenecek
    if od is None:
        od = sayi(ham.get("genel_toplam"))                         # eski alan adı
    t_yazi, t_kesir = tevkifat_orani(ham.get("tevkifat_orani"))
    if tev is not None and tev <= 0:
        tev = None
    if tev is None and t_kesir and kdv is not None:                # tutar okunmadı, oran var: hesapla
        tev = round(kdv * t_kesir, 2)

    taban = vd if vd is not None else (round(m + kdv, 2) if None not in (m, kdv) else None)
    beklenen_od = round(taban - (tev or 0), 2) if taban is not None else None
    g = od if od is not None else beklenen_od                      # GENEL TOPLAM = ÖDENECEK TUTAR
    k.update(
        matrah=m, kdv_tutari=kdv,
        kdv_orani=int(oran) if oran is not None and oran == int(oran) else oran,
        vergiler_dahil=taban,
        tevkifat_var="Evet" if (tev or t_kesir) else "Hayır",
        tevkifat_orani=t_yazi, tevkifat_tutari=tev,
        genel_toplam=g,
    )

    if g is None:
        notlar.append("Genel toplam / ödenecek tutar okunamadı")
    elif od is None:
        notlar.append("Ödenecek tutar faturada okunamadı; vergiler dahil toplam − tevkifat olarak hesaplandı")
    if m is None and kdv is None:
        notlar.append("Matrah/KDV okunamadı")
    if vd is not None and None not in (m, kdv) and abs(m + kdv - vd) > 0.10:
        notlar.append(f"Matrah+KDV ({m + kdv:.2f}) vergiler dahil toplamla ({vd:.2f}) uyuşmuyor "
                      "(iskonto, başka vergi veya yuvarlama olabilir)")
    if tev and kdv is not None:
        if tev > kdv + 0.10:
            notlar.append(f"Tevkifat tutarı ({tev:.2f}) KDV tutarından ({kdv:.2f}) büyük")
        elif t_kesir:
            bek_t = kdv * t_kesir
            if abs(bek_t - tev) > max(0.5, 0.01 * bek_t):
                notlar.append(f"Tevkifat tutarı ({tev:.2f}) KDV x oran ({bek_t:.2f}) ile uyuşmuyor")
    if od is not None and beklenen_od is not None and abs(beklenen_od - od) > 0.10:
        notlar.append(f"Ödenecek tutar ({od:.2f}) ≠ vergiler dahil toplam − tevkifat ({beklenen_od:.2f}) "
                      "(stopaj, damga vergisi vb. olabilir)")
    if m and oran and kdv is not None:
        beklenen = m * oran / 100
        if abs(beklenen - kdv) > max(1.0, 0.01 * beklenen):
            notlar.append("KDV oranı/tutarı tutarsız (çok oranlı fatura olabilir)")

    k["odeme"] = _metin(ham.get("odeme_bilgisi"))

    # Bu sisteme giren her fatura gelen faturadır: yön SABİT olarak "Alış".
    # (Önceki sürümde yön, yapay zekanın satıcı/alıcıyı hangi sırada doldurduğuna
    # bağlıydı ve kararsız çıkıyordu.)
    k["yon"] = "Alış"
    if taraf_notu:
        notlar.append(taraf_notu)

    k["durum"] = "Kontrol Gerekli" if notlar else "Tamam"
    k["not"] = "; ".join(notlar)
    return k
