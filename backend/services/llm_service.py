import json
import os
import random
from dataclasses import dataclass
from typing import Dict, Optional
import datetime
from google import genai


@dataclass
class ElderCardText:
    title: str
    subtitle: str
    footer: str


class LLMService:
    """
    使用 Gemini API 產生長輩圖文案。
    - 有 GEMINI_API_KEY 或 GOOGLE_API_KEY 就呼叫 Gemini
    - 沒有或出錯則使用內建模板 fallback
    """

    def __init__(self) -> None:
        # 這些是預設模板，會在沒有 LLM 或錯誤時使用
        self.templates: Dict[str, ElderCardText] = {
            "morning": ElderCardText(
                title="早安 祝福滿滿",
                subtitle="新的一天記得多呼吸幾口新鮮空氣，讓心情跟著亮起來。",
                footer="把這份祝福分享給在乎的人，一起元氣滿滿迎接今天 ☀️",
            ),
            "health": ElderCardText(
                title="健康是最大的財富",
                subtitle="少熬夜、多喝水，適度活動筋骨，身體才會跟你當好朋友。",
                footer="想起好久不見的親朋好友，關心一句：最近也要記得照顧自己喔 💕",
            ),
            "life": ElderCardText(
                title="人生慢慢來也沒關係",
                subtitle="偶爾停下腳步，看看身邊的人、身邊的風景，也是種收穫。",
                footer="把這張圖傳給懂你的人，一起好好過生活 🌿",
            ),
            "festival_newyear": ElderCardText(
                title="新年快樂 福氣滿滿",
                subtitle="願你新的一年，平安順心、笑口常開，家人健康闔家團圓。",
                footer="想到誰想一起過好年，就快把祝福傳給他吧 🧧",
            ),
            "festival_christmas": ElderCardText(
                title="聖誕快樂 平安喜樂",
                subtitle="願溫暖的燈火，照亮你與家人的笑容與心。",
                footer="把這份小小的祝福傳出去，讓聖誕更有味道 🎄",
            ),
        }

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        print("[LLMService] GEMINI_API_KEY loaded:", bool(api_key))

        self.client: Optional[genai.Client] = (
            genai.Client(api_key=api_key) if api_key else None
        )

        # 可調整成你想用的模型
        # self.model_name = "gemini-2.5-flash"
        # 邏輯：先試 2.0 Flash (最新但有額度限制)，失敗就自動轉 1.5 Flash (穩定且額度高)
        self.model_candidates = [
            # "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash-lite",
            "gemini-flash-latest",
            "gemini-pro-latest",
        ]

        # 主題說明
        self.theme_descriptions: Dict[str, str] = {
            "morning": "早安、早晨開啟新的一天，溫暖打氣的祝福。",
            "health": "健康、保重身體、注意飲食作息的提醒與祝福。",
            "life": "生活感悟、人生小語，鼓勵放慢腳步、好好生活。",
            "festival_newyear": "農曆新年、新春、過年拜年祝福。",
            "festival_christmas": "聖誕節、雪、禮物、團聚氛圍的祝福。",
            "festival_common": "一般節慶祝福（例如母親節、父親節、紀念日等）。",
            "festival_lantern": "元宵節、提燈籠、吃湯圓、團圓的祝福。",
            "festival_midautumn": "中秋節、賞月、吃月餅、團圓的祝福。",
        }

        # 隨機風格（讓每次語氣有點不一樣）
        self.style_variants = [
            "溫柔關懷",
            "活力元氣",
            "俏皮幽默",
            "穩重安定",
            "溫暖療癒",
        ]

    def _get_zodiac_context(self) -> str:
        """
        計算當前年份與生肖。
        如果月份 >= 11，視為準備過明年農曆年。
        """
        now = datetime.datetime.now()
        year = now.year

        # 如果是 11, 12 月，通常大家都在求「明年」的新年祝福了
        if now.month >= 11:
            year += 1

        # 生肖對照表 (2025是蛇年，2025%12=9)
        # 餘數對應：0猴, 1雞, 2狗, 3豬, 4鼠, 5牛, 6虎, 7兔, 8龍, 9蛇, 10馬, 11羊
        zodiacs = ["猴", "雞", "狗", "豬", "鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊"]
        zodiac_char = zodiacs[year % 12]

        return f"現在是（或即將迎接）{year} 年，也就是「{zodiac_char}年」。"

    # --------- prompt 組裝 ---------

    def _build_prompt(self, theme: str, style: str) -> str:
        # 1. 取得時間與生肖資訊
        zodiac_info = self._get_zodiac_context()

        base_desc = self.theme_descriptions.get(
            theme, "一般祝福，內容溫暖、正向、適合傳給親友。"
        )

        # 先定義特殊的 Prompt 補充說明
        extra_instructions = ""

        # 針對新年主題，強制加入生肖提示
        if theme == "festival_newyear":
            theme_desc = f"{base_desc} 請注意：{zodiac_info} 文案中請務必包含該生肖的吉祥話（例如該生肖行大運），不要寫錯年份。"

        elif theme == "dark_humor":
            theme_desc = "這是一張『毒雞湯』風格的長輩圖。外表溫馨，但文字內容充滿對生活、工作、薪水的無奈與諷刺。"
            style = "極度厭世、腹黑、反諷"
            extra_instructions = """
            請撰寫讓年輕人看了會苦笑的『負能量』金句。
            範例方向：
            - 努力不一定會成功，但不努力會很輕鬆。
            - 雖然你薪水低，但是你工時長啊。
            - 跌倒了別急著站起來，先躺一下比較舒服。
            
            格式要求同樣為 JSON，Title 要像長輩圖的勸世口吻，但 Subtitle 要突然轉折成負能量。
            """
        else:
            theme_desc = base_desc

        instructions = f"""
你是一位擅長幫人寫 Line 「長輩圖」祝福文字的文案設計師。

本次風格設定：
- 主題：{theme_desc}
- 整體語氣：偏向「{style}」的感覺。
{extra_instructions}

風格要求：
- 使用臺灣常見的繁體中文用語。
- 口吻溫暖、關心，可以帶一點可愛或幽默，但不要太油膩。
- 讓長輩看到會想轉傳給朋友或家人的感覺。
- 儘量避免每次都出現以下常見句型：
  - 「又是嶄新的一天」
  - 「祝你有個順心如意的好心情」
  - 「把這份祝福分享給重要的人」
  請多變換用詞與句型，讓每一張圖的文字有明顯差異。

輸出結構：
- title：【絕對不超過 10 個字】。適合作為長輩圖主標題，語氣正向、簡潔有力。
- subtitle：【絕對不超過 12 個字】。只能是一句短語，不要寫兩句。
- footer：15 個字以內，簡短的行動呼籲。

注意：
- 一律使用繁體中文。
- 不要出現色情、暴力、仇恨或歧視內容。
- 不要使用 emoji。
- 最後「只輸出 JSON」，不要任何多餘解釋或文字。
JSON 格式如下：

{{
  "title": "...",
  "subtitle": "...",
  "footer": "..."
}}
        """.strip()

        few_shot = """
以下是幾個示例，僅供你學習風格，不要直接複製：

[範例 1：morning]
{
  "title": "早安 祝福滿滿",
  "subtitle": "深呼吸，讓心情亮起來。",
  "footer": "分享給你重要的人"
}

[範例 2：health]
{
  "title": "健康是最大的財富",
  "subtitle": "多喝水，身體才會好。",
  "footer": "記得照顧自己喔"
}

現在請你依照「主題說明」與這些示例的感覺，產生一組全新的 JSON。
        """.strip()

        full_prompt = instructions + "\n\n" + few_shot
        return full_prompt

    # --------- fallback ---------

    def _fallback(self, theme: str) -> ElderCardText:
        if theme in self.templates:
            return self.templates[theme]

        return ElderCardText(
            title="送上暖暖的祝福",
            subtitle="別忘了幫自己留一點喘口氣的時間。",
            footer="傳給你在乎的人吧",
        )

    # --------- 對外主方法 ---------

    def generate_text(self, theme: str) -> ElderCardText:
        """
        對外呼叫：
        - 優先用 Gemini 產生 JSON 再 parse
        - 失敗就回到模板
        """
        if not self.client:
            return self._fallback(theme)

        style = random.choice(self.style_variants)  # 每次隨機一種風格
        prompt = self._build_prompt(theme, style)

        if theme == "broken_egg":
            return ElderCardText(
                title="誰說這壞了？",
                subtitle="這系統可真是太棒了！",
                footer="—— 來自何老師的邪惡梔子花計畫"
            )

        # ✅ 開始迴圈：依序嘗試每個模型
        for model_name in self.model_candidates:
            try:
                print(f"[LLMService] Trying model: {model_name}...")

                response = self.client.models.generate_content(
                    model=model_name,  # 這裡改用迴圈當下的 model_name
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "temperature": 0.9,
                        "top_p": 0.95,
                        "max_output_tokens": 2048,
                    },
                )

                raw_text = response.text.strip()
                # print(f"[LLMService] Response from {model_name}: success!")

                data = json.loads(raw_text)

                if isinstance(data, list):
                    if not data:
                        # 如果這個模型回傳空陣列，視為失敗，嘗試下一個
                        print(
                            f"[LLMService] {model_name} returned empty list, skipping.")
                        continue
                    data = data[0]

                if not isinstance(data, dict):
                    # 格式不對，嘗試下一個
                    print(
                        f"[LLMService] {model_name} returned invalid format, skipping.")
                    continue

                title = str(data.get("title", "")).strip()
                subtitle = str(data.get("subtitle", "")).strip()
                footer = str(data.get("footer", "")).strip()

                # 簡單防呆與截斷
                if len(subtitle) > 12:
                    subtitle = subtitle[:11] + "…"
                if len(title) > 10:
                    title = title[:10]
                if len(footer) > 20:
                    footer = footer[:19] + "…"

                if not title or not subtitle or not footer:
                    continue  # 欄位缺失，視為失敗，換下一個

                # 🎉 成功！直接回傳結果，結束迴圈
                return ElderCardText(title=title, subtitle=subtitle, footer=footer)

            except Exception as e:
                # 🚨 這裡捕捉錯誤 (例如 429 額度滿了)
                print(
                    f"[LLMService] Model {model_name} failed with error: {e}")
                print(f"[LLMService] Switching to next model...")
                # 繼續迴圈 (continue)，嘗試清單裡的下一個模型
                continue

        # ❌ 如果迴圈跑完了，所有模型都失敗，才使用 Fallback 模板
        print("[LLMService] All models failed. Using fallback template.")
        return self._fallback(theme)
