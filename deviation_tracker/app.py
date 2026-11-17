from __future__ import annotations

import sys
from pathlib import Path

from Foundation import NSObject

from . import service
from .config import AppConfig
from .models import CATEGORY_LABELS, CATEGORY_ORDER, SEVERITY_LABELS, Severity
from .store import DeviationStore


def _alert(title: str, message: str) -> None:
    from AppKit import NSAlert

    alert = NSAlert.alloc().init()
    alert.setMessageText(title)
    alert.setInformativeText(message)
    alert.addButtonWithTitle("OK")
    alert.runModal()


class Controller(NSObject):
    def init(self):
        self = super().init()
        self.config = AppConfig.load()
        self.store = DeviationStore(self.config.store_path)
        self.pending_attachments = []
        self.pending_source_subject = ""
        self.pending_source_sender = ""
        self.window = None
        self.ctrl_category = None
        self.ctrl_severity = None
        self.ctrl_team = None
        self.ctrl_subject = None
        self.ctrl_description = None
        self.ctrl_attachments_label = None
        self.ctrl_status = None
        return self

    def build_window(self):
        from AppKit import (
            NSButton,
            NSMakeRect,
            NSPopUpButton,
            NSScrollView,
            NSTextField,
            NSTextView,
            NSWindow,
            NSWindowStyleMaskClosable,
            NSWindowStyleMaskTitled,
        )

        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 520, 560),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            2,
            False,
        )
        self.window.setTitle("Nouvelle deviation")
        content = self.window.contentView()

        def label(text, y):
            field = NSTextField.alloc().initWithFrame_(NSMakeRect(20, y, 480, 20))
            field.setStringValue_(text)
            field.setBezeled_(False)
            field.setDrawsBackground_(False)
            field.setEditable_(False)
            field.setSelectable_(False)
            content.addSubview_(field)
            return field

        def input_field(y, height=24, placeholder=""):
            field = NSTextField.alloc().initWithFrame_(NSMakeRect(20, y, 480, height))
            field.setPlaceholderString_(placeholder)
            content.addSubview_(field)
            return field

        label("Categorie", 528)
        self.ctrl_category = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(20, 500, 480, 26), False
        )
        for key in CATEGORY_ORDER:
            self.ctrl_category.addItemWithTitle(CATEGORY_LABELS.get(key, key))
        content.addSubview_(self.ctrl_category)

        label("Gravite", 468)
        self.ctrl_severity = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(20, 440, 480, 26), False
        )
        for sev in [s.value for s in Severity]:
            self.ctrl_severity.addItemWithTitle(SEVERITY_LABELS.get(sev, sev))
        self.ctrl_severity.selectItemAtIndex_(1)
        content.addSubview_(self.ctrl_severity)

        label("Equipe concernee", 408)
        self.ctrl_team = input_field(380, 24, "Ex: Support N2, Delivery...")

        label("Sujet", 348)
        self.ctrl_subject = input_field(320, 24, "Resume court de la deviation")

        label("Description", 288)
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 130, 480, 150))
        self.ctrl_description = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, 480, 150))
        scroll.setDocumentView_(self.ctrl_description)
        scroll.setHasVerticalScroller_(True)
        content.addSubview_(scroll)

        self.ctrl_attachments_label = input_field(100, 24, "Aucune piece jointe")
        self.ctrl_attachments_label.setEditable_(False)

        btn_mail = NSButton.alloc().initWithFrame_(NSMakeRect(20, 64, 300, 28))
        btn_mail.setTitle("Joindre le mail selectionne dans Mail.app")
        btn_mail.setBezelStyle_(1)
        btn_mail.setTarget_(self)
        btn_mail.setAction_("attachSelectedMail:")
        content.addSubview_(btn_mail)

        btn_save = NSButton.alloc().initWithFrame_(NSMakeRect(330, 64, 170, 28))
        btn_save.setTitle("Enregistrer")
        btn_save.setBezelStyle_(1)
        btn_save.setTarget_(self)
        btn_save.setAction_("saveDeviation:")
        content.addSubview_(btn_save)

        self.ctrl_status = label("", 30)

    def attachSelectedMail_(self, sender) -> None:
        if sys.platform != "darwin":
            _alert("macOS requis", "L'integration Mail.app ne fonctionne que sur macOS.")
            return
        from . import mailapp

        try:
            mails = mailapp.fetch_selected_messages(self.config.attachments_dir)
        except RuntimeError as exc:
            _alert("Mail.app", str(exc))
            return
        for mail in mails:
            self.pending_attachments.append(mail["path"])
        if mails:
            self.pending_source_subject = mails[0]["subject"]
            self.pending_source_sender = mails[0]["sender"]
            if not self.ctrl_subject.stringValue():
                self.ctrl_subject.setStringValue_(mails[0]["subject"] or "")
            if not self.ctrl_description.string():
                self.ctrl_description.setString_(f"Mail source de {mails[0]['sender']}\n\n")
        self._refresh_attachments_label()
        _alert("Piece jointe", f"{len(mails)} message(s) joint(s) a la deviation.")

    def saveDeviation_(self, sender) -> None:
        try:
            category = CATEGORY_ORDER[self.ctrl_category.indexOfSelectedItem()]
            severity = [s.value for s in Severity][self.ctrl_severity.indexOfSelectedItem()]
            dev = service.add_deviation(
                self.config,
                self.store,
                category=category,
                severity=severity,
                team=self.ctrl_team.stringValue(),
                subject=self.ctrl_subject.stringValue(),
                description=self.ctrl_description.string(),
                attachments=list(self.pending_attachments),
                source_subject=self.pending_source_subject,
                source_sender=self.pending_source_sender,
            )
        except ValueError as exc:
            _alert("Saisie incomplete", str(exc))
            return
        self.pending_attachments = []
        self.pending_source_subject = ""
        self.pending_source_sender = ""
        self.ctrl_team.setStringValue_("")
        self.ctrl_subject.setStringValue_("")
        self.ctrl_description.setString_("")
        self._refresh_attachments_label()
        self.ctrl_status.setStringValue_(f"Deviation enregistree: {dev.id}")

    def sendSummary_(self, sender) -> None:
        try:
            draft, transport = service.send_summary(self.config, self.store)
        except (RuntimeError, ValueError) as exc:
            _alert("Envoi impossible", str(exc))
            return
        _alert(
            "Resume envoye",
            f"Objet : {draft.subject}\n"
            f"Destinataires : {', '.join(draft.to)}\n"
            f"Pieces jointes : {len(draft.attachments)}\n"
            f"Transport : {transport}",
        )

    def showWindow_(self, sender) -> None:
        from AppKit import NSApp

        if self.window is None:
            self.build_window()
        self.window.center()
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

    def quit_(self, sender) -> None:
        from AppKit import NSApp

        NSApp.terminate_(None)

    def _refresh_attachments_label(self) -> None:
        if self.pending_attachments:
            names = ", ".join(Path(p).name for p in self.pending_attachments)
            self.ctrl_attachments_label.setStringValue_(f"Pieces jointes : {names}")
        else:
            self.ctrl_attachments_label.setStringValue_("Aucune piece jointe")


def run() -> None:
    if sys.platform != "darwin":
        raise RuntimeError("L'application graphique necessite macOS (PyObjC / AppKit).")
    from AppKit import NSApp, NSMenu, NSMenuItem, NSStatusBar, NSVariableStatusItemLength

    app = NSApp.sharedApplication()
    app.setActivationPolicy_(1)

    controller = Controller.alloc().init()

    class AppDelegate(NSObject):
        def applicationDidFinishLaunching_(self, notification):
            status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
                NSVariableStatusItemLength
            )
            status_item.button().setTitle("Deviations")
            menu = NSMenu.alloc().init()
            item_new = menu.addItemWithTitle_action_keyEquivalent_(
                "Nouvelle deviation...", "showWindow:", "n"
            )
            item_new.setTarget_(controller)
            item_send = menu.addItemWithTitle_action_keyEquivalent_(
                "Envoyer le resume par e-mail...", "sendSummary:", "e"
            )
            item_send.setTarget_(controller)
            menu.addItem_(NSMenuItem.separatorItem())
            item_quit = menu.addItemWithTitle_action_keyEquivalent_("Quitter", "quit_:", "q")
            item_quit.setTarget_(controller)
            status_item.setMenu_(menu)

    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    run()
