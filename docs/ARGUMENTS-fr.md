[English](ARGUMENTS.md)

# Arguments : évaluation de gauche à droite

Chaque argument est entièrement évalué avant le suivant. Le compilateur
conserve sa valeur dans un temporaire C. La fonction externe n'est exécutée
qu'après préparation de tous ses arguments. Les appels imbriqués appliquent
récursivement la même règle.

## Emprunt temporaire puis transfert

```rust
fn read(data: &Int) -> Int {
    print(data);
    return 7;
}

fn consume(n: Int, mut data: -> Int) {
    print(n);
    print(data);
}

let mut memory = Pool<Int>::new(1);
let mut data = new(memory) Int(42);
consume(read(&data), -> data);
```

`read` affiche `42`, puis produit l'entier copiable `7`. Son emprunt est terminé
avant le transfert de `data`. `consume` affiche ensuite `7`, puis `42`, et détruit
l'allocation en quittant son scope.

Un emprunt stocké dans une variable peut aussi terminer après sa dernière
utilisation dans le premier argument. Un usage ultérieur, après l'appel, maintient
en revanche l'emprunt actif et fait refuser le transfert. L'analyse distingue
les positions des sous-expressions au sein d'une instruction.

L'ordre inverse, avec une signature correspondante, est refusé :

```rust
consume(-> data, read(&data)); // Ancien accès déjà transféré.
```

## Arguments préparés et encore nécessaires

Un emprunt fourni directement à l'appel externe doit rester valide pendant
l'évaluation des arguments suivants et l'appel :

```rust
outer(&data, edit(&mut data)); // Refusé : emprunt partagé déjà préparé.
```

Plusieurs emprunts partagés restent possibles. Un emprunt mutable préparé
empêche les accès concurrents à la même allocation. Un emprunt de source suit
les mêmes restrictions : `outer(&mut memory, create(&mut memory))` est refusé.
Il faut préparer le résultat de `create` avant de prendre cet emprunt de source.
Le prototype n'introduit pas de réservation différée d'emprunts mutables.

Une allocation passée par transfert devient inaccessible par l'ancien accès
dès la préparation de cet argument. Elle reste néanmoins rattachée au scope
appelant pendant l'évaluation des arguments restants, puis entre dans la
fonction appelée. Un reset dans un argument suivant ne peut détruire une
allocation déjà préparée pour l'appel, même si elle n'a plus d'accès nommé.

## Expressions allouées et modes explicites

Les modes restent visibles pour les expressions :

```rust
consume(-> new(memory) Int(42));
consume(-> create(&mut memory));
inspect(&create(&mut memory));
modify(&mut new(memory) Int(42));
```

Un résultat alloué n'est jamais passé implicitement à un paramètre transféré.
Un temporaire alloué et emprunté reste dans le scope appelant jusqu'au nettoyage
automatique ou à un reset autorisé ; il n'est pas détruit automatiquement au
retour de cet appel. Les sources restent des déclarations locales nommées et
ne sont ni transférables ni créées temporairement dans un argument.

Les blocs retournant une allocation peuvent aussi fournir un argument. Un
`return` anticipé dans un tel bloc quitte la fonction englobante : l'appel externe
n'a pas lieu et ses allocations déjà préparées suivent le nettoyage des scopes.

## Traduction en C et validation

Pour le premier exemple, après renommage, l'émetteur produit essentiellement :

```c
Cell *read_argument = data;
int result = read(read_argument);
int first_argument = result;
Cell *second_argument = data;
consume(first_argument, second_argument);
```

Aucun effet de sous-appel n'est laissé dans la liste d'arguments C. Le résultat
ne dépend donc pas de l'ordre d'évaluation des arguments choisi par le
compilateur C. Les paramètres internes nécessaires aux resets restent également
des pointeurs sans effets dans cette liste.

[examples/arguments.crb](../examples/arguments.crb) est un programme exécutable.
[tests/test_arguments.py](../tests/test_arguments.py) vérifie l'ordre observable,
les emprunts partagés et mutables, les transferts, les allocations temporaires,
les resets et réutilisations de pools, les enums, les blocs et les retours
anticipés. Les erreurs de modes et de types produisent un diagnostic avant
émission du programme. Ces régressions ne sont pas une preuve générale de sûreté.


## Valeur de référence déjà existante

```rust
fn read(data: &Int) -> Int { return *data; }
let mut memory = Pool<Int>::new(1);
let mut data = new(memory) Int(42);
let mut view = &data;
let mut n = read(view);
print(n);
```

`read(&data)` crée un emprunt ; `read(view)` fournit celui déjà reçu.
`read(&view)` est refusé : les références imbriquées ne sont pas supportées.
Les résultats de fonctions retournant &Int se passent directement, sans `&`
ajouté. Les paramètres de pools se transmettent aussi par leur nom. La protection
des arguments préparés, leur ordre d'évaluation et les contrôles drop/reset
s'appliquent dans tous ces cas. Voir [REFERENCE_VALUES.md](REFERENCE_VALUES.md).
