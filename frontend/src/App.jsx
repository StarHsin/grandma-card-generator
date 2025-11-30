"use client";

import { useState } from "react";
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
import { Loader2, Download, Sparkles, Heart, AlertCircle } from "lucide-react";

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

const API_BASE_URL = "http://localhost:8000";

export default function ElderCardGenerator() {
  const [selectedTheme, setSelectedTheme] = useState("morning");
  const [selectedLayout, setSelectedLayout] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

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
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-amber-50 to-rose-50">
      <div className="container mx-auto px-4 py-8 md:py-12">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mb-4 flex items-center justify-center gap-3">
            <span className="text-5xl">{selectedThemeEmoji}</span>
            <h1 className="bg-gradient-to-r from-pink-600 via-rose-600 to-amber-600 bg-clip-text text-4xl font-bold tracking-tight text-transparent md:text-5xl">
              長輩圖生成器
            </h1>
            <span className="text-5xl">{selectedThemeEmoji}</span>
          </div>
          <p className="text-balance text-lg text-muted-foreground">
            用 AI 輕鬆生成溫馨祝福圖片 · 一鍵分享愛與關心 💝
          </p>
          <Badge variant="secondary" className="mt-3 gap-1.5">
            <Sparkles className="h-3 w-3" />由 Gemini 智能生成文案
          </Badge>
        </div>

        <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-2">
          {/* Left Panel - Controls */}
          <Card className="border-2 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">🎨</span>
                選擇主題與風格
              </CardTitle>
              <CardDescription>
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
                  <SelectTrigger id="theme-select" className="h-11">
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
                  <SelectTrigger id="layout-select" className="h-11">
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
                <p className="text-sm text-muted-foreground">
                  💡 選擇「自動變換」會根據背景智能選擇最佳排版
                </p>
              </div>

              <Button
                className="h-12 w-full text-base font-semibold"
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

              <Card className="border-amber-200 bg-amber-50/50">
                <CardContent className="p-4">
                  <div className="flex gap-3">
                    <Heart className="mt-0.5 h-5 w-5 shrink-0 text-rose-500" />
                    <div className="space-y-1 text-sm">
                      <p className="font-medium text-amber-900">溫馨小提醒</p>
                      <p className="text-amber-800">
                        生成後可直接下載，傳到 LINE、Facebook 給親朋好友！
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </CardContent>
          </Card>

          {/* Right Panel - Preview */}
          <Card className="border-2 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="text-2xl">👀</span>
                預覽與下載
              </CardTitle>
              <CardDescription>
                文案與圖片即時預覽，滿意就下載分享吧！
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!result ? (
                <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 rounded-lg border-2 border-dashed bg-muted/30 p-8 text-center">
                  <div className="text-6xl">👵👴</div>
                  <div className="space-y-2">
                    <p className="text-lg font-medium">準備好了嗎？</p>
                    <p className="text-balance text-sm text-muted-foreground">
                      選擇主題和排版風格，點擊「立即生成」按鈕
                      <br />
                      AI 會為你創造獨一無二的祝福圖片 ✨
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Text Preview */}
                  <Card className="border-primary/20 bg-gradient-to-br from-background to-primary/5">
                    <CardContent className="space-y-3 p-5">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-balance text-xl font-bold leading-tight text-foreground">
                          {result.text.title}
                        </h3>
                        <Badge variant="outline" className="shrink-0 text-xs">
                          {layouts
                            .find((l) => l.id === result.layout)
                            ?.label.replace(/[✨📍⬆️⬇️◀️📝]/gu, "")
                            .trim() ?? result.layout}
                        </Badge>
                      </div>
                      <p className="text-pretty text-base leading-relaxed text-muted-foreground">
                        {result.text.subtitle}
                      </p>
                    </CardContent>
                  </Card>

                  {/* Image Preview */}
                  <div className="space-y-3">
                    <div className="overflow-hidden rounded-lg border-2 bg-muted/30 p-2">
                      <div className="overflow-hidden rounded-md bg-white shadow-inner">
                        <img
                          src={`data:image/png;base64,${result.image_base64}`}
                          alt="生成的長輩圖"
                          className="w-full"
                        />
                      </div>
                    </div>

                    <Button
                      className="h-11 w-full text-base font-semibold"
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
        <div className="mt-12 text-center text-sm text-muted-foreground">
          <p>用愛與科技，讓每一份祝福都更有溫度 ❤️</p>
        </div>
      </div>
    </div>
  );
}
