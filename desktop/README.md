# KipGPT Masaüstü Uygulaması

Windows (ve Linux/macOS) için native pencere. Mevcut web arayüzünü **pywebview** ile açar; arka planda yerel Flask çalışır.

## Hızlı başlat (geliştirme)

### Windows

```bat
desktop\start.bat
```

### Linux / macOS

```bash
chmod +x desktop/start.sh
./desktop/start.sh
```

İlk çalıştırmada `.venv` kurulur. `.env` yoksa `.env.example` kopyalanır — en azından `FLASK_SECRET_KEY` ve `OPENAI_API_KEY` doldurun.

## Uzak sunucu (ince istemci)

Render’daki KipGPT’yi masaüstünde açmak için:

```bat
set KIPGPT_SERVER_URL=https://kip-asistan.onrender.com
desktop\start.bat
```

Bu modda yerel Flask başlamaz; sadece pencere açılır.

## Windows .exe derleme

```bat
desktop\build_windows.bat
```

Çıktı: `dist\KipGPT\KipGPT.exe`

1. `dist\KipGPT\.env` oluşturun (kök `.env`’yi kopyalayabilirsiniz)
2. `KipGPT.exe` çalıştırın

> Edge WebView2 Windows 10/11’de genelde hazırdır. Yoksa [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) kurun.

## Ortam değişkenleri

| Değişken | Açıklama |
|----------|----------|
| `KIPGPT_SERVER_URL` | Uzak sunucu; doluysa yerel Flask yok |
| `KIPGPT_DESKTOP_PORT` | Yerel port (varsayılan `5001`) |
| `KIPGPT_DESKTOP_START` | Açılış yolu (varsayılan `/login`) |
| `KIPGPT_DESKTOP_WIDTH` / `HEIGHT` | Pencere boyutu |
| `KIPGPT_WEBVIEW_GUI` | Backend: `edgechromium`, `gtk`, `qt`… |

## Microsoft Store (ileri adım)

1. Yukarıdaki `KipGPT.exe` paketini üretin  
2. [MSIX Packaging Tool](https://apps.microsoft.com/detail/9n5twpt60n64) veya Visual Studio ile MSIX oluşturun  
3. Partner Center’dan Store’a yükleyin  

İlk sürüm için Store şart değil; `.exe` dağıtımı yeterlidir.

## Gereksinimler

- Python 3.10+
- `requirements.txt` + `desktop/requirements.txt`
- Linux’ta: `python3-gi` / WebKitGTK (veya Qt)
