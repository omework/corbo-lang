[English](CONDITIONALS.md)

# If / else : chemins qui continuent et nettoyage

Le prototype accepte les instructions `if`, `else` et `else if`. Les conditions
sont `true`, `false` ou une comparaison de deux expressions Int copiables :
`==`, `!=`, `<`, `<=`, `>`, `>=`. Les deux opérandes sont évalués de gauche à
droite avant le choix de la branche. Ce premier sous-ensemble n'ajoute pas de
variables Bool ni d'opérateurs logiques. Les
[expressions `if` allouées](IF_EXPRESSIONS.md) sont désormais prises en charge
avec un receveur et un `<-` final dans chaque branche qui continue.
Les deux branches sont vérifiées, même pour une condition littérale.

## Portée et disponibilité

Chaque paire d'accolades de branche ouvre un scope enfant. La lecture et la
mutation par emprunt peuvent viser le parent ; consommer son allocation exige
le transfert descendant déjà défini :

```rust
let mut data = new(memory) Int(42);
if stop == 1 {
    -> data;
    drop(-> data);
}
print(data); // Refusé : un chemin a consommé l'accès.
```

Un accès n'est disponible après une condition que s'il reste valide sur tous
les chemins qui atteignent cette instruction. Une branche faisant `return`
ne rejoint pas la suite :

```rust
if stop == 1 {
    -> data;
    drop(-> data);
    return;
}
print(data); // Autorisé : seul le chemin conservant data arrive ici.
```

Le compilateur analyse chaque branche depuis le même état d'entrée. Il réunit
ensuite les états des branches qui continuent. Les noms et sources déclarés
dans une branche ne deviennent pas visibles après celle-ci.

La dernière utilisation des emprunts est ajustée au chemin analysé : un emprunt
utilisé seulement dans `else` ne bloque pas une destruction dans `if`. Un
emprunt utilisé après la jonction reste protecteur sur les chemins qui la
rejoignent. Les arguments déjà préparés d'un appel englobant gardent aussi
leurs protections.

## Nettoyage sans double destruction

Une allocation peut être vivante sur certains chemins seulement. Son ancien
accès est alors inutilisable après la jonction, mais le nettoyage doit encore
détruire l'allocation sur les chemins qui l'ont conservée.

Le compilateur utilise un indicateur C par allocation concernée, indépendant
du slot de stockage. Après renommage et simplification :

```c
int live_data = 1;
Cell *data = cell_new(memory, 42, "data");
if (stop == 1) {
    cell_drop(data);
    live_data = 0;
}
/* Nettoyage à la sortie du scope : */
if (live_data) {
    cell_drop(data);
    live_data = 0;
}
```

Cet indicateur ne repose pas sur `Cell.alive` : un pool peut avoir réutilisé le
même slot pour une nouvelle allocation. Le nettoyage de l'ancienne ne doit
alors pas détruire la nouvelle. Un reset collectif à la jonction utilise les
mêmes indicateurs avant de réinitialiser le stockage.

Les indicateurs sont locaux aux fonctions C et leurs adresses sont transmises
par des paramètres internes lorsque le nettoyage passe par une autre fonction.
Le pointeur de nettoyage est remplacé par `NULL` quand l'indicateur vaut zéro,
pour ne pas charger un ancien pointeur de tas après sa libération. L'indicateur
reste transmis séparément et empêche tout appel à `cell_drop` dans ce cas.
Un indicateur local ne s'échappe pas avec une allocation retournée sans
condition : seul un retour d'allocation certainement vivante est autorisé.
Cette implémentation privilégie la vérifiabilité ; elle ne minimise pas encore
le nombre d'indicateurs ni les paramètres internes.

## Retours et effets chez l'appelant

Les retours Void, scalaires et d'allocations sont pris en charge dans les branches,
y compris imbriquées. Les retours d'allocations doivent partager le type déclaré
avec suivi des sources possibles : voir [CONDITIONAL_RETURNS.md](CONDITIONAL_RETURNS.md).
Chaque retour émet d'abord le nettoyage des scopes traversés, en excluant
l'allocation retournée le cas échéant, puis
le `return` C. Si tous les chemins retournent, la suite n'est pas émise.
Une fonction scalaire ou retournant une allocation doit fournir un retour sur
tous les chemins.

Les branches qui retournent sont exclues de la continuation de la fonction,
mais leurs effets sur les allocations de l'appelant restent pris en compte à
la sortie de l'appel. Un reset conditionnel ne peut donc pas laisser l'appelant
accéder à une allocation potentiellement détruite. Sa destruction finale reste
correcte si l'appelant n'en fait plus usage.

## Limites de cette étape

Les retours conditionnels et les expressions `if` avec receveur conservent
les sources possibles des allocations du même type. La réaffectation directe reste limitée au scope actuel :
une branche ne peut réaffecter directement une variable de son parent.
Des transferts aller-retour restent possibles lorsque les chemins qui
continuent admettent un ordre de nettoyage commun. Les allocations déjà mortes
sur un chemin ne contraignent plus son ordre ; une différence de sous-ensemble
vivant ne constitue donc pas à elle seule un conflit. Les ordres des allocations
coexistantes sur chaque chemin doivent être préservés. S'ils imposent un cycle
contradictoire, le prototype produit un diagnostic.

[examples/conditionals.crb](../examples/conditionals.crb) montre les deux
cas de départ et la réutilisation d'une adresse après destruction conditionnelle.
[tests/test_conditionals.py](../tests/test_conditionals.py) vérifie les deux
issues des conditions sur tas, stack et pool, les emprunts, les appels, les
retours imbriqués, les resets, les jonctions successives et les pools d'enum.
Ce périmètre ne comprend pas les boucles ni les destructeurs utilisateur et
ne constitue pas une preuve générale de sûreté.
