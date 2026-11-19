[English](ASYNC_HANDLE_EXCHANGE_CALLS_CYCLE.md)

# Résultats de replace et try_push dans les appels depuis async

## Règles et réalisation

Application de H1–H2, VE3–VE4, U1, F4, B1–B5, AS8–AS13 et SL1–SL2.
Aucune modification normative. Les contrats des helpers synchrones peuvent
désormais transmettre `Result<A<Int>,A<Int>>` et `Result<(),A<Int>>` à un
appelant async, recevoir ces enveloppes par transfert et les restituer.

Le pont C utilise `VectorHandleResult`. Pour replace, chaque variante possède
un handle ; pour try_push, seul Err en possède un. Le transfert d'un argument
préparé avant une suspension conserve ce nettoyage conditionnel jusqu'à l'appel.
Si Select détruit cette branche suspendue, il nettoie l'argument préparé une
seule fois. Sur succès de try_push, le vecteur conserve seul l'entrant.

La provenance de chaque bras est conservée séparément à travers les contrats,
y compris pour un relais. L'ancienne allocation peut ainsi survivre au pool de
l'entrante si son propre pool reste valide. Les expressions directement
transférées `helper(->v.replace(...), ...)` et `helper(->v.try_push(...), ...)`
sont reconnues par le parseur, comme les résultats nommés et les blocs.

## Cas exécutés

Huit méthodes dans `tests/test_async_handle_exchange_calls.py` : dix-neuf
exécutions natives et cinq programmes invalides vérifiés par les deux entrées.

- Retour direct, relais et variantes succès/erreur de replace et try_push.
- Arguments nommés, appels imbriqués, opérations directes et blocs ; un await
  dans l'argument suivant vérifie l'ordre d'évaluation.
- Consommateur Void et drop du retour d'un helper ; destruction unique et
  réemploi des slots.
- Select perdant pendant la préparation d'un appel : replace et try_push,
  vecteur non plein ou limite de région réellement atteinte.
- Pools distincts par bras, allocation ancienne restituée après disparition
  du vecteur et du pool de l'entrante ; source trop courte refusée.
- Flèche absente, mauvais type d'enveloppe, résultat sans usage et double
  consommation refusés.

Les cas de capacité réutilisent le remplissage effectif d'une région de 1 MiB,
sans modifier les limites du runtime C. Les assertions de nettoyage vérifient
la destruction unique des valeurs concernées et le réemploi des pools.

## Exécutions et corrections

| Journal dans validation/ | Résultat |
| --- | --- |
| open-async-handle-exchange-call.log | Refus initial aux deux entrées : signature synchrone non raccordée |
| async-handle-exchange-calls-first-o0.log | Six méthodes, 5,298 s, un échec sur l'argument direct replace |
| async-handle-exchange-calls-second-o0.log | Six méthodes, 6,141 s, code 0 après raccordement du parseur |
| async-handle-exchange-calls-third-o0.log | Huit méthodes, 7,466 s, code 0 |
| async-handle-exchange-calls-regression-o2.log | 131 méthodes, 87,844 s, code 0 |

Le fixture initial a été corrigé pour déclarer l'entrant du helper synchrone
`->A<Int>` : son insertion exige un handle explicite. Le refus initial a été
reproduit sur cette version valide avec le snapshot antérieur au lot. Aucun
oracle ni exigence de type n'a été assoupli.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_exchange_calls -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_exchange_calls test_async_handle_vector_replace test_async_handle_vector_try_push test_async_handle_option_calls test_async_option_join test_select_source test_fixed_arrays test_foundation_rules.FoundationTests.test_handle_vector_replace_error_return_preserves_parameter_identity test_foundation_rules.FoundationTests.test_buffered_handle_replace_preserves_result_after_vector_changes test_foundation_rules.FoundationTests.test_buffered_handle_try_push_cleans_only_rejected_handle -v
```

C11/pthread, avertissements traités en erreurs, O2 et UBSan fatal pour les tests
async. La suite FixedArray emploie ses paramètres par défaut (sans optimisation
ni sanitizer explicitement activés dans cette commande) ; elle ne lit pas
CRUST_TEST_OPT. Les trois tests Foundation utilisent O2 et UBSan fatal.
La régression inclut la suite existante des tableaux fixes, directement
concernée par la syntaxe commune de replace, ainsi que les contrats synchrones
et les nettoyages de Select. Les suites historiques FixedArray et Foundation
conservent leur profil legacy-reset ; cela ne réintroduit pas reset dans le
prototype. Les modèles existants de tableaux et de Select sont rejoués.
Pas de nouveau modèle, de campagne de mutations ni d'audit adversarial approfondi.
Les tests réussis ne constituent pas une preuve générale de sûreté.

## Limites et suite

Périmètre : helpers synchrones depuis async, enveloppes portant A<Int>.
Les captures et retours de tâches de ces enveloppes restent à raccorder,
ainsi que leur enveloppe externe de spawn/join. Le programme
`validation/open-async-handle-exchange-result.crust` reproduit le refus d'un
retour async via await aux deux entrées ; son journal est conservé.
Les types d'éléments supplémentaires et l'ensemble des constructions de
vecteurs ne sont pas clôturés par ce lot. Les arbitrages publics ouverts
restent inchangés.

Snapshot : `/tmp/crust-before-async-handle-exchange-calls/`.
Diffs : `validation/async-handle-exchange-calls-async_lowering.py.patch` et
`validation/async-handle-exchange-calls-crust.py.patch`.
