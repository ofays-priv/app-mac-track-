from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .emailer import EmailDraft


def _require_macos() -> None:
    if sys.platform != "darwin":
        raise RuntimeError("Cette fonction necessite macOS (integration Mail.app)")


def _escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _multiline(value: str) -> str:
    parts = str(value).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return '"' + '" & return & "'.join(_escape(p) for p in parts) + '"'


def _as_list(items: list) -> str:
    return "{" + ", ".join('"%s"' % _escape(i) for i in items) + "}"


def run_osascript(script: str) -> str:
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"osascript a echoue: {proc.stderr.strip()}")
    return proc.stdout


def script_count_selected() -> str:
    return 'tell application "Mail" to return count of (get selection)'


def script_message_meta(index: int) -> str:
    return (
        'tell application "Mail"\n'
        f"\tset m to item {index} of (get selection)\n"
        '\treturn (subject of m) & "\\t" & (sender of m)\n'
        "end tell"
    )


def script_message_raw_source(index: int) -> str:
    return (
        'tell application "Mail"\n'
        f"\tset m to item {index} of (get selection)\n"
        "\treturn raw source of m\n"
        "end tell"
    )


def fetch_selected_messages(directory) -> list:
    _require_macos()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    count = int(run_osascript(script_count_selected()).strip() or "0")
    if count == 0:
        raise RuntimeError("Aucun message selectionne dans Mail.app")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    results = []
    for i in range(1, count + 1):
        meta = run_osascript(script_message_meta(i)).strip()
        parts = meta.split("\t", 1)
        subject = parts[0] if parts else ""
        sender = parts[1] if len(parts) > 1 else ""
        raw = run_osascript(script_message_raw_source(i))
        safe_subject = re.sub(r"[^\w\-]+", "_", subject)[:40] or "mail"
        path = directory / f"{stamp}-{i}-{safe_subject}.eml"
        path.write_text(raw, encoding="utf-8", errors="replace")
        results.append({"path": str(path), "subject": subject, "sender": sender})
    return results


def script_build_message(draft: EmailDraft, mode: str = "send") -> str:
    lines = [
        'tell application "Mail"',
        "\tset newMsg to make new outgoing message with properties "
        f"{{subject:\"{_escape(draft.subject)}\", content:{_multiline(draft.text)}, visible:false}}",
        "\ttell newMsg",
    ]
    for addr in draft.to:
        lines.append(
            f'\t\tmake new to recipient at end of to recipients with properties {{address:"{_escape(addr)}"}}'
        )
    for path in draft.attachments:
        lines.append(
            f'\t\tmake new attachment with properties {{file name:POSIX file "{_escape(path)}"}} at after last paragraph'
        )
    lines.append("\tend tell")
    if mode == "draft":
        lines.append("\tset visible of newMsg to true")
    else:
        lines.append("\tsend newMsg")
    lines.append("end tell")
    return "\n".join(lines)


def send_via_mail_app(draft: EmailDraft, mode: str = "send") -> None:
    if mode not in ("send", "draft"):
        raise ValueError("mode doit etre 'send' ou 'draft'")
    _require_macos()
    run_osascript(script_build_message(draft, mode=mode))
