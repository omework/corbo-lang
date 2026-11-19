[English](ASYNC_HANDLE_VECTOR_ACCESS_CYCLE.md)

# Accès au contenu des handles d'un vecteur depuis async

## Règles et changements

Application de H1, VE1/VE4, B1–B5 et des règles d'ordre d'évaluation et de
suspension. `*values[i]` lit l'Int ciblé par le handle ; ce n'est pas une copie
du handle A<Int>. `*values[i] = valeur` modifie ce contenu avec un accès mutable,
sans remplacer l'allocation ni changer son pool.

Le lowering charge un Cell* depuis la case contrôlée du vecteur, puis lit ou
écrit son contenu. Pour l'écriture, la cible est sélectionnée et les bornes sont
contrôlées avant l'évaluation de la valeur entrante. Une réservation partagée
temporaire du vecteur autorise une lecture dans le RHS mais empêche sa mutation
ou destruction pendant cette évaluation, y compris si elle suspend.

La lecture synchrone `*values[i]` rencontrée lors de la vérification du résultat
après join n'était pas raccordée : elle utilisait le chemin des tableaux de
références. Elle utilise maintenant le contrôle existant d'emprunt de case de
Vector<A<Int>>, puis copie seulement l'Int ciblé. Aucune règle modifiée.

## Cas ciblés

Quatre méthodes dans tests/test_async_handle_vector_access.py : quatre
exécutions natives, dont une terminaison contrôlée hors bornes, et trois
programmes invalides aux deux entrées.

- Lecture après yield, résultat 7 puis réemploi du pool avec 8. La lecture
  implicite du handle comme Int est refusée.
- Écriture `*values[0] = *values[0] + 2`, suspension puis lecture 9 ; le code
  synchrone voit aussi 9 après join. Destruction unique de la cible valant 9.
  Écriture via capture partagée et lecture du caller avant join refusées.
- Indice fourni par un enfant attendu, puis RHS fourni par un autre enfant
  attendu : résultat 12, nettoyage et réemploi.
- Indice 1 dans un vecteur de longueur 1 : diagnostic « indice de Vector hors
  limites », aucune impression du marqueur 123 dans le RHS.

La fixture validation/open-async-owned-vector-read.crust est désormais exécutée
par la première méthode. Son ancien journal de refus demeure historique.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| async-handle-vector-access-first-o0.log | Lecture sync manquante ; oracle du diagnostic hors bornes en anglais corrigé |
| async-handle-vector-access-second-o0.log | Quatre méthodes, 1,708 s, code 0 |

Régressions terminées avec code 0 : 50 méthodes en 48,365 s dans
validation/async-handle-vector-access-regression-o2.log ; trois méthodes
synchrones en 2,469 s dans validation/async-handle-vector-access-sync-regression.log.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_access -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_access test_async_handle_vector_captures test_async_collection_new test_async_vector_remove test_async_vector_operations -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_shared_handle_vector_signature_relays_a_case_borrow test_foundation_rules.FoundationTests.test_handle_vector_result_tracks_replacement_through_a_slot_loan test_foundation_rules.FoundationTests.test_vector_rejects_type_mismatch_and_effectful_alias -v
```

Harnais ciblés et async : C11/pthread, warnings en erreurs, UBSan fatal.
Les cas Foundation utilisent leur harnais O2/UBSan et legacy-reset pour les
scénarios historiques. Pas de nouvelle campagne adversariale ou de mutations.
Les attentes portent sur les valeurs, les diagnostics, l'ordre des effets
et la destruction ; elles ne constituent pas une preuve générale.

## Limites

Les emprunts nommés d'éléments, les insertions/extractions, la construction locale
async et le retour de Vector<A<Int>> restent à raccorder. L'accès aux cibles
Int n'implique pas que toute l'API des vecteurs soit disponible. Les autres
fonctionnalités et arbitrages ouverts ne sont pas clôturés.

Snapshot : /tmp/crust-before-async-handle-vector-access/.
Diffs : validation/async-handle-vector-access-{crust.py,async_lowering.py}.patch.

Prochain cas reproduit : validation/open-async-owned-vector-borrow.crust et .log.
La liaison &*values[0] conservée pendant yield est encore refusée aux deux entrées.
