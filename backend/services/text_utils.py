import re
from typing import List

# 簡單移除 emoji，用來畫在圖片上的文字
# （瀏覽器顯示文字時還是有 emoji，因為那邊用的是原始文字）
EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF]",
    flags=re.UNICODE,
)


def remove_emoji(text: str) -> str:
    """移除字串中的 emoji，避免繪製文字時字型畫不出來。"""
    return EMOJI_PATTERN.sub("", text)


def split_text_to_lines(text: str, max_chars: int) -> List[str]:
    """很粗略地按照字數切行（中文也適用）。"""
    text = text.strip()
    if not text:
        return []
    return [text[i: i + max_chars] for i in range(0, len(text), max_chars)]


TITLE_MAX_CHARS = 10
SUBTITLE_MAX_CHARS = 12
FOOTER_MAX_CHARS = 18  # 目前不畫 footer，但保留常數方便之後擴充
