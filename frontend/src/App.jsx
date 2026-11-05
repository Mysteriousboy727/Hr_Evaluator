import { useEffect, useState } from "react";
import { api } from "./api";
import Auth from "./components/Auth.jsx";
import StudentDashboard from "./components/StudentDashboard.jsx";
import HrDashboard from "./components/HrDashboard.jsx";
import Notifications from "./components/Notifications.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState("main");
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!localStorage.getItem("token")) { setReady(true); return; }
    api.me().then(setUser).catch(() => localStorage.removeItem("token")).finally(() => setReady(true));
  }, []);

  useEffect(() => {
    if (!user) return undefined;
    const f = () => api.notifications().then((d) => setUnread(d.unread)).catch(() => {});
    f();
    const t = setInterval(f, 15000);
    return () => clearInterval(t);
  }, [user, tab]);

  function logout() { localStorage.removeItem("token"); setUser(null); setTab("main"); }

  if (!ready) return <main className="wrap muted">Loading...</main>;
  if (!user) {
    return (
      <main className="auth-page">
        <Auth onAuth={(d) => { localStorage.setItem("token", d.token); setUser(d.user); }} />
      </main>
    );
  }

  return (
    <>
      <header className="nav">
        <div className="nav-in">
          <div className="brand"><span className="mark">A</span>Akshara Hiring</div>
          <div className="seg">
            <button className={tab === "main" ? "on" : ""} onClick={() => setTab("main")}>
              {user.role === "hr" ? "Roles" : "Jobs"}
            </button>
            <button className={tab === "notes" ? "on" : ""} onClick={() => setTab("notes")}>
              Notifications{unread > 0 && <span className="dot">{unread}</span>}
            </button>
          </div>
          <div className="who">
            <span className="who-name">{user.name}</span>
            <span className="pill">{user.role === "hr" ? "HR" : "Student"}</span>
            <button className="ghost" onClick={logout}>Sign out</button>
          </div>
        </div>
      </header>
      <main className="wrap">
        {tab === "notes" ? <Notifications onRead={() => setUnread(0)} />
          : user.role === "hr" ? <HrDashboard /> : <StudentDashboard />}
      </main>
    </>
  );
}