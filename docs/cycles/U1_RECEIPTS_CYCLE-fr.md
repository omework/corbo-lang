[English](U1_RECEIPTS_CYCLE.md)

# U1 — Usage des valeurs reçues, cycle du 7 novembre 2026

## Règles et portée

Suite de [OWNED_RESULTS_CYCLE.md](OWNED_RESULTS_CYCLE.md), intégration des
brouillons 01 et 07, sans nouvelle décision de langage. Le contrôle ne se
limite plus aux wrappers Option/Result : les allocations ordinaires, structures
locales représentées par une allocation, copies de structures, déplacements,
réceptions par await et résultats de blocs/if/boucles sont contrôlés.

Un nom `_` n'est pas un receveur propriétaire valide. Un nom préfixé `_` ne
dispense pas d'usage. Un usage conditionnel suffit. Le nettoyage implicite à
la sortie d'une portée ou lors du remplacement d'une ancienne allocation
ne compte pas comme usage explicite de cette réception. Les écritures de
contenu conservent leur comportement existant : elles utilisent l'allocation.
Le contrôle des réceptions ne modifie pas la convention des paramètres
consommateurs ni l'avertissement prévu pour une tâche inactive abandonnée.

## Contre-exemples corrigés

Les deux programmes acceptés à tort dans le cycle précédent sont désormais
refusés : `let unused = p.new(1);` et la réception inutilisée du résultat
propriétaire de `f(-> n).await`.

Autres cas trouvés pendant ce cycle :

- Une lecture de l'ancien contenu pouvait justifier à tort un remplacement
  depuis un bloc enfant, sans usage ultérieur de la nouvelle allocation.
- Une lecture après un deuxième remplacement pouvait être attribuée à la
  première réception. Un nom identique ne suffit pas à prouver l'usage.
- Une réaffectation async pouvait abandonner son nouveau résultat sans usage.
- Le premier contrôle async rejetait à tort une utilisation après une
  expression passée en argument : il ne voyait pas la continuation de
  l'instruction englobante.
- Il rejetait aussi un usage dans un argument suivant. Le suivi prend désormais
  en compte l'ordre gauche → droite, y compris un remplacement intermédiaire.

La vérification synchrone suit les continuations, les remplacements, les bras,
les masquages locaux et les reprises de boucle. L'async conserve les
continuations d'instructions et d'arguments nécessaires à ce même contrôle.
Les analyses de prêt UTF-8 gardent leur mode ordinaire distinct du mode
« usage d'une réception propriétaire » ; la régression UTF-8 est incluse.

## Modèle indépendant et tests dédiés

`tests/test_owner_usage.py` contient douze méthodes. Le modèle avance dans
l'ordre des instructions et ouvre une nouvelle identité de réception à chaque
remplacement. Il conserve, pour chacune, l'existence d'une opération explicite.
Il ne consulte ni les contrats du compilateur, ni le C généré.

L'alphabet est lecture, écriture de contenu, remplacement et lecture
conditionnelle. Les séquences de longueur deux sont croisées avec la présence
ou l'absence d'un drop final et les deux valeurs du drapeau : 64 cas,
dont 42 programmes admis exécutés et 22 programmes refusés. Pour chaque
programme admis, sorties et ordre des valeurs détruites sont comparés au modèle.
Aucune graine : l'énumération est déterministe et exhaustive sur ce petit domaine.

Les autres cas dédiés vérifient `_`, noms préfixés `_`, structures locales,
copie, chaînes et vecteurs alloués, renommages, blocs, boucles, réaffectation
vers un parent, sortie par await, résultat de join, masquage d'un nom,
continuation après un appel et usage par l'argument suivant.

Commande standard :

```sh
PYTHONPATH=.:tests python3 -m unittest test_owner_usage test_owned_results -v
```

Les deux modules réunissent 21 méthodes ; les 9 méthodes du cycle précédent
conservent notamment les contrôles d'emprunts, de motifs consommateurs, de
capacité et de réemploi. Le script `/tmp/crust_owner_usage_optimizations.py`
exécute ces méthodes à O0/O2 en conservant clang C11, UBSan et
`-fno-sanitize-recover=all`. Passage final réussi : 21 méthodes à O0
(41,651 s) et 21 à O2 (41,396 s), journal
`/tmp/crust-owner-usage-optimizations-final.log`. À chaque niveau, les boucles
et sous-cas des deux modules exécutent 71 programmes natifs admis et vérifient
128 configurations refusées. Ces nombres désignent des programmes/configurations,
pas des règles distinctes ni une couverture exhaustive.

## Régression et migration des anciens tests

Première sélection : 180 méthodes (FoundationTests : noms contenant `handle`,
`consum`, `owned_field` ou `local_structure` ; AsyncRuntimeTests : noms
contenant `owned`), 151,487 s, huit échecs et deux erreurs. Journal :
`/tmp/crust-owner-usage-regression.log`.

Plusieurs fixtures comportaient des allocations volontairement inutilisées
ou vérifiaient un diagnostic différent avec une autre allocation inutilisée.
Elles ont été adaptées avec une lecture ou un emprunt explicite, sans affaiblir
le diagnostic ni les contrôles de réemploi. L'instance gardée jusqu'à la sortie
de `consume` est désormais explicitement empruntée avant le reset externe.

Une fixture async renomme un résultat propriétaire puis le transfère dans un
bloc enfant et le récupère. Cette réception plus récente change légitimement
l'ordre de destruction avec l'autre paramètre : le test vérifie maintenant
la trace exacte de ce programme modifié. Le test distinct de simple renommage
continue de vérifier la conservation de l'ordre sans ce transfert supplémentaire.
Un cas de boucle invalide lit désormais la nouvelle valeur avant `continue`
pour isoler le diagnostic de prêt actif, au lieu d'être aussi invalide selon U1.

Deux passages de 191 méthodes, incluant les onze méthodes de
`test_utf8_try_slice_async`, ont révélé les problèmes de continuation ci-dessus
et les deux dernières fixtures à adapter :
`/tmp/crust-owner-usage-regression-final.log` (158,144 s) et
`/tmp/crust-owner-usage-regression-paths.log` (162,170 s), chacun avec un échec
et une erreur async. Dans le second passage, les 154 méthodes synchrones sont
réussies avec l'analyse des réceptions en place. Les deux méthodes async
concernées passent ensuite en 10,836 s :
`/tmp/crust-owner-usage-async-final.log`.
La dernière relance des 37 méthodes async/UTF-8 réussit en 79,726 s :
`/tmp/crust-owner-usage-async-regression-final.log`. Elle inclut les corrections
finales de continuation et d'arguments. Les 154 méthodes synchrones avaient
réussi dans le passage précédent ; aucun code synchrone n'a changé depuis.
La compilation Python des modules modifiés et des trois modules de tests
réussit également (`python3 -m py_compile`).

## Mutations exécutées

Copies temporaires, tests et oracles inchangés :

| Mutation | Détection |
| --- | --- |
| Retrait du contrôle des réceptions ordinaires | Allocations et renommages inutilisés acceptés à tort |
| Retrait du contrôle d'usage propriétaire async | Réceptions await et transferts inutilisés acceptés |
| Retour à une simple recherche du dernier nom utilisé | Une autre réception ou un nom masqué justifie à tort l'abandon |
| Retrait du contrôle de la réaffectation async | Nouvelle allocation inutilisée acceptée |
| Oubli des arguments restant à évaluer | Programme valide utilisant l'argument suivant rejeté |

Les cinq mutations sont détectées. Journaux :
`/tmp/crust-owner-usage-mutations.log` et
`/tmp/crust-owner-usage-argument-mutation.log`.
Le dernier mutant est détecté par un faux refus, les autres par des faux accords.
Aucun taux de détection global n'est déduit de ces cinq fautes choisies.

## Limites

- Le modèle ne couvre que son petit alphabet ; il ne prouve pas la sûreté de
  l'analyse des usages ni l'ensemble des compositions possibles.
- Les tests de reset sont ceux du profil historique explicite. L'API publique
  reste retirée du prototype.
- Pas de nouvelle campagne ASan, TSan ou comparaison entre compilateurs C.
- L'audit complet des expressions imbriquées, des autres modes de réception,
  des fonctions par contrat et de toutes les jonctions reste à poursuivre.
  Les éléments propriétaires de tous les types de conteneurs ne sont pas
  déclarés couverts par ce cycle.
- Les paramètres de fonctions ne sont pas transformés en nouvelles liaisons
  de résultat ; leur convention consommatrice existante est conservée.
- Ce cycle ne termine ni l'ensemble du brouillon 01 ni les sept lots du but.
  La data stack complète, les type features et le dernier ensemble de règles
  runtime/scheduler/Select/mutex restent dans le périmètre à terminer.
