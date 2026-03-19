import { colors, fonts } from "../../styles/theme.js";
import Btn from "./Btn.jsx";

export default function Pagination({ page, size, total, onChange }) {
  const totalPages = Math.ceil(total / size) || 1;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 0",
        fontFamily: fonts.mono,
        fontSize: 11,
        color: colors.textMuted,
      }}
    >
      <span>{total} risultati</span>
      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
        <Btn small variant="ghost" disabled={page === 0} onClick={() => onChange(page - 1)}>
          ← Prec
        </Btn>
        <span style={{ padding: "6px 12px", color: colors.text }}>
          {page + 1} / {totalPages}
        </span>
        <Btn
          small
          variant="ghost"
          disabled={page >= totalPages - 1}
          onClick={() => onChange(page + 1)}
        >
          Succ →
        </Btn>
      </div>
    </div>
  );
}
