# Extraction et conversions numériques vérifiées

[English](CHECKED_EXTRACTION_CONVERSIONS.md)

Cette décision remplace l’ancienne restriction imposant à `as` de réussir pour
toutes les valeurs possibles du type source. Elle n’ajoute ni trait, ni conversion
d’erreur implicite, ni allocation, ni nouveau modèle de possession.

## Suffixe `!`

`expression!` évalue son opérande une seule fois. Pour `Result<T, E>`, il extrait
`T` depuis `Ok` ; pour `Option<T>`, il extrait `T` depuis `Some`. `Err` et `None`
arrêtent le programme entier avec un diagnostic indiquant la variante et la
position source. Le contenu de l’erreur n’est pas formaté automatiquement.

L’extraction suit les règles ordinaires de déplacement et de copie. Les emprunts
conservent leurs dépendances envers leurs cibles. Les allocations et agrégats
conservent leurs dépendances de stockage et de nettoyage ; ils sont détruits une
seule fois après une extraction réussie. `Result<(), E>!` vérifie le succès et
produit la valeur unité.

`!` a la même priorité postfixe que les appels, indexations, `.await` et `?`.
Les suffixes s’appliquent de gauche à droite. Le préfixe `!condition` reste la
négation booléenne et `!=` reste l’inégalité. `future.await!` extrait le résultat
terminé ; `future!` est refusé car une Future n’est ni Result ni Option.

`?` conserve son retour anticipé. `!` n’exige pas que la fonction englobante
renvoie Result/Option ni qu’elle fournisse une conversion d’erreur.

## Conversion numérique `as`

`valeur as T` évalue son opérande numérique une fois. Il réussit seulement si la
valeur est exactement représentable dans `T` ; sinon le programme s’arrête avec
les types de conversion et la position source. Les types concernés sont les
entiers existants, `usize`, `f32` et `f64`. Cette décision n’ajoute pas de conversion
depuis les booléens/références ni de méthode de conversion arbitraire.

Les vérifications sont celles de `T::try_from(valeur)` : bornes des entiers,
rejet des valeurs négatives vers un entier non signé, valeur flottante finie et
entière avant conversion vers un entier, absence de perte de précision vers un
flottant. Les conversions flottantes non finies sont refusées selon le contrôle
existant de `try_from`. Il n’y a ni troncature, ni saturation, ni débordement
circulaire, ni arrondi considéré comme un succès.

`try_from` renvoie toujours un Result récupérable. `valeur as T` est la variante
avec arrêt de `T::try_from(valeur)!`. Les contrôles redondants peuvent être omis
lorsque toutes les valeurs sources sont exactement représentables.

## Échecs fatals

Les deux opérateurs produisent un diagnostic et arrêtent le processus. Ils ne
dépilent pas les scopes, ne propagent pas d’erreur et ne garantissent pas
l’exécution des destructeurs sur le chemin d’échec. Le succès conserve le
nettoyage ordinaire. Les chemins et positions sources sont conservés à travers
les transformations ; une ancre de code généré est explicitement signalée si la
position exacte n’est pas disponible.
