[English](SYNC_HANDLE_FIELD_EFFECTS_CYCLE.md)

# Contrats synchrones des handles portant des modifications de champs

## Implémentation

Aucune règle normative modifiée. Ce lot raccorde B4/B5, ST10/ST13, AS12/AS13
et RT7 pour les fonctions synchrones qui reçoivent une tâche ou un handle
porteur de modifications de champs déjà préparées. Elles peuvent le retourner,
lancer la tâche inactive reçue, attendre le handle reçu ou détruire la tâche
inactive. La création d'une nouvelle tâche modificatrice dans une fabrique
synchrone reste distincte et non raccordée.

Les valeurs symboliques suivent désormais leurs paramètres de tâche d'origine.
Les contrats de résultat publient `task_wait_parameters` et
`task_forward_parameters`. Ces ensembles se composent à travers les appels,
les conversions vers un handle public, les blocs, les jonctions et les boucles.
Ils décrivent les possibilités des chemins ; la vérification du corps conserve
séparément l'obligation d'attendre chaque handle lancé.

L'appelant opaque publie les effets des paramètres pouvant être attendus avant
de contrôler les destructions de sources du contrat. Les handles rendus
conservent les modifications différées de leurs entrées possibles. Une tâche
inactive simplement transmise ou détruite ne publie aucun effet. Une attente
conserve l'alternative initiale, puisque le lancement peut avoir échoué.
Une fonction qui attend un des deux handles et rend l'autre selon une branche
conserve les deux possibilités sans prétendre avoir attendu les deux à l'exécution.

Les fonctions à résultat scalaire mais avec paramètres de tâche ne passent plus
par le raccourci qui produisait un contrat vide sans parcourir leurs instructions.
Le calcul du contrat a lieu à la définition ; l'appel opaque ne reparcourt pas
le corps. Le test dédié donne à l'appelant les contrats synchrones et les
descriptions async nécessaires à la création, mais aucun catalogue de corps
synchrones, de résultats inférés séparés ni de définitions C auxiliaires.
L'appel de `relay` n'entre pas dans le corps de `finish`.

## Scénarios et écarts corrigés

Sept méthodes dans `tests/test_sync_handle_field_effects.py` couvrent :

- transfert public puis attente à travers trois appels, avec refus de drop ou
  mutation des cibles, et échec de soumission injecté ;
- transfert d'une tâche inactive, lancement dans un helper et destruction
  inactive dans un autre, avec réemploi du slot ;
- transfert conditionnel et résultat de boucle ;
- appelant utilisant uniquement les contrats synchrones ;
- reset historique après attente, encore refusé si un porteur externe doit
  lire la cible ; variante admise après destruction du porteur et réemploi ;
- deux handles vers deux porteurs distincts, l'un attendu et l'autre retourné
  selon le chemin, puis attente finale et protection des deux nouvelles cibles ;
- modèle indépendant de huit cas (inactif/attendu, porteur détruit/vivant,
  ancienne/nouvelle cible) : cinq programmes exécutés et trois refusés par les
  deux entrées.

La régression a exposé une lacune auparavant masquée par le raccourci : le
résumé refusait le déplacement d'un tableau de valeurs reçu d'un join, alors
que cette opération est déjà admise par les règles et le backend. `Value` de
mode `array` est maintenant reconnu dans le transfert explicite. Les trois
cas historiques `[Int;2]`, `[[Int;2];2]` et `[u8;2]` passent à nouveau, avec
réemploi du pool de capture après join. Les attentes de ces tests n'ont pas
été modifiées.

Les premières versions des nouveaux tests utilisaient `Bool` dans une signature
synchrone, corrigé en `bool`, et passaient des handles du scope parent depuis
un bras sans transfert descendant. Les en-têtes `a ->; b ->;` ont été ajoutés
dans ce bras ; les règles n'ont pas été assouplies. Ces diagnostics sont
conservés dans les journaux `-initial` et `-expanded`.

## Preuves exécutées

La passe ciblée O0 réussit sept méthodes en 8,569 s :
`validation/sync-handle-field-effects-complete-o0.log`.
Le voisin ciblé incluant les trois retours de tableaux réussit huit méthodes
en 7,709 s : `-expanded-final.log`.

Les commandes finales complémentaires sont :

```
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_sync_handle_field_effects test_public_handle_contracts test_concrete_handle_relays test_sync_handle_bridges test_plain_join_contracts -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_fixed_arrays test_modular_calls -v
```

La première passe réussit 67 méthodes en 67,906 s dans `-complete-o2.log` ;
la seconde réussit 96 méthodes en 34,122 s dans `-array-regression.log`.
La régression async/enfants/contrats passe
36 méthodes en 16,422 s dans `-async-regression.log`, avant l'ajout final du mode
array au résumé des déplacements. La première sélection de 60 méthodes dans
`-regression.log` exposait les trois erreurs de tableaux décrites ci-dessus.
Ces nombres sont des méthodes de tests ; plusieurs exécutent des familles de
programmes, d'autres vérifient les contrats seuls.

Les programmes natifs sont compilés en C11 avec pthreads, avertissements
bloquants et UBSan fatal, à O0/O2 selon la passe. La compilation Python des
modules et tests modifiés réussit. Les patches depuis le début du lot sont
conservés dans `validation/sync-handle-field-effects-*.py.patch`.

La campagne `tests/run_sync_handle_field_mutations.py` retire séparément le
résumé d'attente, sa composition à travers un relais, l'origine du handle
retourné, ses effets différés, l'application opaque ou l'analyse des fonctions
scalaires à paramètre de tâche. Le journal de la passe finale est
`validation/sync-handle-field-effects-complete-mutations.log`. Ces essais
cherchent notamment un désaccord entre l'appel opaque et le backend qui entre
dans le corps pour produire le C spécialisé.
Les six mutations sont détectées dans cette passe finale. Ce résultat ne
constitue pas un taux général de détection des défauts du compilateur.

## Limites

Les fabriques synchrones créant une tâche modificatrice neuve restent refusées.
Les helpers synchrones appelés depuis un état async ne reçoivent pas encore ces
handles. Les effets sont réunis conservativement ; une branche qui retourne
un handle plutôt que de l'attendre peut conserver davantage de réservations
que nécessaire. La corrélation complète entre branches, résultat de lancement
et effets reste ouverte. Les autres limites des lots de champs async, dont les
champs mutables et les résultats empruntés des tâches modificatrices, subsistent.

Cette sélection ne constitue ni une validation exhaustive ni une preuve de
sûreté générale. Pas de nouvelle preuve ASan/TSan, de comparaison entre
compilateurs C indépendants ni de preuve formelle. L'objectif global reste actif.
