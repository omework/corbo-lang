[English](02-marqueur-transfert.md)

# 02 — Déplacements et captures

## Décision validée

- Une valeur passée ou reçue par valeur se déplace, y compris pour un type
  primitif. Par exemple, `let b = a`, `relayer(a)`, `return a`, la valeur
  finale `a` et `drop(a)` consomment `a`. Un appel explicite à `copy(a)`
  copie une valeur de type primitif. Dans
  `fn relayer(n: A<Int>) -> A<Int>`, la flèche indique le type de retour.
- `move a;` en tête d'un bloc enfant fait entrer la valeur nommée sous
  le même nom, avec effet à l'entrée du bloc.
- `move { ... }` déplace à l'entrée les liaisons du parent utilisées
  dans le bloc, y compris celles de type primitif. `&a` dans le bloc emprunte le contenu de
  la capture. Pour capturer une référence à `a`, on la lie avant le bloc.
- Une valeur qui ressort du bloc est fournie par sa valeur finale et
  reçue dans une nouvelle liaison visible dans le parent. L'ancien nom
  déplacé reste inutilisable. L'ancien retour qui réactivait cet accès
  sans nouveau receveur est retiré.
- Les contrôles de durée de vie des cibles et des pools, de compatibilité
  des emprunts et de validité sur chaque chemin s'appliquent à ces
  déplacements. Une allocation déplacée conserve son adresse et transmet
  la responsabilité de son nettoyage.

```rust
fn main() {
    let mut nombres = pool<Int>(1);
    let a = nombres.new(7);
    let recu = {
        move a;
        print(*a);
        a
    };
    print(*recu);
}
```

Le remplacement de `{ move a; print(*a); a }` par `move { print(*a); a }`
exprime ici la même capture et le même retour.

La syntaxe est intégrée aux opérations du noyau couvertes dans le
[rapport](../docs/SAFETY.md#cycle-des-déplacements-par-valeur). La syntaxe
historique reste disponible à l'échelle du fichier pour les opérations
et les suites qui l'utilisent encore.

## Historique — proposition des chevrons seuls

Cette proposition avait été écartée au profit des flèches alors en vigueur.
Les exemples suivants en conservent la trace.

En tête d'un argument transféré, `>` remplace `->`. Dans `f(> valeur)`,
la préparation de l'argument invalide l'ancien accès avant l'évaluation des
arguments suivants. Dans `f(a > b)`, `>` se trouve entre deux expressions
et exprime une comparaison. La position du signe suffit à distinguer les deux
formes. La flèche de retour dans `fn f() -> Int` reste celle de la signature.

La proposition porte d'abord sur la notation au site d'appel. Elle complète
B4 et B4a de [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md), F4 et VE3 de
[FOUNDATIONS_AND_VECTORS.md](../docs/FOUNDATIONS_AND_VECTORS.md). La proposition
laissait ouverte la notation des signatures et des autres positions de
transfert.

## Exemple admis si les propositions 01 et 02 sont retenues

```rust
fn main() {
    let mut nombres = pool<Int>(2);
    let mut vecteurs = pool<Vector<A<Int>>>(1);
    let mut valeurs = vecteurs.new();
    valeurs.push(> nombres.new(7));
    let entrant = nombres.new(9);

    drop(valeurs.replace(0, > entrant));

    let contenu = <- valeurs.remove(0);
    if *contenu > 7 {
        print(*contenu);
    }
    drop(contenu);
}
```

## Exemple refusé par la proposition

```rust
fn main() {
    let mut nombres = pool<Int>(2);
    let mut vecteurs = pool<Vector<A<Int>>>(1);
    let mut valeurs = vecteurs.new();
    valeurs.push(> nombres.new(7));
    let entrant = nombres.new(9);

    drop(valeurs.replace(0, entrant));
}
```

Le builtin `drop` indique la consommation de son résultat argument selon la
proposition 01. Il ne fournit pas le marqueur de transfert de `entrant` dans
l'appel intérieur à `replace`. Exemples examinés sur papier.

## Variante symétrique pour un résultat de bloc

En tête du résultat d'un bloc, `< valeur` remplace `<- valeur` et transfère
l'allocation au parent direct. Le bloc se termine par ce résultat sans
point-virgule et la déclaration extérieure le reçoit. Le pool et les cibles
empruntées doivent survivre au transfert selon T3, T6, D1 et A3.

```rust
fn main() {
    let mut nombres = pool<Int>(1);
    let resultat = {
        let local = nombres.new(9);
        < local
    };

    print(*resultat);
    drop(resultat);
}
```

Dans `if *resultat < 10`, le signe est une comparaison entre deux expressions.
Dans le bloc, `local` seul reste refusé comme résultat alloué, faute de
marqueur de transfert. La forme `return < valeur` est la candidate symétrique
de `return <- valeur`. La notation du mode de retour dans une signature et
les autres usages de `<-` restent à arbitrer. Exemple examiné sur papier.

## Argument pour conserver les flèches

Go emploie la même flèche `<-` dans les deux formes de communication.
`canal <- valeur` envoie vers le canal et `recu := <-canal` reçoit depuis le
canal. La pointe indique visuellement la direction du flux. Crust applique
ce repère visuel à un transfert de propriété entre scopes, avec `->` vers
l'appelé et `<-` vers le parent. Conserver les flèches distingue aussi les
transferts des comparaisons par le symbole lui-même. Les chevrons gagnent un
caractère par transfert et reposent sur la position du signe.
[Envoi](https://go.dev/ref/spec#Send_statements) et
[réception](https://go.dev/ref/spec#Receive_operator) dans la spécification Go.
