import { colors } from "../../styles/theme.js";
import Badge from "./Badge.jsx";

const STATUS_MAP = {
  PENDING:    { color: colors.textMuted, label: "In attesa" },
  PAID:       { color: colors.blue,      label: "Pagato" },
  PROCESSING: { color: colors.accent,    label: "In lavorazione" },
  SHIPPED:    { color: colors.purple,    label: "Spedito" },
  DELIVERED:  { color: colors.success,   label: "Consegnato" },
  CANCELLED:  { color: colors.danger,    label: "Annullato" },
};

export default function StatusBadge({ status }) {
  const s = STATUS_MAP[status] || { color: colors.textMuted, label: status };
  return <Badge color={s.color}>{s.label}</Badge>;
}
