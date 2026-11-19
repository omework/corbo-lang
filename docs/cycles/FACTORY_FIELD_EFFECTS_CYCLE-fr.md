[English](FACTORY_FIELD_EFFECTS_CYCLE.md)

# Effets différés des fabriques synchrones

## Règles et portée

Ce lot raccorde AS2, AS5, AS12–AS16, B4/B5 et ST10/ST13. Il ne modifie
aucune règle normative. Une fonction synchrone peut créer puis retourner
une tâche inactive ou son handle lancé, dont le corps remplace un champ
partagé `&Int` d'un porteur injecté. Le contrat conserve cette modification
sans l'appliquer à la création. Les relais, l'attente dans un helper et les
fabriques de handles appelées depuis un état async ou natif sont raccordés.

`FunctionResult.task_field_updates` décrit les champs différés relativement
aux paramètres de la fabrique. Les cibles sont sauvegardées à la création,
puis substituées aux arguments à chaque relais. Les valeurs intermédiaires
conservent aussi les porteurs de ces modifications. Les jonctions et sorties
de boucle réunissent leurs alternatives. Le contrat distingue ces champs des
modifications immédiates `structure_fields` et des handles reçus en paramètres.

Un appel opaque instancie ces informations sans reparcourir un corps synchrone.
Le pont d'appel depuis un état transmet aussi les effets au descripteur du handle.
L'attente publie les nouvelles dépendances ; un échec de lancement conserve
l'état initial possible. Détruire une tâche inactive n'applique aucun store.
Les contrats sync et les effets de terminaison async sont recalculés jusqu'à
stabilité avant l'émission, puisque des fabriques et des helpers attendants
peuvent intervenir dans les deux directions.

## Recherche de contre-exemples

Treize méthodes dans `tests/test_factory_field_effects.py` couvrent :

- nouvelle tâche lancée, relais avec permutation des arguments, attente opaque ;
- nouvelle tâche attendue dans le helper qui l'a créée, puis lecture externe ;
- fabrique inactive détruite ou lancée, réemploi du slot du pool de données ;
- choix conditionnel de deux cibles, transfert par résultat de boucle ;
- appelant privé de tous les corps synchrones, disposant seulement des contrats ;
- cible de scope trop court, reset historique puis réemploi après destruction ;
- fabrique appelée depuis un état async, suspension, succès et échec du lancement enfant ;
- référence provenant d'un champ sauvegardée avant remplacement de ce champ ;
- cible mutable conservée par le champ après la fin de l'enfant, mutation refusée ;
- alternatives réunies et attendues dans un même helper ;
- helper attendante depuis un thread natif, et reset dans le helper après attente ;
- modèle indépendant de huit cas : inactif/attendu, porteur vivant/détruit,
  ancienne/nouvelle cible. Cinq programmes exécutés, trois refusés dans les
  deux entrées de vérification et de compilation.

La suppression du refus général des fabriques oblige aussi à raccorder le
pont async : son ancien descripteur rendait toujours une liste d'effets vide.
Le test de mutation de cette liste détecte maintenant l'acceptation indue
d'une mutation de la nouvelle cible pendant que le porteur la référence.
Aucun programme dont la sûreté était mise en cause n'a été exécuté pour
provoquer un comportement indéfini.

L'ancien test imposant le refus général d'une fabrique est remplacé par des
assertions distinguant effets immédiats et différés. Les cas invalides sont
maintenus par les nouveaux tests de durée de vie et l'appel opaque.

## Exécutions

Les journaux sont dans `validation/factory-field-effects-*.log`.
La première sélection ciblée réussit sept méthodes en 7,429 s, puis
la sélection élargie neuf en 10,090 s et onze en 12,112 s, à O0.

La première sélection de régression (`-regression-initial.log`) termine avec
60 méthodes, deux échecs correspondant au refus général désormais obsolète,
et une erreur de commande : le module demandé `test_async_completion_results`
n'existe pas. Ce journal est conservé ; il ne constitue pas une régression réussie.

Passes finales exécutées :

- `PYTHONPATH=tests python3 -m unittest test_factory_field_effects -v` :
  13 méthodes, 13,282 s, OK (`-final-o0.log`).
- `CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_factory_field_effects test_async_field_application test_sync_handle_field_effects test_async_child_field_effects test_async_structure_effects test_captured_cell_descriptors -v` :
  83 méthodes, 80,447 s, OK (`-complete-o2.log`). Cette sélection précède
  l'ajout des deux dernières méthodes de ce lot ; celles-ci passent aussi
  séparément à O2 en 0,606 s et 0,917 s (`-native-final-o2.log`,
  `-direct-final-o2.log`). Aucun changement du compilateur entre ces passes.
- `CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_public_handle_contracts test_concrete_handle_relays test_sync_handle_bridges test_modular_calls -v` :
  77 méthodes, 72,588 s, OK (`-contract-regression.log`).
- Compilation Python des modules modifiés et des nouveaux tests : réussie.
  Les différences depuis le début du lot sont conservées dans
  `validation/factory-field-effects-*.py.patch`.

Ces nombres comptent des méthodes, parfois composées de plusieurs programmes.
Les sélections se recouvrent et ne sont pas un total de programmes distincts.
Les programmes natifs sont compilés en C11/pthreads, avec avertissements
bloquants et UBSan fatal. Les niveaux O0/O2 sont explicités dans les journaux.
Les huit mutations ciblées de `tests/run_factory_field_mutations.py` sont
détectées : perte du contrat retourné, de sa composition, des effets d'attente,
de l'instanciation opaque, du pont natif, de l'alternative initiale, de
l'attente directe ou du recalcul jusqu'à stabilité. La dernière mutation
provoque un refus indu d'un programme valide ; les autres recherchent les
pertes de dépendances. Journal final : `-final-mutations.log`.
Ce n'est pas un taux général de détection des défauts.

## Limites

Les porteurs et cibles pris en charge restent ceux des remplacements de champs
partagés Int injectés. Les champs mutables, résultats empruntés des tâches
modificatrices, sources inline générales et écritures sur des graphes d'agrégats
plus généraux ne sont pas généralisés par ce lot. Les corps async ne peuvent
pas encore recevoir tous les paramètres de handle ni toutes les signatures
synchrones. La corrélation exacte succès/échec et les récurrences de stores
à travers les reprises de boucle restent ouvertes.

Les effets réunissent conservativement les possibilités. Ces tests finis,
leurs modèles et UBSan ne prouvent pas la sûreté générale ou tous les
ordonnancements concurrents. Aucune nouvelle preuve ASan/TSan ou comparaison
entre compilateurs C indépendants. L'objectif global n'est pas terminé.
