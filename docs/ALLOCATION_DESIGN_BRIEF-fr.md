[English](ALLOCATION_DESIGN_BRIEF.md)

# Corbo — Problème de placement et de dimensionnement mémoire

Corbo est un langage qui cherche à déterminer statiquement où placer les
valeurs, combien d’espace réserver et quand le récupérer. Nous cherchons des
propositions d’algorithmes pour passer de l’arbre statique du programme à un
plan de stockage. Les [règles de stockage](GROWING_REGIONS.md) définissent
le modèle cible. Les choix d’algorithme décrits ici restent ouverts.

## Le modèle à respecter

Le prototype distingue deux espaces, chacun avec un seul sens d’allocation.

| Espace | Contenu | Récupération |
| --- | --- | --- |
| Data stack classique | Valeurs de taille fixe, descripteurs de collections et zones des pools typés | Recul du curseur sur un suffixe libre après nettoyage. Le pool gère ses slots dans sa propre zone. |
| Data stack à régions | Contenus grandissants de `Vector<T>`, `String` et `HashMap<K, V>` | Le curseur interne d’une région peut revenir à son point d’entrée après nettoyage. Un emplacement de région intérieur peut être réutilisé via l’index des régions libres. |

Un descripteur de taille fixe désigne la région du contenu. Une région a
des bornes fixes après sa réservation. Le contenu peut grandir à
l’intérieur. La croissance, le transfert et le réemploi d’un autre
emplacement préservent les adresses garanties stables. La réservation
virtuelle et l’engagement des pages sont deux mesures distinctes.

Le placement doit préserver l’ordre d’exécution. Le compilateur peut
réserver l’emplacement d’une valeur chez son futur receveur avant de
l’initialiser. La construction a lieu au point prévu par le programme.
La destruction précède la récupération et aucune zone encore requise
par un emprunt, un résultat ou un thread ne peut être reprise.

Un scope qui demande un autre gabarit reçoit une stack à régions dédiée.
Le placement privilégie la stack à régions courante quand la coexistence
des allocations peut être établie. Si le placement y est impossible,
le choix d’une stack dédiée intervient avant la construction et conserve
la limite applicable à la région. Une croissance qui dépasse la borne
de sa région entraîne un diagnostic.

## Entrées disponibles

Le compilateur part de l’[arbre statique d’exécution](MEMORY_REPRESENTATION.md).
Une proposition peut s’appuyer sur les informations suivantes :

- Les scopes, leur point d’entrée chez le parent et leurs sorties. Les
  branches, appels, retours, ruptures et reprises donnent les chemins
  sur lesquels des allocations peuvent coexister.
- Les identités des emplacements et leurs types. La disposition du type
  concret donne la taille et l’alignement d’une valeur fixe. Le pool donne
  le type des slots et sa capacité.
- Les liens de possession, d’emprunt et de provenance. Ils indiquent
  quel stockage doit survivre à un transfert, à une attente ou à un
  nettoyage.
- Les opérations qui font croître un contenu. Leur effet en octets peut
  être connu, borné par un contrat ou encore inconnu. Une borne sur le
  nombre d’itérations peut, par exemple, borner les ajouts à un vecteur.

Le graphe doit conserver les faits établis même si une autre grandeur
reste inconnue. Un nombre de régions simultanées peut être borné alors
que la croissance d’un contenu ne l’est pas.

## Résultats attendus

**Un plan de placement.** Pour chaque allocation, indiquer la stack,
la zone ou région, l’emplacement ou son mode de calcul, le point de
réservation, le point de construction et les conditions de récupération.
Le plan indique quelles décisions sont statiques et quels contrôles
doivent subsister à l’exécution.

**Trois tailles.** Une borne supérieure justifiée pour le placement
choisi suffit. Une solution peut aussi rechercher un meilleur placement
et comparer son pic d’occupation à une borne inférieure.

| Paramètre | Grandeur à borner |
| --- | --- |
| `size` | Pic du curseur classique, avec alignement, réservations anticipées et trous intérieurs encore compris sous le curseur. |
| `region_size` | Plus grand besoin en octets d’un contenu qui utilise le gabarit global. |
| `region_stack_size` | Pic des emplacements de région réservés, y compris les emplacements vides d’un `count` explicite. Pour un gabarit uniforme, ce pic est multiplié par le pas aligné d’un emplacement. |

Pour chaque propriété de `#(datastack: size=4G, region_stack_size=4G,
region_size=100M)`, l’ordre de choix est la valeur explicite, puis la
borne statique, puis la valeur par défaut si la borne est inconnue.
Le défaut est de `100M` pour une région et de mémoire disponible
divisée par le nombre de cœurs CPU pour une data stack. Le nombre
d’emplacements peut rester déduit statiquement en utilisant un
gabarit de région choisi par défaut. L’annotation de scope
`#(stack_region: max_size=4M, count=8)` fixe un gabarit local
et un nombre facultatif d’emplacements réservés.

## Règles du plan de placement de référence

L’analyse de [destination finale](GROWING_REGIONS.md#1-placement-et-croissance)
s’exécute après la construction de l’AST et la résolution des
transferts. Elle suit chaque valeur jusqu’à son dernier receveur
sur chaque chemin et identifie le scope chargé de son nettoyage.
Le placement utilise ce résultat pour réserver la zone de
destination dès la construction, y compris quand la valeur remonte
plusieurs niveaux de scope.

Quand la construction du résultat a lieu dans une fonction appelée,
l’appelant réserve l’emplacement et lui fournit l’adresse. Une
fonction qui retransmet une valeur déjà construite conserve son
adresse. Le contrat indique quel effet s’applique au résultat.

Le plan traite en priorité le scope final qui reçoit le plus de
valeurs et place autant de valeurs que possible dans leurs scopes
finaux. Si le chemin est choisi avant la construction, chaque
destination peut avoir son propre emplacement. Si le chemin est
choisi après la construction, l’emplacement choisi doit survivre
à toutes les destinations possibles. Les réservations comptent
dans le pic d’occupation jusqu’à leur récupération.

Le plan distingue l’état de l’emplacement et la position du curseur.
Sur chaque chemin, un emplacement peut être **réservé**, **construit**
ou **libérable**. Un emplacement libérable peut encore se trouver sous
le curseur. Les opérations suivantes découlent des règles P3 et P4.

| Opération | Effet dans le plan |
| --- | --- |
| **Réserver** | Choisir une plage alignée dans une zone qui survit à tous les usages prévus. Comptabiliser la plage dès la réservation. |
| **Entrer dans un scope** | Sauvegarder le curseur après les réservations du parent destinées aux résultats de ce scope. |
| **Construire** | Initialiser la valeur à son point d’exécution, dans l’emplacement choisi. L’état passe de réservé à construit. |
| **Transférer** | Changer le rattachement de la valeur et conserver son identité et son adresse. |
| **Quitter un scope** | Sur chaque sortie, nettoyer les valeurs construites dont le scope doit encore assurer le nettoyage. Une réservation abandonnée devient libérable directement. Récupérer le suffixe libérable après le nettoyage, en conservant les emplacements qui doivent survivre. |

Un résultat construit sur plusieurs chemins exclusifs peut utiliser
un emplacement commun lorsque ces chemins alimentent le même receveur
et que la plage convient à leurs constructions. Le plan garde l’état
de cet emplacement sur chaque sortie. Ainsi, une sortie anticipée
abandonne une réservation vide, tandis qu’une sortie qui fournit le
résultat transmet la valeur construite.

Le pic se calcule sur les positions atteintes par le curseur. Une
jonction prend le maximum des chemins possibles en conservant, dans
chacun, les réservations communes qui y sont encore occupées.

## Traces du plan de placement

Les snippets suivants illustrent les mêmes opérations sur des chemins
différents.

### Transfert enfant → parent

Le parent réserve l’emplacement du résultat juste avant l’entrée dans
le bloc. Le bloc sauvegarde le curseur après cette réservation. Il
construit le résultat à l’adresse réservée quand l’exécution atteint son
initialisation.

```rust
struct Point {
    x: i64,
    y: i64,
}

fn main() {
    let point: Point = {
        let temporaire: i64 = 7;
        let nouveau = Point { x: 10, y: 20 };
        print(temporaire);
        nouveau
    };

    print(point.x);
}
```

Le dernier usage de `temporaire` suit la construction de `nouveau`.
Les deux emplacements sont donc nécessaires au point de construction.

Pour illustrer le placement, on suppose un curseur initial à zéro,
une base alignée sur 8, un `Point` de 16 octets aligné sur 8 et un
`i64` de 8 octets aligné sur 8.

| Point d’exécution | Événement | Plage d’octets | Curseur après |
| --- | --- | --- | ---: |
| Parent, juste avant l’entrée dans le bloc | Réserver l’emplacement du résultat. | `[0, 16)` | 16 |
| Entrée de l’enfant | Sauvegarder le curseur à 16. | — | 16 |
| Enfant | Initialiser `temporaire`. | `[16, 24)` | 24 |
| Enfant | Construire `nouveau` à l’adresse réservée. | `[0, 16)` | 24 |
| Sortie de l’enfant | Transmettre la responsabilité à `point`, nettoyer le temporaire et récupérer son suffixe. | `[16, 24)` récupérée | 16 |

Dans ce placement, le pic atteint est de **24 octets**. `point` désigne
l’adresse où `nouveau` a été construit. La réservation est comptée
avant l’initialisation. Un chemin qui quitte le bloc avant la construction
ne déclenche aucune destruction du résultat sur ce chemin.

Le format proposé pour comparer les placements associe à chaque
emplacement son identité, son scope de stockage, son offset, sa taille,
son alignement et ses points de réservation et de construction. Pour
chaque sortie, il indique les emplacements qui survivent, ceux qui sont
nettoyés et la position à laquelle le curseur peut revenir.

### Un receveur commun aux deux bras d’un `if`

```rust
struct Point {
    x: i64,
    y: i64,
}

fn afficher_point(choix: bool) {
    let point: Point = if choix {
        let temporaire: i64 = 7;
        let nouveau = Point { x: 10, y: 20 };
        print(temporaire);
        nouveau
    } else {
        let temporaire: i32 = 3;
        let nouveau = Point { x: 30, y: 40 };
        print(temporaire);
        nouveau
    };

    print(point.x);
}

fn main() {
    afficher_point(true);
    afficher_point(false);
}
```

Après l’évaluation de la condition et avant l’entrée dans le bras
choisi, le parent réserve un seul emplacement pour `point`. Les deux
constructions possibles sont reliées à cet emplacement dans l’arbre.
Chaque bras utilise le curseur après réservation comme repère d’entrée,
construit sa valeur à l’adresse réservée et récupère ses temporaires
à la sortie. Le pic du `if` tient compte de la réservation commune
et du plus grand espace temporaire des bras, alignement compris.
Le calcul global compte aussi les emplacements déjà occupés et les
éventuels temporaires de l’évaluation de la condition.

## Cas pour comparer les propositions

| Situation | Ce que la proposition devrait expliquer |
| --- | --- |
| Deux bras d’un `if` allouent des temporaires différents et le parent conserve une valeur | Comment calculer le pic par chemin et tenir compte du stockage commun. |
| Un bloc construit une structure fixe qui survit chez le parent | Où réserver son emplacement, quand la construire et comment récupérer le reste du bloc. |
| Une boucle de longueur inconnue crée puis nettoie une région à chaque itération | Comment borner le nombre de régions occupées indépendamment du nombre total d’itérations. |
| Un contenu dépend d’une entrée non bornée, mais une seule région peut être occupée | Comment conserver la borne de population et utiliser le gabarit par défaut. |
| Un scope lance plusieurs threads avec des contenus grandissants | Comment distinguer les régions des états simultanément vivants, puis récupérer la zone après leur nettoyage. Un thread autonome qui peut survivre au scope doit utiliser un stockage durable dès son lancement. |

## Questions ouvertes aux contributeurs

- Quel état abstrait suffit pour calculer des pics utiles à travers les
  jonctions, les boucles et les appels sans multiplier les chemins ?
- Quels résumés de fonction permettent de composer les pics de
  stockage, les allocations transférées et les bornes de croissance ?
- Quelle stratégie de placement limite l’alignement perdu et les trous
  tout en conservant un recul de curseur simple ?
- Comment arbitrer entre réemploi, ouverture d’une stack à régions
  dédiée et coût des métadonnées lorsque plusieurs gabarits coexistent ?

Une proposition peut couvrir une seule de ces questions. Une
description de ses entrées, de ses invariants, de ses cas indéterminés
et de ses coûts suffit pour la discuter. Les comparaisons utiles
incluent la mémoire virtuelle réservée, les pages engagées, le pic
du curseur, les octets immobilisés après destruction et le coût
d’analyse à la compilation.
