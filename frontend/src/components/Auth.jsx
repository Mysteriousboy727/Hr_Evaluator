import { useState } from "react";
import { api } from "../api";

export default function Auth({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: "", password: "", phone: "", role: "student", hr_code: "" });
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setErr("");
    try {
      const d = mode === "login" ? await api.login({ email: f.email, password: f.password }) : await api.register(f);
      onAuth(d);
    } catch (ex) { setErr(ex.message); }
  }

  return (
    <form className="card stack auth-card" onSubmit={submit}>
      <div className="brand"><span className="mark">A</span>Akshara Hiring</div>
      <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
      <p className="muted">{mode === "login" ? "Sign in to continue." : "Students apply for roles. HR posts roles and reviews candidates."}</p>
      <div className="seg">
        <button type="button" className={mode === "login" ? "on" : ""} onClick={() => setMode("login")}>Sign in</button>
        <button type="button" className={mode === "register" ? "on" : ""} onClick={() => setMode("register")}>Register</button>
      </div>
      {mode === "register" && (
        <>
          <select value={f.role} onChange={set("role")}>
            <option value="student">I am a student</option>
            <option value="hr">I am HR</option>
          </select>
          <input placeholder="Full name" value={f.name} onChange={set("name")} required />
          <input placeholder="Phone" value={f.phone} onChange={set("phone")} required />
          {f.role === "hr" && <input placeholder="HR signup code" value={f.hr_code} onChange={set("hr_code")} required />}
        </>
      )}
      <input type="email" placeholder="Email" value={f.email} onChange={set("email")} required />
      <input type="password" placeholder="Password (min 6 characters)" value={f.password} onChange={set("password")} required />
      <button type="submit">{mode === "login" ? "Sign in" : "Create account"}</button>
      {err && <p className="err">{err}</p>}
    </form>
  );
}