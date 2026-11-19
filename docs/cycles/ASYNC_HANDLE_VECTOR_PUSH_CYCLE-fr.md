[English](ASYNC_HANDLE_VECTOR_PUSH_CYCLE.md)

# Insertion de handles dans Vector<A<Int>> depuis async

## Règles et implémentation

Application de H1–H2, VE1–VE2, B1–B5, AS8–AS12 et SL1–SL2, sans modification
normative. push reçoit explicitement un A<Int>, conserve l'adresse et le pool
de sa cible, et transmet la responsabilité unique de nettoyage à la case.
La source de chaque élément doit survivre au vecteur receveur.

Le lowering accepte les transferts de variables et de constructions de pool.
Il réserve le vecteur pendant l'évaluation de l'argument, contrôle le type et
la durée de vie de la source, puis écrit le handle et retire la responsabilité
au temporaire. Les prêts expirés peuvent être relâchés avant la nouvelle insertion.
Le nettoyage du vecteur utilise le destructeur de handles déjà existant.

Les contrats publient les sources ajoutées à la terminaison et aux points de
suspension. Les fabriques et relais conservent ces effets différés dans
FunctionResult.task_vector_updates/task_suspension_vectors. La création d'une
tâche n'effectue pas l'insertion. Join applique l'union des états de réussite
et d'échec de lancement. Select prend aussi en compte les ajouts faits par les
branches suspendues qui perdent. Les pools courts sont refusés statiquement.

Les ponts C synchrones savent recevoir un Vector<A<Int>> par emprunt : le
paramètre reste un Cell* avec les sources symboliques de ses éléments. Les
appels aux fabriques et aux helpers synchrones de mutation emploient ces ponts.
Le calcul des effets de vecteurs synchrones a été extrait en une méthode
réutilisée pour les instantanés de suspension, sans changement d'intention.

## Cas ciblés et défauts rencontrés

Neuf méthodes dans tests/test_async_handle_vector_push.py : treize exécutions
natives, dont un échec de lancement injecté, et douze programmes invalides aux
deux entrées verify_program/compile_source.

- Programme consigné : allocation 7 dans un pool injecté, insertion, lecture,
  destruction unique et réemploi du pool de capacité un avec 8.
- Flèche absente, Int inline, Bool transféré et vecteur partagé refusés.
- Transfert d'une variable après le dernier usage de son emprunt ; usage après
  transfert, double transfert et emprunt encore utilisé refusés.
- Fabrique synchrone et relais async attendu ; pool enfant trop court refusé
  dans l'appel direct comme dans l'appel via fabrique.
- Deux éléments transférés depuis deux pools distincts, directement ou via
  fabrique ; résultat 30, destruction unique de 10 et 20, réemploi avec 11 et 21.
- Tâche inactive détruite sans insertion ; échec de lancement sans création de
  l'élément. Aucun destructeur de 7 dans ces chemins sans exécution du corps.
- Prêt d'une cible puis deuxième push après dernier usage ; prêt encore vivant refusé.
- Helper synchrone effectuant l'insertion depuis l'état async.
- Vecteur lui-même transféré à la tâche : nouvel élément détruit avant join,
  réemploi des pools du vecteur et de l'élément.
- Branche perdante de Select ayant inséré avant yield, directement et via
  fabrique : l'élément reste présent après destruction de Select. Un pool plus
  court que le vecteur est refusé dans les deux cas.

Pendant l'intégration, le dernier cas direct était accepté à tort lorsque le
pool expirait avant le vecteur. Les écritures faites dans les arguments
symboliques temporaires n'étaient pas reportées sur leurs alias extérieurs.
La correction propage l'inventaire du vecteur à ses alias après application
d'un contrat de terminaison ou de suspension. Reproduction conservée dans
validation/async-handle-vector-select-short-pool.crust, désormais refusée aux
deux entrées (journal .log). Ce programme invalide n'a pas été exécuté en C.

## Exécutions

Journaux dans validation/ :

| Journal | Résultat |
| --- | --- |
| async-handle-vector-push-first-o0.log | Fabrique depuis async : signature de collection non raccordée |
| async-handle-vector-push-second-o0.log | Pont C : paramètre de vecteur encore traité comme référence scalaire |
| async-handle-vector-push-third-o0.log | Cinq méthodes, 3,487 s, code 0 |
| async-handle-vector-push-fourth-o0.log | Diagnostics de deux arguments invalides masqués par le contrôle de contrat ; contrôles de type et transfert replacés avant ce contrôle |
| async-handle-vector-push-fifth-o0.log | Huit méthodes, 4,042 s, code 0 |
| async-handle-vector-push-sixth-o0.log | Pool trop court accepté sur le chemin Select direct ; défaut de publication des alias corrigé |
| async-handle-vector-push-seventh-o0.log | Neuf méthodes, 4,878 s, code 0 |
| async-handle-vector-push-regression-o2.log | 68 méthodes, 55,594 s, code 0 |
| async-handle-vector-push-sync-regression.log | Cinq méthodes, 5,353 s, code 0 |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_handle_vector_push -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_handle_vector_push test_async_handle_vector_captures test_async_handle_vector_borrows test_async_handle_vector_borrow_returns test_factory_owned_effects test_factory_field_effects test_select_source -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_handle_vector_optional_push_through_borrow_keeps_possible_pool test_foundation_rules.FoundationTests.test_handle_vector_replacement_through_borrow_updates_caller test_foundation_rules.FoundationTests.test_handle_vector_extract_through_borrow_updates_caller test_foundation_rules.FoundationTests.test_owned_handle_vector_return_keeps_inserted_parameter_pool test_foundation_rules.FoundationTests.test_handle_vector_try_push_at_capacity_returns_injected_handle -v
```

C11/pthread, warnings en erreurs, UBSan fatal. Les cinq cas Foundation utilisent
leur harnais O2/UBSan et le profil legacy-reset des scénarios historiques.
Les oracles vérifient valeurs, refus, destruction et réemploi. Pas de nouveau
modèle indépendant ni de campagne de mutations ou de recherche adversariale
élargie ; l'audit indépendant reste distinct. Ces résultats ne prouvent pas
la sûreté générale ni toutes les combinaisons du modèle.

## Limites et suite

Les contrats différés de fabrique retiennent l'ensemble des sources possibles
des ajouts ; ils ne promettent pas une longueur ou un inventaire exact par case.
L'extraction et les autres opérations propriétaires ne sont pas implicitement
couvertes par ce lot. Prochain refus reproduit aux deux entrées :
validation/open-async-handle-vector-remove.crust et .log, pour la réception
explicite de values.remove(0), lecture puis destruction de l'élément extrait.
Try_push, pop, replace, les constructions locales et les retours de vecteurs
restent à compléter dans les états async. Les arbitrages déjà ouverts ne sont
pas clôturés.

Snapshot : /tmp/crust-before-async-handle-vector-push/.
Diffs : validation/async-handle-vector-push-{async_lowering.py,crust.py,results.py,async_structure_effects.py}.patch.
