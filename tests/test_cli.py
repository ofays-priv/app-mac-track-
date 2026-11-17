import pytest

from deviation_tracker import cli
from deviation_tracker.config import AppConfig


def test_ajouter_lister_resume(home, config, capsys):
    rc = cli.main([
        "ajouter",
        "--categorie", "sla_non_respect",
        "--gravite", "haute",
        "--equipe", "Support",
        "--sujet", "SLA non respecte sur ticket 42",
        "--description", "Delai depasse de 4h",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Deviation enregistree" in out
    assert "Non-respect du SLA" in out

    rc = cli.main(["lister"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "SLA non respecte sur ticket 42" in out

    rc = cli.main(["resume"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "RESUME DES DEVIATIONS" in out
    assert "SLA non respecte sur ticket 42" in out

    rc = cli.main(["resume", "--format", "html"])
    assert rc == 0
    assert "<table" in capsys.readouterr().out


def test_ajouter_validation_error(home, config, capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main([
            "ajouter",
            "--categorie", "categorie_invalide",
            "--equipe", "Support",
            "--sujet", "x",
        ])
    assert excinfo.value.code != 0
    err = capsys.readouterr().err
    assert "invalid choice" in err


def test_statut_command(home, config, capsys):
    cli.main([
        "ajouter", "--categorie", "autre", "--equipe", "Support", "--sujet", "test",
    ])
    dev_id = None
    from deviation_tracker.store import DeviationStore

    store = DeviationStore(AppConfig.load(home).store_path)
    dev_id = store.all()[0].id
    rc = cli.main(["statut", dev_id, "--statut", "resolue"])
    assert rc == 0
    assert "Resolue" in capsys.readouterr().out
    rc = cli.main(["lister", "--statut", "ouverte"])
    assert "Aucune deviation" in capsys.readouterr().out


def test_envoyer_sans_transport(home, config, capsys):
    config.utiliser_mail_app = False
    config.smtp = None
    config.save()
    cli.main([
        "ajouter", "--categorie", "autre", "--equipe", "Support", "--sujet", "test",
    ])
    rc = cli.main(["envoyer"])
    assert rc == 2
    assert "Aucun transport" in capsys.readouterr().err


def test_envoyer_via_fake_transport(home, config, capsys, monkeypatch):
    cli.main([
        "ajouter", "--categorie", "pas_de_reponse_mail", "--equipe", "Support",
        "--sujet", "Mail sans reponse",
    ])
    sent = {}

    def fake_send_summary(cfg, store, **kwargs):
        from deviation_tracker import service

        kwargs.pop("mode", None)
        draft = service.summary_draft(cfg, store, **kwargs)
        sent["draft"] = draft
        return draft, "fake"

    monkeypatch.setattr(cli.service, "send_summary", fake_send_summary)
    rc = cli.main(["envoyer", "--groupes", "mon_equipe,direction", "--a", "extra@x.fr"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Resume envoye via fake" in out
    draft = sent["draft"]
    assert set(draft.to) == {
        "equipe@entreprise.fr",
        "chef@entreprise.fr",
        "directeur@entreprise.fr",
        "moi@entreprise.fr",
        "extra@x.fr",
    }
    assert "Resume des deviation" in draft.subject
    assert "Mail sans reponse" in draft.text


def test_config_command(home, config, capsys):
    rc = cli.main(["config"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "mon_equipe" in out
    assert "moi@entreprise.fr" in out


def test_resolve_recipients_unknown_group(config):
    import pytest

    with pytest.raises(ValueError):
        config.resolve_recipients(["groupe_inconnu"])
