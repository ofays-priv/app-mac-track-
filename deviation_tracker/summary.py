from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import CATEGORY_LABELS, CATEGORY_ORDER, SEVERITY_LABELS, SEVERITY_ORDER


@dataclass
class Summary:
    subject: str
    text: str
    html: str
    count: int


def _grouped(deviations: list) -> list:
    groups = {}
    for dev in deviations:
        groups.setdefault(dev.category, []).append(dev)
    ordered_keys = [c for c in CATEGORY_ORDER if c in groups]
    ordered_keys += sorted(k for k in groups if k not in CATEGORY_ORDER)
    return [(key, groups[key]) for key in ordered_keys]


def _sorted(deviations: list) -> list:
    return sorted(
        deviations,
        key=lambda d: (SEVERITY_ORDER.get(d.severity, 0), d.created_at),
        reverse=True,
    )


def build_subject(deviations: list, when: datetime = None) -> str:
    when = when or datetime.now()
    n = len(deviations)
    label = "deviation" if n <= 1 else "deviations"
    return f"Resume des {label} du {when.strftime('%d/%m/%Y')} - {n} {label}"


def render_text(deviations: list, when: datetime = None) -> str:
    when = when or datetime.now()
    lines = [
        f"RESUME DES DEVIATIONS - {when.strftime('%d/%m/%Y')}",
        f"Nombre de deviations : {len(deviations)}",
        "",
    ]
    if not deviations:
        lines.append("Aucune deviation ouverte a signaler.")
        return "\n".join(lines) + "\n"
    for category, items in _grouped(deviations):
        label = CATEGORY_LABELS.get(category, category)
        lines.append(f"== {label} ({len(items)}) ==")
        for dev in _sorted(items):
            severity = SEVERITY_LABELS.get(dev.severity, dev.severity)
            lines.append(
                f"* [{severity.upper()}] {dev.created_at} - equipe {dev.team} - {dev.subject} (statut: {dev.status})"
            )
            if dev.description:
                lines.append(f"  Description : {dev.description}")
            if dev.source_subject:
                sender = f" <{dev.source_sender}>" if dev.source_sender else ""
                lines.append(f"  Mail source : \"{dev.source_subject}\"{sender}")
            if dev.attachments:
                names = ", ".join(Path(a).name for a in dev.attachments)
                lines.append(f"  Pieces jointes : {names}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _cell(value: str) -> str:
    return html.escape(value or "")


def render_html(deviations: list, when: datetime = None) -> str:
    when = when or datetime.now()
    rows = []
    for category, items in _grouped(deviations):
        label = CATEGORY_LABELS.get(category, category)
        rows.append(
            f'<tr><th colspan="6" style="text-align:left;background:#e8eef7;">{html.escape(label)} ({len(items)})</th></tr>'
        )
        for dev in _sorted(items):
            severity = SEVERITY_LABELS.get(dev.severity, dev.severity)
            source = ""
            if dev.source_subject:
                source = html.escape(dev.source_subject)
                if dev.source_sender:
                    source += f" &lt;{html.escape(dev.source_sender)}&gt;"
            attachments = ", ".join(html.escape(Path(a).name) for a in dev.attachments)
            rows.append(
                "<tr>"
                f"<td>{_cell(dev.created_at)}</td>"
                f"<td>{_cell(dev.team)}</td>"
                f"<td>{_cell(severity)}</td>"
                f"<td>{_cell(dev.subject)}</td>"
                f"<td>{_cell(dev.description)}<br><em>{source}</em></td>"
                f"<td>{attachments}</td>"
                "</tr>"
            )
    n = len(deviations)
    body = "\n".join(rows) if rows else '<tr><td colspan="6">Aucune deviation ouverte a signaler.</td></tr>'
    return (
        "<html><body>"
        f"<h2>Resume des deviations - {when.strftime('%d/%m/%Y')} ({n})</h2>"
        '<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">'
        "<tr><th>Date</th><th>Equipe</th><th>Gravite</th><th>Sujet</th>"
        "<th>Description / mail source</th><th>Pieces jointes</th></tr>"
        f"{body}"
        "</table></body></html>"
    )


def build_summary(deviations: list, when: datetime = None) -> Summary:
    when = when or datetime.now()
    return Summary(
        subject=build_subject(deviations, when),
        text=render_text(deviations, when),
        html=render_html(deviations, when),
        count=len(deviations),
    )
