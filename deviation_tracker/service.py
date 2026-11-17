from __future__ import annotations

import sys

from .config import AppConfig
from .emailer import EmailDraft, SmtpTransport, collect_attachments
from .models import Deviation
from .store import DeviationStore
from .summary import build_summary


def add_deviation(
    config: AppConfig,
    store: DeviationStore,
    category: str,
    severity: str,
    team: str,
    subject: str,
    description: str = "",
    attachments=None,
    source_subject: str = "",
    source_sender: str = "",
) -> Deviation:
    deviation = Deviation.create(
        category=category,
        severity=severity,
        team=team,
        subject=subject,
        description=description,
        attachments=attachments,
        source_subject=source_subject,
        source_sender=source_sender,
    )
    return store.add(deviation)


def summary_draft(
    config: AppConfig,
    store: DeviationStore,
    groups=None,
    extra_emails=None,
    since=None,
    status: str = "ouverte",
) -> EmailDraft:
    deviations = store.filter(status=status, since=since)
    summary = build_summary(deviations)
    recipients = config.resolve_recipients(groups, extra_emails)
    return EmailDraft(
        to=recipients,
        subject=summary.subject,
        text=summary.text,
        html=summary.html,
        attachments=collect_attachments(deviations),
    )


def send_draft(config: AppConfig, draft: EmailDraft, mode: str = None) -> str:
    mode = mode or config.mode_envoi
    if config.utiliser_mail_app and sys.platform == "darwin":
        from . import mailapp

        mailapp.send_via_mail_app(draft, mode=mode)
        return "mail_app"
    if config.smtp:
        SmtpTransport(config.smtp).send(draft)
        return "smtp"
    raise RuntimeError(
        "Aucun transport disponible : lancez l'app sur macOS (Mail.app) "
        "ou configurez une section 'smtp' dans config.json"
    )


def send_summary(config: AppConfig, store: DeviationStore, **kwargs) -> tuple:
    mode = kwargs.pop("mode", None)
    draft = summary_draft(config, store, **kwargs)
    transport = send_draft(config, draft, mode=mode)
    return draft, transport
