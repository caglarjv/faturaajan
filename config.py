"""Ayarlar: .env dosyasından okunur."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")


def _liste(v):
    return [x.strip() for x in (v or "").split(",") if x.strip()]


IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASS = os.getenv("IMAP_PASS", "")
IMAP_FOLDER = os.getenv("IMAP_FOLDER", "INBOX")
MAIL_SADECE_GONDERENLER = _liste(os.getenv("MAIL_SADECE_GONDERENLER"))
ILK_CALISMA_GUN = int(os.getenv("ILK_CALISMA_GUN", "7"))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_IZINLI_ID = [
    int(x) for x in _liste(os.getenv("TELEGRAM_IZINLI_ID")) if x.lstrip("-").isdigit()
]

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
METIN_MODELI = os.getenv("METIN_MODELI", "qwen2.5:7b")
GORSEL_MODEL = os.getenv("GORSEL_MODEL", "qwen2.5vl:3b")

KENDI_VKN = "".join(c for c in os.getenv("KENDI_VKN", "") if c.isdigit())
KONTROL_ARALIGI = int(os.getenv("KONTROL_ARALIGI", "120"))

GELEN = BASE / "gelen"
ISLENEN = BASE / "islenen"
HATALI = BASE / "hatali"
MUKERRER = BASE / "mukerrer"
VERI = BASE / "veri"
EXCEL_YOLU = BASE / "Fatura_Kayitlari.xlsx"

for _d in (GELEN, ISLENEN, HATALI, MUKERRER, VERI):
    _d.mkdir(exist_ok=True)
