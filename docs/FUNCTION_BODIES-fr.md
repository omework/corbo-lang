[English](FUNCTION_BODIES.md)

# Vérification mémoire des corps sans appel réel

Chaque fonction est maintenant parcourue par le vérificateur mémoire, même si
le programme ne l'appelle jamais. Les règles du langage ne changent pas.

```rust
fn broken(mut data: -> Int) {
    drop(-> data);
    print(data); // Refusé même sans appel à broken.
}
```

Les consommations multiples, déplacements pendant un emprunt actif, emprunts
mutables incompatibles et mutations via un paramètre en lecture sont également
refusés. Le contrôle tient compte des derniers usages : deux emprunts mutables
successifs restent possibles si le premier a terminé ses usages.

## Procédé

Après validation des signatures et inférence des effets, résultats et contraintes,
`Compiler.verify_function_bodies` crée un vérificateur isolé pour chaque fonction :

1. Chaque paramètre alloué reçoit une identité d'allocation abstraite distincte.
   Son mode réel (`&`, `&mut` ou `->`) est appliqué à l'entrée de la fonction.
2. Chaque source ou provenance de paramètre reçoit une identité de stockage
   symbolique. Les égalités inférées réunissent les identités concernées ; les
   distinctions incompatibles avec ces égalités sont refusées.
3. Une invocation de vérification prépare ces paramètres, puis parcourt le corps
   avec le même vérificateur que les appels réels : déplacements, emprunts,
   expressions, branches, boucles, retours, réaffectations et nettoyages.
4. Les sous-appels sont vérifiés depuis leurs [contrats opaques](MODULAR_CALLS.md),
   sans parcourir leurs corps dans cet environnement symbolique.
   Les états, allocations, indicateurs et textes C de ce passage sont jetés.

Les identités entrantes distinctes ne constituent pas une nouvelle restriction
d'appel. Deux paramètres en lecture peuvent désigner la même allocation réelle.
Les autres combinaisons avec un accès mutable ou transféré restent soumises aux
contrôles d'exclusivité existants aux appels. Les contraintes de sources continuent
de protéger les relations entre provenances, notamment face aux resets.

Les tailles, valeurs et adresses physiques ne sont pas nécessaires à ce passage.
Les branches ne sont pas éliminées à partir de la valeur factice d'un paramètre.
Les chemins devenus inaccessibles après un retour, une sortie de boucle ou un
appel divergent suivent le traitement habituel du vérificateur.

## Sources et backend

Une source `Pool<T>` conserve son type. Une source générique `Allocator` reste
abstraite : le passage ne lui impose pas arbitrairement le tas, une stack ou un
pool concret. Les exigences d'allocation sont toujours inférées et vérifiées
face au stockage réel aux appels. La compatibilité d'un allocateur générique
avec une opération exigeant un pool ne se déduit donc pas de ce seul passage.

Le programme final conserve la spécialisation et les contrôles aux appels réels.
Une fonction inutilisée ne produit aucune définition C dans le binaire. Aucun
objet ni allocateur symbolique ne parvient au C final. Le runtime et les adresses
des allocations ne changent pas.

## Ce que cette étape ne prouve pas

La vérification des corps ne dépend plus de leur utilisation par le programme.
Les sous-appels consomment désormais seulement un contrat opaque. Le backend C
parcourt encore les corps pour la génération spécialisée ; `check` s'arrête avant
ce backend. Le vérificateur des blocs reste partagé avec le backend et ses
fragments C temporaires sont jetés : ce n'est pas une preuve indépendante du
vérificateur ou de la traduction en C.

Les garanties restent celles du sous-ensemble actuel. La récursion, les retours
d'emprunts et les graphes transitifs de références restent hors périmètre.
Les champs &Int immuables sont désormais traités dans le sous-ensemble de
[REFERENCE_FIELDS.md](REFERENCE_FIELDS.md), avec provenances de champs dans les
contraintes des paramètres. Les retours alloués de ces types ont désormais un
[contrat de cibles empruntées](BORROWED_RETURNS.md), contrôlé à chaque frontière
de scope. Les retours directs d'emprunts restent hors périmètre.

## Régressions

[tests/test_function_bodies.py](../tests/test_function_bodies.py) vérifie les refus
sans appel et leur cohérence avec les fonctions appelées, les emprunts terminés,
les paramètres en lecture ou mutables, les branches, les boucles, la protection
des arguments préparés, les égalités de sources, les enums et l'absence de C
symbolique dans le résultat final.

Validation : 494 tests réussis dans la suite complète standard et 494 avec
`CRUST_SANITIZE=undefined`, dont 27 nouveaux tests consacrés aux corps.
