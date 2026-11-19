[English](RESULTS.md)

# Résumés symboliques des résultats alloués

Le compilateur infère les origines des résultats alloués depuis le corps des
fonctions, sans appel concret ni annotation dans la signature. Les adresses
restent stables : les informations nouvelles appartiennent à l'analyse Python,
pas à la représentation runtime des objets.

## Trois cas

| Corps de fonction | Résumé du résultat |
| --- | --- |
| Crée et retourne une allocation via `new(memory)` | Allocation neuve dans la source du paramètre `memory`. |
| Retourne exactement son paramètre transféré `data` | Même allocation que `data`, avec son identité et sa provenance. |
| Choisit entre `a`, `b` ou une allocation créée | Ensemble des alternatives, en distinguant identités entrantes et allocations neuves. |

```rust
fn make(memory: &mut Allocator) -> <- Int {
    let mut data = new(memory) Int(42);
    return <- data;
}

fn forward(mut data: -> Int, n: Int) -> <- Int {
    let mut result = if n == 0 {
        -> data;
        <- data
    } else {
        -> data;
        <- data
    };
    return <- result;
}

fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int {
    if n == 0 { return <- a; }
    return <- b;
}
```

`make` produit une allocation neuve ; `forward` restitue la même allocation sur
tous les retours ; `choose` ne promet pas laquelle de ses entrées sera rendue.
Les sources de `a` et `b` peuvent être différentes.

La fraîcheur est relative à l'entrée de la fonction. Un wrapper qui crée un
objet puis le passe à `forward` rend donc un objet neuf du point de vue de son
propre appelant. Un wrapper qui transmet son entrée conserve cette identité.
Deux sites qui créent des objets dans la même source peuvent être regroupés
sous « neuf dans cette source » : cela ne promet ni une identité commune entre
les objets ni un nombre d'allocations.

## Analyse indépendante

[results.py](../results.py) suit des valeurs nominales et des sources symboliques :

- les allocations reçues sont désignées par l'indice de leur paramètre ;
- les allocations neuves sont décrites par la source symbolique qui les fournit ;
- les déplacements, réaffectations et réceptions transmettent les alternatives ;
- les branches qui continuent réunissent leurs résultats ; les retours explicites
  alimentent le résumé de la fonction, même depuis des blocs ou arguments ;
- les boucles parcourent les retours du corps et conservent les sorties possibles ;
- les sous-appels substituent leurs paramètres par les valeurs et sources du
  contexte appelant, en réutilisant leurs résumés.

Les appels sans retour normal, d'après le résumé d'effets, ne fournissent pas
un résultat fictif. Les signatures scalaires et Void sont exposées avec leur
mode/type, sans alternatives d'allocations. Cette étape ne les vérifie pas
entièrement indépendamment des appels.

Pour les fonctions retournant une allocation, les retours normaux doivent
fournir le type alloué déclaré. Une source locale figurant dans un résultat
normal fait refuser le contrat, y compris sans appel de cette fonction. Les
emprunts retournés restent hors du sous-ensemble. Le retour explicite d'une
allocation garde l'exigence de `<-` ; aucun nouveau raccourci syntaxique n'est
introduit.

## Substitution et contrôle aux appels

Le compilateur résout le résumé avec les arguments réels avant de spécialiser
le corps. La provenance attendue est l'union :

- des sources des allocations entrantes pouvant être rendues ;
- des sources réelles des paramètres dans lesquels un objet neuf peut être créé.

Les résultats de la spécialisation doivent respecter ce contrat. Le compilateur
conserve pour cela une trace des allocations physiques d'origine à travers les
descripteurs de sélection. Les créations par `new` ont une racine symbolique dans leur contexte d'analyse,
avec une source enregistrée ; une sélection réunit ces racines sans en créer une
nouvelle allocation physique. Ce suivi ne repose pas sur l'égalité des pointeurs.

Le contrôle vérifie séparément :

1. que les sources possibles du résultat sont annoncées ;
2. qu'une identité présente à l'entrée est autorisée comme entrée restituée ;
3. qu'une racine neuve provient d'une source autorisée pour les objets neufs ;
4. qu'une restitution garantie d'un paramètre conserve exactement ses racines.

La troisième vérification ne se réduit pas à comparer l'union des sources :
une source autorisée pour une entrée ne peut pas masquer un objet neuf créé
au mauvais endroit. Une incohérence produit un refus avant compilation du C.

Les provenances instanciées sont utilisées pour le résultat chez l'appelant.
Chaque source possible reste protégée contre un reset incompatible avec les
usages futurs, conformément à [PROVENANCES.md](PROVENANCES.md).

## Restitution d'identité et nettoyage

Une expression `if` interne peut représenter le même objet avec un nouveau
descripteur de sélection. Si le résumé garantit la restitution d'une entrée et
que le contrôle des origines la confirme, le compilateur conserve l'identité
nominale d'entrée chez le receveur. Cela préserve les correspondances d'import
et les marquages de transfert déjà établis, même à travers plusieurs wrappers.

Les anciens noms consommés restent invalides. Le receveur reçoit l'accès ; dans
un bloc ordinaire, les règles existantes de retour d'un import restaurent le
seul accès parent prévu. La réception reste une nouvelle entrée dans l'ordre de
nettoyage. Les indicateurs ne réutilisent pas de variable C d'une fonction
terminée, et l'objet retourné est nettoyé exactement une fois.

Un déplacement dans un pool n'est pas introduit. Si une fonction détruit son
entrée puis crée un objet dans le slot libéré, le nouveau résultat est **neuf**,
même lorsque son adresse est identique. Il ne peut pas restaurer l'ancien accès
ou satisfaire une garantie de restitution de cette entrée.

## Inspection

```sh
python3 prototype/crust.py effects examples/results.crb
python3 prototype/crust.py run examples/results.crb
```

La commande `effects` conserve les informations d'effets et ajoute un champ
`result` pour chaque fonction. Exemple pour `forward` :

```json
{
  "mode": "owned",
  "type": "Int",
  "alternatives": [{"kind": "parameter", "parameter": "data"}]
}
```

Pour `make`, l'alternative est :

```json
{"kind": "fresh", "source": {"kind": "parameter", "parameter": "memory"}}
```

Pour `choose`, les alternatives désignent `a` et `b`. Il n'y a pas d'identifiant
d'allocation runtime ni d'adresse concrète dans ces résumés.

## Limites et validation

Les résultats d'objets à champs &Int décrivent désormais les identités des
cibles empruntées dans `borrowed_fields` et les variantes construites dans
`fresh_variants`. Ces métadonnées sont substituées à travers les appels sans
ouvrir leurs corps. La [vérification enfant → parent](BORROWED_RETURNS.md)
refuse les cibles trop courtes selon D1, sans promotion automatique autorisée.
Le retour direct d'un emprunt reste hors du sous-ensemble.

Le backend C reste spécialisé aux appels réels. Un
[passage sur les corps](FUNCTION_BODIES.md) exécute aussi le vérificateur mémoire
avec des entrées symboliques, même sans appel.
L'analyse nominale des résultats n'est pas un vérificateur complet des déplacements,
permissions, références ou usages après destruction ; ces contrôles sont assurés
par le passage sur les corps et maintenus aux appels réels. Les [contraintes entre sources](SOURCE_CONSTRAINTS.md) sont désormais inférées
et vérifiées aux appels. Les [appels par contrats opaques](MODULAR_CALLS.md)
sont également vérifiés sans parcourir les corps. Les [retours directs &Int](DIRECT_BORROW_RETURNS.md)
étendent désormais le résumé avec `reference_targets`, sans candidat alloué ni source neuve.
Les analyses de contraintes conservent l'historique des cibles existantes, sans
les traiter comme des allocations reçues neuves après un reset.

[tests/test_results.py](../tests/test_results.py) couvre les résumés sans appels,
les substitutions, les sélections et sources multiples, les réaffectations, les
retours dans les boucles et arguments, les restitutions à travers un `if`, les
imports et nettoyages, les enums, les resets et les slots réutilisés. Des contrats
intentionnellement faux vérifient le refus d'une identité ou provenance incorrecte
avant émission d'un programme exécutable.

Validation finale : 440 tests réussis en mode standard et 440 avec
`CRUST_SANITIZE=undefined`, dont 25 nouveaux tests de résultats et leurs sous-cas.
Les limites d'instrumentation des binaires de tests restent décrites dans
[SAFETY.md](SAFETY.md). Un contrôle supplémentaire a comparé 18 résumés générés
à un modèle indépendant, avec permutations de paramètres et six niveaux de
fonctions, puis exécuté six programmes C correspondants ; les résultats et
comptes de destruction concordaient.
