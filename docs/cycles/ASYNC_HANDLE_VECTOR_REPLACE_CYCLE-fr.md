[English](ASYNC_HANDLE_VECTOR_REPLACE_CYCLE.md)

# Remplacement de handles de vecteur dans async

## Règles appliquées et implémentation

Application de H1–H2, VE3, U1, B1–B5, AS8–AS12 et SL1–SL2, sans modification
normative. replace prépare l'indice puis la valeur entrante. Sur succès, la case
reçoit le nouveau handle et le résultat possède l'ancien. Sur indice invalide,
le vecteur reste inchangé et le résultat possède l'entrant. Le pointeur de la
cible ne change pas ; seule la responsabilité de nettoyage est transférée.

Le générateur d'états async raccorde les formes de match direct et de résultat
nommé à vector_replace et VectorHandleResult. Le contenu du résultat est
possédé sur les deux branches, contrairement à Option : son drop est donc
inconditionnel. Une extraction dans un bras vide son pointeur source et donne
la responsabilité au receveur du bras. Les sources possibles de l'ancien et
de l'entrant restent distinctes pour cette extraction.

Le receveur est réservé pendant l'évaluation des arguments, y compris les
await. Les sources entrantes sont publiées dans les effets du vecteur afin de
survivre à un retour normal ou à la destruction d'une branche suspendue de
Select. Le résultat peut être déplacé, conservé pendant yield ou détruit
directement. Les signatures de fonctions transportant l'enveloppe complète
ne sont pas raccordées par ce lot.

## Cas ciblés

Sept méthodes dans tests/test_async_handle_vector_replace.py. La version finale
contient quatorze exécutions natives et sept invalides aux deux entrées.

- Remplacement réussi et indice invalide ; valeur renvoyée, valeur conservée
  dans le vecteur, destruction unique de l'ancien et de l'entrant.
- Flèche manquante et réutilisation de l'entrant transféré refusées.
- Résultat nommé, yield, déplacement et drop ; usage manquant et double
  consommation refusés. Drop direct testé sur succès et erreur.
- Emprunt terminé avant remplacement admis ; emprunt encore utilisé après et
  receveur partagé refusés.
- Indice et allocation entrante produits par deux tâches attendues : l'ordre
  observé est 1, 2, puis les valeurs 7, 8 et 9.
- Perdant Select suspendu après remplacement : l'ancien est détruit une fois,
  le nouveau reste dans le vecteur et son pool reste suivi.
- Pool local trop court pour la valeur insérée refusé.
- Retour de l'ancien ou d'un remplacement de secours, via appel direct ou
  fabrique de tâche. Le vecteur et le pool de l'entrant disparaissent avant
  l'utilisation du résultat, dont le pool extérieur survit.

Le cas initial validation/open-async-handle-vector-replace.crust était refusé
aux deux entrées avec « expression array_handle_exchange non prise en charge ».
Il est maintenant exécuté et produit 7, 8, 9. Aucun nouvel écart sémantique n'a
été découvert dans les passes ciblées et les régressions exécutées.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| async-handle-vector-replace-first-o0.log | Six méthodes, 3,523 s, code 0 |
| async-handle-vector-replace-second-o0.log | Sept méthodes, 5,466 s, code 0 ; avant ajout des deux cas de drop direct |
| async-handle-vector-replace-regression-o2.log | 72 méthodes, 77,334 s, code 0, avec les deux cas de drop direct |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_replace -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_replace test_async_handle_vector_pop test_async_handle_vector_push test_async_handle_vector_remove test_async_option_join test_factory_owned_effects test_select_source test_foundation_rules.FoundationTests.test_handle_vector_replace_error_return_preserves_parameter_identity test_foundation_rules.FoundationTests.test_handle_vector_replace_match_requires_explicit_transfer test_foundation_rules.FoundationTests.test_buffered_handle_replace_preserves_result_after_vector_changes -v
```

C11/pthread, avertissements en erreurs, UBSan fatal. La suite Foundation
conserve son profil historique legacy-reset ; reset reste retiré du prototype.
La régression inclut le modèle existant de poll/nettoyage de Select. Aucun nouveau modèle indépendant ni campagne de
mutations. Les tests portent sur les cas convenus et leurs régressions liées ;
l'audit approfondi reste distinct. Aucune preuve générale de sûreté n'est revendiquée.

## Limites et suite

Périmètre : Vector<A<Int>> dans les états async, avec résultats locaux et retour
de l'allocation extraite. La précision des sources des anciennes cases reste
conservative lorsque leur position n'est pas connue. Les signatures transportant
Result<A<Int>,A<Int>>, les constructions et autres retours de vecteurs restent
à compléter dans les chemins async concernés.

Le prochain cas reproduit est validation/open-async-handle-vector-try-push.crust
et .log : try_push de handle est refusé aux deux entrées, « expression
array_handle_try_push non prise en charge ». Les arbitrages publics ouverts
restent inchangés.

Snapshot : /tmp/crust-before-async-handle-vector-replace/.
Diff : validation/async-handle-vector-replace-async_lowering.py.patch.
