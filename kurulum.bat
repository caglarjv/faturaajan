@echo off
chcp 65001 >nul
echo === Fatura Ajani kurulumu ===
where python >nul 2>nul || (echo Python bulunamadi. https://www.python.org/downloads/ adresinden kurun ^(Add to PATH secili olsun^). & pause & exit /b 1)
where ollama >nul 2>nul || (echo Ollama bulunamadi. https://ollama.com/download adresinden kurun, sonra bu dosyayi tekrar calistirin. & pause & exit /b 1)

python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Yapay zeka modelleri indiriliyor ^(toplam yaklasik 8 GB, bir kez^)...
ollama pull qwen2.5:7b
ollama pull qwen2.5vl:3b

if not exist .env copy .env.example .env >nul
python excel_yazici.py

echo.
echo Kurulum tamam. Simdi ".env" dosyasini not defteriyle acip doldurun,
echo sonra "baslat.bat" ile ajani calistirin.
pause
