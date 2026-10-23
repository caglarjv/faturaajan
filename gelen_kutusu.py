"""Gelen dosyaları 'gelen/' klasörüne kaydeder (yanına .json meta dosyası ile)."""
import datetime
import json
import re
from pathlib import Path

from config import GELEN

UZANTILAR = {".pdf", ".jpg", ".jpeg", ".png"}


_TR = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")


def guvenli(ad: str) -> str:
    """Dosya adını ASCII'ye çevirir (Türkçe karakterler Excel bağlantılarında sorun çıkarıyor)."""
    ad = ad.translate(_TR)
    return re.sub(r"[^A-Za-z0-9.\-]+", "_", ad).strip("_")[:80] or "dosya"


def meta_yolu(dosya: Path) -> Path:
    return dosya.with_name(dosya.name + ".json")


def kaydet(icerik: bytes, ad: str, meta: dict) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    yol = GELEN / f"{ts}_{guvenli(ad)}"
    yol.write_bytes(icerik)
    meta_yolu(yol).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return yol


def meta_oku(dosya: Path) -> dict:
    try:
        return json.loads(meta_yolu(dosya).read_text(encoding="utf-8"))
    except Exception:
        return {"kaynak": "Elle"}
