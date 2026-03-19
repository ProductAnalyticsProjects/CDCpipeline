import { colors, fonts } from "../../styles/theme.js";

export default function PageHeader({ title, subtitle, action }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-end",
        marginBottom: 28,
      }}
    >
      <div>
        <h1
          style={{
            fontFamily: fonts.mono,
            fontSize: 22,
            color: colors.text,
            margin: 0,
            letterSpacing: "-0.02em",
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            style={{
              fontFamily: fonts.sans,
              fontSize: 13,
              color: colors.textMuted,
              margin: "4px 0 0",
            }}
          >
            {subtitle}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}
