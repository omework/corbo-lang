[English](ASYNC_TYPED_DIVERGENCE_CYCLE.md)

# Cycle — initialisations async typées sans continuation

## Règles et changement

Application de S5/S5a, B1–B5, D1, E3/E5/E6/E7 et AS10/AS11/AS12, sans
changement normatif. AGENTS.md, VALIDATION_GUIDELINES.md, l’index des sept
brouillons et les règles des résultats de branches et des tableaux ont été
relus. Le cycle précédent avait corrigé les expressions sans continuation
et une fuite des captures préparées ; ce lot complète la réception typée.

Le programme `validation/open-async-diverging-typed-initializer.crust` est
désormais accepté et exécuté : 42, 20, 77. L’annotation `[Int;1]` ne crée
pas un tableau lorsque tous les chemins quittent l’initialisation par break.

Avant le traitement spécialisé d’une liaison annotée, le compilateur examine
les expressions de contrôle connues sans continuation. Pour les types du
répertoire async reconnu, il vérifie et génère leurs sorties effectives avant
d’exiger une valeur pour le receveur. Il ne matérialise aucune liaison sur ces
chemins. Une branche continuante doit toujours fournir le type déclaré.

Ce contrôle ne saute pas l’analyse des sorties : modes de break, cibles,
provenances, transferts et nettoyages suivent les mêmes vérifications. Une
annotation inconnue reste refusée. Les types de tableaux reconnus comprennent
les dimensions imbriquées et les références Int partagées/mutables ; les types
scalaires et résultats builtin reconnus sont également exercés. Aucune nouvelle
API ni règle de copie ou de transfert n’est introduite.

Le traitement est placé aux deux points de réception de variables : dans le
corps principal de la fonction et dans les branches/blocs. Un placement initial
dans le seul traitement scalaire aurait laissé les annotations de tableaux de
références échouer trop tôt dans le traitement spécialisé des boucles.

## Scénarios

`tests/test_async_typed_divergence.py` comporte six méthodes, 25 exécutions
natives et 27 refus attendus par passage complet :

- Tableau vide, tableau imbriqué u8, tableaux de &Int et &mut Int, Bool, char,
  runtime::Error et Result<char,CharFromStrError> comme types de receveurs
  qui ne seront pas matérialisés. Les deux sorties sont exécutées.
- Mutation prématurée de chacune des deux sources du résultat emprunté refusée
  pour chaque annotation, puis utilisation et réemploi des slots après usage.
- Bloc, match, return, boucle sans résultat intermédiaire et continue, avec
  suspension ; aucun marqueur de la suite inaccessible n’est exécuté.
- Un bras sort par break et l’autre fournit réellement un tableau : le voisin
  valide est exécuté, tandis que mauvaise dimension, mauvais type d’élément ou
  annotation Bool sont refusés.
- Cible locale non durable, modes de références divergents, break sans valeur,
  branche continuante d’un mauvais type et types inconnus restent refusés.
- Sortie typée pendant la préparation des arguments d’un appel : l’allocation
  déjà déplacée est détruite exactement une fois, et son pool de capacité un
  est réutilisé après join. La tâche interrompue n’est pas démarrée.

Les attentes sont définies explicitement à partir des branches et des règles
de nettoyage. Aucun nouveau modèle indépendant général n’est ajouté pour cette
correction de réception. Les modèles de contrôle de flux des cycles précédents
font partie de la régression. Aucun raisonnement de sûreté universel n’est déduit
de ces scénarios finis.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| async-typed-divergence-initial.log | 6 méthodes, 10,723 s, OK ; avant déplacement du contrôle aux deux réceptions et ajout du cas loop annoté avec références |
| async-typed-divergence-O0.log | Module final : 6 méthodes, 13,290 s, OK |
| async-typed-divergence-mutations.log | Quatre fautes ciblées détectées |
| async-typed-divergence-O2-regression.log | 96 méthodes, 114,353 s, OK, sans saut |

La régression O2 est terminée. Elle charge test_async_typed_divergence,
test_async_diverging_expressions, test_async_expression_loop_exits,
test_async_loop_references et test_async_match_references, puis les méthodes
d’AsyncRuntimeTests contenant array, conditional, typed ou cleanup.
Le journal garde leurs noms exacts. Les helpers natifs utilisent Clang C11,
pthread, -Wall/-Wextra/-Werror et UBSan fatal.

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_async_typed_divergence -v
python3 tests/run_async_typed_divergence_mutations.py
```

`py_compile` et les liens locaux des documents modifiés ont été vérifiés.
Le diff du compilateur est conservé dans
`validation/async-typed-divergence.patch`. Le runtime n’a pas changé.

## Mutations

| Faute dans une copie temporaire | Détection |
| --- | --- |
| Désactiver le traitement typé sans continuation | Programme valide refusé |
| Accepter toute annotation comme connue | Types inconnus admis à tort |
| Effacer une provenance du résultat | Mutation prématurée d’une cible acceptée |
| Omettre le nettoyage des captures préparées | Pool de capacité un épuisé |

Les tests distinguent les refus attendus des compilations de programmes valides
et vérifient les sorties natives. Aucun taux global de détection n’est extrapolé
de ces quatre fautes sélectionnées.

## Limites et prochain chantier

Ce lot concerne le répertoire de types déjà reconnu par le backend async.
Il ne matérialise pas de nouveaux agrégats et ne généralise pas toutes les
annotations de handles, structures ou types externes. Les autres obligations
de la matrice restent ouvertes ; l’objectif des sept brouillons n’est pas atteint.

Le prochain chantier identifié est RT8 : le bloc synchrone `runtime::thread`.
`validation/open-native-thread-basic.crust` reprend cette primitive validée
avec un bloc sans capture retournant 7, puis un join explicitement traité.
Le compilateur refuse encore ce programme au parsing :

```text
REJECTED valid RT8 program: ligne 2: attendu ';', reçu ':'
```

Ce manque est déjà noté N dans la matrice. Le brouillon 04 impose ensuite les
captures explicites, les retours anticipés, le thread natif distinct du
scheduler, l’échec LaunchFailed, les durées de vie et les obligations d’attente.
La fixture minimale n’est pas présentée comme une couverture de ces exigences.

Suivi : le [cycle de la frontière native](NATIVE_THREAD_BOUNDARY_CYCLE.md)
ajoute depuis le parsing et les primitives internes de lancement. Les contrats
et la génération du bloc restent ouverts ; la matrice actuelle passe RT8 en P
pour ces parties seulement. Le diagnostic de parsing cité ici est historique.

Les règles de scheduler, Select, mutex et stockage implicite restent également
ouvertes. Reset reste retiré. ASan n’a pas été relancé après le blocage documenté
du programme C vide. Aucune preuve ASan/TSan, second compilateur, preuve formelle
ou sûreté générale n’est revendiquée.
