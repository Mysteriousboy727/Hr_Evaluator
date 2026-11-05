export function badgeTone(s = "") {
  if (/Awaiting|Under HR Review/.test(s)) return "warn";
  if (/Not Shortlisted|Rejected|Failed/.test(s)) return "bad";
  if (/Confirmed/.test(s)) return "ok";
  if (/Shortlisted|Test|Interview/.test(s)) return "accent";
  return "";
}