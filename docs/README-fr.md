# Corbo

**Un langage de programmation système expérimental fondé sur l’intention du développeur, la prévisibilité de la mémoire et la vérification statique.**

[English](../README.md)

## Philosophie

**La mémoire est finie. Nous le savons, mais nous écrivons souvent nos programmes comme si elle était illimitée.**

L’allocation dynamique apporte de la souplesse. Elle peut aussi nous amener à laisser les contraintes de ressources implicites, alors même que nous connaissons les limites du système.

Le développeur connaît des éléments que le compilateur ne peut pas toujours déduire : la charge attendue, les budgets, les responsabilités de nettoyage et les durées de vie. Corbo cherche à rendre ces informations exprimables dans le code pour que le compilateur puisse les exploiter. Les contraintes qui exigent un contrôle à l’exécution restent explicites.

Corbo explore les régions sur datastack, les pools de capacité fixe, les emprunts vérifiés statiquement et le placement des valeurs guidé par le compilateur. L’expérience devra être évaluée sur des programmes réels, en termes de sûreté, de performance, de prévisibilité et d’ergonomie.

### Un budget mémoire implicite en Rust

<!-- corpus: rust-only -->
```rust
fn collect_numbers(count: usize) -> Vec<usize> {
    let mut numbers = Vec::new();
    for number in 0..count {
        numbers.push(number);
    }
    numbers
}
```

L’appelant fournit `count`. Le vecteur grandit au fil des insertions et la fonction laisse implicites le budget mémoire et la conduite à tenir en cas de dépassement.

## Démarrage

Le compilateur auto-hébergé est maintenu dans le dépôt
[omework/corboc](https://github.com/omework/corboc). Ce dépôt conserve la grammaire,
les règles, la STD, le runtime, les exemples et les ressources pour les éditeurs.

Le [guide d’installation](../README.md#getting-started) explique comment fournir
un compilateur de départ compatible et lancer la reconstruction. Le fichier
`corbo.lock` du compilateur fixe la révision de la STD et du runtime. Le
compilateur Rust reste figé pour les validations historiques et ne construit
pas les sources actuelles de corboc.

[Installer la coloration pour Vim, Neovim ou VS Code](../ide/README.md)

## Pools à capacité fixe

`pool<i64>(2)` peut contenir deux allocations vivantes. Les deux premiers appels à `new` occupent les deux slots. Détruire `first` libère son slot pour `third`, tandis que `second` reste valide.

```rust
fn main() {
    let mut numbers = pool<i64>(2);
    let first = numbers.new(10);
    let second = numbers.new(20);

    print(*first);
    drop(first);

    let third = numbers.new(30);
    print(*second);
    print(*third);
}
```

[Règles des structures et des pools](STRUCTURES_METHODS.md)

## Datastacks et régions

Le compilateur établit le placement après l’AST. La datastack classique porte le stockage fixe. Une datastack à régions fournit notamment le stockage grandissant des vecteurs et des chaînes. Les sorties de scope nettoient les valeurs puis rendent l’espace réutilisable. `#(free_pages)` demande en plus la restitution des pages entièrement libres. Les seuils de restitution automatique sont facultatifs et se configurent par datastack.

```rust
#(datastack: reclaim_threshold=64M, region_reclaim_threshold=16M)

fn main() {
    let mut vecteurs = pool<Vector<i64>>(1);
    #(stack_region: max_size=64K, count=1) #(free_pages) {
        let mut valeurs = vecteurs.new();
        valeurs.push(7);
        valeurs.push(9);
        print(valeurs[0] + valeurs[1]);
    }
}
```

[Modèle des datastacks](GROWING_REGIONS.md) · [Mesures de restitution](G11_DATASTACK_BENCHMARK.md)

## Emprunt à travers un appel

L’appelant conserve la responsabilité de la valeur. La fonction reçoit une référence mutable. L’appelant peut relire la valeur au retour de l’appel.

```rust
fn increment(value: &mut i64) {
    *value = *value + 1;
}

fn main() {
    let mut number: i64 = 41;
    increment(&mut number);
    print(number);
}
```

## Tâches

L’appel à une fonction `async` crée une Future inactive. `runtime::spawn` la lance et retourne un handle. Dans le `main` synchrone, `join()` fournit le résultat ou une erreur de lancement.

```rust
async fn calculer(n: i64) -> i64 {
    yield;
    n * 2
}

fn main() {
    let execution = runtime::spawn(calculer(6));
    match execution.join() {
        Ok(resultat) => { print(resultat); },
        Err(_) => { print(0); },
    }
}
```

## Références du projet

- [Grammaire du core](../CORE_GRAMMAR.ebnf) et [règles du langage](LANGUAGE_RULES.md)
- [Représentations du compilateur](MEMORY_REPRESENTATION.md) et [compilateur Rust](../rust_frontend/README.md)
- [Checklist d’implémentation](IMPLEMENTATION_CHECKLIST.md) et [matrice de vérification](VERIFICATION_MATRIX.md)
- [Consignes de validation](VALIDATION_GUIDELINES.md) et [guide pour l’audit indépendant](CORE_AUDIT_HANDOFF.md)

Le dépôt conserve le [prototype Python](../prototype/README.md) pour reproduire les validations historiques. Utilisez le compilateur auto-hébergé pour la syntaxe actuelle. La matrice indique la portée des garanties exercées par les tests.
