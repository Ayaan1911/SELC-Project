import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";

export default function OrderDetail() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setOrder(null);
    setError("");
    api(`/orders/${id}`).then(setOrder).catch((err) => setError(err.message));
  }, [id]);

  if (error) return <div className="error">{error}</div>;
  if (!order) return <p>Loading...</p>;

  return (
    <div className="card">
      <h1>Order #{order.id}</h1>
      <p>
        Placed {order.created_at} &middot; {order.status} &middot; card ending{" "}
        {order.card_last4}
      </p>
      <table>
        <thead>
          <tr><th>Product</th><th>Qty</th><th>Price</th></tr>
        </thead>
        <tbody>
          {order.items.map((i, idx) => (
            <tr key={idx}>
              <td>{i.product_name}</td>
              <td>{i.quantity}</td>
              <td>${(i.price * i.quantity).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="price">Total: ${order.total.toFixed(2)}</p>
    </div>
  );
}
