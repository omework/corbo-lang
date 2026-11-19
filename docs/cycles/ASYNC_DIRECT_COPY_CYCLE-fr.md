[English](ASYNC_DIRECT_COPY_CYCLE.md)

# Copie directe de structures dans un corps async

## Règles et écart corrigé

ST17/ST18 s'appliquent dans un corps async : copie explicite et structurellement
autorisée, conservation des cibles partagées, distinction entre valeur locale
et allocation de pool. Aucune règle normative modifiée.

Le programme `validation/open-async-direct-structure-copy.crust` était refusé
par « copy exige une ligne ou un tableau », alors que la même copie dans un
auxiliaire synchrone fonctionnait. Le refus de la version initiale est reproduit
dans `validation/async-direct-copy-baseline.log`.

## Implémentation

Le lowering distingue maintenant la copie de structure de celle d'un tableau.
Il initialise un nouvel objet indépendant et recopie les champs autorisés :

- `copy(local)` utilise la data stack du receveur ; le plan de placement
  identifie aussi ce constructeur avant une sortie de bloc ou un retour async.
- `copy(allocation)` conserve le pool réel de l'original.
- `pool.copy(original)` sélectionne explicitement le pool destinataire.
- Une référence locale vers la structure conserve les origines de son stockage
  et de ses champs empruntés. Les copies ne prolongent pas les cibles.
- Les champs propriétaires et les références mutables rendent la copie refusée.

Le C utilise les primitives existantes de construction puis une copie des
champs. Il ne déplace pas une allocation déjà construite. Les layouts locaux
restent statiques afin de survivre à l'état async producteur.

## Cas exécutés

Six méthodes ciblées dans `tests/test_async_direct_copy.py` : six exécutions
natives et quatre programmes invalides vérifiés aux deux entrées, soit huit
contrôles de refus.

- Copie via une référence locale, suspensions et transferts successifs au parent.
- Copie d'une capture et retour à l'appelant, pour une origine locale ou de pool.
- Copie vers un pool explicite, destruction de l'original et réemploi du slot.
- Copie d'un champ partagé : destruction de l'original autorisée, destruction
  de la cible avant sa dernière lecture refusée.
- Copies de champs A<T> ou &mut Int refusées ; pool trop court refusé.
- Sonde C : original et copie distincts, copie créée dans la destination
  extérieure avant suspension, même adresse après extraction, pool d'états vide
  et stockage destinataire sans allocation vivante après drop.

## Résultats terminés

Tous les processus ci-dessous se sont terminés avec code 0, sans test sauté.

| Passage | Résultat | Journal |
| --- | --- | --- |
| Ciblé initial O0 | 6 méthodes, 2,780 s | `validation/async-direct-copy-o0-first.log` |
| Régression O2 avant ajustement des alias locaux | 69 méthodes, 63,783 s | `validation/async-direct-copy-regression-o2.log` |
| Ciblé final O0 | 6 méthodes, 3,426 s | `validation/async-direct-copy-o0-final.log` |
| Copie et stockage des résultats, final O2 | 20 méthodes, 13,416 s | `validation/async-direct-copy-final-o2.log` |

Clang C11, pthread, avertissements comme erreurs, UBSan fatal. La régression
de 69 méthodes n'a pas été entièrement répétée après l'ajustement des alias ;
les 20 méthodes directement liées ont été rejouées sur la version finale.

## Reproduction et limites

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_async_direct_copy
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_async_direct_copy test_async_result_storage test_async_local_parent test_select_result_placement test_async_result_factories test_public_structure_handles
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_async_direct_copy test_async_result_storage
```

Snapshot initial : `/tmp/crust-before-async-direct-copy/`. Patches archivés dans
`validation/async-direct-copy-{async_lowering,async_local_placement}.py.patch`.

Couverture ciblée des structures représentables Int et &Int ; ce lot ne raccorde
pas les structures inline imbriquées encore non prises en charge. Aucun nouveau
modèle indépendant, audit adversarial ou campagne de mutations. Les résultats
ne constituent pas une preuve générale de sûreté et ne clôturent pas l'ensemble
du chantier d'intégration. Les arbitrages scheduler et capture de handle lancé
restent ouverts.
