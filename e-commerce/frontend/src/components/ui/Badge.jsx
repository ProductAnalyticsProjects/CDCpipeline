import { colors, fonts } from "../../styles/theme.js";

export default function Badge({ children, color = colors.accent }) {
  return (
    <span
      style={{
        padding: "3px 10px",
        borderRadius: 3,
        fontSize: 10,
        fontFamily: fonts.mono,
        fontWeight: 700,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        background: color + "20",
        color,
        border: `1px solid ${color}40`,
      }}
    >
      {children}
    </span>
  );
}
