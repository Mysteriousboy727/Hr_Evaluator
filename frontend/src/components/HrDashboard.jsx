import { Fragment, useEffect, useState } from "react";
import { api } from "../api";
import TestManager from "./TestManager.jsx";
import AiInterviewView from "./AiInterviewView.jsx";
import InterviewSettings from "./InterviewSettings.jsx";
import { badgeTone } from "../ui.js";

const emptyJob = { title: "", description: "", required_skills: "", location: "", work_mode: "onsite", stipend: "", duration_months: 3, threshold: 60 };

function JobForm({ onCreated }) {
  const [f, setF] = useState(emptyJob);
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function submit(e) {
    e.preventDefault();
    setErr("");
    try {
      await api.createJob({ ...f, duration_months: Number(f.duration_months), threshold: Number(f.threshold) });
      setF(emptyJob);
      onCreated();
    } catch (ex) { setErr(ex.message); }
  }
  return (
    <form className="card stack" onSubmit={submit}>
      <h3>Post a role</h3>
      <div className="grid">
        <input placeholder="Role title" value={f.title} onChange={set("title")} required />
        <input placeholder="Required skills (comma separated)" value={f.required_skills} onChange={set("required_skills")} required />
        <input placeholder="Location" value={f.location} onChange={set("location")} />
        <select value={f.work_mode} onChange={set("work_mode")}>
          <option value="onsite">Onsite</option><option value="hybrid">Hybrid</option><option value="remote">Remote</option>
        </select>
        <input placeholder="Stipend (e.g. Rs 10,000/month)" value={f.stipend} onChange={set("stipend")} />
        <input type="number" min="1" max="24" title="Duration in months" value={f.duration_months} onChange={set("duration_months")} />
        <input type="number" min="0" max="100" title="Auto-shortlist score threshold" value={f.threshold} onChange={set("threshold")} />
      </div>
      <p className="muted">Fields: duration (months) and auto-shortlist threshold (0-100) are the last two boxes.</p>
      <textarea rows={2} placeholder="Description" value={f.description} onChange={set("description")} />
      <button type="submit">Post role</button>
      {err && <p className="err">{err}</p>}
    </form>
  );
}

function genSlots(date, from, to) {
  const out = [];
  const [h, m] = from.split(":").map(Number);
  const [eh, em] = to.split(":").map(Number);
  let cur = h * 60 + m;
  const end = eh * 60 + em;
  while (cur + 30 <= end) {
    out.push(`${date}T${String(Math.floor(cur / 60)).padStart(2, "0")}:${String(cur % 60).padStart(2, "0")}`);
    cur += 30;
  }
  return out;
}

function JobPanel({ job, onChange }) {
  const [slots, setSlots] = useState([]);
  const [apps, setApps] = useState([]);
  const [open, setOpen] = useState(null);
  const [ai, setAi] = useState(null);
  const [rng, setRng] = useState({ date: "", from: "10:00", to: "13:00" });
  const [msg, setMsg] = useState("");

  const load = () => {
    api.slots(job.id).then(setSlots).catch(console.error);
    api.jobApps(job.id).then(setApps).catch(console.error);
  };
  useEffect(() => { load(); }, [job.id]);

  async function addSlots() {
    const list = genSlots(rng.date, rng.from, rng.to);
    if (!rng.date || list.length === 0) { setMsg("Pick a date and a time range of at least 30 minutes."); return; }
    const r = await api.addSlots(job.id, list);
    setMsg(`Added ${r.added} slot(s), skipped ${r.skipped} (past or overlapping). Waiting candidates were booked automatically.`);
    load(); onChange();
  }
  async function decide(id, d) {
    try { await api.decide(id, d); load(); onChange(); } catch (e) { setMsg(e.message); }
  }

  return (
    <div className="card">
      <h3>{job.title} - applicants</h3>
      <InterviewSettings job={job} />
      <TestManager job={job} />
      <h4>Interview slots (30 min each, IST)</h4>
      <div className="grid">
        <input type="date" value={rng.date} onChange={(e) => setRng({ ...rng, date: e.target.value })} />
        <input type="time" value={rng.from} onChange={(e) => setRng({ ...rng, from: e.target.value })} />
        <input type="time" value={rng.to} onChange={(e) => setRng({ ...rng, to: e.target.value })} />
        <button onClick={addSlots}>Add slots</button>
      </div>
      {msg && <p className="muted">{msg}</p>}
      <div className="muted">
        {slots.length === 0 ? "No slots yet." : slots.map((s) => (
          <span key={s.id} className="chip">{s.start.replace("T", " ")} {s.booked ? `- ${s.student}` : "(free)"}</span>
        ))}
      </div>
      <h4>Applicants (highest score first)</h4>
      <table>
        <thead><tr><th>Candidate</th><th>College</th><th>Score</th><th>Status</th><th>Interview</th><th></th></tr></thead>
        <tbody>
          {apps.map((a) => (
            <Fragment key={a.id}>
              <tr>
                <td>{a.student}<div className="muted">{a.email} | {a.phone}</div></td>
                <td>{a.college}</td>
                <td>{a.total_score}<div className="muted">resume {a.resume_score} / answers {a.answer_score}</div></td>
                <td><span className={"badge " + badgeTone(a.status)}>{a.status}</span></td>
                <td>{a.slot_start ? a.slot_start.replace("T", " ") : "-"}</td>
                <td>
                  <button onClick={() => setOpen(open === a.id ? null : a.id)}>Details</button>{" "}
                  <button onClick={() => api.resume(a.id).catch((e) => setMsg(e.message))}>Resume</button>{" "}
                  <button onClick={() => setAi(ai === a.id ? null : a.id)}>AI interview</button>{" "}
                  {["Under HR Review", "Not Shortlisted", "Rejected by HR", "Test Failed", "AI Interview Pending"].includes(a.status) &&
                    <button onClick={() => decide(a.id, "shortlist")}>Shortlist</button>}{" "}
                  {a.status !== "Rejected by HR" && <button className="danger" onClick={() => decide(a.id, "reject")}>Reject</button>}
                </td>
              </tr>
              {open === a.id && (
                <tr><td colSpan={6}>
                  <pre>{[
                    `Matched on resume: ${a.breakdown.matched_skills.join(", ") || "-"}`,
                    `Declared only: ${a.breakdown.declared_only.join(", ") || "-"}`,
                    `Missing: ${a.breakdown.missing_skills.join(", ") || "-"}`,
                    `Knockouts: ${a.breakdown.knockouts.join("; ") || "none"}`,
                    a.breakdown.warnings.length ? `Warnings: ${a.breakdown.warnings.join("; ")}` : "",
                    `Skills listed: ${a.skills}`, "",
                    ...Object.entries(a.answers).map(([k, v]) => `${k}: ${v}`),
                  ].filter((x) => x !== "").join("\n")}</pre>
                </td></tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
      {apps.length === 0 && <p className="muted">No applications yet.</p>}
      {ai && <AiInterviewView appId={ai} />}
    </div>
  );
}

export default function HrDashboard() {
  const [jobs, setJobs] = useState([]);
  const [sel, setSel] = useState(null);
  const load = () => api.jobs().then(setJobs).catch(console.error);
  useEffect(() => { load(); }, []);
  const selected = jobs.find((j) => j.id === sel);

  return (
    <>
      <JobForm onCreated={load} />
      <div className="card">
        <h3>My roles</h3>
        {jobs.length === 0 && <p className="muted">No roles posted yet.</p>}
        {jobs.map((j) => (
          <div className="row" key={j.id}>
            <div>
              <b>{j.title}</b> <span className="badge">{j.status}</span>
              <div className="muted">{j.applicants} applicants | {j.shortlisted} shortlisted | {j.free_slots} free slots | threshold {j.threshold}</div>
            </div>
            <div>
              <button onClick={() => setSel(j.id)}>Open</button>{" "}
              {j.status === "open" && <button className="danger" onClick={() => api.closeJob(j.id).then(load)}>Close</button>}
            </div>
          </div>
        ))}
      </div>
      {selected && <JobPanel job={selected} onChange={load} />}
    </>
  );
}