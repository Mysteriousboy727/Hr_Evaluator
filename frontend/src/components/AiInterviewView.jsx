import { useEffect, useState } from "react";
import { api } from "../api";

const tone = { advance: "ok", review: "warn", concern: "bad" };

export default function AiInterviewView({ appId }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    setD(null);
    setErr("");
    api.interviewGet(appId).then(setD).catch((e) => setErr(e.message));
  }, [appId]);

  if (err) return <div className="card"><p className="muted">{err}</p></div>;
  if (!d) return <div className="card"><p className="muted">Loading...</p></div>;
  const s = d.summary || {};
  return (
    <div className="card">
      <h3>AI interview ({d.language}) <span className="badge">{d.status}</span></h3>
      {s.summary && (
        <>
          <p>{s.summary}</p>
          <p>
            <span className={"badge " + (tone[s.recommendation] || "")}>Suggested: {s.recommendation}</span>{" "}
            <span className="badge">Role skills {s.technical}/5</span>{" "}
            <span className="badge">Communication {s.communication}/5</span>{" "}
            <span className="badge">Relevance {s.relevance}/5</span>
          </p>
          {s.strengths?.length > 0 && <p><b>Strengths:</b> {s.strengths.join("; ")}</p>}
          {s.concerns?.length > 0 && <p><b>Concerns:</b> {s.concerns.join("; ")}</p>}
          <p className="muted">This summary is advisory and AI-generated. Check the transcript and decide yourself.</p>
        </>
      )}
      <h4>Transcript</h4>
      <div className="chat">
        {d.turns.map((t, i) => (
          <div key={i} className={"bubble " + (t.role === "assistant" ? "ai" : "me")}>{t.text}</div>
        ))}
      </div>
    </div>
  );
}