[English](STRUCTURES_METHODS.md)

# Corbo — structures, construction et méthodes

Les permissions des références suivent [MA1–MA6](MUTABLE_ACCESS-fr.md).
Les anciennes descriptions d’exclusion ci-dessous ne réintroduisent pas
l’unicité de `&mut` ; les effets invalidants restent soumis aux dépendances.


Décisions validées dans la discussion, consignées le 5 novembre 2026.

Ce document complète [LANGUAGE_RULES.md](LANGUAGE_RULES.md). Il consigne la
conception retenue. La consignation initiale était documentaire ; les cycles
d’implémentation et la matrice indiquent depuis quels comportements ont été
exercés. Les exemples normatifs ne constituent pas à eux seuls des preuves.

Le [cycle des fondamentaux](cycles/FOUNDATIONS_CYCLE.md) a depuis ajouté le cas
`Pool<Int>.new()`, son défaut `0` et la vérification de l'annotation
sur une liaison d'allocation. Les structures plates à champs Int et
références Int nommées peuvent maintenant être construites dans un pool.
Les champs structure omis sont initialisés dans le même slot lorsque
leurs champs terminaux ont tous un défaut.
Les littéraux contenus explicitement sont également raccordés dans ce slot,
en sync et async, avec conservation de l'ordre écrit :
[cycle des constructeurs imbriqués](cycles/INLINE_STRUCTURE_CONSTRUCTION_CYCLE.md).
Les chemins vers des champs Int sont lisibles et modifiables en place.
Les emprunts de champs Int directs ou imbriqués distinguent les chemins.
Les contrats de retour conservent les chemins des emprunts de champs Int,
y compris dans les tableaux fixes retournés. Les emprunts de sous-structures
à champs terminaux Int et références sont raccordés pour les appels et retours synchrones,
y compris les références vers des structures typées :
[cycle des vues avec références typées](cycles/INLINE_TYPED_VIEWS_CYCLE.md). Leurs copies, lorsque les champs sont copiables, vers la
data stack locale ou un pool explicite sont raccordées dans le
[cycle de copie des vues](cycles/INLINE_VIEW_COPY_CYCLE.md). Le [stockage dans des champs références](cycles/STORED_INLINE_VIEWS_CYCLE.md) est
raccordé pour les parcours synchrones testés : construction, copie, remplacement,
retour et match. Les [résultats mêlant référence entière et intérieure](cycles/MIXED_INLINE_RESULTS_CYCLE.md)
sont également raccordés aux sorties synchrones testées. Les
[captures async de vues](cycles/ASYNC_INLINE_VIEWS_CYCLE.md) couvrent maintenant les
champs Int, références Int et descendants propriétaires déjà représentés,
avec suspension, appels, copies et retours de champs empruntés. Les [porteurs de références nominales stockées](cycles/ASYNC_STORED_VIEWS_CYCLE.md)
sont également raccordés aux captures, réemprunts, remplacements, constructions,
copies et retours de porteurs exercés. Les [retours async directs de références
nominales](cycles/ASYNC_NOMINAL_RESULTS_CYCLE.md) traversent await, join, Select, les
relais et les handles publics testés. Les [matchs d’enums à champs références
nominales](cycles/ASYNC_ENUM_NOMINAL_CYCLE.md) couvrent les projections, réemprunts et
retours ciblés, avec nettoyage du porteur. Les graphes récursifs restent ouverts.
Les [vues à champs propriétaires](cycles/INLINE_OWNED_VIEWS_CYCLE.md) permettent aussi
les accès, réemprunts et remplacements synchrones via la racine, y compris les
vues retournées par fonction. Les cas exercés portent sur A<Int> et A<Leaf>.
La copie implicite depuis un pool injecté reste également partielle.
Les méthodes sur des receveurs nommés utilisent les contrats de fonctions.
La copie de structures locales sur la data stack implicite est raccordée pour
les champs déjà pris en charge, avec placement des résultats chez le receveur.
Les preuves et limites figurent dans [STORAGE_DESIGN_CYCLE.md](cycles/STORAGE_DESIGN_CYCLE.md).

## 1. Structures et construction dans un pool

**ST1 — Structure complète et champs contenus.** Une structure déclare des
champs nommés et typés. Une instance utilisable est entièrement initialisée.
Les champs contenus directement, y compris les structures imbriquées, font
partie de son allocation ; ils n'exigent pas chacun un slot indépendant.
Une référence stockée reste une référence vers sa cible, pas une allocation
implicite de cette cible.

**ST2 — Pool.new et annotation de type.** `Pool<T>` est un builtin dont la méthode
`new` construit une instance de `T` directement dans un slot du pool et restitue
l'allocation. Le compilateur lui associe sa provenance. Les deux écritures sont
autorisées et équivalentes :

```rust
let point = points.new();
let point: Point = points.new();
```

La seconde effectue une vérification de type, sans conversion ni allocation
supplémentaire. Un type incompatible avec celui du pool est refusé. La source
reste explicite dans le receveur ; l'appel exige un slot disponible et les droits
d'accès nécessaires au pool. Cette notation ne supprime pas à elle seule les
anciennes constructions `new(source)` hors du périmètre discuté.

**ST3 — Défauts déduits.** Le défaut d'`Int` est `0`. Une structure possède une
construction par défaut lorsque tous ses champs en possèdent une, récursivement.
Une référence n'a aucun défaut implicite : ni cible inventée, ni référence nulle.
Un champ `A<T>` exige un initialiseur explicite qui fournit une allocation.
Le défaut éventuel de `T` ne détermine aucun pool source.
L'absence de défaut n'interdit pas le type ou son pool ; elle interdit sa
construction sans initialisation suffisante.

Les défauts personnalisés ne font pas partie du prototype retenu. La déclaration
`x: Int = 10` a été rejetée ; une éventuelle notation par tags est reportée.
Aucune fonction personnalisée `Type::default()` n'a été validée.

**ST4 — Initialisation explicite nommée.** `pool.new(champ: expression, ...)`
initialise directement les champs nommés dans le slot. Un champ omis reçoit son
défaut s'il existe ; sinon la construction est refusée. Un champ inconnu,
répété ou fourni avec un type incompatible est refusé. Les expressions fournies
sont évaluées de gauche à droite dans l'ordre écrit. Les références et transferts
introduits par un argument restent protégés pendant les arguments suivants,
selon les règles déjà retenues pour les appels.

Pour un receveur `Pool<T>` dont `T` est une structure, `pool.new({ champ:
expression, ... })` applique les mêmes règles. Le type du pool donne le type
de la structure, comme si son nom figurait devant les accolades. Les formes
`pool.new()` et `pool.new({})` sont équivalentes : chaque champ est omis et
doit donc avoir un défaut.

```rust
struct Boite { nombre: A<i64> }

fn main() {
    let mut nombres = Pool<i64>::new(1);
    let mut boites = Pool<Boite>::new(1);
    let boite: A<Boite> = boites.new({ nombre: nombres.new(7) });
    drop(boite);
}
```

Cette forme est retenue pour le builtin `Pool.new` ; elle ne décide pas d'une
syntaxe générale d'arguments nommés dans toutes les fonctions. L'instance
accessible au programme ne présente jamais de champ non initialisé.

## 2. Champs, emprunts et contrats

**ST5 — Mutation en place.** Écrire un champ exige un accès mutable à la
structure. Pour un champ `Int`, `point.x = 30` modifie le contenu sans remplacer
l'allocation de `point`, déplacer ses champs ni consommer un autre slot. Les
restrictions d'emprunt restent applicables.

**ST6 — Réservation par champ.** Deux champs `Int` distincts peuvent être
empruntés mutablement en même temps, puisque leurs stockages sont prouvés
distincts. Chaque réservation se termine au dernier usage de son emprunt. Un
accès incompatible au même champ reste refusé. Déplacer ou détruire la structure
entière exige la fin des emprunts qui le bloquent.

**ST7 — Chemins imbriqués.** Le suivi est récursif : `segment.debut.x` et
`segment.fin.x` sont distincts ; un emprunt de `segment.debut` englobe en revanche
tous les champs de `debut`. Une réservation empêche les accès incompatibles au
chemin ciblé et aux chemins qui l'englobent, pas aux chemins prouvés distincts.
Pour des champs références, la distinction physique des champs ne prouve pas
à elle seule la distinction des cibles pointées.

**ST8 — Contrat du champ retourné.** Une fonction retournant un emprunt vers un
champ direct conserve ce chemin dans son contrat. Après l'appel, seuls les
champs pouvant être ciblés restent réservés ; les champs prouvés distincts sont
accessibles. La structure reste vivante tant que le résultat dépend de son
stockage. Si plusieurs champs peuvent être retournés, toutes les possibilités
pertinentes restent suivies. Les appels exploitent le contrat sans reparcourir
le corps appelé.

**ST9 — L'argument doit d'abord être empruntable.** Une fonction demandant
`&mut Point` exige qu'on puisse créer cet emprunt sur tout le `Point`, même si
son corps n'écrit que `y`. Un emprunt actif incompatible sur `x` bloque cet
argument. Une fonction recevant `&mut Int` peut au contraire recevoir seulement
`&mut point.y`. La précision du contrat après l'appel ne légalise pas un argument
invalide au moment de sa préparation.

**ST10 — Réaffectation d'un champ référence.** Avec un accès mutable au porteur,
`vue.cible = &second` change la cible du champ sans modifier ni détruire les
valeurs pointées. L'ancienne cible cesse d'être réservée si aucun autre emprunt
ne la retient ; la nouvelle cible est suivie dès l'affectation et doit vivre
assez longtemps. La structure reste entièrement initialisée.

**ST11 — Réemprunt d'un champ mutable.** `&mut *vue.cible` réemprunte l'objet
ciblé par un champ `&mut`, sans produire un `&mut &mut T`. Jusqu'au dernier usage
du réemprunt, l'accès mutable d'origine, le remplacement du champ et la
destruction du porteur sont refusés. Les autres champs prouvés distincts
restent accessibles.

**ST12 — Contrat d'un réemprunt indirect.** Une fonction retournant le réemprunt
d'un champ mutable conserve à la fois la cible et la réservation de la capacité
mutable stockée dans le champ. Suivre seulement l'adresse de la cible ne suffit
pas. Le contrat peut néanmoins libérer les autres chemins distincts après
l'appel, comme ST8.

**ST13 — Référence partagée retournée comme valeur.** `return vue.cible`, pour
un champ de type `&Int`, restitue la référence partagée vers sa cible extérieure.
Le résultat conserve cette dépendance, pas une dépendance artificielle envers le
slot du porteur. Le porteur peut donc être détruit après l'appel si aucun autre
emprunt ne le bloque. La cible reste protégée jusqu'au dernier usage du résultat.
Ce cas ne permet pas de copier une référence mutable.

**ST14 — Emprunt du stockage d'un champ direct.** `return &point.x` désigne
au contraire une partie du slot de `point`. Le contrat conserve cette dépendance
envers l'allocation : sa destruction est refusée avant le dernier usage du
résultat. Les frontières enfant → parent, les pools et l'absence de promotion
implicite continuent de s'appliquer, sans nouvel arbitrage spécifique aux structs.

## 3. Transferts, remplacement et copie

**ST15 — Pas d'extraction par déplacement ni d'état partiel.** La décision
finale interdit d'extraire par déplacement un champ non Copy. Par exemple :

```rust
let mut sortie = <- vue.cible; // Refusé si cible est &mut Int.
```

On utilise un emprunt/réemprunt ou on transfère la structure entière. Les champs
peuvent être lus ou copiés quand leur type et les réservations le permettent,
et réaffectés selon les règles de mutation, sans laisser de champ absent.
Le nettoyage détruit les champs présents d'une structure complète, puis libère
son slot complet. Aucune référence nulle n'est introduite pour représenter un
champ déplacé.

Cette décision remplace les accords intermédiaires autorisant extraction,
réinitialisation de champ absent, destruction partielle et jonctions de chemins
avec un champ potentiellement déplacé. Ces accords ne sont plus des règles du
prototype. Elle n'exige pas qu'un objet soit exposé avant la fin de sa construction.

**ST16 — Remplacement de l'allocation entière.** Une variable mutable peut
recevoir une nouvelle allocation par transfert explicite :

```rust
point = <- points.new(x: 30, y: 40);
```

La nouvelle structure est construite complètement avant la destruction de
l'ancienne. Les deux allocations coexistent pendant cette évaluation ; deux
slots sont donc nécessaires dans cet exemple. L'ancienne allocation est ensuite
détruite et son slot rendu. La variable désigne la nouvelle allocation, dont
le stockage n'est pas recopié dans l'ancien slot. Un emprunt de l'ancienne
allocation utilisé après ce remplacement le fait refuser. Cette règle généralise
la réaffectation déjà retenue, sans introduire d'état partiel de structure.

**ST17 — Copiabilité structurelle et explicite.** Une valeur de structure est
copiable si ses champs le sont, récursivement. Dans le périmètre discuté, `Int`
et les références partagées sont copiables ; les références mutables ne le sont
pas, donc une structure qui en contient ne l'est pas non plus. Les références
partagées copiées conservent leurs cibles et restrictions.

Cette propriété n'autorise pas une copie implicite de structure ni une
duplication de l'accès à une allocation par simple affectation. Une copie lit
la source et doit respecter ses emprunts actifs. Elle ne clone pas les objets
pointés par les champs références.

**ST18 — Stockage de la copie.** `copy(original)` sur une structure locale
produit une valeur indépendante du même type sur la data stack implicite du
scope destinataire. Tous les champs doivent être copiables selon ST17. Les
références partagées copiées conservent leurs cibles et leurs contraintes ;
le contenu pointé reste partagé. Le transfert de cette copie suit les mêmes
règles de placement et de durée de vie que les autres valeurs locales.
Cette précision intègre le brouillon 07 validé.

`pool.copy(original)` initialise un nouveau
slot du pool destinataire avec la copie du contenu de l'original. Le pool doit
avoir le type attendu et un slot disponible. Sur une allocation de pool,
`copy(original)` utilise le pool
réel d'origine, retrouvé grâce à la provenance de l'allocation, y compris après
passage entre scopes et fonctions. L'original reste utilisable.

Ces opérations sont spéciales pour le compilateur : elles créent une nouvelle
allocation comme `pool.new`, sans choisir silencieusement un autre pool ou un
allocateur de heap. La proposition `pool.new(-> copy(original))` est remplacée
par ces formes directes. La copie locale ne sélectionne aucun pool implicite.

La notation `copy(tableau)` déjà retenue pour les tableaux fixes inline conserve
son statut : il faut distinguer ce cas existant d'une copie allouée de structure
avec provenance de pool. La future intégration des deux doit conserver leurs
sources et leurs règles de transfert, sans modifier silencieusement les tableaux.

## 4. Méthodes

Les [règles TF1–TF5](TYPE_FEATURES.md) complètent ME1, ME2 et ME4 : les
receveurs de feature `&self`, `&mut self` et `-> self` exigent respectivement
les modes concrets lecture, permission de mutation et consommation ci-dessous. La résolution
statique conserve les effets et les origines du contrat de méthode concret.

**ME1 — Signature du receveur.** Une méthode se déclare dans `impl Type`.
Son premier paramètre est `&self`, `&mut self` ou un receveur typé comme
`self: &Type`, `self: &mut Type` ou `self: Type`.
Les règles des fonctions s'appliquent aux arguments, contrats,
résultats, réservations et nettoyage. Une méthode qui modifie le contenu exige
un accès mutable ; calculer `self.valeur + 1` sans affectation ne modifie pas le
champ et ne suffit pas à justifier une signature mutable.

**ME2 — Emprunt automatique du receveur.** L'appel `point.somme()` peut créer
l'emprunt du receveur demandé par sa signature. Un receveur mutable exige les
droits correspondants et le respect des réservations actives. Cette exception
ergonomique s'applique au seul receveur. ME4 régit le passage du receveur
par valeur.

**ME3 — Noms distincts des champs.** Une méthode ne peut pas avoir le même nom
qu'un champ du type. Le cas `compteur.valeur`/`compteur.valeur()` a été écarté :
un oubli de parenthèses ne doit pas produire un autre accès valide à ce champ.
Cette décision remplace la proposition initiale de coexistence des deux noms.
Elle ne définit pas à elle seule la visibilité, les modules ou une surcharge.

**ME4 — Receveur par valeur.** La signature `fn terminer(self: Compteur)`
déclare un receveur passé par valeur. L'appel `compteur.terminer()`
déplace `compteur` vers le premier paramètre `self` selon la règle des
arguments par valeur. La liaison d'origine est alors indisponible.
Les règles d'emprunt, de provenance et de nettoyage d'un argument
ordinaire s'appliquent.

## 5. Exemples de conception

### Construction, défauts déduits et copies indépendantes

```rust
struct Point {
    x: Int,
    y: Int,
}

fn main() -> Int {
    let mut points = Pool<Point>::new(3);
    let original: Point = points.new(x: 10); // y = 0.
    let mut explicite: Point = points.copy(original);
    let abregee: Point = copy(original);

    explicite.x = 30;
    print(original.x);  // 10
    print(explicite.x); // 30
    print(abregee.x);   // 10

    drop(-> abregee);
    drop(-> explicite);
    drop(-> original);
    return 0;
}
```

### Référence partagée indépendante du porteur

```rust
struct Vue {
    cible: &Int,
}

fn obtenir_cible(vue: &Vue) -> &Int {
    return vue.cible;
}

fn main() -> Int {
    let mut nombres = Pool<Int>::new(1);
    let mut vues = Pool<Vue>::new(1);
    let mut nombre: Int = nombres.new();
    nombre = 10;

    let vue: Vue = vues.new(cible: &nombre);
    let emprunt = obtenir_cible(&vue);
    drop(-> vue);

    // drop(-> nombre); // Refusé ici : emprunt doit encore servir.
    print(*emprunt);
    drop(-> nombre);
    return 0;
}
```

### Méthodes mutables et receveur par valeur

```rust
struct Compteur {
    valeur: i32,
}

impl Compteur {
    fn incrementer(self: &mut Compteur) -> i32 {
        self.valeur = self.valeur + 1;
        return self.valeur;
    }

    fn terminer(self: Compteur) -> i32 {
        return self.valeur;
    }
}

fn main() {
    let mut compteur = Compteur { valeur: 10 };
    print(compteur.incrementer()); // 11
    let resultat = compteur.terminer();
    print(resultat); // 11. compteur a été déplacé.
}
```

## 6. Principe d'intention et méthode de travail

I6 dans LANGUAGE_RULES.md consigne l'objectif de génération par IA : rapprocher
l'intention du code lisible et favoriser le refus d'une intention incohérente
plutôt qu'une autre interprétation valide mais inattendue. Il faut signaler les
implicites, les notations fragiles et les effets qui exigent de lire un corps
pour comprendre un appel. ME2 est une exception explicitement acceptée ; ME3
et ME4 réduisent les changements silencieux de sens au site d'utilisation.

Les règles mémoire existantes s'appliquent aux structures et méthodes sans
être soumises à une nouvelle validation de conception à chaque variante. Leurs
combinaisons deviennent des obligations de test. Ne présenter que les nouveaux
arbitrages dans la suite de la discussion, avec règle d'abord et snippet complet,
et sans implémenter tant que cette phase d'arbitrage reste en vigueur.

## 7. Points reportés et statut

- Les défauts personnalisés, les tags et les méthodes de construction personnalisées restent reportés.
- La [méthode de destruction](DROP-fr.md#méthode-de-destruction) est prise en charge pour les valeurs fixes. La section liée précise les limites.
- Visibilité, modules, surcharge et autres extensions de méthodes : non définis
  par ce chantier et non nécessaires pour réarbitrer les règles mémoire communes.
- Compléter les formes d’expression et les types de champs de `copy` qui ne
  sont pas encore pris en charge ; la distinction entre copie locale et copie
  dans un pool est désormais définie par ST18.
- ABI, alignement des structures, algorithme de résumé des chemins, protocoles
  de copie et vérification des contrats : à implémenter et valider ultérieurement.
- Chaînes UTF-8 : au moment de la consignation initiale, ce chantier était
  seulement proposé. Les décisions ultérieures du 5 novembre sont désormais
  dans [UTF8_STRINGS.md](UTF8_STRINGS.md), avec le nom retenu `str` en minuscule.

Le statut initial de ST1–ST18 et ME1–ME4 était **N**. La couverture actuelle
reste partielle et est détaillée dans [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md).
Les références aux règles déjà testées ne prouvent pas leur extension à tous
les types de structures. Le [rapport documentaire](cycles/STRUCTURES_METHODS_CYCLE.md)
conserve la portée de la consignation initiale.

## Tuples

Un tuple contient au moins deux éléments. Chaque position a son propre type.
Le type attendu du tuple guide l’inférence à chaque position, y compris dans
une déclaration, un argument ou un retour. Sans type attendu, chaque
expression suit les règles habituelles. L’évaluation va de gauche à droite.

Le tuple se transmet comme une seule valeur. Une déclaration comme
`let (gauche, droite) = paire;` consomme le tuple entier et déplace ses
éléments dans de nouvelles liaisons. Chaque liaison suit les règles de
durée de vie et de destruction habituelles. Le groupement `(x)` et le
type unité `()` gardent leur sens.
