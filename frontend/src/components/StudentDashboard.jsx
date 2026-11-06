import { useEffect, useState } from "react";
import { api } from "../api";
import { badgeTone } from "../ui.js";
import ApplyForm from "./ApplyForm.jsx";
import TestRunner from "./TestRunner.jsx";
import InterviewRunner from "./InterviewRunner.jsx";

export default function StudentDashboard() {
  const [jobs, setJobs] = useState([]);
  const [apps, setApps] = useState([]);
  const [applying, setApplying] = useState(null);
  const [testing, setTesting] = useState(null);
  const [interviewing, setInterviewing] = useState(null);
  const [err, setErr] = useState("");

  const load = () => {
    api.jobs().then(setJobs).catch((e) => setErr(e.message));
    api.myApps().then(setApps).catch((e) => setErr(e.message));
  };
  useEffect(() => { load(); }, []);

  async function confirm(id) {
    try { await api.confirm(id); load(); } catch (e) { setErr(e.message); }
  }

  if (interviewing) return <InterviewRunner app={interviewing} onDone={() => { setInterviewing(null); load(); }} />;
  if (testing) return <TestRunner app={testing} onDone={() => { setTesting(null); load(); }} />;
  if (applying) return <ApplyForm job={applying} onDone={() => { setApplying(null); load(); }} onCancel={() => setApplying(null)} />;

  return (
    <>
      {err && <p className="err">{err}</p>}
      <div className="card">
        <h3>My applications</h3>
        {apps.length === 0 && <p className="muted">You have not applied anywhere yet. Pick a role below to get started.</p>}
        {apps.map((a) => (
          <div className="row" key={a.id}>
            <div>
              <b>{a.job_title}</b>{" "}
              <span className={"badge " + badgeTone(a.status)}>{a.status}</span>
              <div className="muted">Match score {a.total_score}/100</div>
              {a.status === "Shortlisted - Awaiting Test Setup" && <div className="muted">Your test is being prepared. You will be notified when it is ready.</div>}
              {a.slot_start && (
                <div>Interview: <b>{a.slot_start.replace("T", " ")} IST</b> - <a href={a.meeting_link} target="_blank" rel="noreferrer">Join call</a></div>
              )}
            </div>
            <div>
              {a.status === "Test Pending" && <button onClick={() => setTesting(a)}>Take test</button>}
              {a.status === "AI Interview Pending" && <button onClick={() => setInterviewing(a)}>Start AI interview</button>}
              {a.status === "Interview Scheduled" && <button onClick={() => confirm(a.id)}>Confirm attendance</button>}
            </div>
          </div>
        ))}
      </div>
      <div className="card">
        <h3>Open roles</h3>
        {jobs.length === 0 && <p className="muted">No open roles right now.</p>}
        {jobs.map((j) => (
          <div className="row" key={j.id}>
            <div>
              <b>{j.title}</b>
              <div className="muted">{j.work_mode} {j.location} | {j.duration_months} months | {j.stipend}</div>
              <div className="muted">Skills: {j.required_skills}</div>
              <div>{j.description}</div>
            </div>
            {j.applied ? <span className="badge accent">Applied</span> : <button onClick={() => setApplying(j)}>Apply</button>}
          </div>
        ))}
      </div>
    </>
  );
}