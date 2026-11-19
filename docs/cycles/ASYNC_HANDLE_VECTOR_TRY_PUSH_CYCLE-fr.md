[English](ASYNC_HANDLE_VECTOR_TRY_PUSH_CYCLE.md)

# Insertion faillible de handles dans async

## Règles et implémentation

Application de H1–H2, VE3–VE4, U1, B1–B5, AS8–AS12 et SL1–SL2, sans
modification normative. try_push transfère l'entrant au vecteur sur succès.
Si la limite est atteinte, le vecteur reste inchangé et Err possède l'entrant.
Ok(()) ne possède aucune allocation, mais le résultat doit être explicitement utilisé.

Le générateur async partage la préparation du receveur et de l'entrant avec
replace. Il conserve une variante de résultat distincte, dont seul le bras
Err exige un nettoyage. Après insertion réussie, le pointeur du résultat est
mis à NULL ; la case du vecteur conserve le handle et son nettoyage. Après
échec, une extraction transfère ce pointeur au receveur du bras. Un drop détruit
uniquement le contenu rejeté. Les chemins suspendus de Select appliquent la
même règle.

Le match direct consomme aussi le résultat sur son bras Ok(()), pour permettre
la continuation après les deux bras sans obligation résiduelle. Les résultats
nommés, annotés Result<(),A<Int>>, déplacés et conservés à travers yield sont
raccordés. Les sources publiées par l'insertion restent suivies dans le vecteur.

## Cas ciblés

Sept méthodes dans tests/test_async_handle_vector_try_push.py : quatorze
exécutions natives et neuf programmes invalides aux deux entrées.

- Succès et capacité réellement atteinte : valeur rendue, contenu du vecteur
  et destruction unique de l'entrant.
- Flèche manquante, motif Ok incompatible et réutilisation de l'entrant refusés.
- Résultat nommé et annoté, yield, déplacement puis match consommant.
- Drop direct et nommé, sur succès et erreur ; résultat inutilisé et double
  consommation refusés.
- Continuation après un match direct ou nommé avec Ok(()).
- Emprunt d'élément terminé avant insertion admis ; usage encore à venir,
  receveur partagé et source locale trop courte refusés.
- Allocation entrante produite par une tâche attendue.
- Perdant Select suspendu après try_push : valeur conservée dans le vecteur
  sur succès, valeur rejetée détruite sur erreur ; réemploi des slots.

Les cas pleins utilisent une région explicite de 1 MiB et la remplissent avec
1 MiB / taille d’un pointeur natif. Sur la plateforme testée, cela fait
131072 cases. Ce sont des programmes Crust exécutés, sans réduction artificielle
de limite dans le C généré.

Le premier passage avait un défaut de snippet : une liaison n ajoutée par le
test entrait en collision avec celle d'un bras. Le snippet a été remplacé par
un emprunt d'élément effectif, avec usage avant/après l'insertion. Aucune règle
de déclaration ni oracle de résultat n'a été assoupli.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| open-async-handle-vector-try-push.log | Refus initial aux deux entrées : array_handle_try_push non raccordé |
| async-handle-vector-try-push-first-o0.log | Six méthodes, 5,846 s ; un échec dû à la collision de noms du snippet |
| async-handle-vector-try-push-second-o0.log | Sept méthodes, 6,981 s, code 0 |
| async-handle-vector-try-push-regression-o2.log | 72 méthodes, 75,217 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_try_push -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_try_push test_async_handle_vector_replace test_async_handle_vector_push test_async_handle_vector_pop test_async_handle_option_results test_factory_owned_effects test_select_source test_foundation_rules.FoundationTests.test_handle_vector_try_push_requires_transfer_and_unit_success test_foundation_rules.FoundationTests.test_buffered_handle_try_push_cleans_only_rejected_handle test_foundation_rules.FoundationTests.test_handle_vector_try_push_returns_incoming_at_capacity -v
```

C11/pthread, avertissements traités en erreurs et UBSan fatal. Les tests vérifient
les sorties, le nettoyage unique et le réemploi des pools. Foundation conserve
son profil historique legacy-reset, sans réintroduire reset dans le prototype.
Le modèle existant de poll/nettoyage de Select est inclus dans la régression.
Aucun nouveau modèle indépendant ni campagne adversariale ou de mutations.
Ces résultats ne constituent pas une preuve générale de sûreté.

## Limites et suite

Périmètre : insertion de A<Int> et enveloppes locales dans les états async.
Les signatures transportant Result<A<Int>,A<Int>> et Result<(),A<Int>> restent
à raccorder aux appels depuis async, puis aux captures et résultats de tâches.
Les constructions et autres retours de vecteurs ne sont pas clôturés ici.

Cas suivant reproduit : validation/open-async-handle-exchange-call.crust et .log.
Le helper synchrone retourne le résultat de replace à une tâche ; les deux
entrées refusent encore sa signature. Les arbitrages publics ouverts restent inchangés.

Snapshot : /tmp/crust-before-async-handle-vector-try-push/.
Diff : validation/async-handle-vector-try-push-async_lowering.py.patch.
