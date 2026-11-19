[English](REFERENCE_EXPRESSIONS_CYCLE.md)

# Cycle — emprunts produits par if et match

## Règles et changement

Ce cycle applique B1/B2/B3, B4a, B5 et D1 sans modifier les règles normatives.
AGENTS.md, VALIDATION_GUIDELINES.md, l’index des sept brouillons et les clauses
sur les emprunts et les frontières de scopes ont été relus. Les spécifications
normatives déjà intégrées continuent de distinguer emprunt et transfert : un
résultat emprunté n’exige pas de flèche et ne promeut pas sa cible.

Le cas `validation/open-join-element-match-expression.crust`, refusé au cycle
précédent, est maintenant exécuté. Le résultat de `join` peut fournir une case
dans le bras Ok et un emprunt de secours dans Err ; la fonction synchrone peut
retourner le résultat de ce match expression. Les deux chemins affichent 255,
y compris avec EAGAIN injecté au lancement bloquant. Le log antérieur reste
une trace historique du défaut.

L’analyse des résultats accepte les modes d’emprunt et réunit leurs provenances
sans perdre l’indication d’un pointeur vers une case inline. La traduction des
expressions conditionnelles conserve séparément les cibles, les chemins de
stockage et les parents d’emprunt. Chaque branche doit fournir le même type
et le même mode. Les branches qui retournent directement de la fonction ne
fournissent pas de résultat à la continuation.

Un Int alloué en pool est représenté par un Cell*, tandis qu’une case de tableau
ou de vecteur utilise un int*. Si une sélection mélange ces représentations,
le C reçoit un pointeur vers la valeur de chaque branche. Les références
ordinaires vers des structures conservent leur représentation existante. Les
vérifications enfant → parent s’exécutent avant le nettoyage du bras ; elles
refusent les cibles locales sans promotion implicite. Le runtime n’est pas modifié.

## Scénarios et oracles

`tests/test_reference_expressions.py` comporte quatorze méthodes : trente
exécutions natives normales et 63 vérifications de refus par passage. Il ne
s’agit pas de programmes tous distincts : certains paramètres et variantes
répètent un même invariant.

- Sélection partagée ou mutable entre deux Int de pool ; deux branches
  exécutées, anciennes valeurs observées, écritures dirigées vers la bonne cible.
- Mélange case de tableau / Int de pool, dans les deux ordres de bras et
  avec les deux décisions ; les autres valeurs restent intactes.
- Nouvelles cases Int/u8 provenant de deux pools, dernier usage, drop et
  réemploi après usage ; destruction prématurée de chaque source refusée.
- Join puis retour par contrat, sur succès et refus de lancement ; un
  marqueur de branche et les longueurs montrent qu’un seul bras s’exécute.
- Liaisons locales, réemprunts, boucles avec continue et break, et
  sous-expressions conditionnelles avec retour anticipé.
- Références de structures, et projection mutable d’un enum à travers if :
  le porteur reste réservé jusqu’au dernier usage, puis redevient accessible.
- Condition avec effet observable : un seul appel, avant le bras choisi.
- Modèle indépendant de sélection parmi trois valeurs, graine 1771,
  cinq tirages ; cible choisie et toutes les valeurs finales comparées.
  Chacune des trois sources possibles reste protégée contre drop avant usage.
- Refus des cibles de pool/tableau/vecteur locales à un bras, des modes ou
  types incompatibles et des accès qui violent un emprunt encore utilisé.
- Reset public refusé. Deux vérifications supplémentaires dans le profil
  historique `allow_legacy_reset=True` conservent le refus de reset précoce ;
  elles ne réintroduisent pas cette API dans le prototype courant.

Les attentes sont calculées depuis les valeurs du programme, les identités
logiques et la sélection du modèle, indépendamment des contrats et du C émis.
Le modèle reste fini et ne prouve pas toutes les combinaisons de chemins.

## Défauts et préparation des tests

Le refus initial existait dans l’analyse des résultats puis dans la sélection
C : les deux n’admettaient que les copies et les propriétaires. Leur extension
conserve les provenances et les contrôles de durée de vie existants. Le contrôle
de sortie de bloc pour les emprunts de cases s’applique désormais aussi aux
bras if et aux matchs builtin, avant destruction de leurs locaux.

Les premiers scénarios utilisaient un paramètre Bool synchrone, encore refusé
par le prototype, ainsi qu’un argument calculé de `.set()` dans une fonction
synchrone, également refusé. Les tests du présent cycle emploient des sélecteurs
Int comparés à 1 et `*n = *n + 1`, sans changer leurs attentes de sélection ou
d’ordre. Les deux limitations initiales ne sont pas corrigées par ce lot ; les
logs initiaux restent disponibles. Les refus de programmes invalides du premier
passage ne sont pas comptés comme preuve de leurs invariants puisque Bool
empêchait alors d’atteindre ces vérifications.

## Exécutions et régression historique

- `validation/reference-expressions-O0.log` : 14 méthodes, 26,128 s, OK ;
  tests natifs du nouveau module sous Clang C11, `-O0`, UBSan fatal.
- `validation/reference-expressions-async.log` : 29 méthodes voisines, 59,656 s,
  OK (push_new async et valeurs d’erreur builtin).
- `validation/reference-expressions-legacy-UBSan.log` : 13 méthodes d’emprunts
  de porteurs, 4,565 s, OK avec `CRUST_SANITIZE=undefined`.
- Première régression : `validation/reference-expressions-O2-regression.log`,
  158 méthodes, 166,441 s, 18 erreurs dans trois méthodes historiques.
  Le helper historique n’utilise pas `CRUST_TEST_OPT` : ce passage n’était pas
  intégralement sous O2 ni UBSan. Les tests du nouveau module l’étaient.

Les erreurs historiques étaient les liaisons propriétaires `outer`, `temp`,
`old` et la première valeur de `data`, sans lecture, emprunt ni consommation
explicite avant nettoyage. Cela contrevient à U1 renforcée par le brouillon 01.
Une copie temporaire du compilateur **avant** ce cycle, avec ses anciens
`crust.py` et `results.py`, reproduit les 18 erreurs des trois méthodes en
0,061 s : `validation/reference-expressions-baseline-legacy.log`.

Les fixtures ont reçu des `print` avant la sortie, le reset ou le remplacement ;
les sorties attendues contiennent ces lectures. Les attentes d’ordre et de
nombre de destructions n’ont pas changé. La règle U1 reste inchangée et le test
de rejet d’un receveur sans usage est conservé. Le module corrigé exécute
24 méthodes en 40,275 s, OK sous UBSan historique :
`validation/reference-expressions-legacy-updated.log`.

La régression finale `validation/reference-expressions-regression-final.log`
exécute les mêmes huit modules : 158 méthodes, 188,023 s, OK. Commande :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_reference_expressions test_if_expressions test_conditionals test_conditional_returns test_direct_borrow_returns test_mutable_borrow_returns test_mutable_match_escape test_mutable_match_function_return -v
```

UBSan est actif pour les deux helpers dans ce passage. Le nouveau helper utilise
O2 ; le helper synchrone historique garde l’optimisation par défaut du compilateur C.
Les 18 erreurs initiales ne sont donc pas cachées par un changement de règle ou
par l’exclusion des méthodes de la régression.

## Mutations

Les copies temporaires du compilateur reçoivent quatre fautes contrôlées :

| Mutation | Observation |
| --- | --- |
| Condition inversée | Mauvaise cible/valeur observée, détectée par le test natif |
| Une provenance de case supprimée | Mutation interdite de b acceptée, assertion de refus en échec |
| Pointeur nul pour une branche pool/tableau | Exécution native refusée par UBSan, assertion de succès en échec |
| Ascendance du porteur effacée | Programme valide refusé par l’invariant interne d’exclusivité du compilateur |

Le quatrième cas était initialement classé inconclusif par le script, qui
reconnaissait seulement les lignes FAIL de unittest. L’inspection a établi que
le test positif échouait par `crust.Error: invariant interne : emprunt mutable
non exclusif`, à cause de la mutation. Le script reconnaît désormais ce résultat
précis pour cette mutation et une nouvelle exécution ciblée le reproduit.
Les deux traces sont conservées : `validation/reference-expressions-mutations.log`
et `validation/reference-expressions-writer-mutation.log`. Cette dernière est
une détection par garde interne, pas la preuve que l’oracle de sortie aurait
repéré à lui seul une ascendance manquante.

## Limites et suite

La même forme dans le corps suspendable reste ouverte :
`validation/open-async-reference-if-expression.crust` reçoit deux emprunts
mutables durables mais refuse encore `return if ...`. La sortie attendue est
30 puis 20 ; son diagnostic est enregistré. Ce refus ne correspond pas à une
règle normative. Le présent lot étend les expressions du compilateur synchrone,
y compris les appels et résultats de tâches qu’il gère ; il n’étend pas encore
le lowering des retours conditionnels d’emprunts dans un cadre async.

ASan n’a pas été relancé : le cycle précédent a reproduit un délai de démarrage
même pour un exécutable C vide sous ASan. Aucun succès ASan, TSan, second
compilateur ni preuve formelle n’est revendiqué. Les corrélations générales
entre destruction conditionnelle et sélection d’un emprunt restent hors des
scénarios exécutés. Les autres obligations ouvertes des sept brouillons,
notamment scheduler, threads, Select, mutex et stockage implicite, demeurent.

## Suivi

Le cycle [ASYNC_REFERENCE_RETURNS_CYCLE.md](ASYNC_REFERENCE_RETURNS_CYCLE.md)
corrige depuis le retour conditionnel async cité ci-dessus. La liaison locale
d’un tel résultat reste un contre-exemple distinct, reproduit dans ce rapport.
