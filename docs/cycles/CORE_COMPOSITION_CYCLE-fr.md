[English](CORE_COMPOSITION_CYCLE.md)

# Cycle d’intégration des compositions du core

## Comportements intégrés

- Une closure conserve la provenance d’une référence scalaire locale ou de
  pool. Une capture partagée copie la référence. Une capture scalaire mutable
  par `move` invalide la liaison d’origine. Une closure peut être passée à une
  fonction async spécialisée et conserver un emprunt partagé à travers `yield`.
- Un wrapper synchrone `branch` peut retourner un handle choisi entre plusieurs
  lancements. Pour les branches scalaires reconnues, le contrat public relaie
  la preuve qui permet au vérificateur d’accepter l’abandon. Le runtime recycle
  le slot à la terminaison de la tâche, pendant que le contexte est actif.
- Un contrat de fonction peut relayer des insertions de références scalaires
  partagées dans une `HashMap` par clé constante. À l’appel, le vérificateur
  met à jour les dépendances des entrées et conserve les alternatives des
  écritures conditionnelles.
- Un ticket qui porte un verrou reste actif dans un champ propriétaire
  retourné par une fonction, ou dans le résultat de `Vector.pop()`. Le bras
  `Some` transfère le ticket et le bras `None` éteint l’option vide.

## Vérification ciblée

La passe à `-O0` a terminé avec 37 tests réussis. La passe à `-O2` a
terminé avec 101 tests réussis et couvre en plus la capacité async, les
obligations des handles, les options de vecteur, le typage numérique et
les ponts sync/async. Les témoins natifs de ces modules utilisent UBSan. Les cas de refus portent notamment sur
une écriture avant la fin d’un emprunt capturé, une dépendance HashMap qui
échapperait à sa cible et une seconde prise du même verrou pendant la vie
du ticket. Un témoin C attend que le pool de tâches redevienne vide avant la
fermeture du contexte.

## Limites observées

- Le suivi de `branch` couvre les corps synchrones reconnus et la preuve
  scalaire. La généralisation de N4, la capacité avec des abandons répétés
  et la distinction `Handle`/`AsyncHandle` dans les signatures restent ouvertes.
- Les captures mutables non scalaires, la composition entre paramètres
  closure et contrats de type, et la vérification des gabarits inutilisés à
  signature non scalaire restent ouvertes.
- Les autres effets sur des entrées HashMap dépendantes, les opérations
  directement en async, les références nominales par entrée et l’acquisition
  directe d’un verrou en async restent à raccorder.
- `SelectGroup` est reporté selon la décision de périmètre. Ce cycle couvre
  les régressions ciblées et laisse l’audit indépendant distinct.

## Suivi du typage des handles

RT4 confirme que `spawn` et `thread` retournent `Handle<R>` depuis les deux
contextes. Le profil numérique conserve la famille du handle lancé lors
d'un déplacement, d'un résultat conditionnel et d'un `break`. Les branches
qui mélangent les familles sont refusées. Le profil historique conserve
son annotation `Handle` pour `spawn_blocking`.

La preuve scalaire peut traverser plusieurs wrappers annotés `branch`.
Le lien doit aboutir à un lancement connu. Un relais sans contrat connu
est refusé. Le transport d'un `AsyncHandle` via une signature et le calcul
de capacité avec des abandons répétés restent ouverts.

La régression ciblée de ce suivi passe à `-O0` (8 tests) et à `-O2`
(24 tests, dont les contrats publics et les obligations des handles). Les
témoins C utilisent UBSan. Les vérifications négatives couvrent notamment
le mélange de familles dans un `if`, une annotation incompatible après
transfert, et l'absence d'un contrat sur le lanceur relayé.

## Composition entre closures et contrats de type

Dans une unité avec contrats de type, le compilateur résout les appels
structurels avant de spécialiser les closures et enregistre ensuite leurs
structures générées. Une closure appelée plusieurs fois peut ainsi transmettre
sa référence partagée à une fonction à contrat de type. La capture d'une
valeur non `Copy` exige toujours `move`.

La passe à `-O0` couvre 15 tests sur les closures et contrats de type.
La passe à `-O2` couvre 31 tests avec les handles et les obligations de tâches. Les autres formes de capture et les
gabarits inutilisés à signature non scalaire restent ouverts.

## Paramètres AsyncHandle et tableaux indépendants

Le transfert d'un `AsyncHandle<R>` autonome à un paramètre d'une fonction
async consomme la liaison de l'appelant. Le handle est stocké par valeur
dans l'état de la tâche et peut être attendu par le receveur. Si cette tâche
est détruite avant son premier poll, son destructeur reprend le nettoyage
du handle. Le cas de lancement échoué conserve l'erreur jusqu'à l'attente.

La preuve d'autonomie admet aussi les tableaux numériques fixes capturés
par valeur. Un tableau emprunté garde l'obligation d'attente. La capacité
sous abandons répétés reste ouverte, comme les paramètres de handles à
dépendances et les retours de handles depuis des fonctions async.

La suite ciblée passe à `-O0` (10 tests) et à `-O2` (66 tests). Le témoin
d'`AsyncHandle` couvre le succès, `LaunchFailed` injecté au lancement
bloquant et la destruction du receveur inactif. Le vérificateur refuse le
mauvais type de handle, la seconde consommation et la capture d'un handle
avec emprunt dans ce périmètre.


## Capacité des boucles et lecture de HashMap par contrat

Quand une boucle a un chemin de reprise, le compilateur compare les pools
dans lesquels elle peut créer et abandonner une tâche. L'intersection
exige une capacité explicite. Les effets des auxiliaires synchrones
traversent leur contrat, et le contrat `branch` conserve les pools
possibles du handle retourné. Un bloc de boucle qui sort immédiatement
par `break` conserve la borne ordinaire.

Les essais couvrent les boucles sync et async, les appels directs et
relayés, le diagnostic sans directive et l'exécution avec quatre slots.
La passe ciblée a réussi à `-O2` avec 67 tests. Les appels indirects
via une tâche async et les retours d'AsyncHandle restent ouverts.

Un paramètre `&HashMap<i64, &i64>` permet maintenant de lire une entrée
et de retourner sa valeur scalaire. Les deux entrées du compilateur
refusent la mutation à travers le paramètre partagé et l'écriture de la
cible tant que la table conserve l'emprunt. La passe HashMap et lock a
réussi à `-O2` avec 20 tests, témoins natifs sous UBSan.

### Relais de capacité dans les tâches async

Le vérificateur suit les créations et abandons à travers les tâches
intermédiaires et leurs appels synchrones. Un wrapper `branch` appelé
en async conserve les pools possibles du handle. Le calcul est
conservateur et peut inclure une tâche créée dont l'exécution effective
n'est pas démontrée.

Le test ciblé passe à `-O0`. Les 36 tests à `-O2` couvrent les capacités,
les contrats publics et les obligations des handles. Les témoins natifs
utilisent UBSan. Les retours d'AsyncHandle et leurs dépendances restent ouverts.


### Signatures nominales des closures

Le compilateur vérifie les corps inutilisés dont le paramètre closure
reçoit une structure par emprunt ou retourne une structure à champs
numériques ou booléens. Le type nominal du résultat est traité comme
une valeur propriétaire. La vérification couvre le refus d'un argument
incompatible, le refus d'un champ inconnu dans le résultat et l'exécution
native du retour nominal. 17 tests passent à `-O2` sur les closures et
les contrats de type, avec UBSan pour les témoins natifs.

Le témoin C minimal avec `cc -fsanitize=address -g` compile. Son
exécution dépasse encore le délai de cinq secondes sur cette machine.
La case ASan reste ouverte.


### Capture mutable d'une structure

Une closure réutilisable peut déplacer une référence mutable nominale
dans un champ synthétique. Le déplacement invalide la liaison d'origine.
L'appel par emprunt partagé projette un réemprunt en lecture qui conserve
la réservation du champ. Le témoin exécute deux lectures, refuse la
réutilisation de la liaison et la mutation concurrente de la cible, puis
écrit dans la cible après destruction de la closure. Test ciblé à `-O0`
et 28 tests à `-O2` sur les closures, contrats de type et verrous.

### Emprunt retourné par une closure

Le corps inutilisé d'une fonction recevant une closure est vérifié
avec une implémentation témoin quand le résultat emprunté correspond à
un paramètre de même type unique. La spécialisation réelle utilise le
corps de la closure. Le test natif vérifie la lecture à travers un relais,
le refus d'une écriture avant la dernière lecture et l'écriture après.
29 tests passent à `-O2` avec UBSan sur les témoins natifs. Le retour
d'une référence scalaire capturée reste refusé lors du calcul de
provenance du champ synthétique.

### Provenance d'une référence scalaire capturée

Le contrat classe le résultat issu d'un champ scalaire partagé de closure
comme un emprunt sur le stockage de la cible. Le témoin lit après destruction
de la closure et écrit après la dernière lecture. Le vérificateur refuse
l'écriture anticipée et le retour d'une cible locale depuis une fonction.
Deux tests passent à `-O0` et 30 à `-O2`, avec UBSan sur les témoins natifs.

### Vue partagée issue d'une capture exclusive

Les contrats des closures réutilisables représentent la projection d'une
capture exclusive comme un emprunt partagé. Le résultat scalaire suit la
cible. Le résultat nominal conserve une réservation sur le champ de la
closure et empêche sa destruction avant la dernière lecture. Les témoins
refusent l'écriture anticipée et permettent de modifier la cible après
la fin de l'emprunt. Le test ciblé passe à `-O0` et 31 tests passent à
`-O2`, avec UBSan sur les témoins natifs.

### Vue nominale après destruction de la closure

La provenance du réemprunt partagé conserve l'identité de la capacité
de champ. Sa durée de vie suit la cible. Le témoin lit après destruction
de la closure, y compris en passant par le retour d'une fonction relais.
Le vérificateur refuse l'écriture sur la cible avant la dernière lecture
et l'accès direct par le porteur pendant la capture exclusive.

Le test ciblé passe à `-O0`. À `-O2`, 41 tests passent sur les closures,
contrats de type, verrous et cas du core, ainsi que 13 sur les emprunts
et retours de structures. Les témoins natifs utilisent UBSan.

### Références nominales partagées en HashMap

Une table locale stocke une référence partagée à une allocation nominale.
La dépendance est conservée par clé, y compris pendant le transfert du
résultat de retrait. Le témoin lit deux fois la cible, retire une entrée,
puis modifie sa cible. Le vérificateur refuse la mutation de l'autre
cible et le stockage d'une référence qui survivrait à sa cible.
Les projections en ligne, références nominales mutables et contrats
interprocéduraux pour ces tables restent ouverts. Le test ciblé passe
à `-O0` et 39 tests passent à `-O2`, avec UBSan sur les témoins natifs.

### Projection partagée en ligne dans une HashMap

Les entrées empruntant une structure utilisent une vue C qui transporte
la racine et le décalage. Le résultat d'un retrait conserve la projection.
Le vérificateur permet l'écriture du champ frère, refuse l'écriture du
champ ciblé pendant l'emprunt et maintient cette protection après retrait
jusqu'à la dernière lecture. Deux tests ciblés passent à `-O0` et 45
tests passent à `-O2`, avec UBSan sur les témoins natifs.

### Transfert d'une référence nominale mutable en HashMap

La table consomme la liaison mutable à l'insertion et en conserve
l'exclusivité par entrée et chemin de projection. Le retrait restitue
la référence mutable, avec la racine et le décalage pour un champ en
ligne. Le témoin rejette l'accès via l'ancienne liaison et via la cible
durant le prêt, autorise un champ frère et écrit via la référence retirée.
Un test passe à `-O0` et 38 à `-O2`, avec UBSan sur les témoins C.
Le réemprunt depuis une case et les signatures de fonctions restent ouverts.

### Analyse syntaxique des annotations branch

`Parser.parse_syntax()` livre l'arbre avant élaboration. L'annotation
`branch` reconnaît la forme nue, `join=result.join()` et
`join=result.await`. La vérification existante de la disponibilité de
l'attente et de la provenance est effectuée ensuite par le compilateur.
Les deux tests syntaxiques et les dix tests de régression du core passent.
Le module natif complet comporte un témoin sémantique dont deux
sous-cas échouent aussi quand le nouveau contrôle d'annotation est
neutralisé. Le programme sans annotation qui abandonne une tâche native
autonome est accepté alors que ces sous-cas attendent un refus.

### Analyse syntaxique des contrats de type empilés

Le parseur conserve l'ordre des annotations, les déclarations libres
et la présence de `with` dans l'arbre syntaxique. Le témoin utilise la
signature de `spawn`, puis supprime le marqueur de type libre, le
paramètre de type ou le point-virgule d'une exigence pour tester les
refus. Cinq tests d'annotations et dix régressions du core passent.
L'élaboration garde son périmètre d'un contrat avec `with`.

### Chemins de types qualifiés

Le parseur conserve les segments `::` d'un nom de type et refuse un
segment absent ou numérique. Le témoin combine une signature de closure,
une HashMap et un AsyncHandle. Les sept tests ciblés d'annotations et de
syntaxe passent. La résolution des noms qualifiés reste distincte de
l'analyse syntaxique.

### Directives de taille au parseur

Le profil numérique du core exige le séparateur `:` après `directive`.
Le témoin syntaxique couvre les facteurs binaires K, M et G, les capacités
qualifiées, et refuse la virgule, Ki, zéro et un littéral hexadécimal
pour une taille de région. La virgule reste admise dans le profil
historique. Les 16 tests des modules d'annotations de région et de
capacité passent.

### Séparateurs de bras de match

Le profil du core exige un bras au minimum et une virgule entre les
bras. La virgule finale reste facultative. Le témoin syntaxique couvre
les formes enum et Option. La suite ciblée compte 42 tests réussis avec
les régressions du core, de HashMap et des closures. Le contrôle
d'exhaustivité déjà présent dans le parseur de résultats reste en place.

### Motifs de match dans l'arbre syntaxique

Le point d'entrée syntaxique du core conserve les bras dans l'ordre,
y compris les motifs imbriqués, le joker, l'unité et les motifs de
champs. Les validations d'exhaustivité et les traductions de résultats
builtin restent sur le chemin de compilation. Les témoins syntaxiques
refusent un argument de motif absent, un champ sans liaison et un chemin
incomplet. 17 tests ciblés passent.

### Arguments de types et listes de closures

Le parseur seul lit les arguments génériques empruntés de Pool, A et
Mutex conformément à la production `type`. Il distingue la virgule
finale admise dans un littéral closure de la liste de types d'une
signature de closure. Le parcours d'élaboration existant conserve
les mêmes formes de types prises en charge. 34 tests ciblés passent.

### Tranches empruntées dans les types

Le parseur seul lit les tranches avec un type d'élément arbitraire
sous `&` ou `&mut`. Il refuse une tranche par valeur, y compris dans
un argument générique ou un type de closure. Les types de tranches
pris en charge par l'élaboration restent les mêmes. Les 35 tests
ciblés passent.

### Signatures AsyncHandle et littéraux annotés

Le point d'entrée syntaxique conserve le type AsyncHandle emprunté dans
une signature et la valeur entière annotée u8. Le chemin de compilation
applique les restrictions existantes sur le passage d'un AsyncHandle et
la borne du littéral u8. Les 18 tests ciblés passent.

### Déclarations nominales et annotations lock

Le parseur réutilise la lecture des noms qualifiés pour les types,
les blocs impl, les motifs et les capacités. Les témoins syntaxiques
couvrent un impl qualifié avec les deux annotations lock, refusent
un chemin tronqué et un contrat lock mal formé. Une enum vide est
refusée au parseur du core. La suite ciblée de 25 tests passe, puis
les deux tests syntaxiques ont été rejoués après ajout du refus d'une
enum vide dans un fichier sans main.

### Chemins de valeurs qualifiés

Le point d'entrée syntaxique conserve les chemins de valeurs qualifiés
dans les liaisons, appels autonomes et attentes async. Un segment absent,
numérique ou mal séparé est refusé. Le chemin de compilation reste inchangé.
21 tests ciblés passent. Le test syntaxique a ensuite été rejoué avec le
refus de `runtime::select_group()` dans le périmètre actuel.

### Littéraux numériques et bornes

Le parseur seul conserve le lexème d'un entier trop grand pour le profil,
y compris avec un signe négatif. Le parcours de compilation conserve son
contrôle de borne. Les témoins vérifient les décimaux sans exposant,
l'indexation par plage et le refus des comparaisons chaînées sans
parenthèses. Les 22 tests ciblés passent.

### En-têtes move et blocs de capture

L'analyse syntaxique autorise plusieurs entrées move en début de bloc,
y compris dans un bloc de thread. Elle refuse une entrée nommée après
une instruction ordinaire et conserve un bloc move avec valeur finale
avant le contrôle du receveur. Les onze tests ciblés passent.

### Expression finale de bloc

Le parseur seul reconnaît une expression finale dans un bloc
d'instruction ou une fonction. Il conserve l'expression dans l'arbre
sans la convertir en return implicite. Le témoin couvre les blocs
imbriqués, une fonction à retour annoté et les mots-clés de contrôle
privés du point-virgule requis. Les 23 tests ciblés passent.

### Expressions employées comme instructions

Le parseur seul conserve une expression suivie d'un point-virgule comme
instruction, y compris une expression numérique ou parenthésée. Il la
distingue d'une expression finale sans point-virgule et refuse deux
instructions sans séparateur. 35 tests ciblés passent.

### Places d'affectation composées

L'arbre syntaxique conserve les déréférencements et l'ordre des champs
et indices d'une place. Les témoins couvrent l'affectation simple et
composée et refusent un appel, une plage, un indice vide ou trois
déréférencements comme place. Le chemin de compilation reste inchangé.
35 tests ciblés passent.

### Chaînes de suffixes en lecture

Le parseur seul conserve l'ordre des champs, indices et appels de
méthode sur une expression composée. Il refuse un champ manquant,
des arguments mal séparés et un indice vide. Le chemin de compilation
conserve ses formes prises en charge. 35 tests ciblés passent.

### Initialisation de pool sur un receveur composé

Le point d'entrée syntaxique reconnaît le suffixe new sur un receveur
composé. Il conserve les champs nommés dans l'ordre et distingue la
forme vide et la forme à une expression. Les formes mixtes et les
expressions positionnelles multiples sont refusées. Le chemin de
compilation conserve ses formes d'initialisation. 34 tests passent.

### Niveau racine du programme

Le point d'entrée syntaxique suit la production programme. Il accepte
les déclarations nominales, les impl, les fonctions synchrones, async et
externes et la directive de capacité. Une instruction au niveau racine
ou une déclaration dans un bloc est refusée. Le mode script de
l'ancien parcours est toujours exercé. 32 tests ciblés passent.

### Directives de région sur les productions de bloc

Le parseur seul accepte la directive avant un corps de fonction ou un
bloc de contrôle et conserve sa taille dans l'arbre. Le corps d'une
closure exige directement les accolades, conformément à la production
bloc_delimite. Les témoins couvrent un corps, une branche if et un
bras de match, puis refusent une directive sans bloc. 34 tests passent.

### Conditionnelle à branche else facultative

Le parseur seul accepte l'absence de else conformément à la production
conditionnelle, y compris dans un receveur ou après else if. Le parcours
de compilation conserve le diagnostic qui exige une branche else pour
un résultat. Un else sans bloc ni conditionnelle est refusé au parseur.
25 tests ciblés passent.

### Déréférencement unaire

Le parseur seul lit les déréférencements récursifs et les opérandes
parenthésés ou postfixés. Le témoin vérifie la priorité de l'indice
et de l'addition ainsi que les refus d'un opérande manquant ou mal
formé. Le chemin de compilation reste inchangé. 40 tests passent.

### Déclarations et appels externes

Le point d'entrée syntaxique représente une déclaration externe sans
corps synthétique et lit son appel comme un appel ordinaire. Il accepte
la virgule finale et refuse une ABI autre que C, un paramètre emprunté
ou une déclaration munie d'un corps. Le contrôle unsafe reste sur le
parcours de compilation. 17 tests ciblés passent.

### Profil du point d'entrée syntaxique

Le point d'entrée syntaxique sélectionne le profil du core même quand
le source ne contient aucun type numérique explicite. Il refuse les
anciennes flèches de transfert et reconnaît la flèche des types de
retour et les entrées move. Les 48 tests ciblés passent. Le témoin a
été rejoué sans annotation numérique explicite pour exercer le cas
où l'heuristique historique choisit l'autre profil.

### Expression unité et appel immédiat de closure

Le point d'entrée syntaxique distingue `()` d'une expression
parenthésée et le reconnaît comme argument. Il vérifie aussi l'appel
immédiat d'un littéral closure parenthésé avec virgule finale.
Les parenthèses mal formées et l'application de l'unité sont refusées.
Le parcours de compilation reste inchangé. 50 tests ciblés passent.

### Chemins qualifiés des types builtin

Le parseur seul conserve les appels qualifiés et les variantes d'erreur
avant la résolution du membre et le contrôle de l'arité. Il refuse un
chemin tronqué ou dont la forme ne correspond pas à l'espace de noms
réservé. Le parcours de compilation conserve les diagnostics existants.
26 tests ciblés passent.

### Receveur de signature de méthode

Le parseur seul exige le receveur self en première position. Les
témoins couvrent &self, &mut self et mut self avec type explicite.
Une méthode sans receveur, un self tardif et un self en paramètre
d'une fonction libre sont refusés. 25 tests ciblés passent.

### Constructeur d'enum sans champs

Le parseur seul représente une variante d'enum déclarée sans accolades
comme un constructeur. Le témoin couvre le constructeur avec champs
et distingue l'accès à un champ sur une variable. 34 tests ciblés passent.
Le test de syntaxe a ensuite été rejoué avec un constructeur sans
champs comme sujet de match.

### Tailles dans les tableaux et les pools

Le parseur seul reconnaît les tailles entières non signées des types
tableau, répétitions et constructeurs de pool. Il conserve une longueur
hors représentation sans conversion prématurée, et sépare une capacité
nulle du contrôle qui la refuse à la compilation. 35 tests ciblés passent.

### Valeurs des directives de capacité async

Le parseur seul conserve une capacité entière, y compris zéro ou
une valeur hors représentation, et refuse une valeur signée ou
décimale. Les contrôles de bornes et de positivité restent sur le
parcours de compilation. Les 18 tests ciblés passent.

### Taille de région hors représentation

Le parseur seul conserve une taille décimale positive avec K, M ou G
même si elle dépasse la représentation du compilateur. Il conserve
le refus de zéro. La compilation garde sa borne existante. Les
19 tests ciblés passent.

### Identifiants dans les déclarations

Le parseur seul refuse les mots réservés aux positions de déclaration.
Le témoin accepte `self` comme receveur de méthode et `_` dans un
motif. Les 36 tests ciblés passent. Ce contrôle couvre les déclarations
et les exceptions exercées par le témoin.

### Initialisation de pool et types parenthésés

Le parseur seul accepte `points.new(data::value)` et refuse un chemin
pointé comme nom de champ d'initialisation. En position de type, il
accepte `()` et refuse la syntaxe historique de paire de tranches.
Les 36 tests ciblés passent. Le parcours historique conserve ses formes.

### Type du constructeur de pool et motifs d’enum

Le parseur seul reconnaît un type d’emprunt complet dans `pool<type>(taille)`.
Dans un motif d’enum, il exige des identifiants ordinaires pour la variante,
les champs et les liaisons, avec `_` pour ignorer un champ. Les 39 tests
ciblés passent. L’admissibilité du type de pool et les contraintes de match
relèvent du vérificateur.

### Syntaxe des contrats de type et de branche

Le parseur seul conserve les alternatives empruntées et les méthodes d’un
contrat avant de contrôler la distinction des noms et le type des receveurs.
Il exige au moins une méthode et refuse les noms réservés dans les paramètres
de type et après `result.` en position de nom de méthode. Les 39 tests ciblés
passent. Un témoin confirme le refus de noms identiques sur le parcours de
compilation.

### Syntaxe des lancements

`parse_syntax()` conserve l’expression passée à `spawn` ou
`spawn_blocking` avant l’analyse du type ou du contexte. L’EBNF exige une
expression unique, sans virgule finale. Les 41 tests ciblés passent.
La suite élargie à 51 tests signale deux assertions en échec dans
`test_native_blocks_enforce_wait_before_drop_or_return`. `verify_program`
et `compile_source` acceptent un thread autonome qui retourne `7` sans
attente, tandis que le témoin exige un refus. Ce programme ne contient
aucun appel à `spawn` ou `spawn_blocking`. Le témoin est à réconcilier
avec RT7 lors de la passe de vérification.

### Blocs de thread et suspensions

Le parseur seul reconnaît `yield;` et `.await` sans décider si le contexte
permet une suspension. Il conserve les captures nommées répétées dans
un bloc de thread et refuse les noms réservés. Les 42 tests ciblés passent,
dont les refus de suspension dans un bloc de thread sur le parcours de
compilation. La divergence du témoin de thread autonome reste ouverte.

### Appels de méthodes et plages

Le parseur seul conserve les arguments d’un appel ordinaire même quand
l’arité serait invalide pour une méthode intégrée. L’EBNF décrit maintenant
la notation `try_slice(début..fin)` déjà consignée pour les chaînes UTF-8.
Les 41 tests ciblés passent. Ils couvrent le parsing et les régressions
directement liées aux appels, sans nouvelle vérification d’arité.

### Constructeurs intégrés

Le parseur seul exige une expression unique sans virgule finale dans
`Mutex::new` et `AsyncMutex::new`. Il refuse la construction préfixée
`new(source) Int(...)`. `stack(...)` et `allocator(...)` suivent la syntaxe
des appels ordinaires à ce stade. Le témoin couvre aussi la construction
de HashMap et la syntaxe de son type de clé. Les 42 tests ciblés passent.

### Chemins qualifiés et types intégrés

Le parseur seul refuse les noms réservés dans les segments ordinaires d’un
chemin qualifié. Les types intégrés suivent leurs productions dédiées. `A`
exige son argument de type, `Execution<T>` reste historique et
`runtime::Future` reste expérimental. Les 44 tests ciblés passent.

### Emprunt d’une découpe

Le parseur seul conserve l’opérateur `&mut` et son opérande dans
`&mut text[1..3]`. Une découpe sans indice ni séparateur `..` est refusée.
Le parcours de compilation conserve son diagnostic de mutabilité. Les
44 tests ciblés passent.

### Cibles d’affectation

Le parseur seul utilise la production `place` pour les affectations simples
et composées. Il accepte `self.total += 1` et `total %= 2`, et refuse des
cibles comme `bool` ou `table._`. Les 45 tests ciblés passent. La validité
des accès et la mutabilité de la cible restent des contrôles de compilation.

### Formes bloc en position finale

Le parseur seul conserve les blocs simples, `move`, `unsafe`, `if`,
`match` et `loop` comme résultats lorsqu’ils terminent le bloc sans
point-virgule. Une forme bloc suivie d’une instruction peut rester une
instruction. Les 46 tests ciblés passent. Les assertions sur la forme de
l’arbre ont été mises à jour pour les `match` terminaux.

### Accolades vides après une variante

Le parseur seul reconnaît `if Choice.First {} else {}` et
`while Choice.First {} {}`. Si l’interprétation des premières accolades
comme initialisation laisse la condition sans bloc, le parseur reprend
ces accolades comme bloc. Quand un autre bloc suit, il conserve la
première paire comme initialisation. Les 47 tests ciblés passent.

### Chemins de valeurs et champs

Le parseur seul reconnaît `self.champ`, `i64::try_from(...)` et
`runtime::Error::LaunchFailed`, et refuse `self::champ`, `packet._`
et les mots réservés en position de valeur. Les anciens appels
`runtime::select`, `runtime::start_poller` et `runtime::set_scheduler`
sont hors du périmètre syntaxique de cette passe. Les 48 tests ciblés passent.

### Chemins de valeurs dans les motifs

Le parseur seul partage la lecture des chemins intégrés entre motifs et
expressions. Un motif reconnaît `Err(runtime::Error::LaunchFailed)` et
`network::Ready(_)`. Les chemins incomplets et les segments réservés
sont refusés. Les 49 tests ciblés passent.

### Type cible d’une conversion

Le parseur seul reconnaît la production `type` complète après `as`,
y compris `&mut [network::Packet]`. Les conversions successives se
rattachent avant l’addition. Un type mal formé est refusé. Les 61 tests
ciblés passent, dont la suite numérique avec les contrôles existants.

### Déclarations du point d’entrée

Le parseur seul reconnaît les déclarations externe et async nommées
`main`. La déclaration externe exige le point-virgule prévu par l’EBNF.
La compilation conserve le contrôle d’un point d’entrée Crust synchrone.
Les 78 tests ciblés et d’intégration passent.

### Nombre de directives de région par bloc

Le parseur seul refuse deux directives de région sur le même bloc,
en position d’expression ou après `move`. Les blocs imbriqués peuvent
chacun porter une directive. Deux assertions de la suite de croissance
ont été ajustées pour lire les annotations dans l’arbre des expressions
terminales. Les 57 tests ciblés passent après cet ajustement.

### Liaisons et déclarations héritées dans un bloc

Le parseur seul refuse `let (mut left, mut right) = split();` et
`type feature` dans un bloc du core. Il reconnaît un import nommé suivi
d’une liaison de closure `move`. Les 58 tests ciblés passent. La suite
élargie à 80 tests relève un échec historique : `test_declaration_storage_and_signature_rejections`
attend le refus de `type feature Plain {fn a(self);}` sur le parcours de
compilation historique, qui l’accepte. Cette passe ne modifie pas ce parcours.

### Séparateur de chemin contigu

Le parseur seul reconnaît `Option<A<network::Packet>>=value` et refuse
un séparateur `::` scindé par un espace, un saut de ligne ou un commentaire.
La même suite confirme que ces caractères restent acceptés dans une chaîne.
Les 73 tests ciblés passent.

### Vérification syntaxique en ligne de commande

`check --syntax-only` appelle le parseur du core. Le témoin `yield;`
passe cette commande et le `check` ordinaire le refuse dans un corps
synchrone. Sans point-virgule, le parseur refuse le témoin. L’option est
refusée avec `emit-c`. Les deux modes acceptent `let_mutability.crust`
et les 50 tests ciblés passent.

### Nom syntaxique du primitif i32

L’arbre du parseur seul conserve `i32`, y compris dans une signature
externe et dans `HashMap<i32, &i32>`. La clé historique `Int` est
refusée dans la syntaxe d’une HashMap du core. Le parcours de compilation
conserve la représentation ABI existante. Les 74 tests ciblés passent.

### Types dans les signatures

Le parseur seul conserve le type complet `A<i32>` dans les paramètres et
le résultat, ainsi que `bool`, `&[u8]` et `runtime::AsyncHandle<i64>` dans
une signature async. L’abaissement des signatures et l’enregistrement des
types liés restent sur le parcours de compilation. Les 76 tests ciblés passent.

### Reprise après une expression refusée

Le parseur seul pouvait accepter `bool();`, `runtime();` ou `bool` en
fin de bloc via les productions historiques après le refus de l’expression.
Ces formes sont désormais refusées. Les 63 tests ciblés passent.

### Appel de méthode après un nom d’enum

Le parseur seul reconnaît `Choice.read()` comme appel de méthode et
`Choice.await` comme expression d’attente, y compris lorsqu’un enum
`Choice` est déclaré. Les 62 tests ciblés passent. La résolution de la
liaison et du membre relève de la vérification.

### Bloc vide suivi d’un opérateur ou d’un suffixe

Le parseur seul reconnaît `if Choice.First {} + 1` et
`if Choice.First {}.read()` en rattachant la suite au `if`. Si un autre
bloc suit, comme dans `if Choice.First {} == 1 {}`, les premières
accolades restent une initialisation de variante. Les 64 tests ciblés passent.

### Receveur en expression et périmètre de SL1

L’EBNF exprime directement que `self` est une valeur et une base
d’affectation. Le parseur accepte `self.champ` et refuse `self()`.
Les deux productions cibles de SelectGroup portent la mention du report.
Les 54 tests ciblés passent.

### Programme public de démonstration

`examples/main.crust` utilise `memory.new(Message.Value { ... })`,
la forme du core pour construire une variante dans un pool. Les commandes
`check --syntax-only`, `check` et `run` passent. L’exécution produit `42`
et le témoin existant confirme la trace de destruction et de récupération.
Les 55 tests ciblés passent. Les autres exemples historiques restent à examiner
selon les invariants qu’ils exercent.

### Exemple de retours conditionnels

`conditional_returns.crust` utilise `Pool<i32>`, `A<i32>` et `drop`.
`check --syntax-only`, `check` et `run` passent. L’oracle d’exécution
vérifie les résultats `10` et `20`, quatre adresses identiques et la
destruction suivie de la récupération de chaque valeur. Le témoin
`pool_requirements.crust` garde `Allocator` pour montrer l’inférence
historique. La commande `effects` confirme que `relay` relaie la même
exigence de pool qu’`inspect`.

### Exemples de retour d’un objet contenant un emprunt

Les deux exemples utilisent `A<View>`, `views.new(...)` et `data.vref()`.
Les deux passent `check --syntax-only`. `run` affiche `View.Item(42)`
pour le relais valide. `check` refuse le retour de l’objet qui emprunte
une cible locale avec le diagnostic de durabilité dans le scope parent.

### Appels ordinaires portant le nom `try_slice`

Le parseur seul distingue `try_slice(..2)` d’un appel ordinaire tel que
`try_slice()` ou `try_slice(1, 2)`. Le premier argument est lu une fois.
Les 54 tests ciblés passent. La résolution de méthode reste au stade de
la compilation.

### Rejeu transversal du parseur seul

Les 57 méthodes appelant directement `parse_syntax` passent dans les
suites déplacements, contrats de type, numérique, croissance et thread.
Elles exercent les déclarations, types, blocs, suffixes, opérateurs,
annotations et formes de lancement. L’EBNF indique aussi la priorité de
la production d’initialisation après `.new(` et celle de la plage dans
`try_slice` avec `..`. Ce rejeu couvre les témoins existants. La vérification
de l’équivalence complète entre l’EBNF et le parseur reste ouverte.

### Fermetures génériques et opérateurs adjacents

Le parseur distingue `>` de l’opérateur qui suit dans `value as A<i32>==other`,
`value as A<i32>>=other` et `value as A<i32>>>2`. Deux fermetures suivies
de `=` restent possibles dans une déclaration. L’expression `4>>>1` et
l’affectation composée `value>>=1` sont refusées. Les 78 tests ciblés
passent, dont la suite numérique.

### Parenthèses de l’appel immédiat d’une closure

Le parseur seul accepte `(move || {42})()` et le regroupement
`((|| {42}))` en position de valeur. Il refuse `((|| {42}))()` et
`(read)()`, absents de la production `appel_closure`. Les 54 tests
ciblés passent. Le parcours historique garde son analyse existante.

### Usages du nom pool

Le parseur seul distingue `pool<Pool<[i32; 2]>>(4)`, `pool.new()`,
`pool < limit >> 1` et `pool()`. Le constructeur prend la priorité lorsque
des arguments suivent le type entre chevrons. Le test exerce un nom déjà
admis en position de liaison. Les 70 tests ciblés passent.

Le parseur distingue aussi `pool < (threshold > (0))` de la construction
`pool<closure(Pool<i32>) -> i32>(4)`. La fermeture du type du constructeur
doit être à l’extérieur des parenthèses et crochets imbriqués. Les 71 tests
ciblés passent après ce complément.

### Échappements des littéraux texte

Le parseur décode les échappements JSON puis encode la chaîne en UTF-8.
Le témoin a vérifié les octets d’un littéral direct, d’un échappement
Unicode, d’une paire de substituts et d’une chaîne avec saut de ligne et
guillemet échappés. Il a confirmé quatre refus : `\q`, `\u{e9}`, un
substitut isolé et un saut de ligne brut. TX1 garantit l’UTF-8 sans fixer
la liste d’échappements. L’EBNF indique l’état du parseur et l’arbitrage
restant. Le comportement du parseur est inchangé.

### Accolades après un nom de structure en condition

Le parseur seul distingue `if Packet { print(1); }`, `if Packet {} else {}`
et `if Packet { field: 1 } {}`. La lecture des accolades suit le même
critère pour les structures et les variantes. Le choix de liaison et le
type de la condition relèvent du vérificateur. Les 65 tests ciblés passent.

### Diagnostic d’une forme bloc mal écrite

Le parseur seul conserve l’erreur interne d’une forme bloc au lieu de
revenir à sa lecture comme instruction. Un témoin instrumenté avec vingt
`if` imbriqués et un `match` vide compte 21 lectures de bloc et retrouve
le diagnostic du `match`. Les 66 tests ciblés passent.

Le même traitement conserve ensuite le diagnostic de l’expression
`1 + ;`. Les formes réservées aux instructions, dont `let` et `return`,
sont traitées par leur production propre. Les 67 tests ciblés passent.

### Oracle d’attente des threads natifs

Le témoin qui exigeait une attente pour tout thread est remplacé par des
cas en syntaxe du core. `verify_program` et `compile_source` acceptent
l’abandon d’un handle autonome. Ils refusent l’abandon explicite et la
sortie de scope sans attente lorsque le thread capture une référence locale.
Les 70 tests ciblés passent. L’écart du témoin précédent est résolu par
la mise à jour des assertions selon N4 et RT7. Le code du vérificateur et
le nettoyage à l’exécution ne sont pas modifiés par cette mise à jour.

### Régression conjointe du core

`PYTHONPATH=tests python3 -m unittest test_numeric_core test_type_features.FunctionTypeContractTests test_value_moves test_growth_annotations test_native_thread_parser test_core_integration`
a terminé avec 124 méthodes réussies en 38,296 s. La sélection couvre le
parseur du core et des parcours de compilation déjà pris en charge. Les
exemples `main`, `conditional_returns`, `borrowed_returns`,
`invalid_borrowed_return_escape` et `let_mutability` passent aussi
`check --syntax-only`. Le refus de `invalid_borrowed_return_escape` lors
de la vérification reste couvert par le témoin du cycle précédent.
La liste normative des échappements reste ouverte, ainsi que les travaux
de vérification des closures, contrats de branche, handles et compositions
de HashMap et de lock indiqués dans la checklist.

### Receveur historique de type feature

Le parseur de `type feature` applique les trois formes de receveur de TF1 :
`&self`, `&mut self` et `-> self`. Il refuse désormais `fn a(self);` dans
cette déclaration historique. Les contrats de type du core continuent
d’utiliser les signatures de méthode de l’EBNF. Les 92 tests des suites
contrats de type, threads et déplacements passent. Cela résout l’échec
historique relevé dans la passe élargie à 80 tests.

### Appel de copy au parseur seul

`copy([1, 2])` conserve la forme d’un appel ordinaire dans l’arbre
syntaxique. Un témoin instrumenté avec `Vector<i32>` en paramètre et
`Result<i32, runtime::Error>` en retour async confirme que les fonctions
d’enregistrement des types ne sont pas appelées par `parse_syntax`.
Les 71 tests ciblés passent.

### Source UTF-8 invalide dans la CLI syntaxique

`check --syntax-only` lit explicitement en UTF-8. Un fichier contenant
`"été"` est accepté. Un octet invalide à la position 20 entraîne une
sortie de code 1 avec la position et sans trace Python. Le `check`
syntaxique et le `check` ordinaire acceptent `examples/main.crust`.

### Programmes complets de la suite d’intégration

La suite `test_core_integration` a terminé avec 30 tests réussis en
29,910 s. Une instrumentation de ses appels directs à `compile_source`
a recueilli 44 sources distinctes acceptées. Le parseur seul accepte
les 42 sources du core. Les deux sources avec `experimental_scheduler=True`
sont refusées sur `runtime::Future`, hors de l’EBNF du core. Cette collecte
couvre les appels directs de la suite. Les programmes lancés uniquement
par sous-processus CLI ne font pas partie du décompte.

### Correspondance entre l’EBNF et le parseur

| Familles de productions | Entrée du parseur | Suite de témoins |
| --- | --- | --- |
| Programme, déclarations, signatures, `type`, `branch` et `lock` | `parse_declarations`, `function`, `foreign_function`, `implementation`, `type_annotation`, `annotated_function`, `lock_annotation` | `FunctionTypeContractTests`, `NativeThreadParserTests` |
| Types, chemins, liaisons et cibles | `type_name`, `type_argument`, `qualified_name`, `syntax_assignment` | `FunctionTypeContractTests`, `ValueMoveTests` |
| Directives, blocs, imports `move` et contrôle de flux | `async_pool_directive`, `region_annotation`, `block`, `branch_tail`, `statement` | `GrowthAnnotationTests`, `ValueMoveTests` |
| Opérateurs, suffixes, littéraux, closures et constructeurs | `numeric_expr`, `postfix`, `primary` | `NumericCoreTests`, `ValueMoveTests`, `FunctionTypeContractTests` |
| Motifs, lancement, attente et bloc de thread | `syntax_match`, `syntax_pattern`, `primary`, `postfix` | `NativeThreadParserTests`, `FunctionTypeContractTests` |

Les 61 méthodes qui appellent directement `parse_syntax` dans ces cinq
suites ont été rejouées et passent. Cette revue relie les productions aux
témoins existants. Elle ne constitue pas une preuve générale d’équivalence.
La liste normative des échappements est ouverte. Les productions de
SelectGroup sont consignées comme reportées.

### Exemples de champ emprunté

`reference_fields.crust` et `invalid_reference_field_drop.crust` passent
`check --syntax-only`. Le premier affiche `42`. Le second est refusé par
`check` avec `emprunt encore utilisé`. La migration nomme `data.vref()`
avant de l’insérer dans le champ. La forme directe dans l’initialiseur
passe l’analyse syntaxique et le vérificateur réclame un emprunt nommé.
Le cas `match &*view` passe aussi l’analyse syntaxique et reste refusé par
le parcours de compilation de ce match. L’exemple garde `match &view`.

### Exemple de match non exhaustif

`invalid_enum_match.crust` utilise `fn main`, `i32` et `memory.new(...)`.
Le parseur seul accepte le programme. `check` le refuse sur l’exhaustivité.
L’ajout de `Message.Empty => {},` dans un témoin temporaire fait passer les
deux commandes. Les quatre appels CLI ont confirmé les issues attendues.

### Exemple de remplacement entre pools

`reassignment.crust` utilise `A<i32>`, `pool.new(...)` et la fin de scope.
L’appel qui lit l’ancienne valeur produit un résultat nommé avant le
premier remplacement. Le second utilise `second.new(30)` directement.
L’analyse syntaxique, la vérification et l’exécution passent. L’oracle
confirme `10`, `20`, `30` et la trace des destructions et récupérations.
Le témoin `data = make(&mut first, view);` passe `parse_syntax` et échoue
en compilation avec `<- exige ici une valeur tableau`. Cette limite reste
ouverte côté compilation.

### Emprunt explicite dans les exemples de retour direct

Les exemples partagés et mutables emploient `.vref()` et `.mut_vref()` pour
emprunter le contenu de `A<i32>`. Les deux passent `check --syntax-only`
et `run`. L’exécution confirme la même adresse avant et après le relais,
puis les sorties `42`, `7` et `30`, `40` respectivement. Les deux extraits
du README passent `parse_syntax` et `verify_program`.

### Exemples de contrôle de flux et de sortie de bloc

Les six exemples `conditionals`, `if_expression`, `loop`, `continue`,
`while` et `scope_exit` passent `check --syntax-only` et `run`. Les traces
observées montrent les deux nettoyages de `temporary` dans les exemples
de boucle et le retour de `3` depuis les blocs imbriqués de `scope_exit`.
Les sources de ces exemples utilisent déjà la syntaxe du core.

### Exemples de drop et de déplacement

`drop`, `drop_reuse`, `invalid_use_after_drop` et `invalid_borrow` passent
`check --syntax-only`. Les deux premiers s’exécutent. `drop_reuse` produit
`42`, deux adresses identiques, `43` et `99`, et sa trace contient
`reuse fresh`. Le vérificateur refuse la lecture après `drop` et le
déplacement alors que l’emprunt doit encore être utilisé.

### Exemples de type et de durée de vie d’un pool

`invalid_pool_type.crust` et `invalid_function_allocator.crust` passent
`check --syntax-only`. `check` refuse la construction de `Message` dans
`Pool<i32>` et le retour d’une allocation dont le pool est local à la
fonction. Le diagnostic d’incompatibilité affiche encore le nom de
représentation `pool<Int>`. Les quatre appels CLI ont confirmé les issues
attendues.

### Exemple d’évaluation des arguments

`arguments.crust` utilise `A<i32>` et le passage par valeur. Il passe le
parseur et la compilation. L’exécution donne `42`, `7`, `42`, `8`, `43`
et nettoie les deux allocations. Le témoin inverse aussi l’ordre des
paramètres pour conserver leurs types. Il passe le parseur, puis le
vérificateur refuse le déplacement avant la lecture de l’emprunt.

### Exemple de champ emprunté mutable

`mutable_reference_fields.crust` utilise `A<Writer>` et
`nombre.mut_vref()`. `check --syntax-only` passe et l’exécution produit
`Writer.Bound(10)` puis `20`. L’écriture déplacée avant `print(writer)`
passe le parseur, puis le vérificateur signale un emprunt actif.

### Exemple de retour depuis deux pools

`provenance.crust` reçoit et retourne des `A<i32>`. La branche retenue
conserve l’adresse de la valeur retournée et le slot de l’autre valeur est
réutilisé dans son pool. Le programme et sa variante temporaire inversée
passent `check --syntax-only` et `run`. Les deux exécutions vérifient les
adresses et les valeurs `20`, `30` puis `10`, `30`.

### Témoins de portée et de déplacement

`invalid_child`, `invalid_transfer_alias`, `invalid_function_move` et
`invalid_allocator_escape` passent `check --syntax-only`. Les trois
premiers échouent à `check` sur l’ancien nom devenu inutilisable. Le
quatrième échoue parce que le pool ne survit pas au bloc. Ces témoins
utilisent `move`, le passage par valeur et `pool<i32>`.

### Inventaire final des exemples pour la passe syntaxique

Les 46 sources d’`examples` ont été analysées avec `parse_syntax`.
31 passent, y compris les témoins qui doivent échouer à la vérification.
Les 15 refus concernent `allocator`, `effects`, `enums`, `functions`,
`invalid_modular_reset`, `invalid_reset`, `modular_calls`, `pool`,
`pool_requirements`, `reset`, `results`, `source_constraints`, `stack`,
`valid` et l’ancienne forme de `select`. `invalid_pool_requirement` passe
le parseur car `Allocator` est lu comme un nom de type, dont la résolution
relève du vérificateur. Les écarts recensés sur les formes validées sont
traités dans la passe syntaxique. L’arbitrage des échappements et les cases
de vérification et de migration des tests historiques restent ouverts.

L’utilisateur a ensuite confirmé le report de l’arbitrage sur les
échappements. La grammaire consigne le comportement actuel du parseur.

Le report a été levé. TX1 fixe les échappements JSON pour les chaînes
Crust. Le témoin couvre 11 formes acceptées avec comparaison des octets
et 7 formes refusées.

### Passage explicite d’une closure

L’EBNF et le parseur du core utilisent `fn(...) -> R` pour la signature
d’appel. Le parseur conserve le mode d’emprunt du paramètre, la mutabilité
de la liaison reçue et le type de retour. Il refuse l’ancienne notation
`closure(...) -> R` dans `check --syntax-only`. Le parcours historique
la reconnaît encore et la représentation interne de l’élaboration est
conservée. Les 35 tests de `FunctionTypeContractTests` passent. Ce lot
couvre la grammaire, le parseur et l’énoncé de la règle. Le contrôle
sémantique des nouveaux modes de passage reste à intégrer.

### Implémentation partielle de N4, N5, N6 et N8

Les jonctions de chemins utilisent la même fusion des obligations
différées pour un receveur remplacé, une valeur imbriquée et une
liaison conservée. Elles conservent les pools et verrous de résultat
ainsi que les écritures différées possibles. La représentation de
cette jonction est décrite dans [MEMORY_REPRESENTATION.md](../MEMORY_REPRESENTATION.md).

La même fusion couvre les résultats de `match` et de `break` et les
charges extraites dont plusieurs représentations sont possibles.
La comparaison du point fixe des boucles inclut désormais les
provenances et variantes de la charge différée et de ses champs,
ainsi que l’exactitude déclarée des mises à jour. Elle compare aussi
les destinations des écritures différées, les liens et réemprunts
qu’elles peuvent installer, et les positions connues des charges.
La fusion évite de recopier le même effet issu d’un état partagé
par plusieurs chemins.

La comparaison des boucles suit aussi les projections récursives
des champs et des résultats différés. Elle lit chaque origine avec
sa table de sources par type. Une table était auparavant lue comme
une source unique, ce qui pouvait interrompre l’analyse Python.
Les jonctions de receveurs, de résultats et de charges imbriquées
conservent les tables de leurs origines possibles.

À l’instanciation d’un résultat différé, un champ explicite du
contrat remplace la projection héritée du porteur, y compris
ses descendants. Les autres chemins sont récupérés à partir de
toutes les origines possibles. L’inférence des variantes applique
la même priorité et préserve les variantes déjà établies dans
le contrat.

L’application des écritures gardées à l’attente conserve le couple
verrou et charge. Si plusieurs charges sont possibles, chacune
conserve son état antérieur et les écritures qui la concernent.
Le raffinement par succès ou `LaunchFailed` exige toujours une
écriture exacte et une charge unique pour le verrou.

Le retour d’un handle depuis un appel synchrone reprend les pools
des handles transmis. Un contrat qui restitue uniquement un handle
argument reprend aussi sa preuve d’autonomie et, sans nouvelle
écriture différée, l’exactitude de ses mises à jour. Si plusieurs
arguments sont des résultats possibles, leurs effets sont réunis
comme des possibilités. L’abaissement async conserve les pools des
handles autonomes transmis par un tel appel pour comptabiliser un
éventuel abandon après le retour.

Lors d’un lancement synchrone, le handle d’exécution reprend les
obligations différées de la tâche inactive via la même représentation.
Cela transmet les pools et la preuve d’autonomie reçus d’un relais,
ainsi que les effets différés jusqu’à l’attente.

L’abaissement publie les pools concrets des handles autonomes
retournés par une tâche. Cette information se stabilise avec les
autres obligations de résultat, y compris quand une tâche restitue
un handle reçu par attente d’une autre tâche. `join()` et les deux
formes de `.await` récupèrent ces pools pour le suivi statique
des abandons. Le périmètre couvre les pools dont l’origine est
connue dans le corps, ainsi que les abandons explicites et les
résultats de handle ignorés. Quand une tâche restitue un handle
autonome injecté, le contrat identifie son paramètre. La création
directe de la tâche substitue les pools de l’argument, en code
synchrone comme async. L’attente et les jonctions async conservent
les pools possibles. Les relais synchrones conservent les pools de
résultat déjà établis sur leurs arguments, y compris quand l’appel
est abaissé dans une tâche. Les sorties de boucle par `break`
réunissent aussi les provenances possibles. Les emprunts et effets
d’un handle dépendant retourné restent à intégrer. Les contrats
des fabriques synchrones qui construisent une nouvelle tâche
publient les origines des pools du handle qu’elle peut retourner.
L’inférence substitue les arguments aux captures lors de la
création de la tâche, puis propage ces origines à travers les
appels et les jonctions. L’abaissement d’un appel synchrone
depuis une tâche récupère les pools concrets du contrat.

Le contrôle de durée de vie suit les valeurs proposées par les
écritures différées dans le même parcours que les charges possédées.
Il vérifie leurs emprunts, leurs verrous et leurs propres effets
différés. Pour une écriture gardée, il vérifie le porteur, la
charge protégée et les liens des cibles que l’écriture peut
installer. Le contrôle sert au transfert et à la sortie de scope.

Le remplacement d’un receveur par un `if`, un `match` ou une
boucle utilise aussi ce graphe. Avant de changer l’identité suivie,
le compilateur vérifie que le résultat de la branche ne retient
pas une dépendance vers cette génération du receveur. Les reprises
de boucle appliquent le même contrôle aux valeurs transférées.
Le résultat d’un `if` fusionne les obligations différées avec les
mêmes règles que les autres jonctions, notamment les pools de
handles retournés et l’exactitude des effets.

Une tâche inactive ou lancée garde une réservation mutable sur
chaque destination d’écriture différée ordinaire. Le contrôle
des accès et des déplacements utilise cette réservation pendant
la durée de vie de la tâche. Pour une écriture gardée, le
contrôle existant continue à passer par le verrou.

À la frontière d’un appel synchrone qui reçoit un handle, les
destinations d’écritures ordinaires sont comparées aux autres
arguments. Pour une écriture gardée, la vérification suit aussi
les dépendances transitives des cibles installées. Les autres
handles sont comparés à partir de leur graphe de durée de vie,
qui inclut les destinations et cibles de leurs propres écritures.

Une tâche attendue directement peut rendre un `AsyncHandle` qui
retient les emprunts de ses paramètres. L’abaissement publie les
indices de ces paramètres au point fixe. Il substitue les prêts des
arguments lors de l’appel et les rattache au handle reçu au moment
où il libère les autres réservations de la tâche extérieure. Le
contrôle interdit l’abandon du handle reçu tant que ces prêts
restent attachés. Ce chemin couvre les emprunts partagés et
mutables dont la cible remonte à un paramètre, avec une charge
autonome et sans écriture différée. Dans un contexte async, la
tâche extérieure peut aussi être lancée. Son handle transporte
les réservations du résultat. Après `.await`, le résultat les
conserve jusqu’au `match` qui les transmet au handle du bras
`Ok` ou les libère dans le bras `LaunchFailed`. Les chemins
d’abandon et de nettoyage suspendu contrôlent cette obligation.
Le raccordement au `join()` synchrone, à Select et aux effets
différés du handle retourné reste ouvert.

Un `AsyncHandle` retourné peut également produire un emprunt
scalaire. Le contrat publie les paramètres dont dépend cet
emprunt séparément de ceux que le handle réserve pendant son
exécution. L’attente directe et le lancement direct préservent
cette distinction. Les branches, les sorties par `break` et les
relais synchrones qui restituent leurs arguments réunissent les
projections possibles. Pour un chemin dépourvu de projection
précise, l’analyse conserve ses captures. L’abaissement traite
les tâches appelées avant leurs appelantes dans la mesure permise
par le graphe de création.

L’analyse des effets publie séparément les écritures ordinaires
de champs du handle retourné. Elle résout les porteurs mutables
et les cibles à partir des paramètres de la tâche extérieure.
L’attente extérieure et l’extraction dans `Ok` transmettent
ces effets dans l’analyse abstraite. L’attente intérieure
les applique en conservant l’état initial possible en cas de
`LaunchFailed`. L’abaissement instancie ces écritures à la
création de la tâche et les conserve jusqu’à l’attente du handle
intérieur. Les jonctions et relais préservent les possibilités.
L’analyse distingue les champs que chaque handle possible écrit
des champs écrits sur certains chemins seulement. `Ok` affine
les premiers. Pour les seconds, et pour les chemins dont le
contrat est incomplet, l’état initial reste possible. Les mises
à jour propriétaires ou de vecteurs exigent encore un contrat
de retour adapté.

Pour un handle retourné qui peut écrire sous verrou, le contrat
relie le mutex injecté aux paramètres empruntés qui fournissent
les cibles. Il distingue les cibles de chaque écriture observable
de l’état possible à la fin de la tâche. Une provenance inconnue
empêche la publication d’un contrat partiel. À la création de
la tâche extérieure, le vérificateur réserve le mutex et
valide chaque écriture possible. L’abaissement rattache ces
effets au handle intérieur et les applique à sa propre attente.
Ce chemin couvre la restitution directe de l’écriture d’un
enfant lancé. Les écritures gardées garanties par tous les
handles possibles affinent l’état après `Ok`. Les écritures
intermédiaires sont contrôlées indépendamment. Les effets
conditionnels et `LaunchFailed` conservent l’état initial
possible. Quand une tâche attend puis retransmet le handle,
l’analyse transporte les écritures observables dans un champ
distinct des changements finaux. Le nouveau contrat résout
les deux ensembles dans les paramètres de la tâche relais.
Les chemins réexportés conservent aussi la preuve d’écriture
garantie. Une jonction retient cette preuve pour un champ
uniquement si tous les résultats possibles la portent.

Le contrat du handle retourné transporte les remplacements de
champs propriétaires. Lors de sa construction, le compilateur
résout les sources et vérifie qu’un pool local survit au champ
qui peut recevoir l’allocation. L’effet reste différé jusqu’à
l’attente du handle intérieur. Après `Ok`, l’analyse affine
la provenance du champ dont le remplacement est garanti.
L’abaissement distingue le stockage de base et les liens propriétaires
des champs ou entrées pour les constructions suivies. À la jonction,
la distinction reste disponible quand chaque chemin fournit sa provenance
de base. Une reprise de boucle élargit les provenances possibles avant de
réanalyser son corps. Le retour d’un handle transporte aussi les
provenances des éléments qu’il peut installer dans un vecteur
d’allocations. Le contrat les exprime par rapport aux paramètres
du porteur et des valeurs insérées. Une nouvelle attente suivie d’un
relais conserve ces provenances, y compris lors de l’extraction du
handle depuis le résultat de lancement. L’effet reste différé jusqu’à
l’attente du handle qui porte la mutation. Le suivi garde les anciennes
provenances possibles et ne déduit aucune position exacte. Les vecteurs
inline à dépendances restent ouverts.

Les chemins d’insertion et de retrait HashMap sont transportés par
le résultat d’un handle. Le résumé conserve les clés constantes et
la provenance paramétrique de la table et de la valeur insérée.
Une clé dont la valeur n’est pas établie rejoint les entrées de clé
inconnue. L’attente du handle applique les chemins sur le graphe
du porteur. Le résultat de lancement permet d’y distinguer l’état
de réussite de celui où la mutation n’a pas eu lieu.
Le résumé de terminaison publie également les chemins d’une table
injectée modifiée par l’attente d’un handle retourné. Le site
d’appel les applique aux entrées correspondantes. Le résumé
conserve l’issue sans mutation si le lancement échoue. Quand
mutations directes et différées sont résumées séparément, les
provenances finales possibles des deux ordres sont conservées.
Le raffinement de ces chemins par bras reste à raccorder.

Le nettoyage lexical async vérifie les réservations restantes
après le nettoyage des tâches et la libération des emprunts du
bloc. Un scalaire ou tableau local qui sert encore de cible à une
réservation survivante entraîne un refus. Les alias et les
paramètres empruntés conservent les contrôles de leurs cibles.

Le nettoyage synchrone vérifie qu’une tâche vivante ne retient
plus la cible d’une destruction. L’abandon d’un handle consulte
les cibles et les pools du graphe, et le chemin historique de
réinitialisation consulte ces mêmes dépendances. Le `drop`
explicite d’un scalaire emprunté contrôle ses prêts avant
d’invalider la liaison.

Depuis un contexte async, un relais synchrone peut restituer un
handle qui porte des écritures gardées. Le contrat doit restituer
le seul handle transmis sans l’attendre. Les éventuels autres
paramètres sont des scalaires passés par valeur. L’appel conserve
les captures et les écritures en attente, que le résultat de
`.await` applique et affine au point d’observation habituel.
Un relais pur sans effet propre ne crée pas une possibilité
supplémentaire où l’écriture n’aurait pas eu lieu.

Le compilateur applique le contrôle de destination aux agrégats construits
avec des emprunts calculés. Il raccorde `match &*vue` aux contrôles d’accès
et conserve la réservation d’une entrée de HashMap lors d’un réemprunt
nominal. Une affectation locale dont le résultat est un appel propriétaire
passe par l’évaluation de la partie droite avant le nettoyage de l’ancienne
valeur. L’inférence de `branch` suit des alias et des sorties conditionnelles.
La spécialisation des paramètres de closure conserve leur mode d’emprunt,
et un contrat d’insertion à clé constante peut propager une cible nominale.

Le lot suivant raccorde le remplacement d’un receveur ancêtre aux contrôles
de destination. Les contrats de branche suivent aussi les bras de match et
les reprises de boucle. Les contrats d’insertion HashMap couvrent les clés
passées en paramètre, les blocs et les retours anticipés. Ils vérifient la
durée de vie de chaque référence enregistrée dans la table. Les closures
réempruntent leurs captures nominales en mutable pour les écritures reconnues.
Le compilateur refuse une seconde acquisition en async quand une garde
vivante retient déjà la même instance, et transmet sa réservation lorsque
la garde est déplacée. Un appel synchrone isolé peut relayer
un handle portant des effets gardés. En cas d’attente possible, le compilateur
conserve les états de réussite et d’échec du lancement.
Lors d’un transfert, il contrôle aussi la durée de vie des destinations,
des emprunts et des pools des écritures différées. L’analyse d’un gabarit
de closure inutilisé peut représenter un retour partagé par une capture
symbolique.

Le corps synthétique d’un gabarit inutilisé représente maintenant
tous les paramètres de référence dont le type correspond au
résultat. Pour un résultat partagé, il inclut aussi une capture.
Des conditions symboliques donnent à l’inférence un chemin par
origine possible. Quand le mode du receveur autorise une invocation
mutable, un emprunt mutable numérique ou nominal peut aussi
provenir du réemprunt d’une capture. Le gabarit utilise le même
champ et le même contrôle de provenance qu’une closure concrète.
Le cas nominal conserve la réservation du champ et la cible
projetée via le contrat de retour.

Pour N6, le remplacement identifie le scope du receveur avant la partie
droite, puis relit sa liaison après l’évaluation. Le nettoyage utilise
ainsi la liaison issue des chemins qui continuent et épargne une
allocation que la partie droite a déjà déplacée.
Quand les branches remplacent un receveur, la jonction vérifie que
chaque chemin qui continue possède une allocation vivante. Elle
reprend les compteurs de modification et utilise la même fusion
des provenances par position que la jonction d’une liaison conservée.
La convergence d’une boucle compare aussi les verrous transportés,
les verrous et pools du résultat d’une tâche et les informations
d’autonomie. La fusion de chemins conserve ces obligations même
quand la valeur concernée est imbriquée dans une autre allocation.
À la reprise d’une boucle, le contrôle de génération suit les
dépendances transitives et les verrous du receveur. Pour N4, la
vérification de destination inclut aussi les pools du résultat
différé, ceux de ses champs et les instances de ses verrous.
La fermeture d’un scope détermine les pools encore requis à partir
des liens de possession des allocations vivantes et de leurs
résultats différés. Le contrôle de fermeture du pool est commun aux
groupes d’allocations.
Le contrôle de destination et la fermeture d’un pool utilisent le
même parcours des liens de stockage. L’emplacement de l’allocation
racine reste vérifié par le transfert lui-même.
Ce parcours suit aussi les valeurs qu’une mise à jour différée peut
installer. Le contrôle à la fermeture du scope retient donc leurs
pools tant que l’effet est porté par une valeur vivante.
Le contrôle des emprunts à la fermeture d’un bloc s’applique aux
valeurs survivantes via leurs liens de dépendance. Pour une
projection, il vérifie la portée de l’allocation qui la contient.
Le contrôle de destination utilise aussi cette racine pour vérifier
la validité et la portée. Il inclut les cibles directes portées par
un descripteur de référence et celles d’une mise à jour différée.
La fermeture du scope et le transfert partagent ce parcours des
cibles. Les références portées par des descripteurs imbriqués sont
prises en compte avec les emprunts, réservations et verrous du groupe.
Le contrôle d’accès valide les réservations projetées sur leur
allocation racine. Il conserve la restriction exclusive quand il ne
dispose pas de la déclaration nécessaire pour prouver qu’une capture
autorise la lecture partagée.
Le contrôle des arguments lors d’un relais de handle à écriture
gardée utilise les pools retenus par ce même parcours. Il compare
aussi les instances verrouillées, y compris celles portées par un
résultat différé, aux autres arguments.

Une attente directe peut recevoir un `AsyncHandle` autonome à résultat
scalaire, tableau scalaire ou `Void`. La frame en garde la responsabilité
jusqu’au transfert du résultat. Si la frame terminée est détruite avant le
transfert, le runtime reprend le handle.

Les résultats de `join` conservent la provenance des mises à jour gardées
pour distinguer la réussite de l’échec du lancement dans le match. Ce
suivi couvre les résultats scalaires, les tableaux et les charges
propriétaires ou empruntées représentées par une allocation. Une vue empruntée
conserve la même information en plus de son descripteur.

Le transfert d’un AsyncHandle autonome vers une frame efface la valeur
source après la copie. Le calcul des capacités tient compte de l’abandon
possible si la frame est détruite avant son démarrage. La détection des
écritures via une capture nominale couvre aussi les réemprunts mutables
explicites et les méthodes mutables des champs.

Une closure peut réemprunter en écriture une référence numérique mutable
transférée dans ses captures. La projection réserve le champ de la closure
et suit la cible numérique. Le contrat d’un retour par ce champ conserve
ces deux réservations chez l’appelant.

L’inférence de `branch` rassemble les provenances des handles retournés
par les `break` d’une expression de boucle. Elle calcule le même point
fixe pour les chemins qui reprennent la boucle et conserve la contrainte
existante sur les modifications des liaisons extérieures à une expression.

Un corps annoté `branch` peut lancer une tâche inactive reçue en
paramètre. L’inférence suit ce paramètre à travers ses alias et
son déplacement dans un bloc enfant, puis rattache le handle
retourné à la tâche lancée. Le vérificateur du corps contrôle la
validité des déplacements. Le raccordement concerne les types
concrets de tâches et la forme synchrone du contrat.

L’inférence distingue l’origine d’une tâche inactive de celle
d’un handle lancé. Lorsque l’argument de lancement est un
résultat de bloc, de branche ou de boucle, elle réunit les
origines inactives des chemins qui fournissent cette valeur.
Les alias et les jointures de liaisons préservent les deux
informations séparément.

La résolution des origines utilise le type de tâche concret d’un
paramètre dès le contrôle de l’annotation. Elle rattache une
fabrique synchrone à la tâche inactive que sa signature retourne.
Pour un auxiliaire qui retourne le handle, elle infère l’origine
depuis son corps lors de la construction des contrats, même en
l’absence d’une annotation `branch` sur l’auxiliaire.

La construction du contrat suit aussi un handle reçu puis
restitué par un auxiliaire. L’analyse du corps publie l’indice
du paramètre. L’appel substitue les origines de l’argument à
cet indice, y compris quand plusieurs branches peuvent fournir
le handle. La déclaration annotée doit finalement établir un
lancement concret dans son corps ou dans ses appels.

Le contrôle d’annotation reconnaît `join=result.await` pour
une fonction async qui retourne un `AsyncHandle`. Il établit
l’origine du lancement dans le corps, y compris après `yield`,
et transmet les pools trouvés au contrat du handle retourné.
L’abaissement contrôle le type et les réservations du handle.
L’inférence suit aussi un lancement restitué par l’attente d’une
tâche inactive. Pour un appel direct, elle substitue les origines
des arguments lorsque le corps attendu relaie un handle reçu.
Pour une tâche nommée ou fournie par une fabrique, elle suit les
lancements concrets du type de tâche. Pour une tâche lancée,
l’analyse suit séparément l’origine du handle extérieur et celle
de la charge de son résultat. L’extraction de la charge dans
`Ok` reprend l’origine du handle intérieur. Si elle provient
d’un handle injecté, l’inférence substitue l’argument à la
création de la tâche puis conserve cette provenance jusqu’à
l’attente. Le contrat d’un relais peut désigner séparément
l’origine de l’argument et celle de son résultat différé.
L’inférence substitue cette seconde provenance quand une
fabrique ou un relais synchrone restitue la tâche ou le handle
extérieur.

En contexte async, le résultat de l’attente d’une tâche lancée peut
contenir un AsyncHandle autonome. Le bras `Ok` reçoit le handle. Si le
résultat est détruit ou son handle ignoré dans le match, le runtime
reprend le nettoyage. Le `join` synchrone peut également recevoir ce
résultat. Le bras `Ok` reçoit un AsyncHandle qui peut être abandonné ou
transféré comme argument à une tâche async pour y être attendu.

La signature publique `Handle<AsyncHandle<R>>` identifie le résultat comme
un handle distinct. La conversion d’un handle concret vers la signature
publique conserve aussi les informations connues sur l’autonomie et le
pool de la branche.

L’attente d’une branche lancée conserve séparément les cibles des champs
empruntés en cas de réussite et d’échec du lancement. Le `match` affine
l’état à partir du résultat. Une écriture ultérieure ou le remplacement
d’un champ englobant invalide cette information. Si les mises à jour
ordinaires et gardées peuvent toucher le même champ, l’analyse conserve
leur union.

Après `join`, le résultat transporte aussi les états de réussite et
d’échec pour une mise à jour ordinaire de références dont le contrat
établit l’effet. L’analyse invalide cette information si le champ est
réécrit ou si les chemins qui se rejoignent portent des résultats
différents.

Le suivi synchrone distingue également les champs propriétaires installés
par la tâche et les pools qui leur appartiennent. Sans information sur
l’issue du lancement, les deux états restent possibles. Les mises à jour
de vecteurs conservent aussi les descriptions des éléments possibles
dans cet état fusionné.

En async, la provenance d’un champ propriétaire dont le pool initial
est suivi peut être affinée dans le `match` du résultat. L’ancien pool
reste retenu s’il héberge le porteur ou si un autre lien suivi le requiert.
Lorsque le stockage de base est inconnu, le suivi conserve l’union des
provenances possibles.

Lorsque le contrat détermine l’état d’un vecteur après `join`, le résultat
conserve séparément les positions, les pools et la provenance des éléments
pour les deux issues. Une mutation ultérieure du vecteur invalide cette
information.

Une tâche attendue directement peut capturer un AsyncHandle à dépendances
si son unique paramètre est attendu dès la première instruction et si
aucun emprunt retourné ni effet de champ différé ne traverse ce paramètre.
L’attente extérieure retient les emprunts du handle jusqu’à la fin du
receveur. Le chemin suspendu reste indisponible au nettoyage anticipé
tant que cette attente est en cours.

L’analyse des effets reconnaît l’attente d’un paramètre AsyncHandle.
Elle conserve le contrat de terminaison du receveur et signale que le
nettoyage d’un bras perdant de Select peut être bloqué à cette suspension.
Un appel immédiatement attendu peut ainsi transférer plusieurs handles
à dépendances quand le receveur les attend dans sa séquence d’ouverture.

Le contrat publie l’ordre de ces attentes. Le compilateur applique les
mises à jour ordinaires des handles capturés dans cet ordre, puis les
effets du corps du receveur. Il conserve les états possibles d’un échec
de lancement lorsque le résultat de l’attente intérieure ne traverse pas
l’appel.

Une attente déléguée conserve aussi les mises à jour gardées sur un
mutex local. Le compilateur les applique après l’attente extérieure
en conservant les deux issues du lancement, puis invalide toute
information d’issue devenue obsolète pour les champs concernés.

Le résultat emprunté d’un AsyncHandle capturé peut être utilisé dans
le corps du receveur. Le compilateur suit une cible symbolique locale
dans ce corps et retient la cible réelle chez l’appelant jusqu’à la fin
de l’attente extérieure. Le résultat extérieur reste scalaire ou Void.

Si le receveur retourne l’emprunt numérique, son contrat identifie le
résultat du paramètre AsyncHandle comme origine. L’appelant remplace
cette origine par la provenance du handle effectivement transmis et
conserve l’emprunt après l’attente.

Les tâches acceptent un emprunt partagé de HashMap à valeurs scalaires
ou à références scalaires partagées. La capture conserve le porteur et
ses dépendances. La tâche peut transmettre l’emprunt à une autre tâche
ou appeler une fonction de lecture synchrone par le pont existant.

Le `match` direct sur `HashMap.get` lit une valeur numérique dans une
tâche async. Le compilateur vérifie l’emprunt de la clé et réserve la
table pendant la préparation de la recherche puis pendant l’utilisation
de la vue de case.

Un emprunt mutable de HashMap à valeurs scalaires peut traverser une
capture ou un appel à une fonction synchrone. Le bras `Some` de
`get_mut` reçoit une vue en écriture et réserve la table tant qu’elle
reste utilisable.

Une tâche peut construire une HashMap scalaire sur sa stack locale.
Elle peut utiliser `insert` ou `remove` dans un match direct. L’insertion
prépare la clé avant la valeur et conserve la réservation mutable de
la table pendant cette évaluation. Le bras `Some` reçoit une copie de
l’ancienne valeur.

Les résultats de `get`, `get_mut`, `insert` et `remove` peuvent être
nommés avant le `match`. Une recherche nommée retient la table jusqu’à
l’extraction ou au dernier usage du résultat. Lors de l’extraction, la
vue de case reprend cette réservation. L’ancienne valeur scalaire de
`insert` ou `remove` peut aussi être ignorée.

`try_insert` à valeur scalaire suit le même ordre d’évaluation que
`insert` dans une tâche. Le compilateur raccorde ses trois issues au
`match` direct ou nommé. `Err` extrait la valeur refusée par la table.
L’analyse des contrats conserve le type de cette valeur et de l’ancienne
valeur, extraite par `Ok(Some)`.

Une tâche qui emprunte une HashMap de références scalaires partagées
peut traiter `get` dans un match direct ou via un résultat nommé.
Le bras `Some` conserve une vue en lecture de la case. `**` lit la
cible. Pour les types d’emprunt déjà pris en charge, `*` copie la
référence et prolonge la réservation de la table jusqu’au dernier
usage de la copie.

Une tâche peut emprunter une HashMap de `A<T>` numériques. `get` donne
accès en lecture à la cible. `get_mut` autorise `**case = valeur` avec
une réservation de la case et de la table pendant l’évaluation de la
valeur. L’écriture conserve l’allocation et son pool. Les appels
synchrones depuis une tâche avec une telle table en mutable exigent
encore un contrat de mutation des entrées propriétaires.

Une table propriétaire construite dans la tâche accepte `insert`,
`try_insert` et `remove` pour des allocations numériques. L’insertion
transfère l’allocation et vérifie que son pool peut survivre à la table.
Le résultat conserve séparément les pools possibles de l’ancienne
allocation et de l’allocation refusée. Le `match`, le `drop`, la sortie
du scope et la destruction d’une frame suspendue raccordent le nettoyage
du résultat. Le suivi des clés couvre les littéraux et les liaisons
immuables initialisées par une constante suivie. `remove` sur une telle
clé détache les pools de l’entrée connue, avec maintien des dépendances
communes aux autres entrées et des entrées à clé inconnue. Au retour de
`try_insert`, le graphe retient les deux issues possibles. Dans le
`match`, `Err` restaure les dépendances antérieures et `Ok` installe
celles de l’insertion réussie. Une mutation ultérieure qui peut toucher
la même entrée invalide cette information. Les clés inconnues gardent
une union conservatrice des provenances.

Une table locale à références partagées scalaires vérifie que les
cibles survivent à son scope. `insert`, `try_insert` et `remove`
suivent les emprunts par clé. Un résultat nommé conserve les emprunts
des valeurs possibles jusqu’à leur dernier usage. Le `match` transmet
au receveur les dépendances de la référence extraite ou refusée.
Quand la tâche prête cette table à une fonction synchrone, le contrat
d’insertion de la fonction est instancié avec les clés et emprunts de
l’appel. Les chemins possibles sont fusionnés et les résultats de
mutations antérieures sont invalidés pour les clés qui peuvent se
recouvrir.

Pour un appelant synchrone, une tâche qui insère directement une référence
dans une table capturée par emprunt mutable publie les chemins de son
contrat via le mécanisme des effets différés. La création contrôle la durée
de vie des cibles par rapport à la table. Le `join` fusionne les états
possibles avant que le `match` distingue le succès de `LaunchFailed`.
Ce trajet couvre les insertions énoncées en instruction, les branches
sur des expressions scalaires de paramètres et `yield`.

Le même contrat d’insertion se propage d’une tâche enfant vers une table
locale de la tâche appelante. Le `.await` direct publie les écritures de
terminaison. Pour `execution.await`, le compilateur conserve les états
possibles et affine les dépendances au `match` du résultat.

Une tâche intermédiaire peut relayer des paramètres de table, de clé
et de référence à une fonction synchrone ou à une tâche enfant
attendue directement. Le compilateur compose les chemins et remappe
leurs paramètres dans le contrat de la tâche intermédiaire.

Le relais lancé suit aussi les deux bras d’un `match` sur `.await`,
pour un lancement direct dans le sujet ou un handle nommé. Le résultat
de l’attente peut lui aussi être nommé avant le `match`. Des `yield`
peuvent séparer le lancement, l’attente et l’observation du résultat.
Le bras de succès ajoute les écritures de l’enfant avant ses propres
effets. Le bras `LaunchFailed` commence avec l’état antérieur au
lancement. Les autres trajets de handles, les effets des branches
Select suspendues et la mutation des entrées propriétaires par un appel
restent ouverts.

Les contrats de tables de références représentent `remove(&clé)` en
instruction par un effet sans valeur entrante. La terminaison retire
l’entrée si la clé est connue à l’appel. Une clé dynamique conserve
les dépendances possibles. Les relais synchrones et asynchrones
conservent cet effet dans leurs chemins de terminaison.

Pour une table de `A<T>` numériques empruntée par une tâche, `remove`
en instruction détruit la valeur extraite. Le contrat cible le graphe
des allocations propriétaires. À l’attente, une clé connue permet
de retirer l’entrée et ses dépendances de pool. Un lancement faillible
conserve les deux états jusqu’à l’observation de son résultat.

Le contrat couvre aussi `insert` en instruction quand une tâche
transfère un de ses paramètres `A<T>` numériques à la table. L’effet
conserve le pool d’origine, vérifie sa durée de vie par rapport à la
table et remplace l’entrée pour une clé connue. Le code de la tâche
détruit l’ancienne allocation quand l’instruction ignore le résultat.
Pour `try_insert` sur une table empruntée, le compilateur suit le
`match` en instruction, avec un résultat direct ou nommé. `Ok(Some)`
et `Ok(None)` publient l’insertion. `Err` conserve l’état antérieur de
la table et restitue la valeur entrante au bras. Le nettoyage local
des valeurs extraites s’applique aussi à `insert` et `remove`.
Le retour interprocédural des valeurs extraites reste ouvert.

Une tâche peut appeler une méthode synchrone portant un contrat
`lock` direct et recevoir son résultat propriétaire dans une liaison
locale. Le graphe de la frame conserve les origines de `self` jusqu’à
la destruction du résultat. L’analyse refuse une nouvelle acquisition
sur une origine commune et une copie du résultat. Les acquisitions
sur une instance réservée par une tâche et les captures de cette
instance pendant la tenue du verrou restent conservatrices. Le
déplacement vers un receveur local, y compris une sortie de bloc ou
un remplacement, conserve la réservation et contrôle sa durée de vie.
Une fonction synchrone peut consommer la valeur ou la restituer
directement à la tâche. La réservation reste active pendant la
préparation des arguments. Le contrat de provenance la rattache au
résultat s’il restitue le paramètre. Les effets de copie inférés après
vérification du corps sont appliqués aux appels qui transmettent ou
empruntent une valeur portant un verrou. Lorsque la vérification des
fonctions synchrones révèle un effet de verrou supplémentaire, le
compilateur régénère les frames avec les contrats inférés. Les
acquisitions indirectes, les exigences d’instances distinctes et les
résultats propriétaires directs sont alors contrôlés à l’appel.
Un résultat portant un verrou peut être transféré à une tâche enfant
à résultat scalaire ou `Void` dont le corps consomme la valeur localement.
Le compilateur prolonge la réservation pendant la construction de la
tâche, puis jusqu’à sa destruction ou à la fin de l’attente. Le
contrôle du corps accepte les liaisons et opérations scalaires, les
blocs, les branches et le nettoyage local. Quand l’enfant retourne
directement le paramètre propriétaire, le contrat de provenance
transmet la réservation au résultat de `.await`. Sur un handle lancé,
le bras `Ok` transmet la réservation au receveur et `LaunchFailed`
la libère. L’enfant peut aussi restituer le paramètre via un appel
synchrone de retour. Le contrat de la fonction doit identifier exactement
ce paramètre et exclure sa copie ainsi que les effets d’acquisition ou
d’écriture qui modifieraient la réservation. L’enfant peut aussi
restituer le paramètre via une tâche descendante attendue directement.
Le compilateur suit la provenance à travers cette chaîne et vérifie
le corps de chaque tâche qui transmet le résultat.

Une tâche peut acquérir un verrou puis retourner la valeur qui le
maintient si l’instance provient d’un paramètre emprunté. Le compilateur
propage cette provenance jusqu’à stabilisation des contrats et la
rattache à la tâche ou à son résultat lors des appels directs. Une
fabrique synchrone peut aussi transmettre la réservation si son
contrat identifie la capture d’origine. Les contrats de handles
publics conservent une projection de cette capture de résultat, même
quand la signature efface la tâche concrète. La fabrique et son
appelant réutilisent cette provenance à travers l’effacement.
Le relais via un handle lancé dans l’enfant reste ouvert.

L’inférence de la séquence d’attente initiale des `AsyncHandle` accepte
les blocs lexicaux, les liaisons de littéraux et `yield` avant une
attente inconditionnelle. Elle compte aussi l’attente dans le sujet
d’un `match`. Les effets des bras viennent après cette attente et
arrêtent la séquence initiale. L’attente directe de la tâche extérieure
conserve les réservations pendant les suspensions. Les arguments
suivant le handle peuvent effectuer des calculs scalaires sans appel
ni suspension. Le receveur peut aussi retourner un tableau scalaire
par le chemin de résultat de tableau existant. Après consommation
d’un handle à dépendances dont la charge est copiée, le receveur peut
produire une allocation ou un nouvel `AsyncHandle`. Le retour de
l’allocation suit son contrat de provenance et le nouvel handle doit
satisfaire le contrôle d’autonomie.

Un appel synchrone à contrat d’attente ou de relais peut recevoir un
handle à effets gardés avec des arguments copiables ou d’autres
handles. Le compilateur vérifie les cibles et les effets des autres
handles, ainsi que le graphe des arguments empruntés ou propriétaires.
Ils doivent rester disjoints du mutex, de sa charge et des cibles que
l’attente peut installer. Les paramètres de pool sont comparés aux
sources du handle, de sa charge et des cibles installées. Un pool
indépendant est admis. Un pool commun reste admissible en lecture
si le contrat ne prévoit aucune allocation ni réinitialisation dessus.

Le compilateur conserve les positions d’un vecteur de valeurs en ligne
lors d’une capture mutable si les contrats de la tâche établissent
l’absence de modification des éléments à la terminaison et aux
suspensions possibles. Si le contrat de terminaison décrit des
retraits exacts sans ajout ni remplacement, une attente directe
reconstruit les positions restantes. Après une attente faillible,
le compilateur conserve les deux états et les distingue dans le
`match`. Une mutation ultérieure invalide cette information. Les
ajouts et remplacements exacts reconstruisent aussi les positions
lorsque le contrat résout la provenance de chaque valeur. Les emprunts
des champs et les pools des enfants propriétaires sont rattachés
à la nouvelle case. Une valeur réinsérée depuis une case d’entrée
connue conserve les dépendances de cette case. Le dernier élément
peut être résolu depuis les exclusions et le décalage du contrat.
Une provenance indéterminée garde le suivi conservateur. Quand les
positions sont exactes, le compilateur reconstruit les dépendances
agrégées des éléments. Pour un vecteur créé dans la tâche, le pool
de son propre stockage est suivi séparément. Un retrait connu peut
ainsi libérer les pools exclusifs à l’élément retiré dès que son
receveur est détruit.

L’inférence du receveur d’une closure suit les alias lexicaux d’une
capture et ses projections. Les écritures par déréférencement, les
affectations composées, les `match` mutables et les appels à
paramètre ou receveur mutable demandent le réemprunt mutable de la
capture. Une liaison qui masque la capture cesse de transmettre
son origine. Les résultats de blocs, de `if`, de `match` et les
`break` d’une boucle sont suivis à travers leurs liaisons lexicales.
Les réaffectations d’alias sont fusionnées à la sortie des blocs,
des `if` et des `match`. L’origine est retenue si elle est présente
sur un chemin qui continue. Les liaisons propres à une branche
sont retirées avant cette fusion. Dans les boucles, les reprises
normales et les `continue` font converger les origines en entrée.
Les états des `break` et des sorties de `while` sont fusionnés
séparément. Le résultat d’une boucle reprend la provenance de la
valeur du `break` à partir de cet état d’analyse stabilisé.
Les expressions terminales de blocs et de bras utilisent la même
analyse de chemin pour suivre les alias réaffectés avant le résultat.
L’appel d’une closure capturée est analysé à partir de la signature
de sa méthode `invoke`. Pour les méthodes résolues sur un alias,
l’analyse examine le receveur et les arguments explicites.
Les réemprunts explicites conservent leur origine de capture. Une
projection indexée utilise le type de l’élément pour suivre un
emprunt ou une allocation stockée dans le tableau.
La sélection du mode de réemprunt s’applique aussi aux allocations
numériques capturées. Une écriture détectée entraîne un receveur
mutable et passe par la projection propriétaire du champ.
L’analyse du receveur reconnaît les emprunts mutables de tableau dans
les signatures et les opérations spécialisées du parseur. Cela inclut
la division en vues mutables, le remplacement et l’échange.
L’élaboration des closures précède l’inférence des contrats. À ce
stade, un appel de signature connue qui reçoit un emprunt issu
d’une capture et retourne un emprunt propage une origine possible.
Le vérificateur utilise ensuite les provenances des contrats pour
contrôler les emprunts.

Les contrats de mutation HashMap substituent une clé constante à un
paramètre de clé lors d’un relais synchrone ou async. La table et la
valeur insérée gardent une provenance de paramètre. Les arguments
absents de l’effet restent contrôlés par la vérification ordinaire
de l’appel.

Restent ouverts les autres trajets de handles à dépendances, les retours
d’`AsyncHandle` via une tâche lancée séparément, les écritures indirectes via les captures de closure et les
compositions async des accès sous verrou et des opérations HashMap.

Aucun test écrit ni exécuté pour ces lots. La vérification de syntaxe
Python des modules modifiés ne valide ni les programmes Crust compilés
ni le C généré.

### Revue token par token des représentations

Première passe à partir des quatre témoins de portée et de déplacement
déjà reconnus par la passe syntaxique, puis des formes de closure de la
spécification. La reconstruction décrit les faits portés par les tokens.
Aucun parseur, vérificateur ou programme n’a été exécuté pour cette passe.

| Source | Tokens pertinents et représentation reconstruite |
| --- | --- |
| [Entrée dans le bloc](../../examples/invalid_child.crb) | `fn main` crée la déclaration et son scope de corps. `let mut memory` crée la liaison mutable du pool. `pool<i32>(1)` porte le type et la capacité. `memory.new(10)` crée l’adresse et son lien de provenance vers ce pool. Les accolades internes créent un enfant et son point d’entrée. `move data;` relie la liaison parent à la liaison enfant et conserve l’adresse. Les deux usages de `*data` ont chacun un point d’exécution et une liaison résolue dans leur scope. |
| [Bloc avec receveur](../../examples/invalid_transfer_alias.crb) | `let received =` désigne la destination. `move original;` rend l’adresse accessible sous la liaison enfant. L’expression finale `original` relie la sortie à `received`. Les noms `original` et `received` après le bloc restent deux liaisons distinctes. |
| [Passage par valeur](../../examples/invalid_function_move.crb) | `fn consume` définit le corps et le paramètre. `A<i32>` porte la forme allocation et le type d’élément. `consume(data)` relie l’argument au paramètre de l’activation et conserve la provenance du pool. L’usage suivant garde l’identité de la liaison d’origine. |
| [Pool déclaré dans l’enfant](../../examples/invalid_allocator_escape.crb) | `let result =` relie la sortie du bloc à un receveur parent. `local.new(42)`, en position finale, relie l’adresse produite à ce receveur. Le token `local` identifie le pool dont le scope reste celui de l’enfant. |
| [Closures](../LANGUAGE_RULES.md#closures) | Les barres identifient une valeur appelable et ses paramètres. Les annotations portent les types des paramètres ou du résultat. Les accolades identifient le corps. `move` porte sur la création. Chaque occurrence extérieure dans le corps se relie à une liaison source et à son champ de capture. Les parenthèses d’appel créent une opération distincte de la création. |

Arrêt à l’arbitrage sur la capture d’une référence partagée avec
`move`. V3 réserve la copie à `copy` sur les primitifs. La section
Closures décrit à la fois un transfert global avec `move` et une
copie de la référence partagée dans ce même contexte. L’arbre peut
porter la source, le champ et la cible dans les deux cas. Le mode
effectif du lien de capture et la disponibilité de la liaison source
dépendaient de la décision.

L’utilisateur a confirmé que le champ capture la référence partagée
par déplacement sous `move`. La liaison source conserve le point
d’exécution du déplacement, associé au chemin qui l’a exécuté.

| Sources parcourues à la reprise | Faits supplémentaires portés par les tokens |
| --- | --- |
| [Retours conditionnels](../../examples/conditional_returns.crb), [if avec receveur](../../examples/if_expression.crb), [provenances](../../examples/provenance.crb), [conditionnelles](../../examples/conditionals.crb) | `if`, la comparaison et `else` identifient les entrées possibles. Les expressions terminales et `return` identifient la destination de la valeur. Les chemins avec `return` quittent la fonction. Les autres chemins apportent leur état à la jonction, avec leurs identités et pools d’origine. |
| [Boucle](../../examples/loop.crb), [continue](../../examples/continue.crb), [while](../../examples/while.crb) | `loop` et `while` identifient l’entrée d’itération. `break` et `continue` portent leurs destinations et les scopes quittés. Le test faux de `while` porte une sortie distincte. `temporary` identifie une liaison du corps, avec une instance de l’allocation pour l’itération. |
| [Réaffectation](../../examples/reassignment.crb), [arguments](../../examples/arguments.crb), [mutabilité](../../examples/let_mutability.crb) | `mut` porte la capacité de modifier la liaison. `=`, `.set` et `*` distinguent place et opération. Les arguments ordonnés de `consume` conservent l’appel imbriqué de `read` avant la consommation de `data`. Les formes de remplacement conservent l’ancienne adresse et l’adresse produite à droite. |
| [Retours d’emprunt](../../examples/direct_borrow_returns.crb), [retours mutables](../../examples/mutable_borrow_returns.crb), [champs empruntés](../../examples/borrowed_returns.crb), [champs mutables](../../examples/mutable_reference_fields.crb), [match nominal](../../examples/main.crb) | `&`, `&mut`, `.vref` et `.mut_vref` déterminent le mode et la cible. Les arguments et retours relient l’origine paramétrique à la cible concrète. Les noms de variante et de champ identifient une position dans le porteur. `match` et les motifs relient le sujet aux entrées et aux liaisons des bras. |
| [Drop](../../examples/drop.crb), [réutilisation](../../examples/drop_reuse.crb) | `drop` désigne l’opération de consommation. `.new` identifie une nouvelle allocation, même si le pool réutilise le slot. Les noms passés à `address` désignent les deux identités d’allocation aux points où elles sont observées. |

Nouvel arrêt sur le témoin de [capture partagée sans move](../../tests/test_closures.py)
qui écrit `let read = || { *vue };`. Les barres et l’usage de `vue`
portent l’instance et son lien de capture. La grammaire admet cette forme
et signale que les captures sans `move` restent à préciser. Le témoin
historique attend une copie de la référence. Avec V3 et le transfert
confirmé sous `move`, il reste à fixer le mode de ce lien sans marqueur,
ou l’exigence de `move` pour cette capture.

#### Parcours du corpus sans arrêt d’arbitrage

La capture sans marqueur conserve la liaison source et sa destination.
Son mode effectif reste indéterminé dans la représentation. La passe a
continué sur les blocs documentaires Rust/Crust, les blocs de texte
identifiés comme du code, les sources Crust d’`examples` et de
`validation`, et les littéraux Python de `tests` repérés comme du
code Crust.

| Origine | Programmes ou déclarations | Fragments de bloc | Fragments de signature | Tokens représentés |
| --- | ---: | ---: | ---: | ---: |
| Documentation | 23 | 9 | 2 | 1 420 |
| Fichiers Crust | 38 | 0 | 0 | 3 633 |
| Littéraux Python | 889 | 1 700 | 105 | 77 754 |
| Total | 950 | 1 709 | 107 | 82 807 |

Le [constructeur de corpus](../../validation/build_representation_corpus.py)
utilise l’entrée syntaxique du core. Les fragments sont relus avec une
enveloppe de bloc ou un corps de signature synthétique, marqués comme
fragments. Leurs tokens d’origine restent identifiables. L’inventaire
porte le diagnostic des candidats non reconnus. Il ne reconstitue pas
les sources générées à l’exécution par Python ni les exemples informels
dispersés dans la prose.

Chaque occurrence reconnue possède une représentation structurée et
des liens entre ses tokens, ses scopes et ses nœuds. Les faits extraits
incluent les liaisons, captures, pools, constructions, projections,
appels et sorties. Les curseurs, certains liens de type et les
provenances qui exigent une résolution sémantique restent symboliques
ou indéterminés. La revue n’a exercé aucune règle et n’a exécuté aucun
programme Crust.

### Frontend Rust et comparaison du corpus

Le [crate Rust](../../rust_frontend/README.md) lit le texte, produit les tokens
avec positions, parse les déclarations et expressions et construit
l’arbre statique avec identifiants de scopes, liaisons et points.
La construction distingue les déclarations des usages de nom et
conserve les liens vers les captures, projections et destinations
lexicales des sorties. Les annotations sont représentées dans l’arbre.

| Origine | Corpus | Rust reconnaît | Toutes les projections comparées concordent |
| --- | ---: | ---: | ---: |
| Documentation | 34 | 34 | 33 |
| Fichiers Crust | 38 | 38 | 37 |
| Littéraux Python | 2 694 | 2 686 | 2 620 |
| Total | 2 766 | 2 758 | 2 690 |

Les 2 758 occurrences communes concordent sur les lexèmes normalisés,
les parents et lignes d’entrée des scopes et la liste ordonnée des noms
de liaisons locales. Les 68 autres projections communes divergent
sur les faits extraits ou les liens de déplacement nommés. Le corpus
Python omet notamment des constructions `.new` à champs nommés et
des déplacements d’entrée de thread natif. Les huit refus Rust
concernent des morceaux de littéraux Python assemblés à d’autres
sources, dont des fins de bloc et des débuts de fonction incomplets.

La comparaison est directionnelle depuis les occurrences reconnues par
le corpus Python et porte sur les projections énumérées. Elle ne démontre
ni l’équivalence grammaticale générale ni l’identité complète des
arbres. Aucun vérificateur de règles, générateur de C ou programme Crust
n’a été exécuté.

### Vérificateur Rust et génération C du sous-ensemble scalaire

Le vérificateur lit les identifiants de liaison et les usages du
frontend. Les signatures résolues déterminent le type des arguments.
Les branches propagent l’état des liaisons sur leurs chemins de
continuation. Pour les emprunts locaux, une référence conserve
l’identité de sa cible à travers un déplacement. Le contrôle des
accès tient compte des réservations actives et le contrôle de
destination compare les scopes de la cible et du receveur.
Le générateur C reçoit les instructions typées du vérificateur.
Les temporaires matérialisent l’ordre des opérandes et des arguments.

Quatre programmes ont été compilés en C11 avec Clang, les
avertissements traités en erreurs et UBSan sans récupération.
Les sorties attendues ont été obtenues pour la mutation par emprunt,
le déplacement puis le drop d’une référence, le retour conditionnel
et le reste du minimum signé par moins un. Six refus ciblés ont été
observés sans émission de C. Ils couvrent l’usage après déplacement,
la consommation sur un chemin, un conflit d’emprunts, un résultat
mal typé, le débordement littéral et la division par zéro.

Cette passe couvre une partie des huit règles. Les réservations sont
lexicales sauf drop explicite. La dernière utilisation, les emprunts
en signatures, les réemprunts, les boucles, les agrégats, les pools,
les destructeurs et les effets async restent ouverts dans le Rust.

### Graphe de contrôle, dernier usage et boucles dans le Rust

Le graphe relie la condition aux branches, les reprises à l’entrée de
boucle, les ruptures à leur continuation et les retours à la fin de
fonction. Une analyse arrière calcule les liaisons dont un usage reste
possible. Le vérificateur consulte ces faits à l’accès à une cible.
Pour une affectation simple de scalaire, il vérifie la réservation au
point de l’écriture après l’évaluation de la droite.

Le vérificateur fusionne les états entrant à la première itération
et par les reprises jusqu’à stabilisation. L’état après la boucle
réunit les ruptures et l’issue fausse de `while`. Le C évalue la
condition à chaque reprise et émet des `break` et `continue` natifs.

Six témoins compilés en C11 avec avertissements en erreurs et UBSan
ont produit les sorties attendues. Ils couvrent la dernière lecture,
les réservations distinctes par branche, les ruptures et reprises,
la réinitialisation avant reprise, une lecture lors de l’itération
suivante et le dernier usage dans la partie droite. Cinq refus ciblés
ont été confirmés sans émission de C, dont un usage après déplacement
sur la reprise et deux conflits avec un emprunt encore utilisé.
Le périmètre reste celui des scalaires synchrones et références locales.

### Réemprunts, contrats de références et boucles à résultat en Rust

Le vérificateur conserve le couple cible et parent de chaque
provenance. Un réemprunt encore utilisé réserve le parent, y compris
à travers une chaîne de réemprunts. Les arguments déjà évalués
gardent leurs réservations pendant la préparation des suivants.
Pour un retour emprunté, le contrat infère les paramètres de
provenance et l’appel substitue les origines concrètes. Les appels
récursifs peuvent garder une approximation conservative du contrat.

Une boucle à résultat installe la valeur du `break` dans un
temporaire de réception. Le vérificateur conserve les provenances
de tous les `break` qui atteignent ce receveur et refuse une cible
ou un parent créé dans la boucle qui doit disparaître à sa sortie.

Huit témoins ont produit les sorties attendues en C11 sous UBSan.
Huit refus ont été confirmés sans émission de C, dont deux alias
d’arguments, deux accès à un parent réservé, deux cibles locales
échappées, une écriture incompatible avec une provenance possible
et un résultat de boucle de type incompatible. Ce lot porte sur les
références de scalaires et les fonctions synchrones. Les agrégats,
les pools et l’async restent ouverts.

## Placement fixe dans le compilateur Rust

L’analyse post-AST relie les constructions, déplacements et réceptions de
structures synchrones à champs scalaires. Elle situe la réservation dans le
scope qui couvre la destination finale, regroupe les constructions exclusives
d’un même résultat et déduit les emplacements de sortie à fournir à chaque
appel. Un résultat transmis depuis un paramètre garde son adresse.

`cargo build --offline` et `cargo fmt --check` ont réussi. Quatre témoins
ont été abaissés en C11 puis compilés et exécutés avec
`-Wall -Wextra -Werror -fsanitize=undefined -fno-sanitize-recover=all`.
Le bloc enfant produit 7. Le conditionnel produit 10 et 30 et chaque paire
de bras écrit dans un emplacement commun. Le relais interfonction produit
42 et transmet l’emplacement de sortie ou l’adresse du paramètre selon le
contrat. Les deux constructions qui peuvent coexister produisent 41 et 42
et le C contient deux emplacements par appel.

Cette validation couvre le placement par stockage automatique C. Le calcul
des curseurs de la datastack, les autres types fixes et le placement des
valeurs dont la durée de vie implique l’async restent à intégrer.

### Datastack à curseur dans le backend Rust

Le plan post-AST fournit les réservations de structures, de liaisons,
de receveurs et de résultats d’appel. Les blocs et appels en position de
résultat peuvent transmettre directement le slot du receveur. Le C réserve
les plages alignées dans un mapping anonyme et restaure le curseur à la
sortie des scopes et des appels, y compris sur `break`, `continue` et
`return`. Le stockage prévu chez l’appelant est antérieur à la marque du
callee.

`cargo build --offline` et `cargo fmt --check` réussissent. Sur macOS, sept
témoins compilent avec `-std=c11 -Wall -Wextra -Werror
-fsanitize=undefined -fno-sanitize-recover=all` à `-O0` et `-O2`. Ils couvrent
une structure remontée d’un bloc, les bras de structure à emplacement
commun, un relais d’appel, deux constructions coexistantes, des retours
scalaires à travers des blocs, un emprunt mutable retourné puis utilisé, et
une boucle avec `break` et `continue`. Le C confirme les réservations
d’une et de deux places selon le chemin et le relais de `crust_out`.
Quatre témoins supplémentaires à `-O2` couvrent un main vide, le code de
sortie de main, un retour d’emprunt partagé depuis une référence mutable et
la sortie d’un while par sa condition.

Avec la capacité ramenée à 64 octets dans le C du témoin de boucle, les
20 000 itérations s’achèvent. À 1 octet, la première réservation de huit
octets quitte avec le code 1 et le diagnostic de limite attendu. La suite
générale et l’audit indépendant n’ont pas été exécutés sur ce changement.

Le backend couvre les types fixes déjà vérifiés. Les autres types fixes,
la capacité issue de l’analyse statique, la configuration explicite et la
datastack à régions restent ouverts.

### Extension du placement des types fixes

Le backend Rust abaisse les primitifs numériques du core, les tableaux
à longueur littérale, les enums nominaux, les structures imbriquées et les
pools locaux. Le plan post-AST reconnaît ces agrégats comme producteurs
d’une identité à placer. Il conserve les réservations de destination et
l’emplacement commun des bras exclusifs. Le backend calcule l’alignement
à partir du type C de stockage et dispose les champs imbriqués en ligne.
Les pools d’enums réservent une zone de payloads par variante. Les
enregistrements de nettoyage libèrent les slots avant le recul de la
datastack. Une libération intérieure est réutilisable à la limite.

Huit nouveaux témoins C11 et sept témoins précédents passent sur macOS sous
UBSan, à `-O0` et `-O2` avec `-Wall -Wextra -Werror`. Les nouveaux témoins
couvrent les six primitifs ajoutés, les retours conditionnels de tableaux
et d’enums, les champs imbriqués et les pools locaux avec réemploi des
slots, nettoyage en fin de bloc et zones distinctes par variante.
Les quatre contrôles supplémentaires à `-O2` couvrent l’écriture
indexée, un indice dynamique négatif, un tableau vide et un pool épuisé.

Huit refus sont confirmés pour un type récursif en ligne, un indice
constant hors borne, un littéral `u8` hors plage, une opération mêlant
un littéral entier et un flottant, une division par zéro flottante,
un match non exhaustif, un pool immuable et un drop de pool encore
utilisé. Les vérifications concernent le sous-ensemble synchrone Rust.
Les signatures de pools et d’allocations, les agrégats à dépendances
et les emprunts de places agrégées restent ouverts. La suite générale
et l’audit indépendant n’ont pas été exécutés.

### Dépendances des agrégats et transferts de pool

Le vérificateur conserve les racines d’emprunt dans les structures, tableaux
et variantes. Il distingue l’adresse d’un paramètre par valeur des
dépendances apportées par ce paramètre, vérifie les sorties de blocs et
réunit les provenances possibles avant de produire le plan post-AST. Un
emprunt de champ ou de case réserve sa racine. Le réemprunt d’une référence
mutable stockée dans un agrégat local réserve également son support.

Le pool se passe par emprunt sans déplacer sa zone. `A<T>` se transmet par
valeur et conserve son adresse de payload. Ses métadonnées sont dans le
pool, avec une marque de nettoyage qui suit le receveur, y compris sur
`break`, lors d’un appel et à son retour. Le retour distingue les racines
du pool des dépendances du payload. Un match sur une allocation lit son
tag puis le payload de la variante dans le slot correspondant.

Sur macOS, `cargo build --offline` et `cargo fmt --check` passent.
`python3 validation/check_rust_placement_dependencies.py` confirme
14 témoins C11 à `-O0` et `-O2` sous UBSan avec avertissements traités en
erreurs, et 10 refus avec diagnostic. Sont notamment exercés le réemprunt
d’une case, les retours d’agrégats empruntés, les conflits d’écriture, le
passage de pools sur plusieurs appels, les choix entre deux pools, la
lecture d’une variante en pool, la réutilisation après consommation et
les refus de faire échapper un pool ou un pointeur local. Les quinze
témoins des deux passes précédentes passent également aux deux niveaux
d’optimisation.

La provenance est suivie par union à l’échelle de l’agrégat. Cette
approximation peut refuser des programmes valides dont la preuve exige
la distinction de deux champs ou de deux cases. Les réemprunts depuis
un agrégat lui-même emprunté et les motifs empruntés à champs agrégés
restent incomplets. La suite générale et l’audit indépendant n’ont pas
été exécutés.

### Provenances par position et match emprunté

Le vérificateur conserve le chemin de chaque dépendance dans une valeur
et, pour un contrat de retour, le chemin correspondant dans l’argument.
Les chemins combinent variante, champ et indice. La sélection d’un indice
dynamique réunit les cases possibles. Le graphe de contrôle conserve les
sites d’usage et sépare les bras de match. Un emprunt direct de case
réserve toujours la racine selon E6. Pour une référence stockée, le
réemprunt réserve la position sélectionnée et suspend les accès qui
peuvent la recouvrir, y compris via la référence à l’agrégat.

Un motif sur un enum emprunté lie un champ agrégé par son adresse et
conserve le mode partagé ou mutable. Pour un enum en pool, l’adresse
désigne le payload du slot de la variante. Le plan post-AST de placement
et le runtime de datastack restent identiques.

`cargo build --offline` et `cargo fmt --check` passent. Huit nouveaux
témoins C11 passent sous UBSan à `-O0` et `-O2`. Ils couvrent la provenance
des champs et cases dans les contrats, un résultat qui permute les
positions, le dernier usage d’un champ, deux réemprunts disjoints via un
agrégat emprunté, la lecture d’un champ disjoint et les motifs empruntés
sur un tableau et un champ de pool. Six refus ciblés couvrent les
recouvrements dynamiques, le réemprunt mutable via une référence
partagée, la destruction du parent ou du slot avant le dernier usage,
et la provenance conservatrice d’un résultat récursif. La commande
`python3 validation/check_rust_placement_dependencies.py` rejoue ces cas
et les quatorze témoins et dix refus précédents.

Un indice non résolu et un contrat récursif encore inconnu gardent
toutes les provenances candidates. La vérification se limite au
backend Rust synchrone et aux cas fonctionnels ciblés. La suite générale
et l’audit indépendant n’ont pas été exécutés.

### Dimensionnement de la datastack classique

Le parseur accepte l’annotation globale facultative et ses propriétés.
La vérification convertit les tailles décimales positives en octets,
contrôle le débordement et transmet la propriété `size` au backend.
Elle prime sur la borne et le défaut. Une réservation qui excède cette
capacité arrête le programme selon le diagnostic de limite existant.

Quand `size` est absente, le compilateur extrait du plan post-AST les
réservations réelles, les marques de scopes et les appels accessibles
depuis `main`. Les deux branches sont mesurées depuis le même curseur.
Une itération inclut le test et le corps, puis revient à sa marque.
Les emplacements anticipés chez l’appelant, les paramètres et la zone
entière des pools sont comptés. Les alias ne réservent aucun octet.
Le backend C calcule la borne au démarrage avec `sizeof` et `_Alignof`,
sans évaluer les expressions du programme. Le calcul et les réservations
réelles partagent l’arithmétique d’alignement vérifiée. Un cycle d’appels
accessible déclenche le défaut de capacité au runtime. La récursion
inaccessible depuis `main` ne change pas la borne.

Sur macOS, le script `validation/check_rust_datastack_capacity.py` exécute
dix témoins C11 à `-O0` et `-O2` sous UBSan. L’instrumentation compare la
capacité au maximum du curseur observé. Les chemins d’alignement retenus
atteignent 144 octets, et la boucle de 20 000 itérations atteint 520 octets.
Les témoins vérifient aussi les appels, les pools, la priorité de 1 Kio
avec une borne déduite ou inconnue, le défaut en récursion et l’arrêt
lors d’un dépassement de 1 Kio. Six annotations sont refusées pour taille
nulle, hexadécimale, unité invalide, répétition, débordement ou position
hors tête du programme. La forme vide et une propriété de région seule
sont acceptées. Les 37 témoins de placement et d’emprunts précédents
passent également sous UBSan aux deux niveaux d’optimisation.

La borne peut être conservatrice. Les conditions du programme ne sont
pas évaluées pour éliminer des chemins et aucun nombre maximal d’appels
récursifs n’est déduit. La datastack à régions et l’audit indépendant
restent en dehors de ce cycle.

### Datastack à régions dans le backend Rust

Les descripteurs des vecteurs à éléments fixes sans dépendances et des
chaînes restent dans leurs slots de pool, sur la datastack classique.
Leur contenu grandit dans une plage à adresse stable, avec un seul
curseur. Le registre d’occupation réutilise les trous lorsque le
curseur atteint la limite. La libération d’un suffixe recule le curseur.
Un transfert d’`A<T>` conserve la région et sa limite. Les bandes locales
fermées restent mappées jusqu’à la libération de leur dernier contenu.

La configuration globale applique séparément les priorités explicite,
déduite, défaut pour `region_stack_size` et `region_size`. Le plan
post-AST majore les slots par les capacités des pools qui peuvent
coexister, et les octets par la somme des ajouts bornés. Une croissance
en boucle donne une taille inconnue sans empêcher de déduire les slots.
Le backend évalue les tailles dépendantes de l’ABI avec `sizeof`. Le
gabarit inconnu utilise 100 Mio. La capacité globale inconnue utilise la
même estimation de mémoire que la datastack classique.

Une annotation locale à gabarit différent ou à `count` explicite ouvre
une bande dédiée. Un gabarit identique sans `count` réutilise la
configuration héritée. Quand le nombre local est omis, l’estimation
statique des slots sert de borne conservatrice. Si elle est inconnue, la
bande commence avec un slot et peut utiliser des bandes dédiées
supplémentaires. La sortie d’un scope restaure sa configuration après
le nettoyage, y compris sur `break`, `continue` et `return`.

`python3 validation/check_rust_regions.py` compile en C11 avec
`-Wall -Wextra -Werror` et UBSan à `-O0` et `-O2`. Sept témoins couvrent
la disposition déduite, UTF-8 et les octets nuls, le réemploi d’un trou,
le débordement du nombre de slots locaux vers une bande dédiée, le
transfert d’une région, l’héritage via appel et les reprises de boucle.
Deux dépassements déclenchent le diagnostic attendu. Trois annotations
invalides sont refusées. Les 47 témoins précédents de placement,
d’emprunts et de dimensionnement classique passent également aux deux
niveaux d’optimisation.

Le cycle porte sur les usages synchrones pris en charge. Il ne couvre
pas le raccordement de `HashMap`, les éléments de vecteur portant des
dépendances, les vues de chaînes et les états async ou multithread.
L’audit indépendant n’a pas été exécuté.

### Collections à dépendances et régions

Le backend Rust place le descripteur des HashMap à valeurs primitives
via le plan post-AST. Chaque table conserve un index chaîné et ses
entrées dans une seule région. L’index compte 16 compartiments. Les
collisions sont résolues par chaînage et comparaison de la clé complète.
Le remplacement conserve l’adresse de l’entrée et la suppression
rend son emplacement réutilisable. Le calcul post-AST borne une
insertion statiquement par une entrée plus l’index initial. Le
nettoyage suit le receveur même si la table garde une adresse placée
dans un scope plus durable. Les prêts de résultat de `get` et `get_mut`
protègent la table jusqu’à leur dernier usage.

Un vecteur peut porter des références partagées ou mutables et prendre
en charge des `A<T>` issus de plusieurs pools. Les insertions réunissent
les dépendances, y compris aux sorties conditionnelles et aux reprises
de boucle. Un handle inséré quitte la liste de nettoyage de son ancien
scope et rejoint celle du vecteur. La destruction du vecteur restitue
les handles dans l’ordre inverse d’insertion avant de rendre sa région.

Sur macOS, sept témoins C11 et les 56 témoins précédents passent à
`-O0` et `-O2` sous UBSan. Le script
`python3 validation/check_rust_region_collections.py` rejoue les nouveaux
témoins et quatre refus. Un témoin complémentaire d’insertion en boucle
dans une région de 1 Kio sort avec le code 1 et le diagnostic de limite.

Les HashMap à valeurs dépendantes, les opérations d’extraction des
handles de vecteurs et le raccordement async et multithread restent
ouverts. Le témoin `async fn work(){yield;} fn main(){}` reste refusé
par le vérificateur Rust avant génération C. Le prototype Python
dispose d’un runtime séparé. L’audit indépendant n’a pas été exécuté.

### État régional des threads natifs

Le backend Rust abaisse `runtime::thread({ ... }).join()` avec un état C
distinct par bloc et un worker pthread. Les captures scalaires
déclarées en tête par `move nom;` sont évaluées dans l’ordre, déplacées
dans cet état avant le lancement, puis reçues en paramètres du worker.
Le bloc retourne un scalaire ou `Void`. Le résultat du join est abaissé
en variante `Ok` ou `Err(LaunchFailed)`.

Le plan post-AST réserve le résultat chez l’appelant et compte une
région pour l’état du lancement. Il calcule séparément les bornes de
l’appelant et celles des datastacks du worker. Les datastacks, les pools
et les métadonnées de région du worker sont isolés par stockage local
au thread. Seul l’état du lancement est partagé. L’appelant y écrit
avant la création, le worker y écrit son résultat, et l’appelant lit ce
résultat après `pthread_join`. Le worker nettoie ses propres valeurs
avant de terminer. L’appelant libère la région de l’état après la
lecture ou directement si le lancement échoue.

`python3 validation/check_rust_native_regions.py` exécute cinq témoins
C11 avec `-pthread -Wall -Wextra -Werror` sous UBSan à `-O0` et `-O2`.
Ils couvrent la croissance d’un vecteur dans le worker pendant qu’une
région de l’appelant reste vivante, la réutilisation d’un slot après
40 joins, deux workers imbriqués, les captures scalaires et la
réutilisation du slot après un échec de lancement injecté. Quatre
refus couvrent les captures implicites ou à dépendances, l’usage
après un déplacement de capture et la suspension dans un bloc
synchrone. Les 63 témoins précédents passent également sous UBSan aux
deux niveaux d’optimisation.

ThreadSanitizer quitte avec le code 139 sans diagnostic sur le témoin
généré et sur un programme C minimal appelant seulement `pthread_create`
et `pthread_join`. Il ne fournit pas de résultat exploitable ici.
Le passage ne couvre que le join immédiat. Les handles conservés,
les résultats agrégés et les retours scalaires anticipés des blocs,
les captures à dépendances et l’abaissement async restent ouverts.

### Handles et contextes async en région

Un lancement natif produit un handle déplaçable. Les liaisons,
les réceptions de bloc et les appels mettent à jour la responsabilité
de nettoyage sans déplacer l’état. Le runtime restitue la région
après un join ou coordonne l’abandon et la terminaison d’une tâche
autonome. Une sortie de scope abandonne seulement les tâches dont
les captures le permettent. La fin de main attend les tâches
autonomes encore actives. Le vérificateur suit les emprunts de
scalaires dans les contrats de retour, bloque les accès concurrents
et refuse la sortie d’un handle dépendant sur un chemin qui
abandonnerait la tâche.

Une fonction async crée une Future inactive en région. Les captures
prennent effet à sa création. `runtime::spawn` consomme la Future
et publie son état dans la file du runtime. Deux pollers peuvent
reprendre une tâche après `yield`. La reprise restaure son contexte
de datastack, ce qui conserve l’adresse et la limite de ses
collections locales. Le plan post-AST décrit les liaisons placées
dans l’état, sa taille et les bornes de stockage de la tâche.
L’échange de contexte intervient après chaque poll, et le nettoyage
du contexte précède la restitution de la région de l’état. Les
captures empruntées restent actives après spawn jusqu’au join.
Sur échec du démarrage du runtime, la Future est nettoyée et le
join restitue `LaunchFailed`.

`python3 validation/check_rust_task_regions.py` compile dix témoins
C11 avec pthread et UBSan à `-O0` et `-O2`. Neuf refus ciblés
confirment les réservations des captures, l’interdiction de les
abandonner, les frontières de scope et la consommation du handle.
Les témoins couvrent le succès, l’échec de démarrage injecté,
l’abandon autonome, la coexistence d’un thread et d’une Future
empruntant des cibles différentes et la croissance de collections
à travers des suspensions. Les 68 témoins précédents passent
également sous UBSan aux deux niveaux d’optimisation.

La vérification porte sur les emprunts de scalaires et les
suspensions `yield` au niveau du corps async. Elle ne force pas une
migration vers un poller différent et ne couvre ni `.await`, ni les
suspensions imbriquées, ni les captures et résultats agrégés à
dépendances. La tentative ASan sur un témoin mixte n’a fourni aucun
résultat. Un programme C minimal sous ASan, limité à créer et
joindre un pthread, a également dépassé son délai. L’audit
indépendant n’a pas été exécuté.

## Attente directe et agrégats empruntés dans le backend Rust

Le plan post-AST numérote les sites de suspension et associe à l’état
régional les temporaires et marques de scope. Un `.await` direct consomme
une Future inactive et la poll sur le worker courant. Si l’enfant suspend,
le parent sauvegarde son état et reprend au poll de ce même enfant. À la
complétion, le résultat est transmis dans un emplacement du parent avant
de rendre la région de l’enfant. Les marques conservées dans l’état
permettent aux blocs, branches, `break` et `continue` de restaurer les bons
curseurs après reprise.

Les captures et résultats fixes contenant des emprunts sont stockés dans
l’état. La Future porte deux ensembles distincts : les dépendances actives
pendant l’attente et celles que le contrat du résultat projette sur le
receveur. Les branches et sorties de boucle conservent ces informations.
Un témoin retourne un seul des deux emprunts capturés et écrit sur l’autre
cible avant le dernier usage du résultat. Un autre traverse deux niveaux
d’attente avec un agrégat à emprunt. La première exécution du témoin de
boucle a révélé un déplacement de l’indice : le témoin utilise désormais
`copy(i)`, conformément à la règle de passage par valeur.

Validation exécutée : `cargo build --offline` du frontend Rust ;
`python3 validation/check_rust_task_regions.py` (15 programmes exécutés,
13 refus) et les suites `check_rust_{datastack_capacity,native_regions,
placement_dependencies,region_collections,regions}.py` (53 programmes
C supplémentaires). Les témoins utilisent C11 avec UBSan à `-O0` et
`-O2`. Ils exercent entre autres la consommation de l’enfant, la
réutilisation d’un slot régional et le refus d’un résultat vers une cible
locale. La migration entre pollers n’est pas imposée par le témoin.
ASan et l’audit indépendant n’ont pas été exécutés dans cette passe.

Limites : agrégats possédant une ressource à nettoyer, résultats dépendants
via `join()`, appels synchrones depuis le corps async et
`runtime::AsyncHandle.await` restent ouverts dans ce backend.

## Ressources et complétions de tâches dans le backend Rust

Le plan post-AST reste responsable des emplacements de résultats et des
marques qui survivent aux suspensions. Pour un agrégat fixe qui possède des
`A<T>`, le code généré transfère la responsabilité de chaque slot à
travers le registre de nettoyage de la tâche, sans déplacer la donnée du
pool. Le nettoyage de l’état distingue les captures d’une Future inactive
du résultat d’une Future terminée. Un transfert réussi rattache les slots
au receveur avant qu’il puisse les utiliser ; un abandon ou un échec
détruit ce que l’état possède encore. Le match consommant transfère la
charge au champ lié par `Ok` ou la détruit si le motif l’ignore.

Les contrats distinguent les dépendances d’exécution du handle et les
dépendances de son résultat. Ces dernières traversent une signature
typée et sont attachées au chemin `Ok` du `Result<R, runtime::Error>`.
Le chemin `Err(LaunchFailed)` ne transporte aucune dépendance de résultat.
Les threads natifs peuvent aussi rendre une valeur fixe à emprunts.

`spawn_blocking` lance la Future sur un thread dédié en contexte async.
L’attente enregistre le poller racine avant de se suspendre, même si elle
se trouve dans une Future directement attendue. La transition vers le
sommeil et la notification de complétion partagent le même verrou. Une
notification arrivée avant le sommeil est conservée ; après le sommeil
elle remet le poller dans la file. La complétion publie le résultat
avant le réveil. Le chemin `LaunchFailed` nettoie les captures avant de
rendre la main.

Validation : compilation Rust hors ligne ; témoins de
`check_rust_task_regions.py` (27 programmes, 18 refus) sous C11/pthread/UBSan
à `-O0` et `-O2`, et les cinq suites Rust de placement, capacité, régions,
collections et threads natifs (53 témoins C supplémentaires). Les témoins forcent les deux ordres entre réveil et mise
en sommeil, injectent les deux échecs de lancement, lisent un résultat à
emprunt après un relais typé, et réutilisent les slots des captures et
résultats. La première exécution de l’agrégat à deux slots a révélé une
confusion entre la dépendance au pool et son emprunt exclusif ; les
contrats conservent désormais cette distinction.

Limites : un slot de pool ou un élément agrégé de vecteur ne peut pas
encore contenir lui-même des `A<T>`. Les threads natifs ne transfèrent
pas de slots propriétaires. La migration entre pollers, ASan, TSan et
l’audit indépendant ne font pas partie de ces preuves.

## Nettoyage composé des slots possédés

Le backend réutilise le parcours des champs propriétaires à l’insertion
dans un pool ou un vecteur. Il rattache les slots trouvés au registre
d’enfants de l’allocation receveuse. Le registre du scope ne contient
alors que les racines. Le déplacement d’une racine, y compris dans une
Future, emporte son sous-arbre sans déplacer les données. Le runtime
parcourt les enfants avant de rendre la région et le slot du parent.
Il réutilise les liens des enfants retirés pour reprendre le parcours,
sans augmenter la profondeur de la pile C. Le plan post-AST garde les
mêmes emplacements et marques. L’analyse des emprunts exclusifs
mémorise les types visités lorsqu’un type se référence via `A<T>`.

Validation sous UBSan à `-O0` et `-O2` avec les six suites
`check_rust_*.py` du backend. 84 programmes C exécutés, dont quatre
nouveaux témoins, et 54 refus confirmés, dont trois nouveaux. Une trace
au point de restitution observe deux fois le même ordre dans un pool
récursif. Le slot terminal est rendu, puis les deux slots de lien du
plus profond à la racine. Les autres témoins couvrent le champ actif
d’un enum, le trajet pool → struct → vecteur → struct → pool et la
transmission d’un sous-arbre à travers `.await`. Les refus couvrent
la sortie d’un pool source trop court, sa destruction explicite et
l’insertion dans un vecteur qui lui survivrait. Les emprunts stockés
restent utilisables après nettoyage si leur cible vit encore.

Ce cycle vérifie le nettoyage généré par le compilateur pour les slots
et les régions. Crust ne prend pas en charge les destructeurs définis
par l’utilisateur. ASan, TSan et l’audit indépendant ne font pas partie
de cette validation.

## Provenance et résumés du post-AST Rust

Le post-AST conserve le lien du temporaire reçu vers sa source et le point
du déplacement d'une liaison locale. Le résumé de dépendances réutilise
les listes internées à travers les scopes. Le résumé de placement propage
les origines par arêtes et conserve les résultats du dernier calcul des
contrats. Ce cycle porte sur la représentation du compilateur. Les règles
normatives restent identiques.

Deux tests Rust inspectent le post-AST. Le premier vérifie le déplacement
de `boite` vers `recu` à travers deux blocs, le même identifiant de résumé
de dépendances, le chemin du champ vers son pool et la réservation dans
le scope de fonction. Le second vérifie que les deux branches gardent
leurs pools et leurs origines de stockage respectifs et partagent la
destination de placement.

Commandes exécutées depuis la racine du projet.

```sh
CARGO_TARGET_DIR=build/rust_frontend cargo test --offline --manifest-path rust_frontend/Cargo.toml
CARGO_TARGET_DIR=build/rust_frontend cargo build --offline --manifest-path rust_frontend/Cargo.toml
python3 validation/check_rust_placement_dependencies.py
python3 validation/check_rust_datastack_capacity.py
python3 validation/check_rust_regions.py
python3 validation/check_rust_region_collections.py
python3 validation/check_rust_native_regions.py
python3 validation/check_rust_task_regions.py
```

| Suite C | Témoins réussis | Refus confirmés |
| --- | ---: | ---: |
| Placement et dépendances | 22 | 16 |
| Dimensionnement de la datastack | 10 | 6 |
| Régions | 9 | 3 |
| Collections à régions | 10 | 7 |
| Threads natifs | 5 | 4 |
| Tâches et reprises | 28 | 18 |
| Total | 84 | 54 |

Les suites utilisent C11 et UBSan fatal à `-O0` et `-O2`. Les témoins
incluent des sorties en erreur contrôlée, dont l'épuisement explicite de
la datastack. Aucun nouvel échec n'a été observé. Les tests internes
inspectent un transfert déterminé et une jonction à deux branches.
ASan, TSan, les mutations et l'audit indépendant restent hors de ce cycle.
Aucune mesure de performance n'a été effectuée.

### Mesure du coût des résumés

Les deux binaires instrumentés ont été compilés avec `cargo build --offline
--release`, Rust 1.99.1, macOS arm64. La version avant a été reconstituée à
partir des sources et des modifications du cycle précédent. Elle rétablit
le balayage jusqu'au point fixe, le second calcul des origines pour le
placement, les anciennes unions de dépendances et la représentation
précédente de `Value`. Le checkout ne contient pas l'ancien commit.

Chaque programme est lu et parsé une fois par processus. La mesure totale
entoure `verify`, qui inclut la vérification, l'abaissement et le placement.
La mesure du placement entoure `placement::plan`. La génération de C,
le lancement des processus et la destruction du résultat sont en dehors
du chronométrage total. Sur chaque cas, sept lots de 35 mesures par version
suivent huit passages de chauffe par processus. L'ordre des versions
alterne et l'ordre des cas varie. Les colonnes de temps donnent la médiane
des médianes de lot. Les gains sont les médianes des réductions appariées.
Les 11 programmes sont acceptés par les deux binaires et produisent du
C identique octet pour octet.

| Cas | Placement avant → après (µs) | Gain placement | Vérification et placement avant → après (µs) | Gain total |
| --- | ---: | ---: | ---: | ---: |
| 4 blocs imbriqués | 8,75 → 5,21 | 40,4 % | 14,83 → 11,33 | 23,6 % |
| 16 blocs imbriqués | 21,00 → 11,25 | 46,2 % | 30,58 → 20,88 | 31,5 % |
| 48 blocs imbriqués | 47,38 → 26,42 | 44,2 % | 66,38 → 46,04 | 30,6 % |
| 4 transferts en chaîne | 13,33 → 5,38 | 59,7 % | 20,83 → 13,04 | 38,0 % |
| 16 transferts en chaîne | 69,46 → 13,58 | 80,3 % | 85,96 → 30,54 | 64,4 % |
| 48 transferts en chaîne | 477,79 → 28,33 | 94,0 % | 516,62 → 68,04 | 86,7 % |
| 4 jonctions successives | 24,25 → 15,75 | 34,8 % | 47,96 → 39,46 | 17,3 % |
| 16 jonctions successives | 101,42 → 67,42 | 33,6 % | 210,83 → 174,21 | 16,5 % |
| 48 jonctions successives | 487,42 → 389,17 | 21,1 % | 1 100,42 → 1 003,71 | 8,7 % |
| 4 jonctions imbriquées | 15,67 → 10,92 | 30,2 % | 28,42 → 23,96 | 15,5 % |
| 16 jonctions imbriquées | 59,92 → 37,42 | 37,7 % | 96,21 → 74,46 | 22,3 % |

Les sept lots donnent un gain total compris entre 83,7 et 87,0 % pour
48 transferts en chaîne, et entre 0,3 et 9,6 % pour 48 jonctions
successives. Ces programmes synthétiques mesurent l'effet combiné des
changements. La contribution isolée des unions de dépendances et la
consommation mémoire du compilateur restent à mesurer.

## Plan de possession des agrégats dans le post-AST

Le post-AST sélectionne les projections qui mènent à un slot possédé.
Le générateur des parcours de nettoyage consomme cette représentation
pour les structures, tableaux et variantes. Il traduit les liens
internes en parcours d'agrégats et les liens vers les slots en appels
au runtime. L'ordre de parcours et la restitution des enfants avant
leur parent suivent les mêmes chemins que dans les témoins précédents.

Les deux tests Rust de représentation passent. Les suites
`check_rust_placement_dependencies.py`, `check_rust_datastack_capacity.py`,
`check_rust_region_collections.py` et `check_rust_task_regions.py`
confirment 70 témoins C sous UBSan à `-O0` et `-O2`, ainsi que 47 refus.
Les témoins couvrent le placement des receveurs et les réservations
par l'appelant, puis le nettoyage composé dans un pool, un vecteur et
un état async. Les sites d'adoption et de transfert sélectionnent encore
l'action à partir du type de la valeur.

## Adoption et transfert selon le plan de possession

Le générateur C consulte le plan de possession pour sélectionner le
parcours d'une valeur lors de l'adoption et du transfert, y compris aux
frontières d'appel et dans les captures et résultats async. Le type
identifie l'entrée du plan. Cette entrée détermine le parcours des
champs possédés.

Les deux tests Rust passent. Les suites placement et dépendances,
collections à régions et tâches confirment 60 témoins C sous UBSan à
`-O0` et `-O2`, ainsi que 41 refus. Le témoin instrumenté d'un pool
récursif vérifie la restitution du slot terminal, puis du lien
intermédiaire et enfin de la racine. Il observe cette séquence une
première fois, puis à nouveau après réutilisation des mêmes slots et
transfert de la racine par une sortie de bloc et un appel. La suite
async exerce le transfert d'un arbre par `.await` et la réutilisation
du pool. La trace slot par slot porte sur le témoin synchrone.

## Placement des scalaires dans leur destination finale

Le plan G1 réutilise la réservation du résultat d'un bloc ou d'un appel
pour sa liaison. Un scalaire synchrone déplacé directement vers un
receveur ou vers le résultat de la fonction peut aussi être initialisé
dans la réservation finale. Le plan vérifie que cette réservation est
accessible dès la construction, que le déplacement est unique et que
la liaison source n'est pas réaffectée. Les appels imbriqués reçoivent
l'adresse finale. Des constructions situées dans des bras exclusifs
peuvent partager la réservation. Les autres sources gardent leur
propre emplacement lorsqu'elles pourraient écraser une valeur vivante.

Deux tests Rust, 75 témoins C et 47 refus passent dans les suites
dimensionnement, dépendances de placement, collections à régions et
tâches. Les cinq nouveaux témoins instrumentent le curseur sous UBSan
à `-O0` et `-O2`. Ils observent un seul emplacement de 8 octets après
des sorties de blocs imbriquées, pour un retour construit chez
l'appelant, pour un appel imbriqué et pour deux bras exclusifs. Le
témoin à deux sources simultanément vivantes observe deux emplacements
et vérifie la valeur rendue.

Cette passe couvre les promotions directes de scalaires synchrones.
Les liaisons réaffectées ou à plusieurs déplacements gardent un
placement conservateur. Les états async utilisent leur frame et le
choix global entre plusieurs scopes finaux reste ouvert.

## G1 — chaînes de déplacements, destinations multiples et frames

Le plan suit les liaisons successives vers la réservation finale.
Pour une valeur construite avant le choix du chemin, il partage une
adresse lorsque le receveur extérieur ou l'appelant couvre tous les
chemins et que les receveurs redirigés n'ont pas d'entrée indépendante.
Pour les emplacements partagés d'agrégats, il examine d'abord les scopes
avec le plus d'origines de construction candidates et conserve les
groupes déjà formés lorsque les candidats suivants ne les couvrent
qu'en partie.

Les scalaires reçus par une Future peuvent être écrits dans leur
emplacement final dans la frame. Les pointeurs des liaisons déplacées
restent dans la frame pendant les suspensions. Une construction
d'agrégat compatible avec la réservation de résultat peut écrire dans
ce résultat directement. Les candidats à coexistence prouvée gardent
des emplacements distincts.

Le témoin de retour conditionnel d'un agrégat propriétaire épuisait le
pool. Son adresse était réservée chez l'appelant et le chemin qui gardait
l'agrégat local laissait un slot occupé après le retour. Les scopes du
runtime ont maintenant une profondeur de possession indépendante de
l'adresse physique. La réception ou le retour transfère la possession
uniquement sur le chemin exécuté. Le témoin couvre les deux chemins et
réutilise ensuite les deux slots.

Deux tests Rust et les six suites C du backend passent. Elles confirment
95 témoins C sous UBSan à `-O0` et `-O2`, et 54 refus. Les nouveaux
témoins vérifient la réservation unique à travers plusieurs liaisons,
les choix entre deux receveurs ou entre un receveur et l'appelant,
la restitution sur le chemin local et la reprise après `await` et
`yield`. Le C généré pour le témoin de retour propriétaire async contient
une construction directement dans `frame->result`.

Le plan reste conservateur pour les sources réaffectées et les chemins
dont il ne peut établir une adresse commune. Le classement des scopes
s'applique aux candidats compatibles calculés par le plan et la
sélection est gloutonne.

## G9 — placement des régions à partir du post-AST

Le plan compte les acquisitions de contenu grandissant et d'états de
tâches. Il compose leur pic à travers les scopes, les branches et les
appels synchrones. Il conserve les régions potentiellement transférées
et retire les acquisitions locales dont la libération est identifiée.
Les bras exclusifs contribuent par un maximum au pic et à la borne de
croissance par type. Le nombre de slots est calculé indépendamment
de la taille d'une région.

Les acquisitions répétées dont la coexistence reste indéterminée
et celles dans le graphe des appels récursifs prennent une région dédiée.
Le gabarit est hérité au site de construction. Un autre gabarit ouvre
une zone distincte, dont le nombre de slots peut être déduit dans le
scope si `count` est omis. Une zone annotée pleine peut déborder vers
une région dédiée du même gabarit. La limite globale explicite et la
limite de croissance d'une région déclenchent leur diagnostic existant
en cas de dépassement.

Les deux tests Rust et les six suites C du backend passent, avec
100 témoins sous UBSan à `-O0` et `-O2` et 54 refus confirmés.
Les cinq nouveaux témoins couvrent la croissance exclusive sous une
limite globale, un appel conditionnel qui transmet une seule région
pendant qu'une autre reste vivante, le contenu retenu par une boucle,
l'isolation d'un appel récursif et l'inférence locale pour un autre
gabarit. La suite async vérifie toujours le réemploi d'un seul slot
sur quatre attentes successives.

Le calcul garde des bornes conservatrices quand les identités des
régions ne peuvent pas être suivies après une jonction ou un appel.
Les appels qui héritent d'une zone annotée vérifient sa capacité
effective au moment de l'acquisition.

## G10 — recul groupé du curseur régional

La libération marque chaque slot libre sous le verrou des régions.
La sortie de scope recalcule ensuite le suffixe libre après le nettoyage
des threads, des collections et des pools. Le runtime écrit le curseur
au plus une fois par zone à cette étape. Une allocation intermédiaire
peut déclencher ce même recul avant de réutiliser la zone.

Deux témoins natifs instrumentent les écritures du curseur. Le premier
lance deux threads dans une zone annotée, les attend dans l'ordre inverse
de leur création et observe un seul recul de 2 à 0 à la sortie du bloc.
Le second conserve un vecteur entre les deux frames et le transfère hors
du bloc. Le curseur recule de 3 à 2. Le test crée un autre vecteur, puis
vérifie l'adresse du premier en le faisant grandir et relit son contenu.

Deux tests Rust et les six suites C du backend passent, avec 102
témoins sous UBSan à `-O0` et `-O2` et 54 refus confirmés. Les traces
d'écriture et le contrôle d'adresse portent sur les deux témoins natifs.

Avant le premier commit, les deux tests Rust, les six suites C du backend
et les vingt tests Python de `test_arguments.py` ont été rejoués.
Les suites C ont confirmé 102 témoins sous UBSan et 54 refus. Les sorties
de build et les caches locaux ont été retirés après cette vérification.

## G12 — Collection transférée à une tâche

Le backend Rust accepte déjà le transfert d'un `A<Vector<i64>>` créé dans
une région de bloc vers une tâche. Le résumé de dépendances du post-AST
conserve la dépendance au pool et distingue les dépendances de la tâche de
celles du résultat attendu. Dans le C généré, le transfert conserve le
descripteur de stockage de la collection et sa région d'origine.

La suite `check_rust_task_regions.py` instrumente désormais un vecteur qui
sort de son bloc, passe à une tâche, grandit après `yield` et revient par
`.await`. Le témoin compare l'adresse des données avant et après croissance
et lors des lectures du résultat. Le programme imprime 7 puis 9 sous UBSan
à `-O0` et `-O2`. Un second programme confirme le refus d'un handle qui
s'échapperait du scope du pool d'origine. La suite complète a exécuté
30 témoins et confirmé 19 refus. Aucun changement du compilateur n'a été
nécessaire pour ces deux chemins. Cette passe ne couvre pas exhaustivement
les collections et modes de lancement.

## G12 — Stabilité, emprunts et provenance

La passe couvre les trois obligations G12 sur les chemins exercés du
backend Rust. Elle complète les témoins précédents, dont le recul après
nettoyage des threads et le réemploi de slots de région.

- **Stabilité.** L'adresse des données d'un vecteur reste identique
  après transfert depuis le bloc d'origine, croissance après suspension
  et réception par `.await` ou par `spawn` puis `join()`. Le témoin
  String compare l'adresse avant et pendant la croissance sur le thread
  de `spawn_blocking`, puis vérifie la longueur après `AsyncHandle.await`.
  Un témoin HashMap compare l'adresse d'une entrée avant et après le
  transfert de la table, l'ajout d'autres entrées et le réemploi d'une
  case libérée.
- **Emprunts.** Une référence stockée dans un vecteur survit à l'aller-retour
  async. L'écriture de la cible passe après le dernier usage et le drop
  du vecteur. La variante qui écrit avant la lecture est refusée pour
  emprunt actif. La suite régionale refuse également la suppression
  d'une entrée encore empruntée.
- **Provenance.** La sortie d'un handle transportant un vecteur hors du
  scope de son pool est refusée. Les dépendances distinctes de la tâche
  et du résultat sont représentées par le résumé du post-AST existant.

Les deux suites ont exécuté 33 témoins de tâches et 12 témoins de collections
sous UBSan à `-O0` et `-O2`, et confirmé respectivement 20 et 7 refus.
La passe ajoute des régressions au backend existant. Elle laisse G12 au
statut partiel. Le backend refuse actuellement les captures et résultats
`HashMap` par valeur dans une fonction async, ainsi que les captures
possédant des slots de pool dans `runtime::thread`. Ces limitations sont
des restrictions d'implémentation. Le runtime de la table associe ses
descripteurs à une liste de nettoyage de contexte et la génération du
thread natif doit disposer d'un nettoyage des captures possédées sur
l'échec de lancement avant d'ouvrir ces chemins.

### G12 — Transferts à travers les tâches dans le backend Rust

Le plan de possession représente désormais aussi la région d'une HashMap.
Quand la table entre dans une Future, le descripteur est détaché de la liste
de nettoyage de l'appelant puis inscrit dans le contexte de la Future au
premier poll. Une sortie par valeur détache le résultat avant la fermeture
du contexte. L'attente inscrit le résultat chez le receveur. Extraire la
table de `Ok` déplace aussi son inscription. Les entrées restent dans leur
région d'origine pendant ces opérations.

Un bloc `runtime::thread` peut recevoir une allocation ou un agrégat
possédant des allocations. Le lancement détache les captures du contexte
appelant. Le worker les rattache à son contexte, et le chemin d'échec
les détruit avant de rendre le slot du handle. Le résultat possédé est
détaché à son tour et reste sous la responsabilité du handle jusqu'au join.
Le verrou des pools est actif aussi dans les programmes multithread sans
fonction async.

Les nouveaux témoins couvrent une HashMap par await direct, par
spawn/join et par spawn_blocking/await, avec une comparaison instrumentée
d'adresse à travers les deux await. Le test d'échec de spawn_blocking
réutilise l'espace de la table. Le test natif compare l'adresse du vecteur
avant lancement, pendant la croissance et après join. Un échec de
pthread_create rend le slot de l'agrégat et celui de son enfant. Un autre
programme est refusé si le handle natif sort du bloc de son pool source.

Les deux tests Rust et les six suites C du backend passent. Les suites
comptent 112 témoins à `-O0` et `-O2` sous UBSan et 57 refus.
Le statut de la matrice reflète une validation par témoins. ASan reste
bloqué sur le témoin minimal documenté dans le rapport G11.

## P1 — Pages de garde

Le backend Rust réserve les plages de données des deux datastacks en
`PROT_NONE`, puis rend accessible leur partie utilisable avec `mprotect`.
La page finale reste inaccessible. Si la capacité est inférieure à une
borne de page ou tombe entre deux pages, le runtime conserve la limite
logique et place la garde après l'arrondi à la page supérieure. Les limites
entre régions sont contrôlées par le runtime. Le démontage libère la plage
entière, garde comprise, notamment à la fin des contextes async et des threads.

Sur macOS arm64, `python3 validation/check_rust_datastack_guard.py` a confirmé
16 scénarios à chacun des niveaux `-O0` et `-O2` sous UBSan. Pour les deux
datastacks et les deux alignements, le dernier octet autorisé est accessible,
un dépassement logique émet le diagnostic Crust, et une lecture ou une
écriture dans la garde est interrompue par le système. Les six suites C
du backend passent également, soit 112 témoins et 57 refus confirmés.
Les deux bancs G11 démarrent avec le nouveau runtime. Les débits et les temps
de réservation publiés dans G11 ont été mesurés avant cet ajout.

## Seuils de restitution, free_pages et initialiseurs de pool

Le backend Rust applique les seuils facultatifs `reclaim_threshold` et
`region_reclaim_threshold` au nettoyage des scopes. `#(free_pages)` force
le traitement en dessous du seuil. Une datastack classique récupère
les pages entières du suffixe libre. La datastack à régions regroupe les
slots libérés contigus sous son mutex, en laissant les pages à cheval
sur une région vivante accessibles. Le remappage anonyme conserve les
adresses virtuelles et la garde. Si le remappage échoue, le runtime garde
la plage et peut retenter ultérieurement. Les seuils sont absents par défaut.

Les initialiseurs nommés, contextuels et nominaux de `Pool.new` partagent
la construction des champs dans le post-AST. Les champs explicites sont
évalués dans l'ordre écrit. Les champs omis reçoivent le défaut disponible,
récursivement pour les structures. Un champ `A<T>` requiert une allocation
explicite. Le backend utilise l'abaissement PoolNew existant, qui initialise
le slot depuis la valeur construite.

Sur macOS arm64, `python3 validation/check_rust_reclaim_constructors.py`
confirme cinq témoins sous UBSan à `-O0` et `-O2` et quatre refus. Le banc
instrumente les remappages pour contrôler le seuil, la demande explicite,
la région transférée entre deux trous et les sorties continue et return
après suspension. La passe ne mesure pas le débit du runtime avec cette
politique activée.

## Placement direct dans Pool.new et extraction des vecteurs

Le plan post-AST reconnaît le littéral de structure immédiatement consommé
par `Pool.new`. Ses expressions de champ restent évaluées avant la prise
du slot. Le générateur écrit les champs dans le slot et utilise le parcours
de possession existant pour adopter les allocations qu'ils portent.
Les valeurs déjà construites continuent à passer par le chemin de transfert
existant.

`Vector<A<T>>` prend en charge `pop` et `remove` dans le backend Rust.
Le runtime rattache la valeur extraite à son nouveau receveur. Le vecteur
conserve statiquement une union des provenances possibles de ses éléments.
Le témoin extrait des allocations de deux pools puis réutilise les deux
slots. L'absence de réservation intermédiaire pour le littéral Boite est
contrôlée dans le témoin des constructeurs.

Les deux tests Rust et les huit suites C ont passé la première passe.
La suite des collections est rejouée après resserrement du résumé de
provenance pour exclure le pool du vecteur de la valeur extraite.
V3 a été rejouée avec quatre programmes par `check`. ASan seul reproduit
le délai dépassé sur le témoin minimal macOS. La mesure de restitution
intégrée est consignée dans G11.

HM6 autorise des valeurs de table `&mut T` et spécifie des résultats
`&&mut T` et `&mut &mut T`. La règle de passage des références et la
production `type` du core excluent actuellement ces types imbriqués.
Le choix de la syntaxe et de la portée de leur support reste ouvert.

### Références imbriquées et HashMap à dépendances

Après arbitrage, la grammaire accepte `&&mut i64` et `&mut &mut i64`.
Le type vérifié conserve chaque mode. Le C qualifie chaque pointeur
au niveau correspondant. Une écriture à travers les deux niveaux
exige que les deux emprunts soient mutables.

Le backend Rust accepte les valeurs de table `A<T>`, `&T` et `&mut T`.
Les entrées possédées sont détachées de la liste des allocations locales
et détruites avec leur table. Une extraction ou un remplacement les
rattache au receveur. Un remplacement direct de référence via `get_mut`
ajoute la nouvelle provenance au résumé de la table et refuse une cible
plus courte. Les résultats suivent les dépendances conservatrices de la
table à travers un relais synchrone. La précision par clé et les effets
de remplacement à travers les appels restent ouverts.

La première passe a exécuté les deux tests Rust et les huit suites C.
La suite des collections a été rejouée avec le remplacement direct,
ses deux témoins supplémentaires et UBSan à `-O0` et `-O2`.

### Dépendances par clé et contrats de remplacement synchrones

Le vérificateur associe les dépendances des entrées à la position
`MapEntry` du résumé post-AST. Une clé littérale, ou déduite d'une liaison
immuable initialisée par un littéral, sélectionne son entrée. Un retrait
ou un remplacement certain supprime sa précédente dépendance. Les clés
dynamiques et les effets d'appel possiblement conditionnels conservent
l'union des provenances compatibles.

Un contrat de fonction synchrone indique quel argument peut fournir le
nouvel emprunt et quel argument désigne l'entrée écrite. Le caller
substitue les provenances réelles et vérifie leur durée de vie avant de
les ajouter au résumé de la table. Les relais transmettent le même
effet. Les effets différés de cette forme sont refusés actuellement.

Les deux tests Rust et les huit suites C passent. La suite des
collections compte 20 programmes sous UBSan à `-O0` et `-O2` et 13
refus. Les nouveaux témoins couvrent la séparation de deux clés et
un relais de remplacement. Les refus couvrent la mutation d'une cible
encore empruntée par une autre clé et une cible trop courte installée
par appel.

### Remplacements différés d’entrées de HashMap

Les captures portent les obligations de la cible et de la référence
entrante avant que la tâche ne soit exécutée. L'effet de remplacement
est enregistré sur la Future ou le handle et la durée de vie de la
nouvelle cible est vérifiée à la capture. L’attente applique l’effet
possible au résumé de la table. Le résumé conserve l’origine initiale
pour les chemins qui peuvent échouer au lancement ou éviter l’écriture.

Les témoins exécutent le transfert natif suivi de join, le lancement
bloquant suivi d’await et un échec de lancement injecté. Le témoin
d’échec relit et modifie la cible initiale. Le compilateur refuse une
cible qui ne survit pas à la table. Les contrats publics de handle
ne transportent pas encore ces effets. Les passages et retours concernés
sont refusés explicitement.

Les contrats publics transmettent désormais le remplacement via un helper
synchrone qui joint le handle, un helper async qui attend l'AsyncHandle et
une fabrique native qui retourne directement le handle. Le résumé reste
conservateur pour les effets conditionnels et LaunchFailed. Les résultats
imbriqués portant un effet et les contrats récursifs non résolus restent
hors de ce raccordement. La suite des tâches a terminé avec 42 programmes
exécutés sous UBSan à `-O0` et `-O2` et 21 refus.

Le contrat de résultat représente la position du handle et conserve
les effets lors du relais d'une fabrique native. Un appel synchrone
récursif utilise une approximation des écritures possibles à partir
des paramètres compatibles. Le témoin récursif passe sous UBSan.
Les deux tests Rust et les huit suites C ont terminé sur ce lot.
Les suites collections et tâches ont confirmé respectivement 21 et 42
exécutions sous UBSan, ainsi que 13 et 21 refus. Le témoin ASan minimal
reste bloqué sur l'hôte. Les formes de handles imbriqués ou récursifs
hors du périmètre du backend restent ouvertes.

### Handles imbriqués et récursifs dans le backend Rust

Les agrégats fixes conservent les dépendances de chaque handle à la position
du champ, de la variante ou de la case. Les dépendances du résultat attendu
gardent un chemin distinct. Le parcours de possession suit les mêmes positions
pour déplacer les handles entre scopes et contextes d’exécution. Une attente
complète les effets du handle consommé. Si le résultat contient un autre
handle, ses effets restent attachés à ce résultat jusqu’à sa propre attente.

L’analyse ordonne les corps par leurs appels. Dans un cycle d’appels, un relais
de handle est vérifié avec une hypothèse de conservation des chemins que son
contrat final doit respecter. Pour les écritures récursives, le résumé
conservateur associe les paramètres cibles aux sources de type compatible.
L’attente d’un appel async applique ce résumé, et l’incertitude de lancement
conserve la provenance initiale aux côtés de celles que l’écriture peut
installer.

La suite des tâches couvre le retour d’un handle depuis un worker natif ou une
Future, les attentes récursives sync et async, la récursion mutuelle, un
tableau de handles, un enum récursif par indirection de handle et la capture
d’un handle autonome par un thread. Le
témoin avec échec de lancement injecté relit la cible d’origine. Les refus
vérifient l’abandon d’un handle imbriqué dépendant et l’accès à une cible
encore réservée après le retour du handle.

Le backend conserve des limites pour les pools et vecteurs de handles, les
relais récursifs qui reconstruisent les chemins ou combinent attente et
restitution, et la capture d’un handle dépendant par un lancement qui
pourrait l’abandonner en cas d’échec. Les résultats exécutés portent sur
les chemins testés. L’état d’un audit indépendant reste distinct.

Validation de ce lot : deux tests Rust et huit suites C réussies. La suite
des tâches compte 53 programmes exécutés sous UBSan à `-O0` et `-O2` et
24 refus confirmés. Aucun résultat ASan n’a été recueilli pour ce lot.

### Handles en collection et contrats des cycles récursifs

Les pools et les vecteurs adoptent les handles des valeurs qu’ils reçoivent.
Leurs opérations d’extraction transfèrent les ressources vers le scope qui les
reçoit. Le déréférencement par valeur d’une allocation de pool contenant un
handle consomme l’allocation entière et rend son slot. Pour les vecteurs,
`remove` décale aussi les chemins de dépendance des éléments suivants.
La destruction détache les handles autonomes en dehors du verrou de pool,
car le résultat d’un handle peut à son tour nécessiter ce verrou.

Le vérificateur analyse les cycles du graphe d’appels jusqu’à stabilisation
des contrats de retour, d’attente et d’écriture. Les chemins de résultat
peuvent différer de ceux des arguments. Quand une branche attend un handle et
qu’une autre le restitue, le résumé ajoute les écritures possibles de
l’attente et le résultat continue de réserver les captures sur le chemin
où il contient le handle. `LaunchFailed` conserve la provenance initiale.

L’analyse exige une position prouvée pour retirer un handle dépendant d’un
vecteur et refuse les cycles dont les contrats ne se stabilisent pas dans
la borne d’analyse. Le test de déplacement dans le vecteur retire d’abord
un élément frère puis attend le handle décalé. Les deux chemins du relais
récursif sont exécutés, ainsi que le passage de handles async par le pool
et le vecteur avec suspension. L’abandon d’un vecteur qui porte encore un
handle dépendant est refusé.

Les deux tests Rust et les huit suites C ont terminé. La suite des tâches a
confirmé 58 programmes et 25 refus. Deux témoins ajoutés en fin de passe,
sur les handles async et l’extraction d’un enum en collection, ont ensuite
terminé avec le même exécutable et les mêmes options. Total : 60 programmes
exécutés sous UBSan à `-O0` et `-O2` et 25 refus. Aucun résultat ASan
n’a été recueilli pour ce lot.

### Déduction de la case unique et vidage d’un vecteur de handles

Avec une longueur prouvée de un, la continuation de `remove(index)`
transfère les dépendances de la case zéro. Le code généré conserve le calcul
de l’indice et son contrôle de borne.

Un `match handles.pop()` raffine l’état du vecteur dans le bras `None` :
la longueur vaut zéro et les dépendances des cases sont retirées. Tant que
le vecteur peut encore contenir un élément, l’analyse conserve les
dépendances possibles des cases restantes. Le point fixe de la boucle
combine les états de chaque sortie. Un `break` dans `Some` peut donc
conserver un emprunt actif malgré le `join()` du handle extrait.

Les témoins couvrent un indice reçu en paramètre, une longueur qui dépend
d’une branche et un `break` après le premier `join()` qui laisse
potentiellement un handle dépendant dans le vecteur. Le raffinement
s’applique à un `pop()` directement scruté par `match`.

Les deux tests Rust et les huit suites C passent. La suite des tâches
confirme 62 programmes sous UBSan à `-O0` et `-O2` et 26 refus.
L’appel du témoin de case unique avec l’indice 1 s’arrête à l’exécution
avec le diagnostic « indice hors du vecteur ».

### Types nommés et appels qualifiés dans le parseur Rust

Le parseur partage la liste d’arguments entre les types nommés et les appels
sur un type paramétré. Les appels `MonType::new()`,
`HashMap<i64, Point>::new()` et `geo::Boite<Option<Point>>::new()` ont le
même nœud d’appel qualifié. Les comparaisons conservent leur syntaxe.

Trois tests Rust et la suite de régression des collections passent.
Les témoins avec types utilisateurs vérifient l’AST. La résolution et le
typage de ces appels relèvent du vérificateur existant.

### Régression du parseur sur le corpus

Le corpus régénéré depuis la documentation, les fichiers Crust et les
littéraux des tests Python sélectionne 2 763 occurrences reconnues par
la référence Python. Le parseur Rust en accepte 2 755. Les huit refus
étaient déjà présents dans le rapport précédent et correspondent à
des chaînes qui nécessitent un assemblage par le test.

Une seconde passe compare le parseur de `fdb71ff` au parseur modifié sur
10 311 occurrences candidates, y compris les littéraux des scripts de
validation Rust. Chacune est essayée comme programme, bloc ou signature.
Les deux versions reconnaissent 3 110 occurrences et aucune occurrence
reconnue auparavant n’est perdue. Cette comparaison porte sur les
sources présentes dans le dépôt et les modes de syntaxe exécutés.

Les huit suites de validation du compilateur Rust passent également,
y compris leurs programmes assemblés.

### Documentation layout and README examples

The main README is in English, with a French version in `docs/README.fr.md`.
Each README contains four Din examples and one Rust example. The four Din
examples in each version were emitted as C, compiled and executed. The
Rust example was compiled with `rustc` and run against an assertion for
three elements.

The corpus skips blocks explicitly marked as Rust-only. After rebuilding
the corpus, the Rust parser accepted 34 documentation snippets, 38 Crust
files and 2,686 Python literals. The eight historical partial Python
literals still produce the same parser refusals.
