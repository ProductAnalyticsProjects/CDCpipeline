import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { useToast } from "../context/ToastContext";
import { colors } from "../styles/theme";
import {
  Btn, Input, TextArea, Card, Table, Pagination,
  Modal, Badge, PageHeader, Loading,
} from "../components/ui";

export default function ProductsPage() {
  const api = useApi();
  const toast = useToast();
  const { isAdmin } = useAuth();

  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [modal, setModal] = useState(null); // null | 'create' | product obj
  const [form, setForm] = useState({ name: "", description: "", basePrice: "", sku: "" });

  const PAGE_SIZE = 15;

  const load = useCallback(
    async (p = 0) => {
      setLoading(true);
      try {
        const data = await api.get(`/products?page=${p}&size=${PAGE_SIZE}&sort=createdAt,desc`);
        setProducts(data.content || data);
        setTotal(data.totalElements ?? (data.content || data).length);
        setPage(p);
      } catch (e) {
        toast.error(e.message);
      } finally {
        setLoading(false);
      }
    },
    [api, toast],
  );

  useEffect(() => {
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    try {
      const payload = { ...form, basePrice: parseFloat(form.basePrice) };
      if (modal === "create") {
        await api.post("/products", payload);
        toast.success("Prodotto creato");
      } else {
        await api.put(`/products/${modal.id}`, payload);
        toast.success("Prodotto aggiornato");
      }
      setModal(null);
      load(page);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const toggleActive = async (p) => {
    try {
      await api.post(`/products/${p.id}/${p.isActive ? "deactivate" : "activate"}`);
      toast.success(p.isActive ? "Disattivato" : "Attivato");
      load(page);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const deleteProduct = async (p) => {
    if (!confirm(`Eliminare "${p.name}"?`)) return;
    try {
      await api.del(`/products/${p.id}`);
      toast.success("Eliminato");
      load(page);
    } catch (e) {
      toast.error(e.message);
    }
  };

  const openEdit = (p) => {
    setForm({
      name: p.name,
      description: p.description || "",
      basePrice: String(p.basePrice),
      sku: p.sku,
    });
    setModal(p);
  };

  const openCreate = () => {
    setForm({ name: "", description: "", basePrice: "", sku: "" });
    setModal("create");
  };

  const columns = [
    {
      key: "sku",
      label: "SKU",
      render: (r) => (
        <span style={{ color: colors.accent, fontWeight: 600 }}>{r.sku}</span>
      ),
    },
    { key: "name", label: "Nome" },
    {
      key: "basePrice",
      label: "Prezzo",
      render: (r) => `€ ${Number(r.basePrice).toFixed(2)}`,
    },
    {
      key: "isActive",
      label: "Stato",
      render: (r) => (
        <Badge color={r.isActive ? colors.success : colors.danger}>
          {r.isActive ? "Attivo" : "Inattivo"}
        </Badge>
      ),
    },
    ...(isAdmin
      ? [
          {
            key: "actions",
            label: "",
            render: (r) => (
              <div
                style={{ display: "flex", gap: 4 }}
                onClick={(e) => e.stopPropagation()}
              >
                <Btn small variant="ghost" onClick={() => openEdit(r)}>✎</Btn>
                <Btn small variant="ghost" onClick={() => toggleActive(r)}>
                  {r.isActive ? "⏻" : "▶"}
                </Btn>
                <Btn small variant="danger" onClick={() => deleteProduct(r)}>✕</Btn>
              </div>
            ),
          },
        ]
      : []),
  ];

  return (
    <div>
      <PageHeader
        title="Prodotti"
        subtitle={`${total} prodotti nel catalogo`}
        action={isAdmin && <Btn onClick={openCreate}>+ Nuovo Prodotto</Btn>}
      />

      <Card>
        {loading ? (
          <Loading />
        ) : (
          <>
            <Table columns={columns} data={products} />
            <Pagination page={page} size={PAGE_SIZE} total={total} onChange={load} />
          </>
        )}
      </Card>

      <Modal
        open={!!modal}
        onClose={() => setModal(null)}
        title={modal === "create" ? "Nuovo Prodotto" : "Modifica Prodotto"}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Input
            label="Nome"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Input
            label="SKU"
            value={form.sku}
            onChange={(e) => setForm({ ...form, sku: e.target.value })}
            disabled={modal !== "create"}
          />
          <Input
            label="Prezzo base (€)"
            type="number"
            step="0.01"
            value={form.basePrice}
            onChange={(e) => setForm({ ...form, basePrice: e.target.value })}
          />
          <TextArea
            label="Descrizione"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={3}
          />
          <Btn onClick={save} style={{ marginTop: 8 }}>
            {modal === "create" ? "Crea" : "Salva"}
          </Btn>
        </div>
      </Modal>
    </div>
  );
}
