import { useEffect, useRef, useState } from "react";
import { api } from "../api";

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

export default function InterviewRunner({ app, onDone }) {
  const [info, setInfo] = useState({ enabled: true, languages: [] });
  const [lang, setLang] = useState("en");
  const [consent, setConsent] = useState(false);
  const [voice, setVoice] = useState(true);
  const [sess, setSess] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [on, setOn] = useState(false);
  const [err, setErr] = useState("");
  const rec = useRef(null);
  const latest = useRef("");
  const endRef = useRef(null);
  latest.current = text;

  useEffect(() => {
    api.interviewLanguages().then(setInfo).catch((e) => setErr(e.message));
    return () => { window.speechSynthesis?.cancel(); rec.current?.abort?.(); };
  }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [sess, busy]);

  const cur = info.languages.find((l) => l.code === lang);
  const bcp = cur ? cur.bcp : "en-IN";
  const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  const noVoice = voice && voices.length > 0 && !voices.some((v) => v.lang.toLowerCase().startsWith(bcp.split("-")[0]));

  function speak(t, code) {
    if (!voice || !window.speechSynthesis) return;
    const l = info.languages.find((x) => x.code === code);
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(t);
    u.lang = l ? l.bcp : "en-IN";
    u.rate = 0.95;
    window.speechSynthesis.speak(u);
  }

  function toggleMic() {
    if (on) { rec.current?.stop(); return; }
    window.speechSynthesis?.cancel();
    const r = new SR();
    r.lang = bcp;
    r.continuous = true;
    r.interimResults = false;
    r.onresult = (e) => {
      let t = "";
      for (let i = e.resultIndex; i < e.results.length; i++) t += e.results[i][0].transcript;
      setText((latest.current ? latest.current + " " : "") + t.trim());
    };
    r.onerror = () => setOn(false);
    r.onend = () => setOn(false);
    rec.current = r;
    r.start();
    setOn(true);
  }

  async function begin() {
    setErr("");
    setBusy(true);
    try {
      const s = await api.interviewStart(app.id, { language: lang, consent });
      setSess(s);
      setLang(s.language);
      const last = s.turns[s.turns.length - 1];
      if (last && last.role === "assistant" && !s.done) speak(last.text, s.language);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  async function send() {
    const t = text.trim();
    if (!t || busy) return;
    rec.current?.stop?.();
    window.speechSynthesis?.cancel();
    setBusy(true);
    setErr("");
    try {
      const s = await api.interviewAnswer(app.id, t);
      setSess(s);
      setText("");
      const last = s.turns[s.turns.length - 1];
      if (!s.done && last && last.role === "assistant") speak(last.text, s.language);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  if (!sess) {
    return (
      <div className="card stack">
        <h3>AI interview: {app.job_title}</h3>
        <p>You will talk with an AI interviewer for about 10 minutes. It asks one question at a time and your answers are saved as a transcript for HR. HR makes the final decision.</p>
        <label>Interview language
          <select value={lang} onChange={(e) => setLang(e.target.value)}>
            {info.languages.map((l) => <option key={l.code} value={l.code}>{l.name} ({l.native})</option>)}
          </select>
        </label>
        <label className="opt"><input type="checkbox" checked={voice} onChange={(e) => setVoice(e.target.checked)} /> Read questions aloud and allow voice answers (Chrome or Edge)</label>
        {noVoice && <p className="muted">Your computer has no {cur.name} voice installed, so questions may not be read aloud. You can still read and type.</p>}
        {voice && SR && <p className="muted">Voice answers use your browser's speech recognition, which may send audio to your browser vendor's service.</p>}
        <label className="opt"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /> I understand this is an AI interviewer and agree to my answers being recorded as text and shared with HR.</label>
        {err && <p className="err">{err}</p>}
        <div className="row">
          <button onClick={onDone}>Back</button>
          <button disabled={!consent || busy || !info.enabled} onClick={begin}>{busy ? "Starting..." : "Start interview"}</button>
        </div>
      </div>
    );
  }

  const asked = sess.turns.filter((t) => t.role === "assistant").length;

  if (sess.done) {
    return (
      <div className="card">
        <h3>Interview complete</h3>
        <p>Thank you. HR will review your interview. If a slot is free, your call with HR has been booked. Check My applications and your notifications.</p>
        <button onClick={onDone}>Back to my applications</button>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="row">
        <h3>AI interview: {app.job_title}</h3>
        <span className="badge accent">Question {asked} of {sess.max_questions}</span>
      </div>
      <div className="chat">
        {sess.turns.map((t, i) => (
          <div key={i} className={"bubble " + (t.role === "assistant" ? "ai" : "me")}>{t.text}</div>
        ))}
        {busy && <div className="bubble ai muted">Thinking...</div>}
        <div ref={endRef} />
      </div>
      <textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} placeholder="Type your answer, or use the mic" />
      {err && <p className="err">{err}</p>}
      <div className="row">
        <div>
          {SR && <button type="button" onClick={toggleMic}>{on ? "Stop mic" : "Answer by voice"}</button>}{" "}
          <button type="button" className="ghost" onClick={() => speak(sess.turns.filter((t) => t.role === "assistant").slice(-1)[0].text, sess.language)}>Replay question</button>
        </div>
        <button disabled={busy || !text.trim()} onClick={send}>{busy ? "Sending..." : "Send answer"}</button>
      </div>
    </div>
  );
}