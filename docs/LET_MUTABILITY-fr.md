[English](LET_MUTABILITY.md)

# Déclarations et mutation du contenu

Extension ultérieure : les [retours &mut Int](MUTABLE_BORROW_RETURNS.md) sont
maintenant disponibles. Les restrictions et mesures ci-dessous décrivent le
périmètre du cycle historique, dont les sources brutes et empreintes sont conservées.

Cycle du 2 novembre 2026. Décision explicite de l'utilisateur : remplacer `var`
par `let` / `let mut`, retirer `set(name, 20)`, et faire de `name = 20` et
`name.set(20)` des mutations de contenu préservant l'allocation. Les règles
V4/B4 sont précisées dans [LANGUAGE_RULES.md](LANGUAGE_RULES.md), leurs
interactions dans la [matrice des 66 règles](VERIFICATION_MATRIX.md).
Le cycle suit les [guidelines de validation](VALIDATION_GUIDELINES.md).

## Comportement

```rust
let mut memory = pool<Int>(1);
let mut nombre = new(memory) Int(10);

nombre = 20;
nombre.set(30);

let vue = &mut nombre;
vue.set(40);
print(vue);
```

Les écritures modifient le même Int, au même slot et à la même adresse.
Aucune allocation, réception ou destruction ne correspond à ces écritures.
Le nettoyage final voit le contenu 40 et n'est exécuté qu'une fois.
L'[exemple exécutable](../examples/let_mutability.crb) affiche aussi les adresses.

La variable et le type de référence ont deux droits distincts :

| Déclaration | Écriture dans la cible | Réaffectation de la variable |
| --- | --- | --- |
| `let nombre = new(memory) Int(10)` | Refusée depuis cet accès | Refusée |
| `let mut nombre = new(memory) Int(10)` | Autorisée, sans emprunt incompatible | Autorisée selon les expressions supportées |
| `let vue = &mut nombre` | Autorisée par `.set` | Refusée |
| `let mut vue = &mut nombre` | Autorisée par `.set` | Autorisée selon les expressions supportées |
| `let mut vue = &nombre` | Refusée : référence en lecture | Autorisée selon les expressions supportées |

L'immutabilité est celle du nom, et non une promesse de gel global attachée à
l'allocation. On peut consommer un accès immutable avec `drop(-> name)` ou le
transférer explicitement à un nouveau receveur mutable. Former `&mut name`
depuis un accès direct exige sa déclaration mutable. Les restrictions d'emprunt
continuent de s'appliquer à tous ces cas.

Un paramètre reçu par valeur est immutable par défaut :

```rust
fn edit(mut data: -> Int) -> <- Int {
    data = 20;
    return <- data;
}

fn write(data: &mut Int) {
    data.set(20); // mut data n'est pas nécessaire pour sa cible.
}
```

`mut n: Int` permet de modifier la copie scalaire reçue, sans modifier l'argument
chez l'appelant. `mut data: &Int` ne permet pas de modifier la cible partagée.
Les noms mutables des paramètres sont conservés dans les contrats et lors de
la normalisation d'un retour Void. Un appel recevant un objet par transfert
peut donc le modifier si son paramètre receveur est mutable, même si le nom
consommé chez l'appelant était immutable.

Les sources locales utilisées pour allouer/reset ou pour `source.drop`
exigent `let mut`. Un paramètre &mut Pool fournit déjà la capacité d'écriture,
sans exiger un paramètre `mut memory`; un &Pool reste en lecture.
Le nettoyage automatique et `drop(-> value)` n'exigent pas de rendre mutable
la variable consommée.

## Mutation, référence et remplacement

`data = scalar_expression` sur un accès direct Int mutable évalue le RHS puis
écrit dans le contenu de la cible. Le RHS peut utiliser un emprunt pour la
dernière fois ; un usage après l'écriture continue de faire refuser celle-ci.
Si le RHS consomme la cible ou reset son stockage, la cible est vérifiée de
nouveau et l'écriture est refusée. Une nouvelle allocation au même emplacement
ne réactive pas cet ancien accès.

`data = new(memory) Int(20)` fournit une allocation : les règles précédentes de
remplacement restent actives. Le nouvel objet est créé avant de détruire
l'ancien, et le pool doit permettre leur coexistence momentanée. Une restitution
d'exactement la même allocation ne la détruit pas. Remplacement et réaffectation
exigent une variable mutable. Le remplacement d'accès alloués ou empruntés reste
limité au scope de la variable dans le prototype ; les mutations en place des
Int et des scalaires peuvent utiliser un accès mutable d'un ancêtre, comme
l'ancienne opération set le permettait.

`view = 20` ne se déréférence pas implicitement : view reste une variable de
référence, que cette réaffectation ne peut convertir en Int. Utiliser
`view.set(20)` avec un &mut Int. La méthode accepte actuellement un littéral
Int32 signé, comme l'ancienne primitive. Les expressions scalaires déjà
supportées sont disponibles à droite de `=`. Les méthodes utilisateur et
l'affectation `*view = expression` ne sont pas ajoutées dans ce cycle.

## Vérificateur, contrats et C

La mutabilité est attachée aux déclarations/paramètres et aux bindings, sans
être un nouveau type d'allocation. Le contrôle d'accès central distingue les
écritures directes depuis un nom mutable des écritures à travers &mut. Les
imports de scopes conservent cette propriété. Les temporaires alloués encore
sans nom peuvent être empruntés mutablement, conformément au comportement
précédent des arguments.

Une mutation de contenu ne crée pas de nouveau binding ni d'entrée de nettoyage.
Le résultat C est une écriture dans `Cell.value`; la source, l'identité et le
pointeur de nettoyage restent inchangés. Les assignations scalaires en place
écrivent leur variable C, y compris depuis les blocs enfants et itérations.
Le runtime de pool et la disposition des slots sont inchangés.

L'analyse des résultats conserve l'identité allouée après une écriture scalaire.
L'analyse des contraintes conserve les assets de cette allocation et vérifie
leur historique après les effets du RHS. Sinon, un contrat opaque pourrait
oublier un reset lors d'une écriture, même si le backend spécialisé rejetait
ensuite le code. Un test avec fonction Void consommant la cible force ce
contrôle sur l'écriture elle-même, sans dépendre d'un usage dans un return.

## Validation exécutée

Le cycle précédent comportait 647 méthodes réussies en standard et sous UBSan.
Les 25 nouvelles méthodes ont passé leurs contrôles ciblés. Un comptage exécuté
sur ce corpus recense **33 programmes distincts admis et exécutés**, et
**50 programmes distincts refusés** par `verify_program` puis `compile_source`.
Les [sources et comptes](../validation/let-fixture-corpus.json) sont conservés ;
ils ne comptent pas tous les sous-cas des suites globales.

Le modèle indépendant de contenu utilise 12 graines (0–11), 12 écritures par
graine, choisies entre `=` et `.set`. L'oracle est une liste de valeurs Int,
sans lecture du vérificateur ni du C. Il compare chaque état affiché, l'adresse
initiale/finale et l'unique destruction. La matrice déclarative des capacités
énumère propriétaire, référence partagée et référence exclusive, avec/sans mut,
pour affectation, méthode et création d'un &mut : **18 cas, 5 admis/13 refusés**.
Les autres cas couvrent fonctions, identité restituée, paramètres scalaires par
copie, parent mutable, imports, branches et continue, RHS avec emprunt/drop/reset,
réaffectation de références, remplacement, sources, slot réutilisé et retours &Int.

Les fixtures précédentes ont été migrées : anciens var → let mut pour préserver
leurs droits précédents, set → méthode, paramètres alloués → bindings mutables.
Le [contrôle de migration](../validation/let-fixture-migration.json) constate les
mêmes noms de méthodes et secondes expressions des assertions de comparaison
pour les 25 fichiers de tests précédents. Il ne constitue pas une preuve de
conservation de chaque oracle. Les graines, graphes et traces attendues des
modèles précédents sont conservés ; les nouveaux tests incluent aussi des let
immutables et ne se contentent pas de cette migration conservative.

Cinq mutations sélectionnées sont détectées dans des copies temporaires : ignorer
l'immutabilité, exiger mut sur la variable contenant un &mut, allouer au lieu
d'écrire le contenu, perdre l'identité dans le résumé après écriture, oublier
l'historique de reset de la cible. La dernière est détectée au stade opaque,
indépendamment du refus supplémentaire par le backend. Les 19 mutations des
références, champs et retours précédents sont rejouées et détectées. Les cinq
campagnes conservent les empreintes Python du projet. Aucun taux global de
détection n'en est déduit.

Les quatre campagnes C (contenu, retours directs, porteurs et pools) ont chacune
12 exécutions : trois programmes en O0, O2, Os et O2+UBSan, soit **48 exécutions
conformes**. Les observations imposées incluent adresses stables, valeurs,
destructions, resets, réutilisation et échec sur capacité. La mutation simple
ne consomme pas de deuxième slot dans un pool de capacité un ; un remplacement
qui dépasse sa capacité s'arrête avant la destruction de l'ancien objet. Les
essais instrumentés arrêtent au premier diagnostic UBSan ; aucun n'est émis.
Une seule famille C est disponible. L'exemple CLI est aussi exécuté, sans
instrumentation implicite par CRUST_SANITIZE.

Rapports : [mutations nouvelles](../validation/let-mutations.json),
[références](../validation/let-reference-value-mutations.json),
[retours directs](../validation/let-direct-mutations.json),
[porteurs](../validation/let-holder-mutations.json),
[champs](../validation/let-field-mutations.json),
[C contenu](../validation/let-content-c.json),
[C retours directs](../validation/let-direct-c.json),
[C porteurs](../validation/let-holder-c.json), [C pools](../validation/let-pool-c.json).
Les suites globales sont terminées : **672 tests standard réussis
(484.091 s)** et **672 tests sous UBSan réussis (484.634 s)**,
sans saut ni échec non résolu. Les modèles précédents de provenance, nettoyage,
contrats, champs, scopes et runtime sont inclus. Le [bilan brut](../validation/let-suites.json)
conserve commandes, sorties, durées, configurations et empreintes Python.

Pendant la mise au point, la nouvelle règle d'immutabilité a d'abord fait refuser
un ancien cas valide de temporaire alloué emprunté mutablement dans un argument.
Le traitement des expressions encore sans nom a été corrigé et le cas est
conservé dans la régression complète. Le suivi des résultats/contraintes a été
adapté avant les suites finales pour distinguer une écriture de contenu de la
création d'une nouvelle valeur scalaire.

## Limites

Les tests et modèles sont bornés, sans preuve générale de sûreté. Les valeurs
allouées mutables en place restent des Int ; les changements de variante enum,
champs mutables, références imbriquées et retours &mut restent hors périmètre.
Les destructeurs utilisateur, collections et graphes transitifs ne sont pas
ajoutés. Les sources ne sont pas déplaçables et l'exécution est synchrone.
Le C ne sert pas à faire appliquer les let immutables : le vérificateur les
contrôle avant émission, et modifier le C contourne ses garanties.
L'inférence, le vérificateur et le backend restent dans la base de confiance.
ASan n'est pas relancé, vu l'échec antérieur de cet hôte même avec un programme
C vide ; voir [SAFETY.md](SAFETY.md). Les programmes CLI ne deviennent pas
instrumentés par la seule variable CRUST_SANITIZE. Les configurations d'une
même famille C ne remplacent pas un compilateur indépendant.

Les rapports bruts antérieurs gardent leurs versions de syntaxe et empreintes.
Les exemples documentaires ont été migrés ; ces modifications ne sont pas
présentées comme des réexécutions des anciennes mesures. L'audit rapide de
migration qui compilait puis sautait les exécutions C n'est pas une suite verte :
ses sauts empêchaient de compléter certains compteurs de modèles. Les suites
finales exécutent les méthodes entières.
