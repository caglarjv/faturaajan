"""Faturadan alanları çıkarır.
- Metin içeren PDF  -> metin modeli (hızlı, doğru)
- Taranmış PDF / fotoğraf -> görsel model (OCR işini de yapar)
Çıktı her zaman sabit bir JSON şemasına uyar."""
import base64
import io
import json
import logging
from pathlib import Path

import fitz  # pymupdf
import requests
from PIL import Image

import config

log = logging.getLogger("ajan")


def _t(tip):
    return {"anyOf": [{"type": tip}, {"type": "null"}]}


ALANLAR = {
    "fatura_tarihi": "string", "fatura_no": "string", "ettn": "string",
    "satici_unvan": "string", "satici_vkn": "string", "satici_vergi_dairesi": "string",
    "alici_unvan": "string", "alici_vkn": "string", "alici_vergi_dairesi": "string",
    "para_birimi": "string", "matrah": "number", "kdv_orani": "number",
    "kdv_tutari": "number", "genel_toplam": "number", "odeme_bilgisi": "string",
}
SEMA = {
    "type": "object",
    "properties": {k: _t(v) for k, v in ALANLAR.items()},
    "required": list(ALANLAR),
}

PROMPT = """Sen bir Türk muhasebe asistanısın. Aşağıdaki fatura/e-fatura belgesinden alanları çıkar.
Kurallar:
- Sadece belgede açıkça yazan değerleri kullan. Bulamazsan null yaz, ASLA tahmin etme.
- Satıcı (faturayı düzenleyen, belgenin üstündeki firma) ile alıcıyı ('SAYIN', 'Alıcı' bölümü) karıştırma.
- fatura_tarihi YYYY-AA-GG biçiminde olsun.
- fatura_no belgedeki 'Fatura No' değeridir (örn. ABC2024000000123). ettn ise UUID biçimli koddur.
- Vergi numarası 10 hane, TC kimlik numarası 11 hane; sadece rakam yaz. Vergi dairesi adını yaz.
- Tutarlar sayı olsun (binlik ayracı yok, ondalık nokta). 
- matrah = KDV hariç toplam (iskonto sonrası mal/hizmet tutarı). 
- kdv_tutari = hesaplanan toplam KDV. genel_toplam = vergiler dahil ödenecek tutar.
- kdv_orani: tek oran varsa o (örn. 20); birden fazlaysa tutarı en yüksek olan.
- para_birimi: TRY, USD, EUR gibi kod.
- odeme_bilgisi: varsa IBAN veya ödeme şekli.
"""


def _gorsel_hazirla(veri: bytes) -> bytes:
    im = Image.open(io.BytesIO(veri))
    im = im.convert("RGB")
    im.thumbnail((1568, 1568))
    cikti = io.BytesIO()
    im.save(cikti, "JPEG", quality=90)
    return cikti.getvalue()


def _pdf_oku(yol: Path):
    with fitz.open(yol) as doc:
        metin = "\n".join(sayfa.get_text() for sayfa in doc)
        png = doc[0].get_pixmap(dpi=170).tobytes("png") if len(doc) else b""
    return metin, png


def _ollama(model, prompt, resimler=None):
    mesaj = {"role": "user", "content": prompt}
    if resimler:
        mesaj["images"] = [base64.b64encode(r).decode() for r in resimler]
    r = requests.post(
        f"{config.OLLAMA_URL}/api/chat",
        json={
            "model": model, "messages": [mesaj], "stream": False, "format": SEMA,
            "options": {"temperature": 0, "num_ctx": 8192},
        },
        timeout=900,
    )
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])


def _yeterli(d) -> bool:
    return bool(d.get("fatura_no") or d.get("genel_toplam"))


def cikar(yol: Path):
    """(ham_alanlar, yontem) döndürür."""
    ext = yol.suffix.lower()
    if ext == ".pdf":
        metin, png = _pdf_oku(yol)
        if len(metin.strip()) >= 150:
            d = _ollama(config.METIN_MODELI, PROMPT + "\nBELGE METNİ:\n" + metin[:9000])
            if _yeterli(d) or not png:
                return d, "pdf-metin"
            log.info("Metin yönteminden yeterli veri çıkmadı, görsel yönteme geçiliyor")
        if not png:
            raise ValueError("PDF boş")
        d = _ollama(config.GORSEL_MODEL, PROMPT, [_gorsel_hazirla(png)])
        return d, "pdf-gorsel"
    d = _ollama(config.GORSEL_MODEL, PROMPT, [_gorsel_hazirla(yol.read_bytes())])
    return d, "foto-gorsel"
