[English](SET_EXPRESSIONS_CYCLE.md)

# Expressions calculées dans Int.set

## Périmètre

V4 et B4a décrivent la mutation du contenu Int, sans remplacement de son
allocation, avec évaluation de la nouvelle valeur avant l'écriture. Ce lot
complète le raccordement synchrone de `nombre.set(expression)` pour les
expressions Int déjà prises en charge. La mention du littéral dans V4 décrit
le prototype initial ; aucune nouvelle conversion ou mutation de collection
n'est introduite. Les méthodes utilisateur nommées set restent résolues
selon leurs propres signatures.

Le résultat de l'expression est calculé une seule fois. La cible est ensuite
revérifiée : un nom ou une adresse C sauvegardés avant le calcul ne prouvent
pas que la valeur soit toujours vivante. Les écritures via référence readonly,
liaison immutable ou emprunt encore utilisé sont refusées. L'analyse des
effets, résultats et contraintes traverse également l'expression, y compris
les appels, retours anticipés et resets du profil historique.

Le parcours général des bras de match gère les écritures calculées sur leurs
projections. Le chemin historique des littéraux est conservé. Le backend async
possédait déjà des écritures calculées ; un appel async vers un auxiliaire
synchrone utilisant set est inclus dans les tests.

## Preuves ciblées

Les huit premières méthodes de `tests/test_set_expressions.py` passent à O2 (4,128 s,
`validation/set-expressions-complete-o2.log`) et O0 (3,884 s,
`validation/set-expressions-complete-o0.log`). Exécutions C11 avec Clang,
pthread, avertissements fatals et UBSan fatal.
Un neuvième test vérifie qu'un retour anticipé dans la nouvelle valeur saute
l'écriture et conserve le contenu précédent. La passe finale des neuf méthodes
réussit à O2 en 4,948 s (`…-final-o2.log`) et O0 en 4,938 s (`…-final-o0.log`).

Les programmes testent l'ordre gauche à droite de deux appels, l'identité
d'adresse avant/après écriture et après réemploi du slot, la destruction
unique avec la dernière valeur, les scalaires locaux, références mutables,
cases de tableaux, projections de match et méthodes utilisateur. Les voisins
invalides sont contrôlés par verify_program et compile_source : lecture
future d'un emprunt, écriture readonly, destruction/transfert/reset de la
cible pendant le calcul, mauvais type et mauvaise arité.

Un auxiliaire réalise un reset dans la nouvelle valeur ; deux relais conservent
cet effet chez l'appelant. Le programme est admis si les allocations affectées
ont fini d'être utilisées, et refusé si une lecture doit encore suivre.
Le reset demeure exclusivement historique et explicitement activé.

Le modèle indépendant utilise les entiers Python pour calculer trois suites
de douze mutations (graines 72, 190 et 602). Il compare les 36 observations
aux sorties natives sans lire les décisions du compilateur.

Trois fautes sont détectées dans des copies temporaires, journal
`validation/set-expressions-mutations-o2.log` : suppression du contrôle
d'écriture, suppression du calcul de la nouvelle valeur, omission des effets
du calcul dans le résumé. Cette dernière provoque un invariant interne
« reset absent du résumé de fonction » sur le programme valide ; elle ne
constitue pas une preuve qu'un programme dangereux ait été exécuté.

## Régression et limites

La régression élargie est consignée dans
`validation/set-expressions-regression-o2.log` : 150 méthodes, trois échecs
d'assertions et douze erreurs répartis dans six méthodes historiques.
Ces six méthodes reproduisent exactement ces échecs avec le compilateur
antérieur au lot (`validation/set-expressions-before-change-failures.log`).
Elles remplaçaient une allocation sans usage de son ancienne valeur ; U1
les arrêtait avant la propriété visée. Les programmes comportent désormais
une lecture contrôlée de cette valeur initiale. Les assertions originales
de sortie, destruction, ordre du C, dépassement et diagnostics sont conservées.
Le journal initial n'est pas effacé. Un premier script de sélection avait
dupliqué les noms de méthodes ; son erreur de chargement est conservée
séparément dans `…-before-change-loader-error.log`.
La deuxième passe de 150 méthodes (`…-regression-fixtures-fixed-o2.log`)
réussit sauf une attente de diagnostic : le test négatif du déplacement
n'utilisait pas non plus le nouveau receveur. Celui-ci est désormais lu avant
l'accès volontairement invalide au nom déplacé. L'assertion « plus utilisable »
est conservée. Les modules modifiés sont rejoués dans
`validation/set-expressions-reassignment-final-o2.log`.
Ces 41 méthodes passent en 13,910 s. Il n'y a pas de troisième exécution
globale des 150 méthodes après cette dernière correction de fixture ; les
149 autres méthodes avaient réussi dans la passe précédente.

Pas de nouvel ASan/TSan, second compilateur C, ni preuve formelle. Les tests
exercent des compositions finies ; ils ne prouvent pas toutes les interactions.
Les diffs sont conservés dans `validation/set-expressions-*.py.patch`.
Le lot d'écritures calculées est terminé pour ce périmètre testé.

L'extension des paramètres async de handles reste en attente de l'arbitrage
documenté dans ASYNC_HANDLE_CAPTURE_DECISION.md. Le reste de l'objectif global
reste actif, sans modification des règles AS14/RT6/RT7 avant réponse.
