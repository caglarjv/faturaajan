"""Telegram botuna gönderilen PDF/fotoğrafları gelen/ klasörüne indirir."""
import logging
from pathlib import Path

import requests

import config
import gelen_kutusu
import state

log = logging.getLogger("ajan")
API = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}"
DOSYA_API = f"https://api.telegram.org/file/bot{config.TELEGRAM_TOKEN}"


def mesaj_gonder(chat_id, metin):
    requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": metin}, timeout=20)


def _indir(file_id):
    r = requests.get(f"{API}/getFile", params={"file_id": file_id}, timeout=20).json()
    yol = r["result"]["file_path"]
    return requests.get(f"{DOSYA_API}/{yol}", timeout=60).content, yol


def topla() -> int:
    if not config.TELEGRAM_TOKEN:
        return 0
    offset = state.al("tg_offset", 0)
    r = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 0}, timeout=30).json()
    adet = 0
    for u in r.get("result", []):
        state.yaz("tg_offset", u["update_id"] + 1)
        m = u.get("message")
        if not m:
            continue
        chat = m["chat"]["id"]
        if chat not in config.TELEGRAM_IZINLI_ID:
            log.warning("İzinsiz Telegram mesajı yok sayıldı. Chat ID: %s "
                        "(sizinse .env içindeki TELEGRAM_IZINLI_ID'ye ekleyin)", chat)
            continue
        try:
            doc, foto = m.get("document"), m.get("photo")
            if doc:
                ad = doc.get("file_name", "belge.pdf")
                if Path(ad).suffix.lower() not in gelen_kutusu.UZANTILAR:
                    mesaj_gonder(chat, "⚠️ Sadece PDF, JPG ve PNG destekleniyor.")
                    continue
                icerik, _ = _indir(doc["file_id"])
            elif foto:
                icerik, yol = _indir(foto[-1]["file_id"])
                ad = Path(yol).name
            else:
                continue
            kisi = (m.get("from") or {}).get("first_name", "")
            gelen_kutusu.kaydet(icerik, ad, {
                "kaynak": "Telegram", "gonderen": kisi,
                "chat_id": chat, "konu": m.get("caption", ""),
            })
            mesaj_gonder(chat, "📥 Alındı, işleniyor...")
            adet += 1
        except Exception:
            log.exception("Telegram dosyası indirilemedi")
            try:
                mesaj_gonder(chat, "❌ Dosya indirilemedi (20 MB sınırı olabilir).")
            except Exception:
                pass
    return adet
