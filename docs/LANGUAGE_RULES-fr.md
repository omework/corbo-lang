[English](LANGUAGE_RULES.md)


Syntaxe actuelle : [méthodes dans les définitions](DEFINITION_METHODS-fr.md), remplaçant les anciens exemples avec `impl`.
# Corbo — règles de langage retenues

Les variantes d’énumération s’écrivent `Enum::Variante` dans les constructions,
`match` et `if let`. L’ancienne forme `Enum.Variante` reste acceptée pour
compatibilité. Les deux formes partagent les mêmes règles de copie, déplacement,
emprunt et destruction. `Type::methode(...)` reste un appel de fonction associée.


La [conception de File et de l’assembleur intégré](FILE-fr.md) consigne `@unchecked`, les opérandes explicites et le type `usize` déduit de la cible.

État : conception expérimentale, décisions initiales du 1er novembre 2026 ;
extension async/multithread et retrait de reset consignés le 4 novembre 2026.
Les décisions sur les data stacks et régions grandissantes sont consignées
dans [GROWING_REGIONS.md](GROWING_REGIONS.md), à la même date.
Les structures, constructions builtin et méthodes retenues le 5 novembre 2026
sont consignées dans [STRUCTURES_METHODS.md](STRUCTURES_METHODS.md).
Les décisions UTF-8, str, char et String du 5 novembre 2026 sont consignées
dans [UTF8_STRINGS.md](UTF8_STRINGS.md). Ces familles disposent désormais d'un
support partiel, détaillé par les rapports et la matrice de vérification.

Ce document consigne les décisions retenues. Il ne constitue pas encore un
système de types formalisé ni une preuve de sûreté. Le [README](../README.md)
décrit séparément le sous-ensemble effectivement implémenté par le prototype.
Les exemples de ce document peuvent employer des fonctionnalités non implémentées.
Le [périmètre de vérification mémoire](SAFETY.md) distingue les obligations,
les tests exécutés et les garanties qui restent à établir.

La [grammaire EBNF du noyau cible](../CORE_GRAMMAR.ebnf) décrit la syntaxe
synchrone et async retenue. Elle emploie les primitifs à largeur fixe et
les transferts par valeur. Le typage, les emprunts, le nettoyage et les
obligations d'attente restent définis par les règles de langage.

Une variante déclarée `Pair(u32, i64)` reçoit tous ses champs dans l’ordre
de déclaration. Le constructeur `E.Pair(premier, second)` évalue les arguments
de gauche à droite. Le motif `E.Pair(a, b)` lie les mêmes positions et accepte
`_` pour ignorer un champ. Les règles de déplacement et d’emprunt des champs
d’enum s’appliquent.

**Extension normative, implémentation partielle :**
[ASYNC_MULTITHREAD_RULES.md](ASYNC_MULTITHREAD_RULES.md) fait partie des règles
retenues. Ses règles AS1–AS16, RT1–RT8, MT1–MT11, SL1–SL2 et PR1 prévalent sur les passages
historiques incompatibles ci-dessous : async et multithread sont désormais conçus,
`main` reste synchrone, les pools d'états async sont injectés automatiquement et
l'API publique `reset()` est retirée du prototype. Le compilateur dispose d'un
support async partiel, suivi dans la matrice. Reset n'est accessible que dans
le profil de compatibilité explicitement activé. Les exemples, contrats et
preuves de reset ci-dessous sont historiques ;
ils ne réintroduisent pas cette API et ne constituent pas des preuves async.

Le prototype comprend désormais des fonctions non récursives, les allocateurs
passés explicitement par emprunt, les arguments transférés et les retours
d'allocations. La notation expérimentale `-> <- Int` distingue un retour
d'allocation de `-> Int`, qui retourne un entier copiable. La vérification
mémoire passe sur chaque corps avec des entrées symboliques et conserve les
contrôles par spécialisation aux sites d'appel réels. Les effets
externes d'allocation et de reset sont désormais résumés avec des sources
symboliques par fonction. Les résultats alloués ont aussi un résumé de leurs
origines et restitutions d’identité. Les relations nécessaires entre sources
sont inférées dans l’ordre des opérations. Les appels sont vérifiés depuis ces
contrats sans parcourir les corps appelés ; le backend C reste spécialisé.

[Règles des packages et modules](MODULES-fr.md).

La décision normative [permission de mutation](MUTABLE_ACCESS-fr.md) remplace
les anciennes obligations d’exclusivité déduites du seul `&mut`. Les obligations
de durée de vie, de synchronisation et de fin de branche sont conservées.
Corboc implémente cette séparation avec une validation ciblée ; les preuves
manquantes restent refusées.

## Noyau mémoire — grille de lecture

Les repères N1–N8 regroupent les règles déjà retenues. Les sections normatives
et les documents auxquels elles renvoient fixent le détail des règles.

| Repère | Invariant | Règles de référence |
| --- | --- | --- |
| N1 | Une valeur accessible est initialisée et utilisée avec son type. `T`, `A<T>`, `&T` et `&mut T` expriment des formes distinctes. | §2, ST1–ST5, H1 |
| N2 | Une valeur à détruire n'a qu'un responsable du nettoyage à la fois. Un déplacement transmet cette responsabilité et un emprunt la laisse en place. | §3, §6, H1 |
| N3 | La syntaxe et le type distinguent copie, emprunt et déplacement ; les primitifs et les enums admissibles selon V3 sont copiés implicitement par valeur. Un transfert sortant a besoin d'un receveur pour prendre effet. Les obligations d'usage et les règles propres aux méthodes s'appliquent. | §0, §3, §4, ST17–ST18, ME1–ME4 |
| N4 | La cible d'un emprunt et le pool source d'une allocation doivent rester valides là où la valeur est transmise. Chaque passage enfant → parent se vérifie séparément, sans promotion implicite de la cible. | §3–§5 |
| N5 | Un seul emprunt mutable actif par place qui se chevauche dans le prototype. Les places prouvées disjointes restent indépendantes. Durées de vie, synchronisation et branches restent suivies. | MA1–MA6, §5 |
| N6 | Chaque chemin qui atteint un usage doit permettre cet usage. L'analyse suit les provenances, les sorties de contrôle et l'ordre d'évaluation, y compris la préparation du remplacement avant la destruction de l'ancienne valeur. | §1–§5, F3–F4 |
| N7 | On détruit une valeur une seule fois avant de récupérer son stockage. Les dépendances contraignent l'ordre de destruction. Un slot réutilisé ne réactive aucun ancien accès. | §6–§8 |
| N8 | Les obligations de type, de provenance, d'emprunt et de nettoyage se conservent aux frontières. Un appel est vérifié à partir du contrat inféré. | §5, §10 |

Les règles async appliquent ces invariants aux captures, suspensions, résultats
et attentes. Les curseurs, régions et index de slots décrivent des politiques
de stockage. Ils restent soumis aux garanties de durée de vie et de stabilité
d'adresse applicables à chaque valeur.

Le [modèle de représentation mémoire](MEMORY_REPRESENTATION.md) décrit
les objets et les liens utilisés pour appliquer ces règles.

## Grammaire, règles et directives d'analyse

- La grammaire décrit les formes que le programmeur peut écrire.
- Une règle définit une obligation du langage et les conditions dans
  lesquelles le compilateur doit l'établir.
- Une primitive définit une opération du langage et son comportement.
- Une directive d'analyse référence une règle et décrit comment établir
  un fait qui aide à vérifier cette règle dans une situation précise.
- Un cas de test exerce ces obligations sur un programme.

Le vérificateur commence par les faits dont il dispose. S'il manque un fait
pour vérifier une règle, il sélectionne les directives qui correspondent à
la règle, à la situation dans le code et au fait recherché. Une directive
peut établir un fait, démontrer une violation ou laisser la vérification
indéterminée. Si la règle exige une preuve statique, une vérification
encore indéterminée conduit au refus. Ajouter une directive peut permettre
de prouver la même règle sur davantage de programmes.

### Refus et arbitrage de la grammaire

Un programme syntaxiquement correct est refusé si le compilateur établit
une violation ou si une obligation qui exige une preuve statique reste
indéterminée. Le diagnostic distingue la violation établie de la preuve
manquante.

Pour examiner un refus, on identifie d'abord la règle et le fait à établir.
Si le fait peut être déduit des informations déjà présentes dans le code,
le travail relève des directives d'analyse. Si une information pertinente
manque et que le développeur peut l'exprimer, on arbitre la forme qui
permet de l'écrire dans la grammaire et la façon de la vérifier.
Les combinaisons particulières de constructions servent de cas de test
des règles existantes.

Pour une branche d'exécution, N4 fixe la validité des dépendances et
l'annotation `branch` décrit un point où la fin de leurs usages peut être
établie. Le nettoyage côté runtime relève de RT7.

Le format suivant est proposé pour consigner une directive. Ici, `g` désigne
le groupe dont le vérificateur doit prouver qu'il est non vide avant
`select()`.

```yaml
règle: SL1
correspond_si:
  - Le fait recherché est « g est non vide » à la jonction d'un if.
  - Sur chaque chemin qui atteint cette jonction, le même groupe g est connu non vide.
établit: g est non vide après la jonction.
```

## 0. Principe d'intention explicite

**I1 — Propriété centrale.** Les choix de gestion mémoire doivent être explicites
dans le code : source du stockage, emprunts, déplacements, transferts et demandes
de destruction anticipée. Le compilateur vérifie ces intentions ; il ne les
remplace pas silencieusement par une autre stratégie.

**I6 — Intention lisible et génération par IA.** La sûreté et l'explicitation des
règles doivent réduire l'écart entre l'intention du développeur et le code généré,
notamment par IA. Favoriser les refus d'intentions incohérentes plutôt que les
changements silencieux de sens ; signaler les allocations, emprunts ou transferts
cachés et les notations proches pouvant produire un autre programme valide.
Les exceptions ergonomiques doivent être identifiées et arbitrées, comme
l'emprunt automatique du receveur de méthode en ME2. Cet objectif n'est pas une
preuve d'équivalence entre une intention en langage naturel et un programme.

**I2 — Source de stockage.** Tout stockage de taille fixe est placé sur
une data stack. Les valeurs locales utilisent la data stack implicite.
Le descripteur d’une collection grandissante et la zone d’un pool
suivent cette règle. Une allocation en pool exige le choix explicite du pool par
`pool.new(...)`. Le compilateur gère le placement sur la data stack sans
sélectionner de pool à la place du programmeur. Les passages qui emploient
`stack(octets)`, `Allocator` ou `new(source)` décrivent l’ancienne API.

**I3 — Calcul du placement.** Le compilateur calcule les emplacements, les
curseurs et le nettoyage de la data stack implicite et des pools choisis
par le programmeur. Ces opérations suivent les règles de durée de vie.

**I4 — Dimensionnement.** L’annotation globale
`#(datastack: size=4G, region_stack_size=4G, region_size=100M)`
et chacune de ses propriétés sont facultatives. Pour chaque taille omise, l’analyse statique
utilise le maximum qu’elle peut établir, puis la valeur par défaut
de G2 si ce maximum est inconnu. P2 définit la configuration locale.

[TYPE_FEATURES.md](TYPE_FEATURES.md) complète I5, B4 et B5 : TF1–TF5
introduisent les contraintes structurelles à une méthode, leur résolution
statique et la conservation des contrats concrets.

**I5 — Référence pour le cœur du langage.** Rust est la base retenue pour les
types, expressions, opérateurs, contrôle de flux et pattern matching. On ne
cherche pas à redessiner ces aspects sans nécessité. Les choix explicites déjà
retenus pour Corbo, notamment la gestion mémoire, restent prioritaires : `new`
avec source explicite, scopes, emprunts, `<-`/`->`, allocateurs et pools.

Pour les conversions numériques, la décision de conversion vérifiée dans
[Extraction et conversions vérifiées](CHECKED_EXTRACTION_CONVERSIONS-fr.md)
remplace la restriction antérieure du brouillon 07 sur `as`. `valeur as T`
vérifie la représentabilité exacte de la valeur et arrête le programme en cas
d’échec. `T::try_from(valeur)` reste l’alternative récupérable. Le suffixe `!`
extrait le contenu de Ok/Some et arrête le programme sur Err/None ; le préfixe
`!` reste la négation booléenne.

Cette référence vise un noyau minimaliste : syntaxe lisible, types simples,
fonctions, blocs, expressions, conditions, boucles, enums et pattern matching.
Elle n'implique pas de reproduire toutes les fonctionnalités de Rust. Les
macros complexes, procédurales ou fondées sur un langage de réécriture restent
hors périmètre. Les directives locales simples de configuration mémoire prévues
en P2 restent compatibles avec ce choix ; elles n'exigent pas un système général
de métaprogrammation.

Cette décision fournit une référence de conception ; elle ne signifie ni que
tout Rust est implémenté, ni que sa bibliothèque `core`/`std` est reprise, ni que
ses règles d'ownership remplacent celles de Corbo. Les traits, threads et async
étaient hors du périmètre initial. Les traits à plusieurs méthodes restent
reportés ; les type features à une méthode ont un support statique. Threads
et async disposent d'un support partiel suivi dans la matrice, qui distingue
les cas exécutés des règles encore à raccorder.

L'ancienne notation du prototype employait `new(source) Int(...)`, avec
`allocator()` ou `stack(octets)` pour déclarer une source locale. I2 décrit
la décision actuelle. Les anciens exemples ci-dessous illustrent les règles
locales indiquées ; ils ne remplacent pas les décisions de notation récentes.

## 1. Blocs et exécution

**S1 — Syntaxe.** Un bloc commence par `{` et finit par `}`. La notation
`scope A { ... }` servait à la discussion ; elle ne fait pas partie de la syntaxe.

**S2 — Modèle initial et extension.** Le modèle initial est synchrone.
La conception async/multithread est définie par AS1–AS16, RT1–RT8, MT1–MT11 et SL1–SL2 dans
[l'extension normative](ASYNC_MULTITHREAD_RULES.md). Elle ne doit pas être
présentée comme entièrement vérifiée par ce compilateur : son support partiel
et ses preuves d'exécution sont suivis dans la matrice.

Les traits à plusieurs méthodes restent hors périmètre pour le moment. Leur absence
n'impose pas de décision définitive sur leur ajout ultérieur.

**S3 — Appels.** Chaque appel de fonction crée une activation de scope dont le
parent est le scope appelant, indépendamment du lieu de déclaration de la
fonction. Chaque appel récursif a sa propre activation.

**S4 — Boucles et branches.** Chaque itération et chaque bloc de branche possède
son propre scope. Les règles de transfert et de nettoyage s'y appliquent.

**S5 — Sorties anticipées.** `return`, `break` et `continue` ferment les scopes
effectivement quittés, du plus interne au plus externe, avec leur bilan de
transfert et de nettoyage.

Le prototype implémente désormais `loop { ... }`, `while condition { ... }`,
`break;` et `continue;`. Chaque itération
ferme son scope avant la suivante. `break` nettoie les scopes traversés jusqu'à
l'itération, sans fermer le parent ; il vise la boucle la plus proche de la
fonction courante. Les états de reprise sont analysés jusqu'à stabilisation,
et les états des sorties `break` déterminent les accès disponibles après la
boucle. `continue` nettoie les scopes quittés puis reprend la prochaine
itération de cette même boucle. Ses chemins participent à l’analyse de reprise.
Les emprunts utilisés à l'itération suivante restent protecteurs.

`return` conserve son effet sur la fonction entière. Une boucle sans sortie
normale ne produit pas de continuation fictive. `for`
et les labels utilisateur restent différés. La lecture
`*data` copie le contenu Int d'une allocation ou d'un emprunt en respectant
les restrictions d'accès. Voir [LOOPS.md](LOOPS.md).

`while` teste sa condition avant chaque itération, y compris avant la première.
`continue` revient au test. Le test et le corps partagent le scope d'itération :
les temporaires du test sont nettoyés même lorsque sa condition est fausse.
L'état après la boucle réunit les sorties `break` et les sorties par test faux,
après ses effets mémoire. Les conditions ont le même format que celles de `if`
et leurs opérandes sont évalués de gauche à droite. Voir [WHILE.md](WHILE.md).

**S5a — Résultat de boucle.** Seul `loop` peut fournir un résultat. Chaque
`break` qui atteint son receveur fournit une valeur du même type et du même
mode. `break <- objet;` déplace une allocation d'un scope quitté, sans changer
son adresse. Le pool et les dépendances doivent survivre dans la destination.
Les provenances, les cibles et les parents des réemprunts possibles sont
conservés à la jonction. Un emprunt direct s'écrit `break &objet;` ou
`break &mut objet;`, et un réemprunt explicite `break &mut *writer;`.
Le réemprunt protège son parent jusqu'à son dernier usage. Une boucle sans
receveur accepte `break <- objet;` avec un avertissement. Le déplacement
est alors sans effet, et le nettoyage ordinaire s'applique. Chaque `break`
cible sa boucle la plus proche. Un `continue` ne fournit aucun résultat.
Un `return` quitte la fonction et annule la réception en cours.

**S5b — Propagation anticipée avec `?`.**
`expression?` est un opérateur postfixé sur `Result` et `Option`.
Il évalue son opérande une seule fois. Les opérateurs postfixés
s'appliquent dans l'ordre d'écriture. Dans `expression.await?`, `?`
s'applique à la valeur produite par `.await`.

- Si l'opérande est de type `Result<T, Inner>`, la fonction ou closure
  englobante doit retourner `Result<U, Outer>`. `Ok(value)` produit
  `value` de type `T` et l'exécution continue. `Err(error)` déclenche un
  retour anticipé. Si `Inner` et `Outer` sont identiques, le retour
  propage directement `Err(error)`. Si les types diffèrent, le
  compilateur vérifie que la fonction associée `Outer::from` est
  accessible au point d'appel et possède exactement la signature
  `Outer::from(Inner) -> Outer`. Il résout l'appel à la compilation et
  signale une erreur de typage si cette condition échoue. Seul le chemin
  `Err` appelle la fonction et retourne `Err(Outer::from(error))`.
- Si l'opérande est de type `Option<T>`, la fonction ou closure
  englobante doit retourner `Option<U>`. `Some(value)` produit `value`
  de type `T` et l'exécution continue. `None` retourne immédiatement
  `None`.

Les types `T` et `U` peuvent différer. La propagation suit les mêmes
règles de propriété et de nettoyage des scopes qu'un `return` explicite.

Un type peut déclarer une fonction associée `from` par type source.
Chaque surcharge prend un seul paramètre et retourne le type qui la
déclare. Le compilateur refuse deux déclarations pour le même type
source, y compris dans des blocs `impl` distincts. L'opérateur `?`
et l'appel explicite `Outer::from(value)` sélectionnent la surcharge
d'après le type source exact. S'il existe plusieurs surcharges, un
littéral numérique sans type prend le type numérique par défaut du
langage. Une annotation de type ou une conversion explicite permet de
sélectionner une autre surcharge.

**S6 — Point d'entrée du prototype.** `fn main()` sans paramètre est le point
d'entrée explicite. Un retour `Void` donne un code de sortie zéro ; un retour
`Int` fournit le code de sortie. Les ressources sont nettoyées avant le retour.
`main` ne retourne pas d'allocation. Avec ce point d'entrée, seules les
déclarations de fonctions et d'enums sont admises au niveau du programme.
L'ancien mode script sans `fn main` est conservé pour les exemples existants.

## 2. Valeurs, allocations et initialisation

Le [brouillon 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#types-primitifs-du-noyau)
fixe les primitifs numériques et logiques du noyau cible. Les exemples
historiques utilisent `Int` pour l'entier signé sur 32 bits du prototype.
Le nom retenu dans le noyau cible est `i32`.

**V1 — Valeurs locales et allocations en pool.** Une structure locale est
construite avec `T { champ: valeur }` et reste de type `T`. Comme un tableau
local, elle peut être transférée avec `<-`. Une construction `pool.new(...)`
produit un `A<T>` qui conserve sa provenance et son adresse. Un transfert
entre scopes ne change ni le type ni le stockage d’origine d’un `A<T>`.

**V2 — Initialisation complète.** `new` produit une valeur entièrement
initialisée. Chaque champ obligatoire doit recevoir une valeur fournie ou une
valeur par défaut définie par son type. Une référence obligatoire est fournie à
la création ; on ne crée pas un objet incomplet pour la renseigner ensuite.

```text
let mut buffer = new Buffer;
let mut writer = new Writer { buffer: &buffer };
```

### EN1 — Motifs conditionnels d’enum et égalité

`if let Motif = expression { ... }` accepte les motifs d’enum de `match`, dont
les champs positionnels et nommés, Option et Result. L’expression est évaluée
une seule fois. Les liaisons du motif n’existent que dans le bras correspondant.
`else`, dont `else if let`, est facultatif ; sans lui, une autre variante ne
fait rien. Une expression exige le même type de résultat dans chaque branche
qui continue ; l’absence de else ne fournit pas un résultat non vide.

La possession suit V3 et les règles existantes de match : une enum admissible
est copiée, une autre est déplacée, un emprunt explicite conserve sa dépendance.
Les données possédées non retenues sont nettoyées, y compris avant une sortie
anticipée du else. Un champ emprunté ne peut pas survivre à sa cible. Aucun
emprunt implicite supplémentaire n’est introduit.

Pour les enums dont chaque variante est vide ou contient uniquement des champs
primitifs directs, `==` et `!=` comparent la variante puis ses champs actifs
avec l’égalité primitive. Les deux opérandes doivent avoir le même type d’enum.
Des variantes différentes sont inégales. Chaque opérande est évalué une fois,
de gauche à droite ; les champs inactifs et le remplissage mémoire ne sont
jamais comparés. Les flottants gardent leur égalité primitive, dont le cas NaN.
Aucun ordre ni égalité récursive d’agrégats n’est ajouté.

**V3 — Copies implicites des primitifs et des enums à champs primitifs.** Les types `i32`, `i64`, `u8`,
`u16`, `u32`, `u64`, `usize`, `bool`, `f32` et `f64` sont copiés lorsqu’ils sont
lus par valeur. Une déclaration, une réaffectation, un argument ou un retour
ne rend donc pas la liaison source indisponible. Cela vaut aussi pour un
primitif servant à initialiser un champ ou une case. `copy(x)` reste une
écriture explicite facultative pour les primitifs et les enums admissibles.

Une enum est implicitement copiée par valeur si chacune de ses variantes est
vide ou contient uniquement des champs primitifs directs. Cette propriété dépend
de sa définition entière, jamais de la variante courante. Cela vaut aussi pour
les instanciations admissibles d’Option et de Result. Les structures, tableaux
et tuples gardent leurs règles de déplacement, même à champs primitifs. Un champ
référence, allocation ou agrégat, dont une enum imbriquée, empêche cette copie.
Ce changement ne copie pas
implicitement les références et ne duplique pas les allocations `A<T>`.
Les captures conservent leurs règles existantes. `drop(x)` et les directives
explicites de transfert conservent leur effet ; une liaison détruite reste
inutilisable. Une copie de `usize` issu de `addr()` conserve sa provenance et
reste confinée au bloc `@unchecked` d’origine.

```rust
let a: i64 = 12;
let b = a;         // Copie a ; a reste disponible.
let c = copy(a);   // Même copie, écrite explicitement.
let vue = &a;     // Emprunt explicite, distinct d’une copie.
```

**V4 — Déclarations, mutations et réaffectations.** Une déclaration utilise
`let name = expression` ; `let mut name = expression` autorise les écritures
sur cette variable. `var` n'est plus accepté. L'initialisation est complète.
Un accès direct à une allocation ou à un scalaire est immutable par défaut :
le modifier ou former `&mut name` exige `let mut`.

La mutabilité de la variable est distincte de celle de la référence :
`let view = &mut data` permet `view.set(20)` sans permettre de réaffecter `view`.
`let mut view = &data` permet de réaffecter la référence selon les expressions
supportées, mais n'autorise pas à modifier sa cible en lecture.
L'immutabilité est celle de l'accès nommé ; elle n'interdit pas un déplacement
vers un nouveau receveur mutable ni sa consommation par `drop(-> name)`.

Pour une allocation Int mutable, `name = 20` et `name.set(20)` modifient son
contenu, sans nouvelle allocation, changement d'adresse, réception, transfert
ou destruction. La partie droite de `=` peut être une expression scalaire
supportée ; elle est entièrement évaluée avant l'écriture. La cible doit encore
être vivante et accessible ensuite, et les emprunts nécessaires après cette
écriture restent protecteurs. Un scalaire mutable est modifié en place selon
les mêmes droits. Une référence ne se déréférence pas implicitement dans
`view = 20` : cette réaffectation changeant son mode est refusée. La mutation de
sa cible passe par `view.set(20)`, sous réserve d'un type &mut Int.
Le prototype accepte un littéral Int signé pour `.set(...)`.

Si la partie droite fournit une allocation, il s'agit au contraire d'un
remplacement. L'expression de droite est entièrement évaluée avant de détruire
l'ancienne allocation et d'installer le nouvel accès dans la variable mutable.
Un emprunt de l'ancienne allocation peut être utilisé pour la dernière fois
dans cette expression ; un emprunt devant encore servir ensuite fait refuser
la réaffectation. L'ancienne allocation n'est pas détruite de nouveau en fin de
scope ni par un reset ultérieur.

Un remplacement exige que l'accès au receveur soit valide sur tous les chemins
qui atteignent le début de l'affectation. Un chemin qui quitte la fonction
avant cette affectation est exclu. Cette condition s'ajoute aux vérifications
sur les effets de la partie droite.

Si l'expression a déjà consommé ou détruit l'ancienne allocation, le compilateur
ne répète pas sa destruction. Si elle retourne exactement la même allocation
par déplacement ou transfert aller-retour, cette allocation reste vivante.
Réaffecter un emprunt ne détruit pas l'objet qu'il référence ; réaffecter un
scalaire copiable remplace simplement sa valeur.

La nouvelle allocation conserve sa source propre, même si elle diffère de celle
de l'ancienne. Une allocation de remplacement peut donc coexister brièvement
avec l'ancienne : la capacité du pool doit le permettre. Un échec d'allocation
arrête le prototype avant cette destruction, selon E1.
Cette décision remplace le nettoyage différé initialement retenu pour l'ancienne
allocation. Le contrat est détaillé dans [REASSIGNMENT.md](REASSIGNMENT.md).

**V5 — Adresse stable.** Une allocation conserve son adresse pendant sa vie,
y compris lors des transferts. Une fois sa vie terminée, son emplacement peut
être réutilisé. Déplacer l'accès entre variables ne déplace pas les octets.

## 3. Déplacements et transferts

Pour la syntaxe moderne, le [brouillon 02](../design-buffer/02-marqueur-transfert.md)
fixe la notation des déplacements par valeur et des captures. Le passage
par valeur copie les primitifs et les enums admissibles selon V3 ; les autres valeurs sont déplacées.
Le receveur d'un résultat de bloc
est visible et l'accès d'origine ne se réactive pas. `move a;` transfère
une liaison à l'entrée du bloc enfant. `move { ... }` capture par valeur les
liaisons utilisées du parent. Les contrôles de durée de vie, d'identité,
d'emprunts et de nettoyage de cette section s'appliquent aussi à ces formes.

Les exemples avec des flèches de transfert ci-dessous décrivent la syntaxe
historique, encore acceptée pour la compatibilité.

**T1 — Intention explicite.** Une affectation ne transfère pas implicitement une
allocation entre scopes. Les intentions sont exprimées par les opérateurs de
déplacement/transfert ou par les emprunts. Les flèches `->` et `<-` restent
la notation des transferts. `>` et `<` restent des comparateurs.

**T2 — Déplacement dans le même scope.** `let mut b = <- a` déplace l'accès de `a`
vers `b`. `a` devient inutilisable. Le rattachement de l'allocation et sa place
dans l'ordre de destruction ne changent pas.

**T3 — Transfert montant.** `<- value` indique un transfert vers le parent
direct, réalisé au bilan de sortie du scope enfant. Ce marquage ne rend pas
l'allocation inutilisable dans son scope de création avant la sortie, sous
réserve des règles d'emprunt et des autres déplacements explicites.

**T4 — Transfert descendant.** `-> value` transfère vers le scope enfant direct,
avec effet à son entrée. L'instruction `value ->;` exprime ce transfert.
Le parseur conserve aussi l'écriture initiale `-> value;`. Le scope source ne peut ensuite réutiliser l'allocation
que si un transfert de retour la rend de nouveau disponible.

**T5 — Niveaux successifs.** Atteindre un ancêtre ou un descendant plus éloigné
demande de traverser les niveaux intermédiaires. Prévoir physiquement le stockage
dans une zone durable ne supprime pas ces étapes sémantiques.

**T6 — Retour et réception.** Une valeur sortant d'une expression bloc doit
être retournée et reçue explicitement dans le parent. Un retour final implicite
à la Rust est admis ; `return <- value` est la forme explicite. Une fonction
`fn creer() -> <- Point` peut rendre une structure locale avec
`return <- point`. Le receveur obtient un `Point` et D1 s’applique.

Le `<-` final d'un bloc ou d'une branche avec receveur s'écrit sans point-virgule.
`<- objet;` est un marquage en fin de bloc et ne fournit pas une valeur de
branche. Une tentative de transfert sans receveur émet un avertissement
et laisse l'allocation rattachée à son scope.

Une réception dans une nouvelle variable ne réactive pas l'ancien accès déplacé
vers l'enfant. Dans un bloc ordinaire sans nouveau receveur, le retour d'une
allocation importée restaure son accès initial dans le parent. Cela évite de
créer deux accès directs utilisables à la même allocation.

```text
let mut result = {
    let mut data = new Data;
    <- data
};
process(&result);
```

La forme compacte `let <- y = new Data` exprime l'intention de transfert dès
la déclaration. Elle ne rend pas le nom `y` visible dans le parent : un retour
et un receveur restent nécessaires. Le retour final peut alors être `y`.

**T7 — Affectations vers un ancêtre.** Un receveur situé dans un ancêtre
détermine la destination requise ; le changement de rattachement doit rester
explicite. La première proposition d'une promotion automatique par affectation
a été remplacée par cette exigence d'opérateur explicite.

**T8 — Réutilisation après transfert descendant.** Une allocation transférée
vers un enfant ne peut être réutilisée après celui-ci que si son retour est
garanti sur tous les chemins qui atteignent cette utilisation. Les blocs `if`
étant eux-mêmes des scopes, `<-` dans un tel bloc ne saute pas son parent direct.

**T9 — Jonction conditionnelle.** Un accès est utilisable après un `if` seulement
s'il reste valide sur tous les chemins qui atteignent cet usage. Les branches
qui font `return` sont exclues de cette continuation, mais leurs effets restent
pris en compte chez l'appelant après la fonction. Une allocation vivante sur
certains chemins seulement reste suivie pour son nettoyage, sans réactiver son
ancien accès. La réutilisation de son adresse ne réactive pas son nettoyage.

Le prototype implémente les instructions `if / else`, les comparaisons Int,
les conditions littérales `true`/`false`, les retours Void/scalaires et les
transferts aller-retour à ordre de réception compatible. Les retours conditionnels
d'allocations sont désormais autorisés si tous les chemins retournent explicitement
une allocation du type déclaré. Les sources réelles peuvent différer : le
résultat porte l'union de leurs provenances possibles. Deux pools distincts
restent deux sources ; les variantes d'un même pool d'enum partagent sa source
publique. Chaque source possible doit être assez durable pour le transfert.

L'allocation choisie est transférée sans copie, les autres allocations du chemin
exécuté sont nettoyées, et le receveur assure ensuite sa destruction unique.
Le compilateur conserve les effets de chaque chemin chez l'appelant. Le contrat
est détaillé dans [CONDITIONAL_RETURNS.md](CONDITIONAL_RETURNS.md).

Le prototype refuse toujours les ordres de réception incompatibles. Les conditions
Bool générales restent à étendre. Le prototype suit les réaffectations
explicites d'un receveur ancêtre sur les branches d'un `if` qui continuent,
avec les contrôles de T7, V4 et L3. Voir [CONDITIONALS.md](CONDITIONALS.md).

**T10 — If avec receveur.** Une expression `if / else` peut fournir une allocation
à un receveur. Chaque branche qui continue fournit le même type et le même
mode. Une allocation exige `<- allocation`, sans point-virgule. Une valeur
Int copiable peut être fournie directement. Les sources possibles sont réunies. `else` est obligatoire ; `else if` est
autorisé. Les temporaires de la branche sont nettoyés et l'allocation sélectionnée
est reçue dans le parent sans copie ni changement d'adresse.

Le `<-` final fournit la valeur de la branche sans quitter la fonction. Un
`return` explicite quitte la fonction et exclut ce chemin de la réception de
l'expression. Les résultats empruntés restent hors de cette étape.
Un ancien accès déplacé n'est pas réactivé par la réception dans une nouvelle
variable. Le receveur doit avoir un usage explicite, comme les autres résultats
de blocs et fonctions. Voir [IF_EXPRESSIONS.md](IF_EXPRESSIONS.md).

**T11 — Provenances multiples.** Un résultat alloué peut dépendre de plusieurs
sources possibles, déduites par le compilateur. Aucun objet n'est relocalisé.
Tant qu'un usage futur du résultat ou d'un emprunt reste nécessaire, chaque
source possible est protégée contre un reset incompatible. Le nettoyage utilise
la provenance réelle de l'objet ; un reset autorisé d'une seule source ne détruit
pas l'objet s'il dépend d'une autre. L'accès potentiellement détruit est invalidé
et le suivi du nettoyage des survivants est conservé. La forme `source.drop`
exige une provenance unique égale à cette source ; `drop` utilise la provenance
réelle. Voir [PROVENANCES.md](PROVENANCES.md).

## 4. Vérification d'usage et dépendances

**U1 — Résultat utilisé.** Un résultat reçu doit avoir un usage explicite
possible dans le parent. Un usage conditionnel suffit. Un résultat sans aucun
usage explicite est rejeté à la compilation.

Les brouillons 01 et 07 précisent que tout résultat faillible, avec ou sans
allocation, exige un usage explicite : traitement, transmission ou
`drop(-> expression)`. L’expression seule suivie de `;`, `let _ = ...` et
une liaison jamais utilisée sont refusés, indépendamment de la variante
connue. `Err(_)` peut ignorer un détail d’erreur sans valeur propriétaire.
Le type entier d'un résultat pouvant posséder une allocation impose également
cet usage : réception, transmission, match consommant ou drop. Une liaison
propriétaire reçue doit être lue, empruntée, transférée ou détruite explicitement
au moins sur un chemin possible ; un préfixe `_` ne dispense pas de cette règle.
Après le dernier usage, le nettoyage ordinaire de portée continue à s'appliquer.


Cette vérification s'ajoute au transfert : elle ne rend pas la durée de vie
conditionnelle à l'exécution effective de l'usage. La proposition initiale
« transfert sans effet si inutilisé » a été remplacée par cette erreur de
compilation.

**D1 — Durabilité des cibles sans promotion implicite.** Transférer une valeur
ne transfère pas les allocations qu'elle emprunte et ne prolonge pas leur vie.
À chaque frontière enfant → parent, toutes les cibles empruntées doivent déjà
être vivantes et rattachées à la destination ou à un de ses ancêtres. Sinon,
le transfert est refusé, même si leurs pools survivent à la frontière.

Cette décision remplace la proposition antérieure où les dépendances locales
accompagnaient automatiquement la valeur. Cette promotion n'est pas une
fonctionnalité différée : elle est interdite. Le même contrôle s'applique
séparément à chaque transfert successif, sans raccourci vers un ancêtre.

**D2 — Sens du graphe.** Une allocation ne survit pas seulement parce qu'elle
référence une allocation survivante. L'analyse suit les dépendances depuis les
valeurs qui sortent pour vérifier leur validité, sans modifier le rattachement
ou la durée de vie des cibles référencées.

**D3 — Analyse conservative.** Si une référence peut viser `x` ou `y` selon une
branche et que l'analyse ne distingue pas le chemin exécuté, les deux
dépendances possibles sont retenues. L'accessibilité statique peut donc retenir
plus d'allocations que l'accessibilité réelle d'une exécution.
Cette conservation concerne les cibles et contraintes de l'analyse : elle ne
prolonge pas leur vie et ne les promeut pas dans un autre scope. D1 s'applique
à chaque cible possible.

**D4 — Références valides.** Aucun transfert, mutation ou nettoyage accepté ne
doit permettre un accès à une valeur détruite ou à un stockage invalidé. Une
situation dont la sûreté ne peut pas être établie est rejetée.

Les dépendances vers un allocateur suivent les règles spécifiques de la section
7 : elles n'autorisent jamais son transfert implicite.

## 5. Emprunts et fonctions

**B1 — Lecture et mutation.** `&T` donne un accès en lecture et `&mut T`
une permission de mutation, sans unicité implicite. Les accès suivent MA1–MA6 :
coexistence permise, synchronisation démontrée pour les accès concurrents concernés,
et conservation des dépendances de validité.

**B2 — Fin d'emprunt.** La dernière utilisation peut terminer une dépendance
d'emprunt avant la fin du bloc. Elle ne termine ni une autre branche encore active,
ni un contrat de verrou porté jusqu'à la destruction d'un résultat.

**B3 — Emprunt et déplacement.** Pour le prototype, un déplacement est interdit
tant qu'un emprunt doit encore être utilisé.

**B4 — Paramètres explicites.** Signature et appel indiquent le mode de passage :

```text
fn inspect(buffer: &Buffer) { /* ... */ }
fn modify(buffer: &mut Buffer) { /* ... */ }
fn consume(mut buffer: -> Buffer) { /* ... */ }
fn count(value: Int) { /* ... */ }

inspect(&buffer);
modify(&mut buffer);
consume(-> buffer);
count(42);
```

Un paramètre sans indication d'emprunt ou de transfert n'est admis que pour un
type built-in copiable ou pour une valeur tableau fournie selon E5. Passer une
référence ne transfère pas l'allocation.

Les paramètres sont eux aussi des variables immutables par défaut. La notation
`fn edit(mut data: -> Int)` permet de modifier l'accès direct reçu par transfert ;
`fn edit(mut n: Int)` permet de réaffecter sa copie scalaire. Recevoir une
allocation d'un accès immutable par transfert reste possible : sa mutabilité
locale dépend du paramètre receveur. Un paramètre `data: &mut Int` peut modifier
sa cible sans `mut data`, puisque le droit d'écriture vient du type de référence.
`mut data: &Int` n'accorde pas ce droit.


À l'appel, on crée un emprunt depuis une allocation avec `inspect(&data)` ou
`modify(&mut data)`. Si `view` est déjà un emprunt, on le passe par son nom :
`inspect(view)` ; un résultat de fonction déjà emprunté se passe directement,
comme `inspect(borrow(&data))`. Le mode reste déclaré dans la signature.
Ce passage ne transfère ni ne copie l’allocation. Une référence mutable conserve
sa permission d’écrire et ses dépendances aux appels. MA1–MA6 régit les accès
coexistants, sans unicité implicite ni suspension automatique de tous les alias.

`&view` ajoute un niveau de référence ; ce n'est pas un raccourci vers sa cible.
Les types de références imbriquées sont admis, par exemple `&&mut i64`
et `&mut &mut i64`. Chaque niveau garde son mode et sa durée de vie.
Une écriture à travers plusieurs niveaux exige un accès mutable à chaque niveau traversé.
La même distinction vaut pour les paramètres de pools : `create(&mut pool)`
depuis une source locale, puis `create(memory)` si `memory` est déjà un paramètre
`&mut Pool<Int>`. Un emprunt de pool en lecture ne devient jamais mutable.
Cette règle de passage/retour par nom n'autorise pas un déplacement d'allocation
sans opérateur ni les affectations générales entre variables de références.
Voir [REFERENCE_VALUES.md](REFERENCE_VALUES.md).


**B4a — Expressions et ordre des arguments.** Les arguments sont évalués de
gauche à droite, chaque expression terminant avant la suivante. Un résultat
scalaire est copié dans un temporaire avant d'évaluer l'argument suivant. Les
appels imbriqués suivent le même ordre. L'appel externe commence seulement
après préparation de tous ses arguments.

Un emprunt utilisé seulement par un sous-appel peut terminer avant l'argument
suivant : `consume(read(&data), -> data)` est autorisé si aucun autre emprunt
ne doit encore servir. Un transfert invalide immédiatement l'ancien accès :
un argument suivant ne peut plus utiliser cet accès.

Un emprunt fourni directement à l'appel externe reste actif pendant les
arguments suivants et l'appel. Il en va de même pour les emprunts de sources.
Une allocation préparée pour être transférée doit rester vivante jusqu'à son
entrée dans la fonction ; un reset dans un argument suivant ne peut la détruire.

Les expressions produisant des allocations conservent un mode explicite :
`consume(-> new(memory) Int(42))`, `consume(-> create(&mut memory))` ou
`inspect(&create(&mut memory))`. Une allocation temporaire empruntée reste
rattachée au scope appelant jusqu'à son nettoyage ou à un reset autorisé.
Les sources doivent toujours être déclarées et passées par emprunt nommé.
Le contrat et la traduction en C sont décrits dans [ARGUMENTS.md](ARGUMENTS.md).

**B4b — Résumés inférés d'effets de sources.** Les allocations et resets sont
déduits des opérations explicites et des sous-appels, sans annotations ajoutées.
Les sources des paramètres sont symboliques ; leurs effets sont substitués aux
appels. Les effets locaux ne sont pas attribués à un paramètre extérieur de même
nom. Un reset conditionnel est un effet possible. Les types qu'une source doit
pouvoir allouer sont conservés, même pour les temporaires non retournés.

Le prototype infère ces résumés pour toutes les fonctions, dont celles non
appelées, et les utilise pour les captures de nettoyage C et les exigences de
stockage aux appels. Les identités, durées de vie et types de résultats sont
contrôlés avec des entrées symboliques puis aux appels réels. Voir [EFFECTS.md](EFFECTS.md).

**B4c — Résumés inférés des résultats alloués.** Le compilateur distingue les
allocations créées pendant une invocation des identités reçues en paramètres.
Le résumé conserve les alternatives de chaque retour normal et substitue celles
des sous-appels. Une restitution d'une même entrée sur tous les retours conserve
son identité ; une sélection ne promet pas l'identité d'un candidat particulier.
La source d'un objet neuf est symbolique, sans annotation de provenance.

Aux appels, les sources et origines réelles doivent respecter ce résumé. Un slot
réutilisé par une nouvelle allocation ne satisfait pas une restitution d'identité,
même à adresse égale. Les anciennes références déplacées ne sont pas réactivées
par la réception dans un autre nom. Les adresses des objets vivants restent fixes.
Les contrôles aux appels réels restent actifs. Voir [RESULTS.md](RESULTS.md).

Un résultat alloué peut contenir des champs &Int ou &mut Int empruntant des allocations
injectées par emprunt dans l'appel. À chaque frontière enfant → parent, les
cibles doivent être vivantes et déjà rattachées à la destination ou à un de ses
ancêtres. Le contrat conserve l'identité de ces cibles, directement depuis un
paramètre Int emprunté ou depuis un champ d'un objet reçu. L'emprunt protège
les usages futurs du résultat après le retour. Un passage par `->` d'un Int
ne fournit pas cette garantie : son rattachement descend dans l'enfant.
La promotion automatique d'une cible locale est interdite par D1. Voir
[BORROWED_RETURNS.md](BORROWED_RETURNS.md).

**B4d — Contraintes inférées entre sources.** Une destruction
`source.drop(-> value)` exige l'égalité de sa source et de toutes les provenances
possibles de la valeur. Un accès à une valeur créée ou reçue avant le reset d'une
source exige que ses provenances soient distinctes de cette source. Lire puis
copier un scalaire avant le reset n'impose pas cette distinction pour la copie.

Ces obligations sont déduites du corps et des sous-appels, sans annotations.
Les branches et reprises de boucle sont prises en compte. Un résultat reçu
vivant suit son historique de réception ; les usages futurs et arguments
préparés restent protégés. Chaque appel vérifie les relations avec les sources
réelles avant émission du corps C. Voir [SOURCE_CONSTRAINTS.md](SOURCE_CONSTRAINTS.md).

**B4e — Vérification des corps sans appel réel.** Le compilateur applique les
règles existantes de déplacements, emprunts et sorties de scopes à chaque corps
avec des entrées symboliques. Les paramètres conservent leur type et leur mode ;
les identités de stockage respectent les égalités de sources inférées. Une
fonction inutilisée peut donc être refusée pour une utilisation après destruction
ou des emprunts incompatibles. Elle n'est pas émise dans le C final.

Les contrôles aux appels réels restent actifs, notamment pour les provenances
et compatibilités de stockage concrètes. Ce passage réutilise le vérificateur
des blocs et applique les contrats des sous-appels sans ouvrir leurs corps.
Le backend parcourt encore les corps pour produire le C spécialisé. Voir
[FUNCTION_BODIES.md](FUNCTION_BODIES.md) et [MODULAR_CALLS.md](MODULAR_CALLS.md).

**B5 — Emprunts retournés.** Une fonction peut retourner un emprunt si le
compilateur établit que sa cible reste valide pendant toutes ses utilisations.
Cet emprunt prolonge les restrictions d'accès correspondantes. Aucun `<-`
n'est nécessaire lorsqu'aucune allocation n'est transférée. Retourner une
référence vers une variable locale détruite au retour est interdit.

Le prototype implémente `fn borrow(data: &Int) -> &Int { return data; }`.
Le résultat est reçu explicitement, sans `<-`, et ne crée aucune allocation.
`return data` renvoie l'emprunt existant ; `return &data` créerait un niveau
supplémentaire et est refusé dans ce prototype. Un paramètre mutable peut
fournir l'accès en lecture promis par `-> &Int`, sans créer un accès mutable
supplémentaire. Les restrictions du parent mutable restent suivies.
Les contrats infèrent les identités des cibles injectées par `&` ou `&mut` et
les substituent à travers les appels successifs. Un retour conditionnel retient
toutes les cibles possibles. Chaque frontière quittée applique D1 : les cibles
sont déjà vivantes et rattachées au parent ou à un ancêtre, sans promotion.
Une cible créée localement ou reçue par `->` ne peut donc pas sortir par emprunt.
L’emprunt retourné conserve les dépendances de toutes ses cibles jusqu’à sa
dernière utilisation. Déplacement invalidant, drop et reset historique restent
soumis à N4 ; les accès au contenu suivent MA1–MA6. Il reste en lecture, même si son
paramètre d'origine est mutable. Les retours &mut Int sont désormais également
implémentés :

```rust
fn borrow_mut(data: &mut Int) -> &mut Int {
    return data;
}

let mut memory = Pool<Int>::new(1);
let mut nombre = new(memory) Int(10);
let mut vue = borrow_mut(&mut nombre);
vue.set(30);
nombre = 40; // Après le dernier usage de vue.
```

Le résultat mutable conserve la permission d’écrire et les dépendances de cible
après l’appel. Un réemprunt les transporte sans exclure automatiquement l’accès
parent. Les accès séquentiels au contenu peuvent coexister ; l’invalidation du
stockage et les accès concurrents restent soumis à MA1–MA6. Les appels successifs
conservent toutes les chaînes de dépendances pertinentes.

Un résultat &mut Int exige une provenance depuis des paramètres &mut Int.
Une entrée &Int ne devient pas mutable parce que sa variable est déclarée mut.
Les cibles locales ou reçues par transfert restent non durables au retour,
même avec une source de stockage durable. Les retours conditionnels conservent
toutes les cibles possibles et leurs obligations de validité et de synchronisation.
Il n'y a ni allocation, ni destruction, ni réception de propriété, ni déplacement
d'octets lors du retour de cet emprunt. Le nom existant s'utilise sans & ajouté.
Les retours vers d'autres types restent hors du prototype. Voir
[DIRECT_BORROW_RETURNS.md](DIRECT_BORROW_RETURNS.md) et
[MUTABLE_BORROW_RETURNS.md](MUTABLE_BORROW_RETURNS.md).


## 6. Destruction et récupération du stockage

[Méthode de destruction](DROP-fr.md#méthode-de-destruction) définit `fn drop(&mut self)` pour les types déclarés.

**L1 — Ordre des étapes.** Le destructeur s'exécute avant la récupération du
stockage de l'allocation. La valeur reste valide pendant son destructeur.

**L2 — Nettoyage automatique.** À la fermeture d'un scope, les allocations
encore rattachées à celui-ci et non déjà détruites sont nettoyées. Les allocations
transférées sont nettoyées dans leur scope de destination final.

**L3 — Ordre retenu.** Les dépendances nécessaires au nettoyage imposent
l’ordre. Pour les valeurs indépendantes, l’ordre par défaut reste inverse à
la création ou à la réception. Un groupe transféré conserve son ordre relatif
interne dans les limites de ces dépendances. L’ordre physique est distinct.

**L4 — Accès des destructeurs.** Une cible lue par un destructeur reste vivante
jusqu’à la fin de cette lecture. Une référence stockée que le destructeur ne
lit pas n’ajoute pas de dépendance de nettoyage. Sa cible respecte toujours
D1. Le compilateur refuse les contraintes qui empêchent tout ordre sûr.

**L5 — Libération anticipée optimisée.** Un mode du compilateur pourra nettoyer
plus tôt s'il prouve la préservation du comportement observable, destructeurs
compris. L'absence d'utilisation ordinaire future ne suffit pas à elle seule.

**L6 — Destruction explicite.** Le développeur peut demander une destruction
anticipée par un déplacement explicite vers `drop` :

```rust
drop(-> data);
```

Cette opération termine aussi la vie d’une liaison locale, y compris quand
sa valeur est copiable. Les contrôles d’emprunt s’appliquent.
`drop(-> expression)` évalue d’abord l’expression, puis consomme son résultat
avant l’instruction suivante. Un résultat faillible sans allocation ne demande
aucun slot de pool pour cette opération.

Pour un `A<T>`, le compilateur utilise sa provenance pour restituer son slot
au pool d’origine après le destructeur. Un accès ultérieur requis par un
emprunt ou un autre destructeur empêche la consommation. Le nettoyage de
fin de scope ignore une valeur déjà consommée.

La sémantique retenue suit celle de Rust : `drop` consomme par déplacement et
respecte les mêmes restrictions d'emprunt que les autres déplacements. Si un
emprunt doit encore être utilisé, le déplacement vers `drop` est refusé. Après
la dernière utilisation de cet emprunt, `drop` est autorisé. Après consommation,
une réutilisation de l'accès déplacé est refusée. `drop` n'est pas une exception
permettant d'invalider des emprunts encore utilisés.

**L7 — Objet mort et stockage réservé.** La data stack récupère un suffixe
libre par recul du curseur. Un trou intérieur est récupéré quand il rejoint
ce suffixe. Un slot de pool libéré peut être réutilisé à l’intérieur du pool
via son index de slots libres. La destruction précède la récupération et
termine définitivement l’accès à la valeur.

L'ajout de L6 remplace l'ancienne restriction « destruction uniquement à la fin
du scope ». Le nettoyage automatique reste le comportement par défaut.

## 7. Pools typés

**A1 — Passage explicite.** L’API publique utilise `Pool<T>::new(n)` avec une
capacité explicite strictement positive. Un pool local utilisé pour allouer
exige `let mut`. Une fonction qui alloue reçoit `&mut Pool<T>`. Le droit
de mutation provient du mode d’emprunt. La data
stack ne constitue pas un type public et n’a pas de constructeur public.
La consommation d’un `A<T>` utilise la provenance qu’il porte.

**A1a — Syntaxe de construction ordinaire.** `Pool<T>::new(capacity)` remplace
l'ancien constructeur contextuel en minuscules, désormais refusé. `Pool` est
aussi exporté par `std`, y compris avec un alias d'import.

**A1b — Saturation récupérable.** `pool.try(...)` accepte les mêmes initialiseurs
que `pool.new(...)` et renvoie `Result<A<T>, PoolError>`. `PoolError.Full`
signale la saturation des slots de la variante sélectionnée, le cas échéant.
`new` conserve son arrêt du programme en cas de saturation. Une valeur fournie
est évaluée une seule fois avant la tentative et déplacée même en cas d'échec.
En cas d'échec, elle est détruite une seule fois avant le retour de l'erreur.
En cas de succès, son nettoyage est transféré à l'allocation. Un `Result`
conservé retient les dépendances du pool et des champs ; sa destruction nettoie
l'allocation qu'il contient. Les erreurs de réservation OS/datastack ne sont
pas rendues récupérables par cette méthode.

**A2 — Dépendance de stockage.** Une allocation ne peut survivre à son pool.

**A3 — Aucun prolongement implicite.** Un pool reste rattaché à son scope
de création et se passe par emprunt. Un transfert de `A<T>` est rejeté si
le pool d’origine ne survit pas au receveur.

**A4 — Réutilisation.** Des allocations vivantes n’empêchent pas de nouvelles
allocations dans les autres slots. La dépendance envers le pool est
distincte de l’emprunt mutable qui autorise une allocation.

**A5 — Ancienne réinitialisation collective, retirée de l'API visée par PR1.**
Le texte qui suit décrit l'implémentation historique à migrer, pas une opération
retenue pour le prochain prototype. Voir [PR1](ASYNC_MULTITHREAD_RULES.md#6-retrait-de-reset-du-prototype).

Historiquement, `source.reset()` demande
explicitement la destruction des allocations encore vivantes de cette source,
puis la réinitialisation de son stockage. Le compilateur refuse l'opération si
un accès à ces allocations doit encore servir, directement ou par emprunt.
Il invalide les accès détruits et évite leur destruction ultérieure en fin de
scope. Les allocations déjà consommées par `drop` sont ignorées.

Les scopes actifs sont nettoyés du plus profond au plus extérieur, et chaque
scope suit l'ordre inverse de création/réception, en ne sélectionnant que les
allocations de cette source. Les allocations d'autres sources restent valides.
Les destructeurs doivent terminer avant la réinitialisation du stockage.
Pour un pool, une fois les destructions terminées, la récupération collective
remet le curseur de chaque stack concernée à zéro et vide son index de slots.

L'effet suit la source réelle à travers les appels : recevoir `&mut Allocator`
ou `&mut Pool<T>` autorise cette destruction collective, y compris d'allocations
de l'appelant. Le résumé de fonction indique ce reset possible ; la vérification
spécialisée contrôle les usages et les destructions à l'appel et
refuse les usages futurs dans les fonctions comme chez l'appelant. Recevoir
`&Allocator` ou `&Pool<T>` ne permet pas de réinitialiser la source.

Cette décision remplace la restriction antérieure exigeant que toutes les
allocations soient déjà détruites. La dernière utilisation seule ne déclenche
toujours pas de destruction : c'est ici l'appel explicite à `reset` qui la demande.
Le contrat et sa traduction en C sont détaillés dans [RESET.md](RESET.md).

**A6 — Fin de vie du pool.** Les allocations restantes sont détruites avant
la fermeture du pool et l’invalidation de son stockage.

## 8. Data stacks et politique de placement

Les éléments suivants constituent l'orientation retenue pour le stockage.
L'algorithme complet de placement et ses critères d'acceptation restent à définir.
L’extension normative [GROWING_REGIONS.md](GROWING_REGIONS.md), G1–G12,
définit la data stack classique, la data stack à régions, les curseurs
à sens unique et la récupération après nettoyage. Le
[rapport des régions](cycles/GROWING_REGIONS_CYCLE.md) décrit l’implémentation
historique.

**P1 — Plusieurs plages virtuelles.** La réservation et l'engagement suivent le
modèle de Goose : grandes plages virtuelles, pages mises à disposition à la
demande selon la plateforme, adresses stables, protection de fin de plage et
arrêt sur dépassement. Cela ne signifie pas réserver immédiatement autant de RAM.

**P2 — Configuration locale.** G2 fixe le dimensionnement au niveau
du programme. Pour les régions grandissantes, G6/G7 retiennent une
annotation avant le scope, par exemple `#(stack_region: max_size=4M, count=8)`,
héritée par ses enfants et remplaçable localement. `max_size` fixe la limite
de chaque région. `count`, facultatif, fixe le nombre d’emplacements
réservés. Chaque région conserve sa limite lors d’un transfert.
G6 définit les multiples binaires `K`, `M` et `G`.

**P3 — Placement anticipé.** Le compilateur suit les transferts d’une
valeur locale jusqu’à sa destination finale, selon G1. Il peut la
construire directement dans un emplacement réservé dans le scope
qui assurera son nettoyage. Des chemins exclusifs peuvent partager
l’emplacement d’un même receveur. Les transferts successifs préservent
l’adresse. La réservation seule ne construit aucune
valeur et ne déclenche aucun destructeur. Le placement préserve l’ordre des
effets d’initialisation. Pour les tailles fixes, empiler en dernier les valeurs
détruites en premier est une optimisation indépendante de la validité.

**P4 — Récupération par curseur.** Après le nettoyage, la plage du scope
enfant revient à sa position d’entrée. Les valeurs transférées résident
déjà dans une plage qui survit à ce recul. Aucun recul ne rend réutilisable
l’emplacement d’une valeur vivante.

**P5 — Curseurs à sens unique.** La data stack classique, la data
stack à régions et chaque région ont chacune un front d’allocation,
selon G3/G4. Les allocations tiennent compte de la borne et de
l’alignement. Le curseur recule lors de la récupération.

**P6 — Population vivante.** Le critère étudié est le nombre maximal
d'allocations dynamiques simultanément vivantes, pas le nombre total
d'allocations successives. Une boucle de longueur inconnue peut avoir une borne
de population vivante connue. Une borne connue ne prouve pas à elle seule la
compatibilité des croissances et des durées de vie dans une plage.

**P7 — Fallback local.** Lorsque le placement statique ne convient pas, un
allocateur local explicitement fourni peut prendre le relais. Cela change la
stratégie de stockage, pas les garanties d'emprunt, de transfert et de nettoyage.
Ce recours est un choix explicite du programmeur, jamais une substitution
silencieuse faite par le compilateur à une source data stack.

G9 ajoute un recours interne à une data stack à régions dédiée lorsque
la stack à régions courante ne permet pas le placement. Cela ne constitue pas un fallback caché vers le heap
et ne permet pas de dépasser une limite de région explicitement configurée.

**P8 — Pools typés.** Un pool de type `T` accepte uniquement des allocations de
ce type. Pour un type concret fixe, ses slots ont une taille et un alignement
adaptés à `T`. Le choix retenu pour les enums est précisé en P9 : une seule
interface publique gère des stacks distinctes par variante, plutôt qu'un slot
uniforme dimensionné pour la plus grande variante.

Le compilateur place la zone du pool sur une data stack. Le pool gère
les slots à l’intérieur de cette zone avec son curseur et son index
de slots disponibles. Il avance le curseur tant que la capacité le
permet, puis réutilise un slot libre à la limite. Détruire un objet intérieur rend son
slot réutilisable sans déplacer les autres. Un suffixe mort est retiré de
l'index libre avant récupération par recul du curseur. L'ordre physique des
slots est distinct de l'ordre sémantique de destruction défini en L3.

Dans le prototype, `Pool<Int>::new(n)` réserve une capacité stricte de `n` slots dans
une plage virtuelle, avec un seul curseur et une liste intrusive des slots
libres. Le paramètre `&mut Pool<Int>` exige cette
source typée. L’épuisement du pool arrête le programme avec un diagnostic.
La réutilisation d’un slot préserve la fin de vie de l’objet précédent.

Les pools constituent une implémentation spécialisée de source de stockage,
pas un remplacement des règles d'emprunt, de transfert, de destruction et de
validité de l'allocateur. Aucun pool n'est choisi implicitement.

**P9 — Pool d'enum.** Un seul `Pool<E>` gère une data stack dédiée à chaque
variante de `E`. Chaque stack a ses slots adaptés à sa variante, son curseur et
son index de slots disponibles. L'interface du pool sélectionne la stack selon
la variante construite ou détruite. Les valeurs vivantes gardent leur adresse.
La provenance de toutes les variantes reste le pool public d'origine.

Dans le prototype, `Pool<E>::new(n)` réserve `n` slots par variante. Les enums sont
déclarés au niveau du programme, ont des champs `Int`, `&Int` ou `&mut Int` entièrement initialisés,
et ne sont construits que via un pool du type correspondant. Une référence
pointe vers le slot, dont la stack fournit le discriminant. Les fonctions
peuvent emprunter, recevoir et retourner ces allocations avec les opérateurs
explicites existants. Le `match &value` est exhaustif. Les champs scalaires
sont copiés et le sujet reste protégé par un emprunt partagé pendant le bras.
Dans un `match &value`, les constructions locales peuvent
appeler des fonctions sous réserve de respecter cet emprunt. Les conditions
et les sorties de boucle appliquent le nettoyage habituel des portées.
Les remplacements de variante en place ne sont pas pris en charge.

Les champs `&Int` constituent une première étape de références stockées : ils
sont immuables après construction et exigent un emprunt nommé vers une allocation
Int. On fournit `field: &data` depuis une allocation, ou `field: view` si
`view` est déjà un emprunt Int ; aucun `&` n'est aplati. Leurs dépendances
conservent les dépendances contre déplacement invalidant, destruction et reset
historique tant que la cible doit servir. La mutation du contenu suit MA1–MA6. Le `match`
lie ces champs par emprunt en lecture, et non par copie de l'allocation.
Le prototype accepte leur transfert de bloc seulement si les cibles sont déjà
assez durables dans la destination, conformément à D1. Les champs vers d'autres
enums restent différés. Les retours de fonctions
contenant ces champs sont admis avec la même vérification enfant → parent ;
leurs contrats transmettent les cibles aux appelants. Un réemprunt partagé
stocké garde les dépendances et donne une permission de lecture, sans créer de
permission mutable ni suspendre automatiquement les accès au contenu du parent. Voir [REFERENCE_FIELDS.md](REFERENCE_FIELDS.md)
et [BORROWED_RETURNS.md](BORROWED_RETURNS.md).

Les champs `&mut Int` sont également admis. Ils exigent une capacité mutable :
`field: &mut data` depuis une allocation mutable, ou `field: view` si `view`
est déjà un emprunt mutable Int. Une référence en lecture ne devient pas
mutable par son stockage. Le champ conserve sa référence après construction.

L’objet conserve les dépendances de chaque cible possible et la permission
d’écriture du champ. Déplacement et retour préservent ces obligations ; D1
s’applique à chaque frontière enfant → parent, sans promotion implicite.
Plusieurs références peuvent coexister selon MA1–MA6. `match &value` donne des
projections en lecture.

`match &mut value` exige une permission d’écriture sur le porteur. Les projections
mutables conservent les dépendances de porteur et de place nécessaires à la validité
des cibles. L’accès au contenu n’exclut pas automatiquement d’autres références.
Remplacement structurel, destruction et concurrence suivent MA1–MA6. La sortie du
bras ne termine pas une dépendance portée par un résultat qui en sort.

Les bras autorisent les lectures du match de lecture et `.set()` sur les
projections mutables. Ils admettent aussi les appels `Void` dont les arguments
sont des projections nommées du bras. Les modes des paramètres suivent B4.
Une déclaration locale du bras peut recevoir le résultat d'un appel
`Int` avec les mêmes arguments. L'Int copié reste indépendant des écritures
ultérieures et sa liaison est limitée à son bloc.
Une déclaration `let mut autre = reemprunter(vue)` peut aussi recevoir
un `&mut Int`. `vue` et `autre` conservent permissions et dépendances selon
MA1–MA6 ; leur coexistence ne suspend pas à elle seule les accès au contenu par
`vue`. Le porteur reste protégé contre l’invalidation tant qu’il est requis.
Après un appel Void ou Int, le bras peut réutiliser ses projections dès le
retour. La réservation du porteur couvre tout l'appel et le reste du bras.
Dans une expression `match` par emprunt, un appel `Void` peut aussi
recevoir les autres arguments permis par B4. Une affectation dans un
bras suit les règles de transfert et de remplacement habituelles, que
le match fournisse un résultat ou soit une instruction. À la jonction,
l'état du receveur tient compte de chaque bras continuant. Un `break`,
un `continue` ou un `return` suit le chemin de sortie correspondant et
nettoie les portées traversées.

Une déclaration locale `let mut dehors = match &mut writer { ... };`
peut recevoir un emprunt mutable. Chaque bras se termine par le nom d'une
projection mutable du porteur ou d'un réemprunt qui en dérive. Le
vérificateur exige que le porteur et toutes les cibles possibles soient
vivants dans la portée du résultat. L'accès au porteur, sa destruction
et la réinitialisation de son stockage sont bloqués pendant les usages
du résultat et de ses réemprunts. Après leur dernier usage, le porteur
est de nouveau accessible selon B2.

Une fonction peut retourner cet emprunt si elle reçoit le porteur
en paramètre `&mut`. Son contrat identifie le paramètre et les champs
possibles. À l'appel, le vérificateur les résout vers le porteur et
les cibles effectifs. La réservation accompagne le résultat jusqu'à
son dernier usage chez l'appelant, y compris à travers des fonctions
relais. Le porteur et les cibles doivent survivre au retour.

Un champ peut stocker ce résultat. Les usages du nouvel objet conservent
les réservations du champ. Un réemprunt via cet objet conserve toute la
chaîne des porteurs. Le dernier usage du réemprunt rend le porteur immédiat
accessible. Les usages restants de ce porteur continuent de protéger ses
propres dépendances. À chaque transfert, les porteurs et les cibles doivent
déjà vivre dans la destination ou un de ses ancêtres. Un retour conditionnel
conserve l'union des porteurs et des cibles possibles.

Pour les resets, le contrat infère les contraintes de sources à partir de
l'ordre des opérations dans le corps et compose celles des sous-appels.
Si un chemin peut utiliser un emprunt après le reset, sa cible et les
allocations réservées doivent avoir des sources distinctes du pool réinitialisé.
L'analyse inclut les retours au début d'une boucle. L'appelant applique ces
contraintes aux allocations réelles. Il protège aussi les autres emprunts
qui devront encore servir et les arguments déjà préparés pendant l'évaluation
des suivants. Après un appel, un reset possible invalide l'accès aux
allocations qu'il peut avoir détruites.
Le chevauchement des cibles possibles ne suffit pas à interdire plusieurs
projections mutables. Le compilateur établit la validité et la compatibilité
des effets sur chaque chemin selon MA1–MA6 ; une preuve requise absente reste un refus.
Voir [MATCH_MUTABLE.md](MATCH_MUTABLE.md).

Un `reset` du pool détruit les valeurs vivantes de toutes ses stacks avant de
les réinitialiser, selon A5. L'ordre de destruction défini en L3 reste global au
scope ; il ne devient pas un ordre de regroupement par variante.

## 9. Échecs et accès aux tableaux

**E1 — Échec d'allocation.** Pour le premier prototype, un échec d'allocation
arrête le programme avec un diagnostic ; il n'est pas récupérable. Le prototype
actuel ne déroule pas les destructeurs sur cet arrêt.

**E2 — Limites des tableaux.** Un accès prouvé hors limites est rejeté à la
compilation. Un accès prouvé valide ne nécessite pas de contrôle supplémentaire.
Dans les autres cas, un contrôle à l'exécution arrête le programme avec un
diagnostic en cas de dépassement.
La découpe textuelle applique également ces contrôles aux frontières UTF-8.
`try_slice` conserve ces vérifications mais retourne une erreur récupérable :
OutOfBounds pour une plage invalide, NotCharBoundary pour une frontière coupée.
Son résultat emprunte les octets d'origine (TX4 et brouillon 07).

**E3 — Valeurs de taille fixe.** La longueur fait partie du type `[T; N]`.
Les littéraux évaluent leurs éléments une seule fois de gauche à droite.
`[expression; N]` exige un élément copiable et évalue l'expression une fois,
y compris pour zéro. `[]` exige un type de contexte. `len()` sur une variable
lit sa longueur statique sans emprunter ni lire ses éléments. Dans le noyau
cible, la longueur a le type `u64`, y compris la longueur zéro d'un tableau vide.

**E4 — Places indexées.** Chaque indice est évalué une fois. Pour une
projection imbriquée, son contrôle précède l'évaluation de l'indice suivant.
Dans le noyau cible, tout type entier est accepté pour l'indice.
Le contrôle des bornes porte sur sa valeur d'origine avant conversion.
Voir le [brouillon 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#indices-et-longueurs).
Une lecture scalaire copie l'élément. L'écriture évalue et contrôle la
destination avant la valeur de droite, puis vérifie les droits au moment de
l'écriture. Un emprunt utilisé pour la dernière fois dans la partie droite
peut finir avant celle-ci. L'écriture conserve le type de la case.

**E5 — Copies et transferts.** La copie d'un tableau ou d'une ligne se
demande avec `copy`. Une copie par valeur reçue en paramètre est indépendante.
Les résultats tableau qui traversent un `return`, un `break` ou la sortie
d'une branche avec receveur utilisent `<-` explicitement. Chaque branche qui
fournit un résultat conserve le type et la longueur. Déplacer directement
une case est interdit. `replace` vérifie l'indice, évalue la nouvelle valeur
puis l’installe après les contrôles de validité et d’effets requis et rend l’ancienne valeur. `swap` évalue
les indices de gauche à droite et les vérifie avant toute écriture. Deux
indices identiques et valides donnent un échange sans effet.

**E6 — Emprunts de tableaux et de cases.** Les emprunts de cases, y compris
des lignes, protègent le tableau d'origine entier. `ref()` et `mut_ref()`
équivalent à `&` et `&mut`. `mut()` est exclu du prototype par décision
explicite. Un emprunt sur une copie temporaire peut servir
dans l'instruction qui l'a créée. Il ne peut lui survivre. La dernière
utilisation est suivie sur les chemins de reprise de boucle. Un emprunt
qui sort par `break` doit avoir une cible durable sur chaque sortie
possible, et toutes les provenances possibles restent suivies.
Les arguments d'un appel conservent l'ordre de B4a. Un emprunt direct
de case reste actif pendant les arguments suivants et l'appel. Les
emprunts mutables ne sont pas refusés du seul fait de leur tableau commun :
leur préparation et leurs effets suivent MA1–MA6. Une fonction peut renvoyer un
emprunt d'une case injectée par emprunt si sa cible et les parents
requis sont durables selon B5 et D1.
Une preuve de bornes sur un chemin peut supprimer un contrôle si elle
vaut encore pour la valeur utilisée.

**E7 — Références stockées.** Chaque case conserve la provenance de sa
référence. Un indice dynamique retient les provenances de toutes les
cases possibles. Copier un tableau de références partagées conserve les
cibles et les emprunts. Un tableau de références mutables ne peut être
copié. Un réemprunt mutable conserve les dépendances de place et de cible sans
suspendre automatiquement les accès au contenu par la référence stockée.
Remplacement invalidant et accès concurrents restent soumis à MA1–MA6. `replace` rend l'ancienne référence avec son emprunt
et refuse le remplacement si un réemprunt actif le bloque. Ignorer
l'ancienne référence mutable termine son emprunt. Tout transfert
vérifie D1 pour les cibles possibles. Un contrat de fonction conserve
les provenances des références retournées par case.

Voir [FIXED_ARRAYS_VALIDATION.md](FIXED_ARRAYS_VALIDATION.md) pour le
périmètre implémenté et les limites du cycle.

## 10. Extension async/multithread retenue, support partiel

Les règles normatives sont regroupées dans
[ASYNC_MULTITHREAD_RULES.md](ASYNC_MULTITHREAD_RULES.md). Les décisions remplacées,
les questions reportées et le statut de chaque famille y sont explicités.
L'injection automatique AS7 concerne les états async ; elle ne rend pas implicite
la source des allocations de données ordinaires de I2/A1/P8.

## 11. Structures et méthodes retenues

[STRUCTURES_METHODS.md](STRUCTURES_METHODS.md) fait partie des règles normatives :
ST1–ST18 et ME1–ME4 consignent la construction complète, les défauts déduits,
`pool.new`, `pool.copy`/`copy`, les chemins de champs et les receveurs de méthodes.
Les accords intermédiaires sur les déplacements de champs et les états partiels
ont été retirés : ils ne sont pas des fonctionnalités à implémenter. Les méthodes
et champs d'un type ne peuvent pas porter le même nom. Les défauts personnalisés
et les tags sont reportés. Le chantier UTF-8 est désormais consigné séparément.
Le support comprend des structures locales et en pool, des copies explicites,
des méthodes et des contrats de champs. La matrice et les rapports de cycle
délimitent les types et compositions effectivement pris en charge.

### Constantes

`const NOM: T = littéral;` déclare une valeur typée dans le module.
`pub const` permet de l’exporter. Une constante déclarée dans `impl Struct`
appartient au type, suit sa visibilité et s’utilise sous la forme
`Struct::NOM`. L’initialiseur est un littéral entier, flottant ou booléen.
Un signe moins peut précéder un littéral numérique. Le compilateur vérifie
que le littéral correspond au type primitif déclaré et insère sa valeur à
chaque utilisation. Une constante n’a pas d’adresse propre.

### Closures

La liste de paramètres d'une closure est délimitée par des barres.
`||` ouvre une closure sans paramètre. Chaque paramètre indique explicitement
son type, comme dans `|x: i64|`. Ce marqueur rend la création d'une valeur exécutable
ultérieurement visible dans le code. Un bloc ordinaire `{ ... }` s'évalue
immédiatement. Entre deux opérandes, `||` conserve son sens de OU logique.
Le corps d'une closure est toujours un bloc délimité par des accolades.
Sa dernière expression fournit le résultat selon la sémantique des blocs.
Le type de retour peut être indiqué par `-> Type` après les barres.
En son absence, le compilateur l'infère à partir du corps. Tous les chemins
de retour, y compris les retours explicites et la valeur finale du bloc,
doivent produire le même type. Si un type est déclaré, chaque retour
doit correspondre à ce type.

Une closure est une instance d'un type concret généré pour son expression.
Ce type se comporte comme une structure qui contient un champ interne par
liaison extérieure utilisée. Son corps est la méthode exécutée par
`f(...)`, où `f` est une liaison nommée. Une expression
closure entre parenthèses peut aussi être appelée directement, comme
dans `(|x: i64| { x * 2 })(21)`. Les champs de capture sont initialisés
à la création de la closure.
Sans `move`, la création de la closure copie automatiquement les valeurs
primitives et les enums admissibles selon V3. La liaison extérieure reste disponible. Cette copie a
lieu une seule fois, à la création. Les autres captures par valeur exigent `move`.
Les captures existantes de références partagées gardent leur dépendance à la cible.

Le marqueur `move` s'applique à toute la closure. Il transfère les liaisons
extérieures utilisées dans ses champs, selon le sens de `move` à l'entrée
d'un bloc. Les sources non copiables deviennent inutilisables dès la déclaration.
Les captures de primitifs et d’enums admissibles sont copiées, même avec `move`,
et leur source reste disponible. La closure
prend en charge le nettoyage des valeurs transférées. La syntaxe de
capture ne prévoit pas de liste de modes individuels.

```rust
fn main() {
    let a: i64 = 10;
    let b: i64 = 20;
    let additionner = move || { a + b };
    print(additionner()); // 30
}
```

Sous `move`, une référence partagée est transférée dans le champ de
capture comme les autres valeurs. Après `let vue = &nombre;`, la
création de `move || { *vue }` rend la liaison extérieure `vue`
indisponible. La référence conserve sa cible.
Lorsqu'un champ contient une référence, la closure porte la dépendance de
ce champ à sa cible, comme une structure ordinaire. N4 exige que la cible
reste valide tant que la closure peut utiliser la référence, y compris
pendant son nettoyage si celui-ci en dépend. Déplacer la closure transmet
la référence et sa dépendance. Détruire la closure met fin à l'emprunt
porté par le champ selon les règles existantes.

En position de type, `fn(...) -> R` décrit la signature d’appel d’une
closure. Le compilateur conserve le type concret de son instance, ses champs
de capture et leurs dépendances. Le paramètre `f: fn(...) -> R` reçoit
l’instance par valeur selon les règles ordinaires de copie et de déplacement.
`f: &fn(...) -> R` et `f: &mut fn(...) -> R` reçoivent respectivement un
emprunt partagé et un emprunt mutable de l’instance, passé explicitement à
l’appel. Le préfixe d’emprunt porte sur la closure, et un emprunt écrit après
`->` porte sur le résultat.

L’appel `f(...)` utilise l’instance comme receveur. Un appel qui modifie ses
captures ou son état exige un accès mutable. Avec un passage par valeur,
`mut f: fn(...) -> R` rend mutable la liaison reçue. Avec un passage par
emprunt, `f: &mut fn(...) -> R` fournit cet accès. Le paramètre `mut f` ne
requiert aucune conversion au point d’appel. Les captures et l’appel
appliquent N1 à N8.

### Types d’éléments des pipelines

`Iter` emprunte la source par référence mutable sans unicité implicite. Chaque `Map` prend possession
de son prédécesseur. `collect(&mut destination)` consomme la chaîne et ajoute
les éléments au vecteur de destination.

Tout type admis comme contenu de `Option<T>` peut être produit par `next()` ou
par une transformation. Pour collecter les éléments, le vecteur de destination
doit accepter ce même type. Cela inclut les `usize` numériques, les références,
les agrégats et les valeurs possédées quand les règles ordinaires le permettent.
Le déplacement d’un élément à travers le pipeline conserve ses dépendances
et ses obligations de nettoyage. Les emprunts qui restent dans un élément
produit ou collecté continuent de suivre N4 et N5. Avancer de nouveau la source
exige notamment que cet accès soit compatible avec les emprunts encore actifs.

C’est le périmètre retenu pour les deux compilateurs. Le [rapport de
validation](cycles/CORE_COMPOSITION_CYCLE.md#iter-map-and-collect) décrit le
sous-ensemble implémenté et testé à ce jour.

## 12. UTF-8 et String retenus, support partiel

[UTF8_STRINGS.md](UTF8_STRINGS.md) fait partie des règles normatives : TX1–TX20
définissent les vues str, conversions explicites, indexation d'octets, String
fondé sur Vector<u8> et invariant UTF-8 lors des mutations. String n'est pas
structurellement Copy. Les itérateurs sont reportés. Les propositions non
arbitrées sont signalées. Les décisions suivantes sur Vector et String
sont consignées dans [FOUNDATIONS_AND_VECTORS.md](FOUNDATIONS_AND_VECTORS.md).

**TX23 — Chaînes inline bornées.** `String<N>`
possède une borne en octets connue à la compilation et un stockage inline fixe
avec métadonnées de longueur. `String` sans argument reste grandissant.
Voir TX23 dans [UTF8_STRINGS-fr.md](UTF8_STRINGS-fr.md).
La grammaire, corboc et la STD sont intégrés ; les preuves ciblées figurent
dans la matrice de vérification.

## 13. Fondamentaux, allocations typées et vecteurs

Voir [FOUNDATIONS_AND_VECTORS.md](FOUNDATIONS_AND_VECTORS.md) pour F1–F5,
H1–H3, VE1–VE6, GR1–GR2 et TX21–TX22. La matrice distingue les parties
exécutables des décisions qui restent à implémenter.

[HASH_MAP.md](HASH_MAP.md) consigne HM1–HM6 pour `HashMap`, avec ses
opérations, son stockage grandissant et le suivi des dépendances des entrées.

## 14. Inventaire historique du travail restant

La liste ci-dessous conserve les travaux identifiés lors de la conception
initiale. Plusieurs ont depuis été partiellement ou entièrement raccordés
dans un périmètre donné, notamment PR1, les contrats, les structures et UTF-8.
Elle ne constitue pas la checklist actuelle d'implémentation : consulter le
[README](../README.md) et la [matrice de vérification](VERIFICATION_MATRIX.md),
dont les cycles les plus récents précisent les écarts encore ouverts.

- Formaliser les effets des signatures, les origines des références retournées
  et le suivi des dépendances dans les structures mutables.
- Préciser le bilan des transferts conditionnels et la syntaxe compacte des
  retours/transferts dans tous les contextes.
- Retirer l'ancienne API `reset` selon PR1 lors de la prochaine passe demandée,
  puis migrer ses documents, exemples, contrats et tests sans affaiblir les
  invariants de durée de vie et de destruction.
- Formaliser les effets de `drop` et des destructeurs, notamment pour les
  groupes de dépendances, les cycles et les allocateurs déplacés.
- Définir les algorithmes de placement des deux data stacks et la
  configuration de leurs tailles au niveau du programme, selon G1–G12.
- Définir l'interface des allocateurs compatibles avec les garanties du langage.
- Définir la notation de source obligatoire pour `new`, aussi bien pour les
  data stacks que pour les allocateurs, conformément au principe I2.
- Définir les frontières avec le C non vérifié. Le backend C est conservé pour
  expérimenter ; les règles sont vérifiées avant génération du C.
- Implémenter et valider ultérieurement les règles async/multithread consignées,
  après résolution des interfaces encore ouvertes ; aucune modification du
  compilateur n'est demandée par la seule consignation de ces décisions.
- Implémenter et valider ultérieurement ST1–ST18/ME1–ME4 et leurs interactions
  avec le modèle mémoire existant, sans réintroduire les états partiels retirés.
- Implémenter et valider ultérieurement TX1–TX20 après clarification des points
  ouverts ; la consignation n'introduit aucun support exécutable de String.

Les parties non implémentées ne doivent pas être présentées comme déjà
vérifiées par le compilateur ou établies correctes par les tests existants.

## 15. Frontière avec le C

**FFI1 — Appel explicite au C.** Une fonction C externe se déclare avec
`extern "C"` et une signature. Tout appel à cette fonction se fait dans un
bloc `unsafe`. Corbo vérifie l'appel à partir de la signature déclarée.
Le bloc `unsafe` indique que le programmeur garantit que le code C respecte
le contrat de l'appel. Cette règle s'applique aussi aux signatures composées
uniquement de types numériques.

```rust
extern "C" fn identite(n: i32) -> i32;

fn main() {
    let n = unsafe { identite(7) };
    print(n);
}
```

**FFI2 — Signatures scalaires.** Dans le premier périmètre, une signature
`extern "C"` peut prendre et rendre les types scalaires `i32`, `i64`,
`u8`, `u16`, `u32`, `u64`, `f32`, `f64` et `bool`. Ces valeurs passent
par copie. Une fonction externe peut aussi ne rendre aucune valeur.
Les références, les allocations `A<T>` et les agrégats sont refusés
dans ces signatures.

**FFI3 — Flottants reçus du C.** Quand une fonction externe rend un
`f32` ou un `f64`, Corbo vérifie que la valeur est finie avant de la
remettre à l'appelant. Si le résultat est un NaN ou un infini de l'un ou
l'autre signe, le programme s'arrête avec un diagnostic. Un zéro signé
reste admis.

**FFI4 — Portée de `unsafe`.** L'autorisation d'appeler une fonction
`extern "C"` s'applique à l'emplacement de l'appel dans le bloc. Elle
ne se propage pas dans les fonctions appelées. Corbo vérifie dans le bloc
les types, les emprunts, les déplacements et les destructions selon les
règles ordinaires.

**FFI5 — Correspondance des scalaires.** Les arguments et résultats
`extern "C"` suivent la convention d'appel C de la cible. Les types
utilisés à cette frontière sont les suivants.

| Corbo | C |
| --- | --- |
| `i32`, `i64` | `int32_t`, `int64_t` |
| `u8`, `u16`, `u32`, `u64` | `uint8_t`, `uint16_t`, `uint32_t`, `uint64_t` |
| `bool` | `_Bool` |
| `f32`, `f64` | `float`, `double`, sur les cibles où ils correspondent à binary32 et binary64 |
| Aucun résultat | `void` |

Le compilateur adapte les représentations internes de Corbo au point
d'appel. La définition C doit correspondre à la déclaration externe.

**FFI6 — Build avec une source C.** La commande
`crust build main.crb --c-source identite.c -o programme` produit
l'objet Corbo avec le backend actif, fait compiler la source C fournie
par le compilateur C, puis lie les objets dans le même build. La liaison
résout les symboles nommés dans les déclarations `extern "C"`. Un
symbole externe introuvable fait échouer le build à la liaison.

## Réplication structurelle dans les tableaux fixes

Dans `[valeur; N]`, l’initialiseur est évalué une fois. Quand `N > 1`,
sa valeur doit être primitive ou être une structure sans destructeur
personnalisé dont tous les champs sont réplicables selon cette même règle.
Chaque case reçoit une valeur indépendante. Les règles de `copy()` restent
les mêmes.

## Arguments du processus

Le point d’entrée reste `fn main()`. `std::env::args()` retourne
`Result<&[&str], ArgsError>` sans le nom de l’exécutable. Le stockage des
arguments est immuable et vit aussi longtemps que le processus.
Un argument Unicode invalide produit `InvalidUtf8`. Un échec
d’acquisition des arguments produit `Unavailable`.

## Déplacement entre threads (TR1)

Voir [les restrictions de thread](THREAD_TRANSFER-fr.md).

## Mutation interne de confiance et mutex

L'acquisition publique utilise `lock(&self)`, dans `std::sync::Mutex<T>` et
`std::sync::asyn::Mutex<T>`. L'implémentation peut créer un emprunt mutable d'un champ
à travers une référence partagée dans `@unchecked`, après acquisition du verrou.
L'emprunt conserve sa provenance et ses vérifications de durée de vie. Ce passage
ne génère aucune synchronisation : l'implémenteur doit respecter le contrat de
verrouillage. Le même emprunt hors du bloc de confiance reste refusé.
Les adresses natives ne peuvent toujours pas sortir de leur bloc unchecked.
Voir [l'API synchrone/asynchrone](ASYNC_API-fr.md).

## Alias de type Self

Dans un bloc `impl`, `Self` désigne le type implémenté avec ses arguments
génériques. Il peut apparaître dans les signatures (`&Self`, `self: Self`),
les constructions `Self { ... }` et les appels `Self::new(...)`. Il n’introduit
aucune conversion ni règle de copie ou de move. Hors d’un `impl`, `Self` est
refusé ; `Self<T>` est également refusé car les arguments sont déjà fixés
par l’implémentation. `self` reste le nom de la liaison receveur.

## Méthodes de référence et déréférencement

[La résolution des méthodes](DEREFERENCE-fr.md) précise la priorité des méthodes explicites, les emprunts de la valeur de A<T> et le déréférencement statique des objets. Les règles de possession, de durée de vie et de verrou restent inchangées.

## Restriction actuelle des emprunts mutables — 24 novembre 2026

Un seul emprunt mutable actif par place qui se chevauche. La dernière utilisation
peut terminer un emprunt ; les champs prouvés disjoints restent indépendants.
Cette décision remplace les anciennes clauses de coexistence dans ce document.
Voir [les accès mutables](MUTABLE_ACCESS-fr.md).

## Ordre des octets de la cible

`target.endian` est disponible dans `#(if: ...)` avec les valeurs `"little"` et
`"big"`. La valeur vient de la cible configurée à la construction du compilateur.
La sélection précède la résolution des imports, comme les autres propriétés
`target`. Elle ne produit aucun test d’ordre des octets dans le programme final.
