[English](NATIVE_BLOCK_LOWERING_CYCLE.md)

# Cycle — compilation des premiers blocs natifs

Suite : [appels synchrones depuis les états](NATIVE_SYNC_CALLS_CYCLE.md).
Le refus de l’auxiliaire add décrit ci-dessous est historique ; sa signature
scalaire est maintenant raccordée. Les appels à signatures générales restent ouverts.

## Règles et périmètre

Application de RT8, RT4–RT7, AS7/AS10/AS11 et des règles existantes de
transfert, de mutabilité, de durée de vie et de provenance. Aucune décision
normative n’a changé. Le cycle précédent constituait un progrès exécuté :
parsing et primitives natives. Ce cycle raccorde ces éléments au compilateur.
AGENTS.md, les guidelines, l’index des brouillons et les règles pertinentes
ont été consultés ; les lectures de LANGUAGE_RULES.md et de l’extension async
du cycle précédent restent applicables.

Le programme minimal `validation/open-native-thread-basic.crust` compile et
s’exécute désormais avec la sortie `7`. Les anciens journaux de refus sont
conservés comme historique, pas comme statut actuel. RT8 reste partiel :
les auxiliaires synchrones appelés depuis le bloc, les créations de pools
dans les corps utilisant ce backend, les captures de handles et les types
généraux ne sont pas tous raccordés.

## Traduction et contrôles

`native_threads.py` isole chaque bloc dans une définition interne dont le
type de résultat est inféré depuis les retours et la valeur finale. Les
types des captures viennent de l’environnement lexical. Le corps ne reçoit
que les liaisons explicitement listées. Les noms internes contiennent un
caractère non accepté dans les identifiants source ; le programme ne peut
pas appeler artificiellement ces définitions comme des fonctions async.

La définition réutilise l’ABI des états et son pool typé, avec le marquage
interne `native_block`. Ce marquage ne change pas le bloc en fonction
suspendable : le parseur refuse toujours yield et await dans son corps et
le lancement appelle la primitive native indépendante du scheduler. Le
contrôle transitoire qui refusait tous les blocs a été remplacé par ce passage.

Les vérificateurs existants contrôlent ensuite les types et les effets de
chaque opération. Le nouveau passage ne constitue pas une preuve d’emprunt.
Les captures allouées passent par les transferts existants ; les liaisons
scalaires et empruntées sont également invalidées après capture. Les cibles
empruntées restent suivies par les dépendances de l’état puis du résultat.
Les branches du résultat conservent l’union des provenances possibles.

Une attente join dans le bloc utilise les contrôles de résultat et de
provenance communs, mais attend par une boucle bloquante de polling avec
sched_yield, sans produire TASK_STEP_YIELD. Cette première implémentation
n’est pas une attente OS optimisée. Un appelant async attend le handle avec
await. L’échec de lancement conserve le traitement LaunchFailed et le
nettoyage des captures ; le handle reste à attendre explicitement.

Les retours terminaux dont l’opérande quitte déjà tous les chemins ne créent
pas de résultat fictif supplémentaire. Ce point était nécessaire pour un
match terminal avec return dans chaque bras. Les tableaux capturés par valeur
utilisent l’opération interne de déplacement de tableau ; les allocations
utilisent leur transfert de pointeur.

## Scénarios et oracles

`tests/test_native_blocks.py` comporte treize méthodes, 29 exécutions de
programmes Crust compilés en C et 40 refus attendus par passage complet.
Le module de parsing conserve sept méthodes ; ses quatre refus transitoires
ont été remplacés par des vérifications de l’obligation d’attente sur les
mêmes programmes qui abandonnent leur handle.

Les cas exécutés comprennent :

- Retours Int, Bool, u8 et Void ; valeur finale, retour anticipé et résultat
  de boucle ; les valeurs Bool/u8 sont observées par branchement/conversion
  explicite vers Int, selon les opérations d’affichage disponibles.
- Capture scalaire dans un appelant sync ou async, ancienne liaison inutilisable
  avant et après l’attente ; transfert du tableau complet avec conservation
  du contenu observé et invalidation de son ancien accès.
- Référence vers une case de tableau, mutation autorisée après attente ;
  référence mutable retournée, lecture/mutation/drop de la cible refusés
  pendant l’exécution et tant que le résultat emprunté doit servir.
- Deux sources possibles d’un résultat mutable : les deux branches sont
  exécutées et chacune des deux mutations prématurées est refusée.
- Allocation Int reçue par un bloc natif depuis main ou une tâche parente,
  nettoyage à la sortie ou à l’échec, puis réemploi d’un pool de capacité un.
- Allocation retournée : adresse conservée entre la capture et la réception,
  puis même slot réutilisé après drop ; à l’échec, réemploi après nettoyage.
  Les traces de destructeurs exigent exactement 7 puis 9, sans doublon.
- Bloc natif qui crée un enfant natif et appelle join, avec succès, échec du
  lancement extérieur ou échec du seul enfant. L’abandon de l’enfant est refusé.
- Fonction synchrone appelante qui capture son paramètre emprunté dans un
  bloc natif et traite join ; indépendance du lancement natif vis-à-vis d’un
  scheduler qui refuse les lancements supplémentaires.

Les refus couvrent aussi les retours de types incompatibles, l’absence de
capture explicite, la mutabilité insuffisante, le transfert du pool lui-même,
la fuite d’un emprunt local et les sorties où une cible ou un pool ne survit
pas au handle. Les cas de durée de vie terminent désormais par un join traité,
afin qu’un abandon volontaire de handle ne masque pas l’erreur visée.

Les attentes sont des valeurs, traces, identités et décisions explicites
dérivées des règles. Les deux flags de sélection, les deux catégories
d’appelants et les échecs injectés constituent une exploration finie ; aucun
modèle général de concurrence ni preuve de sûreté n’est revendiqué. Les modèles
existants de handles et de scheduler font partie de la régression.

## Résultats exécutés

| Journal dans validation/ | Résultat |
| --- | --- |
| native-block-initial.log | Programme minimal : sortie 7 |
| native-block-captures-initial.log | Quatre premiers programmes : 8, 7, 7, 8 |
| native-block-joins-initial.log | Retour mutable et appelant async passent ; match terminal encore refusé avant correction |
| native-block-nested-join.log | Match terminal corrigé : sortie 8 |
| native-blocks-initial-o0.log | Échecs initiaux conservés : pools locaux async non supportés, affichages non adaptés et diagnostics d’attente distincts |
| native-blocks-o0.log | 16 méthodes, 9,374 s, OK, avant les trois interactions ajoutées |
| native-blocks-interactions-initial.log | Deux méthodes passent ; déplacement de tableau refusé avant correction de son opération interne |
| native-blocks-o0-final.log | 19 méthodes, 11,019 s, OK, avant ajout de la sonde de dispatch |
| native-blocks-dispatch-o0.log | Sonde ajoutée : 1 méthode, 1,532 s, OK |
| native-blocks-regression-o2.log | 81 méthodes, 92,846 s, OK, sans saut |
| native-blocks-identity-o0.log / identity-o2.log | Renfort des identités après la régression : 1 méthode, respectivement 1,197 / 1,554 s, OK |
| native-blocks-cleanup-o0.log / cleanup-o2.log | Renfort final des identités et traces : 2 méthodes, respectivement 2,885 / 3,086 s, OK |

La régression charge les modules native_blocks, native_thread_parser,
native_thread_runtime, spawn_blocking, handle_obligations et
async_typed_divergence, puis les méthodes du runtime sélectionnées par
threads/scheduler/workers/spawn/nettoyage/réemploi. Le script reproductible
est `tests/run_native_thread_regression.py` ; les noms exacts sont dans le journal.
Clang C11, pthread, avertissements stricts et UBSan fatal sont employés.

```sh
PYTHONPATH=tests CRUST_TEST_OPT=-O0 python3 -m unittest -v test_native_blocks test_native_thread_parser
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_block_mutations.py
```

Les modules modifiés passent py_compile et les liens locaux des documents
modifiés sont vérifiés (`validation/native-blocks-artifacts.log`). Les artefacts
`validation/native-block-basic.c` et `validation/native-block-ownership.c`
sont cette fois du C généré depuis les programmes Crust correspondants.
L’inspection du second montre le pointeur remis au résultat, la capture mise
à NULL, le chemin de nettoyage qui ne détruit pas le résultat retourné,
task_native_start et task_join_allocation. Le diff de l’implémentation est
conservé dans `validation/native-block-lowering.patch`.

## Mutations

Les mutations vivent uniquement dans des copies temporaires. Trois fautes
du premier passage sont détectées : capture sync non consommée, capture async
non consommée et lancement natif envoyé au scheduler. Effacer toutes les
provenances déclenche l’invariant « emprunt retourné sans cible » : ce résultat
est conservé comme inconclusif dans le protocole ciblant une admission indue.

La mutation affinée ne conserve qu’une des deux origines. Le test détecte alors
l’acceptation indue de la mutation de b, pour les deux flags. Quatre mécanismes
ciblés ont ainsi une détection exécutée ; l’essai initial inconclusif n’est pas
effacé. Voir `native-blocks-mutations.log` et `native-blocks-origin-mutation.log`.

## Obligations encore ouvertes

Deux programmes valides refusés sont conservés avec leurs diagnostics dans
`validation/native-blocks-open-cases.log` :

- `open-native-sync-helper.crust` : appel d’une fonction synchrone add depuis
  le bloc natif, refusé par le backend des corps.
- `open-native-async-local-pool.crust` : création d’un pool dans l’appelant
  async, refusée par ce même backend. Les tests de captures allouées async
  utilisent une allocation reçue de main ; ils ne valident pas ce cas local.

Les captures de pools et handles, les autres agrégats et références composées,
l’inférence de toutes les expressions, les corps divergents sans résultat
déductible, les interactions génériques avec les features et les annotations
publiques runtime::Handle<T> restent à compléter. Les tests d’adresse de ce
cycle concernent A<Int>, pas la stabilité universelle des tableaux déplacés.
Les capacités des états anonymes sont traitées par les bornes existantes ;
les configurations générales et récursives restent à éprouver.

Le cycle n’est pas une preuve ASan/TSan, multi-compilateur ou formelle. ASan
n’a pas été relancé après les blocages précédemment documentés. Les autres
obligations ouvertes des sept brouillons restent dans l’objectif actif.
