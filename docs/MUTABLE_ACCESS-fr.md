[English](MUTABLE_ACCESS.md)

# Références mutables : permission de mutation

Décision retenue le 21 novembre 2026. Il s'agit d'une évolution sémantique du
core, sans nouvelle syntaxe ni API. Corboc sépare désormais permission
de mutation, effets sur le contenu et protection par verrou. Une validation ciblée
est terminée ; les effets et identités de verrou non démontrés restent refusés.

## Restriction actuelle du prototype — 24 novembre 2026

Le prototype autorise à nouveau un seul emprunt mutable actif par place qui se
chevauche. Cette décision remplace les clauses de coexistence MA1–MA2 ci-dessous.
La dernière utilisation peut terminer un emprunt avant la fin du bloc ; des
champs prouvés disjoints peuvent être empruntés indépendamment. Emprunter
`self.tracker` ne réserve pas `self.file`. Les deux dépendent toujours de la
durée de vie de `self`.

Permission de mutation, possession, validité, contrats de verrou et fin de
branche restent distincts. Un verrou ne permet pas à lui seul plusieurs emprunts
mutables qui se chevauchent. Le partage via une API de verrou en `&self` conserve
son contrat de synchronisation.

La décision du 21 novembre est conservée ci-dessous comme historique, soumise
à cette restriction.

**MA1 — Permission, pas unicité.** `&mut T` autorise la mutation de la place
référencée. Il n'affirme pas l'absence d'autres références, mutables ou partagées.
Plusieurs références mutables peuvent coexister. `&T` autorise la lecture par
cet accès ; il ne garantit pas à lui seul que le contenu reste inchangé par
un autre accès autorisé.

**MA2 — Compatibilité des accès.** N5 concerne les accès et leurs effets, pas
le nombre de références. Des accès séquentiels peuvent employer des références
différentes vers la même place. Si des accès potentiellement concurrents se
chevauchent et qu'au moins un écrit, le compilateur doit établir la synchronisation
requise, la protection de chaque accès et l'identité du verrou correspondant.
Créer les références sous verrou ne protège pas leurs usages ultérieurs. Les
preuves de places disjointes et d'exécution ordonnée restent utilisables.

**MA3 — Validité préservée.** N2, N4, N6, N7 et N8 restent applicables. Une
permission de mutation ne donne ni possession ni droit de destruction par emprunt.
La possession est nécessaire à la destruction, sans autoriser l'invalidation d'une
place encore requise. Retrait, remplacement et récupération du stockage conservent
les obligations de dépendance. Modifier le contenu n'invalide pas automatiquement
sa référence. Les règles de déplacement, copie, liaison mutable et construction
des références restent inchangées ; les références mutables ne deviennent pas Copy.

**MA4 — Fin de branche.** Chaque branche conserve ses dépendances jusqu'à une
fin établie sur le chemin concerné, notamment via `#(branch: join=...)`. Finir une
branche ne termine pas les autres. Sans fin déclarée ou démontrée autrement,
le compilateur ne peut pas supposer les usages terminés. Détruire un handle
ne prouve pas la fin. Les résultats empruntés gardent leurs dépendances après
la fin de l'exécution. Les effets de succès/échec, les sorties anticipées et
les suspensions restent suivis par chemin. La jonction établit une relation
de durée de vie, pas la synchronisation des accès qui la précèdent.

**MA5 — Exclusivité explicite des verrous.** `#(lock: on=...)` et
`through_result=true` gardent leur sens et leurs responsabilités d'implémentation.
Leur intervalle exclusif est distinct de la permission d'écrire. Une seconde
acquisition bloquante dont la libération dépend du retour de cet appel reste
refusée. Un verrou porté par un résultat se termine selon son contrat de
libération/destruction, pas simplement à sa dernière utilisation syntaxique.
Le compilateur s'appuie sur le contrat déclaré ; il ne prouve pas le mécanisme
natif de verrouillage.

**MA6 — Preuve absente : refus.** Corboc refuse une violation ou une obligation
de durée de vie, synchronisation ou chemin qu'il ne peut pas établir. Il ne doit
pas supposer `&mut` unique pour accepter un effet inconnu. Les contrats transportent
ces informations à travers appels, captures, agrégats et résultats.

Ces clauses remplacent les obligations historiques d'unicité des emprunts mutables
et d'exclusion automatique par réemprunt, notamment dans B1/B2, AS9/AS15 et
MT1/MT2/MT8. Elles préservent les contrats de verrou, les restrictions liées à
l'invalidation réelle, la possession et les durées de vie des branches. Les API
peuvent exiger une exclusion justifiée par leurs effets ou contrats explicites.
La notation existante suffit. Le plan est consigné dans
`corboc/docs/MUTABLE_ACCESS_PLAN.md`, avec le rapport d’implémentation et ses
limites dans `corboc/docs/MUTABLE_ACCESS_CYCLE.md`. Les anciens rapports et tests ne valident
pas encore cette évolution.

## Noms ordinaires des types de verrou

`Mutex` et `AsyncMutex` n’ont aucun statut builtin ni réservé. Déclaration,
paramètres de type et constructeurs suivent la résolution nominale ordinaire.
Les faits de synchronisation viennent des contrats, pas du nom. Le raccourci objet
`#(lock)` fait hériter le contrat du receveur aux méthodes d’instance publiques ;
la réentrée checked sur le même objet est refusée. Voir MT11 dans
[les règles async et multithread](ASYNC_MULTITHREAD_RULES-fr.md).
