[English](NATIVE_SYNC_CALLS_CYCLE.md)

# Cycle — appels synchrones depuis les états natifs et async

Suite : [paramètres et résultats empruntés](SYNC_BORROW_CALLS_CYCLE.md).
Les limitations ci-dessous décrivent ce premier lot scalaire ; les emprunts
Int et mutables u8 sont désormais raccordés dans le cycle suivant.

## Règles et périmètre

Ce cycle poursuit RT8, B4/B4a/B4e, RT5, AS7 et L1/L2/L6 sans changer
les règles normatives. AGENTS.md, VALIDATION_GUIDELINES.md, l’index des sept
brouillons, LANGUAGE_RULES.md et l’extension async ont été consultés.

Le contre-exemple `validation/open-native-sync-helper.crust` est maintenant
accepté et exécuté : le bloc natif appelle add(7), puis join fournit 8.
La nouvelle frontière couvre les paramètres et résultats Int/u8/char et le
résultat Void. Les fonctions appelées peuvent utiliser leur code synchrone
habituel : autres appels, pools locaux, emprunts, drop, méthodes, créations
de tâches et join quand le contexte l’autorise. Les références et valeurs
propriétaires ne traversent pas encore cette nouvelle frontière d’appel.

L’appel n’alloue pas de tâche intermédiaire. Le C appelle une fonction
synchrone ordinaire ; ses ressources locales sont nettoyées avant son retour.
Les paramètres sont évalués et mémorisés de gauche à droite avant l’appel C.
Un return pendant la préparation d’un argument quitte l’appelant et empêche
l’appel extérieur. Un Int nommé ne devient pas implicitement u8.

## Contrats et traduction

La collecte des fonctions précède désormais la génération des états.
Les provenances des résultats empruntés async sont calculées avant les
vérifications des appelants. La génération des états conserve sa validation
avant celle des corps synchrones pour diagnostiquer les corps invalides
eux-mêmes, et pas seulement leurs conséquences chez l’appelant.

L’appel depuis un état utilise FunctionContract. Il réserve un symbole C
sans ouvrir le corps du callee. La vérification symbolique de chaque fonction
conserve ses appels opaques. Le backend spécialisé produit l’auxiliaire
une fois par fonction appelée, après verify, dans Compiler.compile. Un test
interdit explicitement ce backend pendant verify_program et vérifie qu’add,
relay et main sont chacun visités une fois, sans pile d’appel imbriquée.

FunctionEffects transmet l’effet blocking_join à travers les appels et les
méthodes résolues. Un état async refuse un auxiliaire portant cet effet ;
un bloc natif l’autorise. Créer puis détruire une tâche inactive ne constitue
pas un join. Les appels sont toujours non suspendables.

FunctionContract conserve aussi une borne conservative synchronous_task_slots,
obtenue depuis les emplacements du corps vérifié et les contrats des sous-appels.
Ces bornes contribuent à chaque instance d’état appelante. Le graphe de création
inclut les appels synchrones intermédiaires ; pour les méthodes, il inclut
conservativement les implémentations de même nom. Les cycles ainsi révélés
exigent une capacité explicite. Cette approximation peut surestimer le stockage
et réclamer une configuration supplémentaire ; ce n’est pas une borne optimale.

## Scénarios et recherche de contre-exemples

`tests/test_native_sync_calls.py` contient douze méthodes : quatorze exécutions
Crust/C et dix-sept refus attendus par passage complet, plus les observations
des contrats, capacités et visites de corps.

- Appels imbriqués et Void : traces 1, 2, 30, 12, 14 dans les appelants natif
  et async. Deux allocations locales sont détruites exactement une fois,
  avec les valeurs 12 puis 13 ; le pool de capacité un est réutilisé.
- Un auxiliaire appelle read(&Int), copie le résultat puis détruit l’allocation.
  Le drop avant la dernière lecture, la lecture après drop et reset public
  sont refusés.
- u8 et char sont transmis sans confusion avec Int ; erreurs de type, d’arité,
  d’emprunt et de dépassement du littéral u8 sont refusées.
- Une cible capturée par emprunt reste protégée chez l’appelant pendant
  l’exécution native, bien que l’auxiliaire ne reçoive qu’une copie de sa valeur.
- Join derrière deux auxiliaires : succès, échec du lancement enfant et échec
  du lancement natif ; refus depuis un état async et refus de l’abandon du handle.
- Huit parents peuvent chacun retenir trois enfants. La capacité inférée doit
  couvrir au moins vingt-quatre enfants ; les huit résultats sont exécutés.
  Le test de capacité ne prétend pas imposer un ordonnancement où les vingt-quatre
  enfants sont effectivement simultanément alloués.
- Cycle de création à travers une fonction, puis à travers une méthode locale :
  refus sans configuration et exécution avec deux slots explicitement configurés.
- Retour pendant un argument : trace 1 puis 7, sans exécuter le corps de pair.

Les oracles sont les traces, types, obligations de durée de vie et bornes
d’occupation dérivés des règles. Il n’y a pas de générateur aléatoire ajouté
ni de nouveau modèle général de concurrence. Les suites de contrats et de
runtime existantes restent nécessaires ; les seuls tests de ce module ne
prouvent pas la sûreté de toutes les interactions.

## Défauts intermédiaires et mutations

La première régression a trouvé des KeyError sur les provenances de références
async : elles étaient lues avant leur calcul. Leur calcul préalable corrige
ces erreurs. Déplacer la vérification des corps synchrones avant celle des
états changeait aussi le diagnostic d’une tranche non durable ; l’ordre final
diagnostique de nouveau le corps async fautif sans modifier le test.
Les journaux intermédiaires sont conservés, notamment native-sync-regression-o2.log
et native-sync-regression-o2-final.log ; malgré son nom, ce dernier contient
encore cet échec de diagnostic et n’est pas la validation finale.

Les mutations utilisent des copies temporaires du compilateur, sans modifier
les tests : ordre des arguments inversé, join caché accepté depuis async,
arêtes de création indirecte omises, contribution des slots auxiliaires omise.
Les trois premières ont été détectées au premier passage. La quatrième a
survécu au cas initial de deux parents : d’autres surévaluations masquaient
la sous-estimation. Le cas à huit parents détecte désormais une capacité de
six au lieu du minimum requis de vingt-quatre. Le journal initial et celui
du renfort sont conservés ; aucun taux général de détection n’est revendiqué.

## Résultats exécutés

| Journal dans validation/ | Résultat |
| --- | --- |
| native-sync-initial.log | Trois premières sondes : 8, 9 avec destructions 7/8, puis 7 avec lancement enfant |
| native-sync-o0-initial.log | Premier lot : 9 méthodes, 7,126 s, OK |
| native-sync-regression-o2.log | Première régression : erreurs de provenance et diagnostic, conservées avant correction |
| native-sync-reference-fix.log | Deux méthodes de retours empruntés : 2,371 s, OK |
| native-sync-contracts-o2.log | Première régression de contrats avec les 9 méthodes nouvelles : 114 méthodes, 34,741 s, OK |
| native-sync-regression-o2-final.log | Deuxième régression intermédiaire : 90 méthodes, un diagnostic encore différent ; ce journal n’est pas une passe finale |
| native-sync-order-fix-o0.log | Diagnostic corrigé et premier lot : 10 méthodes, 10,526 s, OK |
| native-sync-separated-o0.log | Vérification/génération séparées : 11 méthodes, 6,010 s, OK |
| native-sync-final-o0.log | Version finale : 12 méthodes, 11,017 s, OK |
| native-sync-final-contracts-o2.log | Effets, contrats modulaires, corps, capacités, arguments : 105 méthodes, 34,059 s, OK |
| native-sync-final-regression-o2.log | Régression native/async finale : 93 méthodes, 105,309 s, OK, sans saut |
| native-sync-mutations.log | Trois mutations détectées, omission des slots initialement survivante |
| native-sync-slots-mutation.log | Test renforcé : omission des slots détectée |
| native-sync-final-mutations.log | Quatre mutations détectées sur la version finale |

```sh
PYTHONPATH=tests CRUST_TEST_OPT=-O0 python3 -m unittest -v test_native_sync_calls
PYTHONPATH=tests CRUST_TEST_OPT=-O2 python3 -m unittest -v test_effects test_modular_calls test_function_bodies test_async_capacity test_arguments
CRUST_TEST_OPT=-O2 python3 tests/run_native_thread_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_native_sync_mutations.py
```

Les exécutions natives nouvelles et la régression runtime utilisent Clang C11,
pthread, avertissements stricts, UBSan et `-fno-sanitize-recover=all`.
Les anciens modules synchrones conservent leurs configurations propres ;
la passe de 105 méthodes ne signifie pas que chacune exécute du C sous UBSan.
Ce n’est pas l’ensemble de tous les tests du dépôt. Les preuves portent sur
les modules et chemins sélectionnés, pas sur tous les programmes Crust.
Les modules modifiés passent py_compile et les liens locaux des documents
modifiés sont vérifiés dans `validation/native-sync-final-artifacts.log`.
Le diff de l’implémentation et des nouveaux tests est conservé dans
`validation/native-sync-implementation.patch`.

## Limites restantes

RT8, RT5 et AS7 restent partiels. Les passages de références, d’allocations,
de tableaux et d’agrégats à ces auxiliaires restent à raccorder avec leurs
contrats de provenance et d’exclusivité. Les signatures Bool synchrones sont
encore refusées, indépendamment de ce nouveau raccordement. Les pools locaux
directement dans les corps async/natifs, les captures générales et le type
public runtime::Handle<T> restent ouverts. Trois programmes valides encore
refusés et leurs diagnostics sont conservés dans native-sync-artifacts.log.

`validation/native-sync-helper.c` est le C réellement généré depuis le
contre-exemple add(7). Il montre le prototype de l’auxiliaire, la capture de
l’argument dans un temporaire, l’appel depuis resume, puis le retour scalaire
et task_native_start. Les autres obligations des sept brouillons restent
dans l’objectif actif. Pas de preuve formelle, de validation TSan, de second
compilateur ni de nouvelle validation ASan : les blocages ASan déjà consignés
n’ont pas été présentés comme des passes.
