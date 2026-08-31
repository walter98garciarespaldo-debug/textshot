<h1 align="center">⌖ TextShot</h1>

<div align="center">

<a href="https://github.com/walter98garciarespaldo-debug/textshot/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/walter98garciarespaldo-debug/textshot?style=flat-square&color=00d4ff"></a>
<a href="https://github.com/walter98garciarespaldo-debug/textshot/blob/master/LICENSE.txt"><img alt="License" src="https://img.shields.io/github/license/walter98garciarespaldo-debug/textshot?style=flat-square"></a>
<a href="https://github.com/tesseract-ocr/tesseract"><img alt="Tesseract" src="https://img.shields.io/badge/OCR-Tesseract%205-00d4ff?style=flat-square"></a>
<a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square"></a>

**Fork of [ianzhao/textshot](https://github.com/ianzhao/textshot) — extended with a full desktop GUI, system tray, global hotkey, and capture history.**

</div>

---

## What's new in this fork

| Feature | Original | This fork |
|---|:---:|:---:|
| CLI screenshot OCR | ✅ | ✅ |
| Dark GUI with capture history | ❌ | ✅ |
| System tray (background mode) | ❌ | ✅ |
| Global hotkey `Ctrl+Alt+S` | ❌ | ✅ |
| Preview & edit before copying | ❌ | ✅ |
| Windows silent launcher (no console) | ❌ | ✅ |
| Auto-start with Windows | ❌ | ✅ |

---

## Screenshots

> Draw a rectangle around any text on screen → instantly copied to clipboard.

---

## Installation

### 1. Prerequisites

Install **Tesseract OCR** (required):
- **Windows**: Download from [UB-Mannheim releases](https://github.com/UB-Mannheim/tesseract/releases) and install. Then add `C:\...\Tesseract-OCR` to your PATH.
- **macOS**: `brew install tesseract`
- **Linux**: `sudo apt install tesseract-ocr`

### 2. Clone & install

```bash
git clone https://github.com/walter98garciarespaldo-debug/textshot.git
cd textshot
pip install -r requirements.txt
```

### 3. Run the GUI

```bash
python run_gui.py
```

On **Windows**, to run silently without a console window, double-click `TextShot.vbs` or use the generated desktop shortcut.

### 4. Setup auto-start (Windows)

Run once to add TextShot to Windows startup and create a desktop shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File install_startup.ps1
```

---

## Usage

### GUI mode (recommended)

```bash
python run_gui.py           # English OCR (default)
python run_gui.py spa       # Spanish
python run_gui.py eng+spa   # English + Spanish
```

**Hotkey**: `Ctrl+Alt+S` — works globally from any app (requires running as Administrator on Windows for system-level hotkey capture).

**Tray icon**: Close the window to minimize to system tray. The app keeps running in the background. Click the tray icon to reopen the history window.

### CLI mode (original)

```bash
textshot            # one-time capture
textshot eng+fra    # with French fallback
textshot -i 200     # capture every 200ms from a fixed region
```

---

## Supported languages

Tesseract supports [100+ languages](https://github.com/tesseract-ocr/tesseract/blob/master/doc/tesseract.1.asc#languages-and-scripts). Install the corresponding data files and pass the language code:

```bash
python run_gui.py spa      # Spanish
python run_gui.py deu      # German
python run_gui.py eng+jpn  # English + Japanese
```

---

## Files

| File | Description |
|---|---|
| `textshot/gui.py` | GUI: tray app, main window, hotkey thread |
| `run_gui.py` | Entry point for the GUI |
| `TextShot.vbs` | Silent Windows launcher (no console) |
| `install_startup.ps1` | One-time setup: autostart + desktop shortcut |
| `textshot/textshot.py` | Original CLI logic (unchanged) |
| `textshot/ocr.py` | Tesseract OCR wrapper (unchanged) |

---

## Requirements

```
Python >= 3.10
PyQt5
pytesseract
Pillow
pyperclip
keyboard
```

---

## License

MIT — see [LICENSE.txt](LICENSE.txt).  
Original project by [Ian Zhao](https://github.com/ianzhao/textshot).
