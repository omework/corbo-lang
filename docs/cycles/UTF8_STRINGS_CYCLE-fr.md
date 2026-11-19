[English](UTF8_STRINGS_CYCLE.md)

# Cycle documentaire — UTF-8, str, char et String

Date : 5 novembre 2026.

## Demande et portée

Consigner les règles du chantier String avant de reprendre le premier cas de
Vector<T>, sans implémentation. AGENTS.md et VALIDATION_GUIDELINES.md ont été lus.
Ce cycle est uniquement documentaire : ni code, ni runtime, ni tests, ni exemples
exécutables ne sont modifiés. Il n'est pas une validation complète selon les
critères des guidelines.

## Documents et fidélité aux décisions

UTF8_STRINGS.md introduit TX1–TX20. LANGUAGE_RULES.md les intègre, le README
distingue conception et support exécutable, STRUCTURES_METHODS.md actualise son
ancien statut du chantier UTF-8 et VERIFICATION_MATRIX.md inventorie les
obligations futures. Aucun cas de Vector générique n'est déclaré validé.

Les décisions finales remplacent les propositions suivantes :

- `Str` devient `str` ; une vue textuelle est &str.
- `slice_bytes(...)` et l'emprunt automatique de découpe sont remplacés par
  `&texte[debut..fin]`. Un index simple retourne un octet, pas un char.
- Le nom d'extraction retenu est char_at, avec index en octets.
- Les itérateurs, chars et char_indices sont reportés ; utf8_len est retenu.
- Le remplacement char limité à une même largeur d'encodage n'a pas été retenu.
  Les remplacements d'octets de longueur constante sont ensuite autorisés sous
  validation du résultat complet, sans garantie du sens du texte.
- Les décalages au milieu exigent un nouveau String et un coût visible.
- truncate_bytes reste proposé, sans accord explicite ; il n'est pas ajouté.
- L'annotation retenue est stack_region_max_size ; les noms intermédiaires ne
  deviennent pas des alias implicitement acceptés.
- print de &str est finalement validé : pas de conversion préalable en char
  nécessaire pour transmettre du texte UTF-8.

## Interactions et contre-exemples prévus

Scénarios d'analyse documentaire, non exécutés :

1. "été" : byte_len=5 ; indices char valides 0/2/3, continuation lisible en u8
   mais char_at refusé avec NotCharBoundary ; fin et dépassement OutOfBounds.
2. Découpe sur frontière admise ; découpe au milieu d'un encodage refusée avant
   exposition d'une vue. Ne pas transformer une annotation &str en emprunt caché.
3. from_str sur vide/multiples valeurs scalaires ; cas combinant visuellement
   unique mais composé de plusieurs char ; résultat indépendant du stockage.
4. from_utf8 sur octets valides et invalides ; pas de remplacement automatique ;
   mutation/drop des octets sources refusés si une vue doit encore servir.
5. push/push_str avec capacité exactement suffisante et dépassement : aucune
   écriture partielle ni déplacement des éléments existants.
6. pop sur vide et sur char multi-octets : ne retirer qu'un char complet et ne
   pas libérer prématurément toute la région.
7. replace_byte sur continuation valide, index négatif/fin, résultat invalide :
   conserver le texte intégralement en cas d'erreur.
8. replace_bytes transformant C3 A9 en 61 62 : résultat groupé valide alors que
   des étapes unitaires seraient invalides ; nombre de char variable, taille fixe.
9. Source de bloc hors limites, calcul d'intervalle débordant et source empruntant
   le receveur : contrôles et restrictions d'arguments habituels à composer.
10. &mut texte[i] et texte[i]=octet refusés ; aucun accès brut au Vector interne
    ne doit permettre de casser l'invariant UTF-8.
11. Duplication indépendante d'un String, destruction de l'original et survie de
    la copie ; copy générique refusé directement et dans un champ de structure.
12. Sous-vues, transferts enfant → parent et captures async : appliquer les
    provenances et réservations existantes sans considérer leurs anciennes
    preuves comme une couverture des nouveaux types.

Ces scénarios ne constituent pas des défauts observés dans un compilateur String.

## Points ouverts et limites

Utf8Error, détails ABI, protocole de région et politique définitive d'échec des
découpes restent à préciser. La discussion a confirmé les contrôles de frontières
et la notation, mais la politique d'arrêt sur erreur de découpe a été proposée
avant correction de notation sans accord distinct ensuite ; elle est conservée
comme proposition, pas comme une décision supplémentaire inventée ici.

L'API de Vector<T> est le prochain chantier : sa construction vide sans défaut
de T n'est pas approuvée par cette seule consignation. Les méthodes classiques
supplémentaires de String ne doivent pas conduire à rejouer tous les arbitrages
mémoire ; seules les décisions nouvelles doivent être présentées à l'utilisateur.

## Vérifications de cette passe

Le contrôle documentaire porte sur les identifiants TX, leurs entrées de matrice,
les fichiers visés par les liens locaux et les délimiteurs des blocs de code.
Il ne vérifie pas les ancres Markdown ni la sémantique des snippets.
Résultat exécuté : 20 identifiants TX uniques, 20 lignes correspondantes au
statut N, 162 liens locaux vers des fichiers existants et blocs de code
équilibrés dans les six documents concernés.

Programmes compilés ou exécutés, tests de langage, modèles indépendants,
génération, mutations, sanitizers et mesures de performances : aucun dans cette
passe. TX1–TX20 restent non implémentés et non vérifiés par exécution. Les coûts
O(1)/O(n) discutés sont des objectifs algorithmiques, pas des résultats mesurés.

## Littéraux statiques, passage de vues et affichage

Le compilateur encode les littéraux UTF-8 en tableaux C statiques
immuables et les représente par adresse et longueur en octets.
Les vues passent par des paramètres et des retours &str, sans
allocation dans un pool. La longueur et print utilisent la taille
explicite. L'analyse refuse une conversion implicite vers Int et
le décodage d'un substitut Unicode isolé. Le prototype choisit
les séquences d'échappement JSON pour les littéraux.

Les essais C11 sous UBSan couvrent le texte multioctet, une
valeur sur quatre octets, un caractère combinant, le texte
vide et un octet nul intérieur. Le résultat d'une branche et
la réaffectation d'une liaison mutable conservent le type de vue.
Le modèle de largeur a exercé dix frontières de scalaires
Unicode. La mutation qui arrête l'affichage au premier octet
nul est détectée.

La couverture concerne TX1, TX3 et TX20 pour les vues statiques.
Les découpes, l'indexation d'octets, char et String restent ouverts.

## Indexation d’octets dans les vues statiques

TX2 et TX5 avancent avec `u8` et `&u8` pour les lectures de littéraux,
de liaisons `&str` et de retours de fonctions `&str`. Les deux modes
restent distincts dans les annotations et les contrats. Le C utilise
`uint8_t` et un pointeur vers octet constant. La vue est évaluée et
capturée avant l’indice. Le backend vérifie les bornes avant toute
arithmétique de pointeur, y compris pour obtenir une référence. Un
indice négatif connu ou hors d’un littéral connu est refusé avant
l’émission. Les autres accès sont gardés dans le C.

Les emprunts ne portent ici que sur les octets statiques. Réaffecter une
liaison `&str` conserve la validité de l’emprunt pris sur ses anciens
octets. Les futurs emprunts sur stockage dynamique devront suivre la
provenance et la durée de vie de ce stockage.

Cinq tests ciblés ont réussi. Les trois nouveaux tests couvrent
un parcours valide à travers plusieurs appels, dix programmes refusés
par le vérificateur et quatre arrêts natifs avec le diagnostic attendu
et sans diagnostic UBSan. Les deux autres vérifient les littéraux, la
transmission des vues et leurs diagnostics. Le test natif valide aussi
l’ordre d’évaluation de la vue et de l’indice avec une trace d’appels.

Les tableaux `[u8; N]`, les littéraux et opérations généraux de `u8`,
les receveurs de texte composés directement d’un `if`, `char`, les
découpes et `String` restent hors de cette couverture. Les états du
backend pour `&u8` statique ne constituent pas une preuve pour les
vues de longueur dynamique ou les emprunts dans des régions recyclables.

Les trois nouveaux tests ont également réussi après les derniers ajustements
du compilateur. Les suites tableaux fixes, arguments, expressions if,
mutabilité et contrats modulaires ont été lancées. Les 68 tests des tableaux fixes ont
réussi. Les 97 tests de l’autre groupe ont aussi réussi. L’oracle d’octets sous
ASan et UBSan et la mutation de la garde supérieure ont été lancés
séparément. Leur résultat terminal reste à consigner.

## Décodage de char dans le C émis

TX2, TX3, TX6, TX7 et TX20 ont maintenant des primitives dans le runtime.
Le scalaire est représenté par `uint32_t`. Les deux conversions produisent
une valeur et un statut internes, sans pool. Le décodage suppose une vue
UTF-8 valide. Il vérifie l’indice et la frontière avant de lire le scalaire,
et contrôle que sa largeur tient dans les octets restants. Cette prémisse
sera à établir séparément pour la future entrée `str::from_utf8`.

`PYTHONPATH=tests:. python3 -m unittest -v test_utf8_runtime` a réussi sous
Clang C11 et UBSan bloquant, à `-O0` et `-O2`. Le modèle encode 522 valeurs
avec Python, dont 12 cas choisis et un échantillon de graine 1439 filtré pour
exclure les substituts. Il compare les valeurs décodées, leurs largeurs et les
octets imprimés. Il exerce chaque position de continuation, les bornes
négative et finale, le texte vide et la conversion d’un texte multiscalaire.
Le test appelle directement les helpers dans le C produit par
`compile_source("")`.

Quatre mutations du C temporaire ont été détectées aux deux niveaux
d’optimisation. Elles autorisent respectivement l’indice égal à la longueur,
une position de continuation et la conversion multiscalaire, ou tronquent
les bits hauts d’un scalaire de quatre octets. Les variantes de l’oracle
sont identiques entre les exécutions.

Le type `char`, les signatures `Result<char, E>` et leur `match` restent
à raccorder au compilateur. Les succès mesurent les chemins C de ce cycle.
Les chemins d’appel, de retour et de branchement du futur type en Crust
restent à vérifier par des programmes source.

Les cinq tests source existants sur les littéraux et l’indexation statique
ont de nouveau réussi avec ces primitives présentes dans le C généré.

## Appels, résultats typés et match depuis Crust

TX2, TX3, TX6, TX7 et TX20 sont maintenant accessibles depuis le langage.
`char` est copiable et distinct de `Int`, de `u8` et de `&str`.
`char_at` et `char::from_str` produisent deux types de résultat distincts
dans les annotations et contrats, avec la même représentation C interne.
Le match instruction accepte les formes consignées `Ok(c)`,
`Err(Type::Variante)` et le bras final `_`. Le compilateur vérifie
l’exhaustivité, la famille d’erreur et les bras dupliqués.

Le sujet est évalué une seule fois dans le scope courant. Le premier
abaissement le plaçait dans un bloc synthétique, ce qui refusait à tort le
transfert d’une allocation dans l’appel qui calcule l’indice. L’évaluation
reste maintenant dans le scope source et tous les bras ont le même
parent lexical. Le scalaire d’un bras Ok est copié, sans prolonger
l’emprunt de la vue.

Cinq tests source ciblés et le modèle C de 522 scalaires ont réussi sous
UBSan bloquant. Les programmes natifs exercent toutes les variantes,
les largeurs de 1 à 4, le scalaire nul, le passage et le retour par fonction,
ainsi que la destruction et le réemploi d’un pool de capacité 1. Dix cas
invalides sont refusés statiquement. La mutation qui réintroduit un scope
synthétique pour les bras tardifs est détectée par le test de transfert
avec un diagnostic sur le parent direct.

Les suites de régression arguments, conditions, effets, résultats et
contraintes sont lancées. La couverture porte sur les deux résultats
UTF-8 et le match instruction. Le match expression, la capture générale
`Err(e)`, les autres spécialisations de Result et les vues issues d’un
stockage dynamique restent à couvrir.

## Découpes de vues statiques

TX4 prend en charge `&texte[debut..fin]`, `&texte[..fin]`,
`&texte[debut..]` et `&texte[..]`. Le receveur et les bornes explicites
sont évalués une fois, dans cet ordre. Le C vérifie la relation entre
les bornes, puis les frontières UTF-8, avant de former le pointeur.
La vue conserve l’adresse des octets d’origine et une longueur ajustée.
La fin est une frontière autorisée, y compris pour une découpe vide.
Le `&` est requis et la vue est immuable.

La politique provisoire reprend E2. Une borne littérale manifestement
invalide est refusée par le compilateur. Une borne dynamique invalide
provoque un arrêt avec diagnostic avant tout accès. La politique de
découpe reste à arbitrer selon la note de TX4. La règle normative est
inchangée.

Sept tests ciblés ont réussi. Ils couvrent les anciennes opérations
UTF-8 et trois nouveaux tests source avec neuf cas rejetés statiquement,
cinq arrêts natifs attendus et la trace de l’évaluation ordonnée. Les
interactions exercées incluent réaffectation de la vue, retour de fonction,
découpe imbriquée et `char_at` sur le résultat. L’oracle C sous Clang et
UBSan bloquant à `-O0` et `-O2` a comparé l’adresse et la longueur de
91 intervalles explicites et 13 suffixes issus de 13 frontières calculées
par Python. Deux mutations temporaires omettant séparément la garde de
début ou de fin ont été détectées. Chacune faisait accepter une vue
tronquée à la position d’un octet de continuation.

Les suites tableaux fixes et expressions conditionnelles ont été
lancées sur ce cycle. Les vues adossées à `String` et à des tableaux
d’octets restent à traiter avec leurs propres contraintes de durée de vie.

## Validation d’octets bruts

TX8 dispose du validateur C `text_validate_utf8`. Le décodeur borné partagé
avec `char_at` et `char::from_str` refuse les séquences tronquées,
les octets de continuation mal placés, les encodages surlongs, les
substituts et les scalaires au-delà de U+10FFFF. Le validateur lit
uniquement les octets du segment fourni et avance d’un scalaire à la fois.
Il n’alloue pas et ne corrige pas le contenu.

L’oracle `test_validation_agrees_with_python_on_raw_bytes` compare le C au
décodeur strict Python sur les 65 536 séquences de deux octets, 20 cas
ciblés et 1 024 séquences générées avec la graine 2671. Trois tests
supplémentaires bornent le même tampon à l’intérieur d’un scalaire valide,
avec les octets suivants encore présents en mémoire. Le modèle de
décodage, d’affichage et d’adresse des découpes continue de s’exécuter.
Les deux tests C ont réussi sous Clang C11 et UBSan bloquant à `-O0` et
`-O2`. L’oracle détecte aux deux niveaux d’optimisation quatre mutations
du C émis, supprimant les gardes de largeur, de longueur minimale,
d’exclusion des substituts et d’octet de continuation.

Le prédicat est interne au C. `str::from_utf8` reste à exposer avec un
résultat typé et un emprunt lié à la provenance du tableau. Tant que
l’analyse ne propage pas cette provenance, l’intégration ne doit pas
assimiler la vue obtenue à un littéral statique. Le détail d’`Utf8Error`
reste ouvert conformément à TX8.

La sélection complète des tests source UTF-8 et des deux oracles C
a également terminé sans échec. Les régressions élargies des cycles
char et découpes restent en cours.

## Tableaux fixes d’octets

Les tableaux `[u8; N]` utilisent des cases C `uint8_t`. Une constante
décimale ou hexadécimale peut initialiser une case en contexte `u8`
si elle est comprise entre 0 et 255. Une valeur `Int` obtenue à
l’exécution reste distincte. L’annotation fixe aussi la longueur.
Les lectures, écritures et remplacements réutilisent les contrôles
des tableaux fixes. Les appels et retours utilisent les mêmes modes
d’emprunt et de transfert que les tableaux d’Int. L’emprunt d’une case
reste attaché à son tableau et suit la règle existante de dernière
utilisation.

Dix-sept tests ciblés ont réussi. Les deux nouveaux tests exercent
les littéraux, répétitions, tableaux vides, lectures et écritures
via appels, transfert du tableau retourné et neuf cas de rejet,
dont les rétrécissements, les dépassements et les écritures
pendant un emprunt encore utilisé. Une sonde du C émis a vérifié
`sizeof([u8; 2]) == 2` et observé les octets 195, 97, 97 et 98
sous Clang C11 et UBSan à `-O0` et `-O2`. Elle détecte une
mutation remplaçant l’octet transmis à l’écriture par zéro.

Les 92 tests de régression du cycle découpes et les 144 du cycle char
ont terminé avec succès sur leurs versions respectives. Les suites
tableaux fixes, contraintes et effets sont relancées pour ce cycle.
Le raccordement de `str::from_utf8` reste à faire. Les signatures
d’emprunt vers une case locale de `u8` et les tableaux de telles
références restent aussi à couvrir. Le `&u8` de l’indexation d’un
`&str` statique reste distinct de ces prêts locaux dans l’analyse.

## Résultat local de str::from_utf8

TX8 est accessible depuis Crust pour un emprunt partagé de `[u8; N]`.
Le résultat local peut être nommé ou analysé directement avec `match`.
Le bras `Ok(vue)` reçoit l’adresse et la longueur des octets validés.
`Err(_)` traite l’échec sans exposer un détail d’erreur encore ouvert.
Le statut du C est interne. Le tableau vide utilise l’adresse de son
octet sentinelle C avec une longueur nulle.

Le vérificateur rattache le résultat, la vue, les découpes et les références
d’octets dérivées aux chemins d’emprunt du tableau. Un alias local conserve
ces chemins. Les expressions d’indices et de bornes gardent l’emprunt
pendant leurs appels. L’analyse permet une mutation après le dernier usage
et refuse de muter une source encore utilisée. Les vues statiques gardent
leur mode interne distinct. Les paramètres et retours interprocéduraux de
vues empruntées, la réaffectation de telles vues et les tableaux temporaires
comme source restent à couvrir.

Les 19 tests ciblés ont réussi. Le programme source combine vue dérivée,
mutation après dernier usage, échec de validation, réparation puis nouvelle
validation, et emprunt d’un tableau vide passé par fonction. Dix variantes
invalides sont rejetées statiquement. L’oracle C vérifie, en plus de la
validation différentielle, l’identité du pointeur et la longueur sur succès,
et un résultat sans vue sur échec, sous UBSan à `-O0` et `-O2`. La mutation
du compilateur qui rend inactifs les emprunts associés au résultat et aux
vues dérivées a fait accepter deux programmes que le test exige de refuser.

Les 115 tests de régression du cycle des tableaux d’octets ont réussi.
Les suites élargies ont été relancées pour la version avec `str::from_utf8`.

## Relais interprocédural des vues UTF-8

Les appels acceptent les vues `&str` et les références `&u8` issues d’un
tableau validé. Chaque argument emprunté réserve sa source pendant
l’évaluation des arguments suivants. Les deux ordres d’un conflit
entre une vue et un emprunt mutable du tableau sont vérifiés. Les
paramètres C conservent la représentation de la vue ou du pointeur.

Une fonction qui relaie ces arguments avec un retour `&str` ou `&u8`
conserve les chemins d’emprunt côté appelant. Dans cette passe,
l’appel prend l’union conservatrice de tous les arguments UTF-8
empruntés, y compris pour un résultat qui dépend d’un seul d’entre
eux ou qui est statique. L’inférence de provenance par paramètre
reste à faire. Le contrat d’un retour directement issu de la
validation d’un tableau dans le corps d’une fonction reste également
hors de cette passe.

Les 21 tests ciblés ont réussi. Le nouveau parcours natif combine
deux relais de découpe, un retour de référence d’octet et une mutation
après le dernier usage, sous UBSan bloquant. Cinq variantes invalides
sont rejetées par le vérificateur. La mutation qui retire l’emprunt
du cadre d’arguments a fait accepter l’écriture dans un argument
suivant et le passage de la source par emprunt mutable après la vue.
Les 160 régressions du cycle précédent ont réussi. Les suites
arguments, appels modulaires et tableaux fixes sont relancées.

## Provenances des retours UTF-8

Les contrats de retour `&str` et `&u8` distinguent les paramètres dont
le résultat peut dépendre. Les découpes, les emprunts d’octets, les
relais et les jonctions conservent ces dépendances. Un retour statique
a un ensemble vide. L’appel résout les provenances sur ses arguments,
et l’émission C vérifie la durabilité et les racines lorsqu’une vue
empruntée est renvoyée. Le succès de `str::from_utf8` peut maintenant
être retourné en `&str` lorsque le tableau est emprunté au parent.
Une cible locale ou temporaire ne peut pas sortir par ce retour.

Les 23 tests ciblés ont réussi. Ils incluent un relais depuis un
tableau emprunté, la mutation d’un argument indépendant avant
l’affichage du résultat, un retour statique, et deux refus d’écriture
sur les cibles possibles d’une jonction. Le C émis affiche les
octets attendus sous UBSan. La mutation du calcul de jonction qui
garde uniquement la provenance du premier bras a fait accepter
l’écriture sur le second tableau pendant son emprunt.

Les 116 régressions arguments, appels modulaires et tableaux fixes du
cycle précédent ont réussi. Les régressions des analyses et des
appels sont relancées pour ce cycle. Le passage ou retour du
`Result<&str, Utf8Error>` lui-même et la réaffectation des vues
empruntées restent ouverts.

## Transport du résultat de validation

`Result<&str, Utf8Error>` peut être reçu et retourné par une fonction.
Le contrat propage les chemins du tableau ou du résultat reçu. La préparation
d’un argument protège les octets jusqu’à l’appel. À la jonction d’une
expression `if`, le vérificateur exige le même type et conserve tous
les chemins des branches qui fournissent une valeur. Une vue ou un
résultat qui dépend d’un tableau local au bras ne peut pas sortir.

Les 26 tests ciblés ont réussi sous UBSan. Les nouveaux programmes
exercent la validation retournée, le relais du résultat entier, son
traitement dans une autre fonction et les branches de succès et d’échec
après modification des octets. Le vérificateur refuse les deux écritures
sur des tableaux possibles avant le dernier usage du résultat, les deux
sorties depuis un tableau local et la mutation dans l’argument suivant.
La mutation supprimant la réservation des résultats pendant la
préparation des arguments a fait accepter ce dernier programme invalide.

Les 124 régressions du cycle de provenance ont réussi. Les suites
arguments, appels modulaires, expressions conditionnelles et résultats
sont relancées pour ce cycle. La réaffectation des vues et résultats
empruntés ainsi que les emprunts de tableaux temporaires dans cette API
restent à traiter.

## Réaffectation de vues et de résultats

Les liaisons mutables `&str`, `&u8` et `Result<&str, Utf8Error>` peuvent
changer de source sans changer de type. Une liaison peut passer d’une
vue statique à une vue empruntée ou inversement. La nouvelle provenance
est vérifiée dans le scope du receveur. Les alias déjà créés continuent
de réserver leurs anciennes cibles. Une jonction garde les emprunts de
chaque chemin qui continue, y compris si la liaison était statique avant
la branche. Une vue utilisée à la prochaine itération reste réservée
sur la reprise de boucle.

Les 29 tests ciblés ont réussi. Les cas natifs sous UBSan exercent les
changements de source des trois types, une jonction, un ancien alias
et une boucle. Les contre-exemples interdisent les écritures avant le
dernier usage et la sortie d’une vue sur un tableau déclaré dans un
bloc enfant. La mutation qui omet de joindre les provenances lorsque
la liaison était statique a fait accepter deux écritures invalides.
Le cas de réaffectation sur un tableau durable, auparavant exclu du
prototype, est désormais couvert par les tests d’acceptation.

Les 97 régressions du cycle de transport du résultat ont réussi. Les
suites tableaux fixes, mutabilité, conditions et boucles sont relancées
pour ce cycle. La validation d’un tableau temporaire reste à couvrir.

## Validation dans l’instruction qui crée le tableau temporaire

Un tableau temporaire peut être validé dans le sujet d’un `match` ou
dans une chaîne d’appels de la même instruction. La provenance suit
le résultat, la vue et ses dérivés. Dans le match, un receveur interne
permet l’usage dans les bras tout en refusant l’affectation à une
liaison du scope qui contient l’instruction. Le stockage C est créé
dans ce scope. Un tableau temporaire créé dans un bras conditionnel
reste dans le bloc C correspondant, et sa vue ne peut pas en sortir.

Les 31 tests ciblés ont réussi. Le nouveau cas natif sous UBSan lit
la vue directement dans un match, dans un appel imbriqué et après
un retour relayé. Quatre sorties illégales sont refusées, par liaison
persistante, réaffectation depuis un bras, retour de fonction et
résultat conditionnel. La mutation autorisant toute liaison à
retenir le temporaire a fait accepter les deux premiers programmes.

Les 149 régressions du cycle de réaffectation ont réussi. Les suites
tableaux fixes, arguments, appels modulaires et expressions
conditionnelles sont relancées pour ce cycle.

## Construction, croissance et destruction de String

`pool<String>` contient les descripteurs stables. `p.new()` construit
un texte vide. `byte_len()`, `push_str(&str)` et `push(char)` sont
accessibles en Crust. L’ajout exige un receveur mutable et utilise le
même encodeur de scalaire que l’affichage. Le stockage réserve la
taille de l’ajout complet avant de copier les octets. La destruction
restitue le stockage grandissant avant le slot de descripteur, y
compris lors de la destruction à la sortie d’un scope.

Le stockage d’octets interne utilise les primitives de croissance.
L’intégration à un `Vector<u8>` générique reste à faire. Sans
annotation, le prototype réserve provisoirement 1 MiB, sur le front
montant du stockage du pool s’il est libre, sinon sur une plage
dédiée. La contiguïté et l’ordre des octets motivent ce choix du
front montant. Avec annotation, le premier gabarit est partagé
par le pool et les gabarits différents utilisent une région dédiée.
Le transfert transporte le descripteur par son adresse, avec la
même limite et les mêmes octets.

Les 46 tests ciblés ont réussi. Les nouveaux programmes Crust
combinent construction dans une fonction, mutation par emprunt,
transfert depuis un bloc annoté, destruction et réemploi. Cinq
formes invalides sont rejetées. Le test C vérifie les octets, la
limite exacte, le diagnostic de dépassement, l’adresse stable et
le retour du slot, sous UBSan à `-O0` et `-O2`. Deux mutations
temporaires sont détectées, la copie incomplète d’un ajout et
l’omission du nettoyage du stockage. Les 84 régressions du cycle
de placement précédent ont réussi.

Les vues de String, `pop`, le remplacement d’octets et la
duplication explicite restent à implémenter. Le nombre de pages
résidentes et les performances n’ont pas été mesurés.

Les 107 régressions destruction, exigences de pools et analyses
des contrats de ce cycle ont terminé avec succès.

## Vues de String et provenance interprocédurale

Les découpes `&texte[..]`, les lectures d’octets et les références
partagées `&texte[i]` utilisent les octets du String en place.
Les mêmes contrôles de bornes et de frontière s’appliquent aux
découpes. Le descripteur de vue retient l’allocation du String et
la chaîne de réemprunt. Les fonctions peuvent renvoyer une vue ou
un octet emprunté à un paramètre `&String` ou `&mut String`.
La mutation, le transfert et la destruction restent refusés
tant qu’un tel emprunt doit encore servir.

Les contrats distinguent une vue statique d’une vue adossée à
une allocation lorsque la source réelle est connue à l’appel.
Ils propagent les dépendances envers les pools pour les vues
et les références d’octets. Les tests refusent le reset suivi
d’une lecture et acceptent la lecture suivie du reset. La
mutation retirant la provenance symbolique des paramètres UTF-8
a fait accepter deux programmes invalides qui lisaient après
un reset dans une fonction appelée.

Le test C sous UBSan vérifie l’identité du pointeur de vue sur
le contenu d’un String. Les programmes Crust exercent le retour
par contrat, le dernier usage, l’indexation partagée, la duplication
explicite vers un autre String et la destruction indépendante.
Les contre-exemples couvrent également la copie depuis une vue du
receveur lui-même, la sortie d’une vue sur un String local et
l’écriture directe par index. Les opérations `pop` et de
remplacement contrôlé restent à couvrir.

Les 49 tests ciblés et les 132 régressions arguments, effets,
contraintes, résultats, appels modulaires et destruction ont réussi.

## Retrait de scalaire et remplacement contrôlé d’octets

`String.pop()` retourne `Option<char>`, avec `Some(c)` ou `None`
dans le match instruction. Le résultat est indépendant du String.
Le runtime décode le dernier scalaire entier puis recule le curseur
du front montant ou de la région. Les octets conservés gardent leur
adresse et le suffixe peut resservir.

`replace_byte` et `replace_bytes` vérifient les bornes puis valident
le texte prospectif avec le décodeur UTF-8, avant toute écriture.
L’implémentation parcourt actuellement le texte entier et utilise
une fenêtre de quatre octets. L’ancien octet est rendu pour la
version unitaire et le succès du remplacement groupé est `Ok(())`.
Les constantes de 0 à 255 sont admises en contexte `u8` pour
`replace_byte`. Le remplacement groupé emprunte un tableau fixe
d’octets. Aucun octet n’est déplacé et la longueur est conservée,
y compris quand le nombre de scalaires change.

Les deux oracles C sous UBSan à `-O0` et `-O2` comparent 120
opérations d’ajout/retrait sur chacun des deux stockages et 183
remplacements à des modèles Python. Ils vérifient les statuts,
les anciens octets, la longueur, l’adresse et l’intégralité du
contenu après les succès et les erreurs. Les deux mutations
temporaires, curseur non reculé après pop et validation omise
avant remplacement, sont détectées. Les programmes source
exercent les résultats typés, la destruction après pop, un
remplacement groupé de deux octets qui change le nombre de
scalaires et les conflits avec une vue encore utilisée.

Le match des résultats accepte les variantes d’erreur qualifiées
de `ByteReplaceError`. Les motifs généraux avec liaison d’erreur
et le match expression restent ouverts. Les régressions élargies
de ce cycle ont été lancées.

La sélection des 55 tests UTF-8, String et croissance a réussi.

## Match expression sur les résultats et options UTF-8

Les motifs existants de Result et d’Option peuvent fournir une
valeur depuis leur bloc. La jonction exige le même type pour les
branches qui continuent et conserve leurs provenances. Un bras
peut quitter la fonction avant de fournir un résultat. Le sujet
est évalué une seule fois dans son scope source, ce qui conserve
les transferts d’arguments autorisés. Les liaisons des motifs
restent dans les bras. Un alias réaffecté par un bras reste suivi
dans la suite de l’expression englobante.

Quatre tests ciblés ont réussi, dont trois cas natifs sous UBSan.
Ils couvrent un transfert et le réemploi de son slot pendant le
match, le retour anticipé, le bras joker seul, la jonction de
vues de String, et le refus d’une vue sur un temporaire qui
dépasse son instruction. Le test de bras joker vide a d’abord
détecté un échec interne du compilateur. Ce cas est maintenant
refusé avec un diagnostic source. La mutation qui ignore la
suite du scope après le match fait accepter une mutation
incompatible avec une vue réaffectée dans les bras.

Les 188 régressions du cycle pop et remplacements ont réussi.
La suite des fondamentaux et les oracles C sont relancés.
Les motifs qui lient une erreur restent à couvrir.

## Concaténation avec transfert

`destination.merge(-> source)` prépare un receveur mutable,
reçoit la source par transfert explicite et ajoute ses octets.
Après l’ajout, la source est détruite et son slot peut resservir
dans son pool d’origine. Le même contrôle de capacité précède
la copie. Une vue encore utilisée, une source identique au
receveur et la réutilisation du nom transféré sont refusées.

Les 14 tests ciblés String ont réussi, dont la concaténation de
deux String de pools différents et quatre cas invalides. Les
141 tests des fondamentaux et oracles du cycle précédent ont
réussi. Les régressions destruction, effets et contrats sont
relancées. Le stockage de String utilise maintenant le même
noyau C que les futurs vecteurs, décrit dans
[FOUNDATIONS_CYCLE.md](FOUNDATIONS_CYCLE.md).

Les 112 régressions de ce cycle ont terminé avec succès.

## Validation d'une tranche de vecteur grandissant

TX8 accepte une tranche partagée de `Vector<u8>` dans
`str::from_utf8`. Une vue issue d'un front descendant garde son
orientation dans le descripteur C. La validation et les opérations de
lecture parcourent les octets dans l'ordre logique. Le décodeur utilise
au plus quatre octets temporaires pour un scalaire et la vue continue
de désigner le stockage d'origine.

Le test Crust couvre le retour de `Result<&str, Utf8Error>` à travers
une fonction, la découpe, `char_at`, l'ajout dans une `String` et le
rejet d'un scalaire tronqué. Une insertion dans le vecteur est refusée
tant que la vue doit encore servir et autorisée après son dernier usage.
Les trois tests ciblés `from_utf8` passent sous Clang C11 à `-O2`
avec UBSan fatal.

Le modèle indépendant utilise le décodeur strict de Python. Le C teste
les 65 536 paires d'octets sur les deux orientations et vérifie les
adresses originales des octets en cas de succès descendant. Il teste
aussi 1 024 séquences de la graine 2671 et 20 cas fixes dans les deux
orientations. Les deux tests runtime passent à `-O0` et `-O2` sous
UBSan fatal. Une mutation qui efface l'orientation de la vue est
détectée. Le rapport de régression élargie est en cours dans
`/tmp/crust-tx8-vector-regression.log`. La régression précédente de
T6 a passé 338 tests.

## Remplacement atomique depuis une tranche d'octets

TX16 accepte une tranche partagée de `Vector<u8>`, y compris
comme paramètre de fonction. Le C valide le texte prospectif
dans l'ordre logique des octets source avant toute écriture.
Les sources contiguës gardent la copie groupée. Pour une tranche
descendante, le C publie les octets dans l'ordre logique après
la même validation.

Les trois tests Crust ciblés passent avec Clang C11 à `-O2` sous
UBSan fatal. Le nouveau cas vérifie un remplacement de deux
octets, les erreurs InvalidUtf8 et OutOfBounds, le remplacement
vide, l'adresse stable et le refus d'une mutation pendant un
emprunt du texte. Le modèle indépendant Python (graine 3581)
calcule le contenu et le statut attendus après chacune des
183 opérations. Les tranches descendantes alternent avec les
chemins historiques, et le modèle vérifie aussi la longueur et
l'adresse après chaque opération. Il passe sous UBSan fatal à
`-O0` et `-O2`. Une mutation qui lit la source descendante dans
l'ordre physique échoue aux deux niveaux.

La régression élargie est en cours dans
`/tmp/crust-tx16-slice-regression.log`.

## Contiguïté des String dans les régions hautes

L'audit de TX21 confirme que l'implémentation existante réserve les
classes annotées de `String` du côté haut de la datastack. Le test
C vérifie la position des classes, les octets contigus dans l'ordre
croissant, la stabilité du début de la vue, le réemploi et le refus
d'un dépassement de région. Le test étendu vérifie aussi deux String
sans annotation. La seconde emploie une stack dédiée quand le front
montant de la stack commune est occupé, et les deux textes restent
indépendants.

Le test C passe sous Clang C11 avec UBSan fatal à `-O0` et `-O2`.
Deux mutations sont détectées aux deux niveaux, le placement des
régions au début de l'espace libre et l'autorisation du front
descendant pour une String. Le scénario Crust de transfert d'une
String annotée et de réemploi de son pool passe aussi. Cette passe
ajoute une couverture au comportement existant. La régression TX8
a passé 275 tests. La suite de croissance et UTF-8 est en cours dans
`/tmp/crust-tx21-placement-regression.log`.

La suite de croissance et UTF-8 a passé 22 tests en 24,280 s.
