# Deviation Tracker (macOS)

Application macOS pour remonter rapidement les **déviations** par rapport au fonctionnement normal de votre équipe (non-respect de SLA, pas de réponse à un e-mail, attente d'une décision claire d'un directeur, etc.), joindre le **mail source / le reply**, générer un **résumé** et l'envoyer **par e-mail** — à votre équipe ou à d'autres destinataires.

## Fonctionnement

- Chaque déviation est enregistrée avec : catégorie, gravité, équipe, sujet, description, statut (ouverte / suivie / résolue) et pièces jointes.
- Sur macOS, le bouton **« Joindre le mail sélectionné dans Mail.app »** récupère le ou les messages sélectionnés dans Mail.app (source brute `.eml`) et les joint à la déviation.
- **« Envoyer le résumé par e-mail »** regroupe toutes les déviations ouvertes, construit un résumé texte + HTML, joint les e-mails sources, puis envoie via **Mail.app** (envoi direct ou brouillon) ou via **SMTP** si configuré. Vos propres adresses (`moi`) sont toujours destinataires.

## Installation (sur votre Mac)

```bash
cd deviation-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[gui]"
cp examples/config.example.json "$HOME/Library/Application Support/DeviationTracker/config.json"
```

Éditez ensuite `~/Library/Application Support/DeviationTracker/config.json` avec vos vraies adresses (`moi`, `groupes`, `groupes_par_defaut`).

## Utilisation

Application graphique (barre de menu, icône « Deviations ») :

```bash
python3 -m deviation_tracker.app
```

Ligne de commande :

```bash
# Enregistrer une déviation en joignant le mail sélectionné dans Mail.app
deviation-tracker ajouter \
  --categorie sla_non_respect --gravite haute \
  --equipe Support --sujet "Ticket #123 traité en 6h au lieu de 2h" \
  --description "Client VIP non pris en charge dans les délais" \
  --depuis-mail

# Lister / résumer
deviation-tracker lister --statut ouverte
deviation-tracker resume --format text

# Envoyer le résumé des déviations ouvertes (à mon équipe + moi, avec PJ)
deviation-tracker envoyer

# Envoyer à d'autres destinataires, en brouillon dans Mail.app
deviation-tracker envoyer --groupes direction --a qualite@entreprise.fr --mode draft

# Changer le statut d'une déviation
deviation-tracker statut <id> --statut resolue
```

Catégories disponibles : `sla_non_respect`, `pas_de_reponse_mail`, `attente_decision_direction`, `autre`.

## Configuration (`config.json`)

| Clé | Rôle |
|---|---|
| `moi` | Vos adresses — toujours destinataires du résumé |
| `groupes` | Noms de groupes → listes d'adresses (mon équipe, direction, qualité…) |
| `groupes_par_defaut` | Groupes utilisés par défaut par `envoyer` |
| `mode_envoi` | `send` (envoi direct) ou `draft` (brouillon Mail.app) |
| `utiliser_mail_app` | `true` = utiliser Mail.app (pièces jointes + envoi) |
| `smtp` | `null`, ou `{host, port, username, password_env, use_tls, from}` — le mot de passe est lu depuis une variable d'environnement, jamais stocké en clair |

Données stockées dans `~/Library/Application Support/DeviationTracker/` (`deviations.json`, `pieces_jointes/`).

## Packaging en .app autonome

```bash
pip install py2app
python3 setup_app.py py2app
# -> dist/DeviationTracker.app (application de barre de menu, LSUIElement)
```

## Tests

```bash
pip install -e ".[test]"
pytest
```

Le cœur (modèle, stockage, résumé, composition e-mail, génération des scripts AppleScript) est testé hors macOS ; l exécution réelle de Mail.app se fait uniquement sur macOS via `osascript`.
