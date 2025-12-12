import React, { useEffect, useMemo, useState } from "react";
import Particles, { initParticlesEngine } from "@tsparticles/react";
import { loadSlim } from "@tsparticles/slim"; // 或者根據您的需求選擇 loadFull 或 loadAll

export default function ChristmasSnow() {
  const [init, setInit] = useState(false);

  // 這個 useEffect 確保 tsParticles 引擎只被初始化一次
  useEffect(() => {
    initParticlesEngine(async (engine) => {
      // 您可以在這裡載入特定的預設或插件
      // loadSlim 是一個輕量級的版本，包含常用的功能
      await loadSlim(engine);
      // 如果您安裝了 @tsparticles/all，可以使用 loadAll(engine);
      // 如果您安裝了 tsparticles (完整版)，可以使用 loadFull(engine);
    }).then(() => {
      setInit(true);
    });
  }, []);

  const particlesLoaded = (container) => {
    console.log("tsParticles 載入完成", container);
  };

  // 使用 useMemo 來優化配置，確保在組件重新渲染時不會重複創建配置對象
  const options = useMemo(
    () => ({
      background: {
        color: {
          value: "transparent", // 背景顏色
        },
      },
      fpsLimit: 120,
      events: {
        onClick: {
          enable: true,
          mode: "push", // 點擊時產生更多雪花
        },
        onHover: {
          enable: false,
        },
        resize: true,
      },
      interactivity: {
        events: {
          onClick: {
            enable: true,
            mode: "push", // 點擊時產生更多雪花
          },
          onHover: {
            enable: false,
          },
          resize: true,
        },
        modes: {
          push: {
            quantity: 10, // 點一下噴出 10 個雪花
          },
        },
      },
      particles: {
        number: {
          value: 100, // 雪花數量
          density: {
            enable: true,
            area: 800,
          },
        },
        color: {
          value: "#ffffff",
        },
        shape: {
          type: "circle",
        },
        opacity: {
          value: 0.8,
          random: true,
        },
        size: {
          value: { min: 2, max: 8 }, // 雪花大小隨機
          random: true,
        },
        move: {
          enable: true,
          speed: 2,
          direction: "bottom", // 向下飄
          random: true,
          straight: false,
          outModes: {
            default: "out",
          },
          attract: {
            enable: false,
            rotateX: 600,
            rotateY: 1200,
          },
        },
      },
      detectRetina: true,
    }),
    []
  );

  if (init) {
    return (
      <Particles
        id="tsparticles"
        particlesLoaded={particlesLoaded}
        options={options}
      />
    );
  }

  return <></>;
}
