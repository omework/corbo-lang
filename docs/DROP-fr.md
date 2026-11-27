[English](DROP.md)

# Destruction explicite : appels et réutilisation des slots

## Méthode de destruction

`fn drop(&mut self)` est le hook de destruction défini dans la déclaration
de la struct ou de l'enum. Son retour omis est le type unité. Le nom `drop` est
réservé : `drop(valeur)` consomme la possession et confie le nettoyage complet à
la procédure de destruction. Celle-ci appelle le hook avec `&mut self` tant que
l'objet et ses champs sont valides, détruit les champs possédés selon leurs
dépendances, puis termine la durée de vie et récupère le stockage. La sortie de
scope déclenche la même procédure.

Le hook utilisateur remplace seulement le hook vide par défaut. Il ne remplace
ni le nettoyage des champs ni la récupération du stockage. Chaque copie autorisée
constitue une valeur distincte avec sa propre responsabilité de nettoyage.

Chaque type déclaré a un destructeur vide par défaut. Si le développeur
définit un destructeur, sa définition remplace le défaut. Le compilateur
peut omettre l’appel au destructeur vide dans le code généré.

`drop(object)` et la destruction automatique à la sortie du scope suivent
le même ordre :

1. Appeler le destructeur une seule fois, pendant que l’objet et ses champs sont valides.
2. Détruire les champs possédés dans l’ordre imposé par leurs dépendances.
3. Récupérer le stockage de l’objet.

Un déplacement transfère la responsabilité de destruction au receveur.
La valeur déplacée est détruite via ce receveur. Le backend Rust prend en charge les destructeurs personnalisés des valeurs
fixes, y compris en pool. Les éléments stockés en ligne dans un vecteur et
les matchs par valeur sur des agrégats à destructeur personnalisé restent
hors du sous-ensemble pris en charge.

Ce contrat complète celui des [sorties de blocs](SCOPE_EXIT.md), pour le
sous-ensemble actuel du prototype.

## Transition vérifiée

`drop(-> data)` consomme un accès direct à une allocation vivante rattachée au
scope actuel. Il est refusé si un emprunt doit encore servir. La forme
`memory.drop(-> data)` vérifie en plus que `memory` est la source d'origine.

Le compilateur émet `cell_drop`, marque l'allocation morte et invalide l'accès
consommé. La sortie du bloc ne la détruit pas une seconde fois.

Lors d'un appel `release(-> data)`, l'accès de l'appelant est invalidé et
l'allocation est transférée à la fonction. Celle-ci peut la détruire directement
ou la transférer à une autre fonction qui la détruit. Recevoir seulement `&data`
ou `&mut data` ne donne pas cette capacité de consommation.

Un emprunt dont la dernière utilisation est un appel reste compatible avec une
consommation ultérieure :

```rust
let mut view = &data;
read(view);       // Dernière utilisation de view.
release(-> data);  // Autorisé.
```

Si un autre `read(&view)` apparaît ensuite, le transfert vers `release` est
refusé. Les mêmes règles s'appliquent aux emprunts mutables et aux réemprunts
transmis à travers plusieurs fonctions.

## Réutilisation physique et identité

L'exemple [examples/drop_reuse.crb](../examples/drop_reuse.crb) remplit un pool
de deux slots : `data = 42`, puis `guard = 99`. Une fonction consomme `data`,
la détruit via une autre fonction et alloue `fresh = 43` dans le même pool.

Le test confirme que l'adresse de `fresh` est celle de `data`, tandis que
`guard` conserve sa valeur. La trace de destruction contient exactement :

```text
destroy data=42
destroy fresh=43
destroy guard=99
```

Le compilateur crée un nouvel objet de suivi d'allocation pour chaque `new`.
Il ne déduit pas son identité de l'adresse obtenue à l'exécution. Ainsi,
réutiliser un slot ne réactive ni l'ancien accès ni les anciens emprunts.
Lire, réemprunter, déplacer ou détruire l'ancien accès reste refusé.

Le C émis pour les deux fonctions correspond à ceci, après renommage et
suppression des variables intermédiaires :

```c
static void release(Cell *data) {
    cell_drop(data);
}

static Cell *replace(Source *memory, Cell *old) {
    release(old);
    Cell *fresh = cell_new(memory, 43, "fresh");
    return fresh;
}
```

Les anciennes variables pointeur peuvent subsister dans le C généré. Le
vérificateur empêche l'émission d'un nouvel accès par leur intermédiaire ; le
runtime ne leur attribue pas de numéro de génération et ne vérifie pas chaque
lecture. Modifier ce C manuellement sort du périmètre vérifié.

## Validation

[tests/test_drop_transitions.py](../tests/test_drop_transitions.py) couvre les
appels imbriqués, les derniers usages et usages futurs des emprunts partagés
et mutables, les arguments aliasés, les doubles consommations et la provenance.
Les cas d'emprunt puis consommation sont exécutés avec tas, stack et pool.

Les tests de pool comparent les adresses lors de la réutilisation d'un trou
intérieur et d'un suffixe récupéré. Ils vérifient aussi vingt remplacements
successifs via des fonctions, les refus d'anciens accès et un pool d'enum dont
les variantes ont des tailles différentes. La réutilisation d'une variante
préserve les valeurs et adresses vivantes de l'autre variante.

Ce sont des régressions exécutables, pas une preuve générale de sûreté.
