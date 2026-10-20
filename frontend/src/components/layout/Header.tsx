import { useState, useEffect } from "react";
import { SettingOutlined } from "@ant-design/icons";
import { useAppStore } from "@/store/useAppStore";
import { useLocation } from "react-router-dom";
import WarehouseSelector from "@/components/shared/WarehouseSelector";

function formatHeaderDateTime(date: Date, lang: string): string {
  const locale = lang === "EN" ? "en-GB" : "vi-VN";
  return date.toLocaleString(locale, {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export default function Header() {
  const location = useLocation();
  const isSettingPage = location.pathname.startsWith('/setting');
  const { lang, setLang } = useAppStore();
  

  // Removed isConnecting and isError because useZone was removed in origin/main's Header
  const statusTone = "online";
  const systemStatusLabel =
    lang === "EN"
      ? "SYSTEM  ·  ONLINE"
      : "HỆ THỐNG  ·  HOẠT ĐỘNG";

  return (
    <div className="flex flex-row justify-between h-full items-center px-4 w-full gap-4">
      <h1 className="font-extrabold text-3xl sm:text-4xl bg-gradient-to-r from-brand-primary to-brand-dark bg-clip-text text-transparent leading-tight">
        Hệ thống quản lý kho
      </h1>
      <div
        className={`iot-status mt-1 inline-flex items-center gap-2 iot-status--online`}
        title={systemStatusLabel}
        role="status"
        aria-live="polite"
      >
        <span className="iot-status__led" aria-hidden />
        <span className="iot-status__label">{systemStatusLabel}</span>
      </div>

      <div className="flex items-center gap-4 min-w-0">
        {/* 1. Bộ chọn Kho hiện tại hoặc Nhãn Cài đặt */}
        {isSettingPage ? (
          <div className="relative flex h-14 w-72 min-w-[288px] max-w-[288px] items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4">
            <SettingOutlined className="text-lg text-slate-400" />
            <div className="truncate text-base font-semibold text-slate-700">
              Cài đặt hệ thống
            </div>
          </div>
        ) : (
          <WarehouseSelector />
        )}

        {/* 2. Bộ chuyển đổi Ngôn ngữ (VI / EN) */}
        <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200">
          <button
            onClick={() => setLang("VI")}
            className={`min-w-[44px] px-4 py-1.5 text-sm font-bold rounded-lg cursor-pointer transition-all ${lang === "VI"
                ? "bg-brand-primary text-white shadow-sm"
                : "text-slate-500 hover:text-slate-700"
              }`}
          >
            VI
          </button>
          <button
            onClick={() => setLang("EN")}
            className={`min-w-[44px] px-4 py-1.5 text-sm font-bold rounded-lg cursor-pointer transition-all ${lang === "EN"
                ? "bg-brand-primary text-white shadow-sm"
                : "text-slate-500 hover:text-slate-700"
              }`}
          >
            EN
          </button>
        </div>
      </div>
    </div>
  );
}
