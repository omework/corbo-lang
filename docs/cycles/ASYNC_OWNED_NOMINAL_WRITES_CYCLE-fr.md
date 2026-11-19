[English](ASYNC_OWNED_NOMINAL_WRITES_CYCLE.md)

# Remplacements de descendants à références nominales

## Règles et périmètre

Extension du raccordement de AS12/AS16 et SL1 aux descendants A<T> qui
contiennent &Point ou &mut Point. Les règles de remplacement, de durée de vie,
d’exclusivité et de dernière utilisation restent inchangées. Une nouvelle
allocation est préparée avant la destruction du descendant remplacé. La cible
simplement empruntée n’est pas détruite avec lui.

Les tests prolongent les cas déjà énumérés du lot
[des descendants à références Int](ASYNC_OWNED_BORROW_WRITES_CYCLE.md).
Aucun nouvel arbitrage ni règle normative.

## Changements

- Le filtre de signatures propriétaires accepte les descendants contenant des
  références nominales dont le graphe de paramètres est déjà représenté et
  acyclique. Les cycles de références ne sont pas autorisés par ce changement.
- L’application des effets de champs dans un état async reconnaît les chemins
  de sous-structures contenues à partir du layout. Elle conserve la provenance
  `(racine, chemin)` et vérifie le type du sous-objet ; elle ne confond plus
  ce chemin avec un champ qui contiendrait lui-même une référence.
- Le reste utilise les descripteurs et les contrats existants : cibles anciennes
  et nouvelles lors d’un remplacement conditionnel ou d’un lancement faillible,
  effets suspendus de Select et contrôles aux sorties de scopes.

## Cas et résultats

Six méthodes dans `tests/test_async_owned_nominal_writes.py` : neuf exécutions
natives admises, dont une avec échec de soumission injecté, et douze programmes
invalides contrôlés par `verify_program` et `compile_source`.

- Remplacement direct et via auxiliaire, puis await : lecture de la nouvelle
  cible et mutation autorisée après destruction du porteur.
- Join normal et échec de lancement : respectivement nouvelle et ancienne
  cible ; toutes les cibles possibles restent protégées avant lecture.
- Perdante suspendue de Select : le remplacement effectué avant yield reste
  visible après nettoyage de la sélection.
- Référence mutable : remplacement direct et via auxiliaire, lecture par
  réemprunt et écriture prématurée de la cible refusée.
- Remplacement conditionnel : les deux branches sont exécutées et les deux
  cibles possibles restent suivies statiquement.
- Sous-structure d’un bloc enfant : refus si le porteur survivant la référence
  encore après sa destruction.

Les sorties attendues sont écrites dans les tests indépendamment du code C.
Compilation Clang C11/pthread, warnings en erreurs, UBSan sans récupération.

| Journal dans validation/ | Résultat |
| --- | --- |
| async-owned-nominal-writes-first-o0.log | 3 méthodes, 3 échecs : filtre de signature propriétaire |
| async-owned-nominal-writes-second-o0.log | 3 méthodes, 2 échecs : provenance intérieure locale non reconnue |
| async-owned-nominal-writes-third-o0.log | 3 méthodes, 2,788 s, code 0 |
| async-owned-nominal-writes-fourth-o0.log | 6 méthodes, 4,079 s, code 0 |
| async-owned-nominal-writes-regression-o2.log | 101 méthodes, 82,937 s, code 0 |

Commande de régression :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_owned_nominal_writes test_async_owned_borrow_writes test_async_owned_field_writes test_async_stored_views test_async_enum_nominal test_nested_field_wrappers test_nested_field_choices test_async_owned_struct_sync_calls test_public_structure_handles test_inline_owned_views -v
```

## Limites

Ce lot ne prouve pas toutes les compositions de graphes ni tous les
entrelacements. Les graphes récursifs et les signatures non représentées
restent distincts. Pas de nouvelle campagne de mutations, de génération
adversariale ou de nouveau modèle indépendant ; l’audit ultérieur n’est pas
réputé effectué. Reset reste retiré par défaut. L’objectif global reste actif.

Snapshot : `/tmp/crust-before-async-owned-nominal-writes/` ; patches des deux
modules sous `validation/async-owned-nominal-writes-*.py.patch`.
