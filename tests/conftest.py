import json

import pytest

from deviation_tracker.config import AppConfig
from deviation_tracker.store import DeviationStore


@pytest.fixture()
def home(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    monkeypatch.setenv("DEVIATION_TRACKER_HOME", str(home_dir))
    return home_dir


@pytest.fixture()
def config(home):
    cfg = AppConfig.load(home)
    cfg.moi = ["moi@entreprise.fr"]
    cfg.groupes = {
        "mon_equipe": ["equipe@entreprise.fr", "chef@entreprise.fr"],
        "direction": ["directeur@entreprise.fr"],
    }
    cfg.groupes_par_defaut = ["mon_equipe"]
    cfg.save()
    return AppConfig.load(home)


@pytest.fixture()
def store(config):
    return DeviationStore(config.store_path)


@pytest.fixture()
def sample_deviations(store):
    from deviation_tracker.models import Deviation

    devs = [
        Deviation.create(
            category="sla_non_respect",
            severity="haute",
            team="Support",
            subject="Ticket #123 traite en 6h au lieu de 2h",
            description="Client VIP non pris en charge dans les delais.",
            attachments=[],
            source_subject="RE: Incident production",
            source_sender="client@externe.fr",
        ),
        Deviation.create(
            category="pas_de_reponse_mail",
            severity="moyenne",
            team="Support",
            subject="Mail du 12/05 sans reponse depuis 3 jours",
            description="Relance necessaire.",
        ),
        Deviation.create(
            category="attente_decision_direction",
            severity="critique",
            team="Delivery",
            subject="Blocage: attente decision directeur sur budget",
            description="Projet en pause depuis lundi.",
        ),
    ]
    for dev in devs:
        store.add(dev)
    return devs
