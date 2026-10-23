"""IMAP ile maili okur, PDF/JPG/PNG eklerini gelen/ klasörüne indirir.
Mailler okundu işaretlenmez (BODY.PEEK); sadece son UID kaydedilir."""
import datetime
import email
import imaplib
from email.header import decode_header, make_header
from pathlib import Path

import config
import gelen_kutusu
import state

AYLAR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _coz(v):
    try:
        return str(make_header(decode_header(v or "")))
    except Exception:
        return v or ""


def _mail_isle(M, uid) -> int:
    _, d = M.uid("fetch", str(uid), "(BODY.PEEK[])")
    if not d or not d[0] or not isinstance(d[0], tuple):
        return 0
    msg = email.message_from_bytes(d[0][1])
    gonderen = _coz(msg.get("From"))
    konu = _coz(msg.get("Subject"))
    if config.MAIL_SADECE_GONDERENLER and not any(
        s.lower() in gonderen.lower() for s in config.MAIL_SADECE_GONDERENLER
    ):
        return 0
    adet = 0
    for part in msg.walk():
        ad = part.get_filename()
        if not ad:
            continue
        ad = _coz(ad)
        ext = Path(ad).suffix.lower()
        if ext not in gelen_kutusu.UZANTILAR:
            continue
        icerik = part.get_payload(decode=True)
        if not icerik:
            continue
        # imza logosu gibi küçük görselleri atla
        if ext != ".pdf" and len(icerik) < 20000:
            continue
        gelen_kutusu.kaydet(icerik, ad, {"kaynak": "Mail", "gonderen": gonderen, "konu": konu})
        adet += 1
    return adet


def topla() -> int:
    if not (config.IMAP_USER and config.IMAP_PASS):
        return 0
    adet = 0
    M = imaplib.IMAP4_SSL(config.IMAP_HOST)
    try:
        M.login(config.IMAP_USER, config.IMAP_PASS)
        M.select(config.IMAP_FOLDER, readonly=True)
        son = state.al("mail_son_uid")
        if son is None:
            g = datetime.date.today() - datetime.timedelta(days=config.ILK_CALISMA_GUN)
            tarih = f"{g.day:02d}-{AYLAR[g.month - 1]}-{g.year}"
            _, veri = M.uid("search", None, "SINCE", tarih)
        else:
            _, veri = M.uid("search", None, "UID", f"{son + 1}:*")
        uidler = sorted(int(x) for x in veri[0].split())
        if son is not None:
            uidler = [u for u in uidler if u > son]
        for uid in uidler:
            adet += _mail_isle(M, uid)
            state.yaz("mail_son_uid", uid)
    finally:
        try:
            M.logout()
        except Exception:
            pass
    return adet
