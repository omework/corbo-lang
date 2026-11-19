[English](ASYNC_VECTOR_REMOVE_CYCLE.md)

# Cycle — remove dans les corps async

## Modification et invariants

VE3 impose une extraction qui conserve l’ordre des cases restantes. Le
contre-exemple `validation/open-async-vector-remove.crust` était refusé dans
le corps suspendable. Il produit maintenant 17, 1, 29. Le log antérieur
reste historique. Pas de changement normatif : AGENTS.md,
VALIDATION_GUIDELINES.md, l’index des brouillons et VE1–VE6 ont été relus.
Les références de durée de vie et de suspension restent LANGUAGE_RULES.md
et ASYNC_MULTITHREAD_RULES.md.

Le lowering reconnaît remove sur Vector<Int/u8>, en expression, retour,
liaison et instruction dont la copie est écartée. Le receveur mutable est
réservé avant l’évaluation de l’indice. Un temporaire d’état conserve cet
indice après ses éventuelles suspensions ; un autre reçoit l’élément extrait.
Le type reste Int ou u8, sans conversion implicite. Le runtime existant
vérifie l’indice, copie la valeur, décale les cases logiques puis réduit la
longueur et récupère le stockage. Il n’a pas été modifié dans ce cycle.

## Scénarios et oracles

Le module `tests/test_async_vector_remove.py` comporte douze méthodes,
15 exécutions natives qui terminent normalement, six qui doivent s’arrêter
avec le diagnostic de borne, et 15 programmes refusés statiquement.

Les deux types sont testés sur les deux fronts de stockage. Une instrumentation
C vérifie la direction réellement choisie, plutôt que de la supposer à partir
de l’ordre des déclarations. Des extractions au début, au milieu et à la fin
vérifient chaque contenu restant et la longueur, jusqu’au vecteur vide.
Deux listes Python (graines 81/183, 32 opérations chacune) calculent les
effets indépendamment du compilateur et du runtime. La comparaison observe
le résultat, la longueur et toutes les cases restantes après chaque étape.

Les indices suspendus ont un effet observable exécuté une fois. Deux remove
dans une addition restent séquentiels. Un indice qui relit ou modifie le
receveur déjà réservé est refusé ; un vecteur disjoint est admis. La dernière
lecture d’une tranche peut précéder remove ; ses usages ultérieurs, même
après yield ou dans une branche, sont refusés. Une boucle combine vue locale,
extraction, suspension, continue et break sans conserver de prêt expiré.

Un résultat u8=255 passe par un enfant, un parent, puis un join après drop
du vecteur et réemploi du pool. Une capture possédée conserve son obligation
de nettoyage. Un compteur indépendant des listes de slots constate deux
destructions pour les deux allocations du scénario ; le même slot est réutilisé,
sur succès et sur EAGAIN injecté au lancement.

Les indices -1, longueur et INT_MAX sont fournis via une tâche suspendable
pour Int/u8. Les six programmes doivent s’arrêter avec le diagnostic Vector,
avant l’impression suivant l’opération et sans diagnostic UBSan. L’arrêt
contrôlé ne prouve pas la sûreté pour tous les calculs d’indice.

## Preuves exécutées

Clang Homebrew 20.1.3, arm64 macOS, C11, pthread, avertissements stricts,
UBSan fatal. Les nouveaux helpers suivent CRUST_TEST_OPT. Les anciens
helpers de régression conservent leurs propres options.

| Exécution | Résultat | Trace |
| --- | --- | --- |
| Lot O0 | 12 méthodes, 10,814 s, réussi | validation/async-vector-remove-O0.log |
| Lot O2 et régressions des opérations/résultats/erreurs | 52 méthodes, 100,106 s, réussi | validation/async-vector-remove-O2-regression.log |
| Voisins sync/async, tranches, handles et réemploi | 20 méthodes, 39,662 s, réussi | validation/async-vector-remove-neighbors.log |
| ABI, attentes, tableaux et pools | 15 méthodes, 35,254 s, réussi | validation/async-vector-remove-abi.log |
| Mutations | Quatre détectées | validation/async-vector-remove-mutations.log |

Les mutations ciblent la réservation du receveur, le choix de l’indice,
la copie des cases suivantes et la réduction de longueur. Les deux dernières
modifient le runtime C dans une copie temporaire. Toutes sont détectées par
des assertions sémantiques ; aucun taux global n’est déduit de cet échantillon.
La compilation Python des fichiers modifiés a réussi. Le premier lot de dix
méthodes a également réussi ; son log initial est conservé.

## Limites et suite

Le résultat de remove est une valeur Copy dans ce lot. Les propriétaires,
emprunts et autres types d’éléments dans les vecteurs async restent à compléter.
Le défaut suivant est reproduit dans `validation/open-async-vector-push-new.crust`
et son log : push_new devrait initialiser une case à zéro et permettre un
emprunt mutable de cette case à travers yield, mais le lowering le refuse.
Le programme valide devrait afficher 0, 23, 1, 23.

Pas de modification de reset, du placement ni de la politique de destruction.
Les handles publics, scheduler, threads, Select, mutex et autres lignes N/P
de la matrice restent ouverts. Aucun ASan/TSan, second compilateur C, test
exhaustif ou preuve formelle dans ce cycle.

Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_vector_remove -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_vector_remove test_async_vector_operations.AsyncVectorOperationTests test_async_vector_results test_builtin_error_values -v
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 tests/run_plain_join_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_async_vector_remove_mutations.py
```


Mise à jour du cycle suivant : le contre-exemple push_new décrit ci-dessus
est corrigé pour Int/u8. Voir [ASYNC_VECTOR_PUSH_NEW_CYCLE.md](ASYNC_VECTOR_PUSH_NEW_CYCLE.md)
pour les preuves, les relais et les limites qui restent ouvertes.
