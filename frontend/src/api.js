const BASE = "/api";
export const getToken = () => localStorage.getItem("token");

async function req(path, opts = {}) {
  const headers = {
    ...(opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
    ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
  };
  const r = await fetch(BASE + path, { ...opts, headers });
  if (!r.ok) {
    let m = r.statusText;
    try { const j = await r.json(); m = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch { /* ignore */ }
    throw new Error(m);
  }
  return r.json();
}
const post = (p, b) => req(p, { method: "POST", body: JSON.stringify(b) });

export const api = {
  register: (b) => post("/auth/register", b),
  login: (b) => post("/auth/login", b),
  me: () => req("/auth/me"),
  jobs: () => req("/jobs"),
  createJob: (b) => post("/jobs", b),
  closeJob: (id) => post(`/jobs/${id}/close`, {}),
  slots: (id) => req(`/jobs/${id}/slots`),
  addSlots: (id, slots) => post(`/jobs/${id}/slots`, { slots }),
  questions: () => req("/questions"),
  apply: (id, fd) => req(`/jobs/${id}/apply`, { method: "POST", body: fd }),
  myApps: () => req("/my/applications"),
  jobApps: (id) => req(`/jobs/${id}/applications`),
  decide: (id, decision) => post(`/applications/${id}/decision`, { decision }),
  confirm: (id) => post(`/applications/${id}/confirm`, {}),
  notifications: () => req("/notifications"),
  interviewLanguages: () => req("/interview/languages"),
  interviewStart: (id, b) => post(`/applications/${id}/interview/start`, b),
  interviewAnswer: (id, text) => post(`/applications/${id}/interview/answer`, { text }),
  interviewGet: (id) => req(`/applications/${id}/interview`),
  interviewConfig: (id) => req(`/jobs/${id}/interview-config`),
  setInterviewConfig: (id, b) => req(`/jobs/${id}/interview-config`, { method: "PUT", body: JSON.stringify(b) }),
  test: (id) => req(`/jobs/${id}/test`),
  setTestConfig: (id, b) => req(`/jobs/${id}/test/config`, { method: "PUT", body: JSON.stringify(b) }),
  addQuestion: (id, b) => post(`/jobs/${id}/test/questions`, b),
  uploadQuestions: (id, fd) => req(`/jobs/${id}/test/upload-file`, { method: "POST", body: fd }),
  deleteQuestion: (qid) => req(`/questions/${qid}`, { method: "DELETE" }),
  startTest: (appId) => post(`/applications/${appId}/test/start`, {}),
  submitTest: (appId, answers) => post(`/applications/${appId}/test/submit`, { answers }),
  markRead: () => post("/notifications/read", {}),
  resume: async (id) => {
    const r = await fetch(`${BASE}/applications/${id}/resume`, { headers: { Authorization: `Bearer ${getToken()}` } });
    if (!r.ok) throw new Error("Could not download resume");
    window.open(URL.createObjectURL(await r.blob()));
  },
};