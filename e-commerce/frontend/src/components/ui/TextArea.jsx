import { colors, fonts } from "../../styles/theme.js";

export default function TextArea({ label, style, ...props }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {label && (
        <label
          style={{
            fontSize: 10,
            fontFamily: fonts.mono,
            color: colors.textMuted,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
          }}
        >
          {label}
        </label>
      )}
      <textarea
        {...props}
        style={{
          padding: "10px 14px",
          background: colors.surfaceAlt,
          border: `1px solid ${colors.border}`,
          borderRadius: 4,
          color: colors.text,
          fontFamily: fonts.mono,
          fontSize: 13,
          outline: "none",
          resize: "vertical",
          ...style,
        }}
      />
    </div>
  );
}
