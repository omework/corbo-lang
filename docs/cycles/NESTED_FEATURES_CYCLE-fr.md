[English](NESTED_FEATURES_CYCLE.md)

# Cycle — Contraintes de méthodes indépendantes et résultats concrets

## Règles et correction

TF2 impose des paramètres indépendants même lorsqu'ils portent le même nom
de feature. TF5 impose un résultat concret déductible, sans imposer qu'il ait
le type du receveur. La comparaison précédente remplaçait toutes les
occurrences de la feature par le type du receveur : elle introduisait donc
une égalité de types explicitement reportée par le brouillon 06.

Contre-exemple reproduit avant correction :

```rust
type feature Visit { fn visit(&self, other: &Visit) -> Int; }
struct Left { value: Int }
struct Right { value: Int }
impl Left { fn visit(self: &Left, other: &Visit) -> Int { return self.value; } }
impl Right { fn visit(self: &Right, other: &Visit) -> Int { return self.value; } }
fn apply(a: &Visit, b: &Visit) -> Int { return a.visit(b); }
fn main() {
    let a = Left { value: 7 };
    let b = Right { value: 9 };
    print(apply(&a, &b));
}
```

Le diagnostic était `type 'Left' : exigence de feature 'Visit' non garantie`.
Le receveur seul est désormais substitué lors de cette comparaison. Les
autres contraintes sont comparées structurellement ; elles ne deviennent pas
le type du receveur. Une méthode prenant uniquement `&Left` ne satisfait pas
la contrainte indépendante `&Visit`, même si un appel particulier lui fournit
un Left.

Un résultat contraint est vérifié contre son propre type concret. Le test
`test_method_feature_result_keeps_its_own_concrete_type` fait renvoyer un
`&Target` par la méthode d'un `Wrapper`, puis par deux relais contraints.
La référence conserve sa cible : détruire cette cible avant son usage reste
refusé. Les modes de receveur, arguments et résultat restent vérifiés.

La comparaison garde les paires de contraintes en cours pour traiter leurs
références récursives. Revoir exactement la même paire clôt cette comparaison,
mais n'ignore pas les autres noms/modes/types. Cela ne permet pas la récursion
de fonctions exécutables. Ce contrôle structurel n'est pas une preuve formelle
de correction du vérificateur.

## Interactions et preuves

Les six nouveaux tests synchrones couvrent : types indépendants par deux
relais ; autre feature dans la signature ; argument mutable et conflit
d'emprunt ; résultat d'un autre type concret ; contraintes structurellement
équivalentes à noms distincts ; contrôle d'une feuille incorrecte à travers
trois types, même si la méthode n'est jamais appelée. Cette dernière famille
refuse une méthode absente, un mauvais receveur et un mauvais résultat.

`test_async_type_features` ajoute quatre programmes natifs :

- `Vector<Int>` et `Vector<u8>` spécialisés indépendamment avec deux awaits ;
  mutation de la cible pendant l'exécution refusée.
- Découpe de String renvoyée par deux fonctions async : l'emprunt protège la
  cible après join ; mutation, drop et reset historique avant le dernier
  usage sont refusés. Mutation puis destruction et réemploi après usage admis.
- Capture mutable réservant Vector dès la création de la tâche, avant spawn ;
  lecture, mutation et destruction incompatibles refusées.
- Capture propriétaire de String : nettoyage unique à la complétion, slot
  réutilisé à la même adresse ; ancien propriétaire inutilisable.

Ce complément représente 10 programmes natifs et 19 variantes refusées. Les
attentes viennent de TF1–TF5, des règles d'emprunt, de capture et de transfert,
pas de l'acceptation du compilateur.

Exécutions finales (journaux conservés dans `validation/`) :

- `CRUST_TEST_OPT=-O0 PYTHONPATH=tests:. python3 -m unittest
  test_async_type_features test_type_features test_builtin_features -v` :
  **42 méthodes réussies en 19,830 s**, `nested-features-final-O0.log`.
- Même commande à O2 : **42 méthodes réussies en 20,032 s**,
  `nested-features-final-O2.log`.
- Le helper compile en C11 avec UBSan fatal, et `-pthread` pour le runtime
  threaded. Les deux modèles de signatures préexistants (81 et 36 cas)
  sont inclus dans ces suites, avec leurs oracles inchangés.
- `CRUST_SANITIZE=undefined python3 tests/run_feature_regression.py` :
  **173 méthodes réussies en 42,295 s**, `nested-features-regression.log`.
- Même script avec `--inject` : **36 méthodes réussies en 17,843 s**,
  `nested-features-injected.log`. Ajout d'une feature inutilisée aux cas
  existants de méthodes et structures pour exercer le nouveau parcours ;
  assertions conservées. Ces cas recouvrent une partie des 173 précédents.
- Compilation Python des modules modifiés et des nouveaux tests réussie.

## Mutations

`python3 tests/run_builtin_feature_mutations.py` a détecté les sept mutations
dans des copies temporaires, avec les assertions originales. Journal :
`validation/nested-features-mutations.log`.

Les quatre mutations du cycle builtin restent détectées. Trois nouvelles :

1. Réintroduire l'égalité entre receveur et autre argument contraint : rejet
   incorrect du programme Left/Right admis.
2. Ignorer la contrainte du résultat : les trois feuilles incorrectes sont
   acceptées à tort, même sans appel de la méthode.
3. Accepter n'importe quelle comparaison imbriquée au lieu d'une paire déjà
   en cours : les mêmes trois violations sont acceptées à tort.

Pas de taux général de détection ni de preuve universelle tirés de ces fautes.

## Écart restant et limites

Le programme `validation/open-feature-async-structure.crust` reste refusé :
la capture `&Item` d'une structure utilisateur n'est pas prise en charge par
le backend async. Le diagnostic exécuté est conservé dans le fichier `.log`
voisin. C'est une limite d'implémentation, pas une nouvelle règle de refus.
La spécialisation de la feature est résolue avant cette restriction.

Les signatures builtin non exercées, `char.utf8_len()` via une feature,
les projections plus générales et les autres limites du backend async restent
à traiter. Les scénarios multithread exercés ne couvrent pas toutes les
interleavings ; ni TSan ni preuve formelle n'ont été employés ici.
Les écarts de stockage et de scheduler du périmètre global restent ouverts.
