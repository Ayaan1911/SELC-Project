import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, getSession } from "../api.js";

export default function ProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const loggedIn = !!getSession();

  async function load() {
    try {
      setProduct(await api(`/products/${id}`));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  async function addToCart() {
    if (!loggedIn) return navigate("/login");
    setError("");
    try {
      await api("/cart", { method: "POST", body: { product_id: Number(id), quantity: 1 } });
      setMessage("Added to cart");
    } catch (err) {
      setError(err.message);
    }
  }

  async function submitReview(e) {
    e.preventDefault();
    setError("");
    try {
      await api(`/products/${id}/reviews`, {
        method: "POST",
        body: { rating: Number(rating), review_text: text },
      });
      setText("");
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!product) return error ? <div className="error">{error}</div> : <p>Loading...</p>;

  return (
    <>
      <div className="card">
        <h1>{product.name}</h1>
        <p>{product.description}</p>
        <div className="price">${Number(product.price).toFixed(2)}</div>
        <p><small>{product.stock} in stock</small></p>
        <button className="primary" onClick={addToCart}>Add to cart</button>
        {message && <div className="ok">{message}</div>}
        {error && <div className="error">{error}</div>}
      </div>

      <div className="card">
        <h2>Reviews</h2>
        {product.reviews.length === 0 && <p>No reviews yet.</p>}
        {product.reviews.map((r) => (
          <div className="review" key={r.id}>
            <strong>{r.username}</strong> &middot; {"★".repeat(r.rating)}{" "}
            <small>{r.created_at}</small>
            {/* VULN-07 FIXED: rendered as plain text, never raw HTML (CWE-79) */}
            <div>{r.review_text}</div>
          </div>
        ))}

        {loggedIn ? (
          <form onSubmit={submitReview} style={{ marginTop: 16 }}>
            <label>Rating</label>
            <select value={rating} onChange={(e) => setRating(e.target.value)}>
              {[5, 4, 3, 2, 1].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <label>Your review</label>
            <textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} />
            <button className="primary" type="submit">Post review</button>
          </form>
        ) : (
          <p>Log in to write a review.</p>
        )}
      </div>
    </>
  );
}
