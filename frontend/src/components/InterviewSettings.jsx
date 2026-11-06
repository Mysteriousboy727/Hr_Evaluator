import { useEffect, useState } from "react";
import { api } from "../api";

export default function InterviewSettings({ job }) {
  const [c, setC] = useState({ role_type: "tech", focus: "" });
  const [msg, setMsg] = useState("");
  useEffect(() => {
    setMsg("");
    api.interviewConfig(job.id).then(setC).catch((e) => setMsg(e.message));
  }, [job.id]);

  async function save() {
    try { await api.setInterviewConfig(job.id, c); setMsg("Saved. New AI interviews will use this."); }
    catch (e) { setMsg(e.message); }
  }

  return (
    <div>
      <h4>AI interview</h4>
      <div className="grid">
        <label>Role type
          <select value={c.role_type} onChange={(e) => setC({ ...c, role_type: e.target.value })}>
            <option value="tech">Technical (skills, projects, problem solving)</option>
            <option value="non_tech">Non-technical (experience, communication, scenarios)</option>
          </select>
        </label>
        <label>Focus areas (optional)
          <input value={c.focus} maxLength={500} placeholder="e.g. handling difficult customers, Excel, negotiation" onChange={(e) => setC({ ...c, focus: e.target.value })} />
        </label>
        <button onClick={save}>Save</button>
      </div>
      {msg && <p className="muted">{msg}</p>}
    </div>
  );
}