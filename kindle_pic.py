#!/usr/bin/env python3
"""Вывод картинок на Kindle Keyboard (600x800) через eips."""

import argparse
import os
import subprocess
import sys
from PIL import Image

KINDLE_W = 600
KINDLE_H = 800
KINDLE_USER = "root"
REMOTE_PATH = "/tmp/root/display.png"
LOCAL_TMP = "display_local.png"


def prepare_image(path, rotate=0, crop=False, fit="contain", invert=False):
    img = Image.open(path)
    if rotate:
        img = img.rotate(-90 * rotate, expand=True)
    if img.mode != "L":
        img = img.convert("L")
    if invert:
        img = Image.eval(img, lambda x: 255 - x)

    if crop:
        # Обрезать под пропорции экрана (заполнить всё)
        target_ratio = KINDLE_W / KINDLE_H
        w, h = img.size
        ratio = w / h
        if ratio > target_ratio:
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))
        img = img.resize((KINDLE_W, KINDLE_H), Image.LANCZOS)
    else:
        # Вписать целиком (contain), фон — белый
        img.thumbnail((KINDLE_W, KINDLE_H), Image.LANCZOS)
        canvas = Image.new("L", (KINDLE_W, KINDLE_H), 255)
        x = (KINDLE_W - img.width) // 2
        y = (KINDLE_H - img.height) // 2
        canvas.paste(img, (x, y))
        img = canvas

    return img


def send_and_show(img, host):
    img.save(LOCAL_TMP, "PNG", optimize=True)

    # Копируем на Kindle
    scp = f"scp {LOCAL_TMP} {KINDLE_USER}@{host}:{REMOTE_PATH}"
    print(f"[scp] {scp}")
    subprocess.run(scp, shell=True, check=True)

    # Показываем
    ssh = f"ssh {KINDLE_USER}@{host} /usr/sbin/eips -g {REMOTE_PATH}"
    print(f"[eips] {ssh}")
    subprocess.run(ssh, shell=True, check=True)

    os.remove(LOCAL_TMP)
    print("Готово.")


def main():
    p = argparse.ArgumentParser(description="Вывод картинки на Kindle Keyboard")
    p.add_argument("image", help="путь к картинке")
    p.add_argument("host", help="IP Kindle, напр. 192.168.31.78")
    p.add_argument("--rotate", type=int, default=0, choices=[0, 1, 2, 3],
                   help="поворот: 0=0°, 1=90°, 2=180°, 3=270°")
    p.add_argument("--crop", action="store_true",
                   help="обрезать под пропорции экрана (заполнить всё)")
    p.add_argument("--invert", action="store_true",
                   help="инвертировать цвета")
    args = p.parse_args()

    if not os.path.isfile(args.image):
        sys.exit(f"Файл не найден: {args.image}")

    img = prepare_image(args.image, args.rotate, args.crop, invert=args.invert)
    send_and_show(img, args.host)


if __name__ == "__main__":
    main()