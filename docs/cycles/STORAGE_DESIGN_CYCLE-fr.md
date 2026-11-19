[English](STORAGE_DESIGN_CYCLE.md)

# Intégration du stockage et des transferts

## Première passe

Les décisions des brouillons 02, 03 et 05 sont reportées dans
[LANGUAGE_RULES.md](../LANGUAGE_RULES.md), [GROWING_REGIONS.md](../GROWING_REGIONS.md),
[SCOPE_EXIT.md](../SCOPE_EXIT.md) et [ASYNC_MULTITHREAD_RULES.md](../ASYNC_MULTITHREAD_RULES.md).
Les flèches explicites sont conservées selon le statut du brouillon 02.
Les changements exécutables de cette passe portent sur la consommation
des valeurs locales par `drop(-> x)`. Les cas de pool testent également
le comportement déjà pris en charge de la création typée et du transfert.

## Exécutions

- Trois tests ciblés sont passés en C11 avec Apple Clang 17 et UBSan bloquant,
  à `-O0` et à `-O2`. Les deux parcours de `drop` local donnent
  respectivement `1\n2\n3\n` et `4\n`. Le second passe par une suspension
  avant de consommer le tableau.
- Un pool de deux `Point` est passé à une fonction par `&mut Pool<Point>`.
  Après le retour de deux `A<Point>`, la destruction du premier libère un
  slot intérieur. La troisième allocation retrouve exactement l’adresse
  du premier, tandis que le second garde son adresse et sa valeur. Avec
  les deux slots vivants, la troisième allocation sort avec le code 1 et
  le diagnostic `pool capacity exceeded`.
- Le vérificateur refuse le retour d’une allocation issue d’un pool local,
  les capacités absente et nulle, la forme `drop(a)` et la consommation
  avec emprunt encore actif. Il refuse également les lectures, copies et
  doubles consommations testées après `drop`.
- Les 68 tests de régression de `test_fixed_arrays` sont passés.
- Deux mutations isolées désactivent respectivement l’invalidation synchrone
  et la consommation async du tableau. Chacune fait échouer trois refus.
  Les mutants acceptent une lecture et un second `drop`. Le troisième cas
  est une copie en synchrone et une lecture de longueur en async.

## Emplacements de tailles différentes

Le runtime mémorise maintenant la taille occupée par chaque cellule. Le recul
du curseur utilise la fin de la dernière cellule vivante. Les pools continuent
à imposer leur taille de slot et rejettent une taille incompatible.

Un modèle indépendant par intervalles, graine 9081, génère 200 opérations de
création et destruction de tailles différentes dans une plage bornée. Il compare
les adresses, les valeurs conservées, le nombre de cellules vivantes et le curseur
après chaque opération. Le test passe à `-O0` et `-O2` sous UBSan bloquant.
Le test ciblé de réemploi du pool typé passe également. Cette primitive reste
à raccorder au placement des structures locales par le compilateur.

## Limites du raccordement

Le runtime distingue également le stockage physique et la description des champs
de chaque cellule. Un test construit deux types dans une même plage, dont un
porteur d’allocation issue d’un pool. Il vérifie le nettoyage du champ détenu,
la conservation du préfixe vivant, le recul après destruction des temporaires
et le réemploi d’un emplacement avec une autre description de champs.
Les parcours normal, taille excessive et source incompatible passent à O0 et
O2 sous UBSan bloquant. Le test de modèle par intervalles et le test de pool
typé passent également après ce changement.

Deux mutations temporaires sont détectées par le test des types locaux.
La première utilise la taille fixe de la source pour calculer la fin du dernier
objet. La seconde utilise la description de la source pour nettoyer les champs.
La régression des 21 tests de régions a réussi avant l’ajout des descriptions
par cellule. Une nouvelle régression des régions et des fondamentaux est en
cours dans la session 46923, journal `/tmp/crust-local-layout-regression.log`.

La primitive `local_cell_new` reste interne au runtime. Les tests précédents
exercent le C émis avec un harnais ajouté. Ils ne démontrent pas encore la
compilation des littéraux `Point { ... }` ni leur transfert stable entre scopes.

## Raccordement des littéraux de structures

La syntaxe `Point { x: 10, y: 20 }` construit désormais une structure locale
sur une data stack implicite du scope. Les analyses des effets, résultats et
contraintes distinguent sa source locale des pools. Les descriptions de champs
ont une durée de stockage statique dans le C émis.

Une réservation interne de 16 Mio est utilisée par scope qui construit une
structure locale. Ce gabarit est un choix provisoire du backend. Son dimensionnement
et son partage avec le reste des valeurs locales restent à intégrer.

Le test `test_local_structure_literal_storage_and_borrows` compile et exécute
un programme Crust complet à O0 et O2 sous UBSan bloquant. Il exerce une lecture
empruntée suivie d’une mutation, un champ propriétaire provenant d’un pool,
sa destruction dans un bloc enfant et le réemploi du slot du pool. La sortie
est `10\n30\n9\n0\n0\n`. Quatre variantes sont refusées, pour emprunt encore
utilisé après mutation, lecture après destruction, annotation `A<Point>` sur
une structure locale et champ initialisé deux fois.

Deux programmes valides restent explicitement non pris en charge dans cette
étape. Le retour d’une structure locale depuis un bloc est refusé car son
stockage n’est pas encore réservé dans le parent. `copy(p)` sur cette structure
est refusé en attendant le placement de la copie dans le scope destination.
Ces refus constituent des écarts d’implémentation aux décisions validées.

## Transfert à travers des blocs imbriqués

Le compilateur réserve maintenant l’emplacement du résultat local dans le
scope receveur pour les blocs à résultat direct. Il suit les déclarations qui
fournissent le résultat à travers les blocs imbriqués. La réservation précède
l’exécution du bloc, tandis que les champs sont évalués et initialisés à leur
position d’origine. La structure conserve la source du receveur pendant ses
réceptions successives.

Le programme de test traverse deux blocs, imprime trois fois la même adresse
et conserve la valeur 9. Les traces détruisent le temporaire intérieur, le
temporaire extérieur puis le résultat après son usage. Ce programme passe sous
UBSan bloquant à O0 et O2. Une variante qui retourne un champ `&Point` vers une
structure locale enfant est refusée. Ces résultats lèvent le refus du retour
de bloc signalé dans l’étape précédente pour les formes directes couvertes.

Les branches conditionnelles, boucles à résultat et retours de fonction restent
à raccorder à cette réservation locale. La copie locale reste à intégrer.
La régression ciblée des structures et champs propriétaires est lancée dans
la session 47022, journal `/tmp/crust-local-transfer-struct-regression.log`.

## Résultat conditionnel local

Les branches d’un `if` qui construisent le même type local partagent maintenant
une réservation dans le receveur. Cette réservation peut traverser un bloc
enveloppant. Seule la branche exécutée initialise l’objet. La sélection du
placement exige pour l’instant que les chemins analysés continuent normalement.

Les deux chemins sont exécutés séparément. Chacun conserve l’adresse observée
dans la branche, dans le bloc enveloppant et dans le receveur final. La trace
détruit uniquement le temporaire et le résultat de la branche choisie. Un type
différent dans l’autre branche est refusé. Les réaffectations entre `Point`
local et `A<Point>` sont refusées dans les deux sens, y compris quand le type
des liaisons est inféré.

La passe finale exécute trois méthodes de test à O0 puis O2 sous UBSan bloquant.
Elle couvre quatre programmes admis et huit variantes refusées par niveau.
Le journal est `/tmp/crust-local-if-final.log`. Les boucles à résultat, sorties
anticipées et retours de fonction restent à raccorder au placement local.

## Sortie terminale de boucle

Une boucle dont le `break <- valeur` final suit la construction du résultat
réserve maintenant ce résultat avant d’entrer dans la boucle. Les chemins
précédents qui font `continue` conservent la réservation inoccupée logiquement.
Les variables de ces itérations restent nettoyées par leurs scopes.

Le test exécute trois itérations, dont deux reprises. Il observe les valeurs
0, 1 et 2 des temporaires, puis la valeur 9 du résultat. L’adresse imprimée
avant le break est celle du receveur. Après destruction du résultat, une nouvelle
structure reçoit la même adresse et contient 10. La trace comporte exactement
trois destructions de temporaire, une destruction du résultat et une destruction
de la nouvelle structure. Le break sans flèche et le retour d’un champ empruntant
le temporaire d’itération sont refusés.

Les trois tests ciblés de boucle, condition et blocs imbriqués passent à O0
et O2 sous UBSan bloquant. Journal `/tmp/crust-local-loop-tests.log`.
La régression de 64 tests de structures et champs propriétaires est terminée
avec succès. Elle a démarré sur l’état précédant les extensions conditionnelles
et de boucle, qui disposent des tests ciblés ci-dessus.

Le placement de boucle couvre ici un break terminal dont la construction suit
les reprises. Les breaks dans plusieurs branches, un résultat déjà construit
avant une reprise, les sorties par return et les retours de fonction restent
à intégrer. La régression élargie de la session 46923 est toujours en cours.

## Breaks dans les branches

La collecte des constructions retournées parcourt désormais les branches `if`
des boucles. Les sorties locales prises en charge partagent la réservation du
parent. Un chemin qui reprend avant ces constructions conserve la réservation
pour une itération suivante. Les types des résultats doivent être identiques.

Un test exécute séparément deux branches de break après deux continue. Pour
chaque branche, il observe trois destructions de temporaire, l’adresse du
résultat identique avant et après break, et une seule destruction du résultat
choisi. La variante avec deux types de structure différents est refusée.
Les quatre méthodes ciblées de boucles, condition et blocs imbriqués passent
à O0 et O2 sous UBSan bloquant. Journal `/tmp/crust-local-loop-branches.log`.

Restent les valeurs construites avant une reprise, les autres formes de contrôle
et les retours de fonction. Les contrats de fonction considèrent encore toutes
les sources locales comme non durables et doivent distinguer le stockage d’un
résultat préparé par l’appelant.

## Résultat local construit par une fonction

Les contrats distinguent maintenant la provenance `local_value` des sources
de pools locaux. À l’appel, le compilateur réserve le résultat dans la data
stack de l’appelant. Un paramètre C interne transmet l’emplacement à la fonction.
Les constructions suivies d’un return initialisent cette réservation, tout en
conservant leur position d’évaluation. L’application opaque du contrat rattache
également le résultat au stockage de l’appelant.

Un test exécute deux chemins d’une fonction, un return dans un if et un return
final. Les deux conservent l’adresse entre construction et réception. Le
temporaire de la fonction est détruit avant l’usage du résultat par l’appelant.
Un résultat annoté `A<Point>` provenant d’une structure locale et une structure
retournée qui emprunte une valeur locale sont refusés. Le test des pools typés
est rejoué et conserve notamment le refus du retour depuis un pool local.
Ces deux méthodes passent à O0 et O2 sous UBSan bloquant, journaux
`/tmp/crust-local-function-tests.log` et `/tmp/crust-local-function-O0.log`.

La sélection du placement couvre les constructions directes que le collecteur
relie aux return. Les relais de résultats locaux par plusieurs fonctions et
les autres formes de contrôle restent à intégrer. Une régression des retours
de fonctions et structures locales est en cours dans la session 46660,
journal `/tmp/crust-local-function-regression.log`.

## Relais du résultat local

Le collecteur de placement reconnaît maintenant les appels dont le contrat
retourne une structure locale. Un appel déjà associé à une réservation la
transmet au prochain appel. Le contrat est utilisé pour identifier le type
et la provenance du résultat. La chaîne conserve l’emplacement du receveur
final jusqu’au constructeur.

Le premier programme exerce deux fonctions et un bloc, observe quatre fois
la même adresse, lit 10 et détruit la structure exactement une fois. Un second
programme retourne par deux fonctions une structure contenant un emprunt vers
un `Point` de l’appelant. Il détruit la structure référente puis utilise la
cible. L’ordre inverse est refusé pour emprunt encore actif.

Les tests de relais, de retours conditionnels de fonction et de breaks
conditionnels passent à O0 et O2 sous UBSan bloquant. Journal
`/tmp/crust-local-relay-tests.log`. La régression précédente de 15 tests de
retours de fonctions et de structures locales a terminé avec succès avant
l’extension des relais. La régression élargie 46923 poursuit son exécution.

Les constructions avant reprise de boucle, les autres formes de sortie et
la copie des structures locales restent à intégrer au placement.

## Construction avant reprise de boucle

Le collecteur suit les producteurs locaux déclarés avant les branches de
sortie. Une réservation active de boucle conserve son emplacement lorsque
la valeur de l’itération est détruite. Les champs propriétaires sont détruits
normalement, puis la réservation peut recevoir la construction suivante.
La sortie de la boucle termine cette rétention du stockage. La destruction
ultérieure du résultat peut alors récupérer l’emplacement.

Le test utilise un pool Int de capacité un et construit trois fois un Holder
qui détient l’allocation courante. Deux continue détruisent chacun le champ et
le Holder. Le break transfère la troisième valeur. Les quatre adresses observées
sont identiques. Après drop du résultat, le pool accepte une allocation de
valeur 99. Les sept destructions attendues sont observées et l’emplacement du
Holder n’est récupéré qu’une fois.

Les huit méthodes de structures locales passent à O0 et O2 sous UBSan bloquant.
Les deux tests runtime des cellules de tailles différentes et du nettoyage
cross-pool passent également aux deux niveaux. Journaux
`/tmp/crust-local-repeat-tests.log` et `/tmp/crust-local-repeat-runtime.log`.
Une mutation désactivant la rétention de réservation est détectée à O2. Le
programme mutant récupère l’emplacement au premier continue puis échoue avec
le diagnostic de réservation incompatible à la construction suivante.

Les sorties par return à travers une boucle ayant une réservation active
restent à intégrer. La collecte actuelle évite de réserver ces formes.

## Return anticipé pendant une réservation de boucle

Le compilateur suit les réservations actives par scope receveur. Quand un return
quitte ce scope, il termine la réservation après la destruction des valeurs
du scope et avant la fermeture des sources. Le runtime dispose d’une opération
de récupération du stockage indépendante de la destruction, ce qui permet de
rendre une réservation vide sans lire des champs non initialisés.

Le nouveau test appelle trois fois une fonction. Le premier chemin retourne
11 avant la construction. Le second retourne 22 après une reprise et une
nouvelle construction. Le troisième sort normalement de la boucle et retourne
33. Un Holder détient un Int venant d’un pool de capacité un. Les huit
destructions attendues sur les deux chemins qui construisent sont observées.

Les neuf tests de structures locales et réservations passent à O0 et O2 sous
UBSan bloquant. Les deux tests runtime ciblés passent également aux deux niveaux.
Journaux `/tmp/crust-local-early-tests.log` et `/tmp/crust-local-early-runtime.log`.
Une mutation qui omet de rendre les réservations vides est détectée à O2,
avec un diagnostic de source fermée alors qu’elle contient encore du stockage
vivant. Le retour testé est un Int. Le transfert direct de l’objet réservé par
un return traversant la boucle reste à raccorder au contrat du résultat local.

La régression élargie 46923 a terminé avec 449 tests réussis sur son état initial,
antérieur au raccordement des littéraux locaux. La régression complète des
régions après séparation destruction/récupération est en cours dans la session
85363, journal `/tmp/crust-local-reservations-growth-regression.log`.

## Transfert direct par return à travers une boucle

La collecte des constructions retournées suit désormais les blocs contenus
dans les expressions et instructions. Les boucles qui construisent le résultat
de la fonction retiennent également l’emplacement fourni par l’appelant.
Le return conserve la valeur construite, termine la rétention de la boucle
et laisse sa destruction au receveur.

Deux programmes exercent une fonction qui construit puis reprend deux fois.
Le premier sort soit par return dans la boucle, soit par break puis return.
Le second utilise une boucle instruction avec return direct. Les deux appels
de chaque programme conservent les adresses, produisent la valeur 2, détruisent
six valeurs au total et récupèrent l’emplacement deux fois. Le second appel
réutilise l’emplacement rendu par le premier. Une structure retournée depuis
la boucle avec un champ empruntant une cible locale est refusée.

Les dix méthodes de structures locales passent à O0 et O2 sous UBSan bloquant.
Le refus supplémentaire est rejoué à O2 avec les deux programmes. Journaux
`/tmp/crust-local-loop-return-tests.log` et `/tmp/crust-local-loop-return-final.log`.
La régression 85363 s’est terminée avec 22 tests de régions réussis sur l’état
du runtime qui précède cette extension du collecteur.

La copie locale, les autres formes syntaxiques de résultats et l’application
de ce placement aux autres types locaux restent à intégrer.

Le test du pool utilise une trace d’adresses et de valeurs attendue.
Cette passe n’ajoute aucun modèle indépendant de la data stack.
Le C émis utilise encore les variables locales et les états async pour
certains types locaux. Les sections ci-dessus exercent le dépilement physique
et la réservation parent des structures locales ; leur généralisation aux
autres types, le nettoyage général par dépendances et la migration des
anciennes syntaxes restent ouverts.

## Copie des structures locales — intégration de ST17/ST18 du brouillon 07

La règle normative distingue désormais la copie locale, qui utilise la data
stack destinataire, de la copie d’une allocation dans son pool d’origine.
Le générateur réserve la place du résultat avant de traverser les scopes
enfants. Une copie conserve les valeurs des champs, mais possède son propre
emplacement et son propre nettoyage. Les champs empruntés conservent leurs
cibles. Les champs propriétaires et les références mutables restent non Copy.

Un contre-exemple était accepté par le vérificateur puis refusé par le backend :
`fn duplicate(p: &Point) -> <- Point { let r = copy(p); return <- r; }`, appelé
avec un Point local. Le contrat de copie est maintenant résolu selon le
stockage de l’argument ; le backend reçoit l’emplacement de l’appelant pour
la copie locale. Deux relais et une sortie de bloc exercent ce raccordement.
La copie dans un pool, y compris depuis un paramètre emprunté, est conservée.

Preuves exécutées :

- 19 méthodes ciblées passent à O0 puis O2 sous UBSan bloquant : copies
  locales, réservations antérieures et quatre régressions de copies de pool.
  Journal `/tmp/crust-local-copy-regression.log`.
- Les nouveaux scénarios exercent l’indépendance des champs, deux adresses
  distinctes, le réemploi après drop, la conservation de l’adresse après
  transfert, trois itérations avec continue, le retour depuis une fonction et
  la copie depuis un paramètre à travers deux appels. Les destructions sont
  comparées aux traces attendues. Les références partagées survivent à
  l’original ; une cible locale trop courte et les drop/reset prématurés sont
  refusés. Les refus de reset utilisent uniquement le profil historique.
- Deux mutants isolés sont détectés à O2 : l’omission du memcpy produit des
  champs incorrects ; l’omission de la réservation de résultat fait rejeter
  les trois programmes valides de transfert. Journal
  `/tmp/crust-local-copy-mutations.log`, copies dans
  `/var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-local-copy-mutations.sj71lyjh`.

La première exécution des nouveaux tests a révélé deux erreurs d’attentes du
test : le format existant est `View(10)` et le diagnostic dit « encore être
utilisée ». Ces attentes ont été corrigées sans changer les propriétés de
copie ou de durée de vie exigées.

La régression élargie des structures, contrats, provenances, pools et runtime
s’est terminée avec 189 tests réussis en 107,972 s, journal
`/tmp/crust-local-copy-interactions.log`. Elle comprend les modèles runtime
par intervalles et les scénarios de destruction/réemploi.
Un scénario supplémentaire de copie de View reçue en paramètre, qui survit
à son original mais protège toujours sa cible, passe à O0/O2, journal
`/tmp/crust-local-copy-shared-relay.log`. Il ajoute un programme admis avec
trace de trois destructions et deux programmes refusés (drop et reset).

Limites : les nouveaux tests ne constituent pas un modèle indépendant du
vérificateur. Le modèle runtime par intervalles est rejoué avec la régression
élargie. La couverture reste celle des champs et formes syntaxiques pris en
charge ; le placement général des autres valeurs locales, les autres décisions
du brouillon 07 et les lots suivants ne sont pas terminés.

Une exécution supplémentaire du programme de copie de View relayée, compilé
avec `-O2 -fsanitize=address,undefined -fno-sanitize-recover=all`, n’a produit
aucune sortie et est restée active lors des observations successives. Le
processus de test a été arrêté par SIGTERM après plus de 30 secondes.
L’échantillonnage de sa pile avec `sample` a été refusé faute de privilèges.
Ce contrôle ASan est **inconclusif** ; sa cause n’est pas établie. Le même
programme a terminé normalement sous UBSan seul. Aucun résultat ASan réussi
n’est revendiqué pour cette passe.
