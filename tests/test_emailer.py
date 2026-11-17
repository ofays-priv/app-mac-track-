import smtplib

from deviation_tracker.emailer import EmailDraft, SmtpTransport, collect_attachments
from deviation_tracker.models import Deviation


def _dev_with_attachment(tmp_path):
    eml = tmp_path / "source.eml"
    eml.write_bytes(b"From: a@b.fr\r\nSubject: x\r\n\r\nbody")
    return Deviation.create(
        category="pas_de_reponse_mail",
        severity="moyenne",
        team="Support",
        subject="pas de reponse",
        description="",
        attachments=[str(eml)],
    )


def test_collect_attachments_dedupes_and_checks_existence(tmp_path):
    dev = _dev_with_attachment(tmp_path)
    missing = Deviation.create(
        category="autre", severity="faible", team="t", subject="s", description="",
        attachments=[str(tmp_path / "inexistant.eml")],
    )
    paths = collect_attachments([dev, dev, missing])
    assert paths == [str(tmp_path / "source.eml")]


def test_smtp_message_build(tmp_path, monkeypatch):
    dev = _dev_with_attachment(tmp_path)
    draft = EmailDraft(
        to=["equipe@x.fr", "moi@x.fr"],
        subject="Resume des deviations",
        text="corps du resume\nligne 2",
        html="<p>corps</p>",
        attachments=collect_attachments([dev]),
    )
    cfg = {
        "host": "smtp.x.fr",
        "port": 587,
        "username": "moi@x.fr",
        "password_env": "SMTP_PASSWORD",
        "use_tls": True,
        "from": "moi@x.fr",
    }
    transport = SmtpTransport(cfg)
    msg = transport._build_message(draft)
    assert msg["To"] == "equipe@x.fr, moi@x.fr"
    assert msg["Subject"] == "Resume des deviations"
    assert msg["From"] == "moi@x.fr"
    parts = list(msg.walk())
    content_types = [p.get_content_type() for p in parts]
    assert "text/plain" in content_types
    assert "text/html" in content_types
    assert "message/rfc822" in content_types
    eml_part = next(p for p in parts if p.get_content_type() == "message/rfc822")
    assert eml_part.get_filename() == "source.eml"


def test_smtp_send_uses_env_password(tmp_path, monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            sent["tls"] = True

        def login(self, user, password):
            sent["login"] = (user, password)

        def send_message(self, msg):
            sent["subject"] = msg["Subject"]

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_PASSWORD", "motdepasse-secret")
    transport = SmtpTransport({
        "host": "smtp.x.fr",
        "port": 2525,
        "username": "moi@x.fr",
        "password_env": "SMTP_PASSWORD",
        "use_tls": True,
    })
    draft = EmailDraft(to=["a@x.fr"], subject="s", text="t")
    transport.send(draft)
    assert sent["host"] == "smtp.x.fr"
    assert sent["port"] == 2525
    assert sent["tls"] is True
    assert sent["login"] == ("moi@x.fr", "motdepasse-secret")
    assert sent["subject"] == "s"
