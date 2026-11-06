import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

export default function TestRunner({ app, onDone }) {
  const [data, setData] = useState(null);
  const [ans, setAns] = useState({});
  const [left, setLeft] = useState(0);
  const [err, setErr] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const sent = useRef(false);
  const ansRef = useRef({});
  ansRef.current = ans;

  async function start() {
    setErr("");
    try {
      const d = await api.startTest(app.id);
      setData(d);
      setLeft(d.seconds_left);
    } catch (e) { setErr(e.message); }
  }

  async function submit() {
    if (sent.current) return;
    sent.current = true;
    setBusy(true);
    try { setResult(await api.submitTest(app.id, ansRef.current)); }
    catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }
  function retry() { sent.current = false; submit(); }

  useEffect(() => {
    if (!data || result) return undefined;
    const t = setInterval(() => setLeft((s) => s - 1), 1000);
    return () => clearInterval(t);
  }, [data, result]);

  useEffect(() => {
    if (data && !result && left <= 0) submit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [left, data]);

  if (result) {
    return (
      <div className="card">
        <h3>Test submitted</h3>
        <p>You scored <b>{result.percent}%</b> ({result.correct}/{result.total} correct).
          {result.late ? " Your time had expired, so your answers were not counted." : ""}</p>
        <p>{result.passed
          ? "You passed. Open My applications for your next step (the AI interview, or your interview booking)."
          : "You did not reach the pass mark this time. HR may still review your application."}</p>
        <button onClick={onDone}>Back to my applications</button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card stack">
        <h3>Test: {app.job_title}</h3>
        <p>The timer starts as soon as you click Start and cannot be paused. Do not refresh the page; answers are not saved until you submit.</p>
        {err && <p className="err">{err}</p>}
        <div className="row">
          <button onClick={onDone}>Back</button>
          <button onClick={start}>Start test</button>
        </div>
      </div>
    );
  }

  const answered = Object.keys(ans).length;
  return (
    <div className="card">
      <div className="row">
        <h3>Test: {app.job_title}</h3>
        <h3>{mmss(Math.max(0, left))}</h3>
      </div>
      {data.questions.map((q, i) => (
        <div className="note" key={q.id}>
          <b>{i + 1}. {q.text}</b>
          {q.options.map((o, j) => (
            <label key={j} className="opt">
              <input type="radio" name={`q${q.id}`} checked={ans[q.id] === j} onChange={() => setAns({ ...ans, [q.id]: j })} /> {o}
            </label>
          ))}
        </div>
      ))}
      {err && <p className="err">{err} {sent.current && <button onClick={retry}>Try submitting again</button>}</p>}
      <p className="muted">Answered {answered} of {data.questions.length}</p>
      <button disabled={busy} onClick={submit}>{busy ? "Submitting..." : "Submit test"}</button>
    </div>
  );
}