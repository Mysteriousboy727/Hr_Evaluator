import { useEffect, useState } from "react";
import { api } from "../api";

export default function Notifications({ onRead }) {
  const [items, setItems] = useState([]);
  useEffect(() => {
    api.notifications().then((d) => { setItems(d.items); return api.markRead(); }).then(onRead).catch(console.error);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div className="card">
      <h3>Notifications</h3>
      {items.length === 0 && <p className="muted">Nothing yet.</p>}
      {items.map((n) => (
        <div key={n.id} className="note">
          <b>{n.title}</b> {!n.read && <span className="badge">new</span>}
          <div className="muted">{n.created_at.replace("T", " ")} UTC</div>
          <pre>{n.body}</pre>
        </div>
      ))}
    </div>
  );
}