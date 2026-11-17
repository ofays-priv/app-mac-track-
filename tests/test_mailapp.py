import pytest

from deviation_tracker import mailapp
from deviation_tracker.emailer import EmailDraft


def test_escape_quotes_and_backslashes():
    assert mailapp._escape('a"b\\c') == 'a\\"b\\\\c'


def test_multiline_uses_return_concatenation():
    script = mailapp._multiline('ligne1\nligne2 "x"')
    assert script == '"ligne1" & return & "ligne2 \\"x\\""'


def test_script_build_message_send():
    draft = EmailDraft(
        to=["equipe@x.fr", 'dir"@x.fr'],
        subject='Resume "deviations"',
        text="Bonjour,\n\nVoici le resume.\n",
        attachments=["/tmp/pj 1.eml", "/tmp/pj2.eml"],
    )
    script = mailapp.script_build_message(draft, mode="send")
    assert 'subject:"Resume \\"deviations\\""' in script
    assert 'address:"equipe@x.fr"' in script
    assert 'address:"dir\\"@x.fr"' in script
    assert 'POSIX file "/tmp/pj 1.eml"' in script
    assert 'POSIX file "/tmp/pj2.eml"' in script
    assert "send newMsg" in script
    assert "content:" in script
    assert '"Bonjour," & return & "" & return & "Voici le resume." & return & ""' in script


def test_script_build_message_draft():
    draft = EmailDraft(to=["a@x.fr"], subject="s", text="t")
    script = mailapp.script_build_message(draft, mode="draft")
    assert "set visible of newMsg to true" in script
    assert "send newMsg" not in script


def test_script_build_message_rejects_bad_mode():
    draft = EmailDraft(to=["a@x.fr"], subject="s", text="t")
    with pytest.raises(ValueError):
        mailapp.send_via_mail_app(draft, mode="bidon")


def test_scripts_for_selected_messages():
    assert "count of (get selection)" in mailapp.script_count_selected()
    assert "item 2 of (get selection)" in mailapp.script_message_meta(2)
    assert "raw source of m" in mailapp.script_message_raw_source(3)


def test_require_macos_on_linux():
    with pytest.raises(RuntimeError):
        mailapp.send_via_mail_app(EmailDraft(to=["a@x.fr"], subject="s", text="t"))
    with pytest.raises(RuntimeError):
        mailapp.fetch_selected_messages("/tmp/whatever")
