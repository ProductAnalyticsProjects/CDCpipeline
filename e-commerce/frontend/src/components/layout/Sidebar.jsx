import { NavLink } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { colors, fonts } from "../../styles/theme.js";
import { Btn, Badge } from "../ui/index.js";

const NAV_ITEMS = [
  { to: "/products",  label: "Prodotti",   icon: "◫" },
  { to: "/inventory", label: "Inventario", icon: "▦" },
  { to: "/orders",    label: "Ordini",     icon: "◳" },
];

export default function Sidebar() {
  const { user, logout, isAdmin } = useAuth();

  const linkStyle = (isActive) => ({
    padding: "10px 14px",
    borderRadius: 6,
    cursor: "pointer",
    fontFamily: fonts.mono,
    fontSize: 12,
    color: isActive ? colors.text : colors.textMuted,
    background: isActive ? colors.accent + "12" : "transparent",
    borderLeft: isActive ? `2px solid ${colors.accent}` : "2px solid transparent",
    transition: "all 0.2s",
    display: "flex",
    alignItems: "center",
    gap: 10,
    letterSpacing: "0.03em",
    textDecoration: "none",
  });

  return (
    <aside
      style={{
        width: 220,
        background: colors.surface,
        borderRight: `1px solid ${colors.border}`,
        display: "flex",
        flexDirection: "column",
        padding: "20px 0",
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div style={{ padding: "0 20px", marginBottom: 32 }}>
        <div
          style={{
            fontSize: 10,
            color: colors.accent,
            fontFamily: fonts.mono,
            letterSpacing: "0.3em",
            textTransform: "uppercase",
          }}
        >
          ⬡ Warehouse
        </div>
        <div
          style={{
            fontSize: 16,
            fontFamily: fonts.mono,
            color: colors.text,
            fontWeight: 700,
            letterSpacing: "-0.02em",
          }}
        >
          OS
        </div>
      </div>

      {/* Navigation */}
      <nav
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: 2,
          padding: "0 10px",
        }}
      >
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            style={({ isActive }) => linkStyle(isActive)}
          >
            <span style={{ fontSize: 15, opacity: 0.7 }}>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* User info */}
      <div style={{ padding: "16px 20px", borderTop: `1px solid ${colors.border}` }}>
        <div
          style={{
            fontFamily: fonts.mono,
            fontSize: 11,
            color: colors.textMuted,
            marginBottom: 4,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {user?.email}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <Badge color={isAdmin ? colors.accent : colors.blue}>{user?.role}</Badge>
        </div>
        <Btn
          small
          variant="ghost"
          onClick={logout}
          style={{ width: "100%", justifyContent: "center" }}
        >
          Logout
        </Btn>
      </div>
    </aside>
  );
}
