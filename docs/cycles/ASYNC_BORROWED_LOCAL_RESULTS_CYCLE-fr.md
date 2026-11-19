[English](ASYNC_BORROWED_LOCAL_RESULTS_CYCLE.md)

# Résultats locaux async contenant des emprunts

## Portée et règles

Ce lot applique les brouillons 01/03/04/05, B1/B2/B4a, D1, L1/L2/L6/L7,
T1/T6, ST6–ST15 et AS8–AS14. Aucune règle normative n'est changée.
Le programme `validation/open-async-result-storage-borrowed.crust` est
maintenant compilé et exécuté. La racine locale reste un T, construit dans
la data stack du receveur, avec son adresse stable. Ses champs empruntés ne
possèdent pas leurs cibles et ne prolongent pas implicitement leurs durées de vie.

Les structures prises en charge dans ce lot ont des champs Int, &Int et
&mut Int. Les origines de leurs champs retournés proviennent de paramètres
empruntés durables décrits par le contrat de terminaison de la tâche.
Les captures propriétaires de structures empruntantes et les graphes mixtes
généraux ne deviennent pas pris en charge par ce raccordement.

## Implémentation

- Chaque champ du résultat conserve ses cibles et ses réservations à travers
  la création d'une tâche, une fabrique, un transfert, await, spawn/join et
  l'extraction du payload Ok. Les branches de Select réunissent les cibles
  possibles ; les captures des perdantes restent protégées jusqu'au nettoyage.
- Le suivi des prêts stockés distingue les champs, les cibles et les porteurs.
  Le détachement d'un champ partagé n'impose pas de garder son porteur vivant ;
  la cible reste protégée jusqu'au dernier usage de la référence détachée.
- Les fonctions synchrones qui attendent un paramètre Execution conservent
  les origines des champs dans leur contrat, y compris à travers un relais.
  L'extraction d'un Result conserve aussi ses métadonnées symboliques.
- La vérification symbolique distingue une racine locale produite par une
  tâche des pools de ses captures. Une alternative fraîche locale est placée
  dans le stockage du receveur ; la racine de la tâche déjà créée est conservée.
  Le slot de l'alternative fraîche est récupéré s'il n'a pas été construit.
- Une construction locale directe dans le corps async utilise le même suivi
  de champs que la construction en pool. Son layout est statique : le résultat
  ne garde aucun pointeur vers des métadonnées dans l'état de la tâche libérée.

## Défauts découverts et corrections

Le raccordement initial perdait les dépendances lors de l'extraction Ok et
laissait certains prêts associés au temporaire C au lieu du receveur. Les
premiers journaux conservent ces refus et les corrections successives.

Le helper qui retourne le résultat d'une attente ou une valeur de secours
révélait trois écarts : classification locale manquante, perte des emprunts
dans le contrat après extraction et absence de récupération du slot réservé
à la branche non prise. Ce dernier défaut compilait, puis le runtime arrêtait
le programme avec `source still has live allocations`. Les deux chemins sont
maintenant exécutés, avec un refus de lancement injecté pour la branche Err.

Le modèle de boucle a initialement attendu à tort que sa cible initiale soit
libérée avant le dernier usage du résultat alors que while peut ne pas itérer.
La fixture a été corrigée pour détruire le porteur avant cette cible, sans
changer la règle conservatrice à la jonction. Deux erreurs de syntaxe dans
des fixtures sont également conservées dans les journaux intermédiaires.

Une mutation de layout a d'abord survécu : elle visait un constructeur de pool
non exercé par la sonde utilisant un helper synchrone. La construction directe
ajoutée au test a exposé une forme valide encore refusée. Ce raccordement est
implémenté ; la faute vise désormais son layout statique et est détectée par
les mêmes oracles d'identité et de destruction, sur les deux constructions.
La survie initiale n'est pas comptée comme une détection.

## Preuves exécutées

- Suite finale O0 : **17 méthodes réussies**, 21,896 s ; **36 exécutions natives**
  et **36 programmes invalides refusés aux deux étapes**, soit 72 contrôles.
  Journal : `validation/async-borrowed-local-results-final-counted-o0.log`.
- Baseline finale O2 : **17 méthodes réussies**, 22,075 s ; **neuf mutations
  détectées**, aucune survivante ou inconclusive dans cette campagne finale.
  Journal : `validation/async-borrowed-local-results-final-mutations-o2.log`.
- Régression élargie antérieure au complément de construction directe :
  **239 méthodes, 238 réussies et une erreur**, 216,031 s.
  Journal : `validation/async-borrowed-local-results-regression-o2.log`.
  L'erreur est une fixture historique créant `old` sans usage explicite.
  Elle est reproduite avec le compilateur sauvegardé avant le lot, préchargé
  depuis sa copie temporaire : `async-borrowed-local-results-historical-baseline-preloaded.log`.
  Le premier essai sans préchargement importait le compilateur courant via le
  chemin du module de test ; il ne constitue pas une preuve sur l'ancien code.
  La fixture lit désormais old avant le reset historique et garde son assertion
  de destruction unique. Le profil public ne réintroduit pas reset.
- Régression sur le compilateur final : **98 méthodes réussies**, 74,357 s.
  Stockage des résultats, graphes propriétaires, placement parent, helpers,
  pools de structures, exigences de stockage et runtime de croissance.
  Journal : `validation/async-borrowed-local-results-final-regression-o2.log`.
- Les deux modules historiques après correction de la fixture passent :
  **49 méthodes réussies**, 25,961 s, avec UBSan demandé explicitement.
  Journal : `validation/async-borrowed-local-results-legacy-fixture-regression.log`.

Tous les processus finaux cités sont terminés avec code 0. La régression
élargie initiale et la campagne de mutations initiale restent des échecs
historiques explicités ci-dessus, pas des passages réussis réétiquetés.

Commandes de reproduction depuis la racine :

```sh
CRUST_TEST_OPT=-O0 python3 validation/count_async_borrowed_local_results.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 tests/run_async_borrowed_local_result_mutations.py
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_local_owned_result_graphs test_async_local_parent test_async_local_struct_helpers test_async_result_storage test_async_struct_pools test_storage_requirements test_growth_runtime
PYTHONPATH=.:tests CRUST_SANITIZE=undefined python3 -m unittest test_borrowed_returns test_reassignment
```

Les suites ciblées et les 98 méthodes utilisent les harnais Clang C11/pthread,
avec UBSan fatal pour les exécutions natives concernées et O0/O2 selon le
journal. Les anciens modules de reset utilisent leur profil historique ;
leur relance demande explicitement `CRUST_SANITIZE=undefined`.

Le modèle indépendant énumère les quatre dispositions parent/enfant de deux
cibles : les deux doivent survivre au receveur. Les sondes C observent l'adresse
de la racine et de sa cible, le relâchement du slot d'état enfant, puis le
nettoyage normal ou suspendu. Elles comptent une seule destruction de la cible
et du porteur. Les mutations retirent des prêts, des origines, un transport
après attente ou le nettoyage de la réservation ; la dernière fait détruire
une cible empruntée comme si elle était possédée. Les oracles restent inchangés
dans les copies mutées. Ce sont des familles finies, pas un taux global de sûreté.

## Limites et suite

Le retour explicite `Result<View,runtime::Error>` par un helper reste non
raccordé au système de signatures ; le programme valide est conservé dans
`validation/open-sync-join-local-payload-type.crust`. Ce lot couvre le helper
qui extrait et retourne View lui-même, sans supprimer l'autre exigence.
Les origines générales par projections de champs, les captures propriétaires
d'agrégats empruntants, les graphes mixtes, les signatures générales et les
deux arbitrages sur les handles lancés restent ouverts. Les sources locales
inconnues ne sont pas promues. Pas de nouvelle mesure ASan/TSan ni de preuve
générale de sûreté, d'absence de course ou d'optimalité de placement.

Snapshot : `/tmp/crust-before-async-borrowed-local-results`.
Diffs : `validation/async-borrowed-local-results-*.py.patch`.
L'objectif complet reste actif et incomplet.
