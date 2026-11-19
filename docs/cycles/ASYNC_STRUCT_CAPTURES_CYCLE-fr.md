[English](ASYNC_STRUCT_CAPTURES_CYCLE.md)

# Cycle — références de structures dans les états async et natifs

Suite du [cycle des régions](ASYNC_REGIONS_CYCLE.md).
Aucune modification normative. Références : ST5/ST7/ST9, ME2/ME3, TF1–TF5,
B1/B2/B4/B4a, AS2/AS8–AS15, RT8 et MT1/MT2/MT3 ; brouillons 04/05/06.
L’objectif global et les autres obligations des sept brouillons restent ouverts.

## Implémentation et portée

Les captures `&Point` et `&mut Point` sont raccordées lorsque la structure
contient uniquement des champs Int, éventuellement imbriqués par valeur.
L’état garde un pointeur vers l’emplacement existant ; il ne copie ni ne
déplace la structure. Le layout aplati est fourni par le vérificateur principal.
Les lectures et écritures de champs conservent leurs offsets et leur type.
L’écriture exige la capacité mutable ; une structure n’est pas traitée
implicitement comme un Int par déréférencement ou `set`.

Les références nommées et leurs réemprunts se relaient entre tâches. Une tâche
peut survivre au bloc de sa liaison intermédiaire tout en gardant le prêt
de la structure racine. L’argument d’un appel réserve le porteur pendant la
préparation des suivants. La dernière utilisation libère les prêts locaux,
mais une capture encore active les conserve jusqu’à l’attente ou au drop
d’une tâche inactive.

Les helpers synchrones peuvent recevoir ces références et restituer directement
un paramètre emprunté. Leur bridge emploie la représentation Cell existante et
le vérificateur synchrone. Les méthodes nommées sont résolues statiquement depuis
le type du receveur ; leurs contrats restent ceux des fonctions sous-jacentes.
Le cas type feature Read → Item.read est ainsi exécutable sans dispatch runtime.

L’inférence des blocs natifs reconnaît les constructions de structures, leurs
champs et les signatures de leurs méthodes ; elle ne remplace pas la vérification
des accès. Aucun changement du runtime mémoire C.

## Contre-exemples et corrections

Le [cas direct historique](../../validation/open-async-struct-reference.crb) et le
[cas type feature](../../validation/open-feature-async-structure.crb) affichent 7.
Le [C généré](../../validation/async-struct-capture-basic.c) et une
[trace exécutée](../../validation/async-struct-capture-artifact.log) sont conservés.
Les anciens journaux de refus restent historiques.

Le premier passage ciblé comporte deux erreurs. La fixture de structure
imbriquée utilisait un littéral enfant que le constructeur actuel ne prend
pas en charge. Elle utilise désormais les défauts établis puis des écritures
de champs avant la capture ; les valeurs et offsets attendus sont inchangés.
Le second échec révèle l’absence d’inférence du type d’un emprunt de structure
dans un bloc natif. Cette inférence a été raccordée, ainsi que celle des champs.

Les variantes refusées couvrent les accès du parent avant lancement et pendant
l’exécution, deux captures exclusives, une écriture pendant un prêt partagé,
une fuite hors du scope de la cible, les types nominaux incompatibles, les
mutations en lecture seule et les arguments préparés qui se recouvrent.

La réutilisation d’un slot Point après drop conserve l’identité attendue.
Les traces imposent une destruction unique de chaque structure, y compris
après un échec de lancement injecté. La tâche qui emprunte la structure ne
la détruit pas ; l’appelant retrouve son accès après attente. Un réemprunt
partagé provenant d’une référence mutable conserve la suspension de cette
référence jusqu’à l’attente, ou jusqu’au drop de l’enfant encore inactif.

## Preuves exécutées

Clang C11 pthread, warnings bloquants, UBSan fatal, O0/O2. Aucun nouveau
résultat ASan/TSan, second compilateur ou preuve formelle.

| Passage | Résultat | Journal |
| --- | --- | --- |
| Initial O0 | Dix méthodes, 2,945 s, deux erreurs examinées | [Initial](../../validation/async-struct-captures-initial-o0.log) |
| Étendu O0 | Dix méthodes, 4,006 s, OK | [Étendu](../../validation/async-struct-captures-extended-o0.log) |
| Ciblé O0 | Treize méthodes, 4,435 s, OK | [O0](../../validation/async-struct-captures-final-o0.log) |
| Complément destruction O0 | Deux méthodes, 1,750 s, OK | [Nettoyage](../../validation/async-struct-captures-cleanup-o0.log) |
| Ciblé O2 avant le dernier réemprunt partagé | Treize méthodes, 8,087 s, OK ; 13 exécutions C et 27 refus | [O2 intermédiaire](../../validation/async-struct-captures-final-o2.log) |
| Complément réemprunt partagé O0 | Une méthode, 0,678 s, OK | [Réemprunt](../../validation/async-struct-captures-shared-reborrow-o0.log) |
| Ciblé final O2 | Quatorze méthodes, 5,952 s, OK ; 15 exécutions C, dont un lancement refusé injecté, et 29 refus statiques | [Final](../../validation/async-struct-captures-complete-o2.log) |
| Modèle O0/O2 | 16 combinaisons, 11 exécutions et cinq refus ; 8,651 s / 8,607 s, OK | [O0](../../validation/async-struct-captures-model-o0.log), [O2](../../validation/async-struct-captures-model-o2.log) |
| Mutations O2 | Baseline 13 méthodes/6,776 s, OK ; six fautes détectées, avant les assertions de destruction supplémentaires | [Mutations](../../validation/async-struct-captures-mutations-o2.log) |
| Features et références O2 | 76 méthodes, 62,071 s, OK | [Contrats](../../validation/async-struct-captures-contracts-o2.log) |
| Régression native O2 | 231 méthodes, 180,102 s, OK ; avant les assertions de destruction supplémentaires et le dernier test de réemprunt partagé | [Régression](../../validation/async-struct-captures-native-o2.log) |

Le modèle indépendant énumère un prêt partagé/exclusif, avant/après attente,
et une action vide/lecture/écriture/drop. Il décide l’admission par sa table
de droits, puis vérifie les valeurs des programmes admis. Il ne consulte ni
les contrats inférés ni les états du compilateur. Ce modèle fini ne couvre
pas les dépendances de champs références.

Les six mutations suppriment ou corrompent l’offset d’un champ, son écriture,
le contrôle mutable, le contrôle du prêt à l’écriture, le prêt racine d’un
enfant et le refus d’assimiler une structure à un Int. Les tests inchangés
détectent chaque faute ; aucun taux général n’est extrapolé.

Diffs conservés : [lowering](../../validation/async-struct-capture-async_lowering.patch),
[vérificateur et bridges](../../validation/async-struct-capture-crust.patch),
[inférence native](../../validation/async-struct-capture-native_threads.patch).

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_struct_captures test_async_struct_capture_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_struct_capture_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_struct_capture_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_type_features test_type_features test_builtin_features test_async_local_references test_async_match_references test_async_loop_references -v
```

## Écarts restants

Les structures contenant des références ou des champs propriétaires, leur
capture par valeur/transfert, leur construction dans un état et les projections
empruntées de leurs champs restent à généraliser. Le lot ne revendique donc pas
la couverture de ST6/ST8/ST10–ST15 en async. Les signatures générales, Select,
le scheduler public et les gardes restent également ouverts.

Le prochain cas est conservé : une tâche lit le champ `&Int` d’un View emprunté,
la cible et son pool étant durables chez l’appelant. Il reste refusé par le
lowering : [programme](../../validation/open-async-struct-reference-field.crb),
[diagnostic](../../validation/open-async-struct-reference-field.log). Aucune nouvelle
règle n’est nécessaire pour ce cas ; il exige le raccordement des dépendances
internes déjà prévues par la spécification.

Ce refus est désormais historique : voir le
[cycle des champs références](ASYNC_STRUCT_REFERENCE_FIELDS_CYCLE.md) pour
son raccordement, les défauts trouvés et les limites qui subsistent.
