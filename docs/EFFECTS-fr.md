[English](EFFECTS.md)

# Résumés inférés des effets sur les sources

Le compilateur analyse les fonctions avant les appels concrets pour déduire
leurs effets externes d'allocation et de reset. Aucun marqueur supplémentaire
n'est requis dans les signatures.

```rust
fn clear(memory: &mut Allocator) { memory.reset(); }
fn relay(memory: &mut Allocator) { clear(memory); }
fn make(memory: &mut Allocator) -> <- Int {
    let mut fresh = new(memory) Int(42);
    return <- fresh;
}
```

Le résumé de `clear` et de `relay` indique un reset possible du paramètre
`memory`. Celui de `make` indique une allocation Int dans ce paramètre et aucun
reset. Une allocation temporaire compte aussi, même si elle est détruite avant
le retour. Posséder un paramètre `&mut Allocator` ne suffit donc plus à classer
une fonction comme pouvant réinitialiser la source.

## Symboles et propagation

[effects.py](../effects.py) représente les sources de paramètres par leurs indices
dans la signature. L'analyse ne crée ni allocation concrète, ni cellule C, ni
source runtime. Un résumé immuable d’effets contient :

- `resets` : paramètres de source pouvant être réinitialisés ;
- `allocations` : couples (paramètre de source, type alloué) ;
- `pool_requirements` : couples (paramètre de source, type de pool exigé),
  même lorsqu'une signature de sous-appel l'exige sans allocation ;
- `may_return` : possibilité abstraite de revenir normalement à l'appelant.

À chaque sous-appel, les symboles du résumé appelé sont substitués par les
paramètres ou sources locales effectivement nommés dans le corps appelant.
L'ordre ou les noms des paramètres peuvent différer. Les résultats sont mis
en cache par fonction pour le graphe d'appels non récursif actuel.

Les signatures `&Pool<T>` et `&mut Pool<T>` imposent un pool du type indiqué,
même avec un corps vide. Cette exigence est propagée à travers les paramètres
génériques et les substitutions successives, et contrôlée pour les sources locales.
Allouer un Int seul ne signifie pas `Pool<Int>` ; construire un enum exige
son pool typé. Les contradictions sont refusées même sans appel concret. Voir
[POOL_REQUIREMENTS_VALIDATION.md](POOL_REQUIREMENTS_VALIDATION.md).

Les sources locales sont suivies pour leurs types et permissions, mais leurs
effets ne sont pas présentés comme des resets d'une source de l'appelant.
Le masquage des noms respecte les blocs : un pool local nommé `memory` ne
réinitialise pas implicitement le paramètre extérieur portant ce nom.

La destruction d'un argument transféré, y compris `source.drop(-> data)`,
n'est pas un reset collectif de sa source. Le nettoyage de cette allocation
reste régi par son transfert, sa provenance et les règles existantes.

## Branches, boucles et expressions

Les effets possibles des branches sont réunis, même avec `if false`, comme
dans l'analyse conservative actuelle. Un reset conditionnel est donc un reset
possible, sans promesse qu'il s'exécute à chaque appel.

Les effets des conditions, des arguments de gauche à droite, des initialiseurs,
des champs d'enum et des blocs expressions sont parcourus. Une sortie anticipée
dans un argument empêche l'ajout des effets du corps de l'appel non commencé.
Les instructions après un `return`, `break`, `continue` ou un appel sans retour
normal ne contribuent pas aux effets de ce chemin.

Les boucles réunissent les effets du corps et du test, y compris avant `continue`.
Une boucle sans sortie normale permet de déduire `may_return: false`. `while`
conserve son chemin abstrait de test faux, même avec `while true`, conformément
au contrat actuel. `may_return: true` n'est ni une garantie de terminaison ni
une validation du type retourné : il existe une continuation abstraite.

La récursion reste refusée. Un sous-appel inconnu ou un cycle nécessaire à
l'inférence produit un diagnostic, y compris dans une fonction non appelée.
Les appels inaccessibles après une sortie sans continuation sont ignorés.

## Utilisation par le compilateur actuel

Une fois les arguments préparés et contrôlés, le compilateur substitue les
sources concrètes dans le résumé :

1. Les exigences de types allouables sont vérifiées sur les sources réelles.
   Un pool d'enum ne peut pas satisfaire une exigence d'allocation Int.
2. Les sources pouvant subir un reset déterminent les captures de nettoyage
   nécessaires dans les fonctions C spécialisées. Une fonction qui alloue
   seulement ne reçoit plus les pointeurs et indicateurs des anciennes
   allocations de l'appelant pour cette source.
3. La vérification mémoire spécialisée et l'émission C restent en place.
   Elles contrôlent les usages futurs, les emprunts et les provenances possibles
   et produisent les destructions conditionnelles et les indicateurs.
4. Les resets et allocations externes rencontrés pendant cette spécialisation,
   y compris dans les sous-appels, sont comparés au résumé. Un effet manquant
   produit un refus interne avant toute compilation ou exécution du C.

La comparaison est une inclusion : le résumé peut être conservateur. Les
sources possibles d'une allocation sont toutes considérées pour les captures
si l'une peut être réinitialisée. Le protocole de reset partiel des
[provenances multiples](PROVENANCES.md) reste applicable.

## Fonctions inutilisées et limite de cette étape

Les résumés sont inférés aussi pour les fonctions non appelées. Les opérations
sur les sources sont contrôlées lors de cette analyse. Par exemple :

```rust
fn wrong(memory: &Allocator) {
    memory.reset(); // Refusé, même si wrong n'est pas appelée.
}
```

L'analyse d'effets seule ne vérifie pas les déplacements ni les emprunts.
Un [passage du vérificateur mémoire](FUNCTION_BODIES.md) parcourt désormais aussi
chaque corps avec des entrées symboliques, même sans appel. Les contrôles des
allocations, emprunts et types de résultats restent également actifs aux sites
d'appel réels.

Les [résumés de résultats](RESULTS.md) complètent désormais ces effets avec
les origines symboliques des allocations retournées. Les [contraintes de sources](SOURCE_CONSTRAINTS.md) complètent également ces
résumés. Les contrats complets décrits dans
[FUNCTION_CONTRACTS.md](FUNCTION_CONTRACTS.md) alimentent désormais la
[vérification des appels sans corps](MODULAR_CALLS.md). Le backend C reste spécialisé et aucune annotation de
provenance ou d'effet n'est ajoutée au langage.

## Inspection

```sh
python3 prototype/crust.py effects examples/effects.crb
python3 prototype/crust.py effects examples/effects.crb -o /tmp/crust-effects.json
python3 prototype/crust.py run examples/effects.crb
```

La commande `effects` produit un objet JSON par nom de fonction, sans compiler
ni exécuter le C. Elle effectue l'analyse des effets et les contrôles habituels
du programme sur ses appels concrets. Elle ne certifie pas tous les corps
inutilisés. `--run` n'est pas accepté avec cette commande.

Extrait des effets pour `make` (le champ `result` est décrit dans
[RESULTS.md](RESULTS.md)) :

```json
{
  "resets": [],
  "allocations": [{"source": "memory", "type": "Int"}],
  "may_return": true
}
```

`main` peut avoir un résumé externe vide alors qu'elle utilise des sources
locales : il s'agit d'effets sur des sources reçues en paramètres, et non d'un
compteur de toutes les opérations mémoire du programme.

## Validation

[tests/test_effects.py](../tests/test_effects.py) couvre les effets directs,
transitifs, les permutations de paramètres, les noms masqués, les sources
privées, les branches, boucles et sorties anticipées, les appels sans retour,
les initialiseurs et arguments imbriqués, les enums, les permissions de sources
inutilisées, les captures C et le maintien des garanties d'emprunt aux appels.
La commande JSON est vérifiée sans exécution d'un `main` infini.

Validation finale : 415 tests réussis en mode standard et 415 avec
`CRUST_SANITIZE=undefined`, dont les 20 nouveaux tests de résumés d'effets.
Les périmètres d'instrumentation du harnais et des tests de CLI restent ceux
décrits dans [SAFETY.md](SAFETY.md). Un contrôle supplémentaire a comparé
18 résumés générés, sur trois graines et plusieurs permutations de paramètres,
à un modèle indépendant de propagation ; les ensembles concordaient.
