import { useEffect, useState } from "react";
import { api } from "../api";

const blank = { text: "", options: ["", "", "", ""], correct: 0 };

function downloadSample() {
  const csv = [
    "question,option_a,option_b,option_c,option_d,correct",
    "Which keyword defines a function in Python?,def,func,function,lambda,A",
    "Which SQL clause filters rows?,WHERE,ORDER BY,GROUP BY,LIMIT,A",
    "What does HTTP status 404 mean?,Server error,Not found,Forbidden,OK,B",
  ].join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = "questions_sample.csv";
  a.click();
}

export default function TestManager({ job }) {
  const [t, setT] = useState(null);
  const [q, setQ] = useState(blank);
  const [cfg, setCfg] = useState({ pass_percent: 60, duration_min: 20 });
  const [file, setFile] = useState(null);
  const [msg, setMsg] = useState("");

  const load = () => api.test(job.id).then((d) => {
    setT(d);
    setCfg({ pass_percent: d.pass_percent, duration_min: d.duration_min });
  }).catch((e) => setMsg(e.message));
  useEffect(() => { load(); }, [job.id]);

  const setOpt = (i, v) => setQ({ ...q, options: q.options.map((o, j) => (j === i ? v : o)) });

  async function add(e) {
    e.preventDefault();
    setMsg("");
    try { await api.addQuestion(job.id, q); setQ(blank); setMsg("Question added."); load(); }
    catch (ex) { setMsg(ex.message); }
  }
  async function saveCfg() {
    try { await api.setTestConfig(job.id, cfg); setMsg("Test settings saved."); }
    catch (ex) { setMsg(ex.message); }
  }
  async function upload() {
    if (!file) { setMsg("Choose a file first."); return; }
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await api.uploadQuestions(job.id, fd);
      setMsg(`Added ${r.added} question(s).` + (r.errors.length ? " Problems: " + r.errors.join(" | ") : ""));
      setFile(null);
      load();
    } catch (ex) { setMsg(ex.message); }
  }
  async function del(id) {
    try { await api.deleteQuestion(id); load(); } catch (ex) { setMsg(ex.message); }
  }

  return (
    <div>
      <h4>Screening test</h4>
      <p className="muted">
        {t ? `${t.questions.length} question(s). Shortlisted candidates receive the test once at least ${t.min_questions} exist. Do not edit questions after candidates have started.` : "Loading..."}
      </p>
      <div className="grid">
        <label>Pass mark (%)
          <input type="number" min="1" max="100" value={cfg.pass_percent} onChange={(e) => setCfg({ ...cfg, pass_percent: Number(e.target.value) })} />
        </label>
        <label>Time limit (minutes)
          <input type="number" min="5" max="180" value={cfg.duration_min} onChange={(e) => setCfg({ ...cfg, duration_min: Number(e.target.value) })} />
        </label>
        <button onClick={saveCfg}>Save settings</button>
      </div>

      <form className="stack" onSubmit={add} style={{ marginTop: 12 }}>
        <textarea rows={2} placeholder="Question text" value={q.text} onChange={(e) => setQ({ ...q, text: e.target.value })} required />
        {q.options.map((o, i) => (
          <div key={i} style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="radio" name="correct" title="Mark as correct answer" checked={q.correct === i} onChange={() => setQ({ ...q, correct: i })} />
            <input value={o} placeholder={`Option ${"ABCD"[i]}${q.correct === i ? " (correct)" : ""}`} onChange={(e) => setOpt(i, e.target.value)} />
          </div>
        ))}
        <button type="submit">Add question</button>
      </form>

      <div style={{ marginTop: 12 }}>
        <input type="file" accept=".csv,.pdf,.txt" onChange={(e) => setFile(e.target.files[0])} />
        <button onClick={upload}>Upload file</button>{" "}
        <button onClick={downloadSample}>Download sample CSV</button>
        <p className="muted">PDF or TXT: number each question (1. 2. 3.), put each option on its own line starting A) B) C) D), and add "Answer: B" under each question or an Answer Key at the end. CSV also works (use Download sample CSV).</p>
      </div>

      {msg && <p className="muted">{msg}</p>}
      {t && t.questions.map((x, i) => (
        <div className="note" key={x.id}>
          <b>{i + 1}. {x.text}</b> <button className="danger" onClick={() => del(x.id)}>Delete</button>
          <div className="muted">{x.options.map((o, j) => `${"ABCDEF"[j]}) ${o}${j === x.correct ? " [correct]" : ""}`).join("   ")}</div>
        </div>
      ))}
    </div>
  );
}