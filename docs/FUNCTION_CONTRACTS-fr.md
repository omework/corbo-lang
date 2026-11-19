[English](FUNCTION_CONTRACTS.md)

# Contrats mémoire des fonctions : inventaire et proposition

État du 2 novembre 2026 : document de conception. L'inventaire décrit le
compilateur actuel. L'orientation retenue est d'inférer les contrats depuis
les opérations du corps, sans ajouter d'annotation de provenance aux signatures.
Les résumés d'effets de sources et de résultats sont désormais implémentés selon
[EFFECTS.md](EFFECTS.md), [RESULTS.md](RESULTS.md) et
[SOURCE_CONSTRAINTS.md](SOURCE_CONSTRAINTS.md). Un passage du vérificateur sur
les [corps avec des entrées symboliques](FUNCTION_BODIES.md) est également en place.
La [vérification des appels à partir des seuls contrats](MODULAR_CALLS.md) est
désormais en place pour le sous-ensemble actuel ; le backend C reste spécialisé.

## Problème observé

Le compilateur valide les signatures et infère les effets de sources avant les
appels. Le vérificateur mémoire parcourt désormais tous les corps avec des entrées
symboliques, même sans appel réel. Il garde aussi les contrôles lorsqu'un appel
fournit ses allocations et sources réelles, puis produit une version C spécialisée.

Les deux exemples de l'inventaire initial sont désormais refusés même sans
appel : l'analyse des effets détecte le reset via une source en lecture, et
l'analyse des contraintes parcourt les lectures et détecte le nom inconnu.

```rust
fn broken() { print(missing); } // Variable inconnue, même sans appel.
```

```rust
fn clear(memory: &Allocator) { memory.reset(); } // Source non mutable.
```

Les déplacements et emprunts des corps inutilisés sont maintenant contrôlés par
le même vérificateur que ceux des fonctions appelées. Les sous-appels de ce
passage utilisent uniquement leurs contrats, avec vérification des modes, types,
contraintes et compatibilités de stockage des sources fournies. Le backend
parcourt encore les corps pour produire le C et conserver ses contrôles de cohérence.

## Ce que les signatures expriment déjà

| Notation actuelle | Information déjà exprimée |
| --- | --- |
| `n: Int` | Copie d'un Int ; aucun accès au stockage de l'appelant par ce paramètre. |
| `data: &Int` ou `&E` | Emprunt de lecture d'une allocation du type indiqué. |
| `data: &mut Int` ou `&mut E` | Emprunt mutable exclusif ; ne confère pas le droit de remplacer ou transférer l'allocation. |
| `data: -> Int` ou `-> E` | Transfert explicite à l'entrée ; l'ancien accès de l'appelant est consommé. La provenance et le nettoyage accompagnent l'allocation. |
| `memory: &Allocator` ou `&Pool<T>` | Accès en lecture à une source ; pas d'allocation ni de reset par cet accès. |
| `memory: &mut Allocator` ou `&mut Pool<T>` | Autorise les opérations de source, dont allocation, destruction explicite par la source et reset. |
| `-> Int` | Retour d'une valeur copiée. |
| `-> <- Int` ou `-> <- E` | Retour d'une allocation du type déclaré, reçue par l'appelant. |
| Retour omis ou `-> Void` | Aucun résultat. |

Les contrôles déjà généraux comprennent l'existence des types, les modes
explicites, les paramètres dupliqués et les contraintes sur `main`. Les règles
d'exclusivité, d'ordre des arguments et de durée de vie continuent de s'appliquer
à chaque appel ; elles n'exigent pas une nouvelle annotation pour chaque usage.

## Informations du contrat et état actuel

| Information | État actuel et besoin pour la vérification indépendante complète |
| --- | --- |
| Types allouables par chaque source | Exigences désormais inférées dans le résumé ; compatibilité vérifiée après substitution des sources concrètes à l'appel. |
| Source de l'allocation retournée | Alternatives symboliques désormais inférées, substituées avec les sources des arguments et appliquées au résultat concret. |
| Identité du résultat | Restitutions symboliques garanties désormais inférées, vérifiées sur les racines d'origine, et identités nominales conservées aux réceptions. |
| Sources réinitialisées, y compris conditionnellement | Effets désormais inférés une fois par fonction, propagés par substitution dans les sous-appels et utilisés pour les captures C. |
| Relations entre sources de paramètres | `memory.drop(-> data)` exige une provenance unique égale à `memory`. Une sélection de retours conserve l'union des sources possibles. Ces obligations sont désormais inférées et substituées aux appels. |
| Éventuelles sources incompatibles | Si une fonction reset une source puis lit un emprunt, elle doit prouver que cette source n'est pas celle de l'emprunt, ou refuser la combinaison ; l'ordre des opérations permet désormais d'inférer la distinction requise, puis le contrôle concret la vérifie. |
| Chemins de terminaison | `may_return` est inféré pour l'analyse des effets ; types retournés et nettoyages sont contrôlés avec des entrées symboliques puis aux appels réels. |

La mutation de la valeur d'un `&mut Int` ne détruit pas son allocation. Il faut
la distinguer d'une invalidation par reset. Consommer un argument transféré ne
signifie pas réinitialiser toute sa source, et n'impose pas de passer séparément
un allocateur pour son nettoyage.

## Contenu minimal proposé d'un contrat

Le contrat représente des propriétés de tous les appels admis, avec des
identités et sources symboliques plutôt que les objets d'un appel particulier.
Il doit contenir :

1. Les types et modes déjà écrits dans la signature.
2. Les types que chaque source doit pouvoir allouer, indépendamment du choix
   concret du backend (tas, stack, pool compatible).
3. Les relations requises entre les sources des paramètres : égalité ou
   distinction, quand le corps en dépend.
4. La provenance du résultat alloué, et séparément la garantie éventuelle de
   restituer exactement une allocation transférée en entrée.
5. Les effets d'invalidation sur les sources : aucune réinitialisation, ou
   réinitialisation possible de telle source. Un effet possible doit être
   conservé même si un chemin particulier ne l'exécute pas.
6. Les informations nécessaires sur les retours et chemins sans continuation.

La représentation précise des résultats peut être plus riche que leur syntaxe
publique : résultat neuf dans une source, restitution d'une identité entrante,
ou sélection entre candidats. Une garantie d'identité ne doit être annoncée
que si tous les chemins de retour concernés la respectent.

Une annotation de provenance décrit une dépendance de stockage. Elle ne doit
pas maintenir un emprunt mutable de l'allocateur pendant toute la vie de l'objet
retourné : cela contredirait la règle A4 de réutilisation de la source.

### Exemple : construire une allocation

```rust
fn make(memory: &mut Allocator) -> <- Int {
    let mut data = new(memory) Int(42);
    return <- data;
}
```

Le contrat doit établir : résultat Int vivant, source `memory`, allocation
créée par cette invocation, aucune réinitialisation de la source. Le passage
mutable ne suffit pas à lui seul pour établir la dernière propriété.

Le contrat doit aussi imposer que `memory` puisse allouer Int. Vérification
reproduite : cette signature est actuellement acceptée avec `allocator()` et
`Pool<Int>::new(1)`, mais son corps est refusé avec `Pool<E>::new(1)`. Le type générique
`Allocator` ne fournit pas encore à lui seul cette garantie. Une fonction qui
alloue uniquement un temporaire Int puis le détruit a la même exigence, même
sans retour d'allocation. La vérification indépendante doit donc conserver
cette exigence comme condition de compatibilité à l'appel.

Il s'agit du type de stockage accepté, pas d'une preuve de capacité suffisante :
l'arrêt runtime sur épuisement reste le choix actuel.

### Exemple : restituer une allocation reçue

```rust
fn forward(mut data: -> Int, n: Int) -> <- Int {
    if n == 0 { return <- data; }
    return <- data;
}
```

Le contrat doit établir : ancien accès consommé à l'entrée, même allocation
restituée sur tous les retours, même source et même adresse. Cela doit rester
possible sans recevoir un paramètre d'allocateur supplémentaire. L'audit récent
a montré pourquoi remplacer systématiquement cette identité par une identité
inconnue ferait perdre des transferts actuellement valides.

### Exemple : choisir entre deux allocations

```rust
fn choose(mut a: -> Int, mut b: -> Int, n: Int) -> <- Int {
    if n == 0 { return <- a; }
    return <- b;
}
```

Les deux anciens accès sont consommés. Une seule allocation est rendue et
l'autre est nettoyée. Le prototype conserve désormais l'union des sources
possibles ; le contrat inféré devra conserver cette union. Il ne peut pas promettre
que le résultat est toujours `a`, ni toujours `b`.

### Exemple : réinitialiser une source

```rust
fn clear(memory: &mut Allocator) {
    memory.reset();
}
```

L'effet concerne les allocations de cette source chez l'appelant, même si elles
ne sont pas des arguments de `clear`. La vérification de l'appel doit donc
contrôler les usages futurs et invalider les accès concernés. Un wrapper qui
appelle `clear` doit porter le même effet.

Une réinitialisation conditionnelle reste un effet possible. À son retour, les
anciens accès ne peuvent pas être utilisés sans preuve suffisante, et le
nettoyage C doit distinguer les chemins où les objets ont été détruits.

### Exemple : relation entre source et emprunt

```rust
fn clear_then_read(memory: &mut Allocator, data: &Int) -> Int {
    memory.reset();
    return *data;
}
```

La fonction peut fonctionner quand `data` dépend d'une autre source. Elle ne
peut pas accepter le cas où `data` vient de `memory`. Une vérification modulaire
ne doit pas supposer implicitement que deux paramètres ont des sources
différentes ; elle doit disposer de la relation requise, ou refuser ce corps.

## Orientation retenue : contrats inférés depuis le corps

`new`, les emprunts, transferts, retours et `reset` sont des opérations reconnues
par le compilateur. Elles alimentent son suivi des allocations et des sources.
La provenance du résultat doit être déduite de ce suivi ; la notation proposée
initialement `from memory` n'est pas retenue pour les fonctions dont le corps
est disponible.

```rust
fn make(memory: &mut Allocator) -> <- Int {
    let mut data = new(memory) Int(42);
    return <- data;
}
```

Lors de la vérification indépendante, `memory` est une source symbolique. Le
résultat porte cette provenance. À l'appel, cette source symbolique est
substituée par la source réelle passée. Ce lien n'est pas un emprunt mutable
de la source maintenu pendant toute la vie du résultat.

Le même principe permet de préparer les autres informations du contrat :

- Une identité d'entrée rendue sur tous les retours est conservée.
- Des candidats distincts restent distincts ; les relations entre leurs sources
  nécessaires aux règles actuelles sont des contraintes à vérifier à l'appel.
- Les opérations `new` imposent les types qu'une source doit accepter, y compris
  pour les temporaires qui ne sont pas retournés.
- Les opérations `reset` produisent des effets d'invalidation, à propager à
  travers les sous-appels et à vérifier face aux usages futurs de l'appelant.

L'intention reste dans les opérations explicites du corps. L'inférence des
contraintes d'égalité et de distinction des sources est désormais implémentée
et testée ; les appels utilisent désormais ces contrats sans parcourir les corps.
Une déclaration
sans corps, notamment externe, nécessiterait un contrat fourni autrement ;
les appels C externes restent hors du prototype.

## Cas suivant : sélectionner entre deux allocations reçues

Pour `choose(a: -> Int, b: -> Int, n: Int) -> <- Int`, retournant `a` ou `b`
selon une branche, le suivi conserve deux identités candidates et l'union de
leurs sources possibles. La contrainte d'égalité des sources proposée initialement
est abandonnée. Aucun paramètre d'allocateur supplémentaire n'est nécessaire.

Les deux anciens accès sont consommés à l'entrée. Le résultat ne promet pas
l'identité de `a` ni celle de `b`. Le candidat non retourné est détruit sur le
chemin exécuté. Chaque source possible reste protégée contre une invalidation
incompatible avec les usages futurs du résultat. Cette union est désormais
implémentée pour les sources concrètes et les résumés symboliques des résultats ;
la vérification des appels par contrats est également en place. Voir
[PROVENANCES.md](PROVENANCES.md) et [MODULAR_CALLS.md](MODULAR_CALLS.md).

## Procédé d'implémentation proposé

1. Représenter les contrats séparément des objets concrets et de l'émission C.
2. Pour le graphe de fonctions non récursif actuel, vérifier les corps, y
   compris inutilisés, avec des paramètres symboliques et les contrats des
   sous-appels. Refuser les contrats non respectés.
3. Aux appels, substituer les allocations/sources réelles, vérifier les
   relations, types allouables et emprunts, puis appliquer les effets et la réception du résultat.
4. Comparer ce nouveau contrôle à l'analyse spécialisée actuelle sur les tests
   acceptés/refusés et les traces C. Toute différence doit être examinée.
5. Conserver d'abord le backend C spécialisé. Ne supprimer cette spécialisation
   qu'après avoir défini un mécanisme runtime équivalent pour les effets.

Vérifier une fonction indépendamment n'exige pas immédiatement une unique
fonction C partagée par tous les appels. Le backend actuel passe des pointeurs
et indicateurs de nettoyage des allocations de l'appelant à un callee pouvant
reset une source. Une fonction C générique ne peut pas simplement appeler le
reset bas niveau : il attend que les destructeurs aient déjà été exécutés.

La liste physique du pool ne donne pas à elle seule l'ordre logique par scopes
et réceptions imposé au reset. Un backend générique nécessiterait un protocole
de nettoyage préservant cet ordre, ou une autre représentation explicitement
définie et vérifiée. Cette difficulté ne doit pas retarder la séparation du
vérificateur et de ses contrats.

## Validation à prévoir

- Erreurs de corps détectées même sans appel.
- Même contrat vérifié pour des sources réelles de types/capacités différents
  compatibles, sans réinterpréter ses garanties à chaque appel.
- Provenance du résultat cohérente sur tous les retours ; source locale refusée.
- Identité préservée pour les restitutions garanties et aucun ancien accès
  réactivé lors d'une réception explicite.
- Relations de sources identiques/distinctes vérifiées aux appels.
- Exigences de types allouables vérifiées sans réanalyser le corps : Int admis
  sur tas/stack/pool Int compatibles et refusé sur un pool d’un autre type.
- Effets de reset directs, conditionnels et transitifs ; protection des emprunts
  et arguments préparés ; destruction et nettoyage exactement une fois.
- Conservation des traces et de l'ordre de destruction avec le backend C.

Les [retours directs &Int](DIRECT_BORROW_RETURNS.md) sont désormais implémentés
avec `reference_targets` et vérification enfant → parent. Les [retours &mut Int](MUTABLE_BORROW_RETURNS.md) conservent désormais le mode
exclusif et les mêmes identités de cibles. La récursion, les graphes transitifs
et la compilation séparée restent différés.
Les champs immuables &Int ont un sous-ensemble dédié dans
[REFERENCE_FIELDS.md](REFERENCE_FIELDS.md) ; leur provenance dans un paramètre
est conservée dans les contrats. Les [retours alloués de porteurs &Int](BORROWED_RETURNS.md)
sont également disponibles pour des cibles déjà durables dans le parent.
