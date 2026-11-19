[English](BORROWED_RETURNS.md)

# Retours d'objets contenant un emprunt : enfant → parent

Extension ultérieure : les [champs &mut Int](MUTABLE_REFERENCE_FIELDS.md) sont maintenant disponibles ; les mesures ci-dessous décrivent ce cycle historique.

Cycle du 2 novembre 2026. Extension demandée par l'utilisateur ; procédure selon
[VALIDATION_GUIDELINES.md](VALIDATION_GUIDELINES.md), règles et dépendances dans
[LANGUAGE_RULES.md](LANGUAGE_RULES.md) et [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md).

## Comportement

```rust
enum View { Item { data: &Int }, Empty {} }

fn make_view(views: &mut Pool<View>, data: &Int) -> <- View {
    let mut view = new(views) View.Item { data: data };
    return <- view;
}
```

L'allocation Int est injectée par emprunt : elle appartient déjà au scope
appelant ou à un ancêtre. La variable de paramètre disparaît au retour, mais le
champ contient le pointeur vers l'allocation d'origine, pas vers cette variable.
Le résultat conserve l'emprunt jusqu'à son dernier usage.

```rust
let mut view = make_view(&mut view_pool, &data);
drop(-> data);   // Refusé si la lecture suivante reste possible.
print(view);
```

Après le dernier usage de `view`, `data` peut être détruite ou son pool reset,
sous réserve des autres emprunts. Détruire/reset le porteur ne détruit pas sa
cible. Une adresse de slot réutilisée ne réactive pas les anciens accès.

## La vérification de frontière

Pour chaque passage enfant → parent, toutes les cibles possibles doivent être
vivantes, valides sur tous les chemins et rattachées à la destination ou à un
ancêtre. Le pool du résultat doit lui aussi survivre selon les règles existantes.
Les frontières successives sont vérifiées séparément :

```rust
fn wrong(data_pool: &mut Pool<Int>, views: &mut Pool<View>) -> <- View {
    let mut data = new(data_pool) Int(42);
    let mut view = make_view(views, &data); // Valide : retour vers ce scope.
    return <- view; // Refusé : data n'est pas durable dans le parent de wrong.
}
```

La durée du pool ne remplace pas la durée de vie de l'allocation. Injecter un
Int par `->` fait descendre son rattachement dans l'enfant ; ce n'est pas une
injection par emprunt. Retourner une vue le référençant est donc refusé dans ce
sous-ensemble. D1 interdit désormais la promotion automatique de cette cible ;
la proposition antérieure est abandonnée, et non simplement différée.

Une cible créée comme argument temporaire `&new(pool) Int(...)` appartient au
scope appelant : une vue peut la retenir dans ce scope. En revanche, un wrapper
qui crée lui-même ce temporaire ne peut pas retourner la vue à son propre parent.

## Contrats sans corps

Le résumé du résultat conserve séparément :

- Ses allocations candidates et leurs sources de stockage, comme auparavant.
- `borrowed_fields` : pour chaque chemin `Variante.champ`, les identités des
  paramètres Int empruntés ou des champs d'objets reçus dont il dépend.
- `fresh_variants` : variantes des objets construits, combinées aux variantes
  réellement possibles des entrées restituées.

Extrait de `effects` pour `make_view` :

```json
"borrowed_fields": [
  {"field": "Item.data", "targets": [{"kind": "parameter", "parameter": "data"}]}
]
```

Un relais substitue les paramètres ; restituer un porteur reçu par `->` conserve
ses champs par identité `field_parameter`. L'analyse refuse d'exporter une cible
locale, même sans appel de la fonction et sans backend mémoire. À l'appel opaque,
les identités concrètes sont substituées et attachées au résultat : le vérificateur
n'ouvre pas le corps du callee. Un test retire explicitement corps et tables
indépendantes d'inférence.

Le backend spécialisé conserve les adresses et vérifie que champs, origines et
variantes observés respectent ce contrat. Les résumés ne sont pas une oracle
indépendante : l'inférence et leur application restent dans la base de confiance.
Le runtime C, la représentation des slots et le format des pointeurs ne changent
pas dans ce cycle. Aucun handle ni comptage de références runtime n'est ajouté.

Les branches réunissent les cibles possibles, même si elles partagent un même
pool. Les variantes vides n'inventent pas de cible. La règle conservative des
resets est maintenue : un reset possible protège les usages futurs, même sur un
chemin divergent. Aucune corrélation de chemin nouvelle n'assouplit ce choix.

## Réemprunt partagé d'un parent mutable

Un objet retourné peut conserver un réemprunt partagé venant d'un accès mutable :

```rust
let mut loan = &mut data;
let mut view = make_view(&mut view_pool, loan);
print(view);
loan.set(7); // Autorisé après le dernier usage de la vue.
```

Inverser les deux dernières instructions est refusé. Les écritures incompatibles
du parent sont suspendues tant que ce réemprunt partagé sert encore. Les liens
`read_parent` / `borrow_parents` sont uniquement des métadonnées statiques ; les
retours et déplacements successifs du porteur les conservent. Il n'y a pas de
champ `&mut` et le champ &Int ne donne aucun droit mutable supplémentaire.
Les réemprunts stockés généraux hors de ces champs restent restreints.

## Baseline, défauts et attentes de tests

La baseline historique était 572 tests standard et UBSan au cycle précédent.
Elle n'a pas été rejouée intégralement avant le correctif ; le snippet initial
a été exécuté et refusé par la restriction explicite des retours contenant des
emprunts. Cette restriction est levée selon la demande approuvée.

Défauts détectés pendant l'implémentation et corrigés :

1. Le contrôle de retour normal cherchait une activation déjà dépilée et pouvait
   produire `StopIteration`. La destination est maintenant enregistrée dans le
   cadre d'appel et employée pour les retours normaux comme conditionnels.
2. Un réemprunt partagé conservé après l'appel réactivait trop tôt le parent
   mutable, produisant une erreur d'invariant. Les liens de suspension sont
   désormais conservés avec le résultat, jusqu'au dernier usage.
3. Une vérification complémentaire après un premier passage réussi de 604 tests
   a trouvé un nouvel alias sans lien avec ce réemprunt : l'accès d'origine
   tentait de créer une référence tandis que le parent mutable devait encore
   servir. Le programme échouait ensuite sur un invariant. Cet accès incompatible
   est désormais refusé au bon endroit ; deux variantes de régression couvrent
   aussi le cas d'arguments déjà préparés. Les suites et campagnes sont relancées
   après cette correction, sans assimiler le premier passage à la validation finale.

Deux premiers programmes de test classés valides violaient U1, car une vue reçue
était écrasée/reset sans usage explicite. Les fixtures ont été corrigées pour
utiliser ces vues ; U1 n'a pas été assouplie. L'ancien test refusant une fonction
vide retournant View vérifie maintenant l'absence de résultat, et non une
restriction de type que l'utilisateur vient de lever.

## Validation et interactions

[tests/test_borrowed_returns.py](../tests/test_borrowed_returns.py) contient 33 méthodes :
transferts successifs de fonctions et blocs, cible locale/paramètre transféré,
pool local, drop, mutation, réaffectation, reset, variantes vides, retours
conditionnels et if expression, identité, réemprunts mutables, arguments,
réutilisation de slots et boucles. Les refus et les cas proches admissibles sont
comparés ; des programmes admissibles sont compilés et exécutés en C.

Le modèle indépendant de routes de scopes utilise les niveaux de création et
de destination des cibles, sans résumés ni décisions du compilateur. Graines
0–23, profondeur 1–4 : **12 programmes attendus valides exécutés** et **12 attendus
invalides refusés**. Il ne modélise pas toute l'exclusivité des emprunts ni tous
les graphes. Les tests d'interaction et les modèles des cycles précédents
complètent cette exploration sans en faire une couverture exhaustive.

Les 66 règles ont été reconsidérées, avec attention à S3/S5, T3/T5/T6/T9/T11,
V4/V5, B1/B2/B3/B4a–e, L1/L2/L3/L6, A2/A3/A5/A6 et P8/P9. La matrice conserve
les règles non implémentées comme non vérifiées. D1 a ensuite été révisée par
décision explicite : pas de promotion implicite, avec le refus déjà implémenté.
Aucun support de graphe général ou de retour direct d'un emprunt B5 n'est déduit
de cette extension. Les [retours directs &Int](DIRECT_BORROW_RETURNS.md) sont
implémentés et validés dans un cycle distinct ultérieur.

## Mutations et C optimisé

```sh
python3 tests/run_borrowed_return_mutations.py --output validation/borrowed-return-mutations.json
python3 tests/run_reference_field_mutations.py --output validation/reference-field-mutations-current.json
python3 tests/validate_borrowed_return_c.py --output validation/borrowed-return-c.json
```

Cinq fautes sélectionnées sont détectées : champ absent du contrat, dépendance
perdue à l'appel opaque, cible locale acceptée par l'inférence seule, ancêtre
valide refusé et parent mutable perdu. Les quatre mutations des champs &Int
ont également été rejouées et détectées, après adaptation d'une ancre à la
nouvelle signature interne. Les tests/oracles n'ont pas été modifiés dans les
copies injectées. Empreintes avant/après identiques pour les deux campagnes.
Ces neuf fautes choisies ne fournissent pas un taux global de détection.

[Rapport des nouvelles mutations](../validation/borrowed-return-mutations.json) ·
[Régressions des mutations précédentes](../validation/reference-field-mutations-current.json).

Le [rapport C](../validation/borrowed-return-c.json) conserve 12 exécutions : trois
programmes × O0/O2/Os/O2-UBSan. Huit exécutions normales vérifient les identités,
valeurs et destructions ; quatre s'arrêtent sur l'épuisement attendu du pool,
sans dérouler les destructeurs. Attentes spécifiées sans lire les décisions du
compilateur ou le C émis. Une seule famille disponible, Clang 20.1.3 ; pas de
comparaison avec une famille indépendante. ASan n'est pas exécuté dans ce cycle,
les essais précédents de l'hôte échouant aussi pour un programme C vide.

## Limites

Champs immuables &Int seulement, pas de références d'enums ni graphes transitifs,
cycles, destructeurs utilisateur, async, threads ou FFI. Les retours directs
&Int ont désormais leur [cycle dédié](DIRECT_BORROW_RETURNS.md). Tous les usages d'un porteur restent des
usages conservateurs de ses champs. La précision est bornée par les unions de
cibles/variantes ; les tailles, chemins et plateformes ne sont pas exhaustifs.
Il ne s'agit pas d'une preuve formelle de sûreté.
La promotion automatique des cibles n'est pas une extension différée : elle est
interdite par la [décision D1 révisée](NO_IMPLICIT_PROMOTION.md).

## Suites complètes

Les suites finales après le dernier correctif ont terminé sans échec :

| Commande | Résultat exécuté |
| --- | --- |
| `python3 -m unittest discover -s tests -q` | 605 tests, OK, 334,931 s |
| `CRUST_SANITIZE=undefined python3 -m unittest discover -s tests -q` | 605 tests, OK, 334,730 s |

Les 33 nouvelles méthodes, les modèles existants de nettoyage et de types de
pools, le modèle des champs &Int et l'oracle runtime de 3000 opérations sont
inclus dans ces deux exécutions. Le décompte des programmes admis/refusés de
toutes les sous-variantes de la suite n'est pas agrégé ; les comptes 12/12
concernent exclusivement le modèle indépendant des routes de scopes.

Les neuf mutations et les douze exécutions C ont été relancées sur le code
final et ont satisfait leurs contrôles, dans des campagnes distinctes des suites.
Les empreintes des fichiers Python sont identiques avant/après chaque injection.
Le [bilan structuré](../validation/borrowed-return-suites.json) conserve les commandes,
durées, premier passage et contre-exemple supplémentaire, ainsi que les limites
d'instrumentation. UBSan instrumente le harnais C et l'oracle ; les tests CLI qui
construisent leurs binaires sans ces options ne deviennent pas instrumentés par
la variable de test. Les trois cas C optimisés sont explicitement instrumentés
dans leur configuration O2-UBSan. Aucun échec de ce cycle ne reste ouvert ;
les limites de couverture ci-dessus restent applicables.
