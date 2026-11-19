[English](SELECT_RESULT_STORAGE_CYCLE.md)

# Select : type concret et stockage du résultat

## Règles appliquées

Ce lot applique SL1 (même type dans toutes les branches), V1 (T local distinct
de A<T>), les transferts explicites et les contrats de provenance existants.
Aucune nouvelle règle normative n'est introduite. Le contrôle s'applique aussi
à une sélection détruite sans être attendue, et à une branche qui ne sera
jamais pollée : l'ordre d'exécution ne change pas le type des branches.

## Contre-exemples et correction

`validation/counterexample-select-mixed-result-storage.crust` était accepté
par verify_program et compile_source. La première tâche rendait un Point local,
la deuxième une allocation A<Point>. Le backend ne comparait que le couple
interne (owned, Point), dont l'ABI C utilise dans les deux cas Cell*.

La comparaison inclut désormais la classe du stockage du résultat. Le contrôle
suit les Select transférés par if et break. Les choix de tâches avant leur
insertion dans Select conservent également cette distinction. Deux allocations
issues de pools différents restent du même type A<T> : leurs provenances sont
conservées, sans exiger un pool identique. Une référence &Int ne change pas de
type selon que sa cible est locale ou allouée.

Un second essai a montré qu'une tâche construisant un résultat en pool pouvait
conserver dans les sources du résultat celle d'une capture locale détruite
avant le retour. Le contrat complet des origines est désormais utilisé même
lorsque la fonction n'a pas besoin d'un emplacement de résultat local injecté.
Le parcours syntaxique conservateur reste le recours lorsque le contrat ne
fournit pas les origines nécessaires. Le test oppose une construction locale
fraîche à une construction en pool et vérifie aussi deux constructions en
pools distincts après destruction de captures locales.

Le stockage reste à adresse stable. Aucun changement du runtime C ni copie
implicite d'une allocation n'est ajouté. Les cas natifs couvrent les structures
avec descendants possédés et références, le drop de Select avant utilisation
du résultat, le réemploi des slots, et l'échec du lancement du parent.

## Validation exécutée

La suite `tests/test_select_result_storage.py` passe 10 méthodes à O0 en
16,905 s : 17 exécutions natives, 18 programmes invalides et 36 contrôles de
refus. Journal : `validation/select-result-storage-count-o0.log`.
Les deux entrées de vérification partagent des composants ; elles ne sont pas
deux implémentations indépendantes.

Le modèle fini croise les deux classes de stockage de chaque branche et la
suspension de la première branche : huit combinaisons, quatre programmes
admis exécutés et quatre refusés aux deux étapes. L'oracle compare les types
source et calcule la gagnante selon l'ordre de poll, sans lire les décisions
du compilateur. Ces comptes sont inclus dans ceux ci-dessus.

La campagne de mutations passe son baseline de dix méthodes à O2 en 17,470 s
et détecte cinq fautes par assertions : omission du stockage lors de la
construction, du if de Select, du break de Select, du choix de tâches et
conservation d'une capture locale non retournée. Journal :
`validation/select-result-storage-mutations-o2.log`. Le processus finit avec
code 0 ; les échecs internes des cinq compilateurs mutés sont attendus.

La régression élargie passe 167 méthodes à O2 en 150,209 s, dans
`validation/select-result-storage-regression-o2.log`. Elle comprend les
contrats/source/runtime de Select, les résultats et handles de structures,
les arguments de tâches et de handles, le stockage local et les nettoyages
suspendus. Les modèles existants de poll, de destruction et de réemploi
exécutés dans ces suites complètent le modèle ciblé. Tous les processus
finaux sont terminés avec code 0.

Les exécutables sont compilés avec clang C11, pthread, O0/O2, avertissements
comme erreurs et UBSan fatal. Aucun nouveau résultat ASan ou TSan ni preuve
formelle n'est revendiqué.

## Chronologie et limites

- Le baseline conserve 27 échecs dans `select-result-storage-baseline.log` :
  26 acceptations invalides aux deux entrées et une erreur d'instrumentation
  du test d'échec de lancement. Ce test injectait dans l'entrée async alors
  que le lancement visé était synchrone ; l'injection cible maintenant la
  bonne entrée, avec réemploi de deux slots après échec.
- La première suite de sept méthodes passe en 5,895 s, puis la suite enrichie
  de dix méthodes en 11,095 s. Journaux `select-result-storage-first-o0.log`
  et `select-result-storage-second-o0.log`.
- Les programmes invalides n'ont pas été exécutés en C. Leurs acceptations
  initiales violent le typage, sans démonstration d'une corruption mémoire.
- Les classes de stockage des structures représentées sont couvertes, pas
  tous les types agrégés ni toutes les signatures async possibles.
- Cette validation ne constitue pas une preuve générale de sûreté.

L'utilisateur a confirmé que le type du scheduler personnalisé et ses
signatures publiques restent à arbitrer. Les responsabilités déjà retenues
restent applicables. Le point est consigné dans `design-buffer/points-ouverts.md`.
Le chantier global reste actif et incomplet, notamment pour les gardes de
mutex et les formes de résultats encore non représentées.
Un prochain écart est conservé dans `validation/open-async-owned-enum.crust` :
le transfert d'un enum utilisateur dans une tâche puis son retour est refusé
par la restriction des captures async, alors que le pendant synchrone est
accepté. Les diagnostics sont dans `validation/open-async-owned-enum.log`.
Ce constat ne codifie pas le refus comme une règle du langage.

## Reproduction

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_select_result_storage -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 tests/run_select_result_storage_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_select_result_storage test_select_source test_select_results test_select_contracts test_select_runtime test_task_result_storage test_public_structure_handles test_sync_task_arguments test_async_execution_arguments test_async_result_storage test_async_local_owned_result_graphs test_suspended_cleanup -v
```

Le diff de l'implémentation est archivé dans
`validation/select-result-storage-async_lowering.py.patch`, depuis le snapshot
`/tmp/crust-before-select-result-storage/`.
