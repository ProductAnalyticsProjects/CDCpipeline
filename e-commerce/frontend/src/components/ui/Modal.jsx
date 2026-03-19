import { colors, fonts } from "../../styles/theme.js";

export default function Modal({ open, onClose, title, children, width = 480 }) {
  if (!open) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        animation: "fadeIn 0.2s ease",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: colors.surface,
          border: `1px solid ${colors.border}`,
          borderRadius: 10,
          padding: 28,
          width,
          maxWidth: "90vw",
          maxHeight: "85vh",
          overflowY: "auto",
          animation: "scaleIn 0.25s ease",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <h3
            style={{
              fontFamily: fonts.mono,
              fontSize: 14,
              color: colors.accent,
              letterSpacing: "0.05em",
              textTransform: "uppercase",
              margin: 0,
            }}
          >
            {title}
          </h3>
          <span
            onClick={onClose}
            style={{
              cursor: "pointer",
              color: colors.textMuted,
              fontSize: 18,
              lineHeight: 1,
            }}
          >
            ✕
          </span>
        </div>
        {children}
      </div>
    </div>
  );
}
