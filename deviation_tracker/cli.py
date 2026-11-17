from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import service
from .config import AppConfig
from .models import CATEGORY_LABELS, Category, SEVERITY_LABELS, Severity, STATUSES, STATUS_LABELS
from .store import DeviationStore
from .summary import build_summary


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deviation-tracker",
        description="Remontee des deviations de l'equipe avec resume envoye par e-mail.",
    )
    sub = parser.add_subparsers(dest="commande", required=True)

    p_add = sub.add_parser("ajouter", help="Enregistrer une deviation")
    p_add.add_argument("--categorie", required=True, choices=[c.value for c in Category])
    p_add.add_argument("--gravite", default=Severity.MOYENNE.value, choices=[s.value for s in Severity])
    p_add.add_argument("--equipe", required=True)
    p_add.add_argument("--sujet", required=True)
    p_add.add_argument("--description", default="")
    p_add.add_argument("--piece-jointe", action="append", default=[], metavar="FICHIER",
                       help="Fichier a joindre (ex: .eml) - repeter l'option pour plusieurs fichiers")
    p_add.add_argument("--depuis-mail", action="store_true",
                       help="Joindre le(s) message(s) selectionne(s) dans Mail.app (macOS)")

    p_list = sub.add_parser("lister", help="Lister les deviations")
    p_list.add_argument("--equipe")
    p_list.add_argument("--statut", default="toutes", choices=list(STATUSES) + ["toutes"])
    p_list.add_argument("--depuis", metavar="AAAA-MM-JJ")

    p_resume = sub.add_parser("resume", help="Afficher le resume des deviations")
    p_resume.add_argument("--statut", default="ouverte", choices=list(STATUSES) + ["toutes"])
    p_resume.add_argument("--depuis", metavar="AAAA-MM-JJ")
    p_resume.add_argument("--format", choices=["text", "html"], default="text")

    p_send = sub.add_parser("envoyer", help="Envoyer le resume par e-mail (avec pieces jointes)")
    p_send.add_argument("--groupes", metavar="g1,g2", help="Groupes de destinataires (config.json)")
    p_send.add_argument("--a", action="append", default=[], metavar="ADRESSE",
                       help="Destinataire supplementaire - repeter l'option")
    p_send.add_argument("--statut", default="ouverte", choices=list(STATUSES) + ["toutes"])
    p_send.add_argument("--depuis", metavar="AAAA-MM-JJ")
    p_send.add_argument("--mode", choices=["send", "draft"], default=None,
                       help="send = envoyer directement, draft = brouillon dans Mail.app")

    p_status = sub.add_parser("statut", help="Changer le statut d'une deviation")
    p_status.add_argument("id")
    p_status.add_argument("--statut", required=True, choices=list(STATUSES))

    p_cfg = sub.add_parser("config", help="Afficher les chemins et destinataires configures")
    return parser


def _print_deviation(dev) -> str:
    return (
        f"[{dev.id}] {dev.created_at} | {dev.status_label()} | {dev.category_label()} | "
        f"{dev.severity_label()} | equipe: {dev.team} | {dev.subject}"
        + (f" | PJ: {', '.join(Path(a).name for a in dev.attachments)}" if dev.attachments else "")
    )


def main(argv=None) -> int:
    args = _make_parser().parse_args(argv)
    config = AppConfig.load()
    store = DeviationStore(config.store_path)

    if args.commande == "ajouter":
        attachments = list(args.piece_jointe)
        source_subject = ""
        source_sender = ""
        if args.depuis_mail:
            if sys.platform != "darwin":
                print("--depuis-mail necessite macOS (Mail.app)", file=sys.stderr)
                return 2
            from . import mailapp

            mails = mailapp.fetch_selected_messages(config.attachments_dir)
            for mail in mails:
                attachments.append(mail["path"])
            if mails:
                source_subject = mails[0]["subject"]
                source_sender = mails[0]["sender"]
        dev = service.add_deviation(
            config, store,
            category=args.categorie,
            severity=args.gravite,
            team=args.equipe,
            subject=args.sujet,
            description=args.description,
            attachments=attachments,
            source_subject=source_subject,
            source_sender=source_sender,
        )
        print(f"Deviation enregistree: {dev.id}")
        print(_print_deviation(dev))
        return 0

    if args.commande == "lister":
        devs = store.filter(team=args.equipe, status=args.statut, since=args.depuis)
        if not devs:
            print("Aucune deviation.")
        for dev in devs:
            print(_print_deviation(dev))
        return 0

    if args.commande == "resume":
        devs = store.filter(status=args.statut, since=args.depuis)
        summary = build_summary(devs)
        if args.format == "html":
            print(summary.html)
        else:
            print(summary.text)
        return 0

    if args.commande == "envoyer":
        groups = [g.strip() for g in args.groupes.split(",")] if args.groupes else None
        try:
            draft, transport = service.send_summary(
                config, store,
                groups=groups,
                extra_emails=args.a,
                since=args.depuis,
                status=args.statut,
                mode=args.mode,
            )
        except (RuntimeError, ValueError) as exc:
            print(f"Erreur: {exc}", file=sys.stderr)
            return 2
        print(f"Resume envoye via {transport}")
        print(f"Destinataires : {', '.join(draft.to)}")
        print(f"Objet : {draft.subject}")
        print(f"Pieces jointes : {len(draft.attachments)}")
        return 0

    if args.commande == "statut":
        try:
            dev = store.update_status(args.id, args.statut)
        except KeyError as exc:
            print(f"Erreur: {exc}", file=sys.stderr)
            return 2
        print(f"Statut mis a jour: {_print_deviation(dev)}")
        return 0

    if args.commande == "config":
        print(f"Dossier de donnees : {config.home}")
        print(f"Fichier de config  : {config.config_path}")
        print(f"Deviations         : {config.store_path}")
        print(f"Pieces jointes     : {config.attachments_dir}")
        print(f"Mes adresses (moi) : {', '.join(config.moi) or '(non configure)'}")
        for name, addrs in sorted(config.groupes.items()):
            print(f"Groupe {name}      : {', '.join(addrs)}")
        print(f"Groupes par defaut : {', '.join(config.groupes_par_defaut) or '(aucun)'}")
        print(f"Mode d'envoi       : {config.mode_envoi} via "
              f"{'Mail.app' if config.utiliser_mail_app else 'SMTP' if config.smtp else 'non configure'}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
