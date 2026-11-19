[English](HANDLE_OBLIGATIONS_CYCLE.md)

# Cycle — Attente obligatoire des handles

## Décisions intégrées

La dernière version du brouillon 04 est intégrée dans
`ASYNC_MULTITHREAD_RULES.md`. Elle remplace les anciennes décisions sur
spawn, l'abandon des handles, les types publics d'attente et les capacités
des pools, et consigne RT8, MT9 et SL1. Cette intégration normative ne
signifie pas que ces fonctionnalités sont toutes implémentées.

Ce lot implémente RT7 : tout handle doit être attendu explicitement. Les
vérificateurs synchrone et async refusent sa destruction et une sortie qui
abandonne son obligation. Le refus ne dépend plus de la présence d'emprunts,
de captures propriétaires ou d'un résultat alloué. Il vaut aussi pour les
captures statiques et les tâches sans capture. Le transfert conserve
l'obligation jusqu'au receveur qui attend.

L'instance inactive demeure destructible selon AS14 ; le résultat obtenu
après attente demeure destructible selon son propre type. La destruction
d'un handle déjà consommé reste un usage invalide. Un remplacement tentant
d'abandonner un handle vivant reçoit désormais le diagnostic d'attente ;
cela ne généralise pas encore la réaffectation de handles du prototype.

## Vérifications

`test_handle_obligations` couvre les destructions explicites, fins de scope,
retours, break, continue, transfert descendant, receveur de bloc/boucle,
fabrique et relais synchrones, ainsi que les branches async et synchrones.
Les signatures de handle de ces tests utilisent encore l'ancienne notation
interne exposée `Execution<fonction>` ; l'API `runtime::Handle<T>` reste à
implémenter.

Le modèle indépendant associe à chaque chemin une obligation, consommée
seulement par une attente explicite. Il énumère les deux branches avec les
actions attente/drop/sortie : neuf configurations synchrones et neuf async,
deux admises et seize refusées. Il n'interroge ni les états du compilateur
ni le C généré. Les deux branches du cas admis sont exécutées.

Le test d'échec de lancement injecte EAGAIN à la création du thread. L'attente
rend l'erreur après destruction unique de la capture propriétaire et le slot
est réutilisé à la même adresse. Les noms publics `runtime::Error` et
`LaunchFailed` ne sont pas encore intégrés au parseur ; le test observe le
bras Err du protocole existant.

Les journaux sont conservés sous `validation/handle-obligation-*.log`.

- `CRUST_TEST_OPT=-O0 PYTHONPATH=tests:. python3 -m unittest
  test_handle_obligations -v` : 8 méthodes réussies en 7,883 s,
  `handle-obligation-final-O0.log`. Les deux helpers respectent ce niveau,
  y compris l'injection d'échec de lancement.
- Passage O2 instrumenté du même module : 8 méthodes réussies en 8,242 s,
  9 sources compilées, 10 exécutions natives, 34 programmes refusés et une
  vérification supplémentaire admise pour contrôler l'avertissement AS14.
  Journal `handle-obligation-counted-O2.log`.
- C11, pthread, UBSan et `-fno-sanitize-recover=all` ; les oracles runtime
  utilisent aussi les avertissements C traités en erreurs.
- `PYTHONPATH=tests:. python3 -m unittest test_handle_obligations
  test_async_type_features test_utf8_try_slice_async test_owner_usage
  test_owned_results -v` : 44 méthodes réussies en 63,768 s à O2,
  `handle-obligation-O2-regression.log`. Les huit nouvelles méthodes sont
  incluses dans ce compte ; il ne s'ajoute pas comme 44 propriétés indépendantes.
- `CRUST_SANITIZE=undefined PYTHONPATH=tests:. python3 -m unittest
  test_async_runtime -v` : 275 méthodes exécutées en 465,478 s. Première
  passe : 264 réussies, 7 erreurs et 4 échecs, tous conservés dans
  `handle-obligation-initial-regression.log`.
- Les 11 méthodes concernées ont été migrées puis réexécutées avec succès :
  neuf dans `handle-obligation-final-migrations.log` (11,886 s), deux dans
  `handle-obligation-U1-migrations.log` (9,710 s). Les noms et assertions
  des fixtures modifiées restent dans `test_async_runtime.py`. Il s'agit
  d'une première passe suivie de corrections ciblées, pas d'une nouvelle
  passe monolithique des 275 méthodes sur une copie figée finale.
- Compilation Python des modules et tests modifiés réussie.

La première version du nouveau test de remplacement attendait un diagnostic
d'obligation mais rencontrait d'abord la restriction générale de réaffectation.
Le compilateur signale désormais précisément le handle encore en attente ;
la réaffectation générale reste hors de ce lot. Lors de la migration d'un
test descendant, remplacer drop par await ne testait plus le même déplacement
explicite. Le cas conserve maintenant le renommage `<-` avant l'attente, avec
le même refus lorsque le transfert descendant manque. Les journaux intermédiaires
en échec sont conservés (`first`, `migration`).

## Migration des preuves historiques

Les anciens tests admettaient l'abandon de handles sans dépendance locale,
notamment avec un résultat tableau ou une capture de texte statique. Ces
programmes deviennent des refus attendus selon RT7. Leurs variantes admises
attendent explicitement avec join/await ; leurs assertions de résultat et de
nettoyage sont conservées. Les auxiliaires qui abandonnaient un handle sont
retirés des fixtures admises et réintroduits uniquement dans les variantes
refusées, même lorsqu'ils ne sont jamais appelés.

Les oracles C du registre historique d'abandon restent exercés comme tests
internes. Ils ne justifient plus une opération admise en Crust. Aucun appel
à ce registre ne remplace l'obligation statique d'attente d'un programme Crust.

Une fixture antérieure de retour d'allocation laissait son receveur inutilisé
avant de tenter de réutiliser le nom transféré. Elle déclenchait d'abord U1.
Le test détruit désormais explicitement ce receveur avant de vérifier le
refus du nom déjà transféré. L'attente du diagnostic n'est pas affaiblie.

Deux autres fixtures U1 ont été corrigées : la variante d'alias n'alloue plus
une valeur de secours devenue inutilisée, et la variante de résultats de
branches incompatibles détruit son résultat propriétaire avant de rendre un
Int. Le match `Ok(_)` qui ignorait un résultat propriétaire imbriqué devient
un refus explicite ; sa variante admise nomme puis détruit le payload.

## Mutations

`python3 tests/run_handle_obligation_mutations.py` travaille dans des copies
temporaires en gardant les oracles inchangés. Trois mutations détectées :

1. Réautoriser l'abandon synchrone : les chemins sans attente sont acceptés
   à tort par le modèle de branches.
2. Réautoriser l'abandon async : drop et sorties sans attente sont acceptés.
3. Omettre le nettoyage après échec de lancement : le pool de capacité un
   reste occupé et la tentative de réemploi échoue avec `pool capacity exceeded`.

La campagne est ciblée ; elle ne mesure pas une couverture générale des
défauts ni une preuve de sûreté.

## Écarts restant dans le brouillon 04

- AS7 : borne statique/capacités explicites par pool, directive
  `async_pool_sizes` et récursion. La capacité C fixe actuelle ne satisfait
  pas à elle seule ces règles.
- RT2–RT4 : installation publique directe dans main, interface de scheduler,
  files/réveils/équité, migration entre polls et spawn_blocking. La politique
  actuelle de créer un thread par spawn reste permise, mais ne démontre pas
  les capacités du scheduler visé.
- RT5–RT6 : types publics `runtime::Handle<T>` et `runtime::Error`, variante
  LaunchFailed et enveloppes de résultats générales.
- RT8 : bloc synchrone `runtime::thread`, captures explicites et résultat
  inféré.
- SL1 : Select, ordre des branches éligibles, résultat unique et conservation
  des perdantes jusqu'à destruction.
- MT9 : gardes synchrones liées au thread et gardes async migrables. La
  syntaxe des constructeurs de mutex reste expressément reportée.
- Captures de structures et autres limites du backend async déjà consignées.

Le lot global reste ouvert. Les tests exécutés ne prouvent pas toutes les
combinaisons de chemins, ni l'absence générale de races ; aucun nouveau
passage TSan ou preuve formelle n'est revendiqué.
