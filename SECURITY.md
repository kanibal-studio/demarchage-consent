# Sécurité / Security

**FR.** Cette bibliothèque n'effectue aucune entrée/sortie, ne lit aucune donnée
personnelle et n'a aucune dépendance : sa surface d'attaque se limite à l'analyse
de chaînes de dates. Son contrat est de **ne jamais lever d'exception** sur une
donnée d'entrée et de **ne jamais rendre « valide » à tort** (fail-closed).

Si vous trouvez une entrée qui fait lever une exception, qui rend `valide` alors
qu'elle ne le devrait pas, ou qui élargit le plafond légal de 365 jours, il
s'agit d'une faille de sûreté : signalez-la en privé via l'onglet **Security →
Report a vulnerability** du dépôt GitHub (ou, à défaut, par une issue en
omettant les détails d'exploitation). Un correctif et une version corrective
sont publiés en priorité, avec un test de non-régression.

Versions prises en charge : la dernière version publiée sur PyPI.

**EN.** No I/O, no personal data, no dependencies: the attack surface is date
string parsing. The contract is *never raise on input data* and *never wrongly
return `valide`* (fail-closed). If you find an input that raises, that is wrongly
valid, or that widens the 365-day legal ceiling, please report it privately via
GitHub **Security → Report a vulnerability** (or an issue without exploitation
details). Only the latest PyPI release is supported.
