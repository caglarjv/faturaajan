"""Küçük kalıcı durum deposu (son okunan mail UID'si, Telegram offset vb.)."""
import json
import os

from config import VERI

_YOL = VERI / "durum.json"


def _oku():
    try:
        return json.loads(_YOL.read_text(encoding="utf-8"))
    except Exception:
        return {}


def al(anahtar, varsayilan=None):
    return _oku().get(anahtar, varsayilan)


def yaz(anahtar, deger):
    d = _oku()
    d[anahtar] = deger
    tmp = _YOL.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, _YOL)
