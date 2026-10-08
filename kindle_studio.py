import os
import sys
import time
import json
import calendar
import datetime
import threading
import subprocess
import urllib.request
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageOps, ImageTk, ImageDraw, ImageFont

try:
    import psutil
except ImportError:
    psutil = None

try:
    import mss
except ImportError:
    mss = None

import kindle_books

# Constants & Defaults
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_IP = "192.168.31.78"
DEFAULT_CITY = "Kirovo-Chepetsk"
SSH_KEY = os.path.expanduser(r"~/.ssh/kindle_key")
SSH_OPTS = f"-i {SSH_KEY} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=3"

X_RES = 600
Y_RES = 800

MONTH_NAMES_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]
MONTH_GEN_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]
WEEKDAYS_RU = [
    "ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"
]

I18N = {
    "ru": {
        "title": "Kindle Studio 2.0 - Стриминг, Монитор, Часы и Книги",
        "tab_canvas": "🎨 Холст и Фото",
        "tab_stream": "🖥️ Стриминг ПК",
        "tab_dash": "📊 Дашборд ПК",
        "tab_clock": "🕰️ Часы и Календарь",
        "tab_todo": "📝 Заметки / To-Do",
        "tab_books": "📚 Книги & Wi-Fi",
        "tab_jb": "🚀 Прошивка & AI",
        "ip_label": "Kindle IP:",
        "btn_ping": "📶 Проверить связь",
        "btn_send": "🚀 Отправить на Kindle",
        "btn_clear": "⌫ Очистить экран",
        "btn_shortcut": "📌 Ярлык на Рабочий стол",
        "btn_lang": "🌐 English",
        "ready": "Готов к работе",
        "books_header": "KINDLE E-INK BOOKSHELF  •  БЕСПРОВОДНАЯ КНИЖНАЯ ПОЛКА",
        "books_wifi_mode": "📶 Wi-Fi (SSH)",
        "books_usb_mode": "🔌 USB Накопитель",
        "books_refresh": "🔄 Обновить список книг",
        "books_search": "🔍 Поиск по названию:",
        "books_col_name": "Название книги / Файл",
        "books_col_ext": "Формат",
        "books_col_size": "Размер",
        "books_delete": "🗑 Удалить выбранную книгу",
        "books_rescan": "⚡ Обновить экран Kindle",
        "books_upload_box": " 📤 Загрузка и автоконвертация книг по воздуху (Wi-Fi) ",
        "books_pick_btn": "➕ Выбрать книги для отправки на Kindle...",
        "books_target_fmt": "Целевой формат:",
        "books_skip_native": "Не конвертировать родные форматы (MOBI, AZW3, PDF)",
        "books_calibre_ok": "✅ Calibre ebook-convert готов",
        "books_calibre_missing": "⚠️ Calibre не найден (только прямая отправка MOBI/PDF)",
        "books_waiting": "Выберите книги на ПК для отправки на читалку...",
        "books_count": "Книг на читалке: {count} (Всего: {size})",
        "books_delete_confirm": "Удалить книгу '{name}' с читалки Kindle?",
        "books_delete_ok": "Книга '{name}' успешно удалена с Kindle.",
        "books_wake_hint": "Разбудите читалку (сдвиньте ползунок включения), чтобы активировать Wi-Fi.",
        "books_sent_success": "✓ Все книги успешно загружены на Kindle ({count} шт.)!",
        "books_offline": "🔴 Офлайн (сдвиньте ползунок включения)",
        "books_online": "🟢 В сети (Wi-Fi)",
        "books_usb_online": "🔌 Подключен (USB {drive})",
        "books_loading": "● Чтение списка книг...",
    },
    "en": {
        "title": "Kindle Studio 2.0 - Screen Streamer, Monitor, Clock & Books",
        "tab_canvas": "🎨 Canvas & Photo",
        "tab_stream": "🖥️ PC Stream",
        "tab_dash": "📊 PC Dashboard",
        "tab_clock": "🕰️ Clock & Calendar",
        "tab_todo": "📝 Notes / To-Do",
        "tab_books": "📚 Books & Wi-Fi",
        "tab_jb": "🚀 Firmware & AI",
        "ip_label": "Kindle IP:",
        "btn_ping": "📶 Ping Test",
        "btn_send": "🚀 Send to Kindle",
        "btn_clear": "⌫ Clear Screen",
        "btn_shortcut": "📌 Desktop Shortcut",
        "btn_lang": "🌐 Русский",
        "ready": "Ready",
        "books_header": "KINDLE E-INK BOOKSHELF  •  WIRELESS BOOK MANAGER",
        "books_wifi_mode": "📶 Wi-Fi (SSH)",
        "books_usb_mode": "🔌 USB Storage",
        "books_refresh": "🔄 Refresh Book List",
        "books_search": "🔍 Search by title:",
        "books_col_name": "Book Title / Filename",
        "books_col_ext": "Format",
        "books_col_size": "Size",
        "books_delete": "🗑 Delete Selected Book",
        "books_rescan": "⚡ Rescan Kindle Display",
        "books_upload_box": " 📤 Wireless Book Upload & Auto-Conversion ",
        "books_pick_btn": "➕ Choose Books to Send to Kindle...",
        "books_target_fmt": "Target format:",
        "books_skip_native": "Skip conversion for native formats (MOBI, AZW3, PDF)",
        "books_calibre_ok": "✅ Calibre ebook-convert ready",
        "books_calibre_missing": "⚠️ Calibre not found (native MOBI/PDF transfer only)",
        "books_waiting": "Select books on PC to send wirelessly to Kindle...",
        "books_count": "Books on Kindle: {count} (Total: {size})",
        "books_delete_confirm": "Delete book '{name}' from Kindle?",
        "books_delete_ok": "Book '{name}' successfully deleted from Kindle.",
        "books_wake_hint": "Wake your Kindle (slide power switch) to enable Wi-Fi.",
        "books_sent_success": "✓ All books successfully uploaded to Kindle ({count} pcs)!",
        "books_offline": "🔴 Offline (wake Kindle screen)",
        "books_online": "🟢 Online (Wi-Fi)",
        "books_usb_online": "🔌 Connected (USB {drive})",
        "books_loading": "● Loading book list...",
    }
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"ip": DEFAULT_IP, "city": DEFAULT_CITY, "rotation": 0}

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_font(size, bold=False, mono=False):
    win_fonts = "C:/Windows/Fonts"
    if mono:
        candidates = [os.path.join(win_fonts, "consola.ttf"), os.path.join(win_fonts, "cour.ttf")]
    elif bold:
        candidates = [os.path.join(win_fonts, "segoeuib.ttf"), os.path.join(win_fonts, "arialbd.ttf")]
    else:
        candidates = [os.path.join(win_fonts, "segoeui.ttf"), os.path.join(win_fonts, "arial.ttf")]
    
    local_font = os.path.join(os.path.dirname(os.path.abspath(__file__)), "futura.ttf")
    if os.path.exists(local_font) and not mono:
        candidates.append(local_font)

    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_progress_bar(draw, x, y, w, h, percent, fill_color=(0, 0, 0), bg_color=(230, 230, 230), border_color=(0, 0, 0)):
    draw.rectangle([x, y, x + w, y + h], fill=bg_color, outline=border_color, width=2)
    fill_w = int((w - 4) * max(0.0, min(1.0, percent / 100.0)))
    if fill_w > 0:
        draw.rectangle([x + 2, y + 2, x + 2 + fill_w, y + h - 2], fill=fill_color)

def get_ssh_target(target):
    if not target:
        target = DEFAULT_IP
    if "@" not in target:
        return f"root@{target}"
    return target

def send_image_to_kindle(img_pil, server=DEFAULT_IP, negative=False, rotation=0, dither=False):
    ssh_target = get_ssh_target(server)
    tmp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_interactive.png")
    
    # Apply rotation
    if rotation % 360 != 0:
        img_pil = img_pil.rotate(-rotation, expand=True)

    # Ensure final dimensions match Kindle framebuffer (600x800)
    if img_pil.size != (X_RES, Y_RES):
        # Fit into 600x800 with white background
        target_ratio = X_RES / Y_RES
        img_ratio = img_pil.width / img_pil.height
        if img_ratio > target_ratio:
            nw = X_RES
            nh = int(X_RES / img_ratio)
        else:
            nh = Y_RES
            nw = int(Y_RES * img_ratio)
        resized = img_pil.resize((nw, nh), Image.Resampling.LANCZOS)
        bg = Image.new("RGB", (X_RES, Y_RES), (255, 255, 255))
        offset = ((X_RES - nw) // 2, (Y_RES - nh) // 2)
        bg.paste(resized, offset)
        img_pil = bg

    if dither:
        # 1-bit Floyd-Steinberg dithering for crisp photo output
        img_proc = img_pil.convert('1')
        if negative:
            img_proc = ImageOps.invert(img_proc)
    else:
        # Standard 8-bit grayscale
        img_proc = img_pil.convert('L')
        if negative:
            img_proc = ImageOps.invert(img_proc)

    img_proc.save(tmp_path, format="PNG")

    scp_cmd = f"scp {SSH_OPTS} \"{tmp_path}\" {ssh_target}:/tmp/display.png"
    res1 = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)
    if res1.returncode != 0:
        raise RuntimeError(f"SCP error: {res1.stderr.strip() or 'Connection failed'}")

    ssh_cmd = f"ssh {SSH_OPTS} {ssh_target} \"/usr/sbin/eips -g /tmp/display.png\""
    res2 = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
    if res2.returncode != 0:
        raise RuntimeError(f"SSH error: {res2.stderr.strip() or 'Display failed'}")

    try:
        os.remove(tmp_path)
    except OSError:
        pass

def clear_kindle(server=DEFAULT_IP):
    ssh_target = get_ssh_target(server)
    res = subprocess.run(f"ssh {SSH_OPTS} {ssh_target} \"/usr/sbin/eips -c\"", shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or "Clear failed")

def check_kindle_ping(server=DEFAULT_IP):
    ssh_target = get_ssh_target(server)
    t0 = time.time()
    res = subprocess.run(f"ssh {SSH_OPTS} {ssh_target} \"echo PING_OK\"", shell=True, capture_output=True, text=True)
    latency_ms = int((time.time() - t0) * 1000)
    return (res.returncode == 0 and "PING_OK" in res.stdout), latency_ms

def fetch_weather(city=DEFAULT_CITY):
    try:
        url = f"http://wttr.in/{city}?format=j1"
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            cur = data['current_condition'][0]
            temp = cur['temp_C']
            desc = cur['lang_ru'][0]['value'] if 'lang_ru' in cur else cur['weatherDesc'][0]['value']
            humidity = cur['humidity']
            wind = cur['windspeedKmph']
            return {
                "temp": f"{int(temp):+d}°C",
                "desc": desc.strip().capitalize(),
                "humidity": f"{humidity}%",
                "wind": f"{wind} км/ч",
                "city": city
            }
    except Exception:
        return {
            "temp": "--°C",
            "desc": "Нет связи с метеосервером",
            "humidity": "--",
            "wind": "--",
            "city": city
        }


# ==============================================================================
# DASHBOARD GENERATOR
# ==============================================================================
def generate_pc_dashboard(w=X_RES, h=Y_RES, landscape=False):
    width, height = (h, w) if landscape else (w, h)
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(22, bold=True)
    f_sub = get_font(12, bold=False)
    f_sec = get_font(15, bold=True)
    f_val = get_font(19, bold=True)
    f_body = get_font(12, bold=False)
    f_mono = get_font(11, mono=True)

    now_str = datetime.datetime.now().strftime("%H:%M:%S | %d.%m.%Y")
    draw.rectangle([0, 0, width, 50], fill=(0, 0, 0))
    draw.text((15, 12), "💻 PC HARDWARE MONITOR", fill=(255, 255, 255), font=f_title)
    draw.text((width - 165, 18), now_str, fill=(255, 255, 255), font=f_sub)

    cpu_pct = psutil.cpu_percent(interval=None) if psutil else 0
    cpu_freq = psutil.cpu_freq() if psutil else None
    freq_str = f"{cpu_freq.current/1000:.1f} GHz" if cpu_freq else ""
    cores = psutil.cpu_count(logical=True) if psutil else 1
    
    mem = psutil.virtual_memory() if psutil else None
    mem_used = mem.used / (1024**3) if mem else 0
    mem_total = mem.total / (1024**3) if mem else 0
    mem_pct = mem.percent if mem else 0

    disk = psutil.disk_usage('C:') if psutil else None
    disk_free = disk.free / (1024**3) if disk else 0
    disk_total = disk.total / (1024**3) if disk else 0
    disk_pct = disk.percent if disk else 0

    uptime_sec = (time.time() - psutil.boot_time()) if psutil else 0
    up_h = int(uptime_sec // 3600)
    up_m = int((uptime_sec % 3600) // 60)

    if not landscape:
        # Portrait (600x800)
        y = 65
        draw.text((20, y), "ЦЕНТРАЛЬНЫЙ ПРОЦЕССОР (CPU)", fill=(0, 0, 0), font=f_sec)
        draw.text((width - 85, y), f"{cpu_pct:4.1f}%", fill=(0, 0, 0), font=f_val)
        draw_progress_bar(draw, 20, y + 26, width - 40, 16, cpu_pct)
        draw.text((20, y + 46), f"Ядер / потоков: {cores}   Частота: {freq_str}   Uptime: {up_h}ч {up_m}м", fill=(70, 70, 70), font=f_body)

        y = 145
        draw.text((20, y), "ОПЕРАТИВНАЯ ПАМЯТЬ (RAM)", fill=(0, 0, 0), font=f_sec)
        draw.text((width - 85, y), f"{mem_pct:4.1f}%", fill=(0, 0, 0), font=f_val)
        draw_progress_bar(draw, 20, y + 26, width - 40, 16, mem_pct)
        draw.text((20, y + 46), f"Занято: {mem_used:.1f} ГБ из {mem_total:.1f} ГБ   (Свободно: {mem.available/(1024**3):.1f} ГБ)", fill=(70, 70, 70), font=f_body)

        y = 225
        draw.text((20, y), "СИСТЕМНЫЙ ДИСК (C:)", fill=(0, 0, 0), font=f_sec)
        draw.text((width - 85, y), f"{disk_pct:4.1f}%", fill=(0, 0, 0), font=f_val)
        draw_progress_bar(draw, 20, y + 26, width - 40, 16, disk_pct)
        draw.text((20, y + 46), f"Свободно: {disk_free:.1f} ГБ   (Всего: {disk_total:.1f} ГБ)", fill=(70, 70, 70), font=f_body)

        draw.line([20, 310, width - 20, 310], fill=(200, 200, 200), width=2)

        # Top processes
        y = 325
        draw.text((20, y), "ТОП ПРОЦЕССОВ ПО НАГРУЗКЕ", fill=(0, 0, 0), font=f_sec)
        procs = []
        if psutil:
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                try:
                    info = p.info
                    if info['name'] and info['name'] not in ('System Idle Process', 'System'):
                        procs.append(info)
                except Exception:
                    pass
            procs.sort(key=lambda x: (x.get('cpu_percent') or 0), reverse=True)

        ty = y + 28
        draw.rectangle([20, ty, width - 20, ty + 22], fill=(240, 240, 240))
        draw.text((25, ty + 3), "ПРОЦЕСС", fill=(50, 50, 50), font=f_sub)
        draw.text((360, ty + 3), "CPU %", fill=(50, 50, 50), font=f_sub)
        draw.text((470, ty + 3), "RAM %", fill=(50, 50, 50), font=f_sub)

        ty += 25
        for p in procs[:11]:
            name = (p['name'][:32] + '..') if len(p['name']) > 34 else p['name']
            c_val = f"{p['cpu_percent']:5.1f}%" if p['cpu_percent'] is not None else " 0.0%"
            m_val = f"{p['memory_percent']:5.1f}%" if p['memory_percent'] is not None else " 0.0%"
            draw.text((25, ty), name, fill=(0, 0, 0), font=f_mono)
            draw.text((365, ty), c_val, fill=(0, 0, 0), font=f_mono)
            draw.text((475, ty), m_val, fill=(0, 0, 0), font=f_mono)
            ty += 22
            draw.line([20, ty - 2, width - 20, ty - 2], fill=(245, 245, 245), width=1)

        draw.rectangle([0, height - 30, width, height], fill=(240, 240, 240))
        draw.text((20, height - 22), "Kindle Studio • Live PC Hardware Monitor", fill=(100, 100, 100), font=f_sub)
    else:
        # Landscape (800x600)
        col_w = (width - 60) // 2
        y = 65
        draw.text((20, y), "CPU НАГРУЗКА", fill=(0, 0, 0), font=f_sec)
        draw.text((col_w - 45, y), f"{cpu_pct:.1f}%", fill=(0, 0, 0), font=f_val)
        draw_progress_bar(draw, 20, y + 26, col_w, 16, cpu_pct)
        draw.text((20, y + 46), f"Ядер: {cores}   Частота: {freq_str}", fill=(70, 70, 70), font=f_body)

        y = 145
        draw.text((20, y), "RAM ПАМЯТЬ", fill=(0, 0, 0), font=f_sec)
        draw.text((col_w - 45, y), f"{mem_pct:.1f}%", fill=(0, 0, 0), font=f_val)
        draw_progress_bar(draw, 20, y + 26, col_w, 16, mem_pct)
        draw.text((20, y + 46), f"{mem_used:.1f} ГБ / {mem_total:.1f} ГБ", fill=(70, 70, 70), font=f_body)

        y = 225
        draw.text((20, y), "ДИСК (C:)", fill=(0, 0, 0), font=f_sec)
        draw.text((col_w - 45, y), f"{disk_pct:.1f}%", fill=(0, 0, 0), font=f_val)
        draw_progress_bar(draw, 20, y + 26, col_w, 16, disk_pct)
        draw.text((20, y + 46), f"Свободно: {disk_free:.1f} ГБ", fill=(70, 70, 70), font=f_body)

        y = 310
        draw.rectangle([20, y, 20 + col_w, y + 48], fill=(248, 248, 248), outline=(210, 210, 210))
        draw.text((30, y + 14), f"Время работы ПК: {up_h} ч {up_m} мин", fill=(0, 0, 0), font=f_sec)

        # Right col
        rx = col_w + 40
        rw = width - rx - 20
        y = 65
        draw.text((rx, y), "ТОП ПРОЦЕССОВ", fill=(0, 0, 0), font=f_sec)
        
        procs = []
        if psutil:
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                try:
                    info = p.info
                    if info['name'] and info['name'] not in ('System Idle Process', 'System'):
                        procs.append(info)
                except Exception:
                    pass
            procs.sort(key=lambda x: (x.get('cpu_percent') or 0), reverse=True)

        ty = y + 26
        draw.rectangle([rx, ty, rx + rw, ty + 22], fill=(240, 240, 240))
        draw.text((rx + 5, ty + 3), "ПРОЦЕСС", fill=(50, 50, 50), font=f_sub)
        draw.text((rx + rw - 130, ty + 3), "CPU%", fill=(50, 50, 50), font=f_sub)
        draw.text((rx + rw - 60, ty + 3), "RAM%", fill=(50, 50, 50), font=f_sub)

        ty += 26
        for p in procs[:13]:
            name = (p['name'][:22] + '..') if len(p['name']) > 24 else p['name']
            c_val = f"{p['cpu_percent']:4.1f}%" if p['cpu_percent'] is not None else "0.0%"
            m_val = f"{p['memory_percent']:4.1f}%" if p['memory_percent'] is not None else "0.0%"
            draw.text((rx + 5, ty), name, fill=(0, 0, 0), font=f_mono)
            draw.text((rx + rw - 125, ty), c_val, fill=(0, 0, 0), font=f_mono)
            draw.text((rx + rw - 55, ty), m_val, fill=(0, 0, 0), font=f_mono)
            ty += 22

        draw.rectangle([0, height - 28, width, height], fill=(240, 240, 240))
        draw.text((20, height - 20), "Kindle Studio • Live PC Hardware Monitor (Landscape)", fill=(100, 100, 100), font=f_sub)

    return img


# ==============================================================================
# CLOCK & CALENDAR GENERATOR
# ==============================================================================
def generate_desk_clock(w=X_RES, h=Y_RES, landscape=False, weather_data=None, custom_note=""):
    width, height = (h, w) if landscape else (w, h)
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_clock = get_font(92, bold=True)
    f_day = get_font(22, bold=True)
    f_date = get_font(18, bold=False)
    f_cal_head = get_font(15, bold=True)
    f_cal_num = get_font(16, bold=False)
    f_cal_today = get_font(16, bold=True)
    f_weather_temp = get_font(36, bold=True)
    f_weather_desc = get_font(16, bold=False)
    f_sub = get_font(13, bold=False)

    now = datetime.datetime.now()
    weekday_str = WEEKDAYS_RU[now.weekday()]
    date_str = f"{now.day} {MONTH_GEN_RU[now.month]} {now.year}"
    time_str = now.strftime("%H:%M")

    if not landscape:
        # Portrait (600x800)
        draw.rectangle([0, 0, width, 55], fill=(0, 0, 0))
        draw.text((width // 2, 28), weekday_str, fill=(255, 255, 255), font=f_day, anchor="mm")

        draw.text((width // 2, 135), time_str, fill=(0, 0, 0), font=f_clock, anchor="mm")
        draw.text((width // 2, 205), date_str, fill=(80, 80, 80), font=f_date, anchor="mm")

        draw.line([30, 235, width - 30, 235], fill=(210, 210, 210), width=2)

        # Weather Box
        w_y = 250
        draw.rectangle([30, w_y, width - 30, w_y + 105], fill=(248, 248, 248), outline=(200, 200, 200), width=2)
        if not weather_data:
            weather_data = {"temp": "--°C", "desc": "Ожидание прогноза...", "humidity": "--", "wind": "--", "city": "Кирово-Чепецк"}
        
        draw.text((50, w_y + 15), weather_data["temp"], fill=(0, 0, 0), font=f_weather_temp)
        draw.text((180, w_y + 18), weather_data["desc"], fill=(0, 0, 0), font=f_weather_desc)
        draw.text((180, w_y + 45), f"Влажность: {weather_data['humidity']}   Ветер: {weather_data['wind']}", fill=(90, 90, 90), font=f_sub)
        draw.text((180, w_y + 68), f"📍 {weather_data['city']}", fill=(110, 110, 110), font=f_sub)

        # Calendar Box
        cal_y = 375
        cal_w = width - 60
        draw.rectangle([30, cal_y, width - 30, cal_y + 280], fill=(255, 255, 255), outline=(200, 200, 200), width=2)
        
        month_header = f"{MONTH_NAMES_RU[now.month].upper()} {now.year}"
        draw.rectangle([30, cal_y, width - 30, cal_y + 40], fill=(240, 240, 240))
        draw.text((width // 2, cal_y + 20), month_header, fill=(0, 0, 0), font=f_cal_head, anchor="mm")

        headers = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        cell_w = cal_w / 7.0
        grid_top = cal_y + 50
        for i, h_text in enumerate(headers):
            cx = 30 + i * cell_w + cell_w / 2
            is_weekend = (i >= 5)
            color = (130, 130, 130) if is_weekend else (0, 0, 0)
            draw.text((cx, grid_top + 10), h_text, fill=color, font=f_cal_head, anchor="mm")

        cal = calendar.monthcalendar(now.year, now.month)
        for row, week in enumerate(cal):
            ry = grid_top + 40 + row * 34
            for col, day in enumerate(week):
                if day == 0:
                    continue
                cx = 30 + col * cell_w + cell_w / 2
                if day == now.day:
                    box_w = 30
                    box_h = 28
                    draw.rectangle([cx - box_w/2, ry - box_h/2, cx + box_w/2, ry + box_h/2], fill=(0, 0, 0))
                    draw.text((cx, ry), str(day), fill=(255, 255, 255), font=f_cal_today, anchor="mm")
                else:
                    color = (130, 130, 130) if col >= 5 else (0, 0, 0)
                    draw.text((cx, ry), str(day), fill=color, font=f_cal_num, anchor="mm")

        if custom_note:
            draw.rectangle([30, height - 90, width - 30, height - 35], fill=(245, 245, 245), outline=(210, 210, 210))
            draw.text((width // 2, height - 62), custom_note, fill=(50, 50, 50), font=f_date, anchor="mm")
        else:
            draw.text((width // 2, height - 35), "Kindle Desk Clock • E-Ink Smart Display", fill=(130, 130, 130), font=f_sub, anchor="mm")
    else:
        # Landscape (800x600)
        left_w = 380
        draw.rectangle([0, 0, left_w, 50], fill=(0, 0, 0))
        draw.text((left_w // 2, 25), weekday_str, fill=(255, 255, 255), font=f_day, anchor="mm")

        draw.text((left_w // 2, 140), time_str, fill=(0, 0, 0), font=f_clock, anchor="mm")
        draw.text((left_w // 2, 210), date_str, fill=(70, 70, 70), font=f_date, anchor="mm")

        w_y = 260
        draw.rectangle([25, w_y, left_w - 15, w_y + 140], fill=(248, 248, 248), outline=(200, 200, 200), width=2)
        if not weather_data:
            weather_data = {"temp": "--°C", "desc": "Ожидание прогноза...", "humidity": "--", "wind": "--", "city": "Кирово-Чепецк"}
        draw.text((45, w_y + 15), weather_data["temp"], fill=(0, 0, 0), font=f_weather_temp)
        draw.text((45, w_y + 65), weather_data["desc"], fill=(0, 0, 0), font=f_weather_desc)
        draw.text((45, w_y + 92), f"Влажность: {weather_data['humidity']}  •  Ветер: {weather_data['wind']}", fill=(90, 90, 90), font=f_sub)
        draw.text((45, w_y + 115), f"📍 {weather_data['city']}", fill=(110, 110, 110), font=f_sub)

        # Right half: Calendar
        rx = left_w + 15
        rw = width - rx - 20
        cal_y = 20
        draw.rectangle([rx, cal_y, rx + rw, height - 25], fill=(255, 255, 255), outline=(200, 200, 200), width=2)
        
        month_header = f"{MONTH_NAMES_RU[now.month].upper()} {now.year}"
        draw.rectangle([rx, cal_y, rx + rw, cal_y + 45], fill=(240, 240, 240))
        draw.text((rx + rw // 2, cal_y + 22), month_header, fill=(0, 0, 0), font=f_cal_head, anchor="mm")

        headers = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        cell_w = rw / 7.0
        grid_top = cal_y + 55
        for i, h_text in enumerate(headers):
            cx = rx + i * cell_w + cell_w / 2
            is_weekend = (i >= 5)
            color = (130, 130, 130) if is_weekend else (0, 0, 0)
            draw.text((cx, grid_top + 15), h_text, fill=color, font=f_cal_head, anchor="mm")

        cal = calendar.monthcalendar(now.year, now.month)
        for row, week in enumerate(cal):
            ry = grid_top + 55 + row * 45
            for col, day in enumerate(week):
                if day == 0:
                    continue
                cx = rx + col * cell_w + cell_w / 2
                if day == now.day:
                    box_w = 36
                    box_h = 32
                    draw.rectangle([cx - box_w/2, ry - box_h/2, cx + box_w/2, ry + box_h/2], fill=(0, 0, 0))
                    draw.text((cx, ry), str(day), fill=(255, 255, 255), font=f_cal_today, anchor="mm")
                else:
                    color = (130, 130, 130) if col >= 5 else (0, 0, 0)
                    draw.text((cx, ry), str(day), fill=color, font=f_cal_num, anchor="mm")

    return img


# ==============================================================================
# TO-DO / STICKY NOTE GENERATOR
# ==============================================================================
def generate_todo_note(title="СПИСОК ДЕЛ", text_items="", w=X_RES, h=Y_RES, landscape=False):
    width, height = (h, w) if landscape else (w, h)
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    f_title = get_font(24, bold=True)
    f_date = get_font(13, bold=False)
    f_item = get_font(18, bold=False)
    f_mono = get_font(16, mono=True)

    # Notepad Header
    draw.rectangle([0, 0, width, 55], fill=(0, 0, 0))
    draw.text((25, 14), f"📝 {title.upper()}", fill=(255, 255, 255), font=f_title)
    now_str = datetime.datetime.now().strftime("%d.%m.%Y")
    draw.text((width - 120, 20), now_str, fill=(255, 255, 255), font=f_date)

    # Lined paper effect
    start_y = 80
    lines = text_items.strip().split("\n")
    cur_y = start_y

    for line in lines:
        line = line.strip()
        if not line:
            cur_y += 20
            continue
        
        # Checkbox check
        if line.startswith("[x]") or line.startswith("[X]"):
            box_text = "☒"
            content = line[3:].strip()
            draw.text((30, cur_y - 2), box_text, fill=(70, 70, 70), font=f_item)
            draw.text((70, cur_y), content, fill=(100, 100, 100), font=f_item)
            # Strike-through
            w_text = int(len(content) * 11)
            draw.line([70, cur_y + 12, 70 + w_text, cur_y + 12], fill=(120, 120, 120), width=2)
        elif line.startswith("[ ]"):
            box_text = "☐"
            content = line[3:].strip()
            draw.text((30, cur_y - 2), box_text, fill=(0, 0, 0), font=f_item)
            draw.text((70, cur_y), content, fill=(0, 0, 0), font=f_item)
        else:
            draw.text((30, cur_y - 2), "•", fill=(0, 0, 0), font=f_item)
            draw.text((60, cur_y), line, fill=(0, 0, 0), font=f_item)

        cur_y += 38
        draw.line([25, cur_y - 4, width - 25, cur_y - 4], fill=(230, 230, 230), width=1)
        if cur_y > height - 40:
            break

    draw.rectangle([0, height - 30, width, height], fill=(240, 240, 240))
    draw.text((width // 2, height - 15), "Kindle E-Ink Smart Desk Sticky Note", fill=(120, 120, 120), font=f_date, anchor="mm")
    return img


# ==============================================================================
# MAIN GUI APPLICATION
# ==============================================================================
class KindleStudioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.lang = self.cfg.get("lang", "ru")
        self.title(self.tr("title"))
        self.geometry("1160x780")
        self.minsize(1040, 700)
        self.configure(bg="#1e1e1e")

        self.rotation = self.cfg.get("rotation", 0) # 0, 90, 180, 270

        # In-memory canvas image
        self.image = Image.new("RGB", (X_RES, Y_RES), (255, 255, 255))
        self.draw = ImageDraw.Draw(self.image)

        # Drawing state
        self.brush_size = 5
        self.brush_color = "black"
        self.tool_mode = "pen"
        self.last_x = None
        self.last_y = None

        # Auto-update / Streaming state
        self.active_mode = None # 'stream', 'dashboard', 'clock'
        self.worker_thread = None
        self.worker_stop_event = None

        # Weather cache
        self.weather_cache = None
        self.weather_last_fetch = 0

        # Slideshow state
        self.slideshow_files = []
        self.slideshow_idx = 0

        # Book server & library sync state
        self.book_server = None
        self.cached_books = []
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self._build_ui()
        self._update_preview()
        self._check_ping_async()

    def _build_ui(self):
        # 1. Top Control Bar
        top_bar = tk.Frame(self, bg="#252526", pady=8, padx=12)
        top_bar.pack(side="top", fill="x")

        self.lbl_ip = tk.Label(top_bar, text=self.tr("ip_label"), fg="#ffffff", bg="#252526", font=("Segoe UI", 9, "bold"))
        self.lbl_ip.pack(side="left")
        self.ip_entry = tk.Entry(top_bar, width=15, font=("Consolas", 10), bg="#333337", fg="#ffffff", insertbackground="white")
        self.ip_entry.insert(0, self.cfg.get("ip", DEFAULT_IP))
        self.ip_entry.pack(side="left", padx=(5, 10))

        self.btn_ping = tk.Button(top_bar, text=self.tr("btn_ping"), bg="#3a3d41", fg="white", relief="flat", padx=6, command=self.action_ping_kindle)
        self.btn_ping.pack(side="left", padx=3)

        self.ping_status_lbl = tk.Label(top_bar, text="● ...", fg="#aaaaaa", bg="#252526", font=("Segoe UI", 8))
        self.ping_status_lbl.pack(side="left", padx=(4, 12))

        self.btn_send = tk.Button(top_bar, text=self.tr("btn_send"), bg="#0e639c", fg="white", font=("Segoe UI", 9, "bold"),
                                  padx=12, pady=3, relief="flat", command=self.action_send_now)
        self.btn_send.pack(side="left", padx=4)

        self.btn_clear_screen = tk.Button(top_bar, text=self.tr("btn_clear"), bg="#3a3d41", fg="white", relief="flat",
                                          padx=8, command=self.action_clear_kindle)
        self.btn_clear_screen.pack(side="left", padx=4)

        self.btn_shortcut = tk.Button(top_bar, text=self.tr("btn_shortcut"), bg="#3a3d41", fg="#cccccc", relief="flat",
                                      font=("Segoe UI", 8), command=self.action_create_desktop_shortcut)
        self.btn_shortcut.pack(side="left", padx=4)

        self.btn_lang = tk.Button(top_bar, text=self.tr("btn_lang"), bg="#0e639c", fg="#ffffff", relief="flat",
                                  font=("Segoe UI", 8, "bold"), padx=8, command=self.action_toggle_language)
        self.btn_lang.pack(side="left", padx=6)

        self.status_lbl = tk.Label(top_bar, text=self.tr("ready"), fg="#89d185", bg="#252526", font=("Segoe UI", 9))
        self.status_lbl.pack(side="right")

        # 2. Main Content (Left: Tabs with controls, Right: Interactive Screen Preview)
        main_frame = tk.Frame(self, bg="#1e1e1e")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Style notebook & widgets
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TNotebook", background="#1e1e1e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#2d2d30", foreground="#cccccc", padding=[10, 5], font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#0e639c")], foreground=[("selected", "#ffffff")])

        # Authentic E-Ink High Contrast Treeview
        style.configure("Treeview", background="#ffffff", foreground="#000000", fieldbackground="#ffffff", rowheight=34, font=("Segoe UI", 11))
        style.configure("Treeview.Heading", background="#222222", foreground="#ffffff", font=("Segoe UI", 11, "bold"), padding=[4, 6])
        style.map("Treeview", background=[("selected", "#005a9e")], foreground=[("selected", "#ffffff")])

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Build Tabs
        self._build_tab_canvas()
        self._build_tab_stream()
        self._build_tab_dashboard()
        self._build_tab_clock()
        self._build_tab_todo()
        self._build_tab_books()
        self._build_tab_jailbreak()

        # 3. Right: Screen Preview Panel
        preview_frame = tk.Frame(main_frame, bg="#252526", padx=12, pady=12)
        preview_frame.pack(side="right", fill="y")

        # Orientation / Rotation Controls Header
        rot_frame = tk.Frame(preview_frame, bg="#252526")
        rot_frame.pack(fill="x", pady=(0, 8))

        tk.Label(rot_frame, text="Ориентация экрана:", fg="#ffffff", bg="#252526", font=("Segoe UI", 9, "bold")).pack(side="left")
        
        self.rot_btn_left = tk.Button(rot_frame, text="⟲ 90° Влево", bg="#3a3d41", fg="white", relief="flat", font=("Segoe UI", 8), command=lambda: self.action_rotate(-90))
        self.rot_btn_left.pack(side="right", padx=2)
        self.rot_btn_right = tk.Button(rot_frame, text="⟳ 90° Вправо", bg="#3a3d41", fg="white", relief="flat", font=("Segoe UI", 8), command=lambda: self.action_rotate(90))
        self.rot_btn_right.pack(side="right", padx=2)

        # Rotation radio buttons
        rot_row = tk.Frame(preview_frame, bg="#252526")
        rot_row.pack(fill="x", pady=(0, 10))
        self.rot_var = tk.IntVar(value=self.rotation)
        for ang, label in [(0, "0° Портрет"), (90, "90° Альбом ⟳"), (180, "180°"), (270, "270° Альбом ⟲")]:
            rb = tk.Radiobutton(rot_row, text=label, variable=self.rot_var, value=ang, fg="white", bg="#252526",
                                selectcolor="#0e639c", activebackground="#252526", font=("Segoe UI", 8),
                                command=self._on_rotation_radio_change)
            rb.pack(side="left", padx=2)

        # Canvas widget
        self.canvas_preview = tk.Canvas(preview_frame, width=300, height=400, bg="white", cursor="cross",
                                        highlightthickness=2, highlightbackground="#555555")
        self.canvas_preview.pack(pady=5)
        self.canvas_preview.bind("<Button-1>", self._canvas_click)
        self.canvas_preview.bind("<B1-Motion>", self._canvas_drag)
        self.canvas_preview.bind("<ButtonRelease-1>", self._canvas_release)

        # Resolution indicator
        self.res_lbl = tk.Label(preview_frame, text="Размер: 600×800 • Портрет", fg="#888888", bg="#252526", font=("Segoe UI", 8))
        self.res_lbl.pack(pady=(4, 0))

        # Bottom Quick Actions under preview
        quick_acts = tk.Frame(preview_frame, bg="#252526")
        quick_acts.pack(fill="x", pady=(8, 0))
        tk.Button(quick_acts, text="🌓 Инвертировать", bg="#3a3d41", fg="white", relief="flat", font=("Segoe UI", 8), command=self.action_invert_canvas).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(quick_acts, text="🗑 Очистить холст", bg="#3a3d41", fg="white", relief="flat", font=("Segoe UI", 8), command=self.action_clear_canvas).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(quick_acts, text="💾 Сохранить PNG", bg="#3a3d41", fg="white", relief="flat", font=("Segoe UI", 8), command=self.action_save_image).pack(side="left", expand=True, fill="x", padx=2)

    # -------------------------------------------------------------------------
    # TAB: CANVAS & DRAWING
    # -------------------------------------------------------------------------
    def _build_tab_canvas(self):
        tab = tk.Frame(self.notebook, bg="#252526", padx=12, pady=12)
        self.notebook.add(tab, text="🎨 Холст и Фото")

        tk.Label(tab, text="Инструменты рисования:", fg="#ffffff", bg="#252526", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
        
        self.mode_var = tk.StringVar(value="pen")
        rb_pen = tk.Radiobutton(tab, text="✏ Ручка / Кисть", variable=self.mode_var, value="pen", fg="white", bg="#252526", selectcolor="#333337", activebackground="#252526", command=self._set_mode)
        rb_pen.pack(anchor="w")
        rb_erase = tk.Radiobutton(tab, text="🧽 Ластик", variable=self.mode_var, value="eraser", fg="white", bg="#252526", selectcolor="#333337", activebackground="#252526", command=self._set_mode)
        rb_erase.pack(anchor="w")
        rb_text = tk.Radiobutton(tab, text="🔤 Текст (кликните по холсту для вставки)", variable=self.mode_var, value="text", fg="white", bg="#252526", selectcolor="#333337", activebackground="#252526", command=self._set_mode)
        rb_text.pack(anchor="w")

        tk.Label(tab, text="Текст для вставки:", fg="#aaaaaa", bg="#252526", font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 2))
        self.text_input = tk.Entry(tab, bg="#333337", fg="white", insertbackground="white")
        self.text_input.insert(0, "Заметка...")
        self.text_input.pack(fill="x", pady=(0, 8))

        tk.Label(tab, text="Толщина кисти / размер текста:", fg="#cccccc", bg="#252526", font=("Segoe UI", 8)).pack(anchor="w")
        self.slider_size = tk.Scale(tab, from_=1, to=40, orient="horizontal", bg="#252526", fg="white", highlightthickness=0, command=self._on_size_change)
        self.slider_size.set(5)
        self.slider_size.pack(fill="x", pady=(0, 10))

        # Image operations
        tk.Label(tab, text="Загрузка картинок:", fg="#ffffff", bg="#252526", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 4))
        btn_load = tk.Button(tab, text="📂 Загрузить картинку с компьютера...", bg="#4e5157", fg="white", relief="flat", command=self.action_load_image)
        btn_load.pack(fill="x", pady=2)

        # Dithering mode option
        self.dither_var = tk.BooleanVar(value=False)
        cb_dither = tk.Checkbutton(tab, text="Фото-дизеринг (Floyd-Steinberg для фото)", variable=self.dither_var, fg="white", bg="#252526", selectcolor="#333337", activebackground="#252526")
        cb_dither.pack(anchor="w", pady=4)

        # Slideshow frame
        slide_frame = tk.LabelFrame(tab, text=" Слайдшоу из папки ", fg="#ffffff", bg="#252526", padx=8, pady=8)
        slide_frame.pack(fill="x", pady=(10, 0))
        tk.Button(slide_frame, text="Выбрать папку с фото...", bg="#3a3d41", fg="white", relief="flat", command=self.action_choose_slideshow_dir).pack(fill="x", pady=2)
        self.slide_info_lbl = tk.Label(slide_frame, text="Папка не выбрана", fg="#888888", bg="#252526", font=("Segoe UI", 8))
        self.slide_info_lbl.pack(pady=2)

        s_ctrl = tk.Frame(slide_frame, bg="#252526")
        s_ctrl.pack(fill="x", pady=2)
        tk.Button(s_ctrl, text="◀ Назад", bg="#3a3d41", fg="white", relief="flat", width=12, command=self.action_slide_prev).pack(side="left", padx=2)
        tk.Button(s_ctrl, text="Вперед ▶", bg="#3a3d41", fg="white", relief="flat", width=12, command=self.action_slide_next).pack(side="right", padx=2)

    # -------------------------------------------------------------------------
    # TAB: SCREEN STREAMING
    # -------------------------------------------------------------------------
    def _build_tab_stream(self):
        tab = tk.Frame(self.notebook, bg="#252526", padx=12, pady=12)
        self.notebook.add(tab, text="🖥️ Стриминг ПК")

        tk.Label(tab, text="Прямая трансляция экрана компьютера:", fg="#ffffff", bg="#252526", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))

        tk.Label(tab, text="💡 Совет: Для широкоформатных экранов ПК выберите ориентацию '90° Альбом' — тогда рабочий стол поместится на весь экран Киндла без черных полос!", fg="#89d185", bg="#252526", wraplength=440, justify="left", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 10))

        btn_cap_full = tk.Button(tab, text="📸 Снимок всего экрана ПК", bg="#3a3d41", fg="white", relief="flat", command=self.action_capture_full_screen)
        btn_cap_full.pack(fill="x", pady=3)

        btn_cap_area = tk.Button(tab, text="✂ Захват выделенной области экрана", bg="#3a3d41", fg="white", relief="flat", command=self.action_select_area_capture)
        btn_cap_area.pack(fill="x", pady=3)

        tk.Label(tab, text="Настройки стриминга:", fg="#ffffff", bg="#252526", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15, 4))
        
        fps_row = tk.Frame(tab, bg="#252526")
        fps_row.pack(fill="x", pady=4)
        tk.Label(fps_row, text="Частота обновления (FPS):", fg="#cccccc", bg="#252526").pack(side="left")
        self.stream_fps = tk.Spinbox(fps_row, from_=0.2, to=3.0, increment=0.2, width=6, bg="#333337", fg="white")
        self.stream_fps.delete(0, "end")
        self.stream_fps.insert(0, "1.0")
        self.stream_fps.pack(side="left", padx=10)

        self.btn_stream_toggle = tk.Button(tab, text="▶ Запустить прямую трансляцию", bg="#28a745", fg="white",
                                           font=("Segoe UI", 10, "bold"), relief="flat", pady=6, command=self.action_toggle_stream)
        self.btn_stream_toggle.pack(fill="x", pady=(15, 5))

    # -------------------------------------------------------------------------
    # TAB: PC HARDWARE DASHBOARD
    # -------------------------------------------------------------------------
    def _build_tab_dashboard(self):
        tab = tk.Frame(self.notebook, bg="#252526", padx=12, pady=12)
        self.notebook.add(tab, text="📊 Дашборд ПК")

        tk.Label(tab, text="Монитор ресурсов компьютера в реальном времени:", fg="#ffffff", bg="#252526", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))

        tk.Label(tab, text="Отображает загрузку процессора, тактовую частоту, память RAM, остаток диска C: и список самых прожорливых процессов Windows.", fg="#aaaaaa", bg="#252526", wraplength=440, justify="left", font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 10))

        btn_render_dash = tk.Button(tab, text="👁 Сформировать дашборд", bg="#0e639c", fg="white", relief="flat", font=("Segoe UI", 9, "bold"), command=self.action_render_dashboard)
        btn_render_dash.pack(fill="x", pady=4)

        tk.Label(tab, text="Автоматическое обновление на Kindle:", fg="#ffffff", bg="#252526", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15, 4))
        
        interval_row = tk.Frame(tab, bg="#252526")
        interval_row.pack(fill="x", pady=4)
        tk.Label(interval_row, text="Интервал обновления (секунд):", fg="#cccccc", bg="#252526").pack(side="left")
        self.dash_interval_spin = tk.Spinbox(interval_row, from_=2, to=60, increment=1, width=6, bg="#333337", fg="white")
        self.dash_interval_spin.delete(0, "end")
        self.dash_interval_spin.insert(0, "5")
        self.dash_interval_spin.pack(side="left", padx=10)

        self.btn_dash_live = tk.Button(tab, text="▶ Запустить живой мониторинг ПК", bg="#28a745", fg="white",
                                       font=("Segoe UI", 10, "bold"), relief="flat", pady=6, command=self.action_toggle_live_dashboard)
        self.btn_dash_live.pack(fill="x", pady=(10, 5))

    # -------------------------------------------------------------------------
    # TAB: CLOCK & CALENDAR
    # -------------------------------------------------------------------------
    def _build_tab_clock(self):
        tab = tk.Frame(self.notebook, bg="#252526", padx=12, pady=12)
        self.notebook.add(tab, text="🕰️ Часы и Календарь")

        tk.Label(tab, text="Умные настольные E-Ink часы с календарем:", fg="#ffffff", bg="#252526", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))

        tk.Label(tab, text="Город для прогноза погоды (wttr.in):", fg="#cccccc", bg="#252526", font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 2))
        self.city_entry = tk.Entry(tab, bg="#333337", fg="white", insertbackground="white")
        self.city_entry.insert(0, self.cfg.get("city", DEFAULT_CITY))
        self.city_entry.pack(fill="x", pady=(0, 8))

        tk.Label(tab, text="Заметка / напоминание внизу часов:", fg="#cccccc", bg="#252526", font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 2))
        self.note_entry = tk.Entry(tab, bg="#333337", fg="white", insertbackground="white")
        self.note_entry.insert(0, "Продуктивного дня!")
        self.note_entry.pack(fill="x", pady=(0, 10))

        btn_render_clock = tk.Button(tab, text="👁 Сформировать часы и календарь", bg="#0e639c", fg="white", relief="flat", font=("Segoe UI", 9, "bold"), command=self.action_render_clock)
        btn_render_clock.pack(fill="x", pady=4)

        tk.Label(tab, text="Режим настольных часов (автообновление раз в минуту):", fg="#ffffff", bg="#252526", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15, 4))
        
        self.btn_clock_live = tk.Button(tab, text="▶ Запустить живые настольные часы", bg="#28a745", fg="white",
                                        font=("Segoe UI", 10, "bold"), relief="flat", pady=6, command=self.action_toggle_live_clock)
        self.btn_clock_live.pack(fill="x", pady=(10, 5))

    # -------------------------------------------------------------------------
    # TAB: TO-DO / NOTES
    # -------------------------------------------------------------------------
    def _build_tab_todo(self):
        tab = tk.Frame(self.notebook, bg="#252526", padx=12, pady=12)
        self.notebook.add(tab, text="📝 Заметки / To-Do")

        tk.Label(tab, text="Стикер задач на E-Ink экран:", fg="#ffffff", bg="#252526", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))

        tk.Label(tab, text="Заголовок:", fg="#cccccc", bg="#252526", font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 2))
        self.todo_title_entry = tk.Entry(tab, bg="#333337", fg="white", insertbackground="white")
        self.todo_title_entry.insert(0, "ПЛАНЫ НА СЕГОДНЯ")
        self.todo_title_entry.pack(fill="x", pady=(0, 6))

        tk.Label(tab, text="Список задач (используйте [x] для выполненных, [ ] для активных):", fg="#cccccc", bg="#252526", font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 2))
        self.todo_text = tk.Text(tab, height=10, bg="#333337", fg="white", insertbackground="white", font=("Segoe UI", 9))
        self.todo_text.insert("1.0", "[x] Прошить Kindle и поставить KUAL\n[x] Настроить ScreenSavers и большие шрифты\n[ ] Протестировать стриминг экрана\n[ ] Поставить KOReader\n[ ] Закинуть любимые книги\n[ ] Отдохнуть вечером")
        self.todo_text.pack(fill="both", expand=True, pady=(0, 8))

        btn_render_todo = tk.Button(tab, text="👁 Сформировать стикер задач", bg="#0e639c", fg="white", relief="flat", font=("Segoe UI", 9, "bold"), command=self.action_render_todo)
        btn_render_todo.pack(fill="x", pady=3)

    # -------------------------------------------------------------------------
    # TAB: BOOKS & WIRELESS SYNC (E-INK STYLE)
    # -------------------------------------------------------------------------
    def _build_tab_books(self):
        tab = tk.Frame(self.notebook, bg="#1e1e1e", padx=10, pady=10)
        self.notebook.add(tab, text=self.tr("tab_books"))

        # Outer E-Ink styled display card
        eink_card = tk.Frame(tab, bg="#f5f4ef", bd=2, relief="solid")
        eink_card.pack(fill="both", expand=True)

        # 1. Kindle Header Bar (Retro E-Ink status style)
        header_bar = tk.Frame(eink_card, bg="#111111", pady=8, padx=14)
        header_bar.pack(fill="x")

        self.books_header_lbl = tk.Label(header_bar, text=self.tr("books_header"), fg="#ffffff", bg="#111111", font=("Segoe UI", 11, "bold"))
        self.books_header_lbl.pack(side="left")

        self.books_count_lbl = tk.Label(header_bar, text=self.tr("books_count", count=0, size="0 МБ"), fg="#ffffff", bg="#111111", font=("Segoe UI", 10, "bold"))
        self.books_count_lbl.pack(side="right")

        # 2. Control & Connection Bar
        ctrl_bar = tk.Frame(eink_card, bg="#eae8e1", pady=8, padx=14, bd=1, relief="solid")
        ctrl_bar.pack(fill="x")

        self.book_conn_mode = tk.StringVar(value="wifi")
        self.rb_wifi = tk.Radiobutton(ctrl_bar, text=self.tr("books_wifi_mode"), variable=self.book_conn_mode, value="wifi",
                                      fg="#000000", bg="#eae8e1", selectcolor="#ffffff", activebackground="#eae8e1",
                                      font=("Segoe UI", 10, "bold"), command=self.action_refresh_books)
        self.rb_wifi.pack(side="left", padx=(0, 10))

        self.rb_usb = tk.Radiobutton(ctrl_bar, text=self.tr("books_usb_mode"), variable=self.book_conn_mode, value="usb",
                                     fg="#000000", bg="#eae8e1", selectcolor="#ffffff", activebackground="#eae8e1",
                                     font=("Segoe UI", 10, "bold"), command=self.action_refresh_books)
        self.rb_usb.pack(side="left", padx=(0, 16))

        self.btn_books_refresh = tk.Button(ctrl_bar, text=self.tr("books_refresh"), bg="#111111", fg="#ffffff", relief="flat",
                                           font=("Segoe UI", 10, "bold"), padx=12, pady=4, command=self.action_refresh_books)
        self.btn_books_refresh.pack(side="left", padx=(0, 12))

        self.books_status_badge = tk.Label(ctrl_bar, text=self.tr("books_loading"), fg="#555555", bg="#eae8e1", font=("Segoe UI", 10, "bold"))
        self.books_status_badge.pack(side="left")

        # 3. Main Center: E-Ink Book Catalog (Large table)
        catalog_frame = tk.Frame(eink_card, bg="#f5f4ef", padx=14, pady=10)
        catalog_frame.pack(fill="both", expand=True)

        # Search row
        search_row = tk.Frame(catalog_frame, bg="#f5f4ef")
        search_row.pack(fill="x", pady=(0, 8))

        self.books_search_lbl = tk.Label(search_row, text=self.tr("books_search"), fg="#000000", bg="#f5f4ef", font=("Segoe UI", 11, "bold"))
        self.books_search_lbl.pack(side="left", padx=(0, 8))

        self.book_search_var = tk.StringVar()
        self.book_search_var.trace_add("write", lambda *a: self._filter_books_list())
        self.search_entry = tk.Entry(search_row, textvariable=self.book_search_var, bg="#ffffff", fg="#000000",
                                     font=("Segoe UI", 11), insertbackground="black", bd=1, relief="solid")
        self.search_entry.pack(side="left", fill="x", expand=True)

        # Big Treeview table
        tree_container = tk.Frame(catalog_frame, bg="#ffffff", bd=1, relief="solid")
        tree_container.pack(fill="both", expand=True)

        self.books_tree = ttk.Treeview(tree_container, columns=("name", "ext", "size"), show="headings", selectmode="browse", height=9)
        self.books_tree.heading("name", text=self.tr("books_col_name"), anchor="w")
        self.books_tree.heading("ext", text=self.tr("books_col_ext"), anchor="center")
        self.books_tree.heading("size", text=self.tr("books_col_size"), anchor="e")

        self.books_tree.column("name", width=440, stretch=True)
        self.books_tree.column("ext", width=90, anchor="center")
        self.books_tree.column("size", width=110, anchor="e")

        sb = ttk.Scrollbar(tree_container, orient="vertical", command=self.books_tree.yview)
        self.books_tree.configure(yscrollcommand=sb.set)
        self.books_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Catalog Actions row
        cat_acts = tk.Frame(catalog_frame, bg="#f5f4ef")
        cat_acts.pack(fill="x", pady=(8, 0))

        self.btn_delete_book = tk.Button(cat_acts, text=self.tr("books_delete"), bg="#c9302c", fg="#ffffff", relief="flat",
                                         font=("Segoe UI", 10, "bold"), padx=10, pady=4, command=self.action_delete_book)
        self.btn_delete_book.pack(side="left", padx=(0, 10))

        self.btn_rescan_display = tk.Button(cat_acts, text=self.tr("books_rescan"), bg="#3a3d41", fg="#ffffff", relief="flat",
                                            font=("Segoe UI", 10), padx=10, pady=4, command=self.action_rescan_library)
        self.btn_rescan_display.pack(side="left")

        # 4. Bottom Section: Upload & Auto-Convert Box
        self.up_box = tk.LabelFrame(eink_card, text=self.tr("books_upload_box"), fg="#000000", bg="#eae8e1", bd=1, relief="solid",
                                    font=("Segoe UI", 10, "bold"), padx=12, pady=10)
        self.up_box.pack(fill="x", padx=14, pady=(0, 12))

        # Big prominent upload button
        self.btn_pick_books = tk.Button(self.up_box, text=self.tr("books_pick_btn"), bg="#0e639c", fg="#ffffff", relief="flat",
                                        font=("Segoe UI", 11, "bold"), pady=6, command=self.action_upload_books)
        self.btn_pick_books.pack(fill="x", pady=(0, 6))

        # Format options row
        fmt_bar = tk.Frame(self.up_box, bg="#eae8e1")
        fmt_bar.pack(fill="x", pady=(0, 4))

        self.lbl_target_fmt = tk.Label(fmt_bar, text=self.tr("books_target_fmt"), fg="#000000", bg="#eae8e1", font=("Segoe UI", 10, "bold"))
        self.lbl_target_fmt.pack(side="left", padx=(0, 6))

        self.book_target_fmt = tk.StringVar(value="mobi")
        tk.Radiobutton(fmt_bar, text="MOBI (Kindle Keyboard / PW)", variable=self.book_target_fmt, value="mobi",
                       fg="#000000", bg="#eae8e1", selectcolor="#ffffff", activebackground="#eae8e1", font=("Segoe UI", 10, "bold")).pack(side="left", padx=4)
        tk.Radiobutton(fmt_bar, text="AZW3 (KF8)", variable=self.book_target_fmt, value="azw3",
                       fg="#000000", bg="#eae8e1", selectcolor="#ffffff", activebackground="#eae8e1", font=("Segoe UI", 10, "bold")).pack(side="left", padx=4)

        conv_bin = kindle_books.find_calibre_converter()
        conv_text = self.tr("books_calibre_ok") if conv_bin else self.tr("books_calibre_missing")
        conv_fg = "#006400" if conv_bin else "#8b0000"
        self.calibre_status_lbl = tk.Label(fmt_bar, text=conv_text, fg=conv_fg, bg="#eae8e1", font=("Segoe UI", 9, "bold"))
        self.calibre_status_lbl.pack(side="right")

        self.skip_native_var = tk.BooleanVar(value=True)
        self.cb_skip_native = tk.Checkbutton(self.up_box, text=self.tr("books_skip_native"), variable=self.skip_native_var,
                                             fg="#222222", bg="#eae8e1", selectcolor="#ffffff", activebackground="#eae8e1", font=("Segoe UI", 9))
        self.cb_skip_native.pack(anchor="w", pady=(0, 4))

        self.book_progress = ttk.Progressbar(self.up_box, mode="determinate")
        self.book_progress.pack(fill="x", pady=(2, 4))

        self.book_log_lbl = tk.Label(self.up_box, text=self.tr("books_waiting"), fg="#333333", bg="#eae8e1", font=("Segoe UI", 10, "bold"), wraplength=650, justify="left")
        self.book_log_lbl.pack(anchor="w")

    # -------------------------------------------------------------------------
    # TAB: JAILBREAK & EXTENSIONS INSTALLER
    # -------------------------------------------------------------------------
    def _build_tab_jailbreak(self):
        tab = tk.Frame(self.notebook, bg="#252526", padx=12, pady=12)
        self.notebook.add(tab, text="🚀 Прошивка & AI")

        # 1. Kindle USB Auto-Detection Section
        detect_box = tk.LabelFrame(tab, text=" 📱 Подключение Kindle по USB ", fg="#ffffff", bg="#252526", padx=10, pady=8)
        detect_box.pack(fill="x", pady=(0, 10))

        row1 = tk.Frame(detect_box, bg="#252526")
        row1.pack(fill="x", pady=2)

        self.btn_detect_kindle = tk.Button(row1, text="🔍 Найти Kindle (USB)", bg="#3a3d41", fg="white", relief="flat", font=("Segoe UI", 9, "bold"), command=self.action_detect_kindle)
        self.btn_detect_kindle.pack(side="left", padx=(0, 10))

        self.kindle_usb_status_lbl = tk.Label(row1, text="Нажмите 'Найти Kindle' для проверки", fg="#aaaaaa", bg="#252526", font=("Segoe UI", 9))
        self.kindle_usb_status_lbl.pack(side="left")

        # 2. 1-Click AI Chat Deployer
        ai_box = tk.LabelFrame(tab, text=" 🤖 Установка AI Chat (GLM-5.3 Flash) в 1 клик ", fg="#ffffff", bg="#252526", padx=10, pady=8)
        ai_box.pack(fill="x", pady=(0, 10))

        tk.Label(ai_box, text="API Ключ Polza.ai (сохраняется в /mnt/us/ai/config.json):", fg="#cccccc", bg="#252526", font=("Segoe UI", 8)).pack(anchor="w")
        self.ai_key_entry = tk.Entry(ai_box, bg="#333337", fg="white", insertbackground="white")
        existing_key = self.cfg.get("api_key", "")
        if existing_key:
            self.ai_key_entry.insert(0, existing_key)
        self.ai_key_entry.pack(fill="x", pady=(2, 6))

        btn_install_ai = tk.Button(ai_box, text="📥 Установить AI Chat на Kindle", bg="#0e639c", fg="white", relief="flat", font=("Segoe UI", 9, "bold"), command=self.action_install_ai)
        btn_install_ai.pack(fill="x", pady=2)

        # 3. Jailbreak & Extensions Guide
        jb_box = tk.LabelFrame(tab, text=" 📖 Мастер Джейлбрейка & Сторонних Приложений ", fg="#ffffff", bg="#252526", padx=10, pady=8)
        jb_box.pack(fill="both", expand=True)

        guide_text = tk.Text(jb_box, height=8, bg="#1e1e1e", fg="#e0e0e0", relief="flat", font=("Segoe UI", 8), wrap="word")
        guide_text.insert("1.0",
            "1. ДЖЕЙЛБРЕЙК KINDLE (K3W / K3G / K4 / K5):\n"
            "   • Подключите Kindle по USB к компьютеру.\n"
            "   • Скачайте архив джейлбрейка (MobileRead Kindle Jailbreak).\n"
            "   • Скопируйте файл update_jailbreak_***_install.bin в корень диска Kindle.\n"
            "   • Безопасно извлеките Kindle. Нажмите: [Menu] -> Settings -> [Menu] -> Update Your Kindle.\n"
            "   • Читалка перезагрузится, внизу экрана появится надпись 'Jailbreak succeeded'.\n\n"
            "2. УСТАНОВКА MKK И KUAL (ЛАУНЧЕР ПРИЛОЖЕНИЙ):\n"
            "   • Скопируйте файл KUAL-KDK-1.0.azw2 в папку documents/ на Kindle.\n"
            "   • На главном экране Kindle появится книга 'KUAL' — это меню всех приложений!\n\n"
            "3. ЗАПУСК AI CHAT:\n"
            "   • Нажмите кнопку 'Установить AI Chat на Kindle' выше.\n"
            "   • В KUAL появится пункт 'AI Chat (GLM-5.3)'.\n"
            "   • Подключитесь к Wi-Fi и общайтесь с ИИ прямо с читалки!"
        )
        guide_text.config(state="disabled")
        guide_text.pack(fill="both", expand=True)

    def find_kindle_drive(self):
        for letter in ["D", "E", "F", "G", "H", "I", "J", "K", "L", "M"]:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                if os.path.exists(os.path.join(drive, "documents")) or os.path.exists(os.path.join(drive, "system")):
                    return drive
        return None

    def action_detect_kindle(self):
        drive = self.find_kindle_drive()
        if drive:
            try:
                import shutil
                total, used, free = shutil.disk_usage(drive)
                free_gb = free / (1024 ** 3)
                self.kindle_usb_status_lbl.config(text=f"✅ Kindle обнаружен: {drive} ({free_gb:.2f} ГБ свободно)", fg="#89d185")
                self.set_status(f"Kindle найден на диске {drive}")
            except Exception:
                self.kindle_usb_status_lbl.config(text=f"✅ Kindle обнаружен: {drive}", fg="#89d185")
        else:
            self.kindle_usb_status_lbl.config(text="❌ Kindle не обнаружен. Подключите USB кабель", fg="#f48771")
            self.set_status("Kindle не найден по USB")

    def action_install_ai(self):
        drive = self.find_kindle_drive()
        if not drive:
            messagebox.showerror("Ошибка", "Kindle не подключен по USB!\nПодключите читалку кабелем к ПК и повторите попытку.")
            return

        api_key = self.ai_key_entry.get().strip()
        if not api_key:
            if not messagebox.askyesno("Внимание", "API ключ не введён. Вы хотите установить AI Chat без ключа?\n(Ключ можно будет ввести позже в /mnt/us/ai/config.json)"):
                return

        try:
            import shutil
            deploy_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_deploy")
            if not os.path.exists(deploy_src):
                messagebox.showerror("Ошибка", f"Папка ai_deploy не найдена: {deploy_src}")
                return

            # Copy ai folder
            src_ai = os.path.join(deploy_src, "ai")
            dst_ai = os.path.join(drive, "ai")
            os.makedirs(dst_ai, exist_ok=True)
            for item in os.listdir(src_ai):
                s = os.path.join(src_ai, item)
                d = os.path.join(dst_ai, item)
                if os.path.isfile(s):
                    shutil.copy2(s, d)

            # Copy extension folder
            src_ext = os.path.join(deploy_src, "extensions", "ai_chat")
            dst_ext = os.path.join(drive, "extensions", "ai_chat")
            os.makedirs(dst_ext, exist_ok=True)
            os.makedirs(os.path.join(dst_ext, "bin"), exist_ok=True)
            for item in os.listdir(src_ext):
                s = os.path.join(src_ext, item)
                d = os.path.join(dst_ext, item)
                if os.path.isfile(s):
                    shutil.copy2(s, d)
            src_ext_bin = os.path.join(src_ext, "bin")
            if os.path.exists(src_ext_bin):
                for item in os.listdir(src_ext_bin):
                    shutil.copy2(os.path.join(src_ext_bin, item), os.path.join(dst_ext, "bin", item))

            # Save API key to Kindle config.json
            if api_key:
                kindle_cfg = {"api_key": api_key, "model": "z-ai/glm-5.3-flash"}
                with open(os.path.join(dst_ai, "config.json"), "w", encoding="utf-8") as f:
                    json.dump(kindle_cfg, f, indent=2)
                self.cfg["api_key"] = api_key
                save_config(self.cfg)

            messagebox.showinfo("Успех", f"AI Chat успешно установлен на Kindle ({drive})!\n\n1. Извлеките Kindle в Windows.\n2. Отключите USB кабель.\n3. Откройте KUAL -> AI Chat (GLM-5.3).")
            self.set_status("AI Chat установлен на Kindle")
        except Exception as e:
            messagebox.showerror("Ошибка установки", f"Не удалось скопировать файлы на Kindle:\n{e}")

    # -------------------------------------------------------------------------
    # ROTATION HANDLING
    # -------------------------------------------------------------------------
    def action_rotate(self, delta):
        self.rotation = (self.rotation + delta) % 360
        self.rot_var.set(self.rotation)
        self._on_rotation_changed()

    def _on_rotation_radio_change(self):
        self.rotation = self.rot_var.get()
        self._on_rotation_changed()

    def _on_rotation_changed(self):
        self.cfg["rotation"] = self.rotation
        save_config(self.cfg)
        is_landscape = (self.rotation in (90, 270))
        mode_text = "Альбом (800×600)" if is_landscape else "Портрет (600×800)"
        self.res_lbl.config(text=f"Ориентация: {self.rotation}° • {mode_text}")
        self._update_preview()
        self.set_status(f"Ориентация: {self.rotation}° ({mode_text})")

    # -------------------------------------------------------------------------
    # CANVAS & DRAWING ACTIONS
    # -------------------------------------------------------------------------
    def _set_mode(self):
        self.tool_mode = self.mode_var.get()

    def _on_size_change(self, val):
        self.brush_size = int(val)

    def _update_preview(self):
        is_landscape = (self.rotation in (90, 270))
        # Display preview size
        pw = 400 if is_landscape else 300
        ph = 300 if is_landscape else 400
        self.canvas_preview.config(width=pw, height=ph)

        # Rotate preview image according to rotation angle
        disp_img = self.image
        if self.rotation % 360 != 0:
            disp_img = disp_img.rotate(-self.rotation, expand=True)

        preview_img = disp_img.resize((pw, ph), Image.Resampling.BILINEAR)
        self.tk_preview = ImageTk.PhotoImage(preview_img)
        self.canvas_preview.create_image(0, 0, anchor="nw", image=self.tk_preview)

    def _canvas_click(self, event):
        is_landscape = (self.rotation in (90, 270))
        pw = 400 if is_landscape else 300
        ph = 300 if is_landscape else 400
        orig_w = Y_RES if is_landscape else X_RES
        orig_h = X_RES if is_landscape else Y_RES

        img_x = int(event.x * (orig_w / pw))
        img_y = int(event.y * (orig_h / ph))

        if self.tool_mode == "text":
            txt = self.text_input.get()
            if txt:
                font = get_font(max(14, self.brush_size * 3), bold=True)
                self.draw.text((img_x, img_y), txt, fill=(0, 0, 0), font=font)
                self._update_preview()
            return

        self.last_x = img_x
        self.last_y = img_y
        self._canvas_drag(event)

    def _canvas_drag(self, event):
        if self.tool_mode == "text":
            return
        is_landscape = (self.rotation in (90, 270))
        pw = 400 if is_landscape else 300
        ph = 300 if is_landscape else 400
        orig_w = Y_RES if is_landscape else X_RES
        orig_h = X_RES if is_landscape else Y_RES

        img_x = int(event.x * (orig_w / pw))
        img_y = int(event.y * (orig_h / ph))

        color = (255, 255, 255) if self.tool_mode == "eraser" else (0, 0, 0)
        radius = self.brush_size * 2

        if self.last_x is not None and self.last_y is not None:
            self.draw.line([(self.last_x, self.last_y), (img_x, img_y)], fill=color, width=radius * 2)
            self.draw.ellipse([img_x - radius, img_y - radius, img_x + radius, img_y + radius], fill=color)

        self.last_x = img_x
        self.last_y = img_y
        self._update_preview()

    def _canvas_release(self, event):
        self.last_x = None
        self.last_y = None

    def action_clear_canvas(self):
        is_landscape = (self.rotation in (90, 270))
        w, h = (Y_RES, X_RES) if is_landscape else (X_RES, Y_RES)
        self.image = Image.new("RGB", (w, h), (255, 255, 255))
        self.draw = ImageDraw.Draw(self.image)
        self._update_preview()
        self.set_status("Холст очищен")

    def action_invert_canvas(self):
        self.image = ImageOps.invert(self.image.convert('RGB'))
        self.draw = ImageDraw.Draw(self.image)
        self._update_preview()
        self.set_status("Цвета инвертированы")

    def action_load_image(self):
        path = filedialog.askopenfilename(
            title="Выберите картинку для холста",
            filetypes=[("Изображения", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp"), ("Все файлы", "*.*")]
        )
        if not path:
            return
        with Image.open(path) as loaded:
            loaded_rgb = loaded.convert('RGB')
            is_landscape = (self.rotation in (90, 270))
            tw, th = (Y_RES, X_RES) if is_landscape else (X_RES, Y_RES)
            
            target_ratio = tw / th
            img_ratio = loaded_rgb.width / loaded_rgb.height
            if img_ratio > target_ratio:
                nw = tw
                nh = int(tw / img_ratio)
            else:
                nh = th
                nw = int(th * img_ratio)
            resized = loaded_rgb.resize((nw, nh), Image.Resampling.LANCZOS)
            bg = Image.new("RGB", (tw, th), (255, 255, 255))
            offset = ((tw - nw) // 2, (th - nh) // 2)
            bg.paste(resized, offset)
            self.image = bg
            self.draw = ImageDraw.Draw(self.image)
            self._update_preview()
            self.set_status(f"Загружено: {os.path.basename(path)}")

    def action_save_image(self):
        path = filedialog.asksaveasfilename(
            title="Сохранить изображение",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")]
        )
        if path:
            self.image.save(path)
            self.set_status(f"Сохранено в {os.path.basename(path)}")

    # -------------------------------------------------------------------------
    # GENERATOR ACTIONS
    # -------------------------------------------------------------------------
    def action_render_dashboard(self):
        is_landscape = (self.rotation in (90, 270))
        self.image = generate_pc_dashboard(landscape=is_landscape)
        self.draw = ImageDraw.Draw(self.image)
        self._update_preview()
        self.set_status("Дашборд ПК сформирован")

    def action_render_clock(self):
        is_landscape = (self.rotation in (90, 270))
        city = self.city_entry.get().strip() or DEFAULT_CITY
        note = self.note_entry.get().strip()
        
        # Save city
        self.cfg["city"] = city
        save_config(self.cfg)

        # Fetch weather if older than 10 mins
        now = time.time()
        if not self.weather_cache or (now - self.weather_last_fetch > 600):
            self.weather_cache = fetch_weather(city)
            self.weather_last_fetch = now

        self.image = generate_desk_clock(landscape=is_landscape, weather_data=self.weather_cache, custom_note=note)
        self.draw = ImageDraw.Draw(self.image)
        self._update_preview()
        self.set_status(f"Часы и календарь сформированы (Погода: {self.weather_cache.get('temp', '')})")

    def action_render_todo(self):
        is_landscape = (self.rotation in (90, 270))
        title = self.todo_title_entry.get().strip() or "СПИСОК ДЕЛ"
        items = self.todo_text.get("1.0", "end")
        self.image = generate_todo_note(title=title, text_items=items, landscape=is_landscape)
        self.draw = ImageDraw.Draw(self.image)
        self._update_preview()
        self.set_status("Стикер заметок сформирован")

    # -------------------------------------------------------------------------
    # LIVE WORKER TOGGLES (STREAM / DASHBOARD / CLOCK)
    # -------------------------------------------------------------------------
    def _stop_active_worker(self):
        if self.worker_stop_event:
            self.worker_stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
        self.active_mode = None
        self.worker_stop_event = None
        self.worker_thread = None

        # Reset button states
        self.btn_stream_toggle.config(text="▶ Запустить прямую трансляцию", bg="#28a745")
        self.btn_dash_live.config(text="▶ Запустить живой мониторинг ПК", bg="#28a745")
        self.btn_clock_live.config(text="▶ Запустить живые настольные часы", bg="#28a745")

    def action_toggle_stream(self):
        if self.active_mode == "stream":
            self._stop_active_worker()
            self.set_status("Трансляция остановлена")
            return

        self._stop_active_worker()
        if not mss:
            messagebox.showerror("Ошибка", "Модуль mss не установлен!")
            return

        try:
            fps_val = float(self.stream_fps.get())
        except ValueError:
            fps_val = 1.0

        self.active_mode = "stream"
        self.worker_stop_event = threading.Event()
        self.btn_stream_toggle.config(text="⏹ Остановить трансляцию", bg="#d9534f")
        self.set_status(f"Идет прямая трансляция ({fps_val} FPS, поворот {self.rotation}°)...", fg="#007acc")

        srv = self.ip_entry.get().strip()
        dither_flag = self.dither_var.get()
        rot = self.rotation

        def worker():
            interval = 1.0 / max(0.1, fps_val)
            is_landscape = (rot in (90, 270))
            tw, th = (Y_RES, X_RES) if is_landscape else (X_RES, Y_RES)
            
            with mss.mss() as sct:
                mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                while not self.worker_stop_event.is_set():
                    t0 = time.time()
                    try:
                        sct_img = sct.grab(mon)
                        cap = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                        
                        target_ratio = tw / th
                        img_ratio = cap.width / cap.height
                        if img_ratio > target_ratio:
                            nw = tw
                            nh = int(tw / img_ratio)
                        else:
                            nh = th
                            nw = int(th * img_ratio)
                        resized = cap.resize((nw, nh), Image.Resampling.BILINEAR)
                        frame = Image.new("RGB", (tw, th), (255, 255, 255))
                        frame.paste(resized, ((tw - nw) // 2, (th - nh) // 2))

                        send_image_to_kindle(frame, srv, rotation=rot, dither=dither_flag)
                    except Exception as e:
                        time.sleep(1)

                    rem = interval - (time.time() - t0)
                    if rem > 0:
                        time.sleep(rem)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def action_toggle_live_dashboard(self):
        if self.active_mode == "dashboard":
            self._stop_active_worker()
            self.set_status("Мониторинг ПК остановлен")
            return

        self._stop_active_worker()
        try:
            interval_sec = max(2, int(self.dash_interval_spin.get()))
        except ValueError:
            interval_sec = 5

        self.active_mode = "dashboard"
        self.worker_stop_event = threading.Event()
        self.btn_dash_live.config(text="⏹ Остановить мониторинг", bg="#d9534f")
        self.set_status(f"Идет живой мониторинг ПК (каждые {interval_sec} сек)...", fg="#007acc")

        srv = self.ip_entry.get().strip()
        rot = self.rotation

        def worker():
            is_landscape = (rot in (90, 270))
            while not self.worker_stop_event.is_set():
                t0 = time.time()
                try:
                    dash_img = generate_pc_dashboard(landscape=is_landscape)
                    # Update local preview safely
                    self.image = dash_img
                    self.draw = ImageDraw.Draw(self.image)
                    self.after(0, self._update_preview)

                    send_image_to_kindle(dash_img, srv, rotation=rot)
                except Exception:
                    time.sleep(1)

                rem = interval_sec - (time.time() - t0)
                if rem > 0:
                    time.sleep(rem)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def action_toggle_live_clock(self):
        if self.active_mode == "clock":
            self._stop_active_worker()
            self.set_status("Режим часов остановлен")
            return

        self._stop_active_worker()
        self.active_mode = "clock"
        self.worker_stop_event = threading.Event()
        self.btn_clock_live.config(text="⏹ Остановить настольные часы", bg="#d9534f")
        self.set_status("Режим живых настольных часов активен (обновление раз в минуту)...", fg="#007acc")

        srv = self.ip_entry.get().strip()
        city = self.city_entry.get().strip() or DEFAULT_CITY
        note = self.note_entry.get().strip()
        rot = self.rotation

        def worker():
            is_landscape = (rot in (90, 270))
            last_weather = 0
            w_data = None
            while not self.worker_stop_event.is_set():
                t0 = time.time()
                try:
                    if not w_data or (t0 - last_weather > 900):
                        w_data = fetch_weather(city)
                        last_weather = t0
                    
                    clock_img = generate_desk_clock(landscape=is_landscape, weather_data=w_data, custom_note=note)
                    self.image = clock_img
                    self.draw = ImageDraw.Draw(self.image)
                    self.after(0, self._update_preview)

                    send_image_to_kindle(clock_img, srv, rotation=rot)
                except Exception:
                    time.sleep(2)

                # Sleep until next minute boundary
                now = datetime.datetime.now()
                sec_to_next = 60 - now.second
                for _ in range(max(1, sec_to_next)):
                    if self.worker_stop_event.is_set():
                        break
                    time.sleep(1)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    # -------------------------------------------------------------------------
    # CAPTURE / SLIDESHOW ACTIONS
    # -------------------------------------------------------------------------
    def action_capture_full_screen(self):
        if not mss:
            messagebox.showerror("Ошибка", "Модуль mss не найден!")
            return
        with mss.mss() as sct:
            mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            sct_img = sct.grab(mon)
            cap = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            self._fit_to_canvas(cap)
            self.set_status("Снимок экрана ПК загружен на холст")

    def action_select_area_capture(self):
        snipper = tk.Toplevel(self)
        snipper.attributes("-fullscreen", True)
        snipper.attributes("-alpha", 0.3)
        snipper.config(cursor="cross")

        canvas_snip = tk.Canvas(snipper, cursor="cross", bg="gray")
        canvas_snip.pack(fill="both", expand=True)

        start_x, start_y = [None], [None]
        rect_id = [None]

        def on_down(e):
            start_x[0], start_y[0] = e.x, e.y
            rect_id[0] = canvas_snip.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)

        def on_move(e):
            if start_x[0] is not None:
                canvas_snip.coords(rect_id[0], start_x[0], start_y[0], e.x, e.y)

        def on_up(e):
            x1, y1 = min(start_x[0], e.x), min(start_y[0], e.y)
            x2, y2 = max(start_x[0], e.x), max(start_y[0], e.y)
            snipper.destroy()

            if x2 - x1 > 20 and y2 - y1 > 20 and mss:
                with mss.mss() as sct:
                    bbox = {"left": x1, "top": y1, "width": x2 - x1, "height": y2 - y1}
                    sct_img = sct.grab(bbox)
                    cap = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    self._fit_to_canvas(cap)
                    self.set_status("Выделенная область загружена на холст")

        canvas_snip.bind("<ButtonPress-1>", on_down)
        canvas_snip.bind("<B1-Motion>", on_move)
        canvas_snip.bind("<ButtonRelease-1>", on_up)

    def _fit_to_canvas(self, loaded_img):
        is_landscape = (self.rotation in (90, 270))
        tw, th = (Y_RES, X_RES) if is_landscape else (X_RES, Y_RES)
        target_ratio = tw / th
        img_ratio = loaded_img.width / loaded_img.height
        if img_ratio > target_ratio:
            nw = tw
            nh = int(tw / img_ratio)
        else:
            nh = th
            nw = int(th * img_ratio)
        resized = loaded_img.resize((nw, nh), Image.Resampling.LANCZOS)
        bg = Image.new("RGB", (tw, th), (255, 255, 255))
        offset = ((tw - nw) // 2, ((th - nh) // 2))
        bg.paste(resized, offset)
        self.image = bg
        self.draw = ImageDraw.Draw(self.image)
        self._update_preview()

    def action_choose_slideshow_dir(self):
        dir_path = filedialog.askdirectory(title="Выберите папку с картинками")
        if not dir_path:
            return
        exts = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif')
        self.slideshow_files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.lower().endswith(exts)]
        if not self.slideshow_files:
            messagebox.showinfo("Инфо", "В папке нет картинок!")
            return
        self.slideshow_idx = 0
        self._load_slide(0)

    def _load_slide(self, idx):
        if not self.slideshow_files:
            return
        self.slideshow_idx = idx % len(self.slideshow_files)
        path = self.slideshow_files[self.slideshow_idx]
        with Image.open(path) as img:
            self._fit_to_canvas(img.convert('RGB'))
        self.slide_info_lbl.config(text=f"[{self.slideshow_idx + 1}/{len(self.slideshow_files)}] {os.path.basename(path)}")
        self.set_status(f"Слайд: {os.path.basename(path)}")

    def action_slide_next(self):
        if self.slideshow_files:
            self._load_slide(self.slideshow_idx + 1)
            self.action_send_now()

    def action_slide_prev(self):
        if self.slideshow_files:
            self._load_slide(self.slideshow_idx - 1)
            self.action_send_now()

    # -------------------------------------------------------------------------
    # KINDLE COMMUNICATION
    # -------------------------------------------------------------------------
    def action_send_now(self):
        srv = self.ip_entry.get().strip()
        self.cfg["ip"] = srv
        save_config(self.cfg)
        
        self.set_status("Отправка на Kindle...", fg="#007acc")
        self.btn_send.config(state="disabled")

        def worker():
            try:
                send_image_to_kindle(self.image, srv, rotation=self.rotation, dither=self.dither_var.get())
                self.set_status("✓ Успешно отображено на экране Kindle", fg="#89d185")
            except Exception as e:
                self.set_status(f"Ошибка: {e}", fg="#f48771")
            finally:
                self.btn_send.config(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    def action_clear_kindle(self):
        srv = self.ip_entry.get().strip()
        self.set_status("Очистка экрана...", fg="#007acc")
        def worker():
            try:
                clear_kindle(srv)
                self.set_status("Экран Kindle очищен", fg="#89d185")
            except Exception as e:
                self.set_status(f"Ошибка: {e}", fg="#f48771")
        threading.Thread(target=worker, daemon=True).start()

    def action_ping_kindle(self):
        self._check_ping_async()

    def _check_ping_async(self):
        srv = self.ip_entry.get().strip() or DEFAULT_IP
        self.ping_status_lbl.config(text="● Проверка...", fg="#aaaaaa")
        def worker():
            ok, latency = check_kindle_ping(srv)
            if ok:
                self.after(0, lambda: self.ping_status_lbl.config(text=f"🟢 В сети ({latency} мс)", fg="#89d185"))
            else:
                self.after(0, lambda: self.ping_status_lbl.config(text="🔴 Офлайн / Wi-Fi?", fg="#f48771"))
        threading.Thread(target=worker, daemon=True).start()

    def action_create_desktop_shortcut(self):
        try:
            from create_desktop_shortcut import make_shortcut
            make_shortcut()
            messagebox.showinfo("Готово", "Ярлык 'Kindle Studio' успешно создан на Рабочем столе!")
            self.set_status("✓ Ярлык создан на Рабочем столе")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать ярлык: {e}")

    def set_status(self, text, fg="#89d185"):
        self.status_lbl.config(text=text, fg=fg)

    # -------------------------------------------------------------------------
    # BOOKS & WI-FI LIBRARY ACTIONS
    # -------------------------------------------------------------------------
    def tr(self, key, **kwargs):
        text = I18N.get(self.lang, {}).get(key, I18N["ru"].get(key, key))
        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass
        return text

    def action_toggle_language(self):
        self.lang = "en" if self.lang == "ru" else "ru"
        self.cfg["lang"] = self.lang
        save_config(self.cfg)
        self._apply_language()

    def _apply_language(self):
        self.title(self.tr("title"))
        self.lbl_ip.config(text=self.tr("ip_label"))
        self.btn_lang.config(text=self.tr("btn_lang"))
        self.btn_send.config(text=self.tr("btn_send"))
        self.btn_clear_screen.config(text=self.tr("btn_clear"))
        self.btn_shortcut.config(text=self.tr("btn_shortcut"))
        self.btn_ping.config(text=self.tr("btn_ping"))
        self.status_lbl.config(text=self.tr("ready"))

        tab_names = [
            self.tr("tab_canvas"),
            self.tr("tab_stream"),
            self.tr("tab_dash"),
            self.tr("tab_clock"),
            self.tr("tab_todo"),
            self.tr("tab_books"),
            self.tr("tab_jb"),
        ]
        for idx, tname in enumerate(tab_names):
            try:
                self.notebook.tab(idx, text=tname)
            except Exception:
                pass

        if hasattr(self, "books_header_lbl"):
            self.books_header_lbl.config(text=self.tr("books_header"))
            self.rb_wifi.config(text=self.tr("books_wifi_mode"))
            self.rb_usb.config(text=self.tr("books_usb_mode"))
            self.btn_books_refresh.config(text=self.tr("books_refresh"))
            self.books_search_lbl.config(text=self.tr("books_search"))
            self.books_tree.heading("name", text=self.tr("books_col_name"))
            self.books_tree.heading("ext", text=self.tr("books_col_ext"))
            self.books_tree.heading("size", text=self.tr("books_col_size"))
            self.btn_delete_book.config(text=self.tr("books_delete"))
            self.btn_rescan_display.config(text=self.tr("books_rescan"))
            self.up_box.config(text=self.tr("books_upload_box"))
            self.btn_pick_books.config(text=self.tr("books_pick_btn"))
            self.lbl_target_fmt.config(text=self.tr("books_target_fmt"))
            self.cb_skip_native.config(text=self.tr("books_skip_native"))
            conv_bin = kindle_books.find_calibre_converter()
            self.calibre_status_lbl.config(text=self.tr("books_calibre_ok") if conv_bin else self.tr("books_calibre_missing"))
            self.action_refresh_books()

    def action_refresh_books(self):
        mode = self.book_conn_mode.get()
        srv = self.ip_entry.get().strip() or DEFAULT_IP
        self.books_status_badge.config(text=self.tr("books_loading"), fg="#555555")

        def worker():
            try:
                if mode == "wifi":
                    books = kindle_books.list_kindle_books_ssh(srv, lang=self.lang)
                    badge_text = self.tr("books_online")
                    badge_fg = "#006400"
                else:
                    drive = self.find_kindle_drive()
                    if not drive:
                        raise RuntimeError("Kindle not connected via USB!" if self.lang == "en" else "Kindle не подключен по USB!")
                    books = kindle_books.list_kindle_books_usb(drive, lang=self.lang)
                    badge_text = self.tr("books_usb_online", drive=drive)
                    badge_fg = "#006400"

                self.cached_books = books
                total_bytes = sum(b["size_bytes"] for b in books)
                summary_text = self.tr("books_count", count=len(books), size=kindle_books.format_size(total_bytes, lang=self.lang))

                def update_ui():
                    self.books_status_badge.config(text=badge_text, fg=badge_fg)
                    self.books_count_lbl.config(text=summary_text)
                    self._filter_books_list()
                    self.set_status(f"Kindle books: {len(books)}" if self.lang == "en" else f"Загружен список книг: {len(books)} шт.")

                self.after(0, update_ui)

            except Exception as e:
                err_str = str(e)
                def update_err(msg=err_str):
                    self.books_status_badge.config(text=self.tr("books_offline"), fg="#c9302c")
                    self.set_status(f"Error: {msg}" if self.lang == "en" else f"Ошибка связи: {msg}", fg="#f48771")
                    self.book_log_lbl.config(text=f"⚠️ {msg}", fg="#c9302c")
                self.after(0, update_err)

        threading.Thread(target=worker, daemon=True).start()

    def _filter_books_list(self):
        query = self.book_search_var.get().strip().lower()
        self.books_tree.delete(*self.books_tree.get_children())
        for b in self.cached_books:
            if not query or query in b["name"].lower():
                self.books_tree.insert("", "end", iid=b["rel_path"], values=(b["name"], b["ext"], b["size_str"]))

    def action_delete_book(self):
        selected = self.books_tree.selection()
        if not selected:
            messagebox.showinfo("Info" if self.lang == "en" else "Инфо", "Select a book from the list to delete." if self.lang == "en" else "Выберите книгу из списка для удаления.")
            return

        rel_path = selected[0]
        book = next((b for b in self.cached_books if b["rel_path"] == rel_path), None)
        book_name = book["name"] if book else rel_path

        confirm_msg = self.tr("books_delete_confirm", name=book_name)
        if not messagebox.askyesno("Confirm" if self.lang == "en" else "Подтверждение", confirm_msg):
            return

        mode = self.book_conn_mode.get()
        srv = self.ip_entry.get().strip() or DEFAULT_IP

        def worker():
            try:
                if mode == "wifi":
                    kindle_books.delete_book_wifi(rel_path, server=srv, lang=self.lang)
                else:
                    drive = self.find_kindle_drive()
                    if not drive:
                        raise RuntimeError("Kindle not connected via USB!" if self.lang == "en" else "Kindle не подключен по USB!")
                    kindle_books.delete_book_usb(rel_path, drive)

                def update_ok():
                    messagebox.showinfo("Success" if self.lang == "en" else "Успех", self.tr("books_delete_ok", name=book_name))
                    self.action_refresh_books()

                self.after(0, update_ok)
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Error" if self.lang == "en" else "Ошибка", str(err)))

        threading.Thread(target=worker, daemon=True).start()

    def action_rescan_library(self):
        srv = self.ip_entry.get().strip() or DEFAULT_IP
        def worker():
            try:
                kindle_books.trigger_kindle_rescan_ssh(srv)
                self.after(0, lambda: self.set_status("Kindle display refreshed ✓" if self.lang == "en" else "Экран библиотеки Kindle пересканирован ✓", fg="#89d185"))
            except Exception as e:
                self.after(0, lambda err=e: self.set_status(f"Error: {err}" if self.lang == "en" else f"Ошибка: {err}", fg="#f48771"))
        threading.Thread(target=worker, daemon=True).start()

    def action_upload_books(self):
        title_str = "Choose book files to send to Kindle" if self.lang == "en" else "Выберите книги для отправки на Kindle"
        file_desc = "E-Books" if self.lang == "en" else "Электронные книги"
        all_desc = "All Files" if self.lang == "en" else "Все файлы"
        files = filedialog.askopenfilenames(
            title=title_str,
            filetypes=[
                (file_desc, "*.epub;*.fb2;*.mobi;*.azw;*.azw3;*.pdf;*.txt;*.docx;*.rtf;*.html;*.cbz;*.zip"),
                (all_desc, "*.*")
            ]
        )
        if not files:
            return

        mode = self.book_conn_mode.get()
        srv = self.ip_entry.get().strip() or DEFAULT_IP
        drive = self.find_kindle_drive() if mode == "usb" else None
        target_fmt = self.book_target_fmt.get()
        skip_native = self.skip_native_var.get()

        if mode == "usb" and not drive:
            messagebox.showerror("Error" if self.lang == "en" else "Ошибка", "Kindle not connected via USB!" if self.lang == "en" else "Kindle не подключен по USB!")
            return

        total_files = len(files)
        self.book_progress.config(maximum=total_files, value=0)

        def worker():
            success_count = 0
            for idx, filepath in enumerate(files, start=1):
                fname = os.path.basename(filepath)
                ext = os.path.splitext(fname)[1].lower()

                self.after(0, lambda i=idx, f=fname: (
                    self.book_progress.config(value=i - 0.5),
                    self.book_log_lbl.config(text=f"[{i}/{total_files}] Processing '{f}'..." if self.lang == "en" else f"[{i}/{total_files}] Обработка '{f}'...", fg="#005a9e")
                ))

                try:
                    need_convert = True
                    if skip_native and ext in kindle_books.KINDLE_NATIVE_EXTS:
                        need_convert = False

                    if need_convert:
                        def conv_progress(msg):
                            self.after(0, lambda m=msg: self.book_log_lbl.config(text=m, fg="#333333"))
                        upload_file = kindle_books.convert_book(filepath, target_format=target_fmt, progress_callback=conv_progress, lang=self.lang)
                    else:
                        upload_file = filepath

                    def send_progress(msg, pct):
                        self.after(0, lambda m=msg: self.book_log_lbl.config(text=m, fg="#006400"))

                    if mode == "wifi":
                        kindle_books.send_book_wifi(upload_file, server=srv, progress_callback=send_progress, lang=self.lang)
                    else:
                        kindle_books.send_book_usb(upload_file, drive_path=drive)

                    success_count += 1
                    self.after(0, lambda i=idx: self.book_progress.config(value=i))

                except Exception as e:
                    self.after(0, lambda f=fname, err=e: self.book_log_lbl.config(text=f"Error '{f}': {err}" if self.lang == "en" else f"Ошибка '{f}': {err}", fg="#c9302c"))
                    time.sleep(2)

            self.after(0, lambda: (
                self.book_progress.config(value=total_files),
                self.book_log_lbl.config(text=self.tr("books_sent_success", count=success_count), fg="#006400"),
                self.set_status(f"Uploaded {success_count} books" if self.lang == "en" else f"Книги успешно отправлены ({success_count} шт.)"),
                self.action_refresh_books()
            ))

        threading.Thread(target=worker, daemon=True).start()

    def on_closing(self):
        self._stop_active_worker()
        self.destroy()


if __name__ == "__main__":
    app = KindleStudioApp()
    app.mainloop()
