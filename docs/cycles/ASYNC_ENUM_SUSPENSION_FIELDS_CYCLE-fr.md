[English](ASYNC_ENUM_SUSPENSION_FIELDS_CYCLE.md)

# Références des descendants d'enums aux suspensions

## Raccordement des règles existantes

Ce lot applique AS16 et SL1 aux écritures de références dans un descendant
possédé d'enum : le contrat de suspension décrit les écritures déjà effectuées,
indépendamment du résultat à la terminaison. Une perdante de Select conserve
l'écriture effectuée avant son dernier yield ; une tâche terminée expose
son écriture finale. Les règles normatives ne changent pas.

L'analyse distinguait mal une modification de référence dans un descendant
d'un remplacement de son allocation. Elle comparait tout le graphe symbolique,
y compris les références stockées, et rejetait le résumé de suspension. La
comparaison porte maintenant sur l'identité du stockage possédé ; les écritures
de références utilisent les chemins aplatis déjà produits par l'analyse commune.
Les remplacements d'allocations sans représentation complète restent signalés
comme incomplets.

Le backend interprète désormais les préfixes `Variante.champ` pour appliquer
un contrat au descendant. L'analyse commune conserve également l'identité de
l'enum local, son propriétaire de stockage et son graphe lorsqu'il est emprunté
mutablement, comme elle le faisait pour les structures. Cela raccorde les
effets des enfants attendus et des branches Select à leur porteur effectif.

## Validation fonctionnelle

La passe ciblée passe cinq méthodes à O0 en 1,127 s, code 0 : les quatre méthodes
de `tests/test_async_enum_suspension_fields.py` et le cas déjà consigné dans
`test_async_enum_match`. Deux programmes sont exécutés nativement, un programme
avec drop prématuré est refusé aux deux entrées. Les contrôles de contrats
vérifient séparément suspension, terminaison, plusieurs yield et relais par await.
Journal : `validation/async-enum-suspension-fields-third-o0.log`.

Le cas historique ne réclame plus un statut incomplet : il exige maintenant
le chemin exact `Item.inner/.view` vers le paramètre cible dans le contrat de
suspension. Son ancien point de mutation, qui supprimait le refus conservateur,
a été retiré de la campagne historique : il ne correspond plus à la propriété
testée. Aucune campagne de mutations n'est exécutée dans ce lot, conformément
à la priorité utilisateur.

La régression à O2 passe 127 méthodes en 78,562 s, processus terminé avec code 0.
Elle couvre les matchs partagés/mutables/consommants, les effets de suspension,
les effets de structure, Select et les mises à jour des descendants par contrats.
Journal : `validation/async-enum-suspension-fields-regression-o2.log`.
Les exécutions natives utilisent Clang C11, pthread et UBSan sans récupération.

## Limites et traces

Les deux premiers passages ont identifié le chemin d'enum non interprété dans
le backend, puis l'identité du porteur local perdue dans l'analyse des contrats.
Leur diagnostic est conservé dans les journaux `first-o0` et `second-o0`.
L'auxiliaire de lecture du test a aussi été réécrit avec un return dans le bras,
forme déjà prise en charge : la forme résultat de match synchrone comportait
une restriction distincte. La lecture directe de champ dans cette forme est
désormais raccordée par [le lot suivant](SHARED_MATCH_FIELD_READS_CYCLE.md).
Les autres restrictions d'appels ne sont pas déclarées résolues ici.

La couverture concerne les références Int d'un graphe dont les allocations
restent les mêmes. Le remplacement de l'allocation d'un descendant pendant
une suspension, les graphes récursifs et les porteurs non représentés ne sont
pas couverts par ce lot. Il ne s'agit pas d'un audit général de sûreté.
Les remplacements sans emprunts contenus sont désormais raccordés par le
[lot des champs possédés](ASYNC_OWNED_FIELD_WRITES_CYCLE.md), avec ses propres limites.
L'audit indépendant prévu par l'utilisateur n'est pas réputé effectué.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_enum_suspension_fields test_async_enum_match.AsyncEnumMatchTests.test_changed_owned_graph_is_not_an_empty_suspension_contract -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_enum_suspension_fields test_async_enum_match test_async_consuming_enum_match test_suspension_effects test_async_structure_effects test_select_source test_nested_field_wrappers test_nested_field_choices -v
```

Snapshot : `/tmp/crust-before-async-enum-suspension-fields/`.
Les patches des trois modules sont archivés dans
`validation/async-enum-suspension-fields-*.py.patch`.
