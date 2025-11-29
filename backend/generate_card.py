from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# 1. 抓取這個腳本的「絕對路徑」，確保不會因為相對路徑出錯
SCRIPT_PATH = Path(__file__).resolve()

# 2. 取得腳本所在的資料夾 (即 backend)
BACKEND_DIR = SCRIPT_PATH.parent

# 3. 往上一層取得專案根目錄 (即 grandma-card-generator)
PROJECT_ROOT = BACKEND_DIR.parent

# 4. 組合出正確的圖片路徑
BACKGROUND_PATH = PROJECT_ROOT / "frontend" / \
    "public" / "backgrounds" / "morning_1.jpg"

OUTPUT = "output/elder_card.png"
TEXT = "早安 ☀\n願今天的你\n身體健康、心情美好"


def main():
    Path("output").mkdir(exist_ok=True)

    bg = Image.open(BACKGROUND_PATH).convert("RGBA")
    w, h = bg.size

    # 文字圖層
    txt_layer = Image.new("RGBA", bg.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    # 字體（請換成你系統有的中文字體檔）
    font = ImageFont.truetype("edukai-5.0.ttf", size=int(w / 12))

    # 多行處理
    lines = TEXT.split("\n")
    line_height = font.size * 1.4
    center_y = h / 2
    start_y = center_y - (len(lines) - 1) * line_height / 2

    # 先畫白色外框
    for line_index, line in enumerate(lines):
        y = start_y + line_index * line_height
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (w - line_w) / 2

        # 外框效果：多次偏移
        for dx in [-3, 3]:
            for dy in [-3, 3]:
                draw.text((x + dx, y + dy), line, font=font,
                          fill=(255, 255, 255, 255))

        # 文字本體（先單色，之後再玩漸層）
        draw.text((x, y), line, font=font, fill=(255, 0, 0, 255))

    out = Image.alpha_composite(bg, txt_layer)
    out.save(OUTPUT)


if __name__ == "__main__":
    main()
