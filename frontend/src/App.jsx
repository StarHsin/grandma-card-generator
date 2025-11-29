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
    <div className="app-root">
      <h1 className="app-title">長輩圖生成器 MVP</h1>

      <div className="app-panel">
        <div className="form-row">
          <label htmlFor="theme-select">選擇主題：</label>
          <select
            id="theme-select"
            value={selectedTheme}
            onChange={(e) => setSelectedTheme(e.target.value)}
          >
            {themes.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        <button
          className="generate-button"
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? "生成中..." : "生成長輩圖"}
        </button>

        {error && <div className="error-box">⚠️ {error}</div>}
      </div>

      {result && (
        <div className="result-section">
          <h2>生成結果</h2>

          <div className="text-preview">
            <h3>{result.text.title}</h3>
            <p>{result.text.subtitle}</p>
            <p className="footer-text">{result.text.footer}</p>
          </div>

          <div className="image-preview">
            <h3>合成圖片預覽</h3>
            <img
              src={`data:image/png;base64,${result.image_base64}`}
              alt="Generated elder card"
            />

            <button className="download-button" onClick={handleDownload}>
              下載圖片
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
