[English](DETACHED_TASK_FACTORIES_CYCLE.md)

# Fabriques de tâches à résultat emprunté détaché

## Règles et périmètre

Ce lot applique les règles existantes ST8/ST10/ST13/ST14, B1/B2/B4a,
T1/T6, D1, AS2/AS8–AS14, RT6 et SL1. Il ne modifie aucune règle normative.
Une référence partagée retournée conserve sa cible ; elle ne conserve pas
arbitrairement le porteur détruit ni les autres champs. Une référence vers
le stockage inline du porteur n'a pas cette indépendance et reste refusée.

Sont couverts les champs &Int des structures Int/&Int/&mut Int prises en
charge, les captures propriétaires locales ou A<T>, les fabriques synchrones,
leurs relais de tâches, les attentes directes, les fonctions attendant un
handle nominal, le résultat Handle<&Int> public et les branches Select
sans obligation d'attente non résolue. Ce lot ne généralise pas les graphes
mixtes ni tous les résultats empruntés, notamment les projections mutables.

## Contre-exemples et corrections

1. `validation/open-owned-borrowed-detached-factory.crust` était refusé
   lors de l'inférence initiale : la fabrique demandait la provenance du
   résultat avant la disponibilité du contrat de terminaison de la tâche.
   Il est maintenant compilé et exécuté, avec les relais couverts.
2. `validation/open-detached-child-target-dropped.crust` était accepté par
   `verify_program` et `compile_source` malgré un drop de la cible suivi
   d'un usage de la référence après await. Le journal
   `detached-factories-unsafe-baseline.log` conserve ces deux acceptations.
   Les prêts du champ retourné manquaient dans le résultat d'un enfant
   créé directement depuis un état async. Les deux étapes refusent
   maintenant ce programme (`detached-factories-unsafe-fixed.log`).
   La preuve du défaut est statique ; aucune exécution native de cette
   version invalide n'est revendiquée.
3. Le chemin passant par une fabrique conservait tous les champs après
   await. La cible non retournée peut maintenant être détruite ; la vraie
   cible reste protégée jusqu'au dernier usage.
4. Le contrat d'une fonction recevant un handle nominal puis faisant join
   conservait également des champs non retournés. Sa projection symbolique
   suit maintenant le chemin de résultat, y compris avec une référence de
   secours fournie en cas de LaunchFailed.
5. Une fabrique dans un argument transféré de Select n'était pas dispatchée
   vers la création de tâche. Elle utilise maintenant le même chemin que
   la création nommée. Les perdantes conservent leurs prêts jusqu'au drop.
6. Remplacer un champ partagé par un autre champ partagé de la structure
   capturée entière était refusé. Le descripteur de la cible déjà empruntée
   est durable à travers la capture. Ce cas passe ; remplacer par une
   référence vers un nouvel Int local puis la retourner reste refusé.

## Implémentation

`ResultAnalyzer.async_definition` demande le contrat de terminaison nécessaire.
L'analyse async reçoit les signatures synchrones et demande leurs résumés au
fournisseur d'inférence. Les corps synchrones restent absents de cet adaptateur.
Seuls les contrats complets sont publiés ; un cycle encore en cours reste
explicitement incomplet. Les formes publiques opaques de handles ne sont pas
traitées comme des définitions async ordinaires. Le calcul global des contrats
jusqu'à stabilisation et la vérification finale demeurent en place.

Le backend distingue les prêts retenus pendant l'exécution de ceux attachés
au résultat. Les captures propriétaires projettent les champs partagés
retournés, tandis que les fabriques filtrent leurs prêts par les mêmes chemins.
Les paramètres symboliques de tâches/handles appliquent aussi cette projection.
Le remplacement des champs reconnaît les cibles déjà empruntées d'un paramètre
propriétaire ; il ne rend pas durable une valeur inline ou locale.

Aucun changement du runtime C ni déplacement d'allocation n'est introduit.
Les snapshots sont dans `/tmp/crust-before-detached-task-factories` et les diffs
sous `validation/detached-factories-{results.py,async_lowering.py,async_structure_effects.py}.patch`.

## Validation ciblée

`tests/test_detached_task_factories.py` contient treize méthodes :

- `validation/detached-factories-complete-count-o0.log` : 13 méthodes en
  30,024 s ; 21 exécutions natives et 30 programmes invalides testés par
  les deux étapes, soit 60 vérifications de refus.
- La base O2 de `validation/detached-factories-complete-mutations-o2.log`
  réussit les mêmes treize méthodes en 29,063 s.
- Clang C11/pthread, Wall/Wextra/Werror, Wno-unused-function et UBSan fatal
  sont utilisés par le harnais natif, à O0 et O2.

Un modèle indépendant croise la cible left/right, l'instant avant/après
l'attente et trois chemins d'appel (direct, fabrique, relais de fabrique).
Avant l'attente aucune cible ne peut être détruite ; après, seule la cible
non retournée peut l'être. Les douze scénarios sont inclus dans les comptes.

Les autres essais couvrent les helpers dans trois ordres de déclaration,
les résultats conditionnels qui protègent toutes les cibles possibles,
la disparition du pool du porteur avant le dernier usage de sa référence,
le refus d'une cible trop courte, les échecs de lancement injectés,
les nettoyages de tâches inactives, les handles publics, Select,
le remplacement d'un champ et trois itérations réutilisant le stockage.
Les valeurs attendues et destructions du porteur sont contrôlées.

## Mutations

Huit fautes sont détectées dans des copies temporaires : refus du remplacement
valide, absence de publication de la terminaison, analyse d'un helper par son
stub vide, perte du prêt du résultat enfant, conservation indue de tous les
champs de fabrique, perte de tous les prêts du résultat de fabrique, fusion des
champs dans le contrat du waiter et sélection du mauvais champ enfant.

La perte du prêt enfant est détectée par l'acceptation indue du contre-exemple
invalide ; l'effacement des prêts de fabrique est également détecté après
attente. Les mutations trop restrictives sont détectées par le refus des
programmes valides. Les mutations ne couvrent qu'une sélection explicite de
fautes : aucun taux général de détection n'est déduit.

## Chronologie des preuves et limites

Les journaux intermédiaires sont conservés. La première suite utilisait
`Bool` dans une signature synchrone qui attend la notation `bool` ; cette
fixture a été corrigée. L'ajout du test Select a révélé le dispatch manquant :
les premières bases de mutations/comptage ont donc échoué et ont été relancées
après la correction. Deux lignes du test Select ont ensuite été insérées dans
le mauvais test de boucle ; elles ont été remises dans le test concerné.
Ces erreurs de fixtures ne sont pas comptées comme défauts du compilateur.

Le journal `detached-factories-final-fields-o0.log` conserve aussi le véritable
refus de remplacement d'un champ capturé, corrigé ensuite. Les suites finales
contiennent le test du remplacement et son voisin à cible locale invalide.

ASan et TSan ne sont pas nouvellement établis. Les tests finis, UBSan et les
mutations n'établissent pas de preuve générale de sûreté, de convergence de
toutes les inférences ou de couverture de tous les ordonnancements.

## Écarts restants

Mise à jour : le [cycle des structures mixtes](ASYNC_MIXED_STRUCTURES_CYCLE.md)
corrige le cas direct ci-dessous. Les emprunts dans les descendants possédés
restent ouverts ; le refus décrit ici est la photographie de la fin de ce lot.

`validation/open-mixed-owned-borrowed-capture.crust` reste refusé aux deux
étapes (`validation/detached-factories-next-mixed-probe.log`). Sa structure
contient un champ A<Int> et un champ &Int ; les deux familles séparées sont
prises en charge mais leur combinaison n'est pas encore raccordée. Les pools
et la cible ont pourtant une durée suffisante dans ce programme.

Ce contre-exemple devient le prochain lot. Les projections récursives,
signatures async générales, API publique du scheduler et placement général
restent ouverts, ainsi que les deux arbitrages déjà documentés sur les handles
lancés. Aucun de ces points n'est supprimé de l'objectif global.

## Régressions

`validation/detached-factories-first-regression-o0.log` : 36 méthodes passent
avant les compléments de conservation des prêts après await.
`validation/detached-factories-regression-o2.log` : 190 méthodes passent en
263,624 s, après le correctif des prêts enfant/fabrique, avant les compléments
finaux du waiter, de Select et du remplacement de champ.

`validation/detached-factories-final-regression-o2.log` : 107 méthodes passent
en 153,837 s, après les compléments du waiter et de Select, avant le dernier
complément du remplacement de champ. Modules : public_borrowed_handles,
concrete_handle_relays, select_source, select_contracts,
async_capture_field_contracts, async_detached_field_returns,
async_result_factories.

`validation/detached-factories-field-regression-o2.log` : 100 méthodes passent
en 104,697 s sur le compilateur final. Modules : async_structure_effects,
async_field_application, async_child_field_effects, factory_field_effects,
async_field_reborrows, stored_field_reborrows, async_borrowed_struct_pools.
Les treize méthodes ciblées finales passent également sur ce compilateur.

Les trois sélections O2 emploient CRUST_SANITIZE=undefined explicitement.
Elles se recouvrent et leurs comptes ne sont pas additionnés comme des tests
distincts. Tous les processus finaux sont terminés. Le lot est clos dans son
périmètre et l'objectif global demeure actif.
