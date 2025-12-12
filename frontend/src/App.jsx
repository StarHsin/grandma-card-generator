"use client";

import { useState, useEffect, useRef } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Loader2,
  Download,
  Sparkles,
  Heart,
  AlertCircle,
  Music,
  PauseCircle,
  Snowflake,
} from "lucide-react";

// 引入下雪特效元件 (請確保檔案存在於 src/components/ChristmasSnow.jsx)
import ChristmasSnow from "./components/ChristmasSnow";

const themes = [
  { id: "morning", label: "早安 ☀️", emoji: "☀️" },
  { id: "health", label: "健康 💪", emoji: "💪" },
  { id: "life", label: "生活格言 🌿", emoji: "🌿" },
  { id: "festival_newyear", label: "節慶：新年 🧧", emoji: "🧧" },
  { id: "festival_christmas", label: "節慶：聖誕 🎄", emoji: "🎄" },
  { id: "festival_midautumn", label: "節慶：中秋 🥮", emoji: "🥮" },
  { id: "festival_lantern", label: "節慶：元宵 🏮", emoji: "🏮" },
  { id: "festival_common", label: "節慶：一般 🎊", emoji: "🎊" },
];

const layouts = [
  { id: "auto", label: "✨ 自動變換" },
  { id: "center", label: "📍 置中經典" },
  { id: "top_bottom", label: "⬆️⬇️ 上下分佈" },
  { id: "left_block", label: "◀️ 左側文字" },
  { id: "vertical", label: "📝 直書標題" },
];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// 無版權聖誕音樂 (Kevin MacLeod / Pixabay)
const XMAS_MUSIC_URL = "we-wish-you-a-merry-christmas-444573.mp3";

export default function ElderCardGenerator() {
  const [selectedTheme, setSelectedTheme] = useState("morning");
  const [selectedLayout, setSelectedLayout] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // === 🎄 聖誕彩蛋狀態 🎄 ===
  const [isXmasMode, setIsXmasMode] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);

  useEffect(() => {
    // 1. 自動偵測月份：如果是 12 月，自動開啟聖誕模式
    const today = new Date();
    if (today.getMonth() === 11) {
      // 11 代表 12月
      setIsXmasMode(true);
      setSelectedTheme("festival_christmas"); // 自動選聖誕主題
    }

    // 2. 初始化音樂播放器
    audioRef.current = new Audio(XMAS_MUSIC_URL);
    audioRef.current.loop = true; // 循環播放

    return () => {
      // Cleanup: 離開頁面時暫停音樂
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  // 音樂開關
  const toggleMusic = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
    } else {
      // 瀏覽器可能會擋自動播放，需透過使用者點擊觸發
      audioRef.current.play().catch((e) => console.error("播放失敗:", e));
    }
    setIsPlaying(!isPlaying);
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          theme: selectedTheme,
          layout: selectedLayout,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const msg = data.detail || `API error: ${res.status}`;
        throw new Error(msg);
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error ? err.message : "發生未知錯誤，請稍後再試。"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;

    const link = document.createElement("a");
    const themeLabel =
      themes.find((t) => t.id === result.theme)?.label || result.theme;

    link.href = `data:image/png;base64,${result.image_base64}`;
    link.download = `長輩圖-${themeLabel}-${Date.now()}.png`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const selectedThemeEmoji =
    themes.find((t) => t.id === selectedTheme)?.emoji || "💌";

  return (
    <div
      className={`min-h-screen relative transition-colors duration-700 ease-in-out ${
        isXmasMode
          ? "bg-slate-900" // 聖誕模式：深色背景凸顯雪花
          : "bg-gradient-to-br from-pink-50 via-amber-50 to-rose-50" // 一般模式
      }`}
    >
      {/* 1. 聖誕特效層 (只在模式開啟時顯示) */}
      {isXmasMode && (
        <>
          <ChristmasSnow />
          {/* 頂部跑馬燈 Banner */}
          <div className="w-full bg-gradient-to-r from-green-800 via-red-700 to-green-800 text-white py-2 text-center shadow-md relative z-20 animate-pulse border-b border-yellow-400/30">
            <div className="flex items-center justify-center gap-2 text-sm md:text-base">
              <Snowflake className="h-4 w-4" />
              <span className="font-bold tracking-wider drop-shadow-md">
                Ho Ho Ho! 聖誕節將近，祝大家聖誕快樂！
              </span>
              <Snowflake className="h-4 w-4" />
            </div>
          </div>

          {/* 音樂控制按鈕 (右下角懸浮) */}
          <div className="fixed bottom-6 right-6 z-50">
            <Button
              onClick={toggleMusic}
              className={`rounded-full h-14 w-14 p-0 shadow-xl border-4 transition-all duration-300 ${
                isPlaying
                  ? "bg-red-600 hover:bg-red-700 border-green-400 animate-[spin_4s_linear_infinite]"
                  : "bg-white/90 hover:bg-white border-gray-300 text-slate-800"
              }`}
            >
              {isPlaying ? (
                <PauseCircle className="h-8 w-8 text-white" />
              ) : (
                <Music className="h-7 w-7" />
              )}
            </Button>
          </div>
        </>
      )}

      {/* 手動開關彩蛋按鈕 (右上角) */}
      <div className="absolute top-4 right-4 z-30">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsXmasMode(!isXmasMode)}
          className={
            isXmasMode
              ? "text-white/70 hover:text-white hover:bg-white/20"
              : "text-muted-foreground"
          }
        >
          {isXmasMode ? "關閉特效" : "🎄"}
        </Button>
      </div>

      <div className="container mx-auto px-4 py-8 md:py-12 relative z-10">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mb-4 flex items-center justify-center gap-3">
            <span className="text-5xl drop-shadow-sm">
              {selectedThemeEmoji}
            </span>
            <h1
              className={`text-4xl font-bold tracking-tight md:text-5xl bg-clip-text text-transparent transition-all duration-500 ${
                isXmasMode
                  ? "bg-gradient-to-r from-red-400 via-white to-green-400 drop-shadow-[0_0_10px_rgba(255,255,255,0.5)]"
                  : "bg-gradient-to-r from-pink-600 via-rose-600 to-amber-600"
              }`}
            >
              長輩圖生成器
            </h1>
            <span className="text-5xl drop-shadow-sm">
              {selectedThemeEmoji}
            </span>
          </div>
          <p
            className={`text-balance text-lg transition-colors duration-500 ${
              isXmasMode ? "text-gray-300" : "text-muted-foreground"
            }`}
          >
            用 AI 輕鬆生成溫馨祝福圖片 · 一鍵分享愛與關心 💝
          </p>
          <Badge variant="secondary" className="mt-3 gap-1.5 backdrop-blur-sm">
            <Sparkles className="h-3 w-3" />由 Gemini 智能生成文案
          </Badge>
        </div>

        <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-2">
          {/* Left Panel - Controls */}
          <Card
            className={`border-2 shadow-lg transition-colors duration-500 ${
              isXmasMode
                ? "bg-slate-800/80 border-slate-600 text-white"
                : "bg-white border-border"
            }`}
          >
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">🎨</span>
                選擇主題與風格
              </CardTitle>
              <CardDescription className={isXmasMode ? "text-gray-400" : ""}>
                挑選你喜歡的主題和排版，讓 AI 為你生成專屬祝福圖
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <Label
                  htmlFor="theme-select"
                  className="text-base font-semibold"
                >
                  長輩圖主題
                </Label>
                <Select value={selectedTheme} onValueChange={setSelectedTheme}>
                  <SelectTrigger
                    id="theme-select"
                    className={`h-11 ${
                      isXmasMode
                        ? "bg-slate-700 border-slate-500 text-white"
                        : ""
                    }`}
                  >
                    <SelectValue placeholder="選擇主題" />
                  </SelectTrigger>
                  <SelectContent>
                    {themes.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-3">
                <Label
                  htmlFor="layout-select"
                  className="text-base font-semibold"
                >
                  文字排版風格
                </Label>
                <Select
                  value={selectedLayout}
                  onValueChange={setSelectedLayout}
                >
                  <SelectTrigger
                    id="layout-select"
                    className={`h-11 ${
                      isXmasMode
                        ? "bg-slate-700 border-slate-500 text-white"
                        : ""
                    }`}
                  >
                    <SelectValue placeholder="選擇排版" />
                  </SelectTrigger>
                  <SelectContent>
                    {layouts.map((l) => (
                      <SelectItem key={l.id} value={l.id}>
                        {l.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p
                  className={`text-sm ${
                    isXmasMode ? "text-gray-400" : "text-muted-foreground"
                  }`}
                >
                  💡 選擇「自動變換」會根據背景智能選擇最佳排版
                </p>
              </div>

              <Button
                className={`h-12 w-full text-base font-semibold transition-all hover:scale-[1.02] ${
                  isXmasMode
                    ? "bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 text-white border-0 shadow-[0_0_15px_rgba(34,197,94,0.4)]"
                    : ""
                }`}
                size="lg"
                onClick={handleGenerate}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    AI 生成中...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-5 w-5" />
                    立即生成長輩圖
                  </>
                )}
              </Button>

              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Card
                className={`border transition-colors ${
                  isXmasMode
                    ? "bg-red-900/20 border-red-800"
                    : "border-amber-200 bg-amber-50/50"
                }`}
              >
                <CardContent className="p-4">
                  <div className="flex gap-3">
                    <Heart
                      className={`mt-0.5 h-5 w-5 shrink-0 ${
                        isXmasMode ? "text-red-400" : "text-rose-500"
                      }`}
                    />
                    <div className="space-y-1 text-sm">
                      <p
                        className={`font-medium ${
                          isXmasMode ? "text-red-200" : "text-amber-900"
                        }`}
                      >
                        溫馨小提醒
                      </p>
                      <p
                        className={
                          isXmasMode ? "text-red-300" : "text-amber-800"
                        }
                      >
                        生成後可直接下載，傳到 LINE、Facebook 給親朋好友！
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </CardContent>
          </Card>

          {/* Right Panel - Preview */}
          <Card
            className={`border-2 shadow-lg transition-colors duration-500 ${
              isXmasMode
                ? "bg-slate-800/80 border-slate-600 text-white"
                : "bg-white border-border"
            }`}
          >
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">👀</span>
                預覽與下載
              </CardTitle>
              <CardDescription className={isXmasMode ? "text-gray-400" : ""}>
                文案與圖片即時預覽，滿意就下載分享吧！
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!result ? (
                <div
                  className={`flex min-h-[400px] flex-col items-center justify-center gap-4 rounded-lg border-2 border-dashed p-8 text-center ${
                    isXmasMode
                      ? "border-slate-600 bg-slate-700/30"
                      : "border-gray-200 bg-muted/30"
                  }`}
                >
                  <div className="text-6xl animate-bounce">
                    {isXmasMode ? "🎅" : "👵👴"}
                  </div>
                  <div className="space-y-2">
                    <p className="text-lg font-medium">準備好了嗎？</p>
                    <p
                      className={`text-balance text-sm ${
                        isXmasMode ? "text-gray-400" : "text-muted-foreground"
                      }`}
                    >
                      選擇主題和排版風格，點擊「立即生成」按鈕
                      <br />
                      AI 會為你創造獨一無二的祝福圖片 ✨
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Text Preview */}
                  <Card
                    className={
                      isXmasMode
                        ? "bg-slate-700 border-slate-500"
                        : "border-primary/20 bg-gradient-to-br from-background to-primary/5"
                    }
                  >
                    <CardContent className="space-y-3 p-5">
                      <div className="flex items-start justify-between gap-2">
                        <h3
                          className={`text-balance text-xl font-bold leading-tight ${
                            isXmasMode ? "text-white" : "text-foreground"
                          }`}
                        >
                          {result.text.title}
                        </h3>
                        <Badge
                          variant="outline"
                          className={`shrink-0 text-xs ${
                            isXmasMode ? "text-gray-300 border-gray-500" : ""
                          }`}
                        >
                          {layouts
                            .find((l) => l.id === result.layout)
                            ?.label.replace(/[✨📍⬆️⬇️◀️📝]/gu, "")
                            .trim() ?? result.layout}
                        </Badge>
                      </div>
                      <p
                        className={`text-pretty text-base leading-relaxed ${
                          isXmasMode ? "text-gray-300" : "text-muted-foreground"
                        }`}
                      >
                        {result.text.subtitle}
                      </p>
                    </CardContent>
                  </Card>

                  {/* Image Preview */}
                  <div className="space-y-3">
                    <div
                      className={`overflow-hidden rounded-lg border-2 p-2 ${
                        isXmasMode
                          ? "bg-slate-700 border-slate-600"
                          : "bg-muted/30"
                      }`}
                    >
                      <div className="overflow-hidden rounded-md bg-white shadow-inner">
                        <img
                          src={`data:image/png;base64,${result.image_base64}`}
                          alt="生成的長輩圖"
                          className="w-full"
                        />
                      </div>
                    </div>

                    <Button
                      className={`h-11 w-full text-base font-semibold ${
                        isXmasMode
                          ? "bg-red-600 hover:bg-red-700 text-white"
                          : ""
                      }`}
                      variant="default"
                      size="lg"
                      onClick={handleDownload}
                    >
                      <Download className="mr-2 h-5 w-5" />
                      下載圖片（PNG）
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Footer */}
        <div
          className={`mt-12 text-center text-sm ${
            isXmasMode ? "text-gray-500" : "text-muted-foreground"
          }`}
        >
          <p>用愛與科技，讓每一份祝福都更有溫度 ❤️</p>
        </div>
      </div>
    </div>
  );
}
