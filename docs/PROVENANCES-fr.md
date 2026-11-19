[English](PROVENANCES.md)

# Plusieurs provenances possibles, adresses stables

Une allocation sélectionnée peut provenir de plusieurs sources différentes.
Le compilateur conserve un ensemble fini de sources possibles ; l'exécution
ne contient qu'un objet sélectionné, à son adresse d'origine.

```rust
fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int {
    if n == 0 { return <- a; }
    return <- b;
}
let mut first = Pool<Int>::new(1);
let mut second = Pool<Int>::new(1);
let mut a = new(first) Int(10);
let mut b = new(second) Int(20);
let mut result = choose(-> a, -> b, 1);
print(result);
drop(-> result);
first.reset();
second.reset();
```

Les deux anciens accès sont consommés. Le candidat non retourné est détruit
dans la fonction. Le receveur suit une seule allocation, dont les sources
possibles sont `{first, second}`. L'allocation sélectionnée n'est ni copiée ni
déplacée. Le même type reste requis pour les candidats.

Ce contrat remplace la restriction précédente « même source dans tous les
retours ». Il s'applique aux retours conditionnels de fonctions et aux résultats
alloués des expressions `if`. Les appels imbriqués et les sélections successives
réunissent les ensembles, avec déduplication des sources identiques. Pour un
enum, une source possible désigne son pool public, pas sa stack privée de bras.

## Protection statique des sources

Tant qu'un accès au résultat doit encore servir, chaque source possible doit
rester suffisamment durable et ne peut pas être réinitialisée :

```rust
let mut result = choose(-> a, -> b, n);
first.reset(); // Refusé : result peut dépendre de first.
print(result);
```

La protection couvre les accès directs, les emprunts partagés/mutables, les
réemprunts des appels et les arguments déjà préparés. Un reset exécuté via une
fonction a le même effet qu'un reset direct. Les lectures de l'itération suivante
restent prises en compte. Une source extérieure à l'ensemble peut être reset
sans invalider le résultat.

Une source locale trop courte fait refuser un transfert dès qu'elle figure
parmi les provenances possibles. Le compilateur ne prolonge pas sa durée de vie
et ne déplace pas le résultat dans une autre source.

L'analyse reste conservative : une condition littérale ou la connaissance
humaine de la branche exécutée ne réduit pas automatiquement cet ensemble.
Les raffinements de chemins et les relocalisations sont différés.

## Drop et réaffectation

`drop(-> result)` détruit l'objet sélectionné via sa provenance réelle, conservée
par le runtime dans la cellule depuis son allocation. Il ne nécessite pas
d'allocateur supplémentaire ni d'inspection du programme à l'exécution.

`source.drop(-> result)` exige au contraire que toutes les provenances possibles
soient exactement cette source. Si l'ensemble en contient plusieurs, cette
forme est refusée : le receveur explicite ne peut pas être garanti correct.
Deux candidats provenant du même pool ne créent qu'une provenance et permettent
cette forme de destruction.

La réaffectation évalue complètement le nouveau résultat avant de détruire
l'ancien objet sélectionné, s'il est encore vivant et distinct. Elle conserve
les effets éventuels du membre droit, dont un reset d'une source de l'ancienne
valeur. La garantie de restituer exactement une allocation entrante conserve
son identité, même si elle possède plusieurs provenances possibles.

## Reset après la dernière utilisation

L'absence d'usage futur autorise un reset d'une source possible. Cela ne donne
pas le droit de détruire le résultat s'il appartient en réalité à une autre :

```rust
let mut result = choose(-> a, -> b, n);
print(result); // Dernière utilisation.
first.reset();
// Si result provient de second, son nettoyage reste à effectuer.
second.reset();
```

Le compilateur contrôle les usages et organise les nettoyages avant d'émettre
le C. Pour un résultat possiblement dans plusieurs sources, le nettoyage émis
pour `first.reset()` détruit le résultat uniquement si sa source réelle est
`first`. Le runtime possède déjà cette provenance ; cette sélection du nettoyage
n'est pas une vérification dynamique des emprunts.

Après ce reset, l'accès nommé au résultat devient invalide, puisqu'il peut
avoir été détruit. Le suivi du nettoyage garde uniquement les sources restantes
possibles pour les chemins où l'allocation survit. L'indicateur de nettoyage
vaut zéro sur les chemins détruits et reste armé sur les autres.

Un reset ultérieur de `second` ou la fermeture du scope nettoie le survivant
exactement une fois. Un slot de `first` peut être réutilisé entre-temps : son
ancienne identité et ses anciens accès ne sont pas réactivés. Les resets répétés
et les jonctions réconcilient les états et ensembles des chemins encore vivants.

## C émis et pools d'enum

Les retours restent des retours de `Cell *`. Aucun stockage supplémentaire pour
l'objet ou pour un ensemble runtime de provenances n'est créé.
Un nettoyage partiel ressemble à ceci, après simplification :

```c
if (*live && cell_has_source(result, first)) {
    cell_drop(result);
    *live = 0;
}
source_reset(first);
```

Le test de l'indicateur précède toute lecture de la cellule. Un ancien pointeur
de tas déjà libéré ne peut donc pas être déréférencé par ce contrôle. Les captures
de nettoyage passées aux fonctions continuent de fournir `NULL` quand cet
indicateur est nul, pour éviter aussi de charger le pointeur mort.

Pour un enum, `cell->source` désigne sa stack privée. `cell_has_source` reconnaît
les bras appartenant au pool public demandé. Réinitialiser un autre pool du même
type ne détruit pas ce résultat. Le reset reste précédé des destructeurs dans
l'ordre logique des scopes et des créations/réceptions, indépendamment des bras,
des adresses et de l'ordre physique des slots.

La vérification des fonctions reste spécialisée aux appels dans ce prototype.
Les ensembles de sources concrètes préparent le suivi symbolique décrit dans
[FUNCTION_CONTRACTS.md](FUNCTION_CONTRACTS.md), sans l'implémenter implicitement.

## Exemple et validation

```sh
python3 prototype/crust.py run examples/provenance.crb
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_provenances.py -q
```

Les tests couvrent les couples de tas/stack/pool, les candidats transférés et
créés, les adresses, les sources trop courtes, les appels imbriqués, les
réaffectations, les arguments préparés, les emprunts futurs, les resets directs,
conditionnels et transitifs, les reprises de boucle et les pools d'enum.
Les limites générales de la validation restent dans [SAFETY.md](SAFETY.md).

Validation complète : 395 tests réussis en mode standard et 395 avec
`CRUST_SANITIZE=undefined`, dont les 24 nouveaux tests de provenances et leurs
sous-cas. Les binaires compilés par le harnais sont instrumentés ; les tests
de CLI gardent les options de leur compilation habituelle.
