from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def default_home() -> Path:
    env = os.environ.get("DEVIATION_TRACKER_HOME")
    if env:
        return Path(env).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "DeviationTracker"
    return Path.home() / ".deviation-tracker"


@dataclass
class AppConfig:
    home: Path
    moi: list = field(default_factory=list)
    groupes: dict = field(default_factory=dict)
    groupes_par_defaut: list = field(default_factory=list)
    mode_envoi: str = "send"
    utiliser_mail_app: bool = True
    smtp: dict = None

    @property
    def config_path(self) -> Path:
        return self.home / "config.json"

    @property
    def store_path(self) -> Path:
        return self.home / "deviations.json"

    @property
    def attachments_dir(self) -> Path:
        return self.home / "pieces_jointes"

    @classmethod
    def load(cls, home=None) -> "AppConfig":
        home = Path(home).expanduser() if home else default_home()
        home.mkdir(parents=True, exist_ok=True)
        (home / "pieces_jointes").mkdir(parents=True, exist_ok=True)
        data = {}
        config_path = home / "config.json"
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        return cls(
            home=home,
            moi=list(data.get("moi", [])),
            groupes=dict(data.get("groupes", {})),
            groupes_par_defaut=list(data.get("groupes_par_defaut", [])),
            mode_envoi=data.get("mode_envoi", "send"),
            utiliser_mail_app=bool(data.get("utiliser_mail_app", True)),
            smtp=data.get("smtp"),
        )

    def save(self) -> None:
        data = {
            "moi": self.moi,
            "groupes": self.groupes,
            "groupes_par_defaut": self.groupes_par_defaut,
            "mode_envoi": self.mode_envoi,
            "utiliser_mail_app": self.utiliser_mail_app,
            "smtp": self.smtp,
        }
        with self.config_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    def resolve_recipients(self, groups=None, extra=None) -> list:
        chosen = list(groups) if groups else list(self.groupes_par_defaut)
        unknown = [g for g in chosen if g not in self.groupes]
        if unknown:
            raise ValueError(
                f"Groupe(s) inconnu(s): {', '.join(unknown)}. "
                f"Groupes connus: {', '.join(sorted(self.groupes)) or '(aucun)'}"
            )
        recipients = []
        for group in chosen:
            recipients.extend(self.groupes.get(group, []))
        recipients.extend(self.moi)
        recipients.extend(extra or [])
        seen = set()
        unique = []
        for addr in recipients:
            addr = addr.strip()
            if addr and addr.lower() not in seen:
                seen.add(addr.lower())
                unique.append(addr)
        if not unique:
            raise ValueError(
                "Aucun destinataire: configurez 'moi' et/ou 'groupes' dans config.json"
            )
        return unique
