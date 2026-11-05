import os
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def build_ics(uid, start_ist, minutes, summary, location) -> str:
    start_utc = start_ist - timedelta(hours=5, minutes=30)
    end_utc = start_utc + timedelta(minutes=minutes)
    fmt = "%Y%m%dT%H%M%SZ"
    return "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Akshara HR//EN", "METHOD:REQUEST",
        "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{datetime.utcnow().strftime(fmt)}",
        f"DTSTART:{start_utc.strftime(fmt)}", f"DTEND:{end_utc.strftime(fmt)}",
        f"SUMMARY:{summary}", f"LOCATION:{location}", "END:VEVENT", "END:VCALENDAR",
    ])


def send_mail(to, subject, body, ics=None) -> str:
    host = os.getenv("SMTP_HOST")
    if not host:
        print(f"\n[email logged - SMTP not configured]\nTo: {to}\nSubject: {subject}\n{body}\n")
        return "logged"
    try:
        msg = EmailMessage()
        msg["From"] = os.getenv("FROM_EMAIL", os.getenv("SMTP_USER", ""))
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        if ics:
            msg.add_attachment(ics.encode(), maintype="text", subtype="calendar",
                               filename="interview.ics", params={"method": "REQUEST"})
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=20) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", ""))
            s.send_message(msg)
        return "sent"
    except Exception as e:  # noqa: BLE001
        print(f"[email failed] {to}: {e}")
        return "failed"