[English](SOURCE_CONSTRAINTS.md)

# Contraintes inférées entre sources

**Actualisation des emprunts mutables :** [MA1–MA6](MUTABLE_ACCESS-fr.md)
remplace l’exclusivité déduite du seul `&mut`. Les exemples et verdicts d’exclusion
rapportés dans les anciens cycles ci-dessous sont historiques ; ils ne définissent
pas la compatibilité actuelle des accès. Permissions, validité, synchronisation
et fins de branche se vérifient séparément.


Le compilateur déduit les relations entre les sources des paramètres depuis les
opérations du corps, puis les substitue aux appels. Aucune annotation n'est
ajoutée aux signatures. Les contraintes complètent les résumés d'effets et de
résultats ; le vérificateur mémoire complet reste également exécuté aux appels.

## Lire avant ou après un reset

```rust
fn clear_then_read(memory: &mut Allocator, data: &Int) -> Int {
    memory.reset();
    return *data;
}
```

Le contrat contient `source(data) != memory`. Une lecture après le reset exige
que l'allocation ne puisse pas dépendre de la source réinitialisée. À l'appel,
la totalité des provenances possibles de `data` doit être distincte de `memory`.
Une seule source possible commune suffit à faire refuser l'appel.

```rust
fn read_then_clear(memory: &mut Allocator, data: &Int) -> Int {
    let mut value = *data;
    memory.reset();
    return value;
}
```

Le corps n'impose pas cette distinction : l'entier est copié avant le reset.
Il peut fonctionner avec `data` dans `memory`, si aucun usage ultérieur de cette
allocation ou d'un emprunt ne subsiste chez l'appelant. Une utilisation future
chez un wrapper fait apparaître une contrainte supplémentaire dans son résumé ;
les contrôles concrets des usages futurs restent aussi actifs.

## Égalité pour une destruction avec source explicite

```rust
fn consume(memory: &mut Allocator, mut data: -> Int) {
    memory.drop(-> data);
}
```

Le corps impose `source(data) == memory`. Toutes les provenances possibles du
paramètre doivent être égales à cette source. Un résultat provenant de deux
pools distincts ne satisfait pas cette exigence.

`drop(-> data)` utilise directement la provenance de l'objet et n'impose pas
cette égalité avec un paramètre d'allocateur. Ni cette destruction individuelle,
ni le nettoyage automatique ne sont assimilés à un reset collectif.

## Analyse symbolique ordonnée

[constraints.py](../constraints.py) distingue :

- une source reçue en paramètre, `source_parameter` ;
- la source d'une allocation reçue en paramètre, `allocation_parameter` ;
- une source locale créée dans le corps.

Les valeurs allouées et emprunts sont suivis par des actifs symboliques. Chaque
actif conserve les resets possibles survenus depuis sa création ou sa réception.
Une lecture, mutation, création d'emprunt, transmission ou retour exige qu'il
soit encore utilisable : elle produit les distinctions de sources nécessaires.
Une allocation créée après un reset commence avec un historique vide. Une copie
scalaire ne conserve pas la dépendance à l'allocation dont elle a lu la valeur.

Les branches partent d'états séparés. Leurs historiques ne se rejoignent que
sur les chemins qui continuent. Un reset dans une branche quittant la fonction
ne rend donc pas automatiquement une lecture de l'autre branche incompatible.
Un reset conditionnel précédant une lecture commune impose en revanche une
contrainte, même lorsque la condition est littérale : l'analyse reste conservative.

Les boucles réunissent les états de reprise jusqu'à stabilisation. Lire un
paramètre puis reset une source avant `continue` protège aussi la lecture du
passage suivant. Un chemin qui fait `break` ne reprend pas cette lecture.
Les effets du test de `while` sont pris en compte, ainsi que le chemin de sortie
avant la première exécution du corps et les usages après la boucle.

Les actifs locaux sont retirés lors de la fermeture des scopes. Le nettoyage
automatique ne crée pas une fausse obligation de survie après reset : le runtime
et le code généré nettoient seulement les objets encore vivants.

## Sous-appels et réception des résultats

Les contraintes d'un sous-appel sont substituées par les sources et valeurs du
corps appelant, y compris lorsque les paramètres sont réordonnés. Une sélection
de plusieurs provenances produit les obligations pour chacune des alternatives.
Les effets de reset du sous-appel alimentent ensuite les historiques de l'appelant.

Un résultat alloué est reçu vivant sur chaque chemin qui retourne normalement.
Son historique de réception est donc rétabli sans lui attribuer aveuglément
tous les resets possibles du sous-appel. Cela préserve les cas où un chemin
retourne l'entrée sans reset et un autre réinitialise une source puis retourne
un objet différent. Les contraintes nécessaires à la survie de l'entrée sont
vérifiées dans le contrat appelé. Les anciens accès consommés ne sont pas
réactivés : le contrôle des déplacements reste assuré par le vérificateur complet.

Les arguments sont évalués de gauche à droite. Une allocation ou un emprunt
préparé doit survivre jusqu'au début de l'appel, même si le paramètre est inutilisé.
Un reset dans un argument suivant impose donc une distinction de source. Une
valeur Int déjà copiée n'a pas cette obligation. Les emprunts de sources déjà
préparés restent exclusifs selon les règles d'arguments existantes.

## Simplifications et refus

L'égalité d'un symbole avec lui-même est vraie ; sa distinction avec lui-même
est impossible. Une source locale fraîche est distincte des sources d'entrée
et des autres créations locales. Les règles d'exclusivité déjà imposées par les
modes de paramètres de sources permettent aussi de reconnaître certaines
sources comme distinctes.

Une obligation impossible fait refuser le corps, même sans appel. Cela détecte
notamment une allocation créée dans `memory`, suivie de `memory.reset()` puis
d'une lecture de cette allocation. Des égalités et distinctions directement
opposées sont également refusées. Le solveur n'est pas une preuve générale de
satisfiabilité de toutes les relations de types et de sources.

Les contraintes exportées ne contiennent que des paramètres, sans identités de
sources runtime. Aux appels concrets, le compilateur compare les identités des
sources possibles avant de spécialiser et d'émettre le corps. Il n'ajoute aucun
contrôle dynamique de relation ni déplacement d'objet.

## Inspection

```sh
python3 prototype/crust.py effects examples/source_constraints.crb
python3 prototype/crust.py run examples/source_constraints.crb
```

La commande `effects` ajoute `constraints` aux effets et résultats. Exemple :

```json
{
  "relation": "distinct",
  "left": {"kind": "allocation_parameter", "parameter": "data"},
  "right": {"kind": "source_parameter", "parameter": "memory"}
}
```

Le contrat de `read_then_clear` contient une liste vide ; celui de `consume`
contient l'égalité des mêmes catégories de symboles.

## Portée et validation

Cette analyse ne remplace pas la vérification des déplacements, des alias
mutables, des types ou de tous les usages après destruction. Les erreurs de
noms rencontrées pendant le parcours sont maintenant refusées même sans appel,
et un [passage du vérificateur mémoire](FUNCTION_BODIES.md) contrôle désormais
aussi chaque corps avec des entrées symboliques, même sans appel. La récursion,
les graphes transitifs et les retours autres que &Int restent hors du sous-ensemble.
Les [retours directs &Int](DIRECT_BORROW_RETURNS.md) conservent désormais
l'historique des cibles d'origine à travers les contrats, sans naissance d'un
nouvel objet à la réception de la référence. Les champs immuables &Int ont désormais des symboles de source
`allocation_field_parameter`, substitués aux appels sans corps ; voir
[REFERENCE_FIELDS.md](REFERENCE_FIELDS.md). Les règles et restrictions de transfert et de portée
restent applicables à l'analyse des états de boucle.

[tests/test_constraints.py](../tests/test_constraints.py) couvre l'ordre lecture/reset,
les sources égales/distinctes et multiples, les substitutions transitives, les
sources locales, les branches, boucles et `continue`, les résultats garantis vivants,
les arguments préparés, les copies scalaires, les pools d'enum et la commande JSON.
Les limites générales d'instrumentation sont décrites dans [SAFETY.md](SAFETY.md).

Validation : 467 tests réussis dans la suite complète standard et 467 avec
`CRUST_SANITIZE=undefined`, y compris les 27 nouveaux tests de contraintes.
