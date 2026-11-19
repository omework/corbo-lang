[English](05-data-stack-et-pools.md)

# Brouillon 05 — Data stack et pools typés

Décisions retenues dans l’atelier, à intégrer sur demande. Ce brouillon
complète le [brouillon 03 sur le dépilement](03-depilement-des-scopes.md)
et le [brouillon 04 sur les pools d’états async](04-async-et-select.md).

## Contrat de stockage

- Les valeurs créées hors d’un pool utilisent la data stack par défaut.
  Le compilateur gère l’empilement, le dépilement et le placement. La data
  stack classique ne constitue pas un type public et le programmeur ne
  la construit pas avec `stack(octets)`.
- Le placement des valeurs de taille fixe peut favoriser la récupération
  anticipée. Si le compilateur détermine que certaines valeurs sont
  détruites en premier, il les empile en dernier lorsque le placement le
  permet. À défaut, le dépilement ordinaire suffit. Ce choix d’optimisation
  est distinct de la validité du programme.
- Une structure locale peut être transférée au parent avec `<-`, comme
  un tableau local. Son type reste `T`, par exemple `Point`. La data
  stack réserve son emplacement dans la plage du parent selon le
  brouillon 03. Les emprunts et les dépendances restent vérifiés à
  chaque frontière.
- Le programmeur choisit un pool en écrivant `pool<T>(n)` puis
  `pool.new(...)`. Le pool reste dans son scope de création. Une fonction
  qui alloue dans ce pool le reçoit en `&mut Pool<T>`. Le type générique
  `Allocator` et les allocateurs personnalisés sont écartés de cette API.
- `pool.new(...)` produit un `A<T>`. L’allocation conserve son adresse
  et sa provenance lors des transferts. Son pool doit survivre au
  receveur. Après destruction, le slot peut être réutilisé même s’il est
  intérieur au pool. Pour un pool typé borné, l’épuisement arrête le
  programme avec un diagnostic.
- `ref()` et `mut_ref()` empruntent le handle `A<T>`. `vref()` et
  `mut_vref()` empruntent le contenu `T`. L’affectation par l’emprunt
  mutable du contenu modifie `T` en place. Ces quatre méthodes forment
  l’API d’emprunt retenue pour `A<T>`.
- Pour un `Vector<T>` local, le descripteur de taille fixe vit sur la
  data stack. Il contient une référence vers la donnée grandissante,
  stockée dans une région séparée. Le vecteur n’a pas de champ
  `capacity`. L’annotation `stack_region` fixe la taille maximale
  de chaque région via `max_size` et peut réserver un nombre
  d’emplacements via `count`. Le descripteur et les métadonnées de gestion
  stockées ailleurs occupent leurs propres espaces.

## Cas admis

### Transférer une structure locale et consommer une liaison locale

```rust
struct Point {
    x: Int,
    y: Int,
}

fn creer_local() -> <- Point {
    let point = Point { x: 10, y: 20 };
    return <- point;
}

fn main() {
    let point = creer_local();
    print(point.x);

    let tampon = [0; 4096];
    print(tampon[0]);
    drop(-> tampon);

    let suivant = [1; 4096];
    print(suivant[0]);
}
```

`drop` termine la vie de `tampon` même si sa valeur est copiable.
Le compilateur décide du placement de `suivant`.

### Injecter un pool typé et réutiliser un slot intérieur

```rust
struct Point {
    x: Int,
    y: Int,
}

fn creer(points: &mut Pool<Point>, x: Int) -> <- A<Point> {
    let point = points.new(x: x, y: 20);
    return <- point;
}

fn main() {
    let mut points = pool<Point>(2);
    let a = creer(&mut points, 10);
    let b = creer(&mut points, 30);

    drop(-> a);
    let c = creer(&mut points, 50);

    print(b.x);
    print(c.x);
    drop(-> c);
    drop(-> b);
}
```

Le pool reste dans `main`. Le slot rendu par `a` peut accueillir
`c` pendant que `b` reste vivant.

## Cas refusés

| Cas | Motif |
| --- | --- |
| `let mut memoire = stack(1024);` | La data stack est gérée par le compilateur et n’a pas de constructeur public. |
| Une signature avec `&mut Allocator`. | Le passage explicite d’une source utilise un pool typé. |
| `pool<Point>()` comme constructeur public. | La forme sans capacité a été écartée. |
| `let autre = <- points;` ou un retour qui transfère le pool lui-même. | Le pool reste dans son scope de création et se passe par emprunt. |
| Faire retourner `creer_local` avec le type `-> <- A<Point>`. | Un `Point` local transféré conserve son type et n’acquiert pas de provenance de pool. |
| Retourner un `A<Point>` créé dans un pool local à la fonction. | Le pool serait fermé avant que le receveur ait terminé avec l’allocation. |
| Lire `tampon[0]` après `drop(-> tampon)`. | Le transfert à `drop` consomme la liaison. |

Demander une troisième allocation au pool de deux slots avant de détruire
`a` ou `b` est un cas d’épuisement. L’exécution s’arrête avec un
diagnostic selon E1.

## Règles à mettre à jour lors de l’intégration

- **I2, V1 et T6.** Décrire la data stack implicite, le choix explicite
  du pool et les retours de structures locales avec `<-`. Conserver
  les contraintes de durée de vie de D1.
- **L6, L7, P3 et P4.** Inclure la consommation explicite d’une valeur
  locale. Distinguer destruction, récupération d’un suffixe de data
  stack et réemploi d’un slot de pool.
- **A1–A4, A6 et P8.** Décrire les signatures `&mut Pool<T>`, la
  provenance des allocations et la durée de vie du pool dans son scope.
  Migrer les passages historiques qui exposent `Allocator`, `stack(...)`
  ou `new(source)`.
- **H2.** Préserver la distinction entre emprunt du handle et emprunt
  du contenu. [FOUNDATIONS_AND_VECTORS.md](../docs/FOUNDATIONS_AND_VECTORS.md)
- **G1, G5–G7 et G10, GR1–GR2 et TX21.** Distinguer l’emplacement du
  descripteur de celui de la donnée grandissante et préciser la portée
  de la limite de région. Relier cette précision à la stabilité
  d’adresse et au dépilement du brouillon 03.
- **AS7 et MT7.** Aligner les références à la source des données ordinaires
  avec la data stack implicite. Pour les états async, appliquer la
  génération et le dimensionnement consignés dans le brouillon 04.

[LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md) ·
[GROWING_REGIONS.md](../docs/GROWING_REGIONS.md) ·
[FOUNDATIONS_AND_VECTORS.md](../docs/FOUNDATIONS_AND_VECTORS.md) ·
[ASYNC_MULTITHREAD_RULES.md](../docs/ASYNC_MULTITHREAD_RULES.md)

Exemples de conception examinés sur papier.
