[English](TYPED_ASYNC_HANDLE_VECTORS_CYCLE.md)

# Cycle — Vecteurs de handles typés dans les états async

## Règles et portée

Application de H1–H3, VE1–VE4, F2–F4, U1, B1–B5 et des règles de capture,
suspension et nettoyage AS2/AS8–AS14, sans modification normative. AGENTS.md,
VALIDATION_GUIDELINES.md, l'index des brouillons et les règles normatives ont été
consultés dans cette session. La consigne de se concentrer sur les cas retenus et
les régressions directes reste appliquée.

Ce lot raccorde les conteneurs typés et leurs résultats locaux dans une tâche.
Il ne clôt pas le chantier des signatures `Option<A<T>>` async :
`validation/open-typed-async-vector-option.crust/.log` reste refusé par le parseur
pour T non Int. Le retour de ces options depuis la tâche, les enveloppes de join
et les paramètres correspondants sont la suite explicite du travail.

## Implémentation

`async_lowering.py` utilise le type des éléments du vecteur pour les captures,
pools injectés/locaux, appels synchrones, push, remove, pop local et replace
local. Le type de la charge est conservé après extraction de Some/Ok/Err et
suspension. Les annotations locales Option/Result sont vérifiées même lorsque
la charge peut être absente. Les formes numériques Int antérieures restent
prises en charge.

Les vecteurs créés dans l'état appellent `vector_new_handles`. La disposition
reste celle de cases Cell* ; le runtime existant assure la destruction des
éléments auprès de leurs pools d'origine. Aucun déplacement de cible, aucune
conversion implicite et aucun nouveau runtime de conteneur ne sont introduits.

Les charges à champs propriétaires/empruntés restent explicitement refusées
comme dans la voie synchrone : leurs dépendances transitives ne sont pas encore
raccordées. Ce refus est une limite d'implémentation, pas une nouvelle règle.
Il s'applique aussi aux paramètres async et aux pools créés dans un état.

## Défauts rencontrés et corrigés

1. La première émission de construction utilisait le constructeur numérique,
   dont le paramètre testé était le sens de croissance et non la propriété des
   handles. Le vecteur ne détruisait donc pas l'élément restant. Le scénario de
   réemploi échouait avec `pool capacity exceeded`. L'appel au constructeur de
   handles corrige le nettoyage ; les quatre Point du scénario sont détruits.
2. Après généralisation du conteneur, le contrôle de replace conservait Int
   en dur. Le programme
   `validation/typed-async-handle-vectors-wrong-replace.crust` insérait un
   A<Int> dans Vector<A<Point>> et était accepté aux deux entrées. Il n'a pas
   été exécuté en natif. Les journaux before/after conservent l'acceptation puis
   le refus `allocation Point`. Le contrôle et le résultat utilisent maintenant
   le type réel de l'élément.
3. Un échantillon de charge grandissante réutilisait un nom déjà déclaré dans
   l'état async ; il a été renommé pour rester dans le périmètre existant. La
   généralisation du masquage dans les états async n'est pas revendiquée ici.

## Scénarios exécutés

`tests/test_typed_async_handle_vectors.py` contient neuf méthodes : seize
programmes natifs admis et dix-sept invalides contrôlés par les deux entrées.

- Capture partagée, mutable ou transférée ; lecture de longueur et nettoyage.
- Push/remove avec yield et relais synchrone ; transfert explicite requis,
  type incorrect et valeur locale non allouée refusés.
- Pools locaux, deux pools d'éléments, destruction de l'élément extrait et du
  restant, réemploi des deux slots.
- Some/None typés conservés autour de yield, appel synchrone retournant l'option,
  mauvais type d'annotation refusé même sur None.
- Destruction d'une tâche encore inactive : corps non exécuté, vecteur et
  contenu nettoyés, source transférée inutilisable.
- Charges String UTF-8, Vector<Int> et Vector<u8> extraites et lues après yield.
- Replace avec index valide ou invalide, annotation Result typée, nettoyage des
  deux pools et des deux variantes.
- Refus explicite des dépendances de champs non encore raccordées.

Le C du scénario de nettoyage est conservé dans
`validation/typed-async-handle-vectors-cleanup.c`, avec son source `.crust`.

## Exécutions et preuves

- Première exécution push/remove : code 0,
  `validation/typed-async-handle-vectors-first-o0.log`.
- Première option locale typée : code 0,
  `validation/typed-async-handle-vectors-local-pop-o0.log`.
- Premier ciblé O0 : cinq méthodes, 4,440 s, code 1 ; défaut de nettoyage.
  `validation/typed-async-handle-vectors-targeted-o0.log`.
- Deuxième ciblé O0 : cinq méthodes, 4,954 s, code 0.
  `validation/typed-async-handle-vectors-targeted-second-o0.log`.
- Troisième ciblé O0 : six méthodes, 4,462 s, code 1 ; nom réutilisé dans
  l'échantillon. `validation/typed-async-handle-vectors-targeted-third-o0.log`.
- Quatrième ciblé O0 : six méthodes, 5,988 s, code 0.
  `validation/typed-async-handle-vectors-targeted-fourth-o0.log`.
- Première régression O2 : 82 méthodes, 79,791 s, code 0, avant les derniers
  contrôles de replace et de charges complexes.
  `validation/typed-async-handle-vectors-regression-o2.log`.
- Ciblé final O0 : neuf méthodes, 7,286 s, code 0.
  `validation/typed-async-handle-vectors-targeted-final-o0.log`.
- Régression finale O2 : 84 méthodes, 80,216 s, code 0.
  `validation/typed-async-handle-vectors-regression-final-o2.log`.
  Sélection : typed_async_handle_vectors, typed_handle_vectors,
  typed_vector_options, async_handle_vector_push/remove/pop,
  async_handle_option_calls/results, async_handle_vector_replace/try_push et
  strict_structure_returns (modules test_ correspondants).

Les tests passent par verify_program et compile_source puis C11/pthread,
Wall/Wextra/Werror et UBSan fatal. Les traces, les sorties et la capacité à
réutiliser les pools servent d'oracles explicites. Aucun nouveau modèle,
générateur ou campagne de mutations n'est ajouté ; les régressions existantes
restent exécutées. Leurs succès ne constituent pas une preuve générale.

## Artefacts et limites restantes

Snapshot initial : `/tmp/crust-before-typed-async-handle-vectors`.
Deux diffs exacts et manifeste d'empreintes :
`validation/typed-async-handle-vectors-*.patch` et
`validation/typed-async-handle-vectors-changes.json`.

Restent notamment : paramètres/retours async d'options et de résultats typés,
leurs enveloppes de join, charges contenant des emprunts ou des allocations,
généralisation des emprunts de cases/cibles typées au-delà des parcours déjà
raccordés. Les autres points de la checklist globale sont conservés. Le runtime
n'est pas déclaré sûr pour toutes les compositions et l'objectif global reste
actif.

Commande de régression finale :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_typed_async_handle_vectors test_typed_handle_vectors test_typed_vector_options test_async_handle_vector_push test_async_handle_vector_remove test_async_handle_vector_pop test_async_handle_option_calls test_async_handle_option_results test_async_handle_vector_replace test_async_handle_vector_try_push test_strict_structure_returns -v
```
