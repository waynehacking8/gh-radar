"""Email delivery via SMTP (Gmail). Prints the digest instead if SMTP is unset."""
import os
import smtplib
import sys
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

from .render import md_to_html


def send_email(subject, md):
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    pw = os.environ.get("SMTP_PASS")
    to = os.environ.get("EMAIL_TO") or user      # empty/unset -> fall back to sender
    if not (host and user and pw and to):
        print("  i SMTP not configured — printing digest instead.\n", file=sys.stderr)
        print(md)
        return False
    msg = MIMEText(md_to_html(md), "html", "utf-8")
    msg["Subject"] = str(Header(subject, "utf-8"))     # safe for em dash / Chinese
    msg["From"] = formataddr(("GitHub Radar", user))
    msg["To"] = to
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        port = 587
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.ehlo()
        s.starttls()
        s.login(user, pw)
        s.sendmail(user, [to], msg.as_string())
    print(f"  ✓ emailed digest to {to}")
    return True
