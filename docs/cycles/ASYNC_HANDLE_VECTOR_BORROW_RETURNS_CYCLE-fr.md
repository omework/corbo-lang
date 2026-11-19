[English](ASYNC_HANDLE_VECTOR_BORROW_RETURNS_CYCLE.md)

# Retours async d'emprunts vers les éléments de Vector<A<Int>>

## Règles et changements

Application de H2, VE1/VE4, B1–B5 et AS9–AS12. Un emprunt partagé ou mutable
vers le contenu d'une allocation contenue dans un vecteur peut sortir de la
tâche si le porteur extérieur reste valide. Le résultat conserve sa réservation
jusqu'au dernier usage, y compris à travers les relais attendus. Un vecteur
transféré à la tâche puis détruit à sa terminaison ne permet pas ce retour.
Aucune règle normative modifiée.

Le calcul de provenance reconnaît désormais les projections &*v[i] et
&mut *v[i] des paramètres Vector<A<Int>>. Il conserve le vecteur porteur dans
le contrat. Côté appelant synchrone, le résultat est représenté comme un int*
emprunté avec réservation du porteur ; le descripteur n'est plus confondu avec
le Cell du vecteur. Les retours relayés et les résultats utilisés dans un état
async emploient les mécanismes existants de durée de vie.

La validation après join a rencontré une écriture synchrone manquante :
*values[i] = valeur. Elle est raccordée avec vérification de la case, sélection
de la cible avant le RHS, réservation partagée pendant ce RHS, puis contrôle
d'accès mutable avant l'écriture. Lire le vecteur dans le RHS est permis ;
l'emprunter mutablement pendant cette préparation est refusé.

## Couverture ciblée

Six méthodes dans tests/test_async_handle_vector_borrow_returns.py : sept
exécutions natives (six normales, une terminaison contrôlée) et dix programmes
invalides contrôlés aux deux entrées.

- Retour partagé puis mutation du vecteur après dernière lecture : admis.
  Drop, écriture ou remplacement du porteur avant lecture : refusés.
- Retour depuis un vecteur transféré à la tâche : refusé, sans promotion.
- Retour mutable, écriture 11 via le résultat, puis 12 par le porteur après
  dernier usage ; destruction unique de 12 et réemploi du pool avec 8.
  Lecture prématurée du porteur et usage de l'emprunt après mutation refusés.
- Relais async partagé et mutable, yield dans les deux états : résultats 7/13,
  nettoyage et réemploi ; drop prématuré du vecteur refusé dans les deux cas.
- Résultat d'await conservé dans un état, yield, lecture puis mutation après
  dernier usage ; prolonger l'usage au-delà de la mutation est refusé.
- RHS synchrone lisant le vecteur admis ; RHS demandant &mut refusé.
- Hors bornes synchrone : diagnostic avant le marqueur 123 du RHS.

## Exécutions et défauts rencontrés

Journaux conservés dans validation/ :

| Journal | Résultat |
| --- | --- |
| async-handle-vector-borrow-returns-first-o0.log | Écriture synchrone *v[i] encore traitée comme tableau de références ; raccordée |
| async-handle-vector-borrow-returns-second-o0.log | Oracle de drop du pool refusé plus tôt pour transfert interdit ; remplacé par un remplacement du porteur pour tester le conflit visé |
| async-handle-vector-borrow-returns-third-o0.log | Flèche manquante dans le nouveau remplacement négatif ; ajoutée. Réservation du RHS trop forte, corrigée pour permettre la lecture partagée |
| async-handle-vector-borrow-returns-fourth-o0.log | Cinq méthodes, 2,860 s, code 0 |
| async-handle-vector-borrow-returns-final-o0.log | Six méthodes, 3,248 s, code 0 |
| async-handle-vector-borrow-returns-regression-o2.log | 49 méthodes, 41,046 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_borrow_returns -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_borrow_returns test_async_handle_vector_borrows test_async_handle_vector_access test_async_handle_vector_captures test_async_reference_returns test_async_vector_push_new test_recursive_borrow_results test_recursive_mutable_results -v
```

C11/pthread, warnings en erreurs et UBSan fatal. La régression exerce les
retours de références vers tableaux, vecteurs scalaires et champs récursifs.
Les oracles de valeurs, diagnostics, ordre d'effets et destruction sont explicités
par les tests. Aucun nouveau modèle ni campagne adversariale/mutation ; les
modèles des suites existantes sont conservés. Pas de preuve générale de sûreté.

## Limites et suite

La provenance du résultat réserve le vecteur entier, sans précision par indice.
Ce lot ne prétend pas vérifier tous les indices disjoints ou toute l'API des
vecteurs. L'insertion depuis async reste ouverte :
validation/open-async-handle-vector-push.crust et .log reproduisent le refus
aux deux entrées de push(-> numbers.new(7)) après yield, avec pools injectés.
Les opérations restantes et les arbitrages publics scheduler/mutex restent ouverts.

La fixture open-async-handle-vector-borrow-return.crust est désormais couverte ;
son journal de refus reste historique.
Snapshot : /tmp/crust-before-async-handle-vector-borrow-returns/.
Diffs : validation/async-handle-vector-borrow-returns-{crust.py,async_lowering.py}.patch.
