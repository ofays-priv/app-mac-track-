from deviation_tracker.summary import build_summary, build_subject, render_html, render_text


def test_text_summary_contains_all_deviations(sample_deviations):
    text = render_text(sample_deviations)
    assert "Nombre de deviations : 3" in text
    assert "Non-respect du SLA" in text
    assert "Pas de reponse a un e-mail" in text
    assert "Attente d'une decision claire d'un directeur" in text
    assert "Ticket #123 traite en 6h au lieu de 2h" in text
    assert 'Mail source : "RE: Incident production" <client@externe.fr>' in text
    assert "[HAUTE]" in text
    assert "[CRITIQUE]" in text


def test_text_summary_empty():
    text = render_text([])
    assert "Aucune deviation ouverte a signaler." in text
    assert "Nombre de deviations : 0" in text


def test_subject_line():
    subject = build_subject([1, 2, 3])
    assert subject.endswith("3 deviations")
    assert "Resume des deviations du" in subject


def test_html_escapes_user_content(store):
    from deviation_tracker.models import Deviation

    dev = Deviation.create(
        category="autre",
        severity="faible",
        team="Support",
        subject='<script>alert("x")</script>',
        description="<b>gras</b> & \"guillemets\"",
    )
    html = render_html([dev])
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    assert "<b>gras</b>" not in html
    assert "&lt;b&gt;gras&lt;/b&gt;" in html
    assert "<table" in html
    assert "Autre deviation (1)" in html


def test_build_summary_fields(sample_deviations):
    summary = build_summary(sample_deviations)
    assert summary.count == 3
    assert summary.subject == build_subject(sample_deviations)
    assert "RESUME DES DEVIATIONS" in summary.text
    assert summary.html.startswith("<html>")


def test_attachment_names_in_text(sample_deviations, tmp_path):
    eml = tmp_path / "mail-source.eml"
    eml.write_text("raw source", encoding="utf-8")
    sample_deviations[0].attachments = [str(eml)]
    text = render_text(sample_deviations)
    assert "mail-source.eml" in text
