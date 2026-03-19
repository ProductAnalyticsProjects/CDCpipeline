import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { useToast } from "../context/ToastContext";
import { DEFAULT_WAREHOUSE } from "../api/client";
import { colors, fonts } from "../styles/theme";
import {
  Btn, Input, Card, Table, Modal, PageHeader, Loading,
} from "../components/ui";

export default function InventoryPage() {
  const api = useApi();
  const toast = useToast();
  const { isAdmin } = useAuth();

  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lowStock, setLowStock] = useState([]);
  const [showLow, setShowLow] = useState(false);
  const [modal, setModal] = useState(null); // null | 'add' | stock obj
  const [form, setForm] = useState({ productId: "", quantity: "" });
  const [threshold, setThreshold] = useState(10);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get("/inventory?page=0&size=100");
      setStocks(data.content || data);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, [api, toast]);

  const loadLowStock = useCallback(async () => {
    try {
      const data = await api.get(`/inventory/low-stock?threshold=${threshold}`);
      setLowStock(data.content || data);
      setShowLow(true);
    } catch (e) {
      toast.error(e.message);
    }
  }, [api, toast, threshold]);

  useEffect(() => {
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    try {
      if (modal === "add") {
        await api.post("/inventory", {
          productId: form.productId,
          warehouseId: DEFAULT_WAREHOUSE,
          quantity: parseInt(form.quantity),
        });
        toast.success("Stock aggiunto");
      } else {
        await api.put(
          `/inventory/${modal.product.id}?warehouseId=${DEFAULT_WAREHOUSE}&quantity=${parseInt(form.quantity)}`,
        );
        toast.success("Stock aggiornato");
      }
      setModal(null);
      load();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const openUpdate = (s) => {
    setForm({ productId: s.product.id, quantity: String(s.availableQuantity) });
    setModal(s);
  };

  const columns = [
    {
      key: "product",
      label: "Prodotto",
      render: (r) => (
        <span style={{ color: colors.text, fontWeight: 500 }}>
          {r.product?.name}
        </span>
      ),
    },
    {
      key: "sku",
      label: "SKU",
      render: (r) => <span style={{ color: colors.accent }}>{r.product?.sku}</span>,
    },
    {
      key: "warehouse",
      label: "Magazzino",
      render: (r) => r.warehouse?.name || "—",
    },
    {
      key: "available",
      label: "Disponibile",
      render: (r) => {
        const qty = r.availableQuantity;
        const c = qty <= 5 ? colors.danger : qty <= 20 ? colors.accent : colors.success;
        return <span style={{ color: c, fontWeight: 700 }}>{qty}</span>;
      },
    },
    {
      key: "reserved",
      label: "Riservato",
      render: (r) => r.reservedQuantity || 0,
    },
    ...(isAdmin
      ? [
          {
            key: "actions",
            label: "",
            render: (r) => (
              <div onClick={(e) => e.stopPropagation()}>
                <Btn small variant="ghost" onClick={() => openUpdate(r)}>
                  ✎ Aggiorna
                </Btn>
              </div>
            ),
          },
        ]
      : []),
  ];

  return (
    <div>
      <PageHeader
        title="Inventario"
        subtitle="Gestione stock magazzino"
        action={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <Input
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                type="number"
                style={{ width: 60, padding: "6px 10px" }}
              />
              <Btn small variant="ghost" onClick={loadLowStock}>
                ⚠ Low Stock
              </Btn>
            </div>
            {isAdmin && (
              <Btn
                onClick={() => {
                  setForm({ productId: "", quantity: "" });
                  setModal("add");
                }}
              >
                + Aggiungi Stock
              </Btn>
            )}
          </div>
        }
      />

      {/* Low stock alert */}
      {showLow && lowStock.length > 0 && (
        <Card style={{ marginBottom: 20, borderColor: colors.danger + "40" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 12,
            }}
          >
            <span
              style={{
                fontFamily: fonts.mono,
                fontSize: 12,
                color: colors.danger,
                fontWeight: 600,
                letterSpacing: "0.05em",
                textTransform: "uppercase",
              }}
            >
              ⚠ Scorte basse (≤ {threshold})
            </span>
            <Btn small variant="ghost" onClick={() => setShowLow(false)}>
              ✕
            </Btn>
          </div>
          <Table columns={columns.filter((c) => c.key !== "actions")} data={lowStock} />
        </Card>
      )}

      <Card>
        {loading ? <Loading /> : <Table columns={columns} data={stocks} />}
      </Card>

      <Modal
        open={!!modal}
        onClose={() => setModal(null)}
        title={modal === "add" ? "Aggiungi Stock" : "Aggiorna Quantità"}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {modal === "add" && (
            <Input
              label="Product ID (UUID)"
              value={form.productId}
              onChange={(e) => setForm({ ...form, productId: e.target.value })}
              placeholder="uuid del prodotto"
            />
          )}
          {modal !== "add" && modal && (
            <div
              style={{
                fontFamily: fonts.mono,
                fontSize: 12,
                color: colors.textMuted,
                padding: "8px 12px",
                background: colors.surfaceAlt,
                borderRadius: 4,
              }}
            >
              Prodotto:{" "}
              <span style={{ color: colors.text }}>{modal.product?.name}</span>
            </div>
          )}
          <Input
            label="Quantità"
            type="number"
            value={form.quantity}
            onChange={(e) => setForm({ ...form, quantity: e.target.value })}
          />
          <Btn onClick={save} style={{ marginTop: 8 }}>
            Salva
          </Btn>
        </div>
      </Modal>
    </div>
  );
}
