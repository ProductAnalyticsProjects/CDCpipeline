import { colors } from "../../styles/theme.js";

export default function Card({ children, style }) {
  return (
    <div
      style={{
        background: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: 8,
        padding: 24,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
