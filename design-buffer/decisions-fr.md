[English](decisions.md)

# Décisions validées dans l’atelier

Les brouillons ci-dessous regroupent les décisions prêtes à transmettre
au chat d’implémentation. Chaque brouillon indique les règles à intégrer.

| Brouillon | Décisions |
| --- | --- |
| [01 — Résultats propriétaires](01-resultat-proprietaire.md) | Usage explicite, consommation par `drop` et motifs dans un `match` consommant. |
| [02 — Notation des transferts](02-marqueur-transfert.md) | Déplacement par valeur des types non `Copy`, `move a;` à l'entrée d'un bloc enfant, captures par valeur dans `move { ... }` et retour dans un nouveau receveur visible. Intégration dans le périmètre du noyau testé. |
| [03 — Dépilement des scopes](03-depilement-des-scopes.md) | Placement des valeurs transférées, récupération de la data stack et ordre imposé par les dépendances de nettoyage. |
| [04 — Async, runtime et Select](04-async-et-select.md) | Pools d’états, lancement, attente, scheduler, threads natifs avec captures nommées ou déduites, mutex et sélection. |
| [05 — Data stack et pools typés](05-data-stack-et-pools.md) | Data stack implicite, pools typés, transferts locaux, réemploi et régions grandissantes. |
| [06 — Type features](06-type-features.md) | Résolution statique, contraintes structurelles, modes du receveur et notation des directives. |
| [07 — Primitifs, conversions, résultats faillibles, copies et vues](07-conversions-resultats-copies-et-vues.md) | Primitifs numériques à largeur fixe et `bool`, sans type `Int` dans le noyau cible. Littéraux flottants `f64` par défaut, type précisé par annotation. `as`, `try_from`, résultats faillibles sans allocation, copies locales et découpes UTF-8. |
