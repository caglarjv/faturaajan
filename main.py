"""Fatura ajanı: mail + Telegram'dan topla -> yapay zeka ile oku -> doğrula -> Excel'e yaz.

Kullanım:
  python main.py                 # sürekli çalışır
  python main.py --bir-kez       # tek tur çalışıp çıkar
  python main.py --dosya x.pdf   # tek bir dosyayı elle işler
"""
import argparse
import datetime
import hashlib
import logging
import shutil
import sys
import time
from pathlib import Path

import requests

import config
import excel_yazici
import extractor
import gelen_kutusu
import mail_toplayici
import telegram_toplayici
import validator
from excel_yazici import ExcelKilitli

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.VERI / "ajan.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("ajan")


def _bildir(meta, metin):
    if meta.get("kaynak") == "Telegram" and meta.get("chat_id"):
        try:
            telegram_toplayici.mesaj_gonder(meta["chat_id"], metin)
        except Exception:
            log.warning("Telegram bildirimi gönderilemedi")


def _tasi(dosya: Path, hedef: Path):
    hedef.parent.mkdir(parents=True, exist_ok=True)
    if hedef.exists():
        hedef = hedef.with_name(f"{hedef.stem}_{int(time.time())}{hedef.suffix}")
    shutil.move(str(dosya), str(hedef))
    meta = gelen_kutusu.meta_yolu(dosya)
    if meta.exists():
        meta.unlink()
    return hedef


def isle(dosya: Path):
    meta = gelen_kutusu.meta_oku(dosya)
    h = hashlib.sha256(dosya.read_bytes()).hexdigest()[:16]

    neden = excel_yazici.mukerrer_mi(h)
    if neden:
        log.info("Mükerrer atlandı: %s (%s)", dosya.name, neden)
        _tasi(dosya, config.MUKERRER / dosya.name)
        _bildir(meta, f"ℹ️ Atlandı: {neden}.")
        return

    log.info("İşleniyor: %s", dosya.name)
    try:
        ham, yontem = extractor.cikar(dosya)
        k = validator.dogrula(ham, config.KENDI_VKN)
    except Exception as e:
        log.exception("Okunamadı: %s", dosya.name)
        hedef = _tasi(dosya, config.HATALI / dosya.name)
        hedef.with_name(hedef.name + ".hata.txt").write_text(repr(e), encoding="utf-8")
        _bildir(meta, f"❌ Fatura okunamadı: {e}")
        return

    neden = excel_yazici.mukerrer_mi(h, k["fatura_no"], k["satici_vkn"])
    if neden:
        log.info("Mükerrer atlandı: %s (%s)", dosya.name, neden)
        _tasi(dosya, config.MUKERRER / dosya.name)
        _bildir(meta, f"ℹ️ Atlandı: {neden}.")
        return

    t = k["fatura_tarihi"] or datetime.date.today()
    ad = "_".join([
        t.strftime("%Y-%m-%d"),
        gelen_kutusu.guvenli(k["satici_unvan"] or "bilinmiyor")[:30],
        gelen_kutusu.guvenli(k["fatura_no"] or h),
    ]) + dosya.suffix.lower()
    arsiv = config.ISLENEN / str(t.year) / t.strftime("%Y-%m") / ad

    k.update(
        kaynak=meta.get("kaynak", "Elle"),
        gonderen=meta.get("gonderen", ""),
        dosya_adi=dosya.name,
        arsiv_yolu=str(arsiv),
        hash=h,
    )
    kayit_no = excel_yazici.ekle(k)  # ExcelKilitli fırlatabilir -> dosya gelen/'de kalır
    _tasi(dosya, arsiv)

    log.info("Kaydedildi #%s | %s | %s | %s %s | %s", kayit_no, k["fatura_no"],
             k["satici_unvan"], k["genel_toplam"], k["para_birimi"], k["durum"])
    ozet = (f"{k['satici_unvan']} | No: {k['fatura_no']} | "
            f"{k['genel_toplam']} {k['para_birimi']}")
    if k["durum"] == "Tamam":
        _bildir(meta, f"✅ Kaydedildi (#{kayit_no}): {ozet}")
    else:
        _bildir(meta, f"⚠️ Kaydedildi ama kontrol gerekli (#{kayit_no}): {ozet}\n{k['not']}")


def tur():
    for ad, fn in (("Mail", mail_toplayici.topla), ("Telegram", telegram_toplayici.topla)):
        try:
            n = fn()
            if n:
                log.info("%s: %d yeni dosya alındı", ad, n)
        except Exception:
            log.exception("%s toplanırken hata", ad)

    for dosya in sorted(config.GELEN.iterdir()):
        if dosya.suffix.lower() not in gelen_kutusu.UZANTILAR:
            continue
        try:
            isle(dosya)
        except ExcelKilitli:
            log.warning("Excel dosyası açık, yazılamadı. Kapatın; sonraki turda denenecek.")
            return


def ollama_kontrol():
    try:
        r = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5).json()
        mevcut = {m["name"] for m in r.get("models", [])}
        for m in (config.METIN_MODELI, config.GORSEL_MODEL):
            if m not in mevcut and f"{m}:latest" not in mevcut:
                log.warning("Model yüklü değil: %s  ->  'ollama pull %s'", m, m)
    except Exception:
        log.error("Ollama'ya ulaşılamıyor (%s). Ollama uygulaması çalışıyor mu?", config.OLLAMA_URL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bir-kez", action="store_true")
    ap.add_argument("--dosya")
    a = ap.parse_args()

    if not config.EXCEL_YOLU.exists():
        excel_yazici.sablon_olustur()
    ollama_kontrol()

    if a.dosya:
        src = Path(a.dosya)
        gelen_kutusu.kaydet(src.read_bytes(), src.name, {"kaynak": "Elle"})
        tur()
        return
    if a.bir_kez:
        tur()
        return

    log.info("Ajan başladı. Durdurmak için Ctrl+C. Kontrol aralığı: %s sn", config.KONTROL_ARALIGI)
    while True:
        tur()
        time.sleep(config.KONTROL_ARALIGI)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Durduruldu.")
