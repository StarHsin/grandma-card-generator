import React, { useState } from "react";

const themes = [
  { id: "morning", label: "早安" },
  { id: "health", label: "健康" },
  { id: "life", label: "生活 / 人生格言" },
  { id: "festival_newyear", label: "節慶：新年" },
  { id: "festival_christmas", label: "節慶：聖誕" },
  { id: "festival_midautumn", label: "節慶：中秋" },
  { id: "festival_lantern", label: "節慶：元宵" },
  { id: "festival_common", label: "節慶：一般祝福" },
];

const API_BASE_URL = "http://localhost:8000";

function App() {
  const [selectedTheme, setSelectedTheme] = useState("morning");
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
        body: JSON.stringify({ theme: selectedTheme }),
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
      setError(err.message || "發生未知錯誤，請稍後再試。");
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
    link.download = `elder-card-${themeLabel}-${Date.now()}.png`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 via-slate-50 to-sky-100">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-8">
        {/* Header */}
        <header className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-800">
              長輩圖生成器
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              選擇主題，一鍵產生長輩最愛的祝福小卡 💌
            </p>
          </div>
          <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-3 py-1 text-xs text-slate-500 backdrop-blur">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Gemini 文案生成中
          </span>
        </header>

        {/* Main layout */}
        <main className="grid flex-1 gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1.3fr)]">
          {/* 左側：控制面板 */}
          <section className="h-max rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm backdrop-blur">
            <h2 className="mb-4 text-base font-semibold text-slate-700">
              1. 選擇主題與操作
            </h2>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label
                  htmlFor="theme-select"
                  className="text-sm font-medium text-slate-700"
                >
                  長輩圖主題
                </label>
                <select
                  id="theme-select"
                  value={selectedTheme}
                  onChange={(e) => setSelectedTheme(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm outline-none ring-0 focus:border-amber-400 focus:ring-2 focus:ring-amber-200"
                >
                  {themes.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500">
                  目前支援早安、健康、生活感悟與各種節慶主題。
                </p>
              </div>

              <button
                className="inline-flex items-center justify-center rounded-full bg-amber-500 px-6 py-2 text-sm font-semibold text-white shadow-md shadow-amber-200 transition hover:bg-amber-600 disabled:cursor-not-allowed disabled:bg-amber-300"
                onClick={handleGenerate}
                disabled={loading}
              >
                {loading ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/60 border-t-transparent" />
                    生成中…
                  </span>
                ) : (
                  "生成長輩圖"
                )}
              </button>

              {error && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                  ⚠️ {error}
                </div>
              )}

              <div className="mt-4 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-500">
                小提醒：生成好的圖片可以直接下載後傳到 Line、Messenger
                給家人朋友。
              </div>
            </div>
          </section>

          {/* 右側：預覽區 */}
          <section className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm backdrop-blur">
            <h2 className="text-base font-semibold text-slate-700">
              2. 文案與長輩圖預覽
            </h2>

            {!result && (
              <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-4 py-8 text-center text-sm text-slate-500">
                <span className="text-3xl">👵👴</span>
                <p>
                  選一個主題，點擊「生成長輩圖」，這裡會顯示文案與圖片預覽。
                </p>
              </div>
            )}

            {result && (
              <>
                {/* 文案區 */}
                <div className="rounded-xl border border-slate-100 bg-slate-50/80 px-4 py-3">
                  <h3 className="text-lg font-semibold text-slate-800">
                    {result.text.title}
                  </h3>
                  <p className="mt-1 text-sm text-slate-600">
                    {result.text.subtitle}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    {result.text.footer}
                  </p>
                </div>

                {/* 圖片預覽 + 下載 */}
                <div className="flex flex-1 flex-col items-center gap-3 rounded-xl border border-slate-100 bg-slate-50/60 px-4 py-4">
                  <div className="w-full max-w-[480px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                    <img
                      src={`data:image/png;base64,${result.image_base64}`}
                      alt="Generated elder card"
                      className="block w-full"
                    />
                  </div>

                  <button
                    className="inline-flex items-center justify-center rounded-full bg-emerald-500 px-5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-600"
                    onClick={handleDownload}
                  >
                    下載圖片（PNG）
                  </button>
                </div>
              </>
            )}
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
