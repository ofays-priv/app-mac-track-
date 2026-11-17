from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


class Category(str, enum.Enum):
    SLA_NON_RESPECT = "sla_non_respect"
    PAS_DE_REPONSE_MAIL = "pas_de_reponse_mail"
    ATTENTE_DECISION_DIRECTION = "attente_decision_direction"
    AUTRE = "autre"


CATEGORY_LABELS = {
    Category.SLA_NON_RESPECT.value: "Non-respect du SLA",
    Category.PAS_DE_REPONSE_MAIL.value: "Pas de reponse a un e-mail",
    Category.ATTENTE_DECISION_DIRECTION.value: "Attente d'une decision claire d'un directeur",
    Category.AUTRE.value: "Autre deviation",
}

CATEGORY_ORDER = [
    Category.SLA_NON_RESPECT.value,
    Category.PAS_DE_REPONSE_MAIL.value,
    Category.ATTENTE_DECISION_DIRECTION.value,
    Category.AUTRE.value,
]


class Severity(str, enum.Enum):
    FAIBLE = "faible"
    MOYENNE = "moyenne"
    HAUTE = "haute"
    CRITIQUE = "critique"


SEVERITY_LABELS = {
    Severity.FAIBLE.value: "Faible",
    Severity.MOYENNE.value: "Moyenne",
    Severity.HAUTE.value: "Haute",
    Severity.CRITIQUE.value: "Critique",
}

SEVERITY_ORDER = {
    Severity.FAIBLE.value: 1,
    Severity.MOYENNE.value: 2,
    Severity.HAUTE.value: 3,
    Severity.CRITIQUE.value: 4,
}

STATUS_OUVERTE = "ouverte"
STATUS_SUIVIE = "suivie"
STATUS_RESOLUE = "resolue"
STATUSES = (STATUS_OUVERTE, STATUS_SUIVIE, STATUS_RESOLUE)

STATUS_LABELS = {
    STATUS_OUVERTE: "Ouverte",
    STATUS_SUIVIE: "Suivie",
    STATUS_RESOLUE: "Resolue",
}


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _validate(value: str, allowed, kind: str) -> str:
    if value not in allowed:
        raise ValueError(f"{kind} invalide: {value!r} (attendu: {', '.join(allowed)})")
    return value


@dataclass
class Deviation:
    id: str
    created_at: str
    category: str
    severity: str
    team: str
    subject: str
    description: str
    status: str = STATUS_OUVERTE
    attachments: list = field(default_factory=list)
    source_subject: str = ""
    source_sender: str = ""

    @classmethod
    def create(
        cls,
        category: str,
        severity: str,
        team: str,
        subject: str,
        description: str,
        attachments=None,
        source_subject: str = "",
        source_sender: str = "",
        status: str = STATUS_OUVERTE,
        dev_id: str = "",
        created_at: str = "",
    ) -> "Deviation":
        category = _validate(category, [c.value for c in Category], "Categorie")
        severity = _validate(severity, [s.value for s in Severity], "Gravite")
        status = _validate(status, list(STATUSES), "Statut")
        if not team.strip():
            raise ValueError("L'equipe est obligatoire")
        if not subject.strip():
            raise ValueError("Le sujet est obligatoire")
        return cls(
            id=dev_id or new_id(),
            created_at=created_at or now_iso(),
            category=category,
            severity=severity,
            team=team.strip(),
            subject=subject.strip(),
            description=description.strip(),
            status=status,
            attachments=list(attachments or []),
            source_subject=(source_subject or "").strip(),
            source_sender=(source_sender or "").strip(),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "category": self.category,
            "severity": self.severity,
            "team": self.team,
            "subject": self.subject,
            "description": self.description,
            "status": self.status,
            "attachments": list(self.attachments),
            "source_subject": self.source_subject,
            "source_sender": self.source_sender,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Deviation":
        return cls(
            id=data["id"],
            created_at=data["created_at"],
            category=data["category"],
            severity=data["severity"],
            team=data.get("team", ""),
            subject=data.get("subject", ""),
            description=data.get("description", ""),
            status=data.get("status", STATUS_OUVERTE),
            attachments=list(data.get("attachments", [])),
            source_subject=data.get("source_subject", ""),
            source_sender=data.get("source_sender", ""),
        )

    def category_label(self) -> str:
        return CATEGORY_LABELS.get(self.category, self.category)

    def severity_label(self) -> str:
        return SEVERITY_LABELS.get(self.severity, self.severity)

    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)
