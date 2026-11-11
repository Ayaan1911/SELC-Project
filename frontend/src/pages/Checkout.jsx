import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

export default function Checkout() {
  const [form, setForm] = useState({ card_name: "", card_number: "", expiry: "" });
  const [error, setError] = useState("");
  const navigate = useNavigate();

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  async function pay(e) {
    e.preventDefault();
    setError("");
    try {
      const order = await api("/checkout", { method: "POST", body: form });
      navigate(`/orders/${order.order_id}`);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="card narrow">
      <h1>Checkout</h1>
      <p><strong>MOCK PAYMENT.</strong> Nothing is charged. Use a dummy number such as
        4242 4242 4242 4242. Never enter a real card.</p>
      <form onSubmit={pay}>
        <label>Name on card</label>
        <input value={form.card_name} onChange={set("card_name")} />
        <label>Card number (dummy)</label>
        <input value={form.card_number} onChange={set("card_number")} placeholder="4242424242424242" />
        <label>Expiry</label>
        <input value={form.expiry} onChange={set("expiry")} placeholder="12/30" />
        <button className="primary" type="submit">Place order</button>
      </form>
      {error && <div className="error">{error}</div>}
    </div>
  );
}
