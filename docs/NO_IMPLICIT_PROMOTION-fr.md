[English](NO_IMPLICIT_PROMOTION.md)

# Décision : aucune promotion implicite d'une cible empruntée

Décision explicite de l'utilisateur, consignée le 2 novembre 2026.

D1 dans [LANGUAGE_RULES.md](LANGUAGE_RULES.md) remplace la proposition antérieure
de transfert automatique des dépendances. Transférer un objet ne transfère pas
ses cibles empruntées et ne prolonge pas leur vie. À chaque frontière enfant →
parent, toutes les cibles doivent déjà être assez durables dans la destination
ou un de ses ancêtres ; sinon, le transfert est refusé. Cela reste vrai lorsque
les pools sont durables et lors de transferts successifs. La promotion
implicite est interdite, et non une fonctionnalité différée.

```rust
fn wrong(data_pool: &mut Pool<Int>, views: &mut Pool<View>) -> <- View {
    let mut data = new(data_pool) Int(42);
    let mut view = new(views) View.Item { data: &data };
    return <- view; // Refusé : data appartient à l'enfant.
}
```

Le compilateur refuse déjà ce cas. Aucun fichier d'implémentation, runtime ou
test n'est modifié par cette décision documentaire. Les contrats continuent
de suivre les cibles pour protéger leurs usages, sans les promouvoir.

## Réexamen et validation

Les 66 identifiants des règles sont conservés dans la matrice. D1/D2 sont
partiellement couverts pour les champs &Int ; les graphes généraux restent
non implémentés et non vérifiés. Les dépendances I1, T3/T5, B4c, D3/D4,
A2/A3, L2/L3 et P8/P9 ont été reconsidérées. Aucune autre sémantique de
transfert, d'emprunt, de pool ou de destruction n'est changée.

Régressions applicables : `test_borrowed_returns`, `test_reference_fields`,
`test_scope_exit` et `test_reset_transitions`, en standard et UBSan. Elles couvrent
les cibles déjà durables admises, les cibles locales refusées, les frontières
successives, drop/reset et sorties de scopes. Elles incluent les modèles
existants de routes de scopes (12 cas valides, 12 invalides) et de frontière des
champs (19 valides, 13 invalides). Leurs attentes ne sont pas modifiées pour
correspondre au compilateur : la décision conserve les refus déjà testés.

La dernière suite globale historique était de 605 tests standard et UBSan ;
elle n'est pas présentée comme réexécutée pour cette modification documentaire.
Les mutations et campagnes C optimisées du cycle précédent restent historiques,
sans prétendre à une nouvelle exécution ici. La validation ciblée ne constitue
pas une preuve formelle ni une exploration exhaustive des graphes.

Résultats exécutés sur le code inchangé :

| Configuration | Résultat |
| --- | --- |
| Standard, quatre modules ciblés | 85 tests, OK, 73,227 s |
| `CRUST_SANITIZE=undefined`, mêmes modules | 85 tests, OK, 72,920 s |

Les effets sur les autres règles ont été examinés dans la matrice ; les
fonctionnalités non implémentées restent non vérifiées. Les contrôles ciblés
ne sont pas présentés comme une nouvelle exécution de toute la suite globale.
Les [résultats structurés](../validation/no-implicit-promotion.json) conservent
les commandes, les limites et la référence à la baseline historique.
