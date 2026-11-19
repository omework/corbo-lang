[English](GROWING_REGIONS_CYCLE.md)

# Cycle documentaire — data stacks et régions grandissantes

Date : 4 novembre 2026.

Correction documentaire du 5 novembre 2026 : le nom retenu pour l'annotation
est `stack_region_max_size`. Les exemples normatifs, P2 et la ligne G6 de la
matrice ont été harmonisés, sans changement de comportement, d'héritage ou de
portée de la limite. Aucun code ni test modifié par ce renommage.

## Portée demandée

Consigner les décisions validées, puis reprendre le chantier suivant sans
implémenter. AGENTS.md et VALIDATION_GUIDELINES.md ont été lus. Ce cycle est
documentaire : aucun compilateur, runtime, test ou exemple exécutable modifié.
Il ne constitue pas un cycle complet de validation du langage selon les guidelines.

## Résultat documentaire

- GROWING_REGIONS.md : douze identifiants G1–G12, décisions et questions ouvertes.
- LANGUAGE_RULES.md : intégration normative et clarification P2/P5/P7.
- README.md : lien et distinction entre conception et implémentation.
- VERIFICATION_MATRIX.md : obligations futures pour chaque identifiant, statut N.

Les choix sont la croissance au sommet quand elle convient, deux curseurs opposés,
des régions de même gabarit sous annotation héritée et le recours à une stack
dédiée si le placement courant ne convient pas. Le maximum de région est distinct
du maximum de stack ; le transfert conserve le gabarit et ne déplace pas la valeur.
Les régions réemploient la politique de slots des pools sans réintroduire reset.

## Interactions et contre-exemples à vérifier ultérieurement

- Construction après réservation anticipée : ne pas avancer ses effets.
- Restaurer les curseurs d'un enfant alors qu'une région a été transférée :
  invaliderait une allocation vivante et doit être empêché.
- Transférer d'un scope configuré 4M vers un parent configuré 1M : ne pas réduire
  la région ni déplacer son contenu ; conserver sa dépendance de stockage.
- Calcul de croissance incluant alignement : deux curseurs apparemment séparés
  peuvent néanmoins ne pas laisser assez d'espace ; refuser avant écriture.
- Réutiliser une région intérieure libérée, puis réutiliser aussi son entrée
  d'index après recul de curseur : ne jamais attribuer deux fois le même espace.
- Une annotation fournit une taille par région, pas une borne sur la population
  vivante ; ne pas en déduire un espace total suffisant sans autre analyse.
- Un espace libre d'un gabarit différent n'est pas automatiquement réutilisable
  comme un slot du gabarit courant.
- Dépassement d'une région existante : ne pas contourner la limite en déplaçant
  son contenu sur une nouvelle stack ; ne pas confondre ce cas avec le choix
  initial d'une stack dédiée.
- Accès via un emprunt, un objet référent ou une tâche : préserver cibles, sources,
  exclusivité et stabilité malgré croissance, transfert et réutilisation voisine.
- Allocations/libérations concurrentes : la politique région/slot ne remplace
  pas le protocole de synchronisation exigé par MT7.

Ces scénarios sont issus de l'analyse documentaire. Aucun n'est présenté comme
un contre-exemple exécuté sur une implémentation de régions.

## Questions laissées ouvertes

Les unités M/G, tailles par défaut, alignement et métadonnées, représentation
descendante, coexistence des gabarits, décision statique/runtime de placement,
création et durée de vie des stacks dédiées, et API des collections restent à
définir. Aucun gain de performance n'est affirmé ; des mesures seront nécessaires.
La règle initiale proposée pour les structures n'est pas validée par ce cycle.

## Vérifications et limites

Une vérification documentaire contrôle les identifiants, leur correspondance
dans la matrice, les liens locaux et l'équilibrage des blocs de code. Elle ne
valide pas la sémantique, les ancres Markdown ni la compilation des snippets.
Résultat exécuté : 12 identifiants uniques, 12 lignes correspondantes au statut N,
145 liens locaux vers des fichiers existants et blocs de code équilibrés dans
les cinq documents concernés.

Programmes exécutés, nouveaux tests d'acceptation/refus, modèles indépendants,
génération aléatoire, mutations et sanitizers : aucun dans cette passe.
Les douze règles sont non implémentées et non vérifiées par exécution ; les
preuves historiques du pool à slots fixes ne couvrent pas ces extensions.

## Primitives des deux fronts dans le C émis

Le runtime émis par Crust dispose de `GrowthStack` et de `GrowthSpan`.
Une stack réserve sa plage avec le mécanisme existant de `source_stack`.
Un front est associé à un descripteur C à adresse stable. Son ouverture
vérifie l’alignement et réserve uniquement le padding qui tient dans
l’espace disponible. Une extension vérifie le nombre d’éléments par
division avant de calculer le nombre d’octets. Un échec interne laisse
les curseurs inchangés. Le retour du front à son curseur initial
préserve l’autre front. Une fermeture avec un front vivant ou une
restitution par un descripteur copié produit un diagnostic.

Ce choix de représentation est interne. Le C retourne l’adresse du
bloc ajouté, y compris au front descendant. La future collection
devra définir l’ordre logique de ses éléments et appeler la restitution
après leur nettoyage. Le cycle ne fixe ni ABI de collection, ni
politique de placement automatique, ni API source. Il ne mesure pas
le nombre de pages résidentes.

`test_growth_runtime` compare les opérations à un modèle Python par
intervalles, avec 180 transitions générées par la graine 2219. Il
contrôle les adresses et les octets vivants, puis l’ajustement exact,
l’alignement, les demandes extrêmes, la restitution et les deux
diagnostics. Le test et les deux oracles UTF-8 ont réussi sous Clang
C11 et UBSan bloquant, à `-O0` et `-O2`. Trois mutations du C
temporaire ont été détectées aux deux niveaux, refus erroné de
l’ajustement exact, absence de restitution du curseur bas et
acceptation d’un descripteur copié pour grandir.

Les 140 régressions du cycle UTF-8 précédent ont réussi. Les suites
tableaux fixes, destruction et exigences de pools sont relancées
sur le C qui inclut ces primitives. Le placement par scope,
les sous-stacks à gabarit fixe et leurs index de réemploi, les
transferts et les emprunts de collections restent à intégrer.

Les 103 tests de cette régression tableaux fixes, destruction et
exigences de pools ont terminé avec succès.

## Régions bornées d’un même gabarit

Le runtime C associe une plage de slots à une classe de régions.
Chaque région a une capacité fixe, une longueur utilisée indépendante
et un descripteur à adresse stable. La limite comptabilise les octets
utilisables. L’en-tête et le padding de placement restent en dehors de
cette limite dans la représentation interne. Le pas est aligné sur
`max_align_t`. Le descripteur est associé à son slot, ce qui empêche
une copie du descripteur d’étendre ou de restituer la région.

Le placement réutilise la logique de slots des pools existants.
Il privilégie le curseur, consulte l’index lorsque la plage est
pleine, puis retire de l’index les slots récupérés par recul du
curseur. Le contenu grandit dans sa propre région, sans déplacer
les octets existants. Le code qui utilise le runtime doit nettoyer les
éléments avant de restituer le slot. La classe a sa propre plage
virtuelle. Sa coexistence avec d’autres classes et avec les deux
fronts, ainsi que le placement automatique depuis un scope, restent
à intégrer.

Les deux tests `test_growth_runtime` ont réussi sous Clang C11
et UBSan bloquant à `-O0` et `-O2`. Le modèle de régions utilise
220 transitions générées, graine 6077, et compare les slots,
le curseur, les adresses et les octets encore vivants. Des cas
déterministes couvrent la limite exacte, le dépassement, la
fermeture prématurée et un descripteur copié. Trois mutations du C
temporaire sont détectées aux deux optimisations, réemploi trop
tôt d’un trou, suffixe laissé dans l’index et refus de la taille
exacte. Les tests de régression tableaux fixes, destruction et
exigences de pools sont relancés après le partage de la logique
de slots.

Les 103 tests de cette régression ont terminé avec succès.

## Configuration lexicale et placement de secours

Le parseur reconnaît `#(stack_region_max_size=4M)` avant un bloc
instruction ou expression. Le compilateur transmet la limite aux
scopes lexicaux enfants, permet un remplacement local et restaure
la limite après la sortie du bloc. Une fonction conserve sa
configuration lexicale quand elle est appelée depuis un bloc annoté.
Le prototype interprète provisoirement M et G en puissances de 1024,
avec une borne de calcul de 2^63−1 octets. Ces choix d’implémentation
ne fixent pas les unités normatives ni la comptabilisation future
des métadonnées.

Le C émis propose deux entrées internes de placement. Sans gabarit,
il essaie le front bas puis le haut s’il reste de quoi placer un
élément, puis une stack dédiée dont la capacité est fournie par
l’appelant du runtime. Avec un gabarit, il essaie un pool de régions
compatible, puis un pool dédié d’une seule région de la même taille.
Le choix se fait avant l’ouverture du contenu. Un dépassement
ultérieur échoue sur la plage choisie. Le placement et l’annotation
sont testés séparément. Le compilateur doit encore relier la
configuration de scope au stockage des collections qu’il émet.

Cinq tests ciblés ont réussi. Les tests de scopes vérifient
l’héritage, les branches, le bloc expression, l’isolation de l’appel
et six formes invalides. Les tests C sous UBSan à `-O0` et `-O2`
vérifient les deux fronts, la limite de la région dédiée, la
réutilisation du pool et la conservation des adresses vivantes.
Le test détecte une mutation qui autorise la réutilisation d’un
gabarit incompatible. Le test de scopes détecte également l’héritage
erroné de la configuration de l’appelant. Les régressions arguments,
conditions, expressions if et destruction sont relancées.

Le placement est désormais raccordé à `String` et à la limite du
scope de construction. Le rapport [UTF8_STRINGS_CYCLE.md](UTF8_STRINGS_CYCLE.md)
détaille les choix provisoires de capacité, le transfert et les
vérifications de destruction.

### Rétablissement du test lexical G6–G7

La suite globale a signalé une erreur reproduite par
`python3 -m unittest discover -s tests -p test_growth_annotations.py -v`.
La surcharge de test ScopeRecorder.statements échouait avec
TypeError lorsque le compilateur lui transmettait expected_array.
Elle transmet désormais les paramètres de la méthode de base.
Les assertions sur les limites, les scopes et les entrées
invalides ont été conservées.

`python3 -m unittest discover -s tests -p 'test_growth*.py' -v`
a réussi 20 tests. Les tests natifs de cette suite utilisent
C11 avec UBSan fatal à -O0 et -O2. Les deux tests d’annotation
ont aussi réussi après l’alignement final de la signature.
Cette correction restaure une vérification G6–G7 du compilateur
sans modifier la politique de placement.

### Alignement des régions dans une réserve de capacité impaire

L’oracle G4/G8 qui partage une réserve entre une classe de régions
et deux fronts a été rejoué avec une capacité logique augmentée
d’un octet. Avant correction, UBSan signalait un accès à un Cell
mal aligné à -O0 et -O2. Le backend mmap arrondit les pages, mais
la recherche des régions part de la capacité logique. Le placement
aligne maintenant sa borne haute avant de calculer l’adresse du
premier slot. Les autres classes restent alignées car leur pas
et leur borne le sont déjà. Le test vérifie aussi la collision,
les adresses encore vivantes et le réemploi après nettoyage.
Le contre-exemple initial détecte la suppression de cet alignement.

La suite a également reproduit un TypeError dans l’observateur
des annotations. Le test transmet désormais les arguments
supplémentaires du vérificateur sans dupliquer sa signature.
Les assertions sur l’héritage et l’isolation des scopes sont intactes.

Le cas natif G4/G8 et le filtre de régions des règles fondamentales
ont réussi. La capacité impaire est exercée via le runtime C émis.
La capacité par défaut des collections dans Crust reste un multiple
de page sur les configurations testées.

La suite `test_growth*.py` a réussi ses 20 tests après correction.

### Réservation anticipée avec des trous au curseur maximal

G1/G8. La réservation de transfert compte les places libres
du pool de descripteurs et de la classe de régions, y compris
les trous de leurs index. Elle n’anticipe que si le nombre
nécessaire de places reste disponible pour les temporaires.
Le chemin ordinaire d’allocation continue de privilégier le
curseur tant qu’il reste des slots au-delà.

L’oracle C remplit un pool et sa classe de régions, puis
libère deux slots intérieurs. Une réservation qui devrait
laisser deux places est refusée. Celle qui doit en laisser
une utilise le premier trou, puis le temporaire utilise
l’autre. Le test contrôle les adresses jusqu’au nettoyage.
Il passe sous Clang C11 avec UBSan fatal à -O0 et -O2.
Deux mutations recalculant la capacité disponible à partir
du seul curseur font échouer l’oracle aux deux niveaux.
La sélection des réservations émises par le compilateur
a réussi cinq tests. Le réemploi anticipé des deux trous
est exercé directement via le runtime C émis.

La suite `test_growth*.py` a réussi 21 tests.

### Placement anticipé autour d’un push_str littéral

G1/G8. Le programme Crust avec trois String et deux trous
intérieurs montrait que la réservation testée dans le C
n’était pas émise dès qu’une construction était suivie
d’un push_str. Le planificateur sait désormais traverser
un push_str de littéral sur un String construit dans le
bloc par un pool identifié. L’opération reste à sa place
dans le programme généré. Le planificateur garde le placement
ordinaire pour un push_str dont l’argument est une vue.

Le contre-exemple échouait sur l’ordre des adresses des trous
avant correction. Après correction, sous Clang C11 à O2 et
UBSan fatal, le temporaire et la valeur transférée occupent
chacun la place attendue. La valeur conserve son adresse
au transfert. Le programme affiche le contenu transféré et
celui du String resté vivant. Le cas avec vue empruntée
vérifie l’ordre d’allocation du placement ordinaire et les
mêmes contenus. L’oracle C du cycle précédent couvre
séparément l’adresse du contenu dans la région.

Les filtres de réservation du compilateur et de croissance ont
réussi respectivement 6 et 21 tests.

### Réservation anticipée à travers un match nominal

G1/G8. Un match non consommant peut partager une réservation
de transfert entre ses bras. Le plan retient les constructeurs
possibles et leurs temporaires, et exige une source commune.
Les liaisons des champs du bras masquent les noms de l’extérieur
pendant cette recherche. La construction reste dans le bras choisi.

Le test source exécute les deux variantes et vérifie que la région
de String est anticipée, que le descripteur précède le temporaire
et que l’adresse et le contenu survivent au transfert. Avec une
place disponible, le temporaire se construit avant le diagnostic
sur le constructeur suivant. Avec des pools différents selon le
bras, le test exécute le placement ordinaire. Les exécutions
utilisent clang C11 à O2 et UBSan fatal. Sur copie temporaire,
ignorer le match dans le plan fait échouer la vérification des
deux variantes. Mutation détectée. Le filtre de réservation du
compilateur a réussi sept tests. Les match consommants restent
hors de ce plan car ils peuvent libérer le slot du sujet.

La suite de croissance a réussi 21 tests.

### String sur les deux fronts

G2–G4, G9, G12 et TX. String partage maintenant le placement
à deux fronts des autres collections. Les vues reprennent le
sens déjà prévu par CrustText. La découpe et la lecture suivent
l’ordre logique. Le pop décode dans cet ordre. Le remplacement
valide d’abord le texte prospectif, puis écrit les octets selon
le sens de la destination. La réservation anticipée peut
utiliser le front descendant pour un String avec un temporaire.

L’oracle de placement contrôle deux String dans la réserve
partagée et un troisième sur une plage dédiée. Il vérifie
les octets et l’adresse stable du premier octet après ajout.
Le modèle Python de remplacement, graine 3581, rejoue ses
183 cas sur région et sur front descendant, puis exerce
un ajout et un pop d’un char sur quatre octets. Les deux
oracles passent sous clang C11 et UBSan fatal à O0 et O2.
Forcer le sens montant dans la vue est détecté aux deux
optimisations. Le test source vérifie un String transféré
depuis le front réservé, sa découpe, le pop et son contenu.
Les suites de croissance, UTF-8 fondamentales et String
ont réussi respectivement 21, 27 et 15 tests. Le modèle
couvre les opérations internes sur les vues, indépendamment
d’une éventuelle représentation exposée à du C natif.

### Emprunt async d’un String descendant

G12 et AS12. Un test de bout en bout construit deux String
sans annotation dans le même pool. Une tâche reçoit la vue
du deuxième String, suspend son exécution et retourne une
découpe à la frontière d’un caractère UTF-8. Le premier
String peut grandir pendant que l’emprunt est réservé.
La croissance du deuxième est refusée avant join et avant
le dernier usage de la découpe. Après ce dernier usage,
la croissance est admise. Le drop permet ensuite le réemploi
du slot du deuxième String, avec conservation du premier.

Le cas ciblé réussit sous clang C11 à O2 et UBSan fatal.
Sur copie temporaire, effacer l’orientation de la vue fait
échouer la découpe lors de l’exécution du worker. Mutation
détectée. Le test exerce le partage d’une vue entre threads.
Il ne couvre pas la mutation concurrente de deux collections
détenues. Une copie figée exécute la suite globale et consigne
sa sortie dans /tmp/crust-desc-string-regression.log.

Le filtre UTF-8 async a réussi 17 tests.

### Métadonnées de croissance partagées entre threads

MT7 et G10. En mode multithread, un verrou protège la
réservation, le placement, la croissance et la libération
qui modifient les curseurs communs ou les classes de
régions. L’ordre est verrou de croissance puis verrou de
slots. Le nettoyage des éléments détenus précède la prise
du verrou de croissance. Les octets restent protégés par
les règles d’accès de Crust, et le verrou est relâché avant
la copie des octets vers une plage allouée.

L’oracle C répète 30 remplissages de deux fronts dans une
réserve de 257 octets. Il vérifie le total exact et l’absence
d’écrasement des contenus. Il exécute ensuite 400 cycles de
création, croissance et libération par thread sur deux
gabarits de régions. Il passe sous clang C11 avec UBSan
fatal à O0 et O2. Le harnais ajoute un yield entre le
contrôle de capacité et le mouvement du curseur pour
favoriser les entrelacements. En supprimant le verrou,
UBSan a signalé un débordement du calcul de pointeur.
Mutation détectée.

ThreadSanitizer a été tenté. Le binaire instrumenté
termine par SIGSEGV, y compris avec un main vide.
Il n’y a donc pas de résultat ThreadSanitizer exploitable.
L’oracle concerne le C émis. Le transfert vers une tâche
d’une collection détenue reste à implémenter côté langage.

La suite de croissance a réussi 22 tests. Le scénario
Crust d’emprunt du String descendant après join a aussi réussi.

### Correction du placement de String selon TX21

La relecture de FOUNDATIONS_AND_VECTORS.md a révélé un écart
avec TX21. Cette règle exige des vues String contiguës dans
le sens des adresses croissantes. L’extension précédente avait
placé le deuxième String sur le front descendant. Les tests
réussis de cette extension validaient son comportement interne
mais pas sa conformité à cette exigence normative.

La construction String utilise de nouveau le front montant,
une région ou une stack dédiée. Sa réservation anticipée choisit
une stack dédiée lorsque son temporaire utilise le front montant.
L’oracle de placement vérifie que deux String non annotés occupent
un front montant partagé et un front montant dédié. Les tests
du sens descendant continuent d’exercer des Vector<u8> et leurs
vues internes, dont l’orientation est explicitement représentée.
Le test async sur le deuxième String est renommé pour refléter
son stockage dédié. Ses obligations d’emprunt restent exercées.

Les statuts historiques obsolètes de la matrice et du document
async ont été rapprochés de leurs lignes et rapports actuels.
Aucune règle normative de placement n’est modifiée.

Après correction TX21, la suite de croissance a réussi 22 tests.
Le scénario source de réservation de String et celui de durée
de vie de sa vue async ont aussi réussi. Sur copie temporaire,
réactiver le placement descendant de String fait échouer l’oracle
à O0 et O2. Mutation détectée. Les tests du modèle descendant
utilisent maintenant explicitement Vector<u8> dans ce cas.
