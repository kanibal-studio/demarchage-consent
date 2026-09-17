# demarchage-consent

[![PyPI](https://img.shields.io/pypi/v/demarchage-consent)](https://pypi.org/project/demarchage-consent/) [![Licence MIT](https://img.shields.io/badge/licence-MIT-blue)](https://github.com/kanibal-studio/demarchage-consent/blob/main/LICENSE)

**FR — Validité du consentement au démarchage téléphonique (France).**
Une fonction pure, sans dépendance, qui prend la date de recueil d'un
consentement et rend `valide`, `expire`, `revoque` ou `preuve_manquante`,
conformément au décret n° 2026-662 du 23 juillet 2026 (JO du 25/07, en
vigueur le 11/08/2026, art. R. 223-1) : consentement libre, spécifique,
clair et révocable, valable **un an au maximum** à compter du recueil,
preuve numérique datée conservée **trois ans**.

**EN — French cold-call consent validity.** A pure, dependency-free
function: give it the date a phone-marketing consent was collected, get
`valide` (valid), `expire` (expired), `revoque` (revoked) or
`preuve_manquante` (no dated proof), per French decree 2026-662
(entered into force 2026-08-11): one-year maximum validity from
collection, revocable at any time, dated digital proof kept for three
years.

## Pourquoi / Why

Le décret est récent et aucun outil open source équivalent n'a été
repéré à date (septembre 2026) ; juristes, éditeurs de CRM, centres
d'appels et agences doivent tous appliquer la même règle d'âge. Cette
bibliothèque est extraite d'une garde appliquée **en production** dans
un centre d'appels, avec une sémantique choisie pour ne jamais mentir :

- **fail-closed** — une date absente, illisible ou dans le futur ne vaut
  jamais « valide » (`preuve_manquante`), sans repli ni exception ;
- **le plafond légal borne tout** — `max_age_days` peut resserrer la
  fenêtre, jamais l'élargir au-delà de 365 jours ;
- **la révocation prime** — toute date de révocation lisible donne
  `revoque`, quel que soit l'âge du consentement.

EN: extracted from a production consent gate; fail-closed by design —
a missing/unreadable/future date is never "valid", the legal ceiling
can only be tightened, and a readable revocation always wins.

## Installation

```bash
pip install demarchage-consent        
```

Ou copiez `demarchage_consent/core.py` (~100 lignes, stdlib seule).

## Usage

```python
from demarchage_consent import evaluate_consent

evaluate_consent("2026-03-01T10:00:00Z")
# → 'valide'   (moins d'un an)

evaluate_consent("2024-03-01T10:00:00Z")
# → 'expire'   (plus d'un an)

evaluate_consent("2026-03-01T10:00:00Z", revoked_at="2026-06-01T00:00:00Z")
# → 'revoque'

evaluate_consent(None)          # → 'preuve_manquante'
evaluate_consent("pas une date")  # → 'preuve_manquante'  (fail-closed)

# Fenêtre resserrée à 30 jours (politique interne plus stricte que la loi) :
evaluate_consent("2026-08-01T00:00:00Z", max_age_days=30)  # → 'expire'
```

Les dates naïves (sans fuseau) sont interprétées comme UTC ; `now` est
injectable pour les tests et les replays.

## Ce que cette bibliothèque N'est PAS

- **Ce n'est pas un conseil juridique.** C'est une transposition en code
  d'une règle d'âge ; la responsabilité de la conformité globale
  (recueil, preuve, opposition Bloctel/DNC, preuve de la preuve) reste
  celle de l'appelant.
- Elle ne lit, ne stocke et ne transmet **aucune donnée personnelle** :
  elle ne voit que des dates.

EN: *Not legal advice — an age-rule in code; the caller owns overall
compliance. Handles dates only, never personal data.*

## Licence

MIT — voir `LICENSE`.
