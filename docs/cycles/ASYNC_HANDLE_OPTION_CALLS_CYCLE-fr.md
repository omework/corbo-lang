[English](ASYNC_HANDLE_OPTION_CALLS_CYCLE.md)

# Options propriétaires dans les appels synchrones depuis async

## Règles et implémentation

Application de H1–H2, VE3, U1, B1–B5, AS8–AS12 et SL1–SL2, sans modification
normative. Une Option<A<Int>> transférée peut traverser un helper synchrone
appelé depuis une tâche. Le résultat conserve le pool de l'élément et sa
responsabilité unique de nettoyage. None ne possède aucune allocation.

La signature est raccordée à VectorHandleResult dans les appels et les ponts C.
Le résultat est déclaré propriétaire et exige un receveur utilisé ou un drop.
L'argument exige -> et conserve le statut et le pointeur. Les arguments sont
préparés de gauche à droite ; un contenu déjà transféré est enregistré pour
le nettoyage d'une suspension avant la fin de préparation de l'appel.
Les champs du résultat absent ne sont pas lus dans le calcul du contrat.
Le drop d'une option statiquement vide matérialise son usage en C avec (void),
sans inventer d'allocation ni de destruction.

## Cas ciblés et défauts rencontrés

Sept méthodes dans tests/test_async_handle_option_calls.py : quinze exécutions
natives et sept programmes invalides contrôlés aux deux entrées.

- Retour Some/None par helper, consommation et réemploi du pool.
- Résultat propriétaire ignoré et match sans consommation explicite refusés.
- Option nommée, appel imbriqué, pop direct explicitement transféré et bloc
  retournant l'option ; argument suivant contenant un await, ordre 4/7/8.
- Flèche absente, seconde consommation et A<Int> à la place d'Option refusés.
- Consommateur Void et drop direct du résultat, sur Some et None.
- Option encore utilisable après destruction du vecteur transféré à la tâche.
- Perdant de Select suspendu pendant l'argument suivant : le helper n'est pas
  appelé, l'élément préparé est détruit une fois, le slot est réutilisable.
- Retour async de l'élément après extraction par helper ; sortie du bloc du
  vecteur admise, pool de l'élément trop court refusé sur les deux branches.
- Relais synchrone d'une option statiquement vide, suivi d'un drop.

Deux régressions synchrones ont rencontré un plantage préexistant : le contrat
lisait owned_fields sur une allocation absente. Elles échouent aussi sur le
snapshot antérieur au lot (journal baseline-empty). Le cas minimal conservé
est validation/empty-handle-option-forward.crust : avant correction,
verify_program acceptait et compile_source levait AttributeError. Après
correction, la compilation native a révélé un usage C manquant pour le drop
vide ; il est également corrigé. Les tests concernés passent sans affaiblir
leurs oracles.

## Exécutions

Journaux dans validation/ :

| Journal | Résultat |
| --- | --- |
| open-async-handle-option-call.log | Refus initial aux deux entrées : signature non prise en charge |
| async-handle-option-calls-first-o0.log | Cinq méthodes, exécutions réussies ; diagnostic d'un type incompatible trop vague |
| async-handle-option-calls-second-o0.log | Six méthodes, 6,401 s, code 0 |
| async-handle-option-calls-regression-o2.log | 61 méthodes, 99,319 s, code 0, avant les corrections du cas statiquement vide et du diagnostic de match |
| async-handle-option-calls-sync-regression.log | Quatre méthodes, deux erreurs sur le relais de None |
| async-handle-option-calls-baseline-empty.log | Les mêmes deux erreurs sur le snapshot antérieur, 0,118 s |
| empty-handle-option-forward-before.log | Cas minimal : check accepte, compilation lève AttributeError |
| async-handle-option-calls-third-o0.log | Sept méthodes, échec C warnings-as-errors pour le drop du résultat vide |
| async-handle-option-calls-final-o2.log | Sept méthodes ciblées + quatre synchrones : onze méthodes, 10,245 s, code 0 après toutes les corrections |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_option_calls -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_option_calls test_async_handle_vector_pop test_async_handle_vector_remove test_sync_owned_calls test_async_awaited_owned_results.AsyncAwaitedOwnedResultsTests.test_argument_expression_families_and_forms test_async_awaited_owned_results.AsyncAwaitedOwnedResultsTests.test_suspended_prepared_result_cleanup test_select_source -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_option_calls test_foundation_rules.FoundationTests.test_buffered_handle_pop_return_contract_across_calls test_foundation_rules.FoundationTests.test_buffered_handle_pop_passes_statically_empty_option_from_function test_foundation_rules.FoundationTests.test_buffered_handle_pop_transfers_as_argument test_foundation_rules.FoundationTests.test_buffered_handle_pop_cleans_only_a_present_payload -v
```

C11/pthread, avertissements en erreurs, UBSan fatal. Foundation conserve son
profil historique legacy-reset ; reset reste exclu du prototype normal.
La passe de 61 méthodes inclut le modèle existant d'ordre de poll/nettoyage de
Select ; aucun nouveau modèle indépendant ni campagne de mutations. Les
preuves portent sur les chemins exécutés et ne constituent pas une preuve
générale de sûreté. La suite de 61 méthodes n'a pas été rejouée après les deux
corrections finales : leurs cas ciblés et les quatre régressions synchrones
ont été rejoués à O2, avec succès.

## Suite et limites

Le résultat Option<A<Int>> d'une tâche async, sa capture et son enveloppe après
spawn/join restent à raccorder. Prochain cas reproduit aux deux entrées :
validation/open-async-handle-option-result.crust et .log, où extract devient
async et son option est reçue par await. La signature async est encore refusée.
Les autres opérations de vecteurs et les arbitrages publics déjà ouverts ne
sont pas clôturés par ce lot. Le match consommant d'option testé passe par une
liaison explicite.

Snapshot : /tmp/crust-before-async-handle-option-calls/.
Diffs : validation/async-handle-option-calls-{async_lowering.py,crust.py}.patch.
