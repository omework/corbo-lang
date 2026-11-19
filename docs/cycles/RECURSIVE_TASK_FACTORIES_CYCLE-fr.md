[English](RECURSIVE_TASK_FACTORIES_CYCLE.md)

# Fabriques de tâches portant des graphes récursifs

## Règles et périmètre

Suite du lot ASYNC_RECURSIVE_OWNED_CYCLE.md. Application des règles existantes
AS8–AS12, des transferts explicites et des contrats par paramètres aux fabriques
synchrones et relais de tâches nominales. Aucun changement normatif.
Les appels restent vérifiés à partir des contrats, sans parcourir le corps.

## Défauts et corrections

La description des chemins d’un type s’arrête au premier type répété. Elle ne
suffisait pas à instancier la valeur concrète reçue par une fabrique : seuls les
premiers descendants étaient conservés, et leur variante était perdue. Le join
refusait alors un graphe pourtant fini. Les métadonnées concrètes de l’argument
sont maintenant instanciées par les origines publiées du contrat ; chaque
chemin conserve ses sources, identités et variantes, ainsi que ses descendants.
Les champs explicitement décrits par le contrat sont raccordés séparément.

Les captures empruntées héritées d’un propriétaire entier, ainsi que celles
d’une tâche relayée, conservent les chemins concrets au-delà du premier type
répété. Un chemin prouvé absent pour la variante active est représenté par une
capture vide ; il peut être relayé sans être confondu avec une capture inconnue.
Les pools de tous les descendants capturés restent protégés, même si le
résultat futur est un scalaire et ne conserve aucun propriétaire.

## Vérification ciblée

Trois méthodes dans tests/test_recursive_task_factories.py : cinq exécutions
natives admises, cinq programmes invalides refusés par verify_program et
compile_source.

- Fabrique depuis un propriétaire puis relais d’une tâche : graphe à deux liens,
  variante terminale, destruction unique et réemploi du slot terminal ; drop du
  pool terminal avant l’attente refusé.
- Référence stockée dans le descendant terminal : fabrique puis relais, et
  création directe puis relais ; mutation prématurée après join refusée.
- Tâche qui détruit le graphe et retourne Int : protection du pool terminal
  jusqu’à complétion et réemploi ensuite.

Les attentes sont écrites dans les tests. La sortie native, les traces de
nettoyage et les diagnostics sont vérifiés. Le harnais utilise C11/pthread,
les warnings en erreurs et UBSan fatal.

| Journal dans validation/ | Résultat |
| --- | --- |
| recursive-task-factories-first-o0.log | 2 méthodes, 2 échecs : descendants incomplets et capture introuvable |
| recursive-task-factories-second-o0.log | 2 méthodes, 1,428 s, code 0 |
| recursive-task-factories-third-o0.log | 3 méthodes, 2,282 s, code 0 |

La régression liée se termine avec code 0 : 99 méthodes en 77,697 s,
`validation/recursive-task-factories-regression-o2.log`, à O2/UBSan.
Les modèles déterministes existants dans la sélection sont rejoués ; aucune
nouvelle campagne de génération ou de mutations n’a été ajoutée.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_task_factories -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_recursive_task_factories test_async_recursive_owned test_async_result_factories test_detached_task_factories test_task_result_storage test_public_structure_handles test_async_owned_borrowed_captures test_async_owned_borrow_writes test_async_owned_nominal_writes test_async_owned_struct_returns -v
```

Le premier journal O0 porte sur la première version de deux méthodes ; le
second aussi. La troisième version ajoute le consommateur scalaire et le relais
direct de la tâche, d’où les cinq exécutions et cinq refus détaillés ci-dessus.

## Limites

Ce lot couvre les origines concrètes héritées des paramètres et des tâches
relayées. Il ne déclare pas terminés les résultats construits avec une forme
récursive neuve entièrement opaque, les auxiliaires qui attendent un résultat
récursif symbolique, ni toutes les projections et substitutions profondes.
Le programme `validation/open-recursive-join-helper.crust` reproduit le refus
d’un helper recevant Handle<A<Node>> et retournant le résultat de join.
`validation/open-recursive-join-helper.log` localise le déroulement infini dans
ResultContext.async_owned_result_value. C’est un écart d’implémentation ouvert,
pas un arbitrage sémantique ni un programme invalidé par les règles.
La conservation des captures entières peut rester conservatrice quand un
contrat modifie certains descendants. Les régressions sur les écritures de
champs sont incluses dans la sélection ; elles ne constituent pas une preuve
sur toutes les combinaisons. Pas de nouvelle campagne adversariale ni mutation.

Snapshot : /tmp/crust-before-recursive-task-factories/.
Patch : validation/recursive-task-factories-crust.py.patch.

Suite : le cas du helper public de join est désormais corrigé et testé dans
[RECURSIVE_JOIN_HELPERS_CYCLE.md](RECURSIVE_JOIN_HELPERS_CYCLE.md).
