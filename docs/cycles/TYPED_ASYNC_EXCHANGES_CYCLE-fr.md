[English](TYPED_ASYNC_EXCHANGES_CYCLE.md)

# Cycle — Résultats async typés de replace et try_push

## Règles et portée

Application de H1–H3, VE1–VE4, F2–F4, U1, B1–B5, AS2/AS8–AS14, MT5–MT6
et des règles de nettoyage des perdantes de Select. Les documents normatifs
restent inchangés. AGENTS.md, VALIDATION_GUIDELINES.md, l’index des décisions
et les règles concernées ont été lus dans cette session. Le périmètre reste
celui des fonctionnalités retenues et de leurs régressions directes.

Ce lot raccorde les signatures async Result<A<T>,A<T>> et Result<(),A<T>>,
leurs captures et leurs enveloppes de runtime. Il prolonge les échanges
synchrones et locaux à une tâche déjà implémentés. Les charges exercées sont
Point, String, Vector<Int> et Vector<u8>, avec régression du parcours Int.
Les éléments contenant des dépendances transitives restent un chantier ouvert.

## Implémentation

- Le registre des échanges distingue le type de charge et la forme de résultat
  à chaque profondeur. L’ABI C reste partagée : statuts et pointeur Cell*.
- Parseur, contrats, effets async, handles publics et abaissement conservent
  le type réel et les provenances de chaque branche. Les retours et paramètres
  n’assimilent plus les charges à Int.
- L’analyse des exigences de stockage conserve désormais les charges d’un
  échange après await, directement ou à travers un handle. Elle reçoit les
  sources du contrat ; elle ne promeut pas de valeur locale dans un pool.
- Le nettoyage du résultat de try_push dépend de sa variante : Ok(()) ne
  détruit pas l’allocation placée dans le vecteur ; Err conserve et nettoie
  l’entrante. Ce contrôle est utilisé pour les arguments préparés, les
  captures, les tâches inactives, les attentes et les perdantes de Select.
- Une charge d’échange sans précision par variante nominale conserve les
  variantes possibles de son type. Le contrôle interne du contrat reste actif.

Aucune modification des allocateurs/pools du runtime et aucun déplacement de
la cible des allocations ne sont introduits.

## Défauts rencontrés

1. Le refus explicite des signatures async typées empêchait le programme
   `validation/open-typed-async-vector-exchange.crust`. Il est maintenant
   accepté aux deux entrées et exécuté : 7, 8, 9.
2. L’analyse des exigences de stockage produisait une valeur sans charge après
   await. Les relais valides étaient rejetés avec « attend une allocation » ou
   « exige un résultat de replace ou try_push ». Le descripteur de résultat et
   ses sources par branche sont maintenant propagés dans cette analyse.
3. Un relais de résultat enveloppé conservait la provenance de l’échange mais
   pas les variantes possibles de Point. Le contrôle interne signalait
   « variante absente du contrat de résultat ». L’information de type est
   conservée sans retirer ce contrôle.

Les premiers journaux en échec sont conservés. La deuxième tentative a été
interrompue après l’échec d’une assertion du script d’édition, avant application
du correctif ; elle ne compte pas comme validation. Les deux modèles existants
inclus dans la régression sont rejoués sans modification : quatre combinaisons
de stockage de deux paramètres (quatre admis et quatre refus), et 36 cas de
permissions de capture (18 admis et 18 refus). Ils ne modélisent pas à eux seuls
les nouveaux résultats d’échange.

## Scénarios ciblés

Neuf méthodes, 26 exécutions C dont cinq avec LaunchFailed injecté, et quinze
programmes invalides contrôlés par verify_program et compile_source. Les
21 exécutions sans injection passent les deux entrées avant génération/exécution
C ; les cinq injections partent du C compilé et simulent un échec du scheduler.

- Replace avec index valide ou invalide, pools d’origine distincts et profondeurs
  de join 1/3 : ancien élément ou entrante restitués, élément résident lu,
  quatre destructions Point et réemploi des deux pools.
- Attente inactive nommée, fabrique synchrone, relais sync/async, annotation
  exacte du résultat et erreurs de type/transfert refusées.
- Handles publics, trois enveloppes, capture/restitution/extraction après await.
- Échec de lancement à chaque niveau ; l’entrante est nettoyée, le vecteur garde
  son ancien élément, les deux pools sont réutilisables.
- Capture de chacune des branches du résultat, drop inactif et LaunchFailed :
  aucun corps exécuté en cas inactif, nettoyage unique de la charge reçue.
- Try_push accepté ou refusé sur une région de 1 MiB effectivement pleine ;
  l’élément accepté reste dans le vecteur, le rejeté reste dans Err.
- Capture de ces deux variantes dans une tâche inactive ou une perdante de
  Select suspendue : nettoyage conforme à la présence effective de la charge.
- Charges String UTF-8 et vecteurs numériques lues après transferts et suspensions.
- Sources trop courtes, accès au vecteur avant join, usage après transfert,
  résultat ignoré et double consommation refusés.

Le source et le C de trois enveloppes sont conservés dans
`validation/typed-async-exchanges-nested.crust/.c`. Les statuts guident les
extractions et nettoyages ; la valeur transférée reste le pointeur Cell*.

## Preuves d’exécution

- Premier programme enregistré O0 : code 0,
  `validation/typed-async-exchanges-first-o0.log`.
- Premier ciblé O0 : huit méthodes, 7,557 s, code 1, trois échecs.
- Deuxième tentative : interrompue, code 130, pas une validation.
- Troisième ciblé O0 : huit méthodes, 9,285 s, code 1, un échec de variantes.
- Quatrième ciblé O0 : huit méthodes, 10,419 s, code 0.
- Ciblé final O0 : neuf méthodes, 12,541 s, code 0,
  `validation/typed-async-exchanges-targeted-final-o0.log`.
- Régression finale O2 : 135 méthodes, 183,427 s, code 0,
  `validation/typed-async-exchanges-regression-o2.log`.

Sélection exacte : `validation/typed-async-exchanges-test-selection.txt`.
Reproduction :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_typed_async_exchanges -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_typed_async_exchanges test_typed_async_options test_typed_async_handle_vectors test_typed_vector_exchanges test_typed_vector_options test_async_handle_exchange_calls test_async_handle_exchange_results test_async_handle_vector_try_push test_async_exchange_join test_async_nested_exchange_join test_async_nested_option_join test_recursive_owned_join test_public_handle_contracts test_storage_requirements test_strict_structure_returns -v
```

Le harness compile en C11/pthread, Wall/Wextra/Werror et UBSan fatal
(`-fsanitize=undefined -fno-sanitize-recover=all`). Les tests vérifient des
valeurs attendues et des destructions, pas seulement l’acceptation du source.
Les passes ciblées ne constituent pas une preuve générale de sûreté.

## Traçabilité et suite

Snapshot : `/tmp/crust-before-typed-async-exchanges`. Huit fichiers du compilateur
et une nouvelle suite ; diffs exacts et empreintes dans
`validation/typed-async-exchanges-changes.json`. Aucun modèle de référence
modifié ; aucune campagne de mutations ou d’exploration adversariale approfondie.
Les injections du scheduler exercent les chemins d’échec déjà définis.

Les dépendances transitives des éléments de vecteur, les autres types et
compositions non encore raccordés restent ouverts. Le prochain cas enregistré,
`validation/open-vector-handle-borrowed-fields.crust/.log`, est encore refusé
explicitement aux deux entrées : il stocke une allocation Item contenant &Int
puis la retire et utilise sa référence avant les destructions. Les champs
propriétaires constituent l’autre partie de ce chantier.

Reset demeure retiré par défaut. Les interfaces publiques du scheduler et de
construction des mutex restent à arbitrer. L’objectif global n’est pas terminé.
