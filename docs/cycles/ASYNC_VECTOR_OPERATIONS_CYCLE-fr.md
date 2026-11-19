[English](ASYNC_VECTOR_OPERATIONS_CYCLE.md)

# Cycle — opérations scalaires de vecteurs dans les corps async

## Portée et décisions

Implémentation de VE3/VE4 avec AS2/AS4/AS8/AS10, F4/B4a, B1/B2 et U1,
sans modification normative. Les documents de référence sont
LANGUAGE_RULES.md, FOUNDATIONS_AND_VECTORS.md et ASYNC_MULTITHREAD_RULES.md.
AGENTS.md, VALIDATION_GUIDELINES.md et l’index des sept brouillons ont été
relus avant la validation. L’interdiction actuelle de reset (PR1) demeure.

`pop`, `replace` et `try_push` produisent directement leurs Option/Result
dans un corps async sur Vector<Int/u8>. `try_extend` et `read_fd` opèrent
sur Vector<u8>. La représentation du résultat conserve la valeur rejetée,
l’ancienne valeur ou le statut approprié. Les opérations utilisent les
primitives du runtime déjà présentes ; pas de nouvelle politique mémoire.

Le receveur est réservé avant les arguments. Chaque argument est évalué,
puis copié dans un temporaire de l’état avant le suivant. Ces temporaires
survivent aux suspensions. Les contrôles de mutabilité, type et usage
explicite s’appliquent également aux appels en instruction ; un pop scalaire
peut être écarté, un Result faillible exige un usage explicite.

## Contre-exemples, modèle et observations

Le programme `validation/open-async-vector-result-producer.crust`, auparavant
refusé pour expression non prise en charge, produit maintenant `1` puis `1`.
Le log historique est préservé. Le test de remplacement évalue un indice,
puis suspend pendant une modification de cette variable : l’ancien indice
reste celui de l’opération. Supprimer son instantané change effectivement
la case remplacée et fait échouer le test.

Huit familles de résultat sont exercées dans leurs deux issues. Les
vecteurs réellement pleins occupent une région de 1M. Une extension de deux
octets avec un seul octet disponible doit échouer sans publier le premier ;
l’insertion suivante occupe cette dernière case. Un read sur le vecteur
plein signale la capacité avant l’erreur du descripteur. EOF et Io préservent
la longueur et le contenu existant. Ce n’est pas un test de tous les systèmes
de fichiers ou de toutes les erreurs d’E/S.

Deux programmes générés (graines 37 et 91) réalisent 28 opérations chacun.
Une liste Python calcule indépendamment les résultats de push, pop et replace,
y compris les indices invalides ; 112 observations de valeur/longueur sont
comparées au C exécuté. Les choix du compilateur ne servent pas d’oracle.

Les emprunts sont contestés par l’auto-extension, l’appel d’une tâche lisant
le receveur pendant la préparation de ses arguments et la réutilisation
d’une tranche après mutation. Les voisins valides sont exécutés. Un octet
et une tranche obtenus par await sont acceptés. Chez l’appelant, mutation,
lecture et drop avant join sont refusés ; drop puis réemploi après join sont
exécutés. Les retours scalaires ne retiennent pas le vecteur source.

Une capture possédée est testée sur succès et échec de lancement EAGAIN.
Le résultat est lu après réemploi du même slot. Une instrumentation du C
compte les entrées du destructeur indépendamment de la liste de slots libres :
deux allocations du scénario donnent exactement deux destructions, avec la
même adresse réutilisée. Cette instrumentation ne modifie pas les décisions
de libération du runtime et ne remplace pas une preuve générale.

Les premiers tests contenaient des erreurs de scénario : masquage du nom
du vecteur dans un motif, réemprunt écrit `&other` au lieu de `&*other`, et
réutilisation de l’indice du premier sous-cas dans le second. Ces erreurs
ont été corrigées dans les tests ; les logs initiaux ne sont pas effacés.

Un véritable écart indépendant a été minimisé dans
`validation/open-read-error-residual-pattern.crust` et son log : le parseur
assimile Err(_) à Utf8Error et refuse son association avec une variante
ReadError précise. F2 autorise le bras résiduel. Ce manque reste ouvert ;
le test de capacité emploie les variantes explicites pour vérifier séparément
l’atomicité de l’extension. Aucune règle n’a été changée pour légitimer le refus.

Mise à jour : le cycle suivant
[RESIDUAL_ERROR_PATTERNS_CYCLE.md](RESIDUAL_ERROR_PATTERNS_CYCLE.md) corrige et
valide ce motif résiduel. Le refus historique ci-dessus décrit la découverte.

## Validation exécutée

Le nouveau module final comporte 15 méthodes, 35 programmes natifs et
21 refus attendus. Les 14 premières méthodes représentent 33 exécutions
natives ; le complément de nettoyage instrumenté en ajoute deux.
Clang Homebrew 20.1.3, arm64 macOS, C11, pthread, avertissements stricts et
UBSan fatal. Les helpers concernés respectent CRUST_TEST_OPT pour O0/O2.

| Exécution | Résultat / trace |
| --- | --- |
| Lot O0, avant complément du compteur | 14 méthodes, 16,238 s, réussi ; validation/async-vector-operations-O0-final.log |
| Compteur et identité O0 | 1 méthode, 0,754 s, réussi ; validation/async-vector-operations-cleanup-O0.log |
| Compteur et identité O2 | 1 méthode, 0,808 s, réussi ; validation/async-vector-operations-cleanup-O2.log |
| Lot O2 et résultats scalaires/métier/imbriqués | 64 méthodes, 104,622 s, réussi ; validation/async-vector-operations-O2-regression.log |
| Voisins String, tranches et collections possédées | 31 méthodes, 50,114 s, réussi ; validation/async-vector-operations-neighbor-regression.log |
| ABI, emprunts, tableaux, attentes calculées | 15 méthodes, 19,995 s, réussi ; validation/async-vector-operations-abi.log |
| Mutations | Cinq détectées ; validation/async-vector-operations-mutations.log |

Les cinq mutations utilisent des copies temporaires : réservation supprimée,
instantané supprimé, charge du remplacement effacée, extension faussement
réussie et garde U1 supprimée. Chaque mutation est détectée par une assertion
sémantique, non par un échec de syntaxe. Aucun survivant dans cet échantillon ;
aucun taux général de détection n’en est déduit. Le runtime lui-même n’a pas
été muté dans ce cycle. La compilation Python des fichiers modifiés a réussi.

## Limites et suites

Ce lot ne couvre pas les éléments propriétaires/empruntés généraux, toutes les
APIs Vector, ni les erreurs enum autonomes dans les corps async. Le défaut de
motif résiduel reste ouvert. Les obligations restantes des sept brouillons
incluent les handles publics, scheduler, thread natif, Select, mutex et les
écarts de stockage déjà consignés. Pas d’ASan/TSan, de deuxième compilateur C,
de preuve formelle ou de preuve générale de sûreté dans ce cycle.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_vector_operations.AsyncVectorOperationTests -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_vector_operations.AsyncVectorOperationTests test_async_vector_results test_business_result_envelopes test_nested_plain_results test_plain_join_contracts test_runtime_error_values -v
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 tests/run_plain_join_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_async_vector_operation_mutations.py
```
