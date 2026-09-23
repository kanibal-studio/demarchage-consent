# demarchage-consent

[![PyPI](https://img.shields.io/pypi/v/demarchage-consent)](https://pypi.org/project/demarchage-consent/)
[![Python](https://img.shields.io/pypi/pyversions/demarchage-consent)](https://pypi.org/project/demarchage-consent/)
[![CI](https://github.com/kanibal-studio/demarchage-consent/actions/workflows/ci.yml/badge.svg)](https://github.com/kanibal-studio/demarchage-consent/actions/workflows/ci.yml)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-blue)](https://github.com/kanibal-studio/demarchage-consent/blob/main/LICENSE)

**FR — Validité du consentement au démarchage téléphonique (France).**
Une fonction pure, sans dépendance, qui prend la date de recueil d'un
consentement et rend `valide`, `expire`, `revoque` ou `preuve_manquante`,
conformément au régime d'opt-in en vigueur depuis le 11 août 2026 (loi
n° 2025-594 du 30 juin 2025, art. 13 → art. L. 223-1 du code de la
consommation) et à son décret d'application n° 2026-662 du 23 juillet 2026
(JO du 25/07, art. R. 223-1) : consentement libre, spécifique, éclairé,
univoque et révocable, valable **un an au maximum** à compter du recueil,
sans renouvellement tacite, preuve numérique datée conservée **trois ans**.

**EN — French cold-call consent validity.** A pure, dependency-free
function: give it the date a phone-marketing consent was collected, get
`valide` (valid), `expire` (expired), `revoque` (revoked) or
`preuve_manquante` (no dated proof), per the French opt-in regime in force
since 2026-08-11 (law 2025-594, decree 2026-662): one-year maximum validity
from collection, no tacit renewal, revocable at any time, dated digital
proof kept for three years.

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
  `revoque`, quel que soit l'âge du consentement et même sans preuve de
  recueil : la personne a dit non, on ne la re-sollicite pas ;
- **déterministe** — le format de date accepté est défini par la
  bibliothèque, pas par la version de Python : la même chaîne rend le
  même verdict de Python 3.9 à 3.14, ce que la CI vérifie.

EN: extracted from a production consent gate; fail-closed by design —
a missing/unreadable/future date is never "valid", the legal ceiling
can only be tightened, a readable revocation always wins, and the
accepted date grammar is identical across Python versions.

## Installation

```bash
pip install demarchage-consent
```

Ou copiez `demarchage_consent/core.py` (un seul fichier, stdlib seule).
La ligne de commande s'utilise aussi sans installation permanente :
`pipx run demarchage-consent 2026-03-01T10:00:00Z`.

Python ≥ 3.9, aucune dépendance, typage complet (`py.typed`).

## Usage

### Verdict simple

```python
from demarchage_consent import evaluate_consent

evaluate_consent("2026-03-01T10:00:00Z")
# → 'valide'   (moins d'un an)

evaluate_consent("2024-03-01T10:00:00Z")
# → 'expire'   (plus d'un an)

evaluate_consent("2026-03-01T10:00:00Z", revoked_at="2026-06-01T00:00:00Z")
# → 'revoque'

evaluate_consent(None)  # → 'preuve_manquante'
evaluate_consent("pas une date")  # → 'preuve_manquante'  (fail-closed)

# Fenêtre resserrée à 30 jours (politique interne plus stricte que la loi) :
evaluate_consent("2026-08-01T00:00:00Z", max_age_days=30)  # → 'expire'

# Replay à une date donnée (tests, audits) :
evaluate_consent("2026-03-01", now="2027-03-01")  # → 'valide' (jour anniversaire)
evaluate_consent("2026-03-01", now="2027-03-02")  # → 'expire'
```

### Résultat détaillé : expiration, jours restants, conservation de la preuve

```python
from demarchage_consent import assess_consent

a = assess_consent("2026-03-01T10:00:00Z", now="2026-09-16T12:00:00Z")
a.status  # 'valide'
a.is_valid  # True
a.expires_at  # datetime(2027, 3, 1, 10, 0, tzinfo=UTC) — dernier instant valide
a.days_remaining  # 165 — pour planifier un renouvellement (None si non valide)
a.proof_retention_until  # datetime(2029, 2, 28, 10, 0, tzinfo=UTC) — fin des trois ans
a.max_age_days  # 365 — plafond effectivement appliqué
a.to_dict()  # dict sérialisable en JSON (dates ISO 8601 UTC)
```

`ConsentAssessment` est immuable (dataclass gelée) ; `evaluate_consent`
en est le raccourci et suit exactement la même logique.

### Ligne de commande

```bash
demarchage-consent 2026-03-01T10:00:00Z                    # affiche : valide  (code 0)
demarchage-consent 2024-03-01T10:00:00Z                    # affiche : expire  (code 1)
demarchage-consent 2026-03-01 --revoked-at 2026-06-01      # affiche : revoque (code 1)
demarchage-consent 2026-03-01 --now 2026-09-16 --json      # résultat détaillé en JSON
python -m demarchage_consent --help                        # équivalent
```

Code de sortie : `0` si `valide`, `1` pour tout autre état, `2` en cas
d'erreur d'usage (dont un `--now` illisible) — utilisable tel quel dans
un script ou un pipeline de conformité.

## Sémantique précise

Ordre de décision (le premier critère vérifié l'emporte) :

| # | Condition | État |
|---|-----------|------|
| 1 | `revoked_at` est une date lisible (même future ou antérieure au recueil) | `revoque` |
| 2 | `collected_at` absent, illisible, d'un type inattendu ou **postérieur à `now`** | `preuve_manquante` |
| 3 | `now − collected_at` > plafond (365 jours, ou moins si `max_age_days` resserre) | `expire` |
| 4 | sinon (le jour anniversaire, à la microseconde près, est encore valide) | `valide` |

- `now` : `None` (défaut) = horloge UTC courante. Une valeur explicite
  mais illisible lève `ValueError` : c'est une erreur de l'appelant, pas
  une donnée, et la remplacer en silence par l'horloge réelle pourrait
  changer le verdict d'un replay.
- `max_age_days` : `None`, `0`, négatif ou illisible = plafond du
  décret ; toute valeur > 365 est ramenée à 365.
- `revoked_at` illisible (`"n/a"`, `""`, `"false"`…) est **ignoré** — ce
  n'est pas une date de révocation. Si votre système stocke la révocation
  sous forme de booléen, convertissez-la en date avant l'appel.
- Aucune entrée (`collected_at`, `revoked_at`, `max_age_days`) ne fait
  lever d'exception, quel que soit son type ou sa valeur — vérifié par
  des tests de propriétés (Hypothesis).

## Dates acceptées

Chaînes : un sous-ensemble strict d'ISO 8601 / RFC 3339, le même sur
toutes les versions de Python :

```
AAAA-MM-JJ[(T| )HH[:MM[:SS[.ffffff]]][Z|±HH[:MM[:SS]]|±HHMM]]
```

Acceptés : `2026-09-01`, `2026-09-01T10:30`, `2026-09-01 10:30:15`,
`2026-09-01T10:30:15Z`, `2026-09-01t10:30:15z`, `2026-09-01T10:30:15.123Z`,
`2026-09-01T10:30:15.123456789+02:00` (fraction tronquée à la
microseconde, virgule décimale tolérée), `2026-09-01T10:30:15+0200`,
`2026-09-01T10:30:15+02` — c'est-à-dire tout ce que produisent
`datetime.isoformat()`, `Date.toISOString()` (JavaScript) ou une colonne
`TIMESTAMP` SQL. Les espaces autour sont ignorés.

Refusés (→ `preuve_manquante`) : formats « basiques » sans tirets
(`20260901`), dates de semaine ou ordinales (`2026-W36-1`, `2026-244`),
formats nationaux (`01/09/2026`), timestamps Unix, RFC 2822, et toute
date impossible (`2026-02-30`, `10:60`, décalage `+24:00`).

- Une date **naïve** (sans fuseau) est interprétée comme **UTC**.
- Un objet `datetime` est accepté tel quel (converti en UTC) ; un objet
  `date` vaut minuit UTC.
- Tout autre type (entier, flottant, `bytes`…) vaut `preuve_manquante` :
  aucune coercition implicite.

## Limites et choix assumés

- **365 jours, pas une année civile.** Le décret dit « un an » ; la
  bibliothèque compte 365 jours, jamais plus. Lorsqu'une année bissextile
  est traversée, c'est un jour plus strict que la date anniversaire — le
  côté sûr.
- **Ce n'est pas un conseil juridique.** C'est la transposition en code
  d'une règle d'âge ; la conformité globale (information du consommateur,
  recueil par acte positif clair, conservation et fourniture de la
  preuve, prise en compte des retraits, autres obligations du code de la
  consommation) reste la responsabilité de l'appelant.
- Elle ne lit, ne stocke et ne transmet **aucune donnée personnelle** :
  elle ne voit que des dates.

EN: *365 days, never a calendar year (one day stricter across leap
years); not legal advice — an age rule in code, the caller owns overall
compliance; handles dates only, never personal data.*

## Références légales

- [Code de la consommation, art. L. 223-1 à L. 223-7](https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006069565/LEGISCTA000032221441/)
  — version en vigueur depuis le 11 août 2026 (loi n° 2025-594 du
  30 juin 2025, art. 13).
- [Décret n° 2026-662 du 23 juillet 2026](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000054483939)
  relatif aux modalités de recueil, de conservation et de retrait du
  consentement (art. R. 223-1 et suivants).
- [economie.gouv.fr — Professionnels : comment respecter la réglementation sur le démarchage téléphonique](https://www.economie.gouv.fr/entreprises/developper-son-entreprise/innover-et-numeriser-son-entreprise/professionnels-comment-respecter-la-reglementation-sur-le-demarchage)

## Développement

```bash
pip install -e ".[dev]"
pytest                      # tests unitaires, de propriétés (Hypothesis) et de la CLI
ruff check . && ruff format --check .
mypy                        # strict, paquet et tests
```

La CI exécute ces vérifications sur Python 3.9 → 3.14 et construit le
paquet. Publication : mettre à jour `__version__` dans
`demarchage_consent/__init__.py` (source unique de la version) et
`CHANGELOG.md`, puis pousser le tag `vX.Y.Z` — le workflow refuse un tag
qui ne correspond pas à la version, rejoue la CI et publie sur PyPI via
Trusted Publishing. Historique des versions : [CHANGELOG.md](CHANGELOG.md).

## Maintenu par

[Altavista360](https://altavista360.com) — centre d'appels multilingue et plateformes de conseil en ligne pour l'Europe et le Canada. Cette bibliothèque est extraite de notre garde de consentement en production. Nos autres outils : [kanibal-studio](https://github.com/kanibal-studio).

EN: Maintained by [Altavista360](https://altavista360.com), a multilingual call-center and online-advice company (Europe & Canada) — extracted from our production consent gate.

## Licence

MIT — voir `LICENSE`.
