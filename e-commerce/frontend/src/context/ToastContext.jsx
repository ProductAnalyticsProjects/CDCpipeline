import { createContext, useContext, useState, useCallback } from "react";
import { colors, fonts } from "../styles/theme.js";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const add = useCallback((msg, type = "info") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, msg, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500);
  }, []);

  const toast = {
    success: (m) => add(m, "success"),
    error: (m) => add(m, "error"),
    info: (m) => add(m, "info"),
  };

  const bgMap = {
    success: "#16a34a",
    error: "#dc2626",
    info: "#2563eb",
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div
        style={{
          position: "fixed",
          bottom: 24,
          right: 24,
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            style={{
              padding: "12px 20px",
              borderRadius: 6,
              color: "#fff",
              fontSize: 13,
              fontFamily: fonts.mono,
              letterSpacing: "0.02em",
              maxWidth: 360,
              animation: "fadeSlideIn 0.3s ease",
              background: bgMap[t.type],
              boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
            }}
          >
            {t.msg}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
