import pytest

from deviation_tracker.models import (
    CATEGORY_LABELS,
    Deviation,
    STATUS_OUVERTE,
)


def test_create_assigns_id_and_timestamp():
    dev = Deviation.create(
        category="sla_non_respect",
        severity="haute",
        team="Support",
        subject="SLA depasse",
        description="",
    )
    assert dev.id
    assert "T" in dev.created_at
    assert dev.status == STATUS_OUVERTE
    assert dev.category_label() == CATEGORY_LABELS["sla_non_respect"]


def test_create_rejects_unknown_category():
    with pytest.raises(ValueError):
        Deviation.create(
            category="nimportequoi",
            severity="haute",
            team="Support",
            subject="x",
            description="",
        )


def test_create_rejects_empty_team_and_subject():
    with pytest.raises(ValueError):
        Deviation.create(
            category="autre", severity="faible", team="  ", subject="x", description=""
        )
    with pytest.raises(ValueError):
        Deviation.create(
            category="autre", severity="faible", team="Support", subject=" ", description=""
        )


def test_dict_round_trip():
    dev = Deviation.create(
        category="attente_decision_direction",
        severity="critique",
        team="Delivery",
        subject="Attente decision",
        description="desc",
        attachments=["/tmp/a.eml"],
        source_subject="Mail source",
        source_sender="dir@x.fr",
    )
    clone = Deviation.from_dict(dev.to_dict())
    assert clone.to_dict() == dev.to_dict()
