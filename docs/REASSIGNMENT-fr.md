[English](REASSIGNMENT.md)

# Réaffectation : évaluer, détruire, remplacer

Pour un accès direct mutable, si `expression` fournit une allocation,
`data = expression` remplace cet accès dans l'ordre suivant :

1. Évaluer entièrement l'expression de droite et conserver son résultat.
2. Détruire l'ancienne allocation si elle est encore vivante et distincte de
   celle reçue en résultat.
3. Installer le nouvel accès dans `data`, avec sa source propre.

L'accès à `data` doit être valide sur tous les chemins qui atteignent cette
affectation. Si un `if` a pu déplacer `data` avant, le remplacement est
refusé. Une branche qui quitte la fonction avant l'affectation est exclue.

Un transfert explicite `data = <- local;` peut viser une variable mutable
visible dans un bloc ancêtre. Le pool et les cibles empruntées doivent
survivre dans le scope de `data`. Le prototype accepte ce transfert dans
un bloc linéaire et dans un `if` lorsque chaque branche qui continue laisse
un receveur valide, que les ordres de nettoyage sont compatibles et qu'aucun
emprunt encore actif ne dépend d'une identité remplacée. Le C sélectionne le
pointeur à la fin de la branche exécutée et n'arme qu'une entrée de nettoyage
pour cette sélection. Les contrats conservent les provenances et les
dépendances possibles. Un receveur déclaré avant une boucle peut également
être remplacé pendant l'itération. `continue` et la fin normale du corps
transmettent sa nouvelle valeur au passage suivant. `break` la transmet
à la sortie, où elle rejoint les autres sorties, y compris le test faux
d'un `while`. Les contraintes d'ordre et de validité restent applicables.

La destruction reste suivie de la récupération du stockage selon sa source.
L'ancienne allocation n'est pas détruite de nouveau lors d'un `drop`, d'un
reset collectif ou de la fermeture du scope. Cette règle remplace la décision
initiale de conserver les anciennes allocations jusqu'au nettoyage du scope.

## Mutation du contenu

Pour un Int alloué, `data = 20` et `data.set(20)` modifient le contenu de
l'allocation existante. Ce cas ne suit pas les étapes de destruction/remplacement
ci-dessus. La cible conserve son adresse, sa source et son ordre de nettoyage.
Il exige un accès direct `let mut data`, ou un emprunt &mut via `.set`.
La variable contenant ce dernier peut être déclarée avec `let`.

Une partie droite scalaire s'évalue avant l'écriture. Sa dernière lecture par
emprunt peut terminer avant cette écriture ; détruire/reset la cible pendant
cette évaluation fait refuser l'écriture. Voir [LET_MUTABILITY.md](LET_MUTABILITY.md).

## Lire l'ancienne valeur pendant l'évaluation

```rust
fn make(memory: &mut Pool<Int>, old: &Int) -> <- Int {
    print(old);
    let mut fresh = new(memory) Int(20);
    return <- fresh;
}

let mut memory = pool<Int>(2);
let mut data = new(memory) Int(10);
data = make(&mut memory, &data);
print(data);
```

La fonction lit `10` et retourne sa nouvelle allocation avant la destruction
de `10`. La dernière instruction affiche ensuite `20`.

Un emprunt stocké dans une variable peut aussi être utilisé pour la dernière
fois dans l'expression de droite. L'analyse de dernière utilisation distingue
ces usages des usages suivants du nouvel accès installé dans `data`.
Si un emprunt vers l'ancienne allocation doit encore servir après la
réaffectation, le compilateur refuse l'opération.

## Déplacements, fonctions et provenance

- `data = <- data` ou un aller-retour par fonction de la même allocation ne la
  détruit pas : l'identité d'allocation reste la même.
- Si la fonction consomme l'ancienne allocation et la détruit, ou réinitialise
  sa source, la réaffectation ne déclenche pas une seconde destruction.
- Si la nouvelle allocation vient d'une autre source, la destruction de
  l'ancienne utilise son origine ; `data` conserve ensuite la nouvelle origine.
- Réaffecter un emprunt change l'accès emprunté sans détruire l'objet référencé.
  Les scalaires copiables conservent une affectation ordinaire.

En C, une réaffectation recevant une allocation distincte prend cette forme,
après renommage des variables :

```c
Cell *replacement = make(&memory, data);
cell_drop(data);
/* Les accès Corbo suivants utilisent replacement. */
```

La déclaration temporaire matérialise la valeur de droite avant le nettoyage.
L'émetteur utilise un nouveau nom C pour l'accès remplacé. Le suivi mémoire
associe cet accès à la nouvelle allocation ; il ne se fonde pas sur l'adresse.

## Capacité des pools

La nouvelle allocation existe avant la destruction de l'ancienne. Un pool d'un
seul slot ne permet donc pas `data = new(memory) Int(20)` quand `data` l'occupe.
L'échec arrête le programme avant de détruire l'ancienne allocation ; le
prototype ne déroule pas les destructeurs lors de cet arrêt.

Un pool de deux slots permet des remplacements successifs d'une seule variable,
avec alternance des adresses et réutilisation des trous. Pour un enum, cette
capacité s'apprécie par variante : un pool d'un slot par variante peut remplacer
une allocation `A` par une allocation `B`, puis réutiliser le slot de `A`.

## Validation

[examples/reassignment.crb](../examples/reassignment.crb) illustre une
réaffectation via une fonction lisant l'ancienne valeur, puis une allocation
depuis une autre source.

[tests/test_reassignment.py](../tests/test_reassignment.py) vérifie ces règles
sur le tas, les stacks et les pools, les emprunts partagés et mutables, les
déplacements et transferts, les resets dans l'expression de droite, l'ordre
observable des destructions, les réutilisations répétées et les variantes
d'enum. Ces cas ne constituent pas une preuve générale de sûreté.
