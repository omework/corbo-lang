[English](ASYNC_FIELD_REFERENCE_RETURNS_CYCLE.md)

# Retours de projections de champs depuis une fonction async

Le relais helper synchrone → enfant async → retour synchrone signalé ouvert
ci-dessous est depuis corrigé dans
[ASYNC_HELPER_RESULT_CONTRACTS_CYCLE.md](ASYNC_HELPER_RESULT_CONTRACTS_CYCLE.md).

Cycle du 7 novembre 2026. Règles existantes : ST6–ST9/ST11–ST12/ST14,
B1/B2/B4a, AS8/AS12/AS13, MT3 et V5. Aucune règle modifiée.

## Implémentation

Le contrat async conserve désormais le chemin du champ Int direct ou de la
capacité &mut Int réempruntée. Les chemins se composent à travers les alias,
les fonctions async, les helpers et méthodes synchrones, les branches et
les attentes. Le C rend le pointeur réel sans déplacer la cible.

Après join, le vérificateur reconstruit les réservations de champ et de cible
à partir du contrat. Le champ retourné reste protégé, ainsi que son porteur
et sa cible ; les champs disjoints redeviennent disponibles. Avant l'attente,
la capture continue de réserver tout l'argument exigé par la signature.
Dans un parent async, les prêts du résultat sont également projetés.

Le contre-exemple `validation/open-async-field-reference-return.crust` est
maintenant accepté et affiche 21, 2, 3, 21. Son ancien journal conserve le
refus historique ; `validation/async-field-reference-return-fixed.c` conserve
le nouveau C. Les diffs sont `validation/async-field-returns-*.py.patch`.

## Preuves exécutées

- `async-field-returns-initial-o0.log` : huit méthodes réussies.
- `async-field-returns-final-o0.log` : 12 méthodes, 12,542 s, OK.
- `async-field-returns-final-o2.log` : 14 méthodes, 15,940 s, OK.
- `async-field-returns-complete-final-o0.log` : 14 méthodes, 23,075 s, OK.
- `async-field-returns-regression-o2.log` : 34 méthodes de retours, liaisons
  locales et réemprunts antérieurs, 28,393 s, OK. Ce passage précède le dernier
  ajout de fixtures et la correction du lookup de champs imbriqués.
- `async-field-returns-final-mutations-o2.log` : baseline de 13 méthodes,
  21 exécutions C (dont deux avec refus de lancement injecté), 50 programmes
  invalides vérifiés aux deux entrées, soit 100 contrôles.
- Modèle indépendant : 24 combinaisons de l'ensemble des champs possibles,
  du champ accédé, de lecture/écriture et du dernier usage ; 18 exécutions
  C et six refus. L'état attendu est calculé par un dictionnaire indépendant.
- `async-field-returns-recapture-o2.log` : une méthode supplémentaire réussie
  après la baseline ; recapture du résultat de join par une autre tâche,
  une exécution et quatre programmes refusés aux deux entrées.

Clang C11 pthread, UBSan fatal, O0/O2. Les tests portent aussi sur les pools
du porteur, leur réemploi après drop, les échecs de lancement, les branches
d'erreur, l'ascendance mutable et le reset historique opt-in. Le profil normal
continue de refuser reset. Aucun résultat ASan/TSan ni preuve générale ajouté.

## Mutations et limites

Cinq fautes détectées : perte du chemin dans le contrat, perte du suffixe
dans un relais, perte du prêt après await, réservation indue du porteur entier
après join, décalage du pointeur retourné. Les détections comprennent des refus
injustifiés et des valeurs incorrectes, pas seulement des accès mémoire invalides.

Une mutation a survécu : remplacer les chemins cible/capacité du champ &mut
par son seul chemin de stockage. Dans les cas exercés, ce chemin conserve
encore le porteur et ses dépendances transitives ; les quatre accès prématurés
testés restent refusés. Ce constat n'établit pas l'équivalence générale de
la mutation et reste une limite de couverture. Le runner termine donc avec
un statut non nul, explicitement conservé ; aucune détection fictive.

Audit élargi de cette survivante : `async-field-returns-survivor-audit-o2.log`.
Les 14 méthodes du lot (22 exécutions C, 54 programmes refusés dans deux stages)
passent encore avec le code muté, puis les 24 cas du modèle passent également
(18 exécutions, six refus). Le compteur générique affiche zéro refus pour le
modèle car celui-ci importe sa propre entrée de vérification ; ses six refus
sont contrôlés par ses assertions et son bilan. L'audit renforce le constat
de redondance dans ce périmètre, sans établir une équivalence universelle.

La première campagne de mutations s'est arrêtée sur une ancre ambiguë du
pointeur de retour (deux occurrences). L'ancre finale cible uniquement le
retour de référence. Les deux journaux sont conservés.

## Échecs intermédiaires et écarts ouverts

`async-field-returns-targeted-o2.log` conserve 15 erreurs : fixture de méthode
mal écrite, initialisation imbriquée non supportée, et régression du traitement
builtin push_new par le résolveur de méthodes. Ce dernier n'intercepte plus
les builtins sans contrat synchrone. `async-field-returns-complete-o0.log`
conserve 14 erreurs (certaines dupliquées par l'import d'une classe de test) :
fixture de méthode et lookup de champs imbriqués. La résolution utilise maintenant
le layout aplati. L'import du modèle ne fait plus découvrir la classe dupliquée.

Le test des projections imbriquées initialise un objet complet avec ses défauts
puis écrit ses champs. La construction par littéral de sous-structure n'est pas
masquée : `validation/open-nested-structure-literal.crust` et son diagnostic
conservent cet autre écart pour la suite.

ST13 reste ouvert en async : retourner la valeur d'un champ partagé en détachant
le résultat du porteur. Le programme minimal est conservé dans
`validation/open-async-detached-field-return.crust`. Les remplacements de
références de champs, les types de cibles plus généraux et les autres lots
de l'objectif restent ouverts.

Autre composition encore refusée : si l'enfant async obtient lui-même son
résultat d'un helper synchrone, puis qu'un appelant synchrone retourne le
résultat de join, l'inférence des résumés n'a pas encore les contrats des
helpers à disposition. Contre-exemple et diagnostic conservés dans
`validation/open-async-helper-result-sync-contract.crust` et son journal.
Le cas direct chez main est testé et accepté ; cette limite concerne le
relais supplémentaire par un contrat synchrone.

La régression native élargie `validation/async-field-returns-native-o2.log`
est terminée : 269 méthodes, 199,684 s, OK. Elle précède le complément de
recapture et le correctif de relais synchrone ci-dessous.

## Relais synchrone après join

Un contre-exemple supplémentaire est conservé dans
`validation/probe-sync-relay-async-field-return.crust`. Une fonction synchrone
lance la tâche, attend son handle, puis restitue la référence du champ.
Le premier diagnostic (`un tableau de références Int exige des cibles Int`)
venait de l'effacement du chemin dans le résumé symbolique de résultat.
`results.py` conserve maintenant la projection dans ce résumé. Il a ensuite
fallu conserver l'ascendance de capture lors de la reconstruction des chemins
de join : sans elle, une référence parent encore vivante apparaissait comme
un emprunt concurrent, produisant `emprunt mutable non exclusif`.

Le nouveau test passe par deux auxiliaires synchrones et distingue le champ
frère des accès interdits à la cible et au porteur. Une exécution C donne
21, 8, 21 ; quatre programmes invalides sont contrôlés aux deux entrées.
`async-field-returns-sync-relay-o0.log` : une méthode, 0,382 s, OK.
La régression et les mutations de ce complément sont conservées dans
`async-field-returns-relay-regression-o2.log` et
`async-field-returns-relay-mutations-o2.log`.

Résultats finaux de ce complément : 42 méthodes, 37,343 s, OK à O2.
Baseline des mutations : 15 méthodes, 9,518 s, OK ; 23 exécutions C et
58 programmes invalides contrôlés dans les deux stages (116 contrôles).
Sept mutations détectées, y compris l'effacement du chemin dans le contrat
synchrone et la perte d'ascendance de join ; la mutation précédemment survivante
survit toujours au cas ciblé. Aucun taux global de détection n'en est déduit.
Le test supplémentaire de recapture et celui du relais synchrone ne figuraient
pas dans les 269 méthodes de la campagne native antérieure ; la sélection
finale de 42 méthodes et la baseline finale les couvrent.
