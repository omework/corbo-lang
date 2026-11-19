[English](ASYNC_CHILD_FIELD_EFFECTS_CYCLE.md)

# Modifications de champs à travers les tâches enfants

## Raccordement

Aucune règle normative modifiée. Ce lot prolonge ST10/ST13, B1/B2/B4/B5 et
AS4/AS12/AS13 depuis le lot ASYNC_FIELD_APPLICATION_CYCLE.md. Les tâches async
et blocs natifs à résultat scalaire ou Void peuvent désormais transmettre
leurs modifications de champs partagés Int à travers un enfant attendu.

Le record interne d'une tâche ou d'un handle porte les alternatives de
modifications, préparées depuis les arguments capturés. Il les conserve à
travers lancement, transfert par bloc, résultat conditionnel et sortie de
boucle. La création ne publie pas ces modifications. Une attente directe les
applique à la terminaison ; l'attente d'un handle conserve aussi l'état initial,
car le lancement peut échouer. Détruire une tâche inactive retire ses emprunts
sans appliquer son contrat de terminaison.

Les prêts de champs ainsi publiés servent aux contrôles d'accès dans le parent
et au choix du descripteur Cell lorsqu'un helper stocke l'emprunt. Le contrat
de terminaison du parent conserve ensuite les dépendances chez son propre
appelant. Les cibles ne sont ni copiées ni promues. Les champs sources partagés
sont maintenant résolus depuis les captures, ce qui permet les remplacements
conditionnels conservant l'ancienne cible et les échanges de deux champs.
Toutes les écritures d'un contrat sont préparées avant leur publication.

## Contre-exemple confirmé

Un enfant retournant Void peut modifier un champ malgré l'absence de receveur.
`ResultContext.nodes` ignorait la forme AST `await_statement`. Après ouverture
du raccordement des enfants, le contrat du parent `work` annonçait donc aucun
effet pour `write(v,n).await;`, alors que le C exécutait l'écriture.

`validation/counterexample-async-void-child-field-effect.crust` reproduit ce cas :
après join du parent, un drop de la nouvelle cible précédait une lecture du
champ. Verify et compile acceptaient le programme ; il n'a pas été exécuté dans
cet état invalide. Le journal `async-child-field-effects-void-before.log`
conserve cette acceptation. L'instruction await appelle désormais la même
analyse d'expression que les attentes avec receveur. Le journal `-void-after.log`
montre le refus par les deux entrées. Le voisin sans drop s'exécute et le test
assert explicitement la présence de l'effet dans le contrat du parent.

L'analyse des résultats scalaires attendus d'un handle perdait également
l'enveloppe de résultat de lancement. Un match qui rendait son payload était
alors décrit comme deux branches de types différents. L'enveloppe `join_int`,
`join_bool`, etc. est désormais conservée dans cette analyse. Le cas natif
attendu puis retourné par un match s'exécute sans supprimer les effets du champ.

Un premier test utilisait `Ok(n)` dans une tâche ayant déjà un paramètre `n` ;
il a été corrigé vers `Ok(value)`, conformément au refus de masquage du backend.
Un test historique de helper synchrone appelé par une tâche attendait le
diagnostic de l'ancien refus général des enfants. Il exige maintenant le
diagnostic normatif « join réservé au code synchrone » ; le résumé différé y
reste explicitement incomplet. Le programme n'est pas devenu accepté.

## Couverture exécutée

`tests/test_async_child_field_effects.py` couvre :

- trois relais, permutation des arguments, tâche nommée et attente directe ;
- enfant inactif détruit, puis mutation de sa capture permise ;
- enfant terminé conservant la réservation de sa nouvelle cible dans le parent ;
- enfant lancé, yield, résultat attendu et refus de soumission injecté ;
- choix de tâches, transfert par bloc et résultat de boucle, avec attente directe
  ou lancement, pour douze combinaisons de formes et branches ;
- ancienne référence détachée avant attente, champ conditionnellement inchangé,
  et échange simultané de deux champs ;
- enfant Void et bloc natif attendu depuis une tâche ;
- cible de scope enfant refusée, sans promotion ;
- modèle indépendant de rétention avec enfant inactif/direct/lancé, porteur
  détruit ou vivant et ancienne/nouvelle cible : douze cas, sept exécutés et
  cinq refusés par verify et compile.

Les exécutions natives utilisent Clang C11, pthreads, `-Wall -Wextra -Werror`,
UBSan fatal et délais explicites de compilation/exécution. Les simulations de
refus de lancement injectent EAGAIN à la soumission choisie. La compilation
Python des modules et tests modifiés réussit.

```
CRUST_TEST_OPT=-O0 PYTHONPATH=tests python3 -m unittest test_async_child_field_effects -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_child_field_effects test_async_structure_effects test_async_field_application -v
```

Les onze méthodes ciblées passent à O0 en 31,356 s :
`validation/async-child-field-effects-complete-o0.log`.
La passe O2 réunissant le nouveau module, les contrats et le lot précédent passe
52 méthodes en 57,744 s : `-complete-o2.log`. La régression finale de captures
de champs, descripteurs capturés, handles publics et relais synchrones passe
48 méthodes en 67,462 s : `-final-regression.log`. Ces modules ont été chargés
après les corrections de l'instruction Void et de l'enveloppe scalaire.

Une sélection de 75 méthodes passe en 131,182 s dans
`async-child-field-effects-regression.log` : handles publics, relais synchrones,
résultats propriétaires, références/sorties de boucles, divergence et blocs
natifs. Elle avait démarré avant la correction de l'instruction await Void et
de l'enveloppe scalaire. La première sélection de 50 méthodes de contrats et
descripteurs échouait uniquement sur l'attente du diagnostic historique décrite
plus haut. Les passes finales remplacent cette preuve pour les modules concernés.

La campagne `tests/run_async_child_field_mutations.py` modifie des copies
temporaires. Elle couvre neuf omissions : instruction await Void, enveloppe
scalaire, application après attente directe ou handle, publication à la
création, état initial sur échec de lancement, choix conditionnel, sortie par
break et descripteur de la référence détachée. Le journal final est
`validation/async-child-field-effects-complete-mutations.log`.
Les neuf mutations sont détectées dans cette passe finale. Les compteurs
portent sur cet échantillon ciblé, pas sur un taux général de détection.
Un rejet indu d'un programme admis est distingué d'une acceptation invalide ou
d'une mauvaise sortie native ; une erreur Python interne ne suffit pas à
classer la mutation comme détectée.

Les échecs intermédiaires restent dans les journaux `-initial`, `-expanded`,
`-contract-regression` et `-final-o2`. Les patches depuis le début du lot sont
conservés dans `validation/async-child-field-effects-*.py.patch`.

## Limites encore ouvertes

Les relais synchrones de handles porteurs de modifications de champs ne sont
pas raccordés. Les tâches modificatrices retournant un emprunt ou un agrégat,
les champs mutables, les sources inline/locales non durables et les stores
directs de champs dans le corps async restent incomplets. Le suivi des stores
à travers une reprise de boucle et la corrélation complète aux branches Ok/Err
restent ouverts. L'union conservative de succès/échec peut retenir l'ancienne
cible au-delà du seul chemin réussi.

Les scénarios exécutés ne démontrent pas toutes les compositions de tâches et
de données. Pas de nouvelle preuve ASan/TSan, de comparaison entre compilateurs
C indépendants ni de preuve formelle. Les chantiers Select, scheduler public,
mutex et placement général restent dans l'objectif actif ; ce lot ne termine
pas l'implémentation des sept brouillons.
