[English](SYNC_HANDLE_FIELDS_CYCLE.md)

# Résultats de handles projetés dans les champs

## Périmètre et corrections

AS12/AS13, ST8 et ST11–ST14, B1–B5, D1/D3 et RT5 imposent de distinguer
la capture pendant l'exécution des dépendances conservées par son résultat.
Les règles normatives ne sont pas modifiées.

Une fabrique synchrone appelée dans un état async peut désormais retourner
un handle dont le résultat emprunte un champ Int inline, un champ imbriqué,
ou la cible d'un champ `&mut Int`. Un champ `&Int` retourné comme valeur
conserve sa cible extérieure sans retenir artificiellement son porteur.
La réception nommée et l'attente directe de la fabrique conservent les chemins.

Le relais des contrats perdait le chemin d'un champ mutable indirect et
retenait toute la structure. Il conserve désormais le chemin, la véritable
allocation cible et la capacité mutable d'origine. Le vérificateur comptait
aussi deux fois la même capacité : capture entière du handle, puis projection
de son propre résultat. Ces représentations sont réunies seulement lorsqu'elles
appartiennent au même handle. Les autres prêts continuent d'être comptés.

L'analyse des contraintes ignorait les résultats publics empruntés Int.
Un symbole de source de capture empruntée relie désormais le résultat de
`join`, ses usages et les contrats des relais. Une projection indirecte conserve
la source du champ ainsi que la réservation du porteur. Le test de reset est
exclusivement historique (`allow_legacy_reset=True`), conformément à PR1.

## Contre-exemples et erreurs de tests

`validation/open-sync-handle-field-result.crust` est maintenant accepté et
exécuté ; son ancienne erreur reste conservée dans le cycle précédent.
Les journaux initiaux de ce lot conservent les pertes de chemin et les
violations de l'invariant d'exclusivité provoquées par le double comptage.

Le premier modèle élargi terminait avec 29 erreurs : 28 scénarios valides
refusés par le double comptage et une initialisation imbriquée non prise en
charge dans une fixture. Cette dernière utilise désormais la construction
complète par défaut suivie d'écritures explicites ; ses assertions de valeur
et d'exclusivité ne changent pas. Le test négatif de drop importait aussi une
valeur trop tard dans le bras : l'import explicite est replacé à son entrée.
Le harnais d'appelant opaque a ensuite été corrigé pour installer les types,
sans installer les corps de fonctions. Les échecs intermédiaires restent visibles.

## Exécutions

`tests/test_sync_handle_fields.py` : neuf méthodes ciblées passent à O0
(24,138 s) et O2 (24,345 s), journaux `validation/sync-handle-fields-complete-o*.log`.
Clang C11, pthread, avertissements fatals, UBSan fatal ; timeout de compilation
30 s et d'exécution 10 s. Ces passages finaux incluent le complément d'appel
opaque direct et excluent les diagnostics d'invariant interne des refus attendus.
Les premiers passages groupés et compléments isolés restent dans les journaux
`sync-handle-fields-final-o*.log` et `sync-handle-fields-opaque-direct-o*.log`.

Le modèle indépendant croise trois ensembles de champs retournables, trois
champs écrits, l'ordre avant/après dernier usage et deux choix de branche :
36 scénarios, 28 exécutés et huit refusés aux deux entrées du compilateur.
Il ne consulte ni les contrats ni le C pour décider du résultat attendu.
Les tests voisins couvrent les captures indépendantes, la destruction du
porteur et de la cible, les champs disjoints, la suspension après réception,
les champs imbriqués et un refus de lancement injecté.

Le test de contraintes exige explicitement une relation de sources distinctes
dans les contrats de `finish` et `route`. Un appelant ne disposant que des
contrats accepte le pool indépendant et refuse celui de la cible. Le programme
admis est également exécuté en C. Les corps et définitions async sont absents
de cet appelant de test.

Régression handles : 43 méthodes O2, 63,180 s, toutes réussies dans
`validation/sync-handle-fields-contract-regression-o2.log`. Elle précède les
deux derniers tests ajoutés, le complément opaque et le dernier ajustement du
parcours des contraintes, couvert par les passages ciblés finaux et la relance
élargie ci-dessous.

Régression élargie des contraintes, champs, appels empruntés, vues, résultats
propriétaires et obligations d'attente : 107 méthodes O2 réussies en 77,799 s,
`validation/sync-handle-fields-expanded-final-o2.log`.
Le premier passage (`sync-handle-fields-expanded-o2.log`) compte 107 méthodes
et six erreurs sur les variantes invalides d'un test. Le nouveau parcours de
contraintes tentait d'inférer les retours concrets, hors du périmètre public de
ce correctif, avec un callback de diagnostic incorrect. L'extraction des
groupes de résultat utilise désormais le contrat public préétabli. Le suivi
des contraintes des handles concrets demeure un écart à traiter avec le relais
ci-dessous ; aucune règle normative de refus n'est ajoutée.

## Mutations

`tests/run_sync_handle_field_mutations.py` travaille sur des copies temporaires.
La campagne finale détecte cinq fautes : effacement de projection, double
comptage inline, double comptage indirect, effacement du symbole de résultat
emprunté et effacement de la source du champ indirect.

Une sixième mutation, qui efface la résolution concrète de ce symbole dans
le contrôle des sources, survit. Les autres contrôles continuent de refuser le
programme ; ces tests ne prouvent donc pas l'efficacité isolée de cette branche.
Le script termine avec le statut 1 pour signaler cette survivante. Les deux
campagnes et leurs diagnostics sont conservés, dont
`validation/sync-handle-fields-mutations-final-o2.log`. Aucun taux général de
détection n'est revendiqué.

## Limites et suite

Mise à jour : le contre-exemple du relais ci-dessous est corrigé dans
[CONCRETE_HANDLE_RELAYS_CYCLE.md](CONCRETE_HANDLE_RELAYS_CYCLE.md), avec suivi
des sources concrètes et de l'ordre historique des resets. Le constat initial
est conservé pour la traçabilité.

Nouveau contre-exemple : `validation/open-concrete-borrowed-handle-relay.crust`.
Un paramètre `Execution<leaf>` relayé à une fonction recevant
`runtime::Handle<&mut Int>` perd encore la capture dans son contrat de retour.
Les deux entrées le refusent : `contrat de retour : capture empruntée introuvable`.
Le journal `validation/concrete-borrowed-handle-relay-probe.log` reproduit cet
écart. Le descripteur du paramètre est modifié par la conversion publique
pendant l'appel interne : le contrat cherche encore la capture 0 tandis que
l'allocation porte désormais les groupes 2 et 4. Cette observation isolée est
dans `validation/concrete-borrowed-handle-relay-descriptor.log`.
C'est un défaut d'implémentation, pas une nouvelle règle du langage.

Les signatures et agrégats généraux, Select, le scheduler personnalisable et
le placement statique général restent ouverts. L'arbitrage sur la capture d'un
handle déjà lancé par une tâche inactive est inchangé. Aucun passage ASan/TSan,
aucune preuve formelle et aucune exhaustivité des ordonnancements ne sont
revendiqués. L'objectif global reste actif.

Snapshot : `/tmp/crust-before-sync-handle-fields`. Modifications conservées
dans `validation/sync-handle-fields-*.py.patch`.
