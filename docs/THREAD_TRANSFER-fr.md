[English](THREAD_TRANSFER.md)

# Déplacement entre threads

**TR1 — Restriction de déplacement entre threads.** Par défaut, les types peuvent
être déplacés vers un autre thread. Une struct ou enum peut l’interdire :

```rust
#(thread: transfer=false)
struct LocalResource {
    token: i64,
}
```

L’annotation exprime une exigence d’implémentation, par exemple une ressource dont
l’usage ou la destruction dépend du thread. Les moves dans le même thread restent
autorisés. Aucun verrou ni contrôle dynamique de thread n’est généré.

La restriction se propage par possession : champs imbriqués, tableaux, tuples,
payloads d’enum, allocations possédées et conteneurs. Un type contenant ne peut
pas lever la restriction d’un composant. Les spécialisations génériques conservent
l’annotation et les propriétés des champs. Les captures de closure sont les champs
de leur représentation concrète. Un état async est restreint s’il capture une
valeur possédée restreinte ou en conserve une à travers une suspension. Un résultat
restreint ne peut pas non plus revenir depuis un worker vers un autre thread.

Le compilateur refuse le passage d’une frontière de thread si les captures
possédées, l’état d’exécution ou le résultat contiennent un composant restreint.
Créer puis détruire la ressource entièrement dans un worker reste possible si elle
ne franchit aucune frontière et ne survit pas à une suspension migratable.
Déplacer une référence ne déplace pas la possession de sa cible : cette annotation
n’ajoute pas de classification analogue à Sync pour les références. Les contrôles
N4 de durée de vie, N5 de synchronisation et de fin de branche restent applicables,
indépendamment de TR1. Un verrou ne lève pas la restriction d’un champ possédé.

La propriété est déduite des liens des représentations après spécialisation,
indépendamment du nom concret du type. Toute preuve requise manquante reste un
refus. Seul `transfer=false` est une forme explicite ; l’absence est le défaut.
Le marqueur porte sur les structs/enums, pas sur les fonctions ou blocs.
