import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

export default function Register() {
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const navigate = useNavigate();

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      await api("/register", { method: "POST", body: form });
      navigate("/login");
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="card narrow">
      <h1>Register</h1>
      <form onSubmit={submit}>
        <label>Username</label>
        <input value={form.username} onChange={set("username")} />
        <label>Email</label>
        <input value={form.email} onChange={set("email")} />
        <label>Password</label>
        <input type="password" value={form.password} onChange={set("password")} />
        <button className="primary" type="submit">Create account</button>
      </form>
      {error && <div className="error">{error}</div>}
    </div>
  );
}
