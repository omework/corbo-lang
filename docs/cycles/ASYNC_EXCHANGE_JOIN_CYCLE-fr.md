[English](ASYNC_EXCHANGE_JOIN_CYCLE.md)

# Résultats de replace/try_push enveloppés par spawn et join

## Règles et réalisation

Application de RT6, AS2–AS5, AS8–AS14, H1–H2, VE3–VE4, U1, F3–F4 et
SL1–SL2. Aucune règle normative n'est modifiée. L'erreur de lancement reste
distincte du résultat métier de la tâche : les types raccordés sont
`Result<Result<A<Int>,A<Int>>,runtime::Error>` et
`Result<Result<(),A<Int>>,runtime::Error>`.

Les signatures, contrats et représentations C distinguent les deux enveloppes.
Le stockage C contient un statut extérieur et un VectorHandleResult intérieur.
Le statut extérieur détermine si une charge existe ; pour try_push, le statut
intérieur détermine ensuite si cette charge possède l'entrant rejeté. Le
nettoyage utilise ces conditions dans les scopes, les captures et les arguments
préparés avant suspension. Aucun objet ciblé par un handle n'est déplacé.

Join depuis main et attente d'un handle depuis async restituent l'enveloppe.
Les handles publics, helpers synchrones, captures, retours async et fabriques
conservent les contrats de provenance. L'extraction du Ok extérieur restitue
le résultat intérieur, qui demande à son tour une consommation explicite.
Les jonctions de blocs, branches et boucles transportent les provenances des
deux bras et leurs obligations de nettoyage.

## Cas exécutés

Onze méthodes dans `tests/test_async_exchange_join.py` : 33 exécutions natives
et sept programmes invalides vérifiés par verify_program et compile_source.

- Replace réussi ou refusé par l'index, puis échec de soumission injecté.
- Attente d'un handle depuis async, avec résultat ou erreur de lancement.
- Handle public, helper d'attente, relais du résultat ; transfert absent refusé.
- Drop du résultat nommé et après transfert par bloc, sur les deux variantes.
- Résultat non utilisé et double consommation refusés.
- Try_push avec espace disponible ou région de 1 MiB effectivement pleine.
- Capture du résultat, exécution ou destruction inactive, destruction unique
  et réemploi des slots.
- Résultat préparé avant l'await de l'argument suivant, avec continuation ou
  destruction de la branche perdante de Select.
- Retour de l'enveloppe depuis async, directement ou via une fabrique synchrone.
- Pools distincts par bras ; ancienne allocation restituée après disparition
  du vecteur et du pool entrant ; source trop courte refusée.
- If et loop produisant l'enveloppe ; motif propriétaire ignoré refusé.
- Enveloppe de try_push relayée, détruite, capturée ou issue d'un lancement
  échoué, avec une seule destruction de l'entrant.

## Défauts et corrections

Le premier passage a relevé une perte des métadonnées des bras dans les
paramètres symboliques des relais. Le test d'échec de lancement async visait
aussi le mauvais compteur : le harnais compte séparément les soumissions
synchrones et asynchrones. La première soumission async est désormais ciblée,
sans changer le résultat attendu en cas d'échec.

Les passages suivants ont révélé deux défauts de suivi statique : identité
entrante manquante dans le pont C du relais et provenance perdue à une jonction
if. Les métadonnées de charge et leur collecte aux jonctions ont été corrigées.
Les invariants du vérificateur ont été conservés ; les programmes valides sont
acceptés après correction. Les journaux d'échec restent disponibles.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| open-async-handle-exchange-join.log | Refus initial de l'enveloppe aux deux entrées |
| async-exchange-join-first-o0.log | Cinq méthodes, 5,539 s, deux échecs |
| async-exchange-join-second-o0.log | Cinq méthodes, 5,919 s, code 0 |
| async-exchange-join-third-o0.log | Dix méthodes, 8,984 s, deux échecs |
| async-exchange-join-fourth-o0.log | Dix méthodes, 10,174 s, un échec |
| async-exchange-join-fifth-o0.log | Onze méthodes, 14,599 s, code 0 |
| async-exchange-join-sixth-o0.log | Onze méthodes, 15,461 s, code 0, fabriques incluses |
| async-exchange-join-regression-o2.log | 127 méthodes, 127,747 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_exchange_join -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_exchange_join test_async_handle_exchange_results test_async_handle_exchange_calls test_async_option_join test_async_handle_option_results test_async_handle_option_calls test_async_structure_effects test_factory_owned_effects test_public_handle_contracts test_select_source test_task_wakes -v
```

C11/pthread, avertissements en erreurs, UBSan fatal. Le harnais existant injecte
les échecs de soumission ; les valeurs et nettoyages attendus sont fixés par les
tests. La régression inclut les modèles existants de poll/nettoyage de Select
et de réveil des tâches. Aucun nouveau modèle, campagne de mutations ou audit
adversarial approfondi. Ces résultats concernent les chemins exécutés, sans
preuve générale de sûreté.

## Limites et suite

Les deux enveloppes autour de A<Int> sont raccordées dans le périmètre décrit.
Lancer une tâche qui retourne déjà une telle enveloppe ajoute encore un Result.
Ce niveau supplémentaire reste refusé explicitement et doit être raccordé ;
ce refus est une limite d'implémentation, pas une nouvelle règle de langage.
Reproduction : `validation/open-async-nested-exchange-join.crust` et `.log`.
Les autres types d'éléments et les imbrications générales ne sont pas clôturés
par ce lot. Les arbitrages publics déjà ouverts restent inchangés.

Snapshot : `/tmp/crust-before-async-exchange-join/`.
Neuf diffs sous `validation/async-exchange-join-` : async_lowering.py, crust.py,
effects.py, async_structure_effects.py, results.py, handle_types.py,
constraints.py, async_result_storage.py et le nouveau exchange_join_types.py.
