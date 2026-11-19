[English](INLINE_STRUCTURE_CONSTRUCTION_CYCLE.md)

# Initialisation des structures inline imbriquées

## Règles et écart

ST1 impose que les champs contenus directement appartiennent à l'allocation
extérieure. ST3/ST4 définissent les défauts, les initialisations nommées et leur
ordre ; ST6–ST8, ST17/ST18 et les règles async conservent les contraintes de
chemins, de copie et de durée de vie. Aucune règle normative modifiée.

Le layout aplatissait déjà les champs contenus, et les formes nommées comme
`segment.start.x: expression` étaient prises en charge. La construction
`Outer { a: Pair { left: 1, right: 2 }, ... }` restait refusée par
« champ inconnu dans Outer ». Le refus du programme enregistré
`validation/open-nested-structure-literal.crust` est reproduit sur le snapshot
initial dans `validation/inline-structure-construction-baseline.log`.

## Implémentation

`structure_construction.py` normalise les constructeurs contenus après la
résolution des types/features et avant l'inférence des effets, résultats et
contraintes. Les champs deviennent les chemins du layout extérieur. Le type
nominal du constructeur contenu doit correspondre au type déclaré ; une
structure de même forme mais d'un autre nom n'est pas interchangeable.

La normalisation conserve l'ordre écrit, les expressions de champs et leurs
effets. Les défauts manquants sont traités par les vérifications existantes.
Les chemins nommés restent disponibles ; les initialisations qui se recouvrent
sont refusées. Les paramètres Pool<T>, pools locaux et alias nommés sont suivis
lexicalement pour résoudre les constructions `pool.new(...)`.

Les structures contenues ne créent aucun Cell ni slot indépendant. Les champs
références et propriétaires rejoignent le graphe de la seule allocation
extérieure. La préparation et le nettoyage existants s'appliquent aussi si un
champ ultérieur suspend l'exécution avant la construction de l'objet complet.

## Tests ciblés

Huit méthodes, neuf exécutions natives et huit programmes invalides aux deux
entrées, soit seize contrôles de refus :

- Programme enregistré : une seule allocation locale et une seule destruction.
- Ordre écrit différent du layout, défauts récursifs, pool aliasé et slot réutilisé.
- Retour synchrone, copie, emprunts mutables de champs distincts et conflit refusé.
- Champs évalués avec await, retour async local et copie après réception.
- Constructeurs dans un pool injecté depuis des fonctions sync et async.
- Champs partagés contenus, retours sync/async, copie puis destruction du porteur ;
  destruction prématurée de la cible refusée.
- Champ A<Int> contenu préparé avant suspension : nettoyage normal et destruction
  de la tâche suspendue via son ABI, sans objet extérieur partiellement publié.
- Types nominaux incorrects, doublons, champs inconnus et référence sans défaut
  refusés.

## Résultats exécutés et corrections de fixtures

| Passage | Résultat | Journal dans `validation/` |
| --- | --- | --- |
| Ciblé initial O0 | 8 méthodes, 1 échec de fixture, 3,122 s, code 1 | `inline-structure-construction-o0-first.log` |
| Ciblé après correction du nom de variable | 8 méthodes, 3,064 s, code 0 | `inline-structure-construction-o0-second.log` |
| Première régression O2 | 62 méthodes, 1 échec de diagnostic et 3 erreurs historiques, 39,842 s, code 1 | `inline-structure-construction-regression-o2.log` |
| Trois tests historiques avant migration | 3 erreurs reproduites sur le snapshot, 0,013 s, code 1 | `inline-structure-construction-legacy-baseline.log` |
| Fixtures migrées sur le snapshot initial | 3 méthodes, 1,327 s, code 0 | `inline-structure-construction-migrated-fixtures-baseline-final.log` |
| Ciblé final O0 | 8 méthodes, 3,746 s, code 0 | `inline-structure-construction-o0-final.log` |
| Régression finale O2 | 62 méthodes, 41,024 s, code 0 | `inline-structure-construction-regression-o2-final.log` |

Le premier échec utilisait `pool` comme nom de variable, ce qui entre en conflit
avec le builtin lors de l'emprunt. La fixture utilise désormais `items`.
Trois tests historiques utilisaient une annotation T sur une allocation de pool,
incompatible avec V1 et les exigences de stockage actuelles. Leurs annotations
et signatures sont passées à A<T>, sans changer les assertions d'ordre, d'adresse,
de réemploi, de nettoyage ou de refus. Ils passent sur l'ancien compilateur aussi.
Un diagnostic attendu pour un sous-champ non constructible est devenu plus précis.

Un premier essai de chargement des fixtures migrées avait repris le fichier du
snapshot à cause de l'ordre des imports ; son journal est conservé séparément
(`inline-structure-construction-migrated-fixtures-baseline.log`). L'essai final
charge explicitement le fichier de tests courant avec le compilateur du snapshot.

Les exécutions natives ciblées utilisent Clang C11/pthread et UBSan fatal.
Aucun test sauté dans les passages finaux. La régression inclut les modèles
existants des pools async ; aucune nouvelle campagne de mutations ni nouveau
modèle indépendant revendiqué. Ce n'est pas la suite complète du dépôt.

## Reproduction et limites

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_inline_structure_construction
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_inline_structure_construction test_async_direct_copy test_async_struct_pools test_async_borrowed_struct_pools test_async_local_owned_result_graphs test_foundation_rules.FoundationTests.test_nested_structure_defaults_are_inline_in_one_slot test_foundation_rules.FoundationTests.test_nested_structure_named_paths_initialize_inline_in_written_order test_foundation_rules.FoundationTests.test_direct_recursive_structure_layout_is_rejected test_foundation_rules.FoundationTests.test_struct_pool_defaults_order_and_reuse test_foundation_rules.FoundationTests.test_struct_pool_reference_survives_return_and_checks_initializer_effects test_foundation_rules.FoundationTests.test_structure_methods_share_names_with_expression_builtins
```

Snapshot : `/tmp/crust-before-inline-structure-construction/` ; patches des
fichiers modifiés dans `validation/inline-structure-construction-*.py.patch`.

Ce lot raccorde les littéraux contenus, pas l'insertion d'une structure nommée
ou calculée dans un champ inline. Il ne définit pas de déplacement d'une
allocation stable dans une autre. Les emprunts de sous-structures entières
restent à compléter. Les résultats portent sur les layouts déjà représentables,
pas sur une garantie générale pour tous les types et combinaisons.
