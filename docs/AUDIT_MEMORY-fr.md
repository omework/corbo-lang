[English](AUDIT_MEMORY.md)

# Audit des règles, du vérificateur et du C généré

Audit ciblé du 2 novembre 2026, sur le sous-ensemble effectivement implémenté.
Les règles de référence sont [LANGUAGE_RULES.md](LANGUAGE_RULES.md) et les
contrats des opérations liés dans [SAFETY.md](SAFETY.md). Cet audit conserve
ces règles ; il ne revalide pas les choix du langage et n'étend pas les types
ou les formes d'emprunts acceptées par le prototype.

## Écart 1 : capture trop tardive des champs d'enum

Contre-exemple accepté avant correction :

```rust
enum E { A { x: Int, y: Int } }
fn read(a: &Int) -> Int { return *a; }
let mut memory = pool<E>(1);
let mut temps = allocator();
let mut n = 10;
let mut e = new(memory) E.A {
    x: n,
    y: read(& {
        n.set(20);
        let mut a = new(temps) Int(1);
        <- a
    })
};
print(e);
```

Le C affichait `E.A(20, 1)` au lieu de `E.A(10, 1)`. Le vérificateur visitait
les initialiseurs dans l'ordre écrit, mais conservait le nom de la variable C
pour `x`. La lecture effective de cette variable était émise après les effets
de l'initialiseur de `y`. C'est un écart d'évaluation des valeurs, sans accès à
une mémoire libérée démontré par ce contre-exemple.

Chaque valeur de champ est maintenant copiée dans un temporaire C immédiatement
après son évaluation, avant de passer à l'initialiseur suivant. L'ordre écrit
reste distinct de l'ordre de disposition des champs déclarés. L'enum n'est
alloué et rendu utilisable qu'après évaluation des champs requis ; une sortie
anticipée dans un initialiseur ne publie pas d'enum partiellement initialisé.

## Écart 2 : identité perdue lors d'un retour conditionnel uniforme

Contre-exemple refusé avant correction :

```rust
fn forward(mut a: -> Int, n: Int) -> <- Int {
    if n == 0 { return <- a; }
    return <- a;
}
let mut memory = allocator();
let mut a = new(memory) Int(42);
{
    -> a;
    a = forward(-> a, 0);
    <- a;
}
print(a);
```

Sans le `if` dans `forward`, le programme fonctionnait. Avec ce `if`, il était
refusé comme transfert sans receveur parent. Les deux chemins rendaient pourtant
la même allocation reçue en paramètre, sans changement d'adresse ni de source.

La réunion des retours conditionnels retirait systématiquement les identités
des candidats et créait un descripteur sélectionné chez l'appelant. Dans ce
cas uniforme, elle rompait la correspondance avec l'import et l'accès du parent
qui devait être restauré. Ce défaut était un refus indu, pas une acceptation
permettant un accès après destruction.

Si tous les chemins de retour rendent exactement la même allocation connue
avant l'appel, le vérificateur conserve maintenant son identité. Il réunit les
autres effets normalement, puis transfère le nettoyage au receveur. Les anciens
noms consommés restent invalides. Les allocations locales et les candidats
distincts continuent d'utiliser un descripteur sélectionné. Il n'y a ni copie
ni déplacement des octets, ni comparaison runtime de pointeurs pour décider.

Cette conservation maintient aussi les marquages de transfert déjà posés et
les correspondances entre imports imbriqués. Les indicateurs de nettoyage ne
conservent pas de référence à une variable C d'une fonction terminée.

## Vérifications ajoutées

[tests/test_audit_regressions.py](../tests/test_audit_regressions.py) comprend :

- La capture des champs avant les effets suivants, y compris ordre des champs
  inversé, branche conditionnelle et retour anticipé pendant l'initialisation.
- Les retours de même identité pour Int et enum, les imports imbriqués, les
  marquages de transfert, les jonctions et les reprises de boucle.
- Le maintien des refus d'anciens noms consommés et d'emprunts utilisés après
  destruction ; les candidats réellement différents restent nettoyés une fois.
- Une matrice de 30 tentatives incompatibles avec un emprunt futur, combinant
  emprunts partagés/mutables, mutation, transfert/destruction, reset, blocs,
  conditions et boucles.
- Un modèle indépendant des identités, valeurs et ordres de réception : deux
  graines déterministes, trois sources de stockage, 32 étapes par programme.
  Les mouvements locaux, allers-retours, appels, destructions et destructions
  conditionnelles sont comparés aux impressions et traces du C exécuté.

Le modèle indépendant ne lit ni les états du vérificateur ni le C pour calculer
ses attentes. Il reste petit et borné. L'oracle runtime existant de 3 000
opérations complète ces vérifications pour les slots et les curseurs.

## Validation finale

371 tests réussissent dans chacune des deux exécutions complètes :

```sh
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
CRUST_SANITIZE=undefined PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -q
```

Les 14 nouveaux tests sont inclus, avec leurs sous-cas et programmes générés.
L'instrumentation UBSan couvre les binaires compilés par le harnais et l'oracle ;
les binaires construits séparément par les tests de CLI conservent leurs options
habituelles, comme indiqué dans [SAFETY.md](SAFETY.md).

## Limites du constat

Les recherches de cette passe n'ont pas produit de nouvel exemple confirmé
d'accès après destruction ou de double destruction accepté. Cela ne démontre
pas leur impossibilité. Les deux écarts corrigés portent respectivement sur
les valeurs exécutées et sur un refus indu lié à l'identité d'une allocation.

Les fonctionnalités explicitement hors sous-ensemble (références dans les
structures, retours d'emprunts, récursion, appels C externes, etc.) ne sont pas
considérées comme vérifiées. La spécialisation des fonctions aux sites d'appel
reste une limite connue, pas une garantie de vérification modulaire.
ASan n'est toujours pas validé dans cet environnement ; les limites de
l'instrumentation sont précisées dans [SAFETY.md](SAFETY.md).
