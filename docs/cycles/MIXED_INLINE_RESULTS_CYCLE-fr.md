[English](MIXED_INLINE_RESULTS_CYCLE.md)

# Résultats mêlant références entières et intérieures

## Périmètre

Raccordement de ST7–ST14 et des règles existantes de résultats par branche :
une référence peut désigner un objet entier ou une sous-structure du même type.
Le mode partagé/mutable reste identique entre les branches. Toutes les cibles
possibles restent suivies statiquement. Aucune promotion de durée de vie,
allocation supplémentaire ni modification normative.

## Implémentation

Lorsqu'une possibilité est intérieure, le résultat C utilise le descripteur
de vue existant. Les autres branches convertissent leur pointeur entier vers
un descripteur de la même cible, sans déplacer son stockage. La conversion
est sélectionnée par les types C ; elle évalue la valeur une seule fois.

Le raccordement concerne les retours explicites et terminaux des fonctions,
les résultats de if et match, et les sorties de boucle par break. Les accès,
copies et paramètres prennent en compte tous les référents d'une liaison,
au lieu de choisir leur représentation à partir du premier seulement.
Le chargement d'un champ mutable stocké utilise aussi le descripteur lorsque
ses cibles mélangent les deux représentations.

L'opération de diagnostic `address` conserve l'adresse antérieure de la cible
entière et celle du stockage intérieur pour une sous-structure. La conversion
de représentation ne change donc pas cette adresse observable.

## Cas exécutés

`tests/test_mixed_inline_results.py` : sept méthodes, douze programmes admis
exécutés et onze programmes invalides refusés par `verify_program` et
`compile_source`.

- Retour conditionnel puis relais : les deux branches exécutées, adresse et
  valeur comparées, drop de chacune des cibles possibles refusé avant le dernier usage.
- If retournant un emprunt mutable : écriture dans la bonne cible pour les deux
  branches et accès concurrent refusé.
- Deux sorties break de représentations différentes, avec la valeur attendue
  pour chaque branche.
- Match dont une branche retourne une référence entière et l'autre une vue.
- Copie de la valeur ciblée, stockage de la référence dans une structure,
  extraction et destruction du porteur.
- Résultat mutable d'une fonction, stockage dans un Writer, réemprunt retourné
  puis passage à une fonction de mutation ; destruction et accès concurrents refusés.
- Branche retournant une vue d'une allocation locale trop courte refusée.

## Exécutions et corrections

Clang C11/pthread, UBSan fatal, avertissements comme erreurs ; O0 puis O2.
Les attentes portent sur les valeurs, l'identité observée et les refus, pas
seulement sur le succès de la compilation.

| Passage | Résultat | Journal dans `validation/` |
| --- | --- | --- |
| Initial O0 | 5 méthodes, 2 échecs de sous-cas, 3,736 s, code 1 | `mixed-inline-results-o0-first.log` |
| Deuxième O0 | 5 méthodes, 4,542 s, code 0 | `mixed-inline-results-o0-second.log` |
| Troisième O0 | 7 méthodes, 5,489 s, code 0 | `mixed-inline-results-o0-third.log` |
| Match historique O2 | 6 méthodes, 5,794 s, code 0 | `mixed-inline-results-match-o2.log` |
| Régression O2 | 98 méthodes, 62,352 s, code 0 | `mixed-inline-results-regression-o2.log` |
| Final O2 | 13 méthodes, 10,060 s, code 0 | `mixed-inline-results-final-o2.log` |

Le premier passage a révélé un mauvais choix de représentation lors d'une copie :
la liaison avait un premier référent entier et un autre intérieur, mais le backend
lisait le descripteur comme un Cell*. La représentation est maintenant choisie
sur l'ensemble des référents. Les attentes des tests sont restées inchangées.
Après la régression, le choix du type des retours anticipés a été simplifié en
un typedef C local à la fonction générée, sans substitution textuelle dans son
corps. Le passage final reprend les sept méthodes ciblées et les six méthodes
historiques de match sur cette version.

La régression liée reprend les modules de vues, références stockées, constructions
contenues, réemprunts stockés, structures mixtes async et remplacements propriétaires.
Les six méthodes historiques ciblent les retours typés de match, les retours
anticipés et les projections composées. Les journaux donnent les noms complets.

## Limites

Le lot couvre les chemins synchrones indiqués ; les captures et résultats async
de vues restent à raccorder. Le choix commun de représentation ne prouve pas
la couverture de tous les graphes récursifs et de toutes les combinaisons de
projections. Pas de nouvelle campagne de mutations, de génération adversariale
ou de modèle indépendant. ASan et un second compilateur C n'ont pas été exécutés.
Ces tests ne constituent pas une preuve générale de sûreté.

Diffs : `validation/mixed-inline-results-{crust,structure_views}.py.patch`,
comparés à `/tmp/crust-before-mixed-inline-results/`.
