[English](IF_EXPRESSIONS.md)

# If comme expression : un receveur et un transfert explicite

```rust
let mut result = if choice == 1 {
    let mut a = new(memory) Int(10);
    <- a
} else {
    let mut b = new(memory) Int(20);
    <- b
};
print(result);
```

Chaque branche qui continue fournit une valeur du même type et du même mode.
Une allocation exige un `<- a` final sans point-virgule. Un Int copiable
peut être fourni par son nom, un littéral ou une lecture `*data`. Une valeur
finale de branche ne quitte pas la fonction. Les résultats empruntés sont
hors de ce sous-ensemble. `else` est obligatoire, y compris dans une chaîne
`else if`.

`<- a` fournit la valeur de la branche au receveur dans son parent ; il ne
quitte pas la fonction. À l'inverse, un `return` explicite dans une branche
quitte bien la fonction englobante, après nettoyage. Cette branche ne rejoint
pas le receveur et ne doit donc pas fournir de valeur à l'expression. Si toutes
les branches quittent la fonction, le receveur et sa suite ne sont pas produits.

## Nettoyage et stockage

L'allocation sélectionnée est transférée au scope du receveur. Les autres
allocations de la branche sont détruites à sa fermeture, en ordre inverse de
création/réception. Le receveur assure ensuite le nettoyage de l'allocation
sélectionnée, exactement une fois. Son adresse reste inchangée.

Seule la branche choisie s'exécute : un pool d'un seul slot suffit à l'exemple
si aucune autre allocation ne l'occupe. Le compilateur ne crée pas d'allocation
supplémentaire pour réunir les valeurs des branches.

La provenance est conservée. Deux variantes d'un même enum peuvent provenir
de leur pool public commun. Deux pools distincts de même type restent des
sources différentes, conservées comme provenances possibles du résultat.
Chaque source possible est protégée selon [PROVENANCES.md](PROVENANCES.md).
Une allocation dépendant d'une source déclarée dans sa branche ne peut pas
sortir de cette branche.

## Valeurs du parent et réaffectations

Une allocation du parent exige le transfert descendant déjà défini :

```rust
let mut data = new(memory) Int(10);
let mut result = if choice == 1 {
    -> data;
    <- data
} else {
    let mut other = new(memory) Int(20);
    <- other
};
```

L'ancien accès `data` devient inutilisable après la jonction : un chemin l'a
transféré. Sur le chemin qui conserve l'ancienne allocation, elle reste suivie
pour le nettoyage de son scope. Sur le chemin qui la transfère, seul le résultat
en assure le nettoyage. Les indicateurs indépendants des slots distinguent ces
cas, même si un pool réutilise ensuite une adresse.

Une réaffectation peut recevoir une expression `if`. Le receveur doit être
valide sur tous les chemins qui atteignent l’affectation. Elle évalue d'abord le
résultat sélectionné, puis détruit l'ancienne allocation si elle est encore
vivante et distincte du résultat suivi, selon le
[contrat de réaffectation](REASSIGNMENT.md). Sélectionner l'allocation d'origine
par transfert ne provoque pas de destruction supplémentaire.

## Fonctions, arguments et C généré

Le résultat peut être reçu dans une fonction, transféré à un appel avec
`consume(-> if ... { ... } else { ... })` ou emprunté temporairement avec
`inspect(&if ... { ... } else { ... })`. L'évaluation des arguments reste de
gauche à droite. Un temporaire emprunté suit le nettoyage du scope appelant.

Le C conserve simplement le pointeur choisi dans une variable commune, après
nettoyage de chaque branche. Après renommage et simplification :

```c
Cell *selected = NULL;
if (choice == 1) {
    Cell *a = cell_new(memory, 10, "a");
    selected = a;
} else {
    Cell *b = cell_new(memory, 20, "b");
    selected = b;
}
/* Utilisation du receveur, puis nettoyage de son scope : */
cell_drop(selected);
```

Le vérificateur réunit les candidats dans un descripteur sélectionné, de type
connu et portant les sources possibles, comme pour les
[retours conditionnels d'allocations](CONDITIONAL_RETURNS.md). Les anciennes
identités transférées quittent le nettoyage statique sans destruction de leurs
objets. Les autres effets des branches continuant après l'expression restent
suivis. Les branches qui quittent la fonction conservent leurs effets dans le
bilan de retour de cette fonction.

## Validation

[examples/if_expression.crb](../examples/if_expression.crb) montre le receveur,
la suite de la fonction et la stabilité des adresses dans un pool d'un slot.
[tests/test_if_expressions.py](../tests/test_if_expressions.py) vérifie les deux
issues sur le tas, les stacks et les pools, les enums, les transferts du parent,
les réaffectations, les emprunts, les arguments, les retours anticipés et les
expressions imbriquées. Les branches sans valeur ou de types différents,
sources trop courtes, anciens accès et receveurs inutilisés sont refusés.
Ces tests ne constituent pas une preuve générale de sûreté.
