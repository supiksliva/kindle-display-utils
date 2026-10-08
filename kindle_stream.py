import os
import sys
import time
import argparse
import subprocess
import threading
from PIL import Image, ImageOps

# Try importing mss for fast multi-monitor screen capture
try:
    import mss
except ImportError:
    mss = None

DEFAULT_IP = "192.168.31.78"
SSH_KEY = os.path.expanduser(r"~/.ssh/kindle_key")
SSH_OPTS = f"-i {SSH_KEY} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"

X_RES = 600
Y_RES = 800

def get_ssh_target(target):
    if not target:
        target = DEFAULT_IP
    if "@" not in target:
        return f"root@{target}"
    return target

def run_ssh(server, cmd):
    ssh_target = get_ssh_target(server)
    full_cmd = f"ssh {SSH_OPTS} {ssh_target} \"{cmd}\""
    return subprocess.run(full_cmd, shell=True, capture_output=True, text=True)

def transfer_and_display(img_pil, server, negative=False):
    ssh_target = get_ssh_target(server)
    tmp_local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_display.png")
    
    if negative:
        img_pil = ImageOps.invert(img_pil)
        
    img_pil.save(tmp_local, format="PNG")

    # Send to /tmp/display.png on Kindle and show via eips
    scp_cmd = f"scp {SSH_OPTS} \"{tmp_local}\" {ssh_target}:/tmp/display.png"
    subprocess.run(scp_cmd, shell=True, capture_output=True)

    ssh_cmd = f"ssh {SSH_OPTS} {ssh_target} \"/usr/sbin/eips -g /tmp/display.png\""
    subprocess.run(ssh_cmd, shell=True, capture_output=True)

    try:
        os.remove(tmp_local)
    except OSError:
        pass

def process_image(img, crop=False, rotation=0, fit_white_bg=True):
    if rotation:
        img = img.rotate(rotation * 90, expand=True)

    orig_w, orig_h = img.size
    target_ratio = X_RES / Y_RES
    img_ratio = orig_w / orig_h

    if crop:
        if img_ratio > target_ratio:
            new_h = Y_RES
            new_w = int(new_h * img_ratio)
        else:
            new_w = X_RES
            new_h = int(new_w / img_ratio)

        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - X_RES) // 2
        top = (new_h - Y_RES) // 2
        img = img.crop((left, top, left + X_RES, top + Y_RES))
    else:
        if img_ratio > target_ratio:
            new_w = X_RES
            new_h = int(X_RES / img_ratio)
        else:
            new_h = Y_RES
            new_w = int(Y_RES * img_ratio)

        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        bg_color = (255, 255, 255) if fit_white_bg else (0, 0, 0)
        bg = Image.new('RGB', (X_RES, Y_RES), bg_color)
        offset = ((X_RES - img.width) // 2, (Y_RES - img.height) // 2)
        if img.mode in ('RGBA', 'LA'):
            bg.paste(img, offset, mask=img.split()[-1])
        else:
            bg.paste(img, offset)
        img = bg

    return img.convert('L')

def clear_kindle_screen(server):
    run_ssh(server, "/usr/sbin/eips -c")
    print(f"Screen cleared on {get_ssh_target(server)}")

def send_image(path, server, crop=False, rotation=0, negative=False):
    with Image.open(path) as img:
        processed = process_image(img, crop=crop, rotation=rotation)
        transfer_and_display(processed, server, negative=negative)
    print(f"Image sent: {path} -> {get_ssh_target(server)}")

def capture_screen_stream(server, monitor_index=1, fps=1.0, crop=False, rotation=0, negative=False, stop_event=None):
    if not mss:
        print("Error: mss module is required for screen streaming (pip install mss)")
        return

    interval = 1.0 / fps if fps > 0 else 1.0
    print(f"Starting screen stream to {get_ssh_target(server)} (~{fps} FPS)... Press Ctrl+C or Stop to exit.")

    with mss.mss() as sct:
        monitors = sct.monitors
        if monitor_index < 1 or monitor_index >= len(monitors):
            target_mon = monitors[1] if len(monitors) > 1 else monitors[0]
        else:
            target_mon = monitors[monitor_index]

        while stop_event is None or not stop_event.is_set():
            t0 = time.time()
            try:
                sct_img = sct.grab(target_mon)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                proc = process_image(img, crop=crop, rotation=rotation)
                transfer_and_display(proc, server, negative=negative)
            except Exception as e:
                print(f"Stream frame error: {e}")
                time.sleep(1)

            elapsed = time.time() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

# --- GUI Application ---
def launch_gui(default_server=DEFAULT_IP):
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.title("Kindle Display Tool")
    root.geometry("460x520")
    root.resizable(False, False)

    stream_stop_event = None
    stream_thread = None

    # IP entry
    frame_top = tk.LabelFrame(root, text="Настройки подключения", padx=10, pady=10)
    frame_top.pack(fill="x", padx=10, pady=5)

    tk.Label(frame_top, text="IP Kindle:").grid(row=0, column=0, sticky="w")
    ip_entry = tk.Entry(frame_top, width=25)
    ip_entry.insert(0, default_server)
    ip_entry.grid(row=0, column=1, padx=5, sticky="w")

    # Options
    frame_opts = tk.LabelFrame(root, text="Параметры изображения", padx=10, pady=10)
    frame_opts.pack(fill="x", padx=10, pady=5)

    crop_var = tk.BooleanVar(value=False)
    neg_var = tk.BooleanVar(value=False)
    rot_var = tk.IntVar(value=0)

    tk.Checkbutton(frame_opts, text="Обрезать/заполнить экран (Crop)", variable=crop_var).grid(row=0, column=0, columnspan=2, sticky="w")
    tk.Checkbutton(frame_opts, text="Инвертировать цвета (Negative)", variable=neg_var).grid(row=1, column=0, columnspan=2, sticky="w")

    tk.Label(frame_opts, text="Поворот:").grid(row=2, column=0, sticky="w", pady=4)
    rot_menu = tk.OptionMenu(frame_opts, rot_var, 0, 1, 2, 3)
    rot_menu.grid(row=2, column=1, sticky="w", pady=4)
    tk.Label(frame_opts, text="(0: 0°, 1: 90°, 2: 180°, 3: 270°)").grid(row=2, column=2, sticky="w")

    # Image Sending
    frame_img = tk.LabelFrame(root, text="Отправка картинки", padx=10, pady=10)
    frame_img.pack(fill="x", padx=10, pady=5)

    lbl_status = tk.Label(root, text="Готов к работе", fg="gray")

    def on_choose_and_send():
        path = filedialog.askopenfilename(
            title="Выберите картинку",
            filetypes=[("Изображения", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp"), ("Все файлы", "*.*")]
        )
        if not path:
            return
        
        srv = ip_entry.get().strip()
        lbl_status.config(text="Отправка картинки...", fg="blue")
        root.update()

        def worker():
            try:
                send_image(path, srv, crop=crop_var.get(), rotation=rot_var.get(), negative=neg_var.get())
                lbl_status.config(text=f"Отправлено: {os.path.basename(path)}", fg="green")
            except Exception as ex:
                lbl_status.config(text=f"Ошибка: {ex}", fg="red")

        threading.Thread(target=worker, daemon=True).start()

    btn_img = tk.Button(frame_img, text="Выбрать и отправить картинку 🖼", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=on_choose_and_send)
    btn_img.pack(fill="x", pady=2)

    # Screen Stream
    frame_stream = tk.LabelFrame(root, text="Трансляция экрана ПК на Kindle", padx=10, pady=10)
    frame_stream.pack(fill="x", padx=10, pady=5)

    stream_fps_frame = tk.Frame(frame_stream)
    stream_fps_frame.pack(fill="x", pady=2)
    tk.Label(stream_fps_frame, text="Кадров/сек (FPS):").pack(side="left")
    fps_entry = tk.Entry(stream_fps_frame, width=6)
    fps_entry.insert(0, "1.0")
    fps_entry.pack(side="left", padx=5)

    btn_stream_start = tk.Button(frame_stream, text="Начать трансляцию экрана 🎥", bg="#2196F3", fg="white", font=("Arial", 9, "bold"))
    btn_stream_stop = tk.Button(frame_stream, text="Остановить трансляцию ⏹", bg="#f44336", fg="white", state="disabled")

    def start_stream():
        nonlocal stream_stop_event, stream_thread
        srv = ip_entry.get().strip()
        try:
            fps_val = float(fps_entry.get().strip())
        except ValueError:
            fps_val = 1.0

        stream_stop_event = threading.Event()
        btn_stream_start.config(state="disabled")
        btn_stream_stop.config(state="normal")
        lbl_status.config(text="Идет трансляция экрана...", fg="blue")

        def run_thread():
            capture_screen_stream(
                server=srv,
                fps=fps_val,
                crop=crop_var.get(),
                rotation=rot_var.get(),
                negative=neg_var.get(),
                stop_event=stream_stop_event
            )
            lbl_status.config(text="Трансляция остановлена", fg="black")
            btn_stream_start.config(state="normal")
            btn_stream_stop.config(state="disabled")

        stream_thread = threading.Thread(target=run_thread, daemon=True)
        stream_thread.start()

    def stop_stream():
        nonlocal stream_stop_event
        if stream_stop_event:
            stream_stop_event.set()
        lbl_status.config(text="Остановка...", fg="orange")

    btn_stream_start.config(command=start_stream)
    btn_stream_stop.config(command=stop_stream)

    btn_stream_start.pack(fill="x", pady=2)
    btn_stream_stop.pack(fill="x", pady=2)

    # Clear screen button
    def do_clear():
        srv = ip_entry.get().strip()
        def worker():
            clear_kindle_screen(srv)
            lbl_status.config(text="Экран очищен", fg="green")
        threading.Thread(target=worker, daemon=True).start()

    btn_clear = tk.Button(root, text="Очистить экран Kindle (Erase) ⌫", command=do_clear)
    btn_clear.pack(fill="x", padx=10, pady=5)

    lbl_status.pack(pady=5)
    root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kindle Display & Screen Stream Tool")
    parser.add_argument("input_image", nargs="?", default=None, help="Path to image file (optional, if empty opens GUI)")
    parser.add_argument("ssh_server", nargs="?", default=DEFAULT_IP, help="Kindle IP or user@IP")
    parser.add_argument("--gui", action="store_true", help="Launch Graphical Interface")
    parser.add_argument("--stream", action="store_true", help="Stream PC screen to Kindle")
    parser.add_argument("--clear", action="store_true", help="Clear Kindle screen")
    parser.add_argument("--fps", type=float, default=1.0, help="Stream FPS (default 1.0)")
    parser.add_argument("--monitor", type=int, default=1, help="Monitor index to stream (default 1)")
    parser.add_argument("-c", "--crop", action="store_true", help="Crop image to fill screen")
    parser.add_argument("-n", "--negative", action="store_true", help="Invert colors")
    parser.add_argument("-r", "--rotate", type=int, choices=[0, 1, 2, 3], default=0, help="Rotate (0, 1, 2, 3)")

    args = parser.parse_args()

    if args.gui or (not args.input_image and not args.stream and not args.clear):
        launch_gui(args.ssh_server)
    elif args.clear:
        clear_kindle_screen(args.ssh_server)
    elif args.stream:
        capture_screen_stream(
            server=args.ssh_server,
            monitor_index=args.monitor,
            fps=args.fps,
            crop=args.crop,
            rotation=args.rotate,
            negative=args.negative
        )
    elif args.input_image:
        send_image(
            path=args.input_image,
            server=args.ssh_server,
            crop=args.crop,
            rotation=args.rotate,
            negative=args.negative
        )
