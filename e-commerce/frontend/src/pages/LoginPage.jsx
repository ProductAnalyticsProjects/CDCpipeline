import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { loginRequest, registerRequest } from "../api/auth";
import { colors, fonts } from "../styles/theme";
import { Btn, Input, Card } from "../components/ui";

export default function LoginPage() {
  const { user, login } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (user) return <Navigate to="/products" replace />;

  const submit = async () => {
    setError("");
    setLoading(true);
    try {
      const fn = isLogin ? loginRequest : registerRequest;
      const data = await fn({ email, password });
      login(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: colors.bg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: fonts.mono,
      }}
    >
      {/* Grid background */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: 0.03,
          backgroundImage: `repeating-linear-gradient(0deg, ${colors.accent} 0px, transparent 1px, transparent 40px), repeating-linear-gradient(90deg, ${colors.accent} 0px, transparent 1px, transparent 40px)`,
        }}
      />

      <Card style={{ width: 400, position: "relative", animation: "scaleIn 0.4s ease" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div
            style={{
              fontSize: 11,
              color: colors.accent,
              letterSpacing: "0.3em",
              textTransform: "uppercase",
              marginBottom: 6,
            }}
          >
            ⬡ Warehouse OS
          </div>
          <h2 style={{ fontSize: 20, color: colors.text, margin: 0 }}>
            {isLogin ? "Accedi" : "Registrati"}
          </h2>
        </div>

        {error && (
          <div
            style={{
              padding: "10px 14px",
              background: colors.danger + "15",
              border: `1px solid ${colors.danger}40`,
              borderRadius: 4,
              color: colors.danger,
              fontSize: 12,
              marginBottom: 16,
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="email@esempio.it"
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
          <Btn
            onClick={submit}
            disabled={loading || !email || !password}
            style={{ width: "100%", justifyContent: "center", marginTop: 8 }}
          >
            {loading ? "..." : isLogin ? "Accedi" : "Registrati"}
          </Btn>
        </div>

        <p style={{ textAlign: "center", fontSize: 12, color: colors.textMuted, marginTop: 20 }}>
          {isLogin ? "Non hai un account?" : "Hai già un account?"}{" "}
          <span
            onClick={() => {
              setIsLogin(!isLogin);
              setError("");
            }}
            style={{ color: colors.accent, cursor: "pointer", textDecoration: "underline" }}
          >
            {isLogin ? "Registrati" : "Accedi"}
          </span>
        </p>
      </Card>
    </div>
  );
}
