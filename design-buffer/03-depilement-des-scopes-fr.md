[English](03-depilement-des-scopes.md)

# Brouillon 03 — Dépilement des scopes et placement des transferts

## Sources de stockage

- **Data stack classique.** Source implicite des valeurs locales. Chaque valeur occupe un
  emplacement dans une plage d'octets, avec l'alignement requis. Le recul du
  curseur récupère un suffixe libre. Un trou intérieur est récupéré quand il
  fait à son tour partie d'un suffixe libre. La règle de dépilement ci-dessous
  vise cette source.
- **Pool typé (`pool<T>(n)`).** La capacité est exprimée en slots adaptés à
  `T`. Après destruction, un slot intérieur est réutilisable via l'index des
  slots libres, même si des allocations suivantes sont encore vivantes. Le
  curseur du pool peut aussi reculer sur un suffixe libre.

Voir L7 et P8 dans [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md) et la description
des deux sources dans [SCOPE_EXIT.md](../docs/SCOPE_EXIT.md#destruction-et-récupération-du-stockage).

## Règle retenue dans l’atelier

Dans une data stack classique, une allocation transférée au scope parent
est construite directement à l'emplacement réservé dans la plage du parent.
Elle conserve son adresse pendant le transfert. À la sortie du scope enfant,
le nettoyage détruit les allocations qui lui sont encore rattachées en
respectant leurs dépendances.
Le curseur de la plage enfant revient ensuite à sa position d'entrée.

Les dépendances nécessaires au nettoyage fixent les contraintes d'ordre.
Un destructeur qui lit une cible doit s'exécuter pendant que celle-ci est
vivante. Une référence stockée que le destructeur ne lit pas n'ajoute pas
de contrainte d'ordre. La cible doit néanmoins survivre à la référence
stockée. Par exemple, un champ du parent qui emprunte une valeur locale de
l'enfant doit être réaffecté à une cible durable avant la sortie de l'enfant.

Pour les valeurs de taille fixe, le compilateur tente d'empiler en dernier
celles qui seront détruites en premier. Un placement favorable permet de
récupérer plus tôt un suffixe libre. Si l'ordre ne peut pas être établi,
le dépilement ordinaire s'applique. La validité du programme est indépendante
de cette optimisation. Le placement préserve les durées de vie, les effets
d'initialisation et les adresses stables.

## Exemple admis

```rust
struct Point {
    x: Int,
}

fn main() {
    let resultat = {
        let temporaire = Point { x: 7 };
        print(temporaire.x);

        let conserve = Point { x: 9 };
        <- conserve
    };

    print(resultat.x);
    drop(-> resultat);
}
```

L'emplacement de `conserve` appartient à la plage du parent dès sa
réservation. Le dépilement de la plage enfant récupère le stockage de
`temporaire` et préserve l'emplacement et la valeur de `resultat`.

## Placement interdit

Pour ce même programme, placer `conserve` dans la plage qui sera récupérée
au retour du curseur enfant rendrait un objet vivant réutilisable. Ce cas
est un contre-exemple à ce plan de placement. Le programme source reste admis
si la réservation dans le parent est possible.

## Contre-exemples à chercher

- Un transfert conditionnel dont une autre branche sort sans recevoir
  d'allocation. Vérifier le statut de l'emplacement réservé et le bilan de
  nettoyage.
- Des transferts successifs à travers des scopes imbriqués. Vérifier que
  chaque recul préserve l'adresse et le stockage du résultat vivant.
- Une boucle qui produit un transfert sur un chemin et reprend sur un autre.
  Vérifier le réemploi des réservations, les limites de capacité et l'absence
  de récupération d'un résultat encore vivant.
- Deux chemins détruisant les mêmes allocations dans des ordres différents.
  Vérifier la récupération des suffixes, puis le retour au curseur d'entrée.

Exemple de conception examiné sur papier. Les contre-exemples ci-dessus
restent à rechercher et à valider.

## Règles à relier lors de l'intégration

- V5, T3, T5, L2–L4, L7, P3, P4 et P8 pour l'adresse, les transferts,
  l'ordre de nettoyage fondé sur les dépendances et les modes de récupération.
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
- ST10 pour la durée de vie d'une référence stockée après réaffectation.
  [STRUCTURES_METHODS.md](../docs/STRUCTURES_METHODS.md)
- G10 et G12 pour la récupération de la plage et la stabilité des valeurs
  vivantes. [GROWING_REGIONS.md](../docs/GROWING_REGIONS.md)
