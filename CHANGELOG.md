# Changelog

Toutes les évolutions notables de ce projet sont consignées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ;
numérotation : [SemVer](https://semver.org/lang/fr/).

## [0.2.0] — 2026-09-23

Publication PyPI : pousser le tag `v0.2.0` (le workflow rejoue la CI, vérifie
que le tag correspond à `__version__`, puis publie par Trusted Publishing).

### Corrigé

- **Exception sur certaines dates.** Une date lisible mais non convertible en
  UTC (ex. `9999-12-31T23:59:59-23:59`, `0001-01-01T00:00:00+23:59`) faisait
  lever `OverflowError` au lieu de rendre `preuve_manquante`, en violation du
  contrat « aucune exception ».
- **Dérive de version.** `__version__` valait `0.1.0` alors que le paquet
  était publié en `0.1.2`. La version n'a plus qu'une source
  (`demarchage_consent/__init__.py`), lue par `pyproject.toml` et contrôlée
  par le workflow de release, qui refuse un tag discordant.
- **Avertissements de build.** Métadonnées de licence au format PEP 639
  (`license = "MIT"`, `license-files`), suppression du classifier de licence
  déprécié : `python -m build` et `twine check --strict` passent sans
  avertissement.

### Modifié — comportement (à lire avant de migrer)

- **Grammaire des dates explicite et déterministe.** Les chaînes ne sont plus
  déléguées à `datetime.fromisoformat`, dont l'acceptation variait selon la
  version de Python (`20260901`, `+0200` ou neuf décimales passaient en 3.11+
  mais pas en 3.9/3.10 ; `z` minuscule échouait partout). La grammaire
  `AAAA-MM-JJ[(T| )HH[:MM[:SS[.f]]][Z|±HH[:MM[:SS]]|±HHMM]]` est identique
  partout. Nouveautés acceptées : `z` minuscule, `+HHMM`, `+HH`, décalage
  avec secondes, 1 à 9 décimales, virgule décimale. Désormais refusés
  (→ `preuve_manquante`) : formats ISO « basiques » sans tirets, dates de
  semaine ou ordinales, et tout format exotique que 3.11+ tolérait.
- **Plus de coercition de type.** Seuls `str`, `datetime` et `date` sont
  acceptés ; un entier comme `20260901` (lu comme une date en 3.11+ via
  `str()`) vaut `preuve_manquante`.
- **La révocation prime vraiment tout.** Une révocation datée lisible rend
  `revoque` même si la date de recueil est absente, illisible ou future
  (auparavant `preuve_manquante`). Les deux états interdisent l'appel ;
  `revoque` évite de re-solliciter le consentement d'une personne qui a dit
  non. Le docstring le promettait déjà, le code ne le faisait pas.
- **Une révocation illisible vaut révocation (fail-closed).** Jusqu'en 0.1.2,
  `revoked_at=True`, `"oui"`, `1` ou une date mal formée étaient ignorés et
  le verdict pouvait rester `valide` : une personne qui avait dit non
  redevenait appelable. Désormais seules les absences explicites (`None`,
  `False`, `0`, `NaN`/`NaT`, chaîne vide, `"false"`, `"faux"`, `"non"`,
  `"no"`, `"0"`, `"n/a"`, `"na"`, `"none"`, `"null"`, `"-"`, casse
  ignorée) ne sont pas des révocations ; toute autre valeur rend `revoque`
  (`revoked_at=None` dans `assess_consent`).
- **`now` explicite et illisible lève `ValueError`** au lieu de retomber
  silencieusement sur l'horloge réelle, ce qui pouvait changer le verdict
  d'un replay. `now=None` reste l'horloge UTC courante.
- `max_age_days` booléen (`True`/`False`) vaut désormais le plafond du
  décret, comme toute valeur illisible.

### Ajouté

- `assess_consent()` et `ConsentAssessment` : statut, `expires_at`,
  `days_remaining`, `proof_retention_until` (trois ans — la constante
  `DECREE_PROOF_RETENTION_DAYS`, jusqu'ici inutilisée), `max_age_days`
  effectif, `is_valid`, `to_dict()` sérialisable en JSON. `evaluate_consent`
  en est le raccourci (une seule logique).
- Ligne de commande `demarchage-consent` / `python -m demarchage_consent`
  (codes de sortie 0/1/2, `--json`, `--now`, `--revoked-at`,
  `--max-age-days`, `--version`).
- Objets `date` acceptés (minuit UTC).
- Typage : `ConsentStatus` (`Literal`), `STATUSES`, constantes `Final`,
  marqueur `py.typed`, `mypy --strict` sur le paquet et les tests.
- `LAW_REFERENCE` (loi n° 2025-594 du 30 juin 2025, art. 13).
- Tests : 14 → 138, dont des tests de propriétés Hypothesis (aucune entrée ne
  lève, chaîne ISO et objet `datetime` rendent le même verdict, règle d'âge
  exacte à la microseconde, plafond toujours entre 1 et 365) ; exécutés sur
  Python 3.9 → 3.14.
- CI GitHub Actions : tests sur la matrice 3.9 → 3.14, ruff (lint + format),
  mypy, build + `twine check --strict` ; release conditionnée à la CI et au
  contrôle tag = version ; actions épinglées par SHA (le workflow de
  publication détient le jeton OIDC PyPI) ; Dependabot (actions et
  dépendances de dev).
- Extra `dev`, configuration ruff / mypy / pytest dans `pyproject.toml`,
  `.gitignore`, `SECURITY.md`, ce changelog.
- README : ordre de décision, grammaire des dates, limites assumées
  (365 jours vs année civile), références
  légales (loi et décret), procédure de publication.

## [0.1.2] — 2026-09-18

- README : section « Maintenu par ».

## [0.1.1] — 2026-09-18

- README : installation via PyPI, badges PyPI/MIT, URLs du projet.

## [0.1.0] — 2026-09-16

- Première publication : `evaluate_consent()`, quatre états, plafond de
  365 jours, sémantique fail-closed ; publication PyPI par Trusted Publishing.

[0.2.0]: https://github.com/kanibal-studio/demarchage-consent/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/kanibal-studio/demarchage-consent/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/kanibal-studio/demarchage-consent/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/kanibal-studio/demarchage-consent/releases/tag/v0.1.0
