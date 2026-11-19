[English](POOL_REQUIREMENTS_VALIDATION.md)

# Exigences de pools : correction et validation

Cycle du 2 novembre 2026. Références : [guidelines](VALIDATION_GUIDELINES.md),
[règles normatives](LANGUAGE_RULES.md), [matrice de traçabilité](VERIFICATION_MATRIX.md).

## Défaut, baseline et règles concernées

Aucune règle normative n'est ajoutée ni modifiée. P8 impose le type du pool,
B4 les types/modes des paramètres, B4b la propagation des exigences et B4e
le contrôle par contrats. Le défaut concernait le compilateur :

```rust
enum Message { Empty {} }
fn inspect(p: &Pool<Int>) {}
fn relay(p: &Allocator) { inspect(p); }
fn main() {
    let mut p = Pool<Message>::new(1);
    relay(&p);
}
```

Reproduit avant correction : `check` acceptait, le backend refusait avec
`p attend une source Pool<Int>`. Une signature sans allocation imposait un type
qui disparaissait du résumé du wrapper. Le contrôle concret n'ouvrait plus le
corps appelé ; le passage symbolique admettait une source générique.

La baseline historique du cycle précédent était 522 tests standard et UBSan.
Elle n'a pas été réexécutée intégralement avant modification ; le contre-exemple
ci-dessus a été exécuté sur l'état initial. Les résultats nouveaux sont distincts.

## Correctif

`FunctionEffects.pool_requirements` contient des couples (indice du paramètre,
type de pool). L'interface opaque `FunctionContract` porte ce champ, également
exporté dans le JSON de `effects`.

- Une signature `&Pool<T>` ou `&mut Pool<T>` impose ce pool, même vide.
- L'exigence est substituée dans les sous-appels, y compris à plusieurs niveaux
  et lorsque les paramètres sont réordonnés.
- Une source locale est contrôlée localement ; son exigence n'est pas exportée
  comme celle d'un paramètre extérieur masqué.
- Des types de pools incompatibles pour une même source sont refusés, ainsi
  que les conflits avec les types d'allocations dans cette source.
- Les entrées symboliques intègrent les exigences, y compris si des provenances
  sont réunies par une égalité imposée par `source.drop`.
- Les appels opaques vérifient la source réelle sans corps ni tableaux
  d'inférence séparés. Le backend conserve le même contrôle.

Une allocation Int n'impose pas un pool : les backends Int explicites existants
restent admis. Un enum exige son pool typé. Le type exigé n'accorde aucun droit
mutable supplémentaire.

Un test existant a détecté un changement de diagnostic : le mauvais pool était
bien refusé mais le mot `incompatible` manquait. Le message a été corrigé, sans
affaiblir l'attente du test. Un premier lancement des suites complètes a été
interrompu à cette détection, puis relancé après réussite des tests ciblés.

## Réexamen et invariants

Les 66 règles ont été relues et reliées à leurs profils de preuves/limites dans
la matrice. Les règles futures restent non vérifiées ; les règles implémentées
restent partiellement couvertes. Cet inventaire n'est pas une preuve règle par règle.

Invariants examinés : type de source conservé, substitution correcte des
arguments, distinction allocation/exigence de pool, portée des sources locales,
permissions readonly/mutable inchangées, provenance et identité conservées,
nettoyage unique et ordre sémantique, capacité et réutilisation.

Interactions nouvelles : branches littérales, return, divergence, boucle et
condition while, arguments imbriqués, masquage local, égalité de sources de drop,
allocation d'un autre type, restitution d'identité, slot réutilisé et reset.
Les suites existantes apportent d'autres combinaisons de transferts, emprunts,
provenances, réaffectations et sorties de scopes. Ce n'est pas un produit
cartésien exhaustif de toutes les règles.

## Modèle indépendant et génération

[pool_requirement_model.py](../tests/pool_requirement_model.py) construit des
sommets (fonction, paramètre), des routes d'arguments et des exigences terminales.
Il énumère les chemins sans lire le parseur, les résumés du compilateur ou le C.
Le compilateur utilise des résumés récursivement mis en cache ; le modèle suit
les routes jusqu'aux déclarations typées.

Campagne exécutée : graines **0 à 39**, **7 fonctions** et **3 paramètres de
source** par fonction, permutations et terminaux Int/Message. **20 programmes
attendus valides acceptés**, **40 attendus invalides refusés** (contrats
contradictoires ou mauvaise source concrète). Les résumés des graphes admissibles
sont comparés aux obligations prédites indépendamment.

Limites : modèle readonly sans allocation, reset, boucle ni alias mutable.
Ces interactions ont des tests distincts. Le renderer du graphe est lui-même
une hypothèse, challengée par des exemples déterministes de réordonnement et
le contre-exemple minimal ; il ne prouve pas toute la grammaire. Les **23 méthodes
ciblées** contiennent plusieurs sous-cas ; le nombre global de programmes
admis/refusés de toute la suite n'est pas agrégé.

## Mutations en copies temporaires

```sh
python3 tests/run_pool_requirement_mutations.py --output validation/pool-requirement-mutations.json
```

La baseline ciblée passe avant injection ; tests et oracles restent inchangés.

| Faute sélectionnée | Résultat | Témoin |
| --- | --- | --- |
| Omettre une exigence de signature vide | Détectée | Résumé de la signature |
| Omettre la propagation transitive | Détectée | Modèle indépendant des routes |
| Substituer le mauvais paramètre | Détectée | Réordonnement à plusieurs niveaux |
| Omettre le contrôle d'appel opaque | Détectée | Appel sans corps ni tableaux d'inférence |
| Refuser un pool correspondant | Détectée | Programme valide exécuté |

Les empreintes avant/après confirment l'absence de modification du checkout
par l'injection. Le [rapport JSON](../validation/pool-requirement-mutations.json)
conserve résultats, diagnostics et empreintes. Cinq fautes choisies ne donnent
pas un taux global de détection. Aucune mutation runtime n'a été réexécutée ici.

## C généré et instrumentation

```sh
python3 tests/validate_pool_contract_c.py --output validation/pool-requirement-c.json
```

**12 exécutions C** : trois programmes × `-O0`, `-O2`, `-Os` et
`-O2 -fsanitize=undefined -fno-sanitize-recover=all`. Deux programmes couvrent
les deux chemins d'une sélection avec exigence transitive, identité, slot réutilisé,
enums, retours et resets ; le troisième doit s'arrêter sur dépassement de capacité
sans déroulement des destructeurs. Valeurs/traces attendues spécifiées sans lire
l'état du compilateur ou le C généré. **Huit exécutions normales et quatre arrêts
attendus** ont satisfait ces contrôles. Aucun diagnostic UBSan n'a été observé
sur ces chemins.

Une seule famille C disponible : **Homebrew Clang 20.1.3**. L'alias `gcc` pointant
vers Clang n'est pas compté comme une implémentation indépendante. Le
[rapport JSON](../validation/pool-requirement-c.json) conserve configurations et résultats.

Les suites complètes incluent les modèles existants : nettoyage indépendant
(32 opérations, graines 17 et 83, trois backends) et oracle runtime
(3000 opérations, graine 12345, deux tailles de variantes). Exploration bornée.
Le résultat de leur exécution est consigné avec celui des suites complètes.

ASan non exécuté dans ce cycle : les essais précédents sur cet hôte échouaient
également sur un programme C vide. Dans la suite UBSan, le harnais C et l'oracle
sont instrumentés ; les binaires construits par la CLI gardent ses options
ordinaires. La campagne dédiée instrumente explicitement ses trois cas à `-O2`.

## Limites et ambiguïtés conservées

- Ni preuve formelle, ni couverture exhaustive de toutes les combinaisons.
- Récursion, collections grandissantes, graphes de références, destructeurs
  utilisateur, références retournées, concurrence et FFI restent hors périmètre.
- La mission vise l'absence d'allocation dynamique générale, mais le prototype
  et P7 gardent des backends explicites de compatibilité. Leur retrait n'est
  pas décidé ici ; les exemples nouveaux privilégient les pools.
- Les exemples historiques et règles futures ne sont pas interprétés comme
  des fonctionnalités implémentées ou vérifiées.
- Les obligations des branches abstraitement possibles sont réunies, même
  avec une condition littérale. Après un return sans continuation, elles ne
  sont plus ajoutées. Ce comportement vient des règles existantes.
- Toutes les erreurs OS, tailles et plateformes de mapping ne sont pas explorées.
  Aucune comparaison de familles C distinctes n'a été possible.

## Résultat global

Les deux suites ont terminé sans échec :

| Commande | Résultat exécuté |
| --- | --- |
| `python3 -m unittest discover -s tests -q` | 545 tests, OK, 281,060 s |
| `CRUST_SANITIZE=undefined python3 -m unittest discover -s tests -q` | 545 tests, OK, 281,265 s |

Le modèle de nettoyage et l'oracle runtime existants sont inclus dans ces deux
exécutions. Les 23 nouvelles méthodes de régression, la campagne générée et
les scénarios d'interaction ciblés sont également inclus. Les mutations et les
12 exécutions C à plusieurs niveaux d'optimisation sont des campagnes séparées,
exécutées selon les commandes précédentes. Le nombre de tests ne mesure ni
l'exhaustivité ni un niveau de sûreté global.

Les [résultats structurés des suites](../validation/pool-requirement-suites.json)
conservent les commandes, durées et restrictions d'instrumentation. Aucun
échec de ce cycle ne reste ouvert. Les propriétés non vérifiées et les limites
de la méthode restent celles indiquées dans ce rapport et dans la matrice.
