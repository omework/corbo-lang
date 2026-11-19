[English](ASYNC_ENUM_MATCH_CYCLE.md)

# Match d'enums par emprunt dans un état async

## Règles et périmètre

Ce lot applique P9, B1–B5, D1, ST13, les règles de projection et de retour de match,
AS8–AS15 et SL1. Aucune nouvelle sémantique normative n'est ajoutée. Le sujet
reste réservé pendant tout le bras, même après le dernier usage d'une
projection. Une référence qui sort du bras conserve ses cibles et les
capacités nécessaires ; un Int copié n'emporte pas ces emprunts.

`validation/open-async-enum-match.crust` était refusé aux deux entrées du
compilateur, alors que son pendant synchrone était accepté. Il s'exécute
maintenant. Le backend émet les branches selon les discriminants du pool,
conserve les projections nécessaires dans l'état stable et utilise les
nettoyages existants pour suspension, retour, break et continue.

Les matchs partagés et mutables sont raccordés en instruction et en expression,
avec bras multiples, résultats scalaires, références Int et allocations
construites dans les bras. Un champ A<Int> peut être lu par projection sans
transfert du descendant. Les noms des projections restent locaux aux bras.
Un alias nommé du porteur peut traverser une suspension avant le match.

## Corrections et invariants

- Les branches async gèrent maintenant plus de deux alternatives. Elles
  fusionnent les obligations des chemins continuants ; les chemins terminaux
  n'apportent pas de valeur au receveur.
- Une réservation du sujet dure jusqu'à la sortie du bras. Elle est retirée
  par les sorties ordinaires ou anticipées, sans raccourcir la durée des prêts
  qui sortent du bras ou sont capturés par une tâche enfant.
- Les contrats de résultats reconnaissent les chemins `Variant.field` et
  leurs cibles. Les champs &Int peuvent rendre leur cible indépendamment du
  porteur ; les champs &mut Int conservent la réservation de sa capacité.
- Le suivi des réservations distingue le chemin `.field` d'une structure et
  `Variant.field` d'un enum. L'ancienne interprétation produisait un invariant
  interne d'exclusivité au lieu de traiter correctement un retour mutable.
- Un résultat partagé créé depuis un parent mutable conserve aussi ce parent
  exclusif jusqu'au dernier usage. Le test oppose une mutation avant et après
  l'utilisation du résultat.
- Les enums à champs directs ont un contrat de suspension utilisable par
  Select. Une perdante conserve son porteur et ses cibles jusqu'au drop de
  Select ; son écriture effectuée avant yield reste observable.

La revue des effets a identifié une limite distincte : les modifications d'un
descendant possédé d'un enum ne disposent pas encore d'une représentation
complète aux suspensions. Le résumé de terminaison peut être complet, mais
le résumé de suspension doit rester explicitement incomplet lorsque le graphe
suivi change. Un test inspecte ce statut sans classer le programme comme
invalide selon le langage. Cette limite reste un travail d'implémentation.

## Validation ciblée exécutée

La suite `tests/test_async_enum_match.py` passe 17 méthodes à O0 en 16,579 s :
20 exécutions natives, 16 programmes invalides et 32 contrôles de refus.
Journal : `validation/async-enum-match-complete-count-o0.log`.
Verify_program et compile_source partagent des analyses ; les deux refus ne
sont pas deux preuves indépendantes.

Les programmes admis couvrent trois variantes dans un ordre différent de la
déclaration, les suspensions dans les bras, les appels et réemprunts, le résultat
mutable retourné chez l'appelant, le résultat partagé après destruction du
porteur, les alias, les résultats Bool et les matchs imbriqués. S'ajoutent les
retours anticipés, break et continue, une tâche enfant capturant une projection,
l'échec du lancement du parent, le réemploi des pools et le nettoyage d'une
perdante de Select.

Les programmes invalides couvrent l'exhaustivité, les champs et variantes
incorrects, l'accès au porteur pendant le bras, l'accès à la projection pendant
un réemprunt encore utilisé, les drop prématurés et les résultats vers des cibles
locales. Le résultat mutable protège le porteur chez l'appelant avant son
dernier usage et le libère ensuite.

Le petit oracle des variantes associe chaque constructeur et ses valeurs à
son résultat source, indépendamment des tags du backend : trois constructions
avec ordre de bras différent et yield, suivies d'un réemploi du slot. Les
traces exigent une destruction unique du sujet. Il s'agit d'une exploration
finie, pas d'un modèle de tout le système de types ou de toutes les traces.

## Mutations

La campagne finale passe son baseline de 17 méthodes à O2 en 16,855 s et
détecte six fautes par assertions : mauvais tag, réservation du match relâchée
trop tôt, mauvais chemin de capacité mutable, perte de la projection d'une
capture partagée, lecture à la place du réemprunt mutable, et publication d'un
contrat de suspension incomplet comme complet. Journal :
`validation/async-enum-match-complete-mutations-o2.log`, processus terminé
avec code 0. Les échecs des compilateurs mutés sont attendus.

Les campagnes intermédiaires de cinq puis six mutations sont conservées dans
`async-enum-match-mutations-o2.log` et `async-enum-match-final-mutations-o2.log`.
Aucune extrapolation du taux de détection à l'ensemble du compilateur n'est faite.

## Régressions et anomalie historique

La régression synchrone passe 125 méthodes à O2 en 84,630 s, code 0 :
`validation/async-enum-match-sync-regression-o2.log`. Elle comprend les matchs
mutables, appels, retours, sorties de projection, champs partagés/mutables,
retours directs d'emprunts et résultats propriétaires.

La première régression async exécute 170 méthodes en 174,516 s et rencontre
un échec : `test_deferred_writes_cannot_disappear_inside_sync_handle_helper`.
Cet échec est également reproduit sur le snapshot antérieur à ce lot. Le
contrat d'attente avait déjà été raccordé dans les travaux précédents ; le
test attendait encore un résumé incomplet. Le programme reste refusé parce
qu'il masque une attente synchrone depuis async. Le test conserve ce refus
et exige maintenant exactement les origines du champ : ancienne cible si
le lancement échoue, nouvelle cible si l'enfant s'exécute. La preuve du
comportement antérieur est dans `async-enum-match-existing-effect-test.log`.
Les attentes ne sont pas modifiées pour masquer une perte d'effet.

La régression async finale passe 173 méthodes à O2 en 164,353 s, avec code 0 :
`validation/async-enum-match-final-async-regression-o2.log`. Elle couvre les
enums capturés, matchs de résultats builtin, effets différés, pools et résultats
de structures, Select, handles publics et graphes locaux retournés.
Tous les processus finaux sont terminés. Le lot est clos pour ce périmètre,
sans clôturer le chantier global ni les compositions explicitement ouvertes.

Les exécutables utilisent clang C11, pthread, O0/O2, avertissements comme
erreurs et UBSan fatal. Aucun résultat nouveau ASan/TSan ni preuve formelle
n'est revendiqué.

## Échecs intermédiaires et limites

Le snapshot initial échoue sur 16 assertions des neuf premières méthodes
en 0,123 s (`async-enum-match-baseline.log`). Les journaux `first-o0` à
`fifth-o0` conservent les défauts de classification des captures, contrats de
champs, notation interne `match_yield`, portée Python de `replace` et chemin
de réservation mutable. `sixth-o0` conserve aussi deux erreurs de préparation
des tests : affichage Bool non raccordé en synchrone et lecture d'une allocation
Int async sans déréférencement. Les oracles utilisent maintenant une condition
Bool explicite et `*next`. Les douze méthodes passent dans `seventh-o0`.
Les ajouts suivants couvrent les enfants, échecs de lancement, alias et parent
exclusif ; leurs journaux ciblés restent disponibles.

À la clôture de ce lot, le match consommant n'était pas encore raccordé en async.
Il est désormais traité par [le lot suivant](ASYNC_CONSUMING_ENUM_MATCH_CYCLE.md).
Le cas minimal
`validation/open-async-consuming-enum-match.crust` est refusé aux deux entrées,
alors que son pendant synchrone est accepté ; diagnostics dans le fichier
`.log` correspondant. Ce refus n'est pas une nouvelle règle du langage.
Les écritures de références dans les descendants sont désormais traitées dans
[le lot de suspension](ASYNC_ENUM_SUSPENSION_FIELDS_CYCLE.md). Les remplacements
du stockage possédé et les compositions générales de résultats restent à compléter.
Ce lot ne prouve pas toutes les combinaisons
de fonctions, pools, captures, Select, récursion ou types agrégés.

Le chantier global reste actif : match consommant, compositions async restantes,
gardes de mutex et audit des sept brouillons. Le type et les signatures publiques
du scheduler restent explicitement à arbitrer, conformément à la décision utilisateur.

## Reproduction et archives

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_enum_match -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 tests/run_async_enum_match_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_enum_match test_async_owned_enums test_async_match_references test_async_structure_effects test_async_borrowed_struct_pools test_async_borrowed_local_results test_select_source test_select_results test_async_owned_struct_returns test_public_structure_handles test_async_local_owned_result_graphs -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_mutable_match test_mutable_match_calls test_mutable_match_function_return test_mutable_match_escape test_reference_fields test_mutable_reference_fields test_direct_borrow_returns test_owned_results -v
```

Les cinq diffs d'implémentation sont archivés dans
`validation/async-enum-match-*.py.patch`, depuis
`/tmp/crust-before-async-enum-match/`. Les nouveaux tests, le test historique
actualisé, les programmes minimaux et les journaux accompagnent le rapport.
