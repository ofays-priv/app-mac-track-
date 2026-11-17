from __future__ import annotations

import mimetypes
import os
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path


@dataclass
class EmailDraft:
    to: list
    subject: str
    text: str
    html: str = ""
    attachments: list = field(default_factory=list)


def collect_attachments(deviations: list) -> list:
    seen = set()
    paths = []
    for dev in deviations:
        for att in dev.attachments:
            path = Path(att)
            if not path.is_file():
                continue
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                paths.append(str(path))
    return paths


class SmtpTransport:
    def __init__(self, smtp_cfg: dict):
        self.host = smtp_cfg["host"]
        self.port = int(smtp_cfg.get("port", 587))
        self.username = smtp_cfg.get("username")
        self.password_env = smtp_cfg.get("password_env")
        self.use_tls = bool(smtp_cfg.get("use_tls", True))
        self.from_addr = smtp_cfg.get("from") or self.username

    def _build_message(self, draft: EmailDraft) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(draft.to)
        msg["Subject"] = draft.subject
        msg.set_content(draft.text)
        if draft.html:
            msg.add_alternative(draft.html, subtype="html")
        for att in draft.attachments:
            path = Path(att)
            ctype, encoding = mimetypes.guess_type(path.name)
            if path.suffix.lower() == ".eml":
                maintype, subtype = "message", "rfc822"
            elif ctype:
                maintype, subtype = ctype.split("/", 1)
            else:
                maintype, subtype = "application", "octet-stream"
            with path.open("rb") as fh:
                msg.add_attachment(
                    fh.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=path.name,
                )
        return msg

    def send(self, draft: EmailDraft) -> None:
        password = os.environ.get(self.password_env, "") if self.password_env else None
        msg = self._build_message(draft)
        with smtplib.SMTP(self.host, self.port, timeout=30) as server:
            if self.use_tls:
                server.starttls()
            if self.username:
                server.login(self.username, password or "")
            server.send_message(msg)
