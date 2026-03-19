import { Outlet, Navigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import { colors } from "../../styles/theme.js";
import Sidebar from "./Sidebar.jsx";

export default function AppLayout() {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: colors.bg }}>
      <Sidebar />
      <main
        style={{
          flex: 1,
          padding: "28px 36px",
          overflowY: "auto",
          maxHeight: "100vh",
        }}
      >
        <Outlet />
      </main>
    </div>
  );
}
