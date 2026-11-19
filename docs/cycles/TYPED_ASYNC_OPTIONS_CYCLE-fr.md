[English](TYPED_ASYNC_OPTIONS_CYCLE.md)

# Cycle — Options d’allocations typées en async

## Règles et portée

Application des règles H1, VE1–VE3, F2–F4, U1, B1–B5, AS2/AS8–AS14 et MT5–MT6.
Les documents normatifs restent inchangés. AGENTS.md, VALIDATION_GUIDELINES.md,
l’index des décisions et les règles concernées ont été consultés ; le périmètre
reste l’implémentation des cas retenus et de leurs régressions directes.

Le lot raccorde Option<A<T>> aux paramètres et résultats async, aux attentes
inactives et lancées, aux enveloppes Result imbriquées et aux handles publics.
Les types exercés sont Point, Int, String, Vector<Int> et Vector<u8>. Les charges
contenant elles-mêmes des emprunts ou des allocations restent un chantier ouvert.

## Implémentation

- Le registre des enveloppes d’options distingue statiquement chaque type de
  charge, avec des identifiants injectifs dérivés de son orthographe UTF-8.
  Les enveloppes partagent la représentation C existante : statut et Cell*.
- Le parseur, les contrats de résultats et de contraintes, les effets async,
  les handles publics et l’abaissement conservent le type jusqu’à l’extraction
  finale. Le nettoyage teste les statuts de chaque enveloppe et de Some/None.
- Les variantes possibles d’un élément extrait d’un vecteur sont celles de
  son type lorsque le conteneur ne fournit pas de précision par variante.
  Une provenance de tâche garde ses variantes connues, sinon l’ensemble du
  type. Le contrôle de conformité du résultat à son contrat reste en place.
- Le runtime de pool n’est pas modifié. Les transferts copient le descripteur
  de résultat et son pointeur, sans déplacer la cible de l’allocation.

## Défauts rencontrés et corrigés

1. Le parseur refusait explicitement les signatures Option<A<T>> non Int.
   Le cas enregistré `validation/open-typed-async-vector-option.crust` est
   maintenant accepté aux deux entrées et exécuté avec sorties 7 puis 9.
2. Après raccordement initial, les contrats de join et les effets de champs
   async produisaient encore l’identifiant de l’option Int. Les retours
   imbriqués perdaient leurs provenances ; le C émettait à tort le diagnostic
   « pop de handle : aucun élément possible » sur Some(Point).
   Le programme et le C avant correction sont conservés dans
   `validation/typed-async-options-nested-before.crust/.c`.
3. Le relais d’un handle public conservait la source, mais omettait les
   variantes de la charge provenant du vecteur. Le contrôle interne détectait
   « variante absente du contrat de résultat ». Le cas minimal est dans
   `validation/typed-async-options-public-before.crust` ; les tests de handles
   publics le couvrent après correction.
4. Une édition de lisibilité a momentanément produit une erreur Python à
   l’import ; elle est consignée dans `typed-async-options-refactor-import-error.log`.
   Elle a été corrigée avant les passes finales. La branche des résultats
   propriétaires ordinaires conserve également son enveloppe d’origine.

## Cas exécutés

Huit méthodes ciblées : 26 exécutions C, dont huit avec échec de soumission
injecté, et 17 programmes invalides contrôlés à la vérification et à la
compilation. Dix-huit programmes admis passent les deux entrées avant exécution ;
les huit injections partent du C compilé et simulent LaunchFailed.

- Some/None aux profondeurs de join 1 et 3, avec réemploi du pool de capacité 1.
- Attente nommée, fabrique synchrone, capture puis restitution de l’option,
  annotation typée et relais synchrone.
- Handle public, relais d’enveloppe, capture async puis extraction après await.
- Échec de lancement à chacun des trois niveaux ; destruction unique puis
  allocation de remplacement dans le pool d’origine.
- Drop d’une tâche inactive et échec de son lancement : capture détruite,
  corps non exécuté dans le cas inactif.
- Résultat survivant au vecteur, mais transfert refusé si le pool de la
  charge ne survit pas ; accès prématuré au vecteur refusé avant join.
- Types incorrects refusés même pour None ; transferts absents, double usage
  et résultat ignoré refusés. Options Int et Point coexistantes dans un programme.
- Charges String UTF-8 et vecteurs numériques transférées dans des options,
  attendues, extraites et lues après suspension.

Le C final de trois enveloppes est conservé dans
`validation/typed-async-options-nested.crust/.c` : restitution des descripteurs
`frame->result`, `task_async_take_into` puis extraction du pointeur de Some.
Le marqueur d’échec artificiel du C avant correction n’est plus présent.

## Exécutions

- Cas enregistré initial : code 0 ; log `typed-async-options-first-o0.log`.
  Malgré son nom, cette commande n’avait pas CRUST_TEST_OPT et utilise donc
  **O2**, valeur par défaut du harness.
- Ciblés intermédiaires O0 : 7 méthodes, 8,983 s puis 8,741 s, code 1,
  trois échecs ; troisième passe 9,356 s, code 1, un échec de variante.
- Quatrième ciblé O0 : 7 méthodes, 10,778 s, code 0.
- Ciblé final O0 : 8 méthodes, 11,610 s, code 0,
  `validation/typed-async-options-targeted-final-o0.log`.
- Cinquième ciblé O0 : 8 méthodes, 11,547 s, code 0 ; avant la dernière
  conservation explicite de la branche des résultats propriétaires ordinaires.
- Régression finale O2 : 119 méthodes, 163,268 s, code 0,
  `validation/typed-async-options-regression-o2.log`.

Les noms des suites de régression sont dans
`validation/typed-async-options-test-selection.txt`. Reproduction :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_typed_async_options -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_typed_async_options test_typed_async_handle_vectors test_typed_vector_options test_async_handle_option_results test_async_handle_option_calls test_async_option_join test_async_nested_option_join test_async_nested_exchange_join test_recursive_owned_join test_public_handle_contracts test_public_handle_types test_async_child_field_effects test_strict_structure_returns test_typed_vector_exchanges -v
```

Le harness compile en C11/pthread avec Wall/Wextra/Werror et UBSan fatal
(`-fsanitize=undefined -fno-sanitize-recover=all`). Les valeurs attendues et
les destructions sont vérifiées par les tests ; aucun résultat n’est déduit
uniquement de l’acceptation du compilateur.

## Traçabilité et limites

Snapshot initial : `/tmp/crust-before-typed-async-options`. Sept fichiers du
compilateur modifiés et une nouvelle suite ; diffs exacts et empreintes dans
`validation/typed-async-options-changes.json`. Les logs intermédiaires restent
conservés. Le modèle indépendant de rétention imbriquée existant a été rejoué dans la
régression : sept programmes admis exécutés et cinq refus attendus. Aucun modèle
n’a été modifié ; aucune campagne de
mutations ou de recherche adversariale approfondie n’a été lancée. Les
injections LaunchFailed exercent les chemins d’échec déjà définis.

La suite ne prouve ni la sûreté générale ni tous les ordonnancements. Les
signatures async des échanges replace/try_push typés restent ouvertes :
`validation/open-typed-async-vector-exchange.crust/.log` enregistre le refus
explicite aux deux entrées du prochain cas. Restent également à traiter
les dépendances transitives des charges, les autres compositions générales
et les chantiers indiqués dans IMPLEMENTATION_CHECKLIST.md. Reset reste retiré
par défaut ; ce lot n’en réintroduit aucun usage. L’objectif global reste actif.
