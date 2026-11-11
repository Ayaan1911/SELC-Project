import { useEffect, useState } from "react";
import { api } from "../api.js";

const EMPTY = { name: "", description: "", price: "", stock: "" };

export default function Admin() {
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    setProducts(await api("/products"));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  async function save(e) {
    e.preventDefault();
    setError("");
    const body = {
      name: form.name,
      description: form.description,
      price: Number(form.price),
      stock: Number(form.stock || 0),
    };
    try {
      if (editingId) {
        await api(`/admin/products/${editingId}`, { method: "PUT", body });
      } else {
        await api("/admin/products", { method: "POST", body });
      }
      setForm(EMPTY);
      setEditingId(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  function edit(p) {
    setEditingId(p.id);
    setForm({ name: p.name, description: p.description, price: p.price, stock: p.stock });
  }

  async function remove(id) {
    setError("");
    try {
      await api(`/admin/products/${id}`, { method: "DELETE" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <h1>Admin: manage products</h1>
      {error && <div className="error">{error}</div>}

      <div className="card">
        <h2>{editingId ? `Edit product #${editingId}` : "Add product"}</h2>
        <form onSubmit={save}>
          <label>Name</label>
          <input value={form.name} onChange={set("name")} />
          <label>Description</label>
          <input value={form.description} onChange={set("description")} />
          <label>Price</label>
          <input type="number" step="0.01" value={form.price} onChange={set("price")} />
          <label>Stock</label>
          <input type="number" value={form.stock} onChange={set("stock")} />
          <button className="primary" type="submit">{editingId ? "Save changes" : "Add product"}</button>{" "}
          {editingId && (
            <button type="button" onClick={() => { setEditingId(null); setForm(EMPTY); }}>
              Cancel
            </button>
          )}
        </form>
      </div>

      <table>
        <thead>
          <tr><th>ID</th><th>Name</th><th>Price</th><th>Stock</th><th /></tr>
        </thead>
        <tbody>
          {products.map((p) => (
            <tr key={p.id}>
              <td>{p.id}</td>
              <td>{p.name}</td>
              <td>${Number(p.price).toFixed(2)}</td>
              <td>{p.stock}</td>
              <td>
                <button className="small" onClick={() => edit(p)}>Edit</button>{" "}
                <button className="danger small" onClick={() => remove(p.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
