import { useState, useEffect, useCallback } from "react";
import {useApi} from "../hooks/useApi.js";
import {useToast} from "../context/ToastContext.jsx";
import {useAuth} from "../context/AuthContext.jsx";
import {Btn, Input, Loading, Modal, PageHeader, Pagination, Table} from "../components/ui/index.js";


export default function OrdersPage() {
  const api = useApi();
  const toast = useToast();
  const { isAdmin, user } = useAuth();

  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [detail, setDetail] = useState(null);
  const [createModal, setCreateModal] = useState(false);
  const [form, setForm] = useState({
    customerEmail: "",
    notes: "",
    items: [{ productId: "", quantity: 1 }],
  });

  const PAGE_SIZE = 15;

  const load = useCallback(
    async (p = 0) => {
      setLoading(true);
      try {
        const endpoint = isAdmin ? "/orders" : "/orders/my";
        const data = await api.get(
          `${endpoint}?page=${p}&size=${PAGE_SIZE}&sort=createdAt,desc`,
        );
        setOrders(data.content || data);
        setTotal(data.totalElements ?? (data.content || data).length);
        setPage(p);
      } catch (e) {
        toast.error(e.message);
      } finally {
        setLoading(false);
      }
    },
    [api, toast, isAdmin],
  );

  useEffect(() => {
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const createOrder = async () => {
    try {
      const payload = {
        customerEmail: form.customerEmail || user.email,
        items: form.items
          .filter((i) => i.productId)
          .map((i) => ({ productId: i.productId, quantity: parseInt(i.quantity) })),
        ...(form.notes ? { notes: form.notes } : {}),
      };
      await api.post("/orders", payload);
      toast.success("Ordine creato");
      setCreateModal(false);
      load(0);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const orderAction = async (id, action, label) => {
    try {
      await api.post(`/orders/${id}/${action}`);
      toast.success(label);
      load(page);
      if (detail?.id === id) {
        const updated = await api.get(`/orders/${id}`);
        setDetail(updated);
      }
    } catch (e) {
      toast.error(e.message);
    }
  };

  const viewDetail = async (o) => {
    try {
      const data = await api.get(`/orders/${o.id}`);
      setDetail(data);
    } catch (e) {
      toast.error(e.message);
    }
  };

  // Dynamic items management
  const addItem = () =>
    setForm({ ...form, items: [...form.items, { productId: "", quantity: 1 }] });

  const removeItem = (i) =>
    setForm({ ...form, items: form.items.filter((_, idx) => idx !== i) });

  const updateItem = (i, field, val) => {
    const items = [...form.items];
    items[i] = { ...items[i], [field]: val };
    setForm({ ...form, items });
  };

  // Table columns
  const columns = [
    {
      key: "id",
      label: "ID",
      render: (r) => (
        <span style={{ color: colors.textMuted, fontSize: 11 }}>
          {r.id?.slice(0, 8)}…
        </span>
      ),
    },
    {
      key: "status",
      label: "Stato",
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: "totalPrice",
      label: "Totale",
      render: (r) => (
        <span style={{ fontWeight: 700, color: colors.text }}>
          € {Number(r.totalPrice).toFixed(2)}
        </span>
      ),
    },
    {
      key: "items",
      label: "Articoli",
      render: (r) => r.items?.length || "—",
    },
    {
      key: "notes",
      label: "Note",
      render: (r) => (
        <span
          style={{
            color: colors.textMuted,
            maxWidth: 150,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            display: "block",
          }}
        >
          {r.notes || "—"}
        </span>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Ordini"
        subtitle={isAdmin ? "Tutti gli ordini" : "I tuoi ordini"}
        action={
          <Btn
            onClick={() => {
              setForm({
                customerEmail: user.email,
                notes: "",
                items: [{ productId: "", quantity: 1 }],
              });
              setCreateModal(true);
            }}
          >
            + Nuovo Ordine
          </Btn>
        }
      />

      <Card>
        {loading ? (
          <Loading />
        ) : (
          <>
            <Table columns={columns} data={orders} onRowClick={viewDetail} />
            <Pagination page={page} size={PAGE_SIZE} total={total} onChange={load} />
          </>
        )}
      </Card>

      {/* ─── Order Detail Modal ─── */}
      <Modal open={!!detail} onClose={() => setDetail(null)} title="Dettaglio Ordine" width={560}>
        {detail && <OrderDetail detail={detail} isAdmin={isAdmin} onAction={orderAction} />}
      </Modal>

      {/* ─── Create Order Modal ─── */}
      <Modal open={createModal} onClose={() => setCreateModal(false)} title="Nuovo Ordine" width={520}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Input
            label="Email cliente"
            value={form.customerEmail}
            onChange={(e) => setForm({ ...form, customerEmail: e.target.value })}
          />
          <Input
            label="Note (opzionale)"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />

          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              <label
                style={{
                  fontSize: 10,
                  fontFamily: fonts.mono,
                  color: colors.textMuted,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                }}
              >
                Articoli
              </label>
              <Btn small variant="ghost" onClick={addItem}>
                + Aggiungi
              </Btn>
            </div>
            {form.items.map((item, i) => (
              <div
                key={i}
                style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-end" }}
              >
                <div style={{ flex: 1 }}>
                  <Input
                    label={i === 0 ? "Product ID" : undefined}
                    value={item.productId}
                    onChange={(e) => updateItem(i, "productId", e.target.value)}
                    placeholder="UUID prodotto"
                  />
                </div>
                <div style={{ width: 80 }}>
                  <Input
                    label={i === 0 ? "Qtà" : undefined}
                    type="number"
                    min="1"
                    value={item.quantity}
                    onChange={(e) => updateItem(i, "quantity", e.target.value)}
                  />
                </div>
                {form.items.length > 1 && (
                  <Btn small variant="danger" onClick={() => removeItem(i)} style={{ marginBottom: 1 }}>
                    ✕
                  </Btn>
                )}
              </div>
            ))}
          </div>

          <Btn onClick={createOrder} style={{ marginTop: 8 }}>
            Crea Ordine
          </Btn>
        </div>
      </Modal>
    </div>
  );
}

/* ─── Order Detail Sub-component ─── */
function OrderDetail({ detail, isAdmin, onAction }) {
  return (
    <div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
        <StatusBadge status={detail.status} />
        <span style={{ fontFamily: fonts.mono, fontSize: 13, color: colors.text }}>
          € {Number(detail.totalPrice).toFixed(2)}
        </span>
        <span style={{ fontFamily: fonts.mono, fontSize: 11, color: colors.textMuted }}>
          {detail.id}
        </span>
      </div>

      {detail.notes && (
        <div
          style={{
            fontFamily: fonts.mono,
            fontSize: 12,
            color: colors.textMuted,
            padding: "8px 12px",
            background: colors.surfaceAlt,
            borderRadius: 4,
            marginBottom: 16,
          }}
        >
          {detail.notes}
        </div>
      )}

      {/* Items list */}
      <div style={{ marginBottom: 20 }}>
        <div
          style={{
            fontFamily: fonts.mono,
            fontSize: 10,
            color: colors.textMuted,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            marginBottom: 8,
          }}
        >
          Articoli
        </div>
        {detail.items?.map((item, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "10px 12px",
              borderBottom: `1px solid ${colors.border}20`,
              fontFamily: fonts.mono,
              fontSize: 12,
            }}
          >
            <div>
              <span style={{ color: colors.text }}>{item.product?.name}</span>
              <span style={{ color: colors.textMuted, marginLeft: 8 }}>
                ({item.product?.sku})
              </span>
            </div>
            <div style={{ display: "flex", gap: 16, color: colors.textMuted }}>
              <span>×{item.quantity}</span>
              <span>€ {Number(item.unitPrice).toFixed(2)}</span>
              <span style={{ color: colors.text, fontWeight: 600 }}>
                € {Number(item.subtotal).toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {detail.status === "PENDING" && (
          <>
            <Btn variant="success" onClick={() => onAction(detail.id, "pay", "Pagamento registrato")}>
              💳 Paga
            </Btn>
            <Btn variant="danger" onClick={() => onAction(detail.id, "cancel", "Ordine annullato")}>
              Annulla
            </Btn>
          </>
        )}
        {isAdmin && detail.status === "PAID" && (
          <Btn variant="blue" onClick={() => onAction(detail.id, "process", "In lavorazione")}>
            ⚙ Processa
          </Btn>
        )}
        {isAdmin && detail.status === "PROCESSING" && (
          <Btn variant="blue" onClick={() => onAction(detail.id, "ship", "Spedito")}>
            📦 Spedisci
          </Btn>
        )}
        {isAdmin && detail.status === "SHIPPED" && (
          <Btn variant="success" onClick={() => onAction(detail.id, "deliver", "Consegnato")}>
            ✓ Consegna
          </Btn>
        )}
        {!["DELIVERED", "CANCELLED", "PENDING"].includes(detail.status) && (
          <Btn variant="danger" onClick={() => onAction(detail.id, "cancel", "Annullato")}>
            Annulla
          </Btn>
        )}
      </div>
    </div>
  );
}
