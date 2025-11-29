import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.compose_service import ComposeService
from services.llm_service import LLMService, ElderCardText

# ===== 基本設定 =====

BASE_DIR = Path(__file__).resolve().parent
BACKGROUND_BASE_DIR = BASE_DIR / "assets" / "backgrounds"
FONT_PATH = r"C:\Windows\Fonts\msjh.ttc"

# 允許的主題（前後端都盡量用這組）
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

# ===== FastAPI App =====

app = FastAPI(title="Elder Card Generator API")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Services 單例 =====

compose_service = ComposeService(
    background_base_dir=str(BACKGROUND_BASE_DIR),
    font_path=FONT_PATH or None,
)

llm_service = LLMService()


# ===== Pydantic Models =====

class GenerateRequest(BaseModel):
    theme: str


class ElderCardTextModel(BaseModel):
    title: str
    subtitle: str
    footer: str


class GenerateResponse(BaseModel):
    theme: str
    text: ElderCardTextModel
    image_base64: str


# ===== Routes =====

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Elder Card API is running"}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_card(req: GenerateRequest):
    theme = req.theme

    if theme not in ALLOWED_THEMES:
        raise HTTPException(status_code=400, detail=f"Unknown theme: {theme}")

    theme_dir = BACKGROUND_BASE_DIR / theme
    if not theme_dir.exists():
        raise HTTPException(
            status_code=400,
            detail=f"No background directory for theme: {theme}",
        )

    # 1) 產出文字（目前用模板，未來這裡改成真的 LLM）
    elder_text: ElderCardText = llm_service.generate_text(theme)

    # 2) 合成圖片
    image_base64 = compose_service.compose_image(
        theme=theme,
        title=elder_text.title,
        subtitle=elder_text.subtitle,
        footer=elder_text.footer,
    )

    return GenerateResponse(
        theme=theme,
        text=ElderCardTextModel(
            title=elder_text.title,
            subtitle=elder_text.subtitle,
            footer=elder_text.footer,
        ),
        image_base64=image_base64,
    )
