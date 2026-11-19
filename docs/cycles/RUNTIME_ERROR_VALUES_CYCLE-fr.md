[English](RUNTIME_ERROR_VALUES_CYCLE.md)

# Cycle RT5/RT6 — Valeurs runtime::Error

## Portée et règles

Application des règles déjà retenues dans le brouillon 04 et
ASYNC_MULTITHREAD_RULES.md, sans changement normatif. `runtime::Error` devient
une valeur typée : construction de `runtime::Error::LaunchFailed`, extraction
avec `Err(error)`, copie par liaison, annotation, réaffectation, paramètre et
retour synchrones. Les tâches peuvent également capturer et retourner cette
valeur, la conserver après yield, la recevoir par await direct ou dans le
résultat de join/await d’un handle.

Le code C distingue le statut de lancement de la valeur retournée :
`CrustJoinResult.runtime_error_value` contient un résultat métier de type
runtime::Error ; `status` décrit le lancement. L’erreur extraite ne conserve
aucune dépendance aux captures détruites ni aux emprunts terminés par l’attente.
La séparation des types interdit son utilisation comme Int, u8 ou référence
vers Int. Les anciens `Err(valeur)` des vecteurs conservent leurs charges utiles
et leurs contrats.

Les interactions réexaminées sont AS2/AS8/AS10/AS12, RT4–RT7, MT1/MT3/MT5/MT6,
U1, les transferts explicites, les sorties de boucle et le drop. Le retrait du
reset public reste inchangé ; les tests historiques de reset utilisent le
profil explicitement réservé à la régression. Ce cycle ne prétend pas vérifier
les autres types de résultats ni l’ensemble des chemins du compilateur.

## Défauts trouvés et corrections

- L’affectation async passait par l’évaluateur Int et rejetait une erreur valide.
  Elle utilise désormais l’évaluateur du type runtime::Error.
- Le bras Err d’un résultat propriétaire était invalidé avant l’extraction de
  son erreur. L’extraction lit maintenant le tag sauvegardé par match, sans
  rouvrir l’accès au résultat consommé ni lire sa charge utile.
- Un match async avec un unique joker refusait un sujet runtime::Error calculé
  par if. Le sujet est évalué une fois et son type est contrôlé.
- Le résultat d’un break synchrone était traité comme une allocation et causait
  une exception Python. Le résultat runtime::Error a maintenant son type C et
  sa représentation de valeur sans allocation.
- Le drop d’une liaison runtime::Error est maintenant reconnu dans les deux
  contextes. Il invalide cette liaison, sans invalider sa copie indépendante.

Le premier test de réaffectation omettait l’usage de la première valeur reçue :
le diagnostic U1 était correct. Le test lit désormais cette valeur avant son
remplacement. Le générateur de branches utilise un discriminant Int dans les
deux contextes ; l’ancien nom Bool n’était pas accepté par les signatures
synchrones de ce prototype.

L’élargissement aux tests de boucle a retrouvé quatre scénarios historiques
sans usage explicite d’une allocation reçue (`old`, `temp`, `b` ou l’ancien
receveur). Des lectures ont été ajoutées dans `test_loop_results.py`. Les oracles
de destruction, de réemploi, de limites de portée et les voisins invalides
restent identiques. Il ne s’agit pas d’un relâchement de U1.

## Preuves exécutées

Clang Homebrew 20.1.3, arm64 macOS, C11. Les 10 nouvelles méthodes exécutent
19 binaires par niveau d’optimisation et vérifient 27 programmes refusés.
UBSan est fatal (`-fsanitize=undefined -fno-sanitize-recover=all`). Les oracles
C de tâches activent également les avertissements stricts et pthread.

| Vérification | Résultat | Trace |
| --- | --- | --- |
| Nouveau lot final O0, UBSan | 10 méthodes, 10,525 s, succès | validation/runtime-error-values-O0-final.log |
| Nouveau lot O2 + résultats propriétaires et boucles | 37 méthodes, 22,241 s, succès | validation/runtime-error-values-O2-validated.log |
| Boucles historiques avec UBSan explicitement activé | 18 méthodes, 11,121 s, succès | validation/runtime-error-loop-ubsan.log |
| Premier lot O2 + spawn_blocking, handles, capacités, features async | 34 méthodes, 36,639 s, succès | validation/runtime-error-values-O2.log |
| Régressions async, contrats et scheduler sélectionnées | 14 méthodes, 46,189 s, succès | validation/runtime-error-regression.log |
| Charges utiles Err de vecteurs et résultats propriétaires | 37 méthodes, 32,897 s, succès | validation/runtime-error-vector-regression.log |
| Mutations du lot précédent rejouées | 5 détectées | validation/runtime-error-blocking-mutations.log |
| Mutations ciblant les valeurs d’erreur, version finale | 4 détectées | validation/runtime-error-values-mutations-validated.log |

Dans le groupe de 37 méthodes, les nouveaux tests et les tests de résultats
propriétaires utilisent O2/UBSan. Le helper historique des boucles ignore
CRUST_TEST_OPT ; celles-ci ont donc aussi été rejouées séparément avec
CRUST_SANITIZE=undefined (optimisation par défaut). Le premier groupe de 34
méthodes précède les ajouts des cas loop, joker calculé et drop : il ne remplace
pas les vérifications finales. Aucun test n’a été sauté dans ces exécutions.

Les modèles indépendants comprennent une table de quatre chemins
(synchrone/async × choix 0/1), dont les marqueurs et le résultat sont fixés sans
consulter le compilateur. Le modèle historique de destruction par blocs a
également été rejoué avec la graine 20261103 (huit programmes et leurs voisins
invalides). Les autres oracles contrôlent le succès et le refus injecté du
scheduler, le réemploi de la même adresse, la destruction unique, la libération
d’un emprunt mutable après join à travers deux contrats, et l’indépendance du
résultat après drop de sa cible initiale.

Le programme `validation/open-runtime-error-value.crust`, auparavant refusé,
est conservé et exécuté avec succès (7) et échec de lancement injecté (1).
L’ancien diagnostic reste dans `validation/open-runtime-error-value.log` comme
preuve historique.

## Mutations et limites des oracles

Quatre fautes sont injectées uniquement dans des copies temporaires : statut
Err remplacé par zéro ; lecture du champ Int à la place du résultat enum async ;
acceptation d’une erreur comme Int ; statut Err async remplacé par zéro.

Deux ont survécu au premier passage (`runtime-error-values-mutations.log`).
Un match synchrone à une seule variante n’observait pas la représentation
corrompue. Les programmes de test ont été enrichis : recapture de l’erreur dans
une tâche après nettoyage et match dans la tâche avant retour. Ces chemins
observent désormais les deux corruptions ; les quatre mutations sont détectées.
Le défaut initial de l’oracle n’est pas caché et aucun taux global n’en est déduit.

Il n’y a ici ni preuve formelle ni campagne aléatoire de concurrence. Le
scheduler injecté refuse le lancement sans exécuter la tâche, conformément à
son contrat C interne. La sûreté de C arbitraire n’est pas évaluée. Les erreurs
plus riches qu’une unique variante et la totalité des conteneurs de cette valeur
ne sont pas couvertes.

## Travail encore ouvert

`runtime::Handle<T>` public, les signatures générales de Result<T,runtime::Error>,
le remplacement public du scheduler, les réveils, l’équité, runtime::thread,
Select et les gardes de mutex restent à intégrer ou compléter. La syntaxe de
construction des mutex reste reportée par points-ouverts.md. Les autres lots
des sept brouillons ne sont pas déclarés achevés par ce cycle.

État historique à la clôture de ce cycle (résolu ensuite dans
[PLAIN_JOIN_CONTRACTS_CYCLE.md](PLAIN_JOIN_CONTRACTS_CYCLE.md)) :
le prochain écart était reproduit par `validation/open-runtime-result-contract.crust` :
un join Int reçu puis relayé dans deux contrats explicitement annotés
Result<Int,runtime::Error> est encore refusé. Le diagnostic exécuté est conservé
dans `validation/open-runtime-result-contract.log`. Cette restriction ne vient
pas des règles validées.

Commandes de reproduction :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_runtime_error_values -v
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_runtime_error_values test_loop_results test_owned_results -v
CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_loop_results -v
python3 tests/run_runtime_error_regression.py
python3 tests/run_spawn_blocking_regression.py
python3 tests/run_runtime_error_mutations.py
python3 tests/run_spawn_blocking_mutations.py
```
