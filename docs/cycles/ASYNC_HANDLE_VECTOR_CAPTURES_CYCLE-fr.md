[English](ASYNC_HANDLE_VECTOR_CAPTURES_CYCLE.md)

# Captures async de vecteurs de handles

## Règles et implémentation

Application de VE1–VE2, H1, B1–B5 et AS2/AS8–AS12, sans modification normative.
Vector<A<Int>> contient des handles propriétaires ; la tâche qui reçoit le
vecteur par transfert prend en charge le nettoyage des éléments. Un emprunt
partagé ou mutable conserve les réservations ordinaires du vecteur et de ses
pools jusqu'à la terminaison établie.

Le lowering refusait ce type dans les captures alors que la représentation
Cell du vecteur et son nettoyage existaient déjà. Le type est maintenant admis
pour le passage au cadre et classé comme collection. Les deux formes internes
de len lisent sa longueur via vector_len. Aucun nouveau runtime d'allocation
ni copie de contenu n'a été introduit.

## Cas ciblés

Cinq méthodes dans tests/test_async_handle_vector_captures.py : cinq exécutions
natives et six invalides aux deux entrées du compilateur.

- Emprunt partagé : lecture de longueur après yield ; destruction du vecteur,
  destruction du pool d'éléments et ajout avant join refusés.
- Emprunt mutable : relais async avec enfant attendu ; lecture concurrente
  chez l'appelant refusée.
- Transfert du vecteur : destruction de l'élément une seule fois en terminaison
  normale, puis réemploi du pool Int de capacité un.
- Même nettoyage pour une tâche inactive explicitement détruite et pour un
  échec de lancement injecté EAGAIN. Aucune exécution du corps dans ces cas.
- Une signature Vector<Int> ne reçoit pas silencieusement Vector<A<Int>>.

La fixture validation/open-async-owned-vector-capture.crust, refusée dans le
journal historique associé, est maintenant exécutée par le test partagé.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| async-handle-vector-captures-first-o0.log | Trois méthodes, 1,401 s, code 0 |
| async-handle-vector-captures-second-o0.log | Cinq méthodes, 1,787 s, code 0 |

Régression terminée : 57 méthodes, 73,554 s, code 0, dans
validation/async-handle-vector-captures-regression-o2.log.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_captures -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_captures test_async_vector_operations test_async_vector_remove test_async_vector_results test_async_collection_new -v
```

C11/pthread, warnings en erreurs, UBSan fatal. Les oracles ciblés portent sur
les sorties, la destruction unique et le réemploi de capacité un. Les modèles
finis existants des suites de collections sont réexécutés ; aucun nouveau
modèle indépendant ou campagne de mutations.

## Limites

Ce lot raccorde les captures et la lecture de longueur, pas l'ensemble de l'API
Vector<A<Int>> dans les états. L'accès aux éléments, les insertions/extractions,
les retours de ces vecteurs et leur construction locale async restent à
compléter. Les vecteurs de références et les autres types d'éléments ne sont
pas déclarés couverts. L'objectif global et les arbitrages publics restent
ouverts ; aucune preuve générale de sûreté.

Snapshot : /tmp/crust-before-async-handle-vector-captures/.
Diff : validation/async-handle-vector-captures-async_lowering.py.patch.

Lecture de case encore refusée aux deux entrées :
validation/open-async-owned-vector-read.crust et .log. Ce cas est le prochain
raccordement, pas une restriction normative.
