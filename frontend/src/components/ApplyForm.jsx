import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

function MicTextarea({ value, onChange }) {
  const [on, setOn] = useState(false);
  const ref = useRef(null);
  const latest = useRef(value);
  latest.current = value;

  function toggle() {
    if (on) { ref.current?.stop(); return; }
    const r = new SR();
    r.lang = "en-IN";
    r.continuous = true;
    r.onresult = (e) => {
      let t = "";
      for (let i = e.resultIndex; i < e.results.length; i++) t += e.results[i][0].transcript;
      onChange((latest.current ? latest.current + " " : "") + t.trim());
    };
    r.onend = () => setOn(false);
    ref.current = r;
    r.start();
    setOn(true);
  }

  return (
    <>
      <textarea rows={3} value={value} onChange={(e) => onChange(e.target.value)} />
      {SR && <button type="button" onClick={toggle}>{on ? "Stop mic" : "Answer by voice"}</button>}
    </>
  );
}

export default function ApplyForm({ job, onDone, onCancel }) {
  const [qs, setQs] = useState([]);
  const [college, setCollege] = useState("");
  const [skills, setSkills] = useState("");
  const [file, setFile] = useState(null);
  const [ans, setAns] = useState({});
  const [err, setErr] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.questions().then(setQs).catch((e) => setErr(e.message)); }, []);
  const set = (k) => (v) => setAns((a) => ({ ...a, [k]: v }));

  async function submit(e) {
    e.preventDefault();
    setErr("");
    if (!file) { setErr("Please attach your resume (PDF)."); return; }
    const fd = new FormData();
    fd.append("college", college);
    fd.append("skills", skills);
    fd.append("answers", JSON.stringify(ans));
    fd.append("resume", file);
    setBusy(true);
    try { setResult(await api.apply(job.id, fd)); }
    catch (ex) { setErr(ex.message); }
    finally { setBusy(false); }
  }

  if (result) {
    return (
      <div className="card">
        <h3>Application submitted</h3>
        <p>Status: <b>{result.status}</b> | Match score: <b>{result.total}/100</b></p>
        {result.breakdown.missing_skills.length > 0 &&
          <p className="muted">Skills not found on your resume or list: {result.breakdown.missing_skills.join(", ")}</p>}
        <p className="muted">You will be notified here and by email about the next steps.</p>
        <button onClick={onDone}>Back to jobs</button>
      </div>
    );
  }

  return (
    <form className="card stack" onSubmit={submit}>
      <h3>Apply: {job.title}</h3>
      <p className="muted">Required skills: {job.required_skills} | {job.work_mode} {job.location} | {job.duration_months} months | {job.stipend}</p>
      <label>College / university<input value={college} onChange={(e) => setCollege(e.target.value)} required /></label>
      <label>Your skills (comma separated)<input value={skills} onChange={(e) => setSkills(e.target.value)} required placeholder="Python, React, SQL" /></label>
      <label>Resume (PDF or TXT, max 5 MB)<input type="file" accept=".pdf,.txt" onChange={(e) => setFile(e.target.files[0])} required /></label>
      <h4>Screening questions</h4>
      {qs.map((q) => (
        <label key={q.key}>
          {q.text}
          {q.type === "text" && <MicTextarea value={ans[q.key] || ""} onChange={set(q.key)} />}
          {q.type === "select" && (
            <select value={ans[q.key] || ""} onChange={(e) => set(q.key)(e.target.value)} required={!q.optional}>
              <option value="">Select...</option>
              {q.options.map((o) => <option key={o}>{o}</option>)}
            </select>
          )}
          {q.type === "date" && <input type="date" value={ans[q.key] || ""} onChange={(e) => set(q.key)(e.target.value)} required />}
          {q.type === "number" && <input type="number" min="1" max="24" value={ans[q.key] || ""} onChange={(e) => set(q.key)(e.target.value)} required />}
        </label>
      ))}
      {err && <p className="err">{err}</p>}
      <div className="row">
        <button type="button" onClick={onCancel}>Cancel</button>
        <button type="submit" disabled={busy}>{busy ? "Submitting..." : "Submit application"}</button>
      </div>
    </form>
  );
}