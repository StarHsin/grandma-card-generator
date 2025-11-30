import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

# ===== FastAPI App =====

app = FastAPI(title="Elder Card Generator API")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://grandma-card-generator.vercel.app/"
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
