"""
kindle_books.py - Wireless Kindle Book Manager & Universal Converter.

Features:
- Direct listing and inspection of books on Kindle over Wi-Fi (SSH) or USB
- Universal book conversion via Calibre ebook-convert (.epub, .fb2, .docx, .txt -> .mobi / .azw3)
- Wireless deployment of books directly into /mnt/us/documents/ on Kindle
- Automatic Kindle library indexer trigger (lipc-set-prop)
- Safe book & cache (.sdr) deletion
- Clean argument-list execution without Windows cmd.exe shell interference
"""

import os
import sys
import shutil
import tempfile
import subprocess

DEFAULT_IP = "192.168.31.78"
SSH_KEY = os.path.expanduser(r"~/.ssh/kindle_key")

SUPPORTED_INPUT_EXTS = {
    ".epub", ".fb2", ".mobi", ".azw", ".azw3", ".pdf", ".txt",
    ".docx", ".doc", ".rtf", ".html", ".htm", ".cbz", ".cbr", ".prc"
}

KINDLE_NATIVE_EXTS = {".mobi", ".azw", ".azw3", ".pdf", ".txt", ".prc"}


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


def format_size(bytes_num, lang="ru"):
    if lang == "en":
        if bytes_num < 1024:
            return f"{bytes_num} B"
        elif bytes_num < 1024 * 1024:
            return f"{bytes_num / 1024:.1f} KB"
        else:
            return f"{bytes_num / (1024 * 1024):.1f} MB"
    else:
        if bytes_num < 1024:
            return f"{bytes_num} Б"
        elif bytes_num < 1024 * 1024:
            return f"{bytes_num / 1024:.1f} КБ"
        else:
            return f"{bytes_num / (1024 * 1024):.1f} МБ"


def convert_book(input_path, target_format="mobi", progress_callback=None, lang="ru"):
    """
    Converts any supported e-book format into target_format (mobi / azw3).
    Returns path to converted file in a temp directory.
    """
    ext = os.path.splitext(input_path)[1].lower()
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    if ext == f".{target_format.lower()}":
        return input_path

    converter = find_calibre_converter()
    if not converter:
        if lang == "en":
            raise RuntimeError(
                "Calibre (ebook-convert) not found!\n"
                "Install Calibre from calibre-ebook.com to convert .epub, .fb2, etc."
            )
        else:
            raise RuntimeError(
                "Calibre (ebook-convert) не найден в системе!\n"
                "Установите Calibre с сайта calibre-ebook.com для конвертации форматов .epub, .fb2 и др."
            )

    out_ext = f".{target_format.lower()}"
    out_dir = os.path.join(tempfile.gettempdir(), "kindle_studio_converted")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{base_name}{out_ext}")

    if progress_callback:
        msg = f"Converting {os.path.basename(input_path)} -> {target_format.upper()}..." if lang == "en" else f"Конвертация {os.path.basename(input_path)} -> {target_format.upper()}..."
        progress_callback(msg)

    cmd = [
        converter,
        input_path,
        out_path,
        "--output-profile", "kindle"
    ]

    if target_format.lower() == "mobi":
        cmd.extend(["--mobi-file-type", "old"])

    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or "Unknown Calibre error"
        raise RuntimeError(f"Calibre error:\n{err[:500]}")

    if not os.path.exists(out_path):
        raise RuntimeError("Converted file was not created.")

    return out_path


# ==============================================================================
# KINDLE INSPECTION & LISTING
# ==============================================================================

def get_ssh_target(server):
    if not server:
        server = DEFAULT_IP
    if "@" not in server:
        return f"root@{server}"
    return server


def parse_kindle_ls_output(output, lang="ru"):
    """
    Parses `ls -l` lines output from Kindle documents directory.
    """
    books = []
    base_prefix = "/mnt/us/documents/"
    
    for line in output.strip().splitlines():
        line = line.strip()
        if not line or not line.startswith("-"):
            continue
        parts = line.split(None, 8)
        if len(parts) < 9:
            continue
        try:
            size_bytes = int(parts[4])
        except ValueError:
            continue
        
        full_path = parts[8].strip()
        if full_path.startswith(base_prefix):
            rel_path = full_path[len(base_prefix):]
        else:
            rel_path = os.path.basename(full_path)
            
        ext = os.path.splitext(full_path)[1].lower()
        if ext in {".mbp", ".tan", ".asc", ".phl", ".ea", ".pdr", ".han", ".tmp", ".part"}:
            continue
            
        name = os.path.basename(rel_path)
        books.append({
            "name": name,
            "rel_path": rel_path,
            "full_path": full_path,
            "size_bytes": size_bytes,
            "size_str": format_size(size_bytes, lang=lang),
            "ext": ext.replace(".", "").upper() or ("FILE" if lang == "en" else "ФАЙЛ"),
            "date": f"{parts[5]} {parts[6]} {parts[7]}"
        })
        
    books.sort(key=lambda x: x["name"].lower())
    return books


def list_kindle_books_ssh(server=DEFAULT_IP, ssh_key=None, lang="ru"):
    """
    Inspects /mnt/us/documents on Kindle over SSH using direct arg list.
    """
    if not ssh_key:
        ssh_key = SSH_KEY
    ssh_target = get_ssh_target(server)

    # Standard POSIX shell loop that safely checks documents/ and subfolders,
    # skips .sdr folders, and prints ls -l for real files
    remote_sh = (
        'for f in /mnt/us/documents/* /mnt/us/documents/*/* /mnt/us/documents/*/*/*; do '
        'case "$f" in *.sdr*|*.sdr) continue ;; esac; '
        '[ -f "$f" ] && ls -l "$f"; '
        'done'
    )

    cmd_args = [
        "ssh",
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=6",
        ssh_target,
        remote_sh
    ]

    res = subprocess.run(cmd_args, capture_output=True, text=True, errors="replace", timeout=12)
    if res.returncode != 0:
        err = res.stderr.strip()
        if "timed out" in err.lower():
            if lang == "en":
                raise ConnectionError("Connection timed out. Wake your Kindle (slide power switch) to enable Wi-Fi.")
            else:
                raise ConnectionError("Таймаут подключения. Разбудите читалку (сдвиньте ползунок включения), чтобы активировать Wi-Fi.")
        if lang == "en":
            raise ConnectionError(f"SSH error ({server}): {err or 'Kindle is unreachable'}")
        else:
            raise ConnectionError(f"Ошибка SSH ({server}): {err or 'Kindle не отвечает по сети'}")

    return parse_kindle_ls_output(res.stdout, lang=lang)


def list_kindle_books_usb(drive_path, lang="ru"):
    """
    Inspects documents directory on USB-connected Kindle drive.
    """
    docs_dir = os.path.join(drive_path, "documents")
    if not os.path.exists(docs_dir):
        return []

    books = []
    for root, dirs, files in os.walk(docs_dir):
        if ".sdr" in root.lower():
            continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in {".mbp", ".tan", ".asc", ".phl", ".ea", ".pdr", ".han", ".tmp", ".part"}:
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
                    "size_str": format_size(sz, lang=lang),
                    "ext": ext.replace(".", "").upper() or ("FILE" if lang == "en" else "ФАЙЛ"),
                    "date": ""
                })
            except OSError:
                pass

    books.sort(key=lambda x: x["name"].lower())
    return books


# ==============================================================================
# SENDING & DELETING BOOKS
# ==============================================================================

def send_book_wifi(local_path, server=DEFAULT_IP, ssh_key=None, progress_callback=None, lang="ru"):
    """
    Transfers a book to /mnt/us/documents/ on Kindle via SSH streaming.
    """
    if not ssh_key:
        ssh_key = SSH_KEY
    ssh_target = get_ssh_target(server)
    filename = os.path.basename(local_path)
    file_size = os.path.getsize(local_path)

    remote_dest = f"/mnt/us/documents/{filename}"

    cmd_args = [
        "ssh",
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=6",
        ssh_target,
        f'cat > "{remote_dest}"'
    ]

    proc = subprocess.Popen(cmd_args, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

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
                msg = (
                    f"Wi-Fi Transfer: {pct}% ({format_size(sent_bytes, lang=lang)} / {format_size(file_size, lang=lang)})"
                    if lang == "en" else
                    f"Передача по Wi-Fi: {pct}% ({format_size(sent_bytes, lang=lang)} / {format_size(file_size, lang=lang)})"
                )
                progress_callback(msg, pct)

    proc.stdin.close()
    proc.wait()

    if proc.returncode != 0:
        err = proc.stderr.read().decode("utf-8", errors="replace").strip()
        err_msg = f"Transfer failed: {err or 'Connection dropped'}" if lang == "en" else f"Ошибка передачи книги: {err or 'Сбой соединения'}"
        raise RuntimeError(err_msg)

    trigger_kindle_rescan_ssh(server, ssh_key=ssh_key)
    return True


def trigger_kindle_rescan_ssh(server=DEFAULT_IP, ssh_key=None):
    """Triggers Kindle content scanner so new books appear in Home library immediately."""
    if not ssh_key:
        ssh_key = SSH_KEY
    ssh_target = get_ssh_target(server)
    cmd_args = [
        "ssh",
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=4",
        ssh_target,
        'touch /mnt/us/documents; lipc-set-prop com.lab126.scanner rescan 1 >/dev/null 2>&1 || true'
    ]
    subprocess.run(cmd_args, capture_output=True, timeout=5)


def delete_book_wifi(rel_path, server=DEFAULT_IP, ssh_key=None, lang="ru"):
    """Deletes a book and its accompanying .sdr cache folder from Kindle over Wi-Fi."""
    if not ssh_key:
        ssh_key = SSH_KEY
    ssh_target = get_ssh_target(server)
    remote_file = f"/mnt/us/documents/{rel_path}"
    remote_sdr = f"/mnt/us/documents/{os.path.splitext(rel_path)[0]}.sdr"

    cmd_args = [
        "ssh",
        "-i", ssh_key,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=6",
        ssh_target,
        f'rm -rf "{remote_file}" "{remote_sdr}"'
    ]
    res = subprocess.run(cmd_args, capture_output=True, text=True, errors="replace", timeout=8)
    if res.returncode != 0:
        err_msg = f"Failed to delete book: {res.stderr.strip()}" if lang == "en" else f"Не удалось удалить книгу: {res.stderr.strip()}"
        raise RuntimeError(err_msg)

    trigger_kindle_rescan_ssh(server, ssh_key=ssh_key)
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
