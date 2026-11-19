[English](LOOP_REPLACEMENT_VALIDATION.md)

# Validation du remplacement d'un receveur à travers une boucle

Ce cycle étend l'implémentation de S4, S5, T7, T9, T11 et V4 aux
remplacements explicites de receveurs déclarés avant une boucle.
Il applique les prémisses existantes de durée de vie, d'emprunt et
d'ordre de destruction des règles D1, B2, B3, L3 et A5.

Le remplacement évalue sa partie droite puis détruit l'ancienne allocation.
Le pointeur C du receveur est mis à jour après le nettoyage de l'itération,
avant la reprise par `continue` ou la fin normale du corps. Chaque sortie
`break`, y compris la sortie par test faux d'un `while`, contribue à la
jonction après la boucle. Les provenances, dépendances et variantes possibles
sont propagées aux reprises et aux contrats de fonctions. Un `return`
n'alimente pas la jonction de la boucle.

## Contre-exemples

- Réinitialiser un pool au début de l'itération est dangereux si le receveur
  peut désormais venir de ce pool et doit encore être lu. Le vérificateur
  réanalyse la boucle avec la provenance du remplacement et refuse ce cas.
- En portant l'identité abstraite du receveur d'une itération à l'autre,
  un ancien accès importé pouvait redevenir visible dans le grand-parent
  avec son ancien pointeur C. Le cas minimal importe `r`, remplace `r`
  dans un `while`, puis marque `<- r;` dans le bloc d'import.
  L'import d'origine est maintenant détaché quand une reprise peut remplacer
  l'allocation. L'accès initial après le bloc est refusé.
- Un emprunt formé avant la boucle ne suit pas le remplacement. Un voisin
  valide emprunte la valeur dans l'itération et termine cet emprunt avant
  le remplacement. Les ordres de réception contradictoires entre le
  premier passage et les reprises restent refusés.

## Vérifications

La régression globale a réussi ses 818 tests, répartis en quatre groupes.

[Test ciblé](../tests/test_loop_replacements.py) avec 14 méthodes, 16 exécutions
de programmes admis et huit programmes refusés aux deux stages. Six
séquences générées avec la graine 20261103 sont comparées à un modèle
indépendant qui remplace une valeur à chaque itération et enregistre les
destructions. Les autres cas vérifient notamment l'adresse, le nettoyage,
les boucles imbriquées, les valeurs de break, les retours de fonctions,
les variantes d'enum et la réutilisation d'un pool de deux slots.
Trois exécutions manuelles complètent la suite ciblée. Deux receveurs
remplacés à la même itération affichent `1` puis `11` et leurs
remplacements sont détruits dans l'ordre `11`, `1`. Un emprunt
fourni par `break` après une reprise affiche `20`. Un résultat de
fonction sélectionné entre deux sorties `break` affiche également `20`.

Les 14 tests ciblés passent sous Clang avec `-O2` et UBSan sans
récupération. ASan reste indisponible sur cet hôte selon la sonde minimale
du [cycle précédent](LOOP_RESULTS_VALIDATION.md).
Les deux [mutations ciblées](../validation/loop-replacement-mutations.json)
sont détectées. Elles omettent respectivement la mise à jour du pointeur C
et le détachement de l'ancien import.

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_loop_replacements.py -q
python3 tests/run_loop_replacement_mutations.py
```

L'analyse reste conservative. Elle refuse les ordres incompatibles, les
transferts déjà marqués qui interfèrent avec le remplacement et les
dépendances d'un objet vivant vers une génération remplacée du receveur.
Les limites de convergence restent applicables. Les tests ne démontrent
pas la validité de tous les programmes de boucles.
