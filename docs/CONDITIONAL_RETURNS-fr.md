[English](CONDITIONAL_RETURNS.md)

# Retours conditionnels d’allocations et provenances possibles

Une fonction peut retourner une allocation différente selon la branche :

```rust
fn create(memory: &mut Pool<Int>, n: Int) -> <- Int {
    if n == 1 {
        let mut a = new(memory) Int(10);
        return <- a;
    } else {
        let mut b = new(memory) Int(20);
        return <- b;
    }
}
```

Le contrat de cette étape impose :

- Un retour d'allocation explicite sur tous les chemins qui terminent la fonction.
- Le type déclaré pour chaque allocation retournée.
- Un suivi de toutes les sources possibles des allocations retournées.
- Une source qui survit au retour, selon les règles de transfert existantes.

Les sources peuvent être différentes. Le résultat conserve l'ensemble fini
des provenances possibles, déduites sans annotation supplémentaire. Chaque
source possible doit survivre aux transferts et rester protégée contre un reset
incompatible avec les usages futurs. Deux pools distincts restent deux sources,
même s'ils ont le même type.

Pour un enum, les variantes retournées peuvent différer et provenir de pools
publics différents du même enum. Les stacks privées des variantes ne sont pas
des sources publiques indépendantes. Voir [PROVENANCES.md](PROVENANCES.md).

## Nettoyage et réception

Seule la branche choisie s'exécute. Une fonction qui crée une allocation dans
chaque branche exclusive peut donc fonctionner avec un pool d'un seul slot,
si rien d'autre ne l'occupe à cet instant.

L'allocation retournée traverse les scopes jusqu'à l'appelant. Les autres
allocations de ce chemin sont détruites avant le retour, dans l'ordre prévu.
Si la fonction choisit entre deux arguments transférés, l'argument non retourné
est nettoyé ; les anciens accès de l'appelant restent consommés dans les deux cas.

Le receveur obtient un accès à l'allocation sélectionnée et une nouvelle entrée
dans son ordre de réception. Cet accès conserve les provenances possibles et peut
être emprunté, transféré, détruit ou affecté par un reset de cette source.
Les règles de dernière utilisation des emprunts restent applicables.

Un indicateur de nettoyage attaché à l'ancien accès est désarmé au retour,
sans détruire l'objet. Si un aller-retour redonne la même allocation au scope
d'origine, la jonction rétablit son indicateur sur les chemins où elle reste
vivante. Les indicateurs locaux à une fonction terminée ne sont pas repris
par une branche ultérieure de l'appelant.

## Représentation du résultat et C émis

Le C effectue simplement un retour de pointeur depuis chaque branche, après
nettoyage des temporaires. Après renommage :

```c
static Cell *create(Source *memory, int n) {
    if (n == 1) {
        Cell *a = cell_new(memory, 10, "a");
        return a;
    } else {
        Cell *b = cell_new(memory, 20, "b");
        return b;
    }
}
```

Aucune allocation supplémentaire ni copie d'objet n'est nécessaire pour réunir
les retours. L'adresse de l'objet choisi reste inchangée.

Pour la vérification, le compilateur réunit les candidats dans un descripteur
unique du résultat chez l'appelant, portant l'union des sources possibles. Les anciennes
identités des candidats retournés sont retirées du nettoyage statique sans
émettre de destruction. Cela représente un transfert, pas une fin de vie de
l'objet exécuté. Le descripteur du résultat assure ensuite son nettoyage unique.
Si tous les retours rendent exactement la même allocation connue avant l'appel,
son identité est conservée : ses correspondances d'import et ses marquages de
transfert restent valides. Les anciens accès consommés ne sont pas réactivés
par cette conservation ; seul le receveur obtient l'accès retourné. Les candidats
locaux ou distincts continuent d'utiliser le descripteur sélectionné décrit
ci-dessus. Voir [AUDIT_MEMORY.md](AUDIT_MEMORY.md).

Les effets des autres opérations de chaque chemin, notamment un reset affectant
des allocations de l'appelant, sont conservés dans la réunion des états.

Un retour peut aussi sélectionner l'allocation d'origine d'une réaffectation ou
une nouvelle allocation. Si la fonction a déjà consommé l'ancienne allocation,
la réaffectation ne déclenche pas de seconde destruction. Si l'ancienne n'a pas
été consommée, elle est détruite après évaluation du nouveau résultat, selon le
[contrat de réaffectation](REASSIGNMENT.md).

## Limites et validation

Les candidats doivent conserver le même type déclaré ; leurs sources peuvent
différer. Les expressions `if` avec receveur sont
désormais prises en charge selon [IF_EXPRESSIONS.md](IF_EXPRESSIONS.md).
Les [retours directs &Int](DIRECT_BORROW_RETURNS.md) sont désormais admis avec
union conservative des cibles et contrôle enfant → parent. Les [retours &mut Int](MUTABLE_BORROW_RETURNS.md) sont aussi admis ; chaque cible
possible conserve une protection exclusive. La fusion d'ordres de réception
incompatibles reste hors du sous-ensemble. Les allocations ne peuvent pas échapper à une source
locale qui serait détruite en quittant la fonction.

[examples/conditional_returns.crb](../examples/conditional_returns.crb) montre
deux branches, une fonction intermédiaire et la réutilisation d'un pool d'un slot.
[tests/test_conditional_returns.py](../tests/test_conditional_returns.py) couvre le
tas, les stacks, les pools, les enums, les appels imbriqués, la sélection d'arguments
transférés, les emprunts, les réaffectations et les resets. Les tests vérifient
les adresses et les traces de destruction, ainsi que les refus de type, de
source, de durée de vie et de retour manquant. Ils ne constituent pas une preuve
générale de sûreté.
