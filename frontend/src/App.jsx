import { useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { clearSession, getSession } from "./api.js";
import Admin from "./pages/Admin.jsx";
import Cart from "./pages/Cart.jsx";
import Checkout from "./pages/Checkout.jsx";
import Login from "./pages/Login.jsx";
import OrderDetail from "./pages/OrderDetail.jsx";
import Orders from "./pages/Orders.jsx";
import ProductDetail from "./pages/ProductDetail.jsx";
import ProductList from "./pages/ProductList.jsx";
import Register from "./pages/Register.jsx";

export default function App() {
  const [session, setSession] = useState(getSession());
  const navigate = useNavigate();

  function logout() {
    clearSession();
    setSession(null);
    navigate("/login");
  }

  return (
    <>
      <div className="banner">
        SecureCart v1 is INTENTIONALLY VULNERABLE. Run on localhost only.
      </div>
      <nav>
        <Link to="/">SecureCart</Link>
        {session && <Link to="/cart">Cart</Link>}
        {session && <Link to="/orders">Orders</Link>}
        {session?.role === "admin" && <Link to="/admin">Admin</Link>}
        <span className="spacer" />
        {session ? (
          <>
            <span style={{ color: "#fff" }}>{session.username}</span>
            <button onClick={logout}>Logout</button>
          </>
        ) : (
          <>
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<ProductList />} />
          <Route path="/products/:id" element={<ProductDetail />} />
          <Route path="/login" element={<Login onLogin={setSession} />} />
          <Route path="/register" element={<Register />} />
          <Route path="/cart" element={session ? <Cart /> : <Navigate to="/login" />} />
          <Route path="/checkout" element={session ? <Checkout /> : <Navigate to="/login" />} />
          <Route path="/orders" element={session ? <Orders /> : <Navigate to="/login" />} />
          <Route path="/orders/:id" element={session ? <OrderDetail /> : <Navigate to="/login" />} />
          <Route path="/admin" element={session ? <Admin /> : <Navigate to="/login" />} />
        </Routes>
      </main>
    </>
  );
}
