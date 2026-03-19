import { colors, fonts } from "../../styles/theme.js";

const variantStyles = {
  primary: { background: colors.accent, color: "#000" },
  danger: { background: colors.danger, color: "#fff" },
  ghost: { background: "transparent", color: colors.textMuted, border: `1px solid ${colors.border}` },
  success: { background: colors.success, color: "#fff" },
  blue: { background: colors.blue, color: "#fff" },
};

export default function Btn({
  children,
  variant = "primary",
  small,
  disabled,
  onClick,
  style,
  ...props
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: small ? "6px 14px" : "10px 20px",
        border: "none",
        borderRadius: 4,
        cursor: disabled ? "not-allowed" : "pointer",
        fontFamily: fonts.mono,
        fontSize: small ? 11 : 12,
        fontWeight: 600,
        letterSpacing: "0.05em",
        textTransform: "uppercase",
        transition: "all 0.2s",
        opacity: disabled ? 0.5 : 1,
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        whiteSpace: "nowrap",
        ...variantStyles[variant],
        ...style,
      }}
      {...props}
    >
      {children}
    </button>
  );
}
