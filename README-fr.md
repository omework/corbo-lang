# Corbo

**Un langage de programmation système expérimental fondé sur l’intention du développeur, la prévisibilité de la mémoire et la vérification statique.**

[English](README.md)

<a id="philosophie"></a>

## Comment la philosophie de Corbo a évolué

Corbo est né d’une expérimentation : concevoir un langage de programmation système principalement destiné au code généré par l’IA.

L’idée initiale était simple : **l’intention du développeur est une ressource que le compilateur devrait exploiter.**

Corbo privilégie les contraintes explicites et vérifiables par une machine plutôt que la facilité d’écriture, tout en cherchant à rendre le code produit compréhensible et auditable par des humains.

La gestion de la mémoire est devenue l’un des axes centraux de cette expérimentation.

**La mémoire est finie. Nous le savons, mais nous écrivons souvent nos programmes comme si elle était illimitée.**

Corbo explore ce qui se passe lorsque les programmes sont conçus autour de capacités mémoire explicites, de durées de vie prévisibles et de stratégies d’allocation bornées, sans dépendre d’un allocateur généraliste sur le tas.

Au départ, il s’agissait surtout d’une question de faisabilité : quelle quantité de logiciels pouvait-on raisonnablement construire sous ces contraintes ?

À mesure que le langage et sa bibliothèque standard se développaient, une autre possibilité a commencé à se dessiner.

**Et si l’IA pouvait exploiter les contraintes d’un système entier pour aider à déterminer comment ce système devrait être implémenté ?**

Les exigences métier, les limites de taille des données échangées, les schémas de communication, les limites de concurrence et les budgets de ressources pourraient guider non seulement les allocations individuelles, mais aussi des architectures logicielles entières.

Ces informations n’apportent pas toutes les mêmes garanties. Une charge attendue est une hypothèse ; une capacité effectivement imposée est une limite. Cette distinction compte : une implémentation peut être optimisée autour d’hypothèses, tandis que ses garanties doivent reposer sur des contraintes que le programme fait réellement respecter.

Des agents IA pourraient exploiter ces informations pour générer des implémentations spécialisées adaptées à des exigences connues. Des contrats explicites permettraient d’examiner ces choix, tandis que le compilateur vérifierait les propriétés qu’il peut établir et que les contrôles à l’exécution feraient respecter les limites qui ne peuvent pas être résolues statiquement.

Ce n’était pas la motivation initiale du modèle mémoire de Corbo. Cette idée est apparue au fil de l’expérimentation.

Elle reste une hypothèse, pas un résultat établi.

Une génération de code moins coûteuse ne supprime pas le coût de la validation, de la maintenance ou de la compréhension d’un système. Corbo cherche à déterminer si des contraintes explicites et la vérification par le compilateur peuvent rendre la spécialisation pratique sans rendre ses conséquences plus difficiles à évaluer.

Corbo tente d’explorer cette hypothèse : **que devient-il possible lorsque la génération de logiciels devient moins coûteuse, que les contraintes sont explicites et que la vérification fait partie du modèle de programmation ?**

## Les budgets mémoire en pratique

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

Le [guide d’installation](README.md#getting-started) explique comment fournir
un compilateur de départ compatible et lancer la reconstruction. Le fichier
`corbo.lock` du compilateur fixe la révision de la STD et du runtime. Le
compilateur Rust reste figé pour les validations historiques et ne construit
pas les sources actuelles de corboc.

[Installer la coloration pour Vim, Neovim ou VS Code](ide/README.md)

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

[Règles des structures et des pools](docs/STRUCTURES_METHODS.md)

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

[Modèle des datastacks](docs/GROWING_REGIONS.md) · [Mesures de restitution](docs/G11_DATASTACK_BENCHMARK.md)

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

- [Grammaire du core](CORE_GRAMMAR.ebnf) et [règles du langage](docs/LANGUAGE_RULES.md)
- [Représentations du compilateur](docs/MEMORY_REPRESENTATION.md) et [compilateur Rust](rust_frontend/README.md)
- [Checklist d’implémentation](docs/IMPLEMENTATION_CHECKLIST.md) et [matrice de vérification](docs/VERIFICATION_MATRIX.md)
- [Consignes de validation](docs/VALIDATION_GUIDELINES.md) et [guide pour l’audit indépendant](docs/CORE_AUDIT_HANDOFF.md)

Le dépôt conserve le [prototype Python](prototype/README.md) pour reproduire les validations historiques. Utilisez le compilateur auto-hébergé pour la syntaxe actuelle. La matrice indique la portée des garanties exercées par les tests.
