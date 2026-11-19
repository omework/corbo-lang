[English](RETURNED_OWNED_REPLACEMENT_CYCLE.md)

# Restituer un objet après remplacement d'un champ propriétaire

## Règles et cas enregistré

Ce lot applique les règles existantes de remplacement, de transfert explicite,
d'identité stable et de durée des pools, ainsi que AS10–AS13 pour le résultat
d'une tâche. Le remplacement évalue la nouvelle allocation, détruit l'ancienne
et conserve le nouveau champ. Rendre le porteur transmet ce graphe final.
Aucune règle normative n'est modifiée.

`validation/open-async-return-replaced-owned-field.crust` était encore refusé
par « restitution avec remplacement de champ propriétaire ». Un auxiliaire
remplace le champ A<Int> d'un Holder par 11 dans un autre pool, puis rend le
même Holder. Une tâche appelle cet auxiliaire et transmet son résultat par join.
Le programme est maintenant accepté et exécuté.

## Corrections

Les contrats de résultat conservent les champs remplacés même lorsque la racine
est le paramètre d'entrée. La résolution superpose ces champs aux champs
inchangés du porteur. La validation du corps vérifie le graphe final contre
ce contrat, au lieu de refuser systématiquement toute différence de disposition.
La restitution conserve l'identité nominale et l'adresse de la racine, sans
restaurer ses anciennes dépendances de champs.

La projection du résultat async distingue désormais le pool de la racine et
les pools de ses champs après remplacement. Un raccourci de l'analyse symbolique
renvoyait auparavant simplement la photographie du paramètre initial : après
la première correction de restitution, cela faisait accepter à tort un résultat
dont le nouveau champ sortait de son pool. Le test de durée a révélé cet écart ;
le raccourci ne s'applique plus à un résultat contenant des champs modifiés.
Les cibles empruntées contenues dans ces champs sont remappées depuis le contrat.

La première régression a détecté deux refus sur des graphes imbriqués inchangés :
le calcul des sources du contrat utilisait seulement le cache du descendant
direct et omettait le pool d'un petit-enfant symbolique. Il parcourt maintenant
le graphe propriétaire, tout en conservant les sources d'éléments des feuilles
comme les collections. Les contrôles de provenance ne sont pas désactivés.

## Cas testés

Six méthodes dans `tests/test_returned_owned_replacement.py` :

- Programme enregistré, égalité des adresses avant/après join, destructions
  uniques de l'ancien champ 7, du nouveau champ 11 et du Holder.
- Échec de lancement injecté : destruction de la capture initiale, sans
  exécution du remplacement ni création de 11.
- Appel synchrone et contrat de restitution, même adresse, réemploi du slot
  ancien avant destruction du résultat, puis réemploi du slot nouveau.
- Await direct puis relais async suspendu conservant le pool du nouveau champ.
- Refus des résultats dont le champ survit à un pool trop court, en synchrone
  et en async ; les transferts de scope nécessaires sont explicites.
- Champ propriétaire voisin inchangé conservé ; descendant contenant &Int
  conservant sa cible jusqu'au dernier usage, avec drop prématuré refusé.

Le passage ciblé comprend six exécutions natives et quatre programmes invalides
vérifiés aux deux entrées, soit huit contrôles de refus. Les adresses comparées,
les valeurs attendues et les traces de nettoyage constituent les oracles des
tests ; ils ne sont pas déduits des décisions internes du compilateur.

## Résultats exécutés

| Passage | Résultat | Journal dans validation/ |
| --- | --- | --- |
| Six méthodes ciblées O0 | Code 0, 2,587 s | `returned-owned-replacement-o0.log` |
| Première régression O2 | 90 méthodes, deux échecs de graphe imbriqué, code 1 | `returned-owned-replacement-regression-o2.log` |
| Contrôle O0 après correction des descendants | Huit méthodes, code 0, 4,831 s | `returned-owned-replacement-o0-final.log` |
| Régression finale O2 | 90 méthodes, code 0, 78,048 s | `returned-owned-replacement-regression-o2-final.log` |

Le dernier passage inclut les six méthodes ciblées, les deux régressions et la
préservation des sources d'éléments des feuilles, sur la version finale.
Clang C11, pthread, avertissements traités comme erreurs et UBSan sans
récupération ; aucun test sauté. Les modèles déjà présents dans les suites liées,
notamment le modèle de profondeurs des pools, sont rejoués. Aucun nouveau modèle
indépendant n'est revendiqué. Ce n'est ni la suite entière ni une preuve générale.

## Limites

Les cas exécutés couvrent une racine restituée avec champs A<Int> et un
descendant contenant &Int. Ils ne prouvent pas tous les graphes récursifs,
changements de variantes, résultats enveloppés et combinaisons de branches.
Les analyses de provenance restent conservatrices. Les arbitrages ouverts
du scheduler, des constructeurs de mutex et des captures de handles restent
inchangés. Pas de nouvelle campagne adversariale ni de mutations.

Les premiers journaux conservent une erreur de syntaxe Python du nouveau test,
puis une fixture à laquelle manquait le transfert explicite du porteur dans le
bloc enfant. La fixture corrigée teste la durée du pool plutôt que ce premier
refus de scope. Le même passage a exposé l'acceptation incorrecte async décrite
ci-dessus ; son contrôle de refus est conservé dans le test final.

## Reproduction et artefacts

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_returned_owned_replacement
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_returned_owned_replacement test_async_owned_struct_sync_calls test_async_local_owned_result_graphs test_public_structure_handles test_nested_owned_borrows test_factory_owned_effects test_async_result_factories test_async_owned_field_writes
```

Snapshot : `/tmp/crust-before-returned-owned-replacement/`. Différences de
`crust.py`, `results.py` et `async_result_storage.py` archivées dans
`validation/returned-owned-replacement-*.py.patch`.
