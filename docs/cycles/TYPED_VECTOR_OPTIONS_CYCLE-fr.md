[English](TYPED_VECTOR_OPTIONS_CYCLE.md)

# Contrats synchrones Option<A<T>>

## Règles et réalisation

Ce lot applique VE3, H1–H3, U1, B1–B5 et F3–F4 aux options de handles
retournées par pop. Aucune règle normative n'est modifiée.

`handle_option_types.py` décrit le type public Option<A<T>> et sa charge T.
Le parseur, les paramètres et résultats de fonctions, les annotations, les
jonctions if/loop et les appels conservent maintenant T au lieu de supposer Int.
Le type de pool d'une charge symbolique est fixé par la signature.

Une option vide conserve désormais un descripteur typé dans le compilateur,
avec une preuve d'absence de charge et aucune source/identité d'allocation.
Ce descripteur est une métadonnée de vérification ; il n'alloue aucun objet dans
le programme généré. Le C conserve son VectorHandleResult et son indicateur de
présence. Some absent est un chemin inaccessible ; drop ne détruit que la charge
présente. Ainsi, None de type Option<A<Point>> n'est pas interchangeable avec
None de type Option<A<Int>>.

Les exigences de stockage savent qu'un paramètre Option<A<T>> contient, le cas
échéant, un handle de pool. Le relais d'une option conserve aussi le contrat de
variantes de sa charge nominale. Les signatures async nouvellement typées restent
refusées explicitement en attendant leur raccordement aux enveloppes runtime.

## Cas exécutés

Huit méthodes dans `tests/test_typed_vector_options.py` : 21 exécutions natives
et onze programmes invalides contrôlés chacun par verify_program et compile_source.

- Some et None, annotations, résultat nommé puis transféré à un relais.
- None conserve son type dans un argument de fonction ; un mauvais type est refusé.
- Options issues d'un if ou d'un loop/break, présentes ou vides ; jonction de
  deux types de charges incompatibles refusée même pour deux options vides.
- L'option survit au pool du vecteur vidé, mais ne peut emporter une charge dont
  le pool se termine avant elle. Une option vide n'invente pas cette dépendance.
- Consommateur de paramètre Option<A<Point>> restituant le handle de Some ou une
  allocation de remplacement en cas de None.
- Annotation locale Point d'une charge A<Point> refusée.
- Destruction directe, résultat nommé/déplacé, nettoyage et réemploi à capacité un.
- Résultat sans usage, double consommation, motif ignorant la charge et absence
  de transfert à un paramètre refusés.
- Emprunt de case utilisé avant pop admis ; usage restant après pop refusé.
- String, Vector<Int> et Vector<u8> traversent le contrat, sont lus puis détruits,
  avant réemploi des slots de leurs pools.

Le harness utilise C11/pthread, Wall/Wextra/Werror, UBSan et
`-fno-sanitize-recover=all`. Le code de sortie de chaque exécution est contrôlé.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_typed_vector_options -v
```

`validation/typed-vector-options-targeted-third-o0.log` : huit méthodes,
7,113 s, code 0.

## Régressions

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
 test_typed_vector_options test_typed_handle_vectors test_typed_vector_exchanges \
 test_storage_requirements test_async_handle_vector_pop \
 test_async_handle_option_calls test_async_handle_option_results \
 test_async_option_join test_async_nested_option_join test_async_failure_only_results \
 test_foundation_rules.FoundationTests.test_buffered_handle_pop_passes_statically_empty_option_from_function \
 test_foundation_rules.FoundationTests.test_buffered_handle_pop_moves_across_explicit_scope_entries \
 test_foundation_rules.FoundationTests.test_buffered_handle_pop_survives_break_and_cleans_continue -v
```

`validation/typed-vector-options-regression-o2.log` : 87 méthodes, 100,393 s,
code 0. Les suites utilisent O2/UBSan ; les trois méthodes Foundation emploient
leur configuration O2/UBSan native et le profil legacy-reset explicite.
Les régressions incluent les options Int vides, les résultats async sans charge,
les enveloppes imbriquées et les nettoyages des branches perdantes déjà testés.
Elles ne prouvent pas l'intégration async des nouvelles charges typées.

## Traces et limites

Le refus initial est conservé dans
`validation/open-typed-vector-option-contract.crust/.log`. Le C désormais
produit est `validation/typed-vector-option-point.c`.

- `typed-vector-options-first-o0.log` : le programme initial s'exécute.
- `targeted-o0` : un relais Option<A<Point>> perdait le contrat de variantes
  de sa charge ; l'invariant du backend le signalait. Résolution de ce contrat
  étendue aux options, sans suppression de l'invariant.
- `targeted-second-o0` : sept méthodes, 7,211 s, code 0.
- `targeted-third-o0` : ajout du cas d'emprunt et du transfert d'argument,
  huit méthodes, code 0.

Les différences avec la sauvegarde avant ce lot sont archivées dans
`validation/typed-vector-options-*.patch`.

Les charges contenant elles-mêmes des références ou allocations, les enums
généraux et les signatures/enveloppes async typées restent à compléter.
L'écart des anciennes signatures de retour T acceptant A<T>, documenté dans
TYPED_VECTOR_EXCHANGES_CYCLE.md, reste ouvert : le refus d'une annotation locale
ne prouve pas le contrôle de toutes les signatures.

Aucune campagne adversariale approfondie, mutation ou génération aléatoire
nouvelle n'a été lancée. Les modèles déjà présents dans les suites sélectionnées
restent exécutés avec elles. Le chantier global n'est pas terminé et ces tests
ne constituent pas une preuve générale de sûreté.
