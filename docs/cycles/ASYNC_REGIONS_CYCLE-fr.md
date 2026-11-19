[English](ASYNC_REGIONS_CYCLE.md)

# Cycle — régions annotées dans les blocs async et natifs

Suite du [cycle des alias de pools](ASYNC_POOL_ALIASES_CYCLE.md).
Aucune règle normative modifiée. Références : G4–G12, A1/A4, D1,
S4/S5, B1/B2/B4a, T6/T11, AS8/AS10/AS12 et RT8 ; brouillons 03/04/05.
Le support global du langage reste partiel.

## Écart et implémentation

Le lowering refusait toute annotation de région dans un bloc async,
y compris lorsque son contenu était déjà compilable sans annotation.
Le [programme conservé](../../validation/open-async-region.crb) utilise un
pool local Vector<u8>, un scope annoté 1M et yield. Il est maintenant
exécutable ; [C généré](../../validation/async-region-basic.c),
[diff du lowering](../../validation/async-region-implementation.patch).

Une pile de configuration lexicale accompagne la génération des blocs.
Un bloc sans annotation hérite de son parent ; un bloc annoté remplace
temporairement la limite. La configuration est restaurée même si le bloc
ne rejoint pas son point de sortie normal. Les blocs instructions et les
blocs produisant un scalaire, une allocation ou un emprunt suivent cette règle.
Les constructeurs String et Vector<Int/u8> reçoivent la limite courante.

La limite est établie à la création de la région : yield, transfert,
réception dans un scope différemment annoté et retour de fonction ne la
modifient pas. Un appel ne transmet pas implicitement sa directive à la
fonction appelée, comme dans le compilateur synchrone existant.
Les pools restent dans leur scope et les frontières de durée de vie sont
inchangées. Les primitives de régions et de synchronisation C sont réutilisées
sans modification. Le code des blocs natifs emprunte le même chemin.

## Oracles et contre-exemples

Un oracle ajouté au C de test lit la taille de la classe de région réellement
associée à chaque collection construite. Les attentes viennent de la source
du test et ne sont pas extraites du C produit. Il distingue aussi la création
sans annotation, qui utilise un front de croissance sans classe de région.

Les scénarios couvrent héritage, remplacement local, restauration, transferts
2M → 1M, retours conditionnels 1M/2M reçus dans 4M, alias de pools, helpers
synchrones, enfants async, scopes de boucles, continue/break, emprunts et
retours anticipés. Les variantes qui perdent leur pool ou utilisent une
collection pendant un emprunt incompatible sont refusées.

Un Vector<u8> créé dans 1M puis transféré hors du bloc est rempli à 1 048 576
octets. Après yield, try_push restitue l’octet refusé ; la longueur et le
dernier octet restent inchangés. Cela vérifie une limite effective après
transfert, pas seulement une valeur de configuration dans le C.

Le modèle généré emploie une pile de configurations indépendante et deux
arbres de scopes issus des graines 19 et 73. Chaque arbre produit 14 régions,
avec allocations avant/après les enfants et suspensions. Les 28 tailles
physiques observées correspondent aux attentes de ce modèle fini.

## Preuves exécutées

Clang C11 pthread, warnings bloquants, UBSan fatal, O0/O2. Aucun nouveau
résultat ASan/TSan, second compilateur ou preuve formelle.

| Passage | Résultat | Journal |
| --- | --- | --- |
| Initial O0 | Sept méthodes, 5,755 s, OK | [Initial](../../validation/async-regions-initial-o0.log) |
| Final O0 | Neuf méthodes, 8,473 s, OK | [O0](../../validation/async-regions-final-o0.log) |
| Final O2 | Neuf méthodes, 8,603 s, OK ; 14 exécutions C, trois refus | [O2](../../validation/async-regions-final-o2.log) |
| Mutations O2 | Baseline huit méthodes/10,147 s, OK, avant ajout du modèle généré ; quatre fautes détectées | [Mutations](../../validation/async-regions-mutations-o2.log) |
| Régression pools/collections/régions O2 | 102 méthodes, 111,887 s, OK | [Régression](../../validation/async-regions-regression-o2.log) |
| Régression contrôle de flux O2 | 36 méthodes, 58,798 s, OK | [Contrôle](../../validation/async-regions-control-o2.log) |

Les fautes injectées suppriment l’héritage, la restauration de la configuration,
la limite des String ou la limite des Vector. Toutes sont détectées dans des
copies temporaires, sans modifier les attentes. La suppression de la limite
Vector est notamment détectée par le test d’épuisement après transfert.
Aucune couverture universelle n’est déduite des quatre mutations.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_regions -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_regions -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_region_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_pool_aliases test_async_local_pools test_async_collection_new test_async_vector_operations test_async_vector_push_new test_growth_annotations test_growth_runtime -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_expression_loop_exits test_async_diverging_expressions test_async_typed_divergence test_async_loop_references -v
```

## Limites

Cette extension raccorde les annotations aux constructions déjà prises en
charge dans les états. Elle ne généralise pas les collections d’agrégats,
les captures de structures ou tous les placements anticipés de data stack.
Les sources injectées et locales continuent à suivre leurs règles existantes.
Le modèle teste des arbres finis ; il ne prouve ni tous les programmes ni
tous les ordonnancements. Les performances ne sont pas mesurées.

À la fin de ce lot, le prochain écart était reproduit sans type feature : une tâche qui capture
un `&Point` local, se suspend puis lit `point.x` reste refusée par la liste
fermée des types de captures du lowering. Le pool et les annotations de
régions ne sont pas en cause : [programme minimal](../../validation/open-async-struct-reference.crb),
[diagnostic actuel](../../validation/open-async-struct-reference.log).

Ce cas est désormais raccordé dans le [cycle des captures de structures](ASYNC_STRUCT_CAPTURES_CYCLE.md).
