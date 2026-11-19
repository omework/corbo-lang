[English](PUBLIC_LOCAL_ENUMS_CYCLE.md)

# Enums locaux à travers les handles publics

## Périmètre

Application de AS10–AS12, de l’API publique des handles du brouillon 04 et
du stockage local T du brouillon 05 aux enums locaux introduits au lot précédent.
Aucune nouvelle règle normative. Les contrats continuent de distinguer T et A<T>,
les sources des champs possédés et les cibles des références stockées.

Les cas de fabrique, relais de join et await utilisent déjà les contrats publics
existants. Ce lot ajoute leur couverture ciblée pour les enums locaux. Il corrige
également un filtre de match partagé qui acceptait `print(nom)` mais refusait
`print(*référence)`, alors que cette expression est une lecture déjà autorisée.
Le filtre accepte maintenant les expressions reconnues par `match_read_expression`.
Le vérificateur ordinaire contrôle toujours leur type, leur validité et leurs
emprunts. Aucune analyse du corps de la tâche n’est ajoutée au contrat public.

## Correction du constat sur bool

L’inspection du compilateur et de `tests/test_sync_bool_calls.py` a montré que
les appels booléens synchrones sont déjà raccordés avec le type `bool` en
minuscule. Le `Bool` du premier test d’enum local était une mauvaise écriture
pour cette signature, pas une absence de la fonctionnalité. Le test conditionnel
synchrone utilise maintenant `bool` et les deux branches passent. Aucun alias
supplémentaire ni nouvelle implémentation booléenne n’a été introduit.
Le rapport du lot précédent corrige également ce constat.

## Cas ciblés

Cinq méthodes dans `tests/test_public_local_enums.py` : sept exécutions natives
admises, dont une avec échec de soumission injecté, et cinq programmes invalides
refusés par `verify_program` et `compile_source`.

- Fabrique publique et auxiliaire join renvoyant Result<Choice,runtime::Error> ;
  distinction Handle<Choice>/Handle<A<Choice>> et issue LaunchFailed.
- Deux fonctions async différentes renvoient des variantes différentes du même
  enum local, avec un seul type public de handle, await et reprise après yield.
- Champ partagé : la cible reste protégée après l’extraction du résultat.
- Champ mutable : écriture dans le bras, maintien de la réservation puis accès
  autorisé après destruction du porteur ; écriture/drop prématurés refusés.
- Champ A<Int> : maintien du pool, destruction unique et réutilisation du slot.

Le test conditionnel `bool` du lot précédent ajoute deux exécutions natives
lors du passage qui le sélectionne. Les attentes sont écrites dans les tests.

## Résultats exécutés

| Journal dans validation/ | Résultat |
| --- | --- |
| public-local-enums-first-o0.log | 4 méthodes, 1 échec : filtre de print dans le match partagé |
| public-local-enums-second-o0.log | 4 méthodes, 3,525 s, code 0, dont le test bool corrigé |
| public-local-enums-third-o0.log | 5 méthodes, 3,068 s, code 0 |
| public-local-enums-regression-o2.log | 67 méthodes, 40,076 s, code 0 ; configurations détaillées ci-dessous |

Les cas ciblés utilisent le harnais C11/pthread avec warnings en erreurs et
UBSan fatal. Les modules historiques `test_mutable_match` et `test_reference_fields`
utilisent le harnais de `test_crust`, sans optimisation explicite ni sanitizer
dans cette commande. Les autres modules utilisent O2/UBSan. Le suffixe O2
du journal ne remplace pas cette distinction.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_public_local_enums test_local_enums test_shared_match_field_reads test_mutable_match test_reference_fields test_public_structure_handles -v
```

## Limites et traces

Les résultats portent sur les cas énumérés, pas toutes les combinaisons de
contrats ou de graphes. Pas de campagne adversariale ou de mutations nouvelle.
Les types récursifs et les autres formes de champs non représentées restent
ouverts. L’objectif global n’est pas achevé.

Snapshot : `/tmp/crust-before-public-local-enums/`. Patch de `crust.py` archivé
sous `validation/public-local-enums-crust.py.patch`.
