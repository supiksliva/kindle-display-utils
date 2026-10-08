"""
kindle_books.py - Book Management, Universal Conversion, and Wi-Fi Server for Amazon Kindle.

Features:
- Universal book conversion via Calibre ebook-convert (.epub, .fb2, .fb2.zip, .docx, .html -> .mobi / .azw3)
- Wi-Fi book synchronization with Kindle over SSH/SCP (/mnt/us/documents)
- USB book synchronization (local drive /documents)
- Direct inspection and listing of books currently stored on Kindle
- Remote deletion of books and their .sdr metadata folders
- Automatic Kindle library indexing rescan (lipc-set-prop)
- Built-in lightweight HTTP Book Server for Kindle browser and mobile uploads
"""

import os
import sys
import time
import json
import shutil
import socket
import tempfile
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import email.parser

DEFAULT_IP = "192.168.31.78"
SSH_KEY = os.path.expanduser(r"~/.ssh/kindle_key")
SSH_OPTS = f"-i {SSH_KEY} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=4"

SUPPORTED_INPUT_EXTS = {
    ".epub", ".fb2", ".mobi", ".azw", ".azw3", ".pdf", ".txt",
    ".docx", ".doc", ".rtf", ".html", ".htm", ".cbz", ".cbr", ".prc"
}

KINDLE_NATIVE_EXTS = {".mobi", ".azw", ".azw3", ".pdf", ".txt", ".prc"}

LIBRARY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "library")
os.makedirs(LIBRARY_DIR, exist_ok=True)


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def find_calibre_converter():
    """Detects Calibre ebook-convert binary."""
    p = shutil.which("ebook-convert")
    if p and os.path.exists(p):
        return p
    candidates = [
        r"C:\Program Files\Calibre2\ebook-convert.exe",
        r"C:\Program Files (x86)\Calibre2\ebook-convert.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Calibre2\ebook-convert.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def format_size(bytes_num):
    if bytes_num < 1024:
        return f"{bytes_num} Б"
    elif bytes_num < 1024 * 1024:
        return f"{bytes_num / 1024:.1f} КБ"
    else:
        return f"{bytes_num / (1024 * 1024):.1f} МБ"


def convert_book(input_path, target_format="mobi", progress_callback=None):
    """
    Converts any supported e-book format into target_format (mobi / azw3).
    Returns path to converted file in a temp or library directory.
    """
    ext = os.path.splitext(input_path)[1].lower()
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    # If already target format, no conversion needed
    if ext == f".{target_format.lower()}":
        return input_path

    converter = find_calibre_converter()
    if not converter:
        raise RuntimeError(
            "Calibre (ebook-convert) не найден в системе!\n"
            "Установите Calibre с сайта calibre-ebook.com для конвертации форматов .epub, .fb2 и др."
        )

    out_ext = f".{target_format.lower()}"
    out_dir = os.path.join(tempfile.gettempdir(), "kindle_studio_converted")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{base_name}{out_ext}")

    if progress_callback:
        progress_callback(f"Конвертация {os.path.basename(input_path)} -> {target_format.upper()}...")

    cmd = [
        converter,
        input_path,
        out_path,
        "--output-profile", "kindle"
    ]

    # For MOBI, specify standard compatible mobi file type
    if target_format.lower() == "mobi":
        cmd.extend(["--mobi-file-type", "old"])

    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or "Неизвестная ошибка Calibre"
        raise RuntimeError(f"Ошибка конвертации Calibre:\n{err[:500]}")

    if not os.path.exists(out_path):
        raise RuntimeError("Файл не был создан конвертером.")

    return out_path


# ==============================================================================
# KINDLE DOCUMENTS LISTING & INSPECTION
# ==============================================================================

def get_ssh_target(server):
    if not server:
        server = DEFAULT_IP
    if "@" not in server:
        return f"root@{server}"
    return server


def list_kindle_books_ssh(server=DEFAULT_IP):
    """
    Inspects /mnt/us/documents on Kindle over SSH.
    Returns list of book dictionaries.
    """
    ssh_target = get_ssh_target(server)
    # Using find to get all files in /mnt/us/documents, ignoring hidden files and .sdr dirs
    remote_cmd = (
        "find /mnt/us/documents -maxdepth 3 -type f "
        "! -path '*/.*' ! -path '*/*.sdr*' "
        "-exec ls -l --full-time {} + 2>/dev/null || "
        "find /mnt/us/documents -maxdepth 3 -type f "
        "! -path '*/.*' ! -path '*/*.sdr*' "
        "-exec ls -l {} +"
    )
    cmd = f'ssh {SSH_OPTS} {ssh_target} "{remote_cmd}"'
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, errors="replace", timeout=8)
    
    if res.returncode != 0:
        err = res.stderr.strip() or "Kindle не отвечает по Wi-Fi"
        raise ConnectionError(f"Ошибка SSH подключения к {server}: {err}")

    books = []
    lines = res.stdout.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("total"):
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        
        # In `ls -l`, file size is field 4 (0-indexed)
        try:
            size_bytes = int(parts[4])
        except ValueError:
            continue

        # File path is everything from field 8 onward
        # Example: -rw-r--r-- 1 root root 1234567 2026-10-08 21:00:00 /mnt/us/documents/Book.mobi
        # or:      -rw-r--r-- 1 root root 1234567 Oct 8 21:00 /mnt/us/documents/Book.mobi
        file_path = None
        for i, part in enumerate(parts):
            if part.startswith("/mnt/us/documents/"):
                file_path = " ".join(parts[i:])
                break

        if not file_path:
            continue

        rel_path = file_path[len("/mnt/us/documents/"):].strip()
        filename = os.path.basename(rel_path)
        ext = os.path.splitext(filename)[1].lower()

        # Skip non-reading system files
        if ext in {".mbp", ".tan", ".asc", ".phl", ".ea", ".pdr", ".han"}:
            continue

        books.append({
            "name": filename,
            "rel_path": rel_path,
            "full_path": file_path,
            "size_bytes": size_bytes,
            "size_str": format_size(size_bytes),
            "ext": ext.replace(".", "").upper() or "ФАЙЛ",
            "source": "Wi-Fi (Kindle)"
        })

    # Sort alphabetically by name
    books.sort(key=lambda x: x["name"].lower())
    return books


def list_kindle_books_usb(drive_path):
    """
    Inspects documents directory on USB-connected Kindle drive.
    """
    docs_dir = os.path.join(drive_path, "documents")
    if not os.path.exists(docs_dir):
        return []

    books = []
    for root, dirs, files in os.walk(docs_dir):
        # Skip .sdr folders
        if ".sdr" in root.lower():
            continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in {".mbp", ".tan", ".asc", ".phl", ".ea", ".pdr", ".han"}:
                continue
            fp = os.path.join(root, f)
            try:
                sz = os.path.getsize(fp)
                rel_path = os.path.relpath(fp, docs_dir).replace("\\", "/")
                books.append({
                    "name": f,
                    "rel_path": rel_path,
                    "full_path": fp,
                    "size_bytes": sz,
                    "size_str": format_size(sz),
                    "ext": ext.replace(".", "").upper() or "ФАЙЛ",
                    "source": f"USB ({drive_path})"
                })
            except OSError:
                pass

    books.sort(key=lambda x: x["name"].lower())
    return books


# ==============================================================================
# SENDING & DELETING BOOKS
# ==============================================================================

def send_book_wifi(local_path, server=DEFAULT_IP, progress_callback=None):
    """
    Sends a book file to /mnt/us/documents/ on Kindle over Wi-Fi (SCP/SSH).
    Triggers Kindle library rescan so the book appears on the Home screen.
    """
    ssh_target = get_ssh_target(server)
    filename = os.path.basename(local_path)
    file_size = os.path.getsize(local_path)

    if progress_callback:
        progress_callback(f"Отправка на Kindle ({format_size(file_size)})...")

    # Use SCP with -O for legacy dropbear compatibility
    # Write to temp on remote or directly to documents
    remote_dest = f"/mnt/us/documents/{filename}"
    
    # We pipe via SSH cat for 100% reliable handling of Cyrillic/spaces in filenames
    cmd = f'ssh {SSH_OPTS} {ssh_target} "cat > \\"{remote_dest}\\""'
    proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    
    chunk_size = 64 * 1024
    sent_bytes = 0
    with open(local_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            proc.stdin.write(chunk)
            sent_bytes += len(chunk)
            if progress_callback and file_size > 0:
                pct = int((sent_bytes / file_size) * 100)
                progress_callback(f"Передача по Wi-Fi: {pct}% ({format_size(sent_bytes)} / {format_size(file_size)})")

    proc.stdin.close()
    proc.wait()

    if proc.returncode != 0:
        err = proc.stderr.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Ошибка передачи книги по Wi-Fi: {err or 'Сбой соединения'}")

    # Trigger Kindle library scanner
    trigger_kindle_rescan_ssh(server)
    return True


def trigger_kindle_rescan_ssh(server=DEFAULT_IP):
    """Triggers Kindle content scanner so new books appear in Home library immediately."""
    ssh_target = get_ssh_target(server)
    cmd = (
        f'ssh {SSH_OPTS} {ssh_target} '
        '"touch /mnt/us/documents; '
        'lipc-set-prop com.lab126.scanner rescan 1 >/dev/null 2>&1 || true"'
    )
    subprocess.run(cmd, shell=True, capture_output=True, timeout=4)


def delete_book_wifi(rel_path, server=DEFAULT_IP):
    """Deletes a book and its accompanying .sdr cache folder from Kindle over Wi-Fi."""
    ssh_target = get_ssh_target(server)
    remote_file = f"/mnt/us/documents/{rel_path}"
    remote_sdr = f"/mnt/us/documents/{os.path.splitext(rel_path)[0]}.sdr"
    
    cmd = f'ssh {SSH_OPTS} {ssh_target} "rm -rf \\"{remote_file}\\" \\"{remote_sdr}\\""'
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
    if res.returncode != 0:
        raise RuntimeError(f"Не удалось удалить книгу: {res.stderr.strip()}")
    
    trigger_kindle_rescan_ssh(server)
    return True


def send_book_usb(local_path, drive_path):
    """Copies a book to documents/ folder on Kindle USB drive."""
    docs_dir = os.path.join(drive_path, "documents")
    os.makedirs(docs_dir, exist_ok=True)
    dst = os.path.join(docs_dir, os.path.basename(local_path))
    shutil.copy2(local_path, dst)
    return True


def delete_book_usb(rel_path, drive_path):
    """Deletes a book from Kindle USB drive."""
    docs_dir = os.path.join(drive_path, "documents")
    target_file = os.path.join(docs_dir, rel_path)
    if os.path.exists(target_file):
        os.remove(target_file)
    sdr_folder = os.path.splitext(target_file)[0] + ".sdr"
    if os.path.exists(sdr_folder):
        shutil.rmtree(sdr_folder, ignore_errors=True)
    return True


# ==============================================================================
# BUILT-IN HTTP BOOK SERVER
# ==============================================================================

class BookServerHandler(BaseHTTPRequestHandler):
    """
    Lightweight, high-speed, E-Ink friendly HTTP book server:
    - Renders clean catalog for Kindle's Experimental Web Browser with 1-click download
    - Accepts file uploads from smartphone/browser and auto-converts + deploys to Kindle
    """
    server_controller = None

    def log_message(self, format, *args):
        # Suppress noisy standard server console logging
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.render_catalog_page()
        elif path.startswith("/download/"):
            filename = urllib.parse.unquote(path[len("/download/"):])
            filepath = os.path.join(LIBRARY_DIR, filename)
            if os.path.exists(filepath) and os.path.isfile(filepath):
                self.serve_file(filepath, filename)
            else:
                self.send_error(404, "Книга не найдена")
        else:
            self.send_error(404, "Страница не найдена")

    def do_POST(self):
        if self.path == "/upload":
            self.handle_upload()
        else:
            self.send_error(404)

    def serve_file(self, filepath, filename):
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            ".mobi": "application/x-mobipocket-ebook",
            ".azw": "application/vnd.amazon.ebook",
            ".azw3": "application/vnd.amazon.ebook",
            ".pdf": "application/pdf",
            ".txt": "text/plain; charset=utf-8",
            ".epub": "application/epub+zip"
        }
        ctype = content_types.get(ext, "application/octet-stream")

        file_size = os.path.getsize(filepath)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(file_size))
        # Quoted filename for Kindle browser download prompt
        safe_fname = urllib.parse.quote(filename)
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{safe_fname}")
        self.end_headers()

        with open(filepath, "rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def handle_upload(self):
        try:
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                self.send_error(400, "Ожидается multipart/form-data")
                return

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            # Parse with email.parser
            msg_headers = f"Content-Type: {content_type}\r\n\r\n".encode("utf-8")
            msg = email.parser.BytesParser().parsebytes(msg_headers + body)

            uploaded_files = []
            for part in msg.get_payload():
                filename = part.get_filename()
                if filename:
                    # Clean filename
                    filename = os.path.basename(filename)
                    data = part.get_payload(decode=True)
                    if data:
                        saved_path = os.path.join(LIBRARY_DIR, filename)
                        with open(saved_path, "wb") as f:
                            f.write(data)
                        uploaded_files.append((saved_path, filename))

            # Automatically convert & forward to Kindle if configured
            status_msg = "Файлы успешно загружены в библиотеку."
            if uploaded_files and self.server_controller:
                for saved_path, fname in uploaded_files:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in KINDLE_NATIVE_EXTS:
                        # Auto-convert
                        try:
                            converted = convert_book(saved_path, "mobi")
                            dest = os.path.join(LIBRARY_DIR, os.path.basename(converted))
                            if converted != dest:
                                shutil.copy2(converted, dest)
                            saved_path = dest
                        except Exception as ce:
                            status_msg = f"Загружено, но ошибка конвертации: {ce}"
                    
                    # Push to Kindle over Wi-Fi
                    if self.server_controller.auto_push_to_kindle:
                        try:
                            send_book_wifi(saved_path, self.server_controller.kindle_ip)
                            status_msg = f"Книга '{fname}' сконвертирована и отправлена на Kindle!"
                        except Exception as we:
                            status_msg = f"Сохранено в библиотеку, но не удалось отправить на Kindle: {we}"

            # Respond with HTML page
            html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Загрузка книги</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; background: #fff; color: #000; text-align: center; }}
        .box {{ border: 2px solid #000; padding: 20px; max-width: 500px; margin: 0 auto; }}
        a {{ display: inline-block; margin-top: 15px; padding: 10px 20px; background: #000; color: #fff; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="box">
        <h2>{status_msg}</h2>
        <a href="/">Вернуться в каталог</a>
    </div>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        except Exception as e:
            self.send_error(500, f"Ошибка обработки загрузки: {e}")

    def render_catalog_page(self):
        # Scan files in LIBRARY_DIR
        books = []
        if os.path.exists(LIBRARY_DIR):
            for f in os.listdir(LIBRARY_DIR):
                fp = os.path.join(LIBRARY_DIR, f)
                if os.path.isfile(fp):
                    sz = os.path.getsize(fp)
                    ext = os.path.splitext(f)[1].lower()
                    books.append({
                        "name": f,
                        "size": format_size(sz),
                        "ext": ext.replace(".", "").upper(),
                        "url": f"/download/{urllib.parse.quote(f)}"
                    })
        books.sort(key=lambda x: x["name"].lower())

        # High-contrast E-Ink optimized HTML template
        book_rows = ""
        if books:
            for b in books:
                book_rows += f"""
                <tr style="border-bottom: 1px solid #ccc;">
                    <td style="padding: 10px 6px; font-weight: bold;">{b['name']}</td>
                    <td style="padding: 10px 6px; text-align: center;">{b['ext']}</td>
                    <td style="padding: 10px 6px; text-align: right;">{b['size']}</td>
                    <td style="padding: 10px 6px; text-align: center;">
                        <a href="{b['url']}" style="background:#000; color:#fff; padding:6px 12px; text-decoration:none; font-weight:bold; border-radius:3px;">Скачать</a>
                    </td>
                </tr>"""
        else:
            book_rows = '<tr><td colspan="4" style="padding: 20px; text-align:center; color:#555;">В библиотеке пока нет книг. Загрузите книги через форму ниже.</td></tr>'

        ip = get_local_ip()
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Kindle Studio • Книжный Сервер</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            margin: 0; padding: 15px; background: #ffffff; color: #000000; line-height: 1.4;
        }}
        .header {{ border-bottom: 3px solid #000; padding-bottom: 10px; margin-bottom: 15px; }}
        h1 {{ margin: 0 0 5px 0; font-size: 22px; }}
        .sub {{ font-size: 13px; color: #444; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ background: #f0f0f0; padding: 8px; text-align: left; border-bottom: 2px solid #000; }}
        .upload-card {{
            margin-top: 25px; padding: 15px; border: 2px dashed #000; background: #fafafa;
        }}
        .btn-upload {{
            background: #000; color: #fff; border: none; padding: 8px 16px; font-size: 14px; font-weight: bold; cursor: pointer;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Kindle Studio Book Server</h1>
        <div class="sub">Локальный сервер книг • Адрес: http://{ip}:8080/ • Всего книг: {len(books)}</div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Название</th>
                <th style="text-align: center;">Формат</th>
                <th style="text-align: right;">Размер</th>
                <th style="text-align: center;">Действие</th>
            </tr>
        </thead>
        <tbody>
            {book_rows}
        </tbody>
    </table>

    <div class="upload-card">
        <h3 style="margin-top: 0;">📤 Загрузить книгу в библиотеку (с телефона или ПК)</h3>
        <p style="font-size: 12px; color: #555;">Поддерживаются форматы: EPUB, FB2, MOBI, AZW3, PDF, TXT, DOCX. Неподдерживаемые форматы будут автоматически сконвертированы в MOBI.</p>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="book" accept=".epub,.fb2,.mobi,.azw,.azw3,.pdf,.txt,.docx" required style="margin-bottom: 10px; display:block;">
            <button type="submit" class="btn-upload">Загрузить и отправить на Kindle</button>
        </form>
    </div>
</body>
</html>"""

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


class BookServerController:
    """Manages background HTTP server thread."""
    def __init__(self, port=8080, kindle_ip=DEFAULT_IP, auto_push=True):
        self.port = port
        self.kindle_ip = kindle_ip
        self.auto_push_to_kindle = auto_push
        self.server = None
        self.thread = None
        self.is_running = False

    def start(self):
        if self.is_running:
            return
        BookServerHandler.server_controller = self
        self.server = HTTPServer(("0.0.0.0", self.port), BookServerHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.is_running = True

    def stop(self):
        if not self.is_running or not self.server:
            return
        self.server.shutdown()
        self.server.server_close()
        self.server = None
        self.thread = None
        self.is_running = False
