import os
import sys
import datetime
import requests
from PIL import Image, ImageDraw, ImageFont

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def load_api_key():
    env_key = os.environ.get("POLZA_API_KEY", "").strip()
    if env_key:
        return env_key
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("api_key", "").strip()
        except Exception:
            pass
    return ""

DEFAULT_API_KEY = load_api_key()
DEFAULT_MODEL = "z-ai/glm-5.3-flash"
API_URL = "https://api.polza.ai/v1/chat/completions"

X_RES = 600
Y_RES = 800

def get_font(size, bold=False, mono=False):
    win_fonts = "C:/Windows/Fonts"
    if mono:
        candidates = [os.path.join(win_fonts, "consola.ttf")]
    elif bold:
        candidates = [os.path.join(win_fonts, "segoeuib.ttf"), os.path.join(win_fonts, "arialbd.ttf")]
    else:
        candidates = [os.path.join(win_fonts, "segoeui.ttf"), os.path.join(win_fonts, "arial.ttf")]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()

def ask_ai(prompt, api_key=DEFAULT_API_KEY, model=DEFAULT_MODEL, system_prompt="Ты полезный, умный ассистент. Отвечай структурированно, емко и по существу, используй списки и абзацы."):
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    resp = requests.post(API_URL, json=payload, headers=headers, timeout=25)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()

def wrap_text(text, font, max_width):
    lines = []
    dummy = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy)
    
    paragraphs = text.split("\n")
    for para in paragraphs:
        para = para.strip()
        if not para:
            lines.append("")
            continue
        
        words = para.split(" ")
        cur_line = ""
        for word in words:
            test_line = f"{cur_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                cur_line = test_line
            else:
                if cur_line:
                    lines.append(cur_line)
                cur_line = word
        if cur_line:
            lines.append(cur_line)
    return lines

def render_ai_pages(prompt, response_text, landscape=False, max_lines_per_page=19):
    w = Y_RES if landscape else X_RES
    h = X_RES if landscape else Y_RES
    
    font_body = get_font(18, bold=False)
    max_w = w - 70
    lines = wrap_text(response_text, font_body, max_w)
    
    pages_lines = []
    cur_page = []
    for line in lines:
        cur_page.append(line)
        if len(cur_page) >= max_lines_per_page:
            pages_lines.append(cur_page)
            cur_page = []
    if cur_page or not pages_lines:
        pages_lines.append(cur_page)
        
    pages_images = []
    total_pages = len(pages_lines)
    
    for page_idx, plines in enumerate(pages_lines):
        img = Image.new("RGB", (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        f_head = get_font(21, bold=True)
        f_sub = get_font(12, bold=False)
        f_page = get_font(13, bold=True)
        f_body = get_font(18, bold=False)
        
        # Header banner
        draw.rectangle([0, 0, w, 52], fill=(0, 0, 0))
        draw.text((25, 12), "🤖 KINDLE AI ASSISTANT", fill=(255, 255, 255), font=f_head)
        now_str = datetime.datetime.now().strftime("%H:%M")
        draw.text((w - 85, 17), now_str, fill=(255, 255, 255), font=f_sub)
        
        # User Prompt Bubble / Bar
        prompt_disp = (prompt[:65] + "...") if len(prompt) > 68 else prompt
        draw.rectangle([25, 65, w - 25, 102], fill=(245, 245, 245), outline=(210, 210, 210), width=1)
        draw.text((36, 74), f"В: «{prompt_disp}»", fill=(30, 30, 30), font=get_font(15, bold=True))
        
        # AI Answer Text
        y = 118
        line_height = 27
        for line in plines:
            if not line:
                y += 10
                continue
            if line.startswith("- ") or line.startswith("* "):
                draw.text((32, y), "•", fill=(0, 0, 0), font=f_body)
                draw.text((50, y), line[2:], fill=(0, 0, 0), font=f_body)
            elif line.startswith("#"):
                clean = line.lstrip("#").strip()
                draw.text((32, y), clean, fill=(0, 0, 0), font=get_font(18, bold=True))
            else:
                draw.text((32, y), line, fill=(0, 0, 0), font=f_body)
            y += line_height
            
        # Footer
        draw.rectangle([0, h - 34, w, h], fill=(240, 240, 240))
        draw.text((25, h - 24), "GLM-5.3 Flash • polza.ai", fill=(100, 100, 100), font=f_sub)
        draw.text((w - 145, h - 24), f"Страница {page_idx + 1} из {total_pages}", fill=(40, 40, 40), font=f_page)
        
        pages_images.append(img)
        
    return pages_images

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = "Привет! Расскажи кратко, в чем главные преимущества экранов E-Ink?"
    
    print(f"Запрос: {q}")
    ans = ask_ai(q)
    print("Ответ:\n", ans)
    imgs = render_ai_pages(q, ans)
    imgs[0].save("test_ai_cli.png")
    print(f"Создано страниц: {len(imgs)}. Сохранено в test_ai_cli.png")
