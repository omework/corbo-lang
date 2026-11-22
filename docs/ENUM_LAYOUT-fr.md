[English](ENUM_LAYOUT.md)

# Stockage compact des enums

Statut : conception retenue, consignée le 22 novembre 2026. Non implémentée.
Périmètre : disposition mémoire et abaissement du compilateur ; aucun changement
à la grammaire ou aux API.

## Implémentation actuelle

Les enums nominales ordinaires occupent actuellement un tag suivi d’emplacements
séparés pour tous les champs de toutes les variantes. Les unions C par champ
fournissent des noms alternatifs ; elles ne partagent pas le stockage entre
variantes. Une seule variante est active, mais les champs des autres occupent
aussi de la place. Cette limite du backend est distincte des règles EN1/V3.

## Amélioration retenue

Représenter une enum inline ordinaire par un tag et une seule zone de données
partagée. Chaque variante à champs possède sa disposition dans cette zone.
Une variante vide ne demande aucun stockage de données. La zone partagée
accueille les données de la plus grande variante et respecte l’alignement
le plus contraignant parmi les variantes.

La taille complète tient compte de l’alignement, du remplissage propre à la cible
et des éventuelles métadonnées de destruction existantes. On n’additionne pas
les tailles des données de toutes les variantes. Réduire le tag ou exploiter
des niches n’est pas exigé ; le tag actuel du backend est sur 64 bits. Cette
décision ne définit pas de format de sérialisation ni d’ABI externe stable.

Pour `Empty`, `Number(i64)` et `Pair(i32, bool)`, une disposition 64 bits
habituelle, sans métadonnées de destruction supplémentaires, donne un tag puis
8 octets partagés : 16 octets au total au lieu des 24 actuels. Ces tailles
dépendent de l’ABI cible et ne constituent pas une garantie universelle.

## Intégration restant à implémenter

- [ ] Abaisser les variantes vers une zone partagée, avec leurs champs distincts.
- [ ] Employer la même disposition cible pour les tailles et alignements, le
      placement post-AST, les réservations de datastack, tableaux, slots de pool
      ordinaires et déclarations C, dont la représentation exposée à `@c`.
- [ ] Conserver construction, copies/moves, motifs, emprunts, égalité des champs
      actifs et destruction unique. Ne pas lire ni détruire une variante inactive.
- [ ] Valider tailles, alignements et opérations directement concernées sur les
      cibles pertinentes au moment de l’implémentation.

La stratégie interne des pools, dont le stockage par variante là où il existe,
reste une question séparée ; cette décision ne la remplace pas. Aucune
implémentation ni validation exécutable n’a été réalisée pour cette consignation.
