import os
from pathlib import Path
import time
from datetime import datetime, date
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# ... 原有的 imports ...
import base64
import uuid
import sys
from fastapi import Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles  # 記得引入這個

# LINE SDK
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

from services.compose_service import ComposeService
from services.llm_service import LLMService, ElderCardText

# 先載入 .env
load_dotenv()

# ===== 基本設定 =====

BASE_DIR = Path(__file__).resolve().parent
BACKGROUND_BASE_DIR = BASE_DIR / "assets" / "backgrounds"
FONT_PATH = str(BASE_DIR / "assets" / "fonts" / "edukai-5.0.ttf")

# 主題
ALLOWED_THEMES = {
    "morning",
    "health",
    "life",
    "festival_newyear",
    "festival_christmas",
    "festival_common",
    "festival_lantern",
    "festival_midautumn",
}

# 排版風格（前端也會用到這組字串）
ALLOWED_LAYOUTS = {
    "auto",         # 交給後端隨機
    "center",       # 經典置中
    "top_bottom",   # 上下分佈
    "left_block",   # 左側文字
    "diagonal",     # 斜斜文字
    "vertical",     # 直書標題
}

# 格式: { "user_id": timestamp }，記錄上次使用的時間
USER_LAST_ACCESS = {}

# 格式: { "2023-10-27": { "user_id": count } }，記錄每天的使用次數
DAILY_USAGE_STATS = {}

# ===== [新增] 設定限制參數 =====
COOLDOWN_SECONDS = 15  # 冷卻時間：每 15 秒才能做一張 (防連點)
DAILY_LIMIT_PER_USER = 20  # 每日上限：每人每天只能做 20 張 (防大戶)

# ===== FastAPI App =====

app = FastAPI(title="Elder Card Generator API")

# ===== LINE Bot 設定 =====
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
app_base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")

# 檢查設定是否存在
if not channel_access_token or not channel_secret:
    print("Warning: LINE Bot keys not found in .env")

configuration = Configuration(access_token=channel_access_token)
async_api_client = ApiClient(configuration)
line_bot_api = MessagingApi(async_api_client)
handler = WebhookHandler(channel_secret)

# ===== 靜態檔案設定 (解決圖片 URL 問題) =====
# 確保 static 資料夾存在
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# 掛載 static 目錄，這樣 https://domain/static/xxx.png 才能被訪問
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://grandma-card-generator.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Services =====

compose_service = ComposeService(
    background_base_dir=str(BACKGROUND_BASE_DIR),
    font_path=FONT_PATH or None,
)

llm_service = LLMService()

# ===== Pydantic Models =====


class GenerateRequest(BaseModel):
    theme: str
    # 新增 layout，預設 None，代表用 auto
    layout: str | None = None


class ElderCardTextModel(BaseModel):
    title: str
    subtitle: str
    footer: str


class GenerateResponse(BaseModel):
    theme: str
    layout: str
    text: ElderCardTextModel
    image_base64: str


# ===== Routes =====

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Elder Card API is running"}


@app.get("/api/config")
async def get_config():
    """
    給前端用的設定查詢：有哪些 theme / layout 可以選
    """
    return {
        "themes": sorted(list(ALLOWED_THEMES)),
        "layouts": sorted(list(ALLOWED_LAYOUTS)),
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_card(req: GenerateRequest):
    theme = req.theme
    layout = req.layout or "auto"

    if theme not in ALLOWED_THEMES:
        raise HTTPException(status_code=400, detail=f"Unknown theme: {theme}")

    if layout not in ALLOWED_LAYOUTS:
        raise HTTPException(
            status_code=400, detail=f"Unknown layout: {layout}")

    theme_dir = BACKGROUND_BASE_DIR / theme
    if not theme_dir.exists():
        raise HTTPException(
            status_code=400,
            detail=f"No background directory for theme: {theme}",
        )

    # 1) 先用 LLM 生文字
    elder_text: ElderCardText = llm_service.generate_text(theme)

    # 2) 合成圖片（layout == auto 就交給 ComposeService 自己隨機）
    image_base64 = compose_service.compose_image(
        theme=theme,
        title=elder_text.title,
        subtitle=elder_text.subtitle,
        footer=elder_text.footer,
        layout=None if layout == "auto" else layout,
    )

    return GenerateResponse(
        theme=theme,
        layout=layout,
        text=ElderCardTextModel(
            title=elder_text.title,
            subtitle=elder_text.subtitle,
            footer=elder_text.footer,
        ),
        image_base64=image_base64,
    )


@app.post("/callback")
async def callback(request: Request):
    # 取得 X-Line-Signature header
    signature = request.headers.get("X-Line-Signature", "")

    # 取得 request body
    body = await request.body()
    body_str = body.decode("utf-8")

    try:
        # 驗證簽章並交給 handler 處理
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    """
    當收到文字訊息時觸發
    """
    user_text = event.message.text
    user_id = event.source.user_id

    user_text_lower = user_text.lower()

    # 簡單過濾：如果使用者輸入太短，可能不是要產生長輩圖，可以忽略或設為預設主題
    # 這裡假設使用者輸入任何文字都視為 Prompt 或主題
    # 為了簡化，我們嘗試把 user_text 當作 theme，如果不在 ALLOWED_THEMES 裡，就預設用 'life' 或 'morning'

    keywords = ["健康", "生活格言", "早安", "節慶", "新年", "聖誕節",
                "壞了", "爛", "老了", "失敗", "地獄", "負能量", "厭世", "開", "炸", "retro",
                "bug", "code", "coding", "debug", "工程師", "程式",
                "雪", "下雪", "躺平", "不想努力", "rebel"]

    # 檢查 user_text 是否包含任一關鍵字
    is_trigger = any(k in user_text_lower for k in keywords)

    # 或是針對你的 ALLOWED_THEMES 檢查
    is_theme_command = user_text in ALLOWED_THEMES

    if not (is_trigger or is_theme_command):
        # 如果不是關鍵字，也不是指令，直接結束函式
        # 這樣就不會呼叫 llm_service，完全不消耗 Google API
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(
                    text=f"關鍵字錯誤，找不到這個指令。")]
            )
        )
        return

    # A. 檢查冷卻時間 (Cooldown)
    current_time = time.time()
    last_time = USER_LAST_ACCESS.get(user_id, 0)

    if current_time - last_time < COOLDOWN_SECONDS:
        # 如果距離上次請求還不到冷卻時間
        remaining = int(COOLDOWN_SECONDS - (current_time - last_time))
        print(f"User {user_id} is ratelimited. Wait {remaining}s.")

        # 回覆使用者「太快了」，直接 return，不呼叫 Google API
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(
                    text=f"製作太快囉！機器人正在喘氣 🥵\n請再等 {remaining} 秒後再試。")]
            )
        )
        return  # [重要] 直接結束，不往下執行

    # B. 檢查每日額度 (Daily Quota)
    today_str = date.today().isoformat()  # 取得 "2023-12-10" 格式

    # 初始化今天的計數器 (如果換日了，會自動產生新的 dict)
    if today_str not in DAILY_USAGE_STATS:
        DAILY_USAGE_STATS.clear()  # 清除舊資料釋放記憶體
        DAILY_USAGE_STATS[today_str] = {}

    user_today_count = DAILY_USAGE_STATS[today_str].get(user_id, 0)

    if user_today_count >= DAILY_LIMIT_PER_USER:
        print(f"User {user_id} hit daily limit.")
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(
                    text=f"您今天的製作額度已達上限 ({DAILY_LIMIT_PER_USER} 張) 🛑\n請明天再來玩！")]
            )
        )
        return  # [重要] 直接結束

    # ===== [新增] 防護機制結束 =====

    # 如果都通過了，更新狀態
    USER_LAST_ACCESS[user_id] = current_time
    DAILY_USAGE_STATS[today_str][user_id] = user_today_count + 1

    target_theme = "life"  # 預設

    # 簡單的關鍵字對應 (您可以做得更複雜)
    if any(k in user_text for k in ["壞了", "爛", "老了", "失敗"]):
        target_theme = "broken_egg"
    # 2. 彩蛋 B：地獄梗
    elif any(k in user_text for k in ["地獄", "負能量", "厭世", "煩"]):
        target_theme = "dark_humor"
    elif any(k in user_text.lower() for k in ["bug", "code", "coding", "debug", "工程師", "程式"]):
        target_theme = "programmer"
    elif any(k in user_text_lower for k in ["雪", "下雪"]):
        target_theme = "festival_christmas"
    elif any(k in user_text_lower for k in ["躺平", "不想努力", "rebel"]):
        target_theme = "rebel"
    elif "早" in user_text:
        target_theme = "morning"
    elif "健康" in user_text:
        target_theme = "health"
    elif "生活格言" in user_text:
        target_theme = "life"
    elif "節慶" in user_text:
        target_theme = "festival_common"
    elif "聖誕節" in user_text:
        target_theme = "festival_christmas"
    elif "新年" in user_text:
        target_theme = "festival_newyear"

    if any(k in user_text for k in ["開", "炸", "retro"]):
        target_theme += "_retro"

    clean_theme = target_theme.replace("_retro", "")

    # [重要] 這裡要放行特殊彩蛋主題，避免被 ALLOWED_THEMES 擋住
    # 如果 target_theme 是彩蛋，我們就不檢查 ALLOWED_THEMES
    if target_theme not in ["broken_egg", "dark_humor"] and target_theme not in ALLOWED_THEMES:
        # 如果不是彩蛋，也不是允許的主題，才做過濾 (原本的邏輯)
        pass

    try:
        # 1. 呼叫 LLM 服務 (同步呼叫)
        elder_text = llm_service.generate_text(clean_theme)

        forced_layout = "center" if target_theme == "dark_humor" else "auto"

        # 2. 呼叫合成服務 (layout 自動)
        image_base64 = compose_service.compose_image(
            theme=target_theme,
            title=elder_text.title,
            subtitle=elder_text.subtitle,
            footer=elder_text.footer,
            layout=forced_layout
        )

        # 3. 將 Base64 轉存為實體檔案
        # 產生唯一檔名，避免快取或衝突
        filename = f"{uuid.uuid4()}.png"
        file_path = STATIC_DIR / filename

        # 解碼並寫入
        image_data = base64.b64decode(image_base64)
        with open(file_path, "wb") as f:
            f.write(image_data)

        # 4. 組建公開 URL
        # 注意：LINE 要求必須是 HTTPS (除了 localhost 開發用 ngrok)
        image_url = f"{app_base_url}/static/{filename}"
        print(f"Generated Image URL: {image_url}")

        # 5. 回覆圖片訊息 (使用 Reply API)
        reply_request = ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[
                ImageMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            ]
        )
        line_bot_api.reply_message(reply_request)

    except Exception as e:
        print(f"Error handling LINE message: {e}")
        # 出錯時回傳文字告知
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="抱歉，長輩圖產生失敗，請稍後再試。")]
            )
        )
