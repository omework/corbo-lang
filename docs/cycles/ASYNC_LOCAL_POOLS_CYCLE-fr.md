[English](ASYNC_LOCAL_POOLS_CYCLE.md)

# Cycle — pools locaux dans les états async et natifs

Suite du [cycle des collections](ASYNC_COLLECTION_CREATION_CYCLE.md).
Aucune modification normative. Références : brouillons 03/04/05,
A1–A4/A6, S4/S5, B1/B4/B4a/B4c, T6/T9/T11, L1/L2/L6, V4/V5,
AS2/AS8–AS14, RT6/RT7/RT8 et MT7.

**Statut : implémentation et validation du périmètre exécutées. Le module
async_runtime a terminé avec deux divergences de diagnostics, examinées et
réexécutées séparément ci-dessous ; son journal initial reste en échec.**
L’objectif global et les autres obligations des sept brouillons restent ouverts.

## Implémentation

Un corps async ou natif peut déclarer un pool local Int, String,
Vector<Int> ou Vector<u8>. Le descripteur Source et, pour les collections,
le VectorStorage sont des membres de l’état stable. Le constructeur s’exécute
au passage de la déclaration, pas à la création de la tâche inactive.
Les mappings utilisent les constructeurs de pools existants du runtime.
Une reprise conserve leur adresse ; une nouvelle itération reconstruit le
pool après fermeture de la précédente.

La source locale est suivie indépendamment de l’emprunt qui permet d’y
allouer. Les allocations, retours de helpers, transferts, tâches enfants,
résultats await/join et jonctions de branches conservent leurs origines.
Un enfant propriétaire d’une allocation conserve la durée de vie du pool
sans emprunter exclusivement ce pool. Recevoir le pool en &mut le réserve
en revanche jusqu’à la fin de l’enfant.

Les sorties vérifient que chaque allocation transférée conserve un pool
durable. Les sources possibles des receveurs sont réunies aux jonctions ;
un remplacement ultérieur met à jour la provenance courante. La fermeture
refuse un receveur extérieur ou une tâche encore dépendante. Le nettoyage
des allocations et enfants inactifs précède source_close. Les handles lancés
gardent leur obligation d’attente existante. Les sources ne sont pas déplacées.

## Contre-exemples

Le [cas historique](../../validation/open-native-async-local-pool.crb), qui crée
une allocation dans le pool local d’une tâche puis la transfère à un thread
natif, s’exécute désormais et affiche 7. Son [C généré](../../validation/async-local-pool-basic.c)
et sa [trace](../../validation/async-local-pool-artifact.log) sont conservés.

Les variantes refusées font sortir une allocation par return, helper,
await, résultat de join, bloc ou break alors que son pool se ferme. Une
affectation à un receveur extérieur est également refusée si elle conserve
la source trop courte à la sortie ; remplacer ensuite par une allocation
du pool extérieur est admis. Les deux sources d’un résultat conditionnel
restent protégées.

Les trois erreurs du premier passage ciblé venaient de fixtures utilisant
`print(a)` dans un corps async là où la lecture d’Int détenu est explicitement
`*a`. Elles sont corrigées sans modifier les résultats ou destructions attendus.
Le journal initial reste en échec. La première campagne de mutations s’est
arrêtée sur une ancre non unique : `loans.extend` apparaissait aussi dans
`returned_loans.extend`. L’ancre a été précisée et la campagne relancée dans
de nouvelles copies temporaires.

## Preuves exécutées

Clang C11 pthread, O0/O2, warnings bloquants, UBSan fatal. Aucun nouvel
essai ASan/TSan, second compilateur ou preuve formelle.

| Passage | Résultat | Journal |
| --- | --- | --- |
| Prérégression pools injectés + collections O0 | 33 méthodes, 23,977 s, OK | [Prérégression](../../validation/async-local-pool-preregression-o0.log) |
| Ciblé initial | 11 méthodes, trois erreurs de fixture | [Initial](../../validation/async-local-pool-initial-o0.log) |
| Ciblé O0 | 17 méthodes, 7,375 s, OK, avant le dernier cas concurrent | [O0](../../validation/async-local-pool-final-o0.log) |
| Baseline finale O2 | 18 méthodes, 13,767 s, OK ; 21 exécutions normales, un épuisement contrôlé, 20 refus | [Baseline et mutations](../../validation/async-local-pool-final-mutations-o2.log) |
| Modèle d’ascendance O0 | Neuf programmes exécutés, trois refus ; le chargement a aussi rejoué les 18 méthodes importées, 19 méthodes/18,901 s, OK | [Modèle O0](../../validation/async-local-pool-model-o0.log) |
| Modèle d’ascendance O2 | Une méthode, neuf exécutions et trois refus, 5,312 s, OK ; import corrigé pour éviter la redécouverte | [Modèle O2](../../validation/async-local-pool-model-o2.log) |
| Native/runtime O2 | 195 méthodes, 175,346 s, OK, dont les 18 ciblées finales | [Régression native](../../validation/async-local-pool-native-o2.log) |
| Module async_runtime complet O2 | 275 méthodes, 412,076 s ; 273 réussites, deux assertions de diagnostics en échec | [Régression async](../../validation/async-local-pool-runtime-o2.log) |

Le modèle calcule l’admission par comparaison des profondeurs lexicales du
pool et du receveur, indépendamment du vérificateur. Une copie d’Int est
indépendante ; une allocation exige un pool au moins aussi durable. Les
autres oracles imposent les valeurs, l’ordre et le nombre de destructions.
Un oracle C compte quatre ouvertures et quatre fermetures de pools à travers
trois itérations et le scope final. Il détecte une fuite de mapping que la
seule trace de destruction ne révélerait pas.

Six fautes injectées sont détectées : origine oubliée à la création, contrôle
de frontière omis, fermeture de mapping omise, dépendance d’un enfant oubliée,
origine perdue après await et origine d’une branche oubliée. Les assertions
restent inchangées dans les copies mutées. Aucun taux général n’en est déduit.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_local_pools -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_local_pool_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_local_pool_model -v
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_runtime -v
```

## Limites et suite

Au terme de ce lot, l’emprunt nommé d’un pool local restait à raccorder :
[programme](../../validation/open-async-local-pool-alias.crb),
[diagnostic](../../validation/open-async-local-pool-alias.log). L’injection directe
`child(&mut p)` est exercée ; `let memory = &mut p; child(memory)` reste refusé
par le lowering. Les types généraux de pools, les blocs async annotés et les
autres familles de captures restent ouverts. Les modèles et tests sont bornés,
et ne prouvent ni toutes les formes de contrôle ni tous les ordonnancements.

Le [diff du lowering](../../validation/async-local-pool-implementation.patch) est
conservé. Le [cycle des alias](ASYNC_POOL_ALIASES_CYCLE.md) poursuit ce travail.

## Résultat terminal de la régression complète

Les deux programmes invalides sont refusés, mais plus tôt que les diagnostics
attendus par les fixtures. Le même comportement est reproduit avec le lowering
antérieur aux pools locaux : [reproduction](../../validation/async-local-pool-diagnostic-baseline.log).
Le premier test reconnaît désormais le diagnostic précis String/Int en plus
du diagnostic Result. Le second enlève uniquement, dans sa variante négative,
l’appel Vector-only `received.push(11)` : il vérifie ainsi le contrat de retour
Int incorrect au lieu d’échouer d’abord sur une méthode absente d’Int.
Les programmes admis et leurs oracles ne changent pas. Les deux méthodes sont
réexécutées à O2 : deux réussites, 5,839 s, [journal](../../validation/async-local-pool-diagnostic-recheck-o2.log).
Le module complet n’est pas présenté comme entièrement vert : le résultat est
273 réussites initiales et deux méthodes corrigées puis réexécutées.
