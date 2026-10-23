# Fatura Ajanı (ücretsiz, yerel)

Mail (Gmail) ve Telegram'dan gelen e-fatura PDF'lerini ve fatura fotoğraflarını yerel yapay zekayla okuyup
`Fatura_Kayitlari.xlsx` dosyasına kaydeder. Hiçbir veri bilgisayarınızdan çıkmaz; ücretli servis yoktur.

```
Gmail (IMAP) ─┐
              ├─> gelen/ ─> okuma (PDF metni / görsel model) ─> doğrulama ─> Excel
Telegram bot ─┘                                                  └─> islenen/YIL/AY/ arşivi
```

## Kurulum (Windows)

  **Dikkat** 
  Repo'yu zip/rar olarak indirin. Kurulumu, Çalıştırmak istediğiniz alana dosya olarak çıkartın. Dosya manuel taşınacak olursa sistem hata verir.
  Yaklaşık olarak 8 gb download ihtiyacı vardır.
  
1. Eğer yoksa, **Python 3.10+** kurun (python.org, kurulumda "Add to PATH" işaretli olsun).
2. **Ollama** kurun (ollama.com/download).
3. **DİKKAT!!! yönetici olarak çalıştırmayın.** `kurulum.bat` dosyasına çift tıklayın  (paketleri ve iki modeli indirir, bir kez yapılır).
4. `.env` dosyasını Not Defteri ile açıp doldurun (aşağıya bakın).
5. `baslat.bat` ile çalıştırın. Pencere açık kaldığı sürece ajan çalışır.
   Bilgisayar açılınca otomatik başlasın isterseniz `baslat.bat` kısayolunu
   `Win+R` > `shell:startup` klasörüne koyun.

## Gmail mi Outlook mu?

**Gmail kullanın.** Gmail "uygulama şifresi" ile IMAP'e izin verir. Microsoft ise kişisel Outlook/Hotmail
hesaplarında şifreyle IMAP erişimini kapattı; OAuth ve Azure uygulama kaydı gerektirir (karmaşık).
Outlook'a gelen faturalar için: Outlook ayarlarından Gmail adresine **otomatik yönlendirme kuralı** ekleyin.

Gmail uygulama şifresi:
1. Google Hesabı > Güvenlik > **2 adımlı doğrulama**yı açın.
2. myaccount.google.com/apppasswords adresinde yeni bir şifre oluşturun (16 haneli).
3. `.env` içinde `IMAP_USER` ve `IMAP_PASS` alanlarına yazın.

Mailler **okundu işaretlenmez**, gelen kutunuza dokunulmaz.

## Telegram

1. Telegram'da `@BotFather` > `/newbot` ile bot oluşturun, token'ı `.env` > `TELEGRAM_TOKEN`'a yazın.
2. Ajanı başlatıp botunuza herhangi bir mesaj atın. Log'da "Chat ID: 123456789" görünür;
   bu sayıyı `TELEGRAM_IZINLI_ID`'ye yazın ve ajanı yeniden başlatın (başkaları botu kullanamaz).
3. Artık bota PDF veya fotoğraf gönderin; ajan sonucu size mesajla bildirir.
   İpucu: fotoğrafı "dosya olarak" göndermek daha net okunur.

## Excel şablonu

- **Faturalar** sayfası: Fatura tarihi/no, ETTN, satıcı ve alıcı unvan/VKN/vergi dairesi, matrah, KDV oranı ve
  tutarı, genel toplam, para birimi, ödeme/IBAN, kaynak, arşiv yolu, durum ve kontrol notu.
  `Hesap Kodu` ve `Kategori` sütunlarını muhasebe için siz doldurursunuz.
- **Özet** sayfası: yıl/para birimi bazında alış-satış toplamları, aylık KDV tablosu, ödenecek/devreden KDV.
- Sarı satır = "Kontrol Gerekli". Nedeni `Kontrol Notu` sütunundadır.
- Ajan çalışırken Excel açıksa yazamaz; dosyayı kapatınca bekleyen faturalar otomatik işlenir.

## Doğrulama (ajan şunları kontrol eder)

- VKN (10 hane) ve TCKN (11 hane) algoritma doğrulaması
- Matrah + KDV = Genel toplam; KDV oranı ile KDV tutarı uyumu
- Tarih makullüğü, eksik alanlar
- Aynı dosya / aynı fatura numarası + satıcı ikinci kez eklenmez (`mukerrer/` klasörüne taşınır)

Yapay zeka hata yapabilir. Şüpheli kayıtlar işaretlenir ama işaretlenmeyen kayıtları da ara ara kontrol edin.

## Klasörler

| Klasör | Ne var |
|---|---|
| `gelen/` | İşlenmeyi bekleyenler. **Buraya elle PDF/JPG atabilirsiniz**, ajan alır |
| `islenen/YIL/YIL-AY/` | Başarılı faturalar, `tarih_satici_faturano` adıyla |
| `hatali/` | Okunamayanlar + `.hata.txt` |
| `mukerrer/` | Daha önce işlenmiş olanlar |
| `veri/` | Log ve durum dosyası |

## Donanımınıza göre model

Test için kullanılan, RTX 4050 (6 GB VRAM) için varsayılanlar: `qwen2.5:7b` (metin PDF) ve `qwen2.5vl:3b` (fotoğraf/tarama).
Fotoğraflarda doğruluk yetmezse `.env` içinde `GORSEL_MODEL=qwen2.5vl:7b` deneyin
(önce `ollama pull qwen2.5vl:7b`); biraz daha yavaş ama daha doğru olur.
Fatura başına tipik süre: metin PDF birkaç saniye, fotoğraf 10-40 sn.

## Elle test

```
python main.py --dosya C:\yol\fatura.pdf
```
