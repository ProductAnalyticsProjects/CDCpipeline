import { colors } from "../../styles/theme.js";

export default function Loading() {
  return (
    <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
      <div
        style={{
          width: 28,
          height: 28,
          border: `2px solid ${colors.border}`,
          borderTopColor: colors.accent,
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
    </div>
  );
}
