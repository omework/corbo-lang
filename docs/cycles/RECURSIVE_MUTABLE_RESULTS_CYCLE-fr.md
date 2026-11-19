[English](RECURSIVE_MUTABLE_RESULTS_CYCLE.md)

# Retours mutables depuis des descendants récursifs

## Règles et correction

Application des règles existantes ST11–ST12, B1–B5 et AS8–AS12. Contrairement
à une référence partagée stockée retournée comme valeur (ST13), un réemprunt
mutable conserve la capacité exclusive de son porteur jusqu'au dernier usage.
Aucune nouvelle sémantique ni promotion de durée de vie.

Le contrat d'un résultat de match perdait le chemin propriétaire dès qu'il
rencontrait un descendant symbolique de type récursif. results.py publie
maintenant le chemin complet pour les origines owned_projection et
owned_field_input au lieu d'en faire une cible locale. Les autres origines
locales restent locales. crust.py résout les champs propriétaires symboliques
et prépare leurs références terminales avant de reconstruire les réservations
du contrat. La chaîne de porteurs est conservée par le mécanisme existant.

## Cas ciblés

Deux méthodes dans tests/test_recursive_mutable_results.py : trois programmes
valides natifs et sept invalides aux deux entrées (verify_program et
compile_source). Ils suivent deux liens A<Node> jusqu'à un champ &mut Int.

- Appel synchrone et appel depuis une tâche avec yield entre le retour et
  l'écriture : valeur finale 8, porteur détruit après dernier usage.
- Drop du porteur, drop de la cible et écriture directe avant utilisation du
  résultat refusés. Les usages parasites après drop sont retirés dans les tests.
- Relais synchrone ajoutant un paramètre avant le porteur : conservation de la
  provenance après renumérotation, accès après dernier usage et drop précoce refusé.

Les oracles sont les sorties explicites et les règles de durée de vie. Aucun
nouveau modèle indépendant ou campagne de mutations ; les tests existants
liés aux retours et aux contrats sont conservés.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| recursive-mutable-results-first-o0.log | Deux sous-cas refusés à tort : cible non durable |
| recursive-mutable-results-second-o0.log | Deux sous-cas refusés : projection symbolique non résolue |
| recursive-mutable-results-third-o0.log | Une méthode, 0,876 s, code 0 |
| recursive-mutable-results-fourth-o0.log | Deux méthodes, 1,206 s, code 0 |

Régression terminée : 97 méthodes en 42,486 s, code 0, dans
validation/recursive-mutable-results-regression-o2.log.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_mutable_results -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_recursive_mutable_results test_recursive_borrow_results test_recursive_borrow_projections test_recursive_join_helpers test_recursive_task_factories test_async_recursive_owned test_shared_match_field_reads test_async_stored_views test_async_enum_nominal test_mutable_match_function_return test_mutable_borrow_returns test_direct_borrow_returns -v
```

Harnais ciblés : C11/pthread, warnings en erreurs et UBSan fatal. La sélection
async utilise O2 ; les anciens harnais synchrones activent UBSan via
CRUST_SANITIZE mais n'ajoutent pas O2. Leurs cas de reset utilisent explicitement
le profil historique et ne réintroduisent pas reset dans le prototype.

## Limites

Ces tests concernent les chemins parcourus et les graphes construits dans les
programmes indiqués. Pas de preuve générale sur les graphes récursifs ; les
remplacements de liens restent à compléter. Les autres fonctionnalités et
arbitrages ouverts ne sont pas clôturés par ce lot.

Snapshot : /tmp/crust-before-recursive-mutable-results/.
Diffs : validation/recursive-mutable-results-{crust.py,results.py}.patch.
