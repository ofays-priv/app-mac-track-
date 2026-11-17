import pytest

from deviation_tracker.models import Deviation


def _dev(**kwargs):
    defaults = dict(
        category="autre",
        severity="moyenne",
        team="Support",
        subject="sujet",
        description="",
    )
    defaults.update(kwargs)
    return Deviation.create(**defaults)


def test_add_and_list(store):
    store.add(_dev(subject="premiere"))
    store.add(_dev(subject="seconde", team="Delivery"))
    devs = store.all()
    assert len(devs) == 2
    assert {d.subject for d in devs} == {"premiere", "seconde"}


def test_persistence_round_trip(config, store):
    store.add(_dev(subject="persiste"))
    from deviation_tracker.store import DeviationStore

    reloaded = DeviationStore(config.store_path)
    assert [d.subject for d in reloaded.all()] == ["persiste"]


def test_filter_by_team_and_status(store):
    d1 = store.add(_dev(subject="a", team="Support"))
    store.add(_dev(subject="b", team="Delivery"))
    assert [d.subject for d in store.filter(team="support")] == ["a"]
    assert len(store.filter(status="ouverte")) == 2
    store.update_status(d1.id, "resolue")
    assert [d.subject for d in store.filter(status="ouverte")] == ["b"]
    assert [d.subject for d in store.filter(status="toutes")] == ["a", "b"]


def test_filter_since(store):
    old = _dev(subject="ancienne", created_at="2020-01-01T10:00:00+00:00")
    new = _dev(subject="recente", created_at="2026-05-10T10:00:00+00:00")
    store.add(old)
    store.add(new)
    result = store.filter(since="2026-01-01")
    assert [d.subject for d in result] == ["recente"]


def test_update_status_unknown_id(store):
    with pytest.raises(KeyError):
        store.update_status("inconnu", "resolue")


def test_get(store):
    dev = store.add(_dev(subject="cible"))
    assert store.get(dev.id).subject == "cible"
    assert store.get("nope") is None
