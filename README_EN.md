[English](README_EN.md) | [Русский](README.md)

# Kindle Studio & Native AI Chat

> Turn your Amazon Kindle (Kindle Keyboard 3, 4, 5, Paperwhite) into an E-Ink monitor, desktop clock, system dashboard, and standalone AI assistant terminal with full Russian touch typing.

---

## Features

### 1. Kindle Studio 2.0 (Desktop PC Application)
* **Authentic E-Ink Design:** High-contrast Carta E-Paper styling (#f5f4ef / #111111), retro headers, enlarged typography, and spacious controls across all 7 tabs.
* **Real-time Screen Streaming:** Streams your computer screen to the Kindle display in real time, turning it into a dedicated E-Ink secondary monitor for reading code, logs, or documentation without eye fatigue.
* **System Dashboard & Weather:** Displays live CPU, RAM, disk usage, network transfer rates, local weather forecast, and a calendar.
* **Desktop Clock:** Full-screen clock face featuring current date and weather, ideal for a nightstand or desk setup.
* **Notes & To-Do List:** Interactive task list with sticky-note export and checkbox rendering.
* **Canvas & Image Viewer:** Freehand drawing canvas, image slideshow, and Floyd-Steinberg dithering for crisp grayscale reproduction on E-Ink.
* **Wireless Book Sync & Universal Converter:** Inspects books stored on the Kindle (over Wi-Fi via SSH or over USB) with instant search and file deletion. Accepts any book format (.epub, .fb2, .docx, .txt, .pdf), automatically converts via Calibre into Kindle-compatible formats (.mobi, .azw3), and deploys wirelessly with automatic Kindle library re-indexing.
* **Full Bilingual Localization (RU / EN):** Instant one-click language toggle between Russian and English in the top bar — all labels, buttons, tooltips, and generated Kindle screens (clock, dashboard, tasks) dynamically adjust to the selected language.
* **Firmware & AI Installer:** Automatically detects USB-connected Kindle storage and deploys AI chat binaries, scripts, and KUAL extensions in one click.

---

### 2. Kindle AI Chat (Standalone On-Device AI)
* **Standalone execution on Kindle hardware:** Once deployed, no connection to a computer is required. The Kindle connects directly via Wi-Fi and queries the Polza.ai API (GLM-5.3 Flash model).
* **Direct rendering without terminal emulators:** A native ARM Go binary writes directly to the framebuffer (`/dev/fb0`) and triggers hardware E-Ink controller screen updates.
* **High-Contrast Dark Mode:** Pure white text on a solid black background, providing maximum contrast and readability on Pearl E-Ink screens without grayscale ghosting or fading.
* **Full Russian touch-typing (ЙЦУКЕН) on the physical keyboard:**
  * Layout switch: `SYM` button toggles between `[RU]` and `[EN]`.
  * Supplementary Cyrillic letters accessible via `Alt`:
    * `Alt + P` = х
    * `Alt + O` = ъ
    * `Alt + L` = ж
    * `Alt + K` = э
    * `Alt + M` = б
    * `Alt + E` = ё
  * Punctuation shortcuts: double-tapping `Space` produces a period followed by a space (`. `), `Alt + Space` produces a comma followed by a space (`, `).
  * Smooth response paging using physical page-turn buttons or the 5-way D-pad up/down arrows.
  * Instant exit back to the Kindle home library via physical `HOME` or `BACK` buttons.

---

## Guide: Jailbreak and Kindle Preparation

This guide is tailored for the Kindle Keyboard 3 (K3W / K3G) and is compatible with Kindle 4 and Kindle 5 devices.

### Step 1. Jailbreak
1. Connect the Kindle to your PC using a USB cable.
2. Download the jailbreak archive from the MobileRead Kindle Jailbreak repository thread.
3. Copy the installation binary matching your device model (e.g., `update_jailbreak_0.13.N_k3w_install.bin`) to the root of the Kindle USB drive.
4. Safely eject the drive in your operating system and unplug the USB cable.
5. On the device, navigate to: `[Home]` -> `[Menu]` -> `Settings` -> `[Menu]` -> `Update Your Kindle`.
6. Wait for the Kindle to restart. A confirmation message (`Jailbreak succeeded`) will appear at the bottom of the screen.

---

### Step 2. Install MKK and KUAL (Application Launcher)
1. Reconnect your Kindle via USB.
2. Copy the MKK update binary (e.g., `update_mkk_20141129_k3w_install.bin`) to the root directory and apply it via `Settings` -> `Update Your Kindle`.
3. Copy `KUAL-KDK-1.0.azw2` into the `documents/` folder on the Kindle drive.
4. Eject the Kindle. A new document titled `KUAL` will appear in your home library, providing the launcher menu for third-party extensions.

---

### Step 3. Install USBNetwork (SSH and Network Access)
1. Copy the USBNetwork installer (`update_usbnetwork_..._k3w_install.bin`) to the root of the Kindle drive and run `Update Your Kindle`.
2. Configure SSH/Wi-Fi access inside the `usbnet/` folder if you plan to use screen streaming from Kindle Studio over the local network.

---

## Installing AI Chat on Kindle

### Method 1: Automatic via Kindle Studio (Recommended)
1. Connect your Kindle to your PC using USB.
2. Launch `Kindle_GUI.bat` (or run `python kindle_studio.py`).
3. Switch to the "Firmware & AI" tab.
4. Click "Find Kindle (USB)" to detect the Kindle drive letter automatically.
5. Enter your Polza.ai API key in the configuration field.
6. Click "Install AI Chat on Kindle". The tool automatically copies all binaries, scripts, and KUAL extension configurations to the reader and generates `config.json`.
7. Eject the device, open KUAL in the Kindle library, and select `AI Chat (GLM-5.3)`.

---

### Method 2: Manual Installation
1. Copy the folder `ai_deploy/ai` to the root of the Kindle drive (target path: `/mnt/us/ai`).
2. Copy the folder `ai_deploy/extensions/ai_chat` to `extensions/ai_chat` on the Kindle drive.
3. Create the file `/mnt/us/ai/config.json` with the following structure:
   ```json
   {
     "api_key": "YOUR_POLZA_AI_KEY",
     "model": "z-ai/glm-5.3-flash"
   }
   ```
4. Safely eject the Kindle and launch `AI Chat (GLM-5.3)` from the KUAL menu.

---

## Key Bindings Reference for AI Chat

| Action | Key / Combination |
| :--- | :--- |
| Toggle Layout (RU / EN) | `SYM` key (status header displays `[RU]` or `[EN]`) |
| Touch-typing Russian (ЙЦУКЕН) | `Q..P` -> `й..з`, `A..L` -> `ф..д`, `Z..M` -> `я..ь`, `.` -> `ю` |
| Additional Cyrillic letters | `Alt + P` = х, `Alt + O` = ъ, `Alt + L` = ж, `Alt + K` = э, `Alt + M` = б, `Alt + E` = ё |
| Period (.) | Double-tap `Space` (or press `Alt + .`) |
| Comma (,) | `Alt + Space` (inserts comma and space) |
| Question mark (?) | `Shift + Alt + .` |
| Exclamation mark (!) | `Alt + A` |
| Hyphen (-) | `Alt + Z` |
| Scroll response text | Side page-turn buttons or 5-way D-pad Up / Down |
| Send prompt | `Enter` |
| Reset conversation history | Type `/new` in the prompt input line |
| Exit to home library | Physical `HOME` or `BACK` button |

---

## Running Kindle Studio on PC

### Launching the Application:
Run `Kindle_GUI.bat` or execute:
```bash
python kindle_studio.py
```

### Requirements:
* Python 3.9+
* Required libraries:
  ```bash
  pip install pillow requests mss psutil
  ```

### Configuration (`config.json`):
Create `config.json` using `config.example.json` as a reference:
```json
{
  "ip": "192.168.1.100",
  "city": "London",
  "rotation": 270,
  "api_key": "YOUR_KEY_HERE",
  "model": "z-ai/glm-5.3-flash"
}
```

---

## Project Structure

```text
├── kindle_studio.py           # Desktop management GUI for Kindle Studio
├── Kindle_GUI.bat             # Quick launch script for Windows
├── kindle_chat_gui.go         # Native E-Ink chat client in Go (direct Linux kernel syscalls)
├── font_data.go               # Embedded 24px Cyrillic and Latin bitmap font
├── gen_font.py                # BDF/HEX font converter for Go bitmap tables
├── kindle-ai                  # Precompiled ARMv6 ELF binary (Linux 2.6 compatible)
├── ai_deploy/                 # Deployment bundle for Kindle (ai and extensions folders)
│   ├── ai/                    # Native binary, launcher script, and curl worker
│   └── extensions/ai_chat/    # KUAL extension configuration and launch menu
├── kindle_books.py            # Wireless book sync and Calibre universal converter module
├── kindle_display.py          # Graphics processing and E-Ink display driver module
├── kindle_stream.py           # PC screen capture and low-latency streaming
├── kindle_pic.py              # Image processing and Floyd-Steinberg dithering
├── config.example.json        # Template configuration file
├── README.md                  # Project documentation (Russian)
└── README_EN.md               # Project documentation (English)
```

---

## Authors and Acknowledgments

* **aniansh19019** ([github.com/aniansh19019/kindle-display-utils](https://github.com/aniansh19019/kindle-display-utils)) — Author of the original `kindle-display-utils` project and foundational graphics streaming scripts (`kindle_display.py`, `screen_stream.py`).
* **Luigi Rizzo** (Universita di Pisa) — Author of the lightweight `myts` terminal for E-Ink hardware (`terminal.c`).
* **NiLuJe** and the **MobileRead** community — Creators and maintainers of `KUAL`, `MKK`, `FBInk`, `USBNetwork`, and Kindle jailbreak packages.

---

## License

This project is licensed under the MIT License.
