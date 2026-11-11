import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

export default function ProductList() {
  const [products, setProducts] = useState([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  async function load(q) {
    setError("");
    try {
      const path = q ? `/products/search?q=${encodeURIComponent(q)}` : "/products";
      setProducts(await api(path));
    } catch (err) {
      setProducts([]);
      setError(err.message);
    }
  }

  useEffect(() => {
    load("");
  }, []);

  function search(e) {
    e.preventDefault();
    load(query);
  }

  return (
    <>
      <h1>Products</h1>
      <form onSubmit={search} className="row" style={{ marginBottom: 16 }}>
        <input
          placeholder="Search products..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button className="primary" type="submit">Search</button>
      </form>
      {error && <div className="error">{error}</div>}
      <div className="grid">
        {products.map((p) => (
          <div className="card" key={p.id}>
            <h2><Link to={`/products/${p.id}`}>{p.name}</Link></h2>
            <p>{p.description}</p>
            <div className="price">${Number(p.price).toFixed(2)}</div>
            <small>{p.stock} in stock</small>
          </div>
        ))}
      </div>
      {!error && products.length === 0 && <p>No products found.</p>}
    </>
  );
}
