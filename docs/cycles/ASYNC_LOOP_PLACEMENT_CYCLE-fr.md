[English](ASYNC_LOOP_PLACEMENT_CYCLE.md)

# Provenances des structures locales après les boucles async

## Règles et changement

Ce lot applique T3/T5/T6, V4/V5, L1/L2/L7, B1/B2 et AS9/AS12,
ainsi que les brouillons 03 et 05. Aucune règle normative n'est modifiée.

Le programme conservé dans
`validation/open-async-local-loop-updated-parent-result.crust` est désormais
accepté et exécuté : il affiche 1, 2, puis 3. Son ancien refus était une limite
d'implémentation, pas une interdiction du langage.

`async_local_placement.py` calcule désormais un point fixe des producteurs
possibles aux entrées de boucle. Les états des reprises normales et des
`continue` alimentent la prochaine itération ; les `break` et le test de
`while` alimentent les sorties. Le test conserve notamment le chemin sans
itération. Les boucles imbriquées ont leurs propres sorties et reprises.
Les scopes intermédiaires propagent les affectations et les sorties.

Les producteurs sont des identités de constructions dans l'AST : leur union
est finie. Une provenance inconnue reste inconnue, distincte d'un ensemble
vide. Le calcul utilise les contrats des fonctions, sans réanalyser leurs
corps. Il s'applique aussi aux boucles à résultat et au plan des affectations
vers des receveurs existants.

Ce plan réserve le stockage parent avant la construction, sans déplacer les
objets après initialisation. Les champs propriétaires conservent leurs propres
pools ; aucune cible empruntée n'est promue. Le vérificateur habituel contrôle
encore les types, les transferts et les prêts. Le code du runtime est inchangé.

## Preuves exécutées

`tests/test_async_loop_placement.py` contient sept méthodes :

- Le cas enregistré avec zéro, une, deux et cinq itérations.
- Des sorties par `break` après des `continue`, avec `while` et `loop`.
- Des boucles et scopes imbriqués.
- Une lecture empruntée avant remplacement admise, puis son déplacement après
  remplacement refusé ; une affectation depuis une variable sans move refusée.
- Une structure avec champ propriétaire dont le pool est durable admise ; la
  même source dans le bloc enfant refusée.
- Une sonde du C généré : toutes les versions occupent la source parent,
  la nouvelle cellule diffère de l'ancienne encore vivante pendant sa
  construction, le dernier objet garde son adresse après sortie du bloc,
  puis son stockage est nettoyé. Quatre destructions sont attendues.
- Un modèle de propagation sur trois producteurs : une chaîne de relais
  nécessite plusieurs passages et doit retrouver les trois origines. Une
  origine inconnue doit empêcher de conclure à un ensemble connu. Ce modèle
  teste l'analyse de placement, pas la validité syntaxique d'un programme Crust.

Le passage final O0 réussit en 5,211 s ; la baseline finale O2 réussit en
6,803 s. Les tests comportent dix exécutions C, dont la sonde, et trois
programmes invalides contrôlés par les deux étapes. Les compilations utilisent
Clang C11, pthread, Wall/Wextra/Werror, Wno-unused-function et UBSan fatal.
Les niveaux d'optimisation sont explicitement définis par `CRUST_TEST_OPT`.
Journaux : `validation/async-loop-placement-final-o0.log` et
`validation/async-loop-placement-mutations-final-o2.log`.

La suite précédente de placement parent passe ses quatorze tests à O0,
puis à O2 dans la campagne de mutations précédente. Les treize tests des
appels synchrones propriétaires passent séparément à O2 en 13,778 s.
La sélection élargie exécute 95 tests avec succès en 123,130 s, mais sa
commande échoue pour une erreur supplémentaire de chargement de module
(96 entrées au total), détaillée ci-dessous. Avec les treize tests exécutés
séparément, 108 tests de régression distincts ont réussi sur le code final.
Le journal initial n'est pas présenté comme une commande réussie :
`validation/async-loop-placement-regression-o2.log`. La suite corrigée est
dans `validation/async-loop-placement-sync-regression-o2.log`.
Tous les processus cités sont terminés et leurs résultats ont été récupérés.

## Mutations et essais initiaux

Les cinq fautes de `tests/run_async_loop_placement_mutations.py` sont détectées :
un seul passage, oubli des reprises continue, oubli des sorties break, oubli
du chemin sans itération, et élimination abusive des provenances inconnues.
Les oracles ne sont pas modifiés avec le code testé. Certaines détections sont
des refus de programmes valides, d'autres des différences du modèle statique ;
elles ne sont pas présentées comme des corruptions mémoire exécutées.

Les huit mutations précédentes sont également détectées dans
`validation/async-loop-placement-previous-mutations-o2.log` ; leur baseline de
quatorze tests passe en 16,975 s. Les tests continuent notamment de détecter
l'oubli des pools des champs et de la fermeture des stacks.

Les essais non concluants restent archivés :

- `parent-o0.log` : option de compilation mal écrite (`0` au lieu de `-O0`),
  corrigée dans `parent-corrected-o0.log` ; aucun résultat de sûreté n'en est déduit.
- `initial-o0.log` : fixture employant le mot réservé `pool` comme variable,
  et attente de refus incorrecte pour un appel constructeur frais sans flèche.
  Le voisin invalide final déplace une variable existante sans flèche.
- `corrected-o0.log` : fixture réutilisant le nom `n` dans un scope où le
  prototype interdit son masquage ; le second nom est corrigé en `next`.
- `mutations-o2.log` : la première mutation de provenance inconnue déclenchait
  une exception Python ; résultat classé inconclusif. La mutation finale
  retire les inconnues de l'union et est détectée par une assertion du modèle.
- La première commande de régression contient un nom de module inexistant,
  `test_async_sync_owned_calls`. La suite réelle `test_sync_owned_calls` est
  exécutée séparément ; l'erreur d'import initiale reste dans le journal.

`py_compile` réussit. Le diff du module est conservé dans
`validation/async-loop-placement-async_local_placement.py.patch`, avec snapshot
initial dans `/tmp/crust-before-async-loop-placement/`.

## Limites et suite

Ce lot ne généralise pas les graphes de types des états async. Le passage de
structures locales aux tâches enfants, leur sortie hors de l'état et la
restitution après remplacement d'un champ propriétaire restent ouverts.
Le point fixe réunit conservativement les chemins ; il ne déduit pas leurs
corrélations et ne recherche pas un placement mémoire optimal.

Le modèle et les sondes sont finis. Les tests exécutés ne prouvent pas la sûreté
générale. Aucun résultat ASan ou TSan nouveau n'est revendiqué. L'objectif
complet d'intégration des sept brouillons reste ouvert.
