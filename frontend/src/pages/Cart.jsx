import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

export default function Cart() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      setItems(await api("/cart"));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function remove(id) {
    await api(`/cart/${id}`, { method: "DELETE" });
    load();
  }

  const total = items.reduce((sum, i) => sum + i.price * i.quantity, 0);

  return (
    <>
      <h1>Your cart</h1>
      {error && <div className="error">{error}</div>}
      {items.length === 0 ? (
        <p>Your cart is empty. <Link to="/">Browse products</Link></p>
      ) : (
        <>
          <table>
            <thead>
              <tr><th>Product</th><th>Qty</th><th>Price</th><th /></tr>
            </thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.id}>
                  <td>{i.name}</td>
                  <td>{i.quantity}</td>
                  <td>${(i.price * i.quantity).toFixed(2)}</td>
                  <td><button className="danger small" onClick={() => remove(i.id)}>Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="price">Total: ${total.toFixed(2)}</p>
          <Link to="/checkout"><button className="primary">Checkout</button></Link>
        </>
      )}
    </>
  );
}
