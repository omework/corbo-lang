[English](FOUNDATIONS_CYCLE.md)

# Cycle de validation des fondamentaux

La [spécification du chantier](../FOUNDATIONS_AND_VECTORS.md) et la
[matrice](../VERIFICATION_MATRIX.md) distinguent les règles consignées du support
exécutable. Ce cycle couvre une partie du noyau synchrone.

## Comportements examinés

- **F2.** Un bras `_` final couvre plusieurs variantes, dont une avec des
  champs ignorés. Les tests contrôlent la branche exécutée et le refus d'un
  bras placé avant les variantes explicites ou entièrement redondant. Le C
  conserve un diagnostic distinct pour un tag invalide.
- **F4.** Les traces natives distinguent un opérande sauté d'un opérande
  évalué et vérifient la précédence. Avec un pool de capacité 1, un transfert
  sur le chemin évalué conduit à exactement une destruction, comme la
  sortie de scope sur le chemin sauté. Un usage après une consommation
  possible est refusé à la jonction.
- **F5.** Les tests confrontent le repliement des constantes, les diagnostics
  dynamiques et les bornes signées. Le test de lecture avant mutation
  vérifie aussi l'ordre des opérandes. Le modèle Python par `divmod`
  calcule les résultats attendus de 41 couples signés pour la division
  et le reste, plus le reste de `INT32_MIN % -1`. Le backend évalue
  les opérations intermédiaires en Int64. Le quotient est tronqué vers
  zéro. Le reste mathématique de `INT32_MIN % -1` vaut zéro.
- **ST2–ST3.** Le test appelle `Pool<Int>.new()` avec un pool injecté,
  transfère le résultat, le détruit, puis réutilise l'unique slot avec
  `p.new(41 + 1)`. Il vérifie la valeur par défaut et les destructions.
  Une source non typée, un pool d'un autre type et une arité invalide
  sont refusés.

## Contre-exemples et mutation

La première traduction du court-circuit plaçait le RHS dans un bloc Crust
artificiel. Elle refusait un transfert à un appel pour un motif de scope.
La traduction utilise désormais des branches C sans créer de scope Crust.

Une allocation temporaire empruntée dans le RHS révélait ensuite une
allocation perdue à la jonction. Le programme C affichait `9` et `10`,
puis le pool signalait `internal error: source still has live allocations`.
Le compilateur avait d'abord interdit ce cas. Le compilateur conserve désormais
le pointeur et un indicateur de présence au-delà de la branche C. Le scope
Crust garde la responsabilité du nettoyage. Deux tests couvrent la présence
ou l'absence du temporaire dans une condition imbriquée et le réemploi d'un
slot unique après `continue` et après la sortie sur un test faux.
Deux vérifications natives supplémentaires ont reproduit la destruction dans
l'ordre `9, 8` pour deux allocations successives sous UBSan à `-O0` et
`-O2`, puis le réemploi d'un slot après `reset()` avec et sans création
du temporaire sous UBSan à `-O2`.
Un retour anticipé depuis le corps du `if` a également nettoyé le
temporaire sur le chemin exécuté, tandis que l'autre chemin a rendu son
résultat sans trace de destruction.
Avec une capacité de 1, une seconde allocation après le `if` et avant la
fin du scope a échoué avec `pool capacity exceeded`, comme attendu tant
que le temporaire occupe le slot.

La suppression de l'activation de l'indicateur dans une copie du C généré
reproduit la fuite sous UBSan. Le témoin affiche `9`, puis détruit et
récupère le slot avec un code 0. Le mutant affiche `9`, puis le pool
signale une allocation encore vivante avec un code 1. L'exécution avec
ASan et UBSan combinés n'a pas terminé et a été interrompue.

La suppression du contrôle de diviseur nul dans une copie du C généré a
déclenché `runtime error: division by zero` sous UBSan. Le programme normal
échoue avec le diagnostic Crust, avant l'opération C. La mutation n'a pas
modifié les fichiers du compilateur.

Une seconde mutation a forcé l'entrée dans le bras évaluant le RHS de
`&&`. Le programme témoin a affiché `1`. La version mutée a affiché
`1, 2, 3`. Le test de trace distingue ainsi un court-circuit effectif
d'un backend qui évaluerait le RHS alors que le gauche est faux.

## Limites

Le court-circuit s'applique dans les conditions. Le compilateur ne dispose
pas de Bool général ni de propagation des faits de chemin reliant le résultat
de l'opérateur logique aux effets de son RHS. Le match consommant prend en
charge les champs Int, &Int et &mut Int en instruction. Les résultats
généraux du match restent ouverts. `Pool<Int>.new` réutilise la représentation existante des
allocations. Il ne fournit pas le type `A<T>` explicite.

La matrice laisse ouverts les types récursifs, les structures et méthodes
générales, `A<T>`, les vecteurs, les régions grandissantes, String et le
runtime async/multithread. Le retrait de reset selon PR1 reste également
ouvert. Aucune preuve générale de sûreté n'est établie par ces exécutions.

## Exécutions

- État de départ, `python3 -m unittest discover -s tests` a terminé avec
  909 tests réussis.
- Version modifiée, la découverte complète `unittest` répartie entre six
  processus a terminé avec 922 tests réussis. Chaque test découvert a été
  affecté à un seul processus, par sa position dans la suite.
- Après l'ajout du nettoyage conditionnel des temporaires, le même découpage
  de la suite a terminé avec 923 tests réussis, dont les deux cas natifs
  sur les temporaires sous UBSan à `-O2`.
- Version modifiée, `PYTHONPATH=tests CRUST_SANITIZE=undefined python3 -m unittest
  test_foundation_rules test_ancestor_join test_if_expressions test_arguments
  test_conditionals test_scope_exit test_continue` a terminé avec 122 tests
  réussis. Les scénarios natifs de `test_foundation_rules` utilisent également
  `-O2 -fsanitize=undefined -fno-sanitize-recover=all`.
- Une exécution native supplémentaire à `-O0` et `-O2` sous UBSan a
  combiné un pool de capacité 1, un emprunt sur le RHS de `&&`,
  l'incrémentation et `continue` dans un `while`. Les deux niveaux
  ont produit `0, 1, 2, 3`, puis les traces `destroy n=3` et `reclaim n`.
- Un cas supplémentaire a calculé un indice de tableau fixe, modifié la
  case par emprunt mutable puis relu la case après le dernier usage de
  l'emprunt. Le C sous UBSan à `-O2` a produit `14`. Un accès concurrent
  au tableau dans une variante avec indice constant replié a été refusé.

## Match consommant avec liaisons Int

Le compilateur charge les champs liés dans l'ordre de leur disposition,
invalide le sujet et détruit son enveloppe avant d'exécuter le bras. Le
slot peut ainsi servir à une nouvelle allocation dans le bras. Les chemins
qui quittent la fonction ou la boucle suivent le nettoyage ordinaire et
sont exclus de la jonction des chemins continuants.

Quatre tests ciblés passent, dont trois exécutent le C sous UBSan à `-O2`.
Ils vérifient le chargement de champs nommés dans un ordre différent de la
déclaration, le réemploi d'un pool de capacité 1, les sorties `return`,
`break` et `continue`, et trois refus liés aux emprunts et à l'accès au
sujet consommé. Une exécution supplémentaire a comparé deux variantes.
Une seule détruisait une allocation externe dans son bras. L'autre la
détruisait à la fin du scope, et une lecture après la jonction a été refusée.
Avec un champ `&mut Int` ignoré par `_`, le bras a modifié la cible
après la destruction de l'enveloppe. À ce stade, le compilateur refusait
encore la liaison nommée de ce champ.

Une mutation du C qui omet la destruction du sujet fait échouer le réemploi
du slot avec `pool capacity exceeded`. Le témoin affiche `E.A(3)` et
nettoie les deux allocations dans l'ordre attendu.

La découverte complète `unittest` répartie entre six processus a terminé
avec 927 tests réussis.

## Déplacement des champs références

Le bras charge les champs références avant de libérer le slot du porteur.
Le vérificateur rattache chaque liaison à ses cibles possibles et conserve
la chaîne des emprunts dont elle dépend. Le porteur consommé sort de cette
chaîne. Les contraintes d'appel et l'inférence des résultats suivent la
provenance de la liaison dans le bras.

Les six tests ciblés du match consommant passent. Les deux nouveaux cas
sous UBSan à `-O2` couvrent la lecture d'un champ partagé, la mutation via
un champ exclusif, la reprise de l'emprunt parent et le retour d'un champ
extrait d'un enum local construit depuis un paramètre emprunté. Le compilateur
refuse une mutation via le champ partagé, une mutation via le parent avant
le dernier usage du champ et une mutation de la cible avant le dernier
usage du résultat retourné.
Un contre-exemple complémentaire tente de retourner le champ d'un enum
dont la cible a été allouée dans la fonction. Il est refusé car la cible
ne survit pas à l'appel.
Un porteur sélectionné par condition entre deux cibles a modifié uniquement
la cible sélectionnée à l'exécution. Les deux variantes qui tentaient de
modifier une cible directement avant le dernier usage de la liaison ont
été refusées. Le C a été compilé sous UBSan avec `-Werror=return-type`.

La suppression de la chaîne des emprunts parents dans une copie temporaire
du compilateur a fait rejeter le cas valide avec `emprunt mutable non exclusif`.
Le C déclare son diagnostic fatal `_Noreturn` pour que le chemin par défaut
du switch soit reconnu comme terminal, y compris dans une fonction qui
retourne une référence.

La découverte complète `unittest` répartie entre six processus a terminé
avec 929 tests réussis.

## Retour direct d'un champ depuis un porteur transféré

Le contrat distingue le champ déplacé d'un réemprunt qui doit garder son
porteur réservé. À l'appel, il résout la cible et sa chaîne d'emprunts
sans ajouter de réservation sur l'enveloppe détruite. L'inférence
propage cette provenance quand une fonction relaie le résultat.

Deux tests ciblés passent sous UBSan à `-O2`. Ils couvrent le retour partagé,
le retour mutable relayé, la réutilisation du slot de capacité 1 avant la
dernière écriture par la référence, et le refus d'un accès mutable
concurrent ou d'un retour vers une cible locale. Supprimer la reprise de
la chaîne d'emprunts parents dans une copie temporaire du compilateur
fait échouer un cas valide avec `emprunt mutable non exclusif`.
Un essai natif supplémentaire replace le champ dans un nouvel enum retourné
par la fonction et modifie ensuite la cible avec succès. Deux vérifications
du compilateur admettent `reset()` sur le pool du porteur libéré et le
refusent sur le pool de la cible tant que la référence doit servir.
Un autre essai sous UBSan retourne l'un de deux champs mutables du même
porteur selon un paramètre. Il produit `20, 2` ou `1, 20` suivant le chemin.
Le compilateur refuse un accès direct anticipé à chacune des deux cibles.

La découverte complète `unittest` répartie entre six processus a terminé
avec 931 tests réussis.

## Champs déplacés dans un tableau retourné

Le contrat des tableaux retournés résout chaque case vers le champ déplacé
correspondant. La provenance traverse une fonction relais et reste
disponible lorsqu'une autre fonction réemprunte une case et la retourne.
Le slot de l'enum consommé reste indépendant de ces références.

Trois nouveaux tests ciblés sous UBSan à `-O2` passent. L'un retourne deux champs
mutables dans l'ordre inverse et obtient `22, 21` après les écritures.
Il admet `reset()` sur le pool de l'enum et le refuse sur le pool des
cibles avant les écritures. L'autre retourne un réemprunt de case,
obtient `22` sur la cible et refuse l'accès direct anticipé à celle-ci.
Une mutation qui résout la case sur le porteur au lieu du champ fait
échouer le cas valide avec `un tableau de références Int exige des cibles Int`.

Le troisième test révèle une régression de l'implémentation initiale. Un
appel avec une variante connue pouvait perdre sa continuation dès qu'une
autre variante figurait dans le contrat du tableau. La résolution des
cases et de leurs réemprunts écarte ces alternatives individuellement.
Le match consommant garde le contrôle d'exhaustivité et de forme sur tous
les bras. Le compilateur traite les corps dont le sujet peut atteindre la
variante. Le test passe désormais par deux variantes connues et produit
`9, 7` sous UBSan.
La suppression du filtre dans une copie du compilateur reproduit la
régression. Le témoin affiche `9`, tandis que Clang rejette le C mutant
car sa continuation utilise un identifiant non déclaré. Un essai
supplémentaire renvoie une case partagée à travers une ligne imbriquée
et affiche `9` sous UBSan.

La découverte complète `unittest` répartie entre six processus a terminé
avec 934 tests réussis.

## Résultat Int du match consommant

Le parseur admet le match consommant parmi les expressions. Le compilateur
reprend la syntaxe de fin de branche du `if` et écrit le résultat dans un
temporaire C commun aux bras continuants. Les sorties de fonction ou de
boucle gardent leur propre chemin de nettoyage.

Deux tests ciblés passent. Le test natif sous UBSan à `-O2` exerce un calcul
dans un bras, un retour anticipé dans un deuxième et un résultat littéral
dans le bras de rattrapage. Il obtient `14, 9, 10` et observe une destruction
par sujet. Le second test vérifie le refus de deux programmes dont un bras
continuant omet le résultat ou produit un tableau.

Un essai natif place le match au milieu des arguments d'un appel. Sous
UBSan, le témoin affiche les évaluations `1, 4, 3` puis le résultat
`8`. Une mutation de la copie C remplace la valeur du bras par zéro.
Elle conserve les trois évaluations, mais produit `4` au lieu de `8`.
Un autre essai place l'expression à droite de `&&` et exécute les deux
chemins sous UBSan. Le sujet est détruit une fois dans chaque appel.
Seul le chemin qui l'évalue réemploie le slot dans le corps du `if`.

Cette étape couvrait uniquement les résultats Int.

La découverte complète `unittest` répartie entre six processus a terminé
avec 936 tests réussis.

## Résultats tableaux et allocations du match consommant

Les bras continuants doivent fournir le même type et le même mode de
résultat. La jonction des tableaux de références conserve les cibles
possibles de chaque case. La jonction des allocations reprend leurs
provenances et confie le nettoyage de l'allocation sélectionnée au
receveur. Les dépendances du résultat protègent les allocations
empruntées lors de la jonction des affectations.

Les neuf tests ciblés du match consommant passent. Le nouveau test natif
sous UBSan à `-O2` exerce les trois formes de résultat, le retour à travers
un appel, le réemploi d'un pool de capacité 1 et la destruction unique
des allocations sélectionnées. Les variantes qui modifient l'une des
deux cibles possibles avant la dernière lecture sont refusées. Un bras
continuant sans résultat ou avec un type différent reste refusé.

Un essai supplémentaire retourne l'allocation sélectionnée entre deux
pools. Le témoin produit `12` et libère le slot du second pool. Le
compilateur refuse de réinitialiser ce pool avant la dernière lecture.
Supprimer le nettoyage du résultat dans une copie du C fait signaler
une allocation encore vivante à la fermeture du pool.

Cette étape couvrait les résultats possédés et copiables.

La découverte complète `unittest` répartie entre six processus a terminé
avec 937 tests réussis.

## Résultats empruntés directs du match consommant

Un bras peut fournir une référence nommée ou une expression d'emprunt.
Le vérificateur contrôle la durée de vie avant de fermer le bras. La
jonction conserve l'ensemble des cibles et la chaîne d'emprunts parents
du résultat. Le porteur déjà consommé n'est pas ajouté à cette chaîne.

Les onze tests ciblés du match consommant passent. Le nouveau cas natif
sous UBSan à `-O2` retourne un champ mutable après la jonction, réinitialise
le pool du porteur, puis écrit via le résultat et l'emprunt parent.
L'inversion de ces deux écritures est refusée. Le second nouveau test
refuse une référence vers une allocation créée dans le bras.

Un essai supplémentaire sous UBSan choisit entre un réemprunt explicite
et une référence nommée. Les deux chemins modifient la cible attendue.
Un accès anticipé à l'une ou l'autre cible est refusé. Une mutation qui
garde uniquement la première cible à la jonction accepte à tort l'accès
anticipé à la seconde. Le compilateur normal refuse ce programme.
Un autre essai natif retourne directement un résultat partagé. Il
affiche `9` pour le champ du porteur et `7` pour la référence de repli.

Cette étape couvrait les emprunts directs d'Int.

La découverte complète `unittest` répartie entre six processus a terminé
avec 939 tests réussis.

## Emprunts de tableaux comme résultats du match consommant

Chaque bras continuant fournit un emprunt du même type et du même mode.
Avant de nettoyer le bras, le compilateur vérifie la durée de vie du
tableau et de ses emprunts parents. La jonction conserve tous les
chemins du résultat et protège leurs dépendances.

Les nouveaux tests couvrent un réemprunt explicite et un emprunt nommé,
le retour d'un emprunt à travers un appel et le refus d'une référence
vers un tableau local au bras. Sous UBSan, les deux variantes du cas
mutable donnent `20, 3` puis `1, 20`. Un accès anticipé à l'un ou
l'autre tableau est refusé. Un essai supplémentaire retourne une
ligne partagée de références et lit `7` dans la case choisie.

Une mutation du compilateur qui conserve uniquement le premier chemin
à la jonction accepte à tort une écriture anticipée dans le second
tableau. Le compilateur normal refuse cette écriture.

À ce stade, le compilateur rejetait la combinaison d'une référence à une
allocation `Int` et d'une référence à une case `Int` dans deux bras.
Ces références ont le même type source et des représentations C distinctes.

La découverte complète `unittest` répartie entre six processus a terminé
avec 941 tests réussis.

## Jonction des références Int d'origines différentes

Lorsqu'un bras produit une référence à une case Int, le C transporte le
pointeur vers la valeur Int. Les bras qui produisent une référence à une
allocation Int utilisent alors l'adresse de la valeur contenue dans
l'allocation. Le vérificateur ajoute le chemin vers cette allocation
aux chemins vers les cases et conserve leur mode d'emprunt commun.

Les quatorze tests ciblés du match consommant passent. Le nouveau cas
retourne un emprunt mutable à travers une fonction et produit
`20, 7` puis `9, 20` sous UBSan. Le compilateur refuse une écriture
anticipée sur chacune des deux cibles. Un essai partagé affiche `9`
puis `7` et réinitialise le pool du porteur après sa consommation.
Retirer le chemin de l'allocation lors de la conversion, dans une
copie du compilateur, fait accepter à tort une écriture anticipée.
Une combinaison d'emprunts partagé et mutable reste refusée même si
leurs deux cibles sont des Int.

La première version tentait aussi cette conversion sur les résultats
`&Enum`. Le compilateur la réserve désormais aux résultats Int.
Un test de régression lit `W.Value(12)` à travers un résultat emprunté
vers un enum.

La suite globale lancée avant cette dernière correction a terminé avec
942 tests réussis. Les 34 tests de `test_foundation_rules` ont ensuite
passé sur la version finale, avec le nouveau cas de régression `&Enum`.

Les formes générales du match par emprunt restent ouvertes.

## Résultat Int du match partagé

Le parseur admet `match &valeur` dans les expressions. Les bras continuants
produisent un Int à partir des lectures et des opérations arithmétiques
existantes. Un bras qui retourne de la fonction suit son chemin de
nettoyage. Le sujet emprunté reste disponible après la jonction.

Deux tests ciblés passent sous UBSan. Le premier produit `10, E.A(4), 7,
E.B()` et vérifie la lecture du porteur après les deux chemins. Le second
lit un champ mutable au travers de sa projection partagée, produit
`10, E.A(9)` et vérifie le refus d'une écriture via la projection.

Une mutation de la copie du compilateur applique le nettoyage du match
consommant au match partagé. Elle fait rejeter la lecture du porteur
après la jonction, alors que le compilateur normal l'accepte.
Un essai sous UBSan détruit le sujet après le calcul et réutilise son
slot. Le résultat reste `4` et la nouvelle allocation contient `90`.

Les autres résultats et l'élargissement des corps des matchs empruntés
restent ouverts.

La découverte complète `unittest` répartie entre six processus a terminé
avec 945 tests réussis.

## Résultat Int du match par emprunt mutable

Un bras continuant peut fournir un littéral, une liaison Int ou un
calcul après des écritures via ses projections. Le vérificateur
réserve le porteur pendant chaque bras mutable. Les bras qui
retournent de la fonction ne fournissent aucune valeur à la jonction.
Les matchs qui fournissent des réemprunts gardent le traitement
existant de la réservation du porteur dans le résultat.

Deux nouveaux tests ciblés passent. Le C sous UBSan affiche
`21, E.A(20), 5, 6, 7` pour les chemins écriture et calcul, copie,
littéral et retour anticipé. Le compilateur refuse de joindre un
réemprunt et un résultat scalaire. Un test existant vérifie encore
le refus d'une liaison qui ne provient pas d'une projection mutable
et ne désigne pas un Int.

Un contre-exemple tente de lire le porteur après la dernière écriture
via la projection, mais avant la fin du bras. Le compilateur refuse
cet accès. Une copie du compilateur dont on a retiré la réservation
du bras accepte ce même programme.
Un essai supplémentaire passe la projection à une fonction qui écrit
`17` puis retourne l'Int lu. Sous UBSan, le match rend `17` et le
porteur reste accessible avec ce champ modifié.

La découverte complète `unittest` répartie entre six processus a terminé
avec 947 tests réussis.

## Résultat emprunté du match partagé

Une projection partagée peut sortir du bras comme résultat. Le
compilateur conserve une réservation partagée du porteur ainsi que
les cibles du champ. Le contrat transmet cette réservation lors
d'un appel relais et lors du stockage de la référence dans un tableau
ou un enum retourné.

Les quatre tests ciblés du match partagé passent. Le nouveau cas natif
sous UBSan lit le porteur et la projection puis détruit le porteur
après le dernier usage. Il produit `E.A(9), 9, 10`. Une destruction ou
une écriture avant le dernier usage est refusée. Le compilateur refuse
aussi le retour d'une projection issue d'un porteur local à la fonction.
Un essai supplémentaire sous UBSan vérifie la lecture d'une case et
d'un enum qui contiennent la projection. La destruction anticipée
du porteur est refusée dans le second cas.

Retirer la réservation du contrat dans une copie du compilateur est
détecté par l'invariant qui compare les porteurs du résultat réel et
du résultat inféré. Retirer la réservation uniquement à l'appel
avec un champ mutable est détecté par l'invariant d'exclusivité.

Les corps généraux et les résultats empruntés qui ne proviennent pas
d'une projection restent ouverts pour le match par emprunt.

La découverte complète `unittest` répartie entre six processus a terminé
avec 949 tests réussis.

## Emprunts partagés extérieurs au sujet du match

Le résultat de `match &` peut emprunter une cible extérieure au
porteur. Le contrat reprend les provenances de chaque bras. Les
contraintes réservent le porteur pour les projections de ses
champs et suivent la cible elle-même pour les autres emprunts.

Les six tests ciblés du match partagé passent. Les deux nouveaux
cas sous UBSan retournent un Int emprunté ou un emprunt de tableau
à travers un appel et lisent après la destruction du sujet. Le
compilateur refuse une écriture anticipée sur la cible du résultat.
Un essai supplémentaire réinitialise le pool du sujet et lit `9`.
Une mutation qui rattache tous les résultats au sujet refuse à tort
la réinitialisation dans cet essai.

Pour un résultat qui peut être une projection ou un emprunt
extérieur, un essai natif au niveau du programme réinitialise le pool
du sujet sur la variante extérieure et lit `7`. La variante qui
retourne une projection refuse la même réinitialisation. À cette
étape, dans le corps d'une fonction, l'analyse des contraintes pouvait
encore refuser ce reset même si le constructeur local fixait la
variante extérieure.

Les corps généraux et les emprunts extérieurs comme résultat de
`match &mut` restent ouverts.

La découverte complète `unittest` répartie entre six processus a terminé
avec 951 tests réussis.

## Variantes connues dans les contraintes d'appel

L'analyse des contraintes conserve les variantes possibles depuis
un constructeur, à travers les emprunts et les jonctions. Un appel
qui retourne un enum reprend les variantes de ses candidats connus.
Une jonction avec une variante inconnue conserve toutes les
provenances possibles. Au site d'appel, seuls les champs d'une
variante absente sont écartés.

Deux tests ciblés passent. L'essai natif sous UBSan affiche `7`
après avoir réinitialisé le pool du sujet local, construit par un
appel et emprunté par une liaison nommée. La variante qui permet
une projection refuse ce reset, de même qu'une jonction qui
conserve les deux variantes. Désactiver le filtre dans une copie
du compilateur reproduit le refus du programme valide.
Un essai supplémentaire joint deux variantes différentes qui ne
portent aucune projection. Les deux exécutions affichent `7` après
le reset. Remplacer l'une des variantes par celle qui porte un
champ fait rejeter le programme.

La découverte complète `unittest` répartie entre six processus a terminé
avec 953 tests réussis.

## Emprunts extérieurs du match par emprunt mutable

Un bras mutable peut rendre une projection du porteur ou un
emprunt extérieur. La réservation exclusive du bras se prolonge
pour les projections et s'arrête à la sortie du bras pour un
résultat extérieur. Le résultat peut aussi être une projection
partagée. Dans ce cas, il garde la réservation exclusive du porteur
issue du match mutable.

Les six tests ciblés du match mutable en expression passent.
Les trois nouveaux cas sous UBSan couvrent le choix entre une
projection et un emprunt extérieur, le retour d'un emprunt de
tableau et la projection partagée d'un champ `&Int`. Le
compilateur refuse de détruire le porteur sur le chemin
projeté, d'écrire prématurément dans un tableau cible et de
lire le porteur réservé avant le dernier usage du champ partagé.

Une mutation qui désactive la réservation de la projection
dans la jonction générale accepte à tort de détruire le
porteur avant de lire le champ partagé.
Un essai supplémentaire joint deux variantes possibles dans une
fonction. Sous UBSan, il modifie la cible projetée ou la cible
extérieure selon la variante. Avancer la destruction du porteur
avant l'écriture est refusé à la jonction.

Pour un match écrit directement dans une fonction, les contraintes
écartent aussi les bras que les variantes connues rendent
inaccessibles. Le quatrième nouveau test affiche `21` après le
reset sur la variante qui choisit l'emprunt extérieur et refuse
le même reset sur la variante projetée.

Les corps généraux et les résultats possédés des matchs par
emprunt restent ouverts.

La suite globale lancée avant le filtrage des bras impossibles
a terminé avec 956 tests réussis. Sur la version finale, 137 tests
ciblant les contraintes, les effets, le match mutable et les règles
fondamentales ont réussi.

## Résultats possédés du match par emprunt

Les bras empruntants peuvent construire des allocations ou tableaux
locaux et transférer explicitement leur résultat. Le sujet reste
emprunté pendant le bras. La sortie transfère le nettoyage de la
valeur sélectionnée et détruit les autres allocations locales.
Les références stockées dans un résultat conservent leurs
réservations.

Les deux nouveaux tests sous UBSan passent. Le premier construit
deux allocations dans un bras partagé, en transfère une et réutilise
le slot de l'autre. Il affiche `E.A(4), 4, 50`. Le second
retourne un tableau de références après une écriture via la projection
mutable. Il affiche `20, E.A(20)` et refuse la destruction
anticipée du porteur. Supprimer le nettoyage de l'allocation
locale dans une copie du C fait échouer le réemploi du slot avec
`pool capacity exceeded`.

Un essai supplémentaire place une projection partagée dans un
nouvel enum et transfère cet enum hors du bras. La lecture de son
champ affiche `R.A(9)` sous UBSan. Le compilateur refuse de détruire
le porteur tant que le nouvel enum doit servir.

Les initialisations locales prises en charge utilisent des
lectures, des emprunts et des constructions sans appels. Les corps
généraux du match par emprunt restent ouverts.

La découverte complète `unittest` répartie entre six processus a terminé
avec 959 tests réussis.

## Appels et contrôle dans les bras d'un match par emprunt

Une construction locale peut évaluer un appel dans son
initialiseur. Le sujet reste emprunté pendant l'appel et le
nettoyage du bras. Les analyses de résultat et de contraintes
joignent les modifications visibles sur les chemins continuants.
Les bras admettent aussi les conditions et les boucles. Les
sorties `break` et `continue` quittent le bras avec le nettoyage
normal.

Deux nouveaux tests passent sous UBSan. Le premier calcule `7`
dans un initialiseur et refuse un appel qui réinitialise le pool
du sujet. Une mutation qui retire la réservation du sujet accepte
à tort ce dernier programme. Le second affiche `11, 3` et compte
une destruction du sujet par itération, y compris sur les deux
sorties de boucle. Un essai supplémentaire exécute une boucle
imbriquée dans un bras et retourne `3`.

Un autre essai met à jour un tableau de références par un appel
dans l'initialiseur. Après le match, la fonction retourne la
référence nouvellement écrite. Sous UBSan, le résultat affiche
`7` et reste lisible après la destruction de l'ancienne cible.

Un contre-exemple utilise le même nom pour un paramètre emprunté
et pour un champ scalaire d'un bras qui exécute `break`. Le
compilateur confondait les deux types après la boucle. Le test
sous UBSan retourne désormais la référence du paramètre et affiche
`9` pour un match empruntant comme pour un match consommant.
Une mutation qui omet l'enregistrement du masquage reproduit
le refus erroné dans les deux cas.

Les corps de match par emprunt conservent des restrictions, dont
les appels directs qui ne passent pas par les formes déjà admises
et les affectations générales dans les bras.

La suite globale, lancée avant le correctif de masquage, a
terminé avec 961 tests réussis, répartis en six lots. Une
nouvelle suite globale a été lancée sur la version finale du
correctif de masquage. Sur cette version, 146 tests ciblant les
contrats, les effets, les boucles et les matchs ont réussi. La
nouvelle suite globale a ensuite terminé avec 962 tests réussis.

## Appels directs et remplacements dans les expressions de match

Les expressions `match` par emprunt acceptent les appels Void et les
affectations via le même vérificateur que les blocs ordinaires. Le
receveur extérieur reçoit la nouvelle allocation uniquement sur le
chemin exécuté, et le remplacement d'une allocation d'un ancêtre exige
toujours `<-`. Le cas natif sous UBSan exerce les deux variantes, avec un
slot disponible pendant la construction et la valeur initiale conservée
sur la branche sans remplacement.

Le sujet reste réservé pendant un appel direct qui tente de
réinitialiser son pool. Un premier test de mutation survivait parce que
le programme lisait encore le sujet après le bras. Le test négatif retire
cette lecture et détecte désormais la mutation qui supprime la
réservation du bras. Le test positif continue d'observer le sujet et le
receveur après chaque variante.

Un second cas UBSan appelle une fonction avec une projection mutable et
un argument Int. Il retourne la projection, modifie la cible via ce
résultat et lit le porteur après le dernier usage. La même lecture avant
cet usage est refusée. Les 83 tests des fondamentaux, des remplacements
de boucle et des retours d'emprunts mutables ont réussi. Le cas négatif
renforcé a été réexécuté séparément sur le compilateur courant et sur la
copie mutée. La suite globale de ce cycle a terminé avec 964 tests réussis.

## Remplacements et sorties dans les matchs sans résultat

Les bras par emprunt sans résultat rejoignent les chemins continuants
après une affectation et propagent leurs sorties de boucle et de
fonction. Le vérificateur passe par le même chemin que les matchs
consommants et les expressions de match dès qu'un bras écrit ou contient
du contrôle. L'analyse des contrats restaure les liaisons de motif à la
sortie du bras et conserve les écritures visibles dans la portée externe.

Deux tests C11 optimisés avec UBSan ont réussi. Le premier remplace le
receveur par transfert avant un continue puis un break, vérifie le
résultat 5 et la trace exacte des cinq destructions, et refuse le
transfert depuis un pool local au bras. Le second remplace un tableau de
références et retourne sa nouvelle cible. Détruire l'ancienne cible est
accepté et affiche 7. Détruire la nouvelle avant le dernier usage est
refusé. La mutation qui omet la jonction symbolique pour un match sans
résultat est détectée par le second test. Un premier essai de mutation
laissait le contexte de résultat de la fonction se propager au match
instruction et ne touchait donc pas la jonction exercée.

Les appels directs avec des arguments autres que les projections
restent restreints dans les matchs sans résultat. Sur la version finale,
19 tests ciblant les retours d'emprunts mutables, les appels dans les bras
et les sorties de boucle ont réussi. La suite globale de cette version
est en cours.

## Annotation des liaisons d'allocation

La vérification de ST2 compare le type nommé dans la déclaration au
type de l'allocation effectivement produite. Elle fonctionne aussi
dans un corps de fonction vérifié à partir des paramètres symboliques.
Une annotation compatible laisse le C généré identique. Le test C11
optimisé sous UBSan transfère l'allocation au retour, la détruit puis
vérifie le réemploi de son adresse dans un pool de capacité un.

Le vérificateur seul refuse une annotation incompatible dans le corps
de la fonction ainsi qu'une annotation appliquée à une valeur scalaire
dans le périmètre de cette implémentation. Une mutation supprimant la
comparaison des types accepte à tort la première variante et fait
échouer le test. La suite globale est lancée. Les structures et leur
construction nommée restent à implémenter.

## Construction des structures plates dans un pool

La construction de ST1–ST4 réutilise le stockage agrégé par slot.
Un pool de structures a une seule disposition, avec les champs contenus
dans la charge utile du slot. Les arguments nommés sont évalués dans
l'ordre écrit avant publication. Les Int omis prennent la valeur zéro.
Un champ référence exige une cible explicite et conserve sa dépendance
à travers le contrat de retour. Le match sur ces types est refusé.

Deux programmes C11 sous UBSan ont réussi. Le premier fait observer
l'ordre 9 puis 4, la disposition Point(4, 9, 0), le réemploi de la même
adresse dans un pool de capacité un et les deux destructions. Le second
retourne une structure contenant une référence et affiche View(7, 0).
Le vérificateur refuse les champs inconnus ou répétés, le défaut d'une
référence, la destruction prématurée de la cible et le reset pendant
l'initialisation d'un champ suivant. La mutation qui inverse
l'évaluation des champs est détectée malgré une disposition identique.
Trois essais au vérificateur confirment la construction dans un pool
local à une fonction, le refus d'un emprunt partagé fourni à un champ
mutable et le refus d'un match sur une structure.

Une suite précédente en cours a exercé le CLI pendant la modification
de l'analyse et rencontré une exception sur une déclaration de pool
local. Le test CLI de construction et d'exécution d'un binaire a réussi
sur la version corrigée, avec les deux nouveaux tests. Les anciens
lots avec sous-processus CLI peuvent mélanger plusieurs versions. Une
nouvelle suite globale est lancée sur une copie figée des sources et
des tests. Les champs imbriqués, les défauts récursifs et les accès
aux champs restent à implémenter.

Le lot ciblé lancé avant la correction des pools locaux s'est terminé
avec 54 tests, un échec et 26 erreurs. Le défaut faisait échouer les
cas valides du modèle de routage des pools. Le cas de masquage d'un
pool local passe isolément sur la copie figée du cycle suivant. Le lot
de régression des exigences de pools et des champs références a été
relancé sur cette même copie corrigée.

## Disposition imbriquée et défaut récursif

Les champs structure contenus directement partagent le slot du
parent. Le vérificateur calcule les champs terminaux de chaque type,
y compris si une déclaration nomme une structure déclarée ensuite.
Il refuse les cycles de contenance directe avant de vérifier les
corps. Un champ structure omis n'a un défaut que si tous ses champs
terminaux en ont un. Pour une référence sans valeur, le diagnostic
indique le chemin du champ terminal.

Quatre tests ciblés ont réussi, dont une exécution C11 à trois
niveaux sous UBSan. Elle vérifie la valeur, le transfert depuis
une fonction, les deux destructions et la réutilisation de la même
adresse pour un pool de capacité un. Les cycles direct et indirect
par contenance sont refusés. La mutation qui omet un champ terminal
à chaque inclusion imbriquée est détectée par la sortie observée.

Un modèle indépendant additionne les tailles logiques des champs et
vérifie le nombre de zéros précédant un champ terminal distinct.
Avec la graine 20471, 12 dispositions et 202 champs terminaux
correspondent à la sortie C11 à -O0 sous UBSan. Une suite globale
tourne sur une copie figée. L'initialisation explicite d'une valeur
structure imbriquée, les accès à ses champs et la récursion par
indirection de structure restent à implémenter.

## Lecture et mutation des champs Int

Les chemins directs et imbriqués vers un Int sont résolus dans la
disposition du slot. La lecture copie l'Int. L'affectation évalue la
valeur, puis vérifie à nouveau le porteur et les emprunts avant
l'écriture. Les expressions utilisées dans print sont également
indexées et suivies par les analyses de durée de vie et d'effets.

Le test ciblé sur la copie figée a réussi sous UBSan à -O2. Il vérifie
la même adresse avant et après mutation, l'écriture à travers un
paramètre &mut, l'absence de modification d'un champ frère et une
seule destruction. La dernière lecture d'un emprunt partagé dans le
calcul de la valeur permet l'écriture. Une utilisation après
l'écriture la bloque. Le vérificateur refuse aussi un porteur
immuable, un chemin inconnu et une valeur qui réinitialise le pool
du porteur pendant son calcul. Supprimer le contrôle d'accès
précédant l'écriture laisse passer la variante avec emprunt actif
et fait échouer le test de mutation.

Un essai UBSan à -O0 confirme l'écriture de part et d'autre d'un
champ référence, avec les valeurs -12, 99 et 61 conservées aux bons
emplacements. Le lot de 51 tests sur les exigences de pools et les
champs références du cycle précédent a réussi sur sa copie figée.
La suite globale de cette version tourne. Les emprunts par chemin
et la mutation des champs références restent à implémenter.

## Emprunts des champs Int par chemin

Les emprunts des champs Int réutilisent les vérifications d'accès par
chemin des tableaux. Chaque couple allocation et chemin terminal
identifie une seule cible. Le porteur reste réservé pendant l'usage
du champ. Le C utilise une adresse de champ et vérifie statiquement
que la disposition des pointeurs respecte l'alignement des Int.

Deux tests ciblés sous UBSan ont réussi sur le code final. Les cas
exercent deux champs frères mutables, leur passage au même appel,
deux emprunts partagés du même champ, une écriture sur un frère et
le nettoyage. Deux prêts incompatibles du même champ, la lecture
du porteur sous prêt mutable, le drop et le reset prématurés et
l'appel demandant le porteur mutable sous prêt partagé sont refusés.

Le modèle de conflit compare le chemin, le chevauchement des
usages et le mode. Il a révélé un faux refus de deux emprunts
partagés d'un même champ. Le vérificateur réservait par erreur
un intermédiaire mutable au lieu de conserver seulement le
véritable parent de l'emprunt. Après correction, les 16 cas du
modèle donnent 13 acceptations et 3 refus. Quatre essais
supplémentaires sur un porteur reçu en paramètre mutable passent.
Une mutation sur la première version qui crée une nouvelle
identité pour chaque accès au même champ laisse passer un second
prêt mutable et une écriture incompatible. Le test détecte ces
deux défauts.

La suite globale finale est lancée sur une copie figée.
Les emprunts de sous-structures entières, les contrats de retour
des champs et les opérations sur les champs références restent
à implémenter.

## Contrats de retour pour les champs Int inline

L'origine symbolique identifie le paramètre porteur et le chemin
terminal. Les relais recopient chaque chemin possible vers leur
propre paramètre. Le résultat concret réutilise les mêmes identités
de champs que les accès locaux et garde le porteur vivant. Les
tableaux fixes retournés transportent aussi ces chemins dans leurs
contrats de cases.

Trois tests ciblés ont réussi sous UBSan. Les deux branches du relais
mutable sont exécutées. Le champ frère tag reste modifiable, tandis
qu'une écriture sur chacune des cibles possibles est refusée. Les
contrats du vérificateur sont inspectés pour le relais. Un retour
depuis un porteur reçu par transfert est refusé. Un tableau fixe
retourné par un relais permet de modifier un champ frère et conserve
son emprunt jusqu'au dernier usage. Le drop du porteur est refusé
dans les deux formes de retour. Un essai statique supplémentaire
confirme le refus de reset avant le dernier usage et son acceptation
après. La mutation qui omet une branche du contrat de relais fait
échouer la vérification du retour.

La suite globale de cette version est lancée sur une copie figée.
Les contrats de mise à jour de tableaux par des emprunts de champs,
les emprunts de sous-structures et les champs références restent à
auditer ou à implémenter.

## Mise à jour de tableaux injectés avec un emprunt de champ

Le contre-exemple remplace une case par un emprunt de champ Int,
passe par une fonction relais et détruit l'ancienne cible. Le contrat
perdait le chemin du champ au relais. Un second contre-exemple fait
passer une ligne par un réemprunt de case sans nom. L'analyse ignorait
la mise à jour de cette ligne faute de nom, même si son identité
symbolique était connue.

Les résultats symboliques transportent désormais le chemin du champ
dans les mises à jour. Les résultats et les contraintes propagent les
changements de lignes par leur identité, y compris pour un argument
sans nom. Un champ d'un porteur consommé ne peut pas être laissé dans
un tableau injecté.

Trois tests ciblés ont réussi, dont deux exécutions C11 sous UBSan
pour la mise à jour directe et la ligne réempruntée. Les deux
exécutions lisent la nouvelle cible après destruction de l'ancienne,
et modifient le champ frère. Les écritures sur le champ réservé et le
drop prématuré du porteur sont refusés. Deux tests existants sur
les contrats opaques et les mises à jour de lignes ont aussi réussi.
La mutation qui réintroduit le filtre des arguments sans nom fait
échouer la variante avec la ligne réempruntée. La suite globale est
en cours sur une copie figée.

## Copie et retour d'un champ référence partagée

La lecture d'un champ &Int charge sa référence et conserve la
provenance extérieure. Le contrat distingue cette origine de
l'emprunt d'un champ inline. Il conserve les parents de l'emprunt
de la cible, sans prolonger le prêt du porteur. Les relais et
les tableaux fixes retournés propagent aussi l'origine extérieure.

Trois tests ciblés passent sous UBSan. Le cas ST13 détruit le porteur,
réutilise son slot pour une autre cible et lit l'ancienne cible par
deux chemins de retour. Détruire la cible ou réinitialiser son pool
avant lecture est refusé. Copier un champ &mut est refusé. Un essai
statique confirme qu'un emprunt mutable d'origine reste suspendu
jusqu'au dernier usage de la copie partagée, même après destruction
du porteur. Ajouter artificiellement une réservation du porteur au
contrat fait échouer le test de réemploi.

La suite globale tourne sur une copie figée. Les remplacements de
champs références, les réemprunts des champs mutables et le retour
depuis un porteur reçu par transfert restent hors de ce résultat.

## Remplacement d'un champ référence partagée sur un porteur direct

Une affectation de champ &Int évalue la nouvelle référence, vérifie
qu'elle survit au porteur, puis met à jour la provenance et écrit le
pointeur dans le même slot. Les copies antérieures gardent l'ancienne
cible. Les jonctions de branche et les reprises de boucle suivent
les provenances des champs modifiés.

Trois tests ciblés passent sous UBSan. Deux portent sur la mutation.
Ils vérifient l'adresse stable, la lecture de l'ancienne cible après
l'écriture, sa destruction après le dernier usage de la copie et
le retour depuis deux branches qui installent des cibles distinctes.
Le drop prématuré de chaque cible et le stockage d'un emprunt local
au bloc enfant sont refusés. Un essai statique en boucle confirme
que la cible écrite reste protégée après la sortie. La mutation qui
ignore les nouvelles dépendances à la jonction est détectée par
le test de contrat de retour.

La suite globale tourne sur une copie figée. Les écritures via
un porteur emprunté, les champs &mut et le relâchement précis des
ancêtres de réemprunt associés à l'ancienne cible restent à traiter.

## Réemprunt de champs références mutables

Un réemprunt de champ &mut Int suit le chemin dans le porteur et
l'identité de la cible extérieure. Les accès dérivés de la capacité
du champ ne concurrencent pas cette capacité avec elle-même.
Deux réemprunts partagés du même champ réutilisent la même
identité de capacité, ce qui corrige le faux refus observé sur
la première version.

Trois tests ciblés réussissent sous UBSan. Le nouveau scénario
réemprunte deux cibles mutables distinctes via un porteur injecté,
les passe au même appel et modifie un champ frère pendant leur
durée de vie. Il relit le champ après le dernier usage et exerce
deux réemprunts partagés du même champ. Les variantes concurrentes
sur le même chemin, le drop du porteur, le reset des deux pools et
les accès incompatibles à la cible sont refusés. Un essai au
vérificateur conserve aussi le porteur vivant quand le réemprunt
est stocké dans un tableau fixe. La mutation qui recrée la capacité
à chaque projection reproduit le faux refus des deux prêts partagés.
Retirer le chemin du porteur change le diagnostic de drop, mais le
programme reste refusé par le contrôle de la cible dans ce cas.

La suite globale tourne sur une copie figée. Le retour contractuel
de ce réemprunt et le remplacement de champs &mut restent à traiter.

## Contrats de retour des réemprunts de champs mutables

L'origine symbolique du réemprunt indirect contient le paramètre
et le chemin de son champ. Le contrat reconstruit le chemin du
porteur et la provenance de la cible. La vérification du corps
compare les deux avec le résultat déclaré. Les relais et les
tableaux fixes retournés propagent cette origine.

Trois tests ciblés ont réussi sous UBSan. Le retour mutable
conditionnel exerce les deux cibles, autorise l'écriture dans
un champ Int frère et refuse l'accès aux deux chemins possibles
avant le dernier usage. Le drop et les resets prématurés du
porteur ou de la cible sont refusés, de même que le retour
depuis un porteur consommé. Le retour d'un tableau partagé
conserve la réservation du porteur. Supprimer le chemin du
porteur dans la reconstruction du contrat fait échouer la
vérification du corps.

Un essai supplémentaire reste refusé si un relais demande de
réinitialiser le pool d'une cible d'un champ frère inutilisé.
Les exigences de source appliquées à un argument structure
emprunté élargissent la contrainte à ses dépendances. Cette
limite concerne les effets de reset, distincts de l'accès
aux champs frères. La suite globale tourne sur une copie
figée. Le remplacement d'un champ référence mutable reste ouvert.

## Remplacement des champs références mutables

L'affectation directe d'un champ &mut Int exige une nouvelle
capacité mutable exclusive. Elle vérifie la durée de vie et la
réservation du chemin, met à jour la provenance puis écrit dans
le slot existant. L'analyse de résultat conserve la nouvelle
cible si la structure est ensuite retournée.

Trois tests ciblés passent sous UBSan. Le scénario principal
réemprunte le champ par un appel, l'utilise, remplace la cible et
modifie l'ancienne cible. Il vérifie la même adresse du porteur
et le réemprunt suivant de la nouvelle cible. Le remplacement
prématuré, une référence partagée, une cible réservée par un
champ frère et une cible locale trop courte sont refusés. Le
retour d'une structure après remplacement permet de détruire
l'ancienne cible chez l'appelant et protège la nouvelle. Une
mutation supprimant la comparaison des modes accepte à tort
une référence partagée et fait échouer le test.

La suite globale tourne sur une copie figée. Les remplacements
via un porteur emprunté et le relâchement précis de certains
parents de réemprunt après remplacement restent ouverts.

## Remplacement d'un champ via un emprunt local du porteur

Une écriture via un emprunt mutable local met à jour le même
porteur. Le vérificateur exige que sa liaison directe soit visible
et identifiable. Les analyses symboliques répercutent l'écriture
sur cette liaison pour le reste du bloc, aux jonctions et au retour.

Trois tests ciblés passent sous UBSan. Le nouveau cas remplace
le champ via l'emprunt dans les deux branches, lit la nouvelle
cible via le même emprunt puis retourne le porteur. L'appelant
peut détruire l'ancienne cible. La destruction de la nouvelle
cible et le remplacement sous un réemprunt de champ encore
actif sont refusés. Une mutation qui omet la mise à jour de la
liaison directe fait échouer le contrôle du contrat de retour.

Le remplacement via un paramètre emprunté et les écritures
qu'un contrat doit propager au-delà de la fonction restent ouverts.

## Remplacement entier par transfert d'une nouvelle structure

La notation `p = <- points.new(...)` passe maintenant par le même
ordre d'évaluation que les autres remplacements. Le constructeur
s'exécute avant la destruction de l'ancienne allocation. Le
remplacement direct par constructeur sans transfert explicite et
le déplacement d'un champ sont refusés.

Deux tests ciblés ont réussi. Sous UBSan, la dernière lecture
d'un champ de l'ancienne structure peut fournir l'initialiseur du
remplaçant. Le remplaçant possède sa propre adresse et l'ancien
slot est réutilisé par l'allocation suivante. Dans un pool d'un seul
slot, l'exécution échoue par manque de capacité avant toute
destruction. Le vérificateur refuse un usage futur de l'ancien
emprunt. La mutation qui détruit l'ancienne structure avant le
constructeur fait échouer la lecture dans l'initialiseur.

Le lot de régression des réaffectations et la suite globale sur
copie figée sont lancés. La couverture de ST15 et ST16 demeure
partielle pour les structures imbriquées et les chemins de contrôle
combinant plusieurs transferts.

## Copie structurelle dans un pool

Les structures dont les champs terminaux sont copiables peuvent
être copiées dans un nouveau slot. Les Int inline sont indépendants
et les références partagées désignent les mêmes cibles. La copie
dans un pool explicite est décrite par les contrats de fonction.
La copie implicite charge le pool réel depuis la cellule source,
y compris après un retour dont plusieurs pools sont possibles.

Trois tests ciblés ont réussi sous UBSan. Ils couvrent les adresses
distinctes, une mutation inline indépendante, la protection de la
cible partagée, le refus d'un mauvais pool et le refus d'une
structure contenant une référence mutable imbriquée. Un essai
statique confirme la copie implicite dans main avec un pool local.
Le test d'origine conditionnelle vérifie aussi que le pool non
sélectionné conserve son slot disponible. Son premier oracle
laissait survivre une mutation qui choisissait un pool statique.
Une fois ce contrôle de capacité ajouté, le compilateur courant
passe et la copie mutée échoue.

La suite globale est lancée sur une copie figée. La copie implicite
dans une fonction lorsque le pool d'origine est injecté reste
ouverte. L'effet d'allocation doit alors être décrit par le contrat.

## Déclarations et appels de méthodes de structures

Les blocs impl déclarent des fonctions qualifiées par type. Le
premier paramètre est self avec l'un des trois modes explicites
et le type de la structure. La vérification refuse une collision
avec un champ ainsi qu'une seconde déclaration du même nom sur
le même type. Un nom peut être partagé entre types distincts.

Les appels sur une variable se ramènent aux contrats ordinaires.
Seul le receveur peut bénéficier de l'emprunt automatique. Un
receveur consommé exige la notation (-> valeur). Les corps
continuent à être vérifiés, même si aucune méthode n'est appelée.

Un lot ciblé de 29 tests a réussi. Le cas natif sous UBSan
distingue deux méthodes homonymes, exerce un relais via un
paramètre mutable, vérifie la consommation et le réemploi
du slot. Le vérificateur refuse l'écriture par un accès partagé,
le conflit avec un prêt de champ et l'usage après consommation.
Une mutation qui retire le contrôle de collision accepte à tort
une méthode homonyme d'un champ et est détectée.

Les appels sur des receveurs nommés sont couverts. La résolution
des homonymes lorsque le type ne peut pas être déduit par
l'analyse d'effets et les interactions avec les noms des
méthodes intégrées restent à vérifier. La suite globale est
lancée sur une copie figée.

## Résolution des méthodes après une expression de contrôle

L'analyse d'effets conserve le type nominal des valeurs produites
par les bras qui continuent et par les sorties de la boucle
concernée. Elle sélectionne le contrat de méthode par le type
du receveur, y compris si un autre type porte le même nom de méthode.
Les breaks d'une boucle interne ne contribuent pas au résultat
de sa boucle englobante.

Le lot ciblé de 22 tests a réussi. Le cas C11 sous UBSan combine
if, match consommant et loop, exécute les deux branches du if et
vérifie la présence de l'effet d'allocation sur le pool injecté
dans le contrat de la fonction. La méthode homonyme de l'autre
type ne possède pas cet effet. Retirer la propagation du type
des branches if reproduit le refus erroné de l'appel.

La suite globale tourne sur une copie figée. La résolution
des collisions avec les noms intégrés reste à traiter.

## Homonymes de set, drop et reset

Les appels de ces trois noms en instruction sont interprétés
selon le type du receveur. Les structures utilisent leurs
contrats de méthodes. Les pools et les Int utilisent leurs
opérations intégrées et gardent leurs contrôles d'arguments.
Une méthode reset de structure ne produit aucun effet de
réinitialisation de pool sauf si son corps en exécute un.

Le scénario natif sous UBSan combine les trois méthodes d'une
structure avec les trois opérations intégrées. Il vérifie les
sorties, le réemploi du slot Int et la présence d'un seul reset
dans la trace. Le contrat distingue aussi l'effet de reset du
pool de l'appel à la méthode de structure. Les arités invalides
sont refusées. Forcer la classification intégrée pour le receveur
structure fait échouer le scénario.

Deux lots intermédiaires de 58 et 12 tests passent. Le lot final
ciblé et la suite globale sur copie figée sont lancés. Les noms
intégrés utilisables en expression, dont new, copy, len et replace,
restent à traiter.

## Homonymes des opérations intégrées en expression

Les formes partagées avec new et copy des pools, et avec les
méthodes des tableaux, sont résolues sur le type du receveur.
Un constructeur de pool à champs nommés conserve sa syntaxe.
Les signatures ordinaires des méthodes peuvent avoir d'autres
arités que les opérations intégrées. Une opération de tableau
sur un receveur non nommé continue de suivre la syntaxe existante.

Le lot ciblé de quatre tests a réussi. Le scénario C11 sous
UBSan combine un constructeur et une copie de pool avec
les méthodes new et copy de la structure, puis distingue len
et swap sur les deux catégories de receveurs. Les arités
erronées sont refusées selon le type. Une mutation qui ignore
la résolution des homonymes dans l'analyse d'effets traite
à tort le receveur structure comme une source et échoue.

Le test étendu à ref et replace a réussi, ainsi que quatre
régressions ciblées des tableaux. La suite globale est
lancée sur une copie figée. Les compositions de résultats
d'emprunts de méthode directement en argument restent à auditer.

## Emprunt retourné par une méthode directement en argument

Les appels de méthode passent par le même traitement des résultats
empruntés que les appels de fonction. Cela inclut les méthodes dont
le nom ressemble à une opération intégrée. L'emprunt préparé reste
actif pendant l'évaluation des arguments suivants.

Les cas natifs sous UBSan couvrent un emprunt partagé vers un champ
inline, un retour mutable utilisé par un appel d'écriture et une
référence partagée vers une cible extérieure. Un reset du porteur
inline avant l'appel est refusé. Pour la cible extérieure, le reset
du porteur est accepté, et le reset de la cible est refusé. Passer
un résultat partagé comme mutable ou préparer deux emprunts
mutables du même champ est refusé. Retirer l'inscription du
premier emprunt dans les arguments préparés permet à tort la
seconde projection et fait échouer le test.

La suite globale tourne sur une copie figée.

## Référence partagée retournée par un porteur consommé

Un paramètre transféré peut restituer la valeur d'un champ &Int.
Son nettoyage libère le slot du porteur, et le contrat conserve
l'emprunt de la cible extérieure. Les retours directs, les
relais et les tableaux fixes conservent cette distinction.
Un résultat de ce type peut aussi initialiser un champ référence
dans un nouveau constructeur de structure. Les cibles de
l'initialiseur sont retenues pendant les arguments suivants.

Les cas ciblés C11 sous UBSan exercent un pool de capacité un.
Le slot est réutilisé après consommation et les références déjà
rendues gardent leurs cibles respectives. Une nouvelle structure
peut reprendre le même slot et la référence retournée. Le
vérificateur refuse le reset prématuré de la cible pendant
l'initialisation et l'usage du porteur après transfert. Une
mutation qui réserve artificiellement le porteur rend le
contrat inutilisable après consommation et est détectée.

Le lot de régression des champs références et la suite globale
sur copie figée sont lancés.

## Stockage commun de Vector et String

Le runtime partage le descripteur `VectorItems` et ses opérations
de placement, extension, lecture indexée et troncature. La taille
de case est fixe pour le descripteur. La longueur est publiée
après l’initialisation des nouvelles cases. Les deux fronts
conservent l’ordre logique et les adresses des cases déjà
initialisées. Le front descendant utilise provisoirement un
ordre physique inverse. String utilise le même stockage avec
des cases de taille 1, une vue contiguë croissante et ses
validations UTF-8 propres.

Les neuf tests C de croissance et UTF-8 ont réussi sous UBSan
à `-O0` et `-O2`. Le nouveau scénario C remplit les deux fronts
avec des entiers, refuse une extension qui ne tient pas, réduit
le vecteur descendant et réemploie son suffixe. L’adresse du
premier élément de chaque front reste stable. La mutation qui
copie un bloc descendant dans le mauvais ordre est détectée
aux deux optimisations.

Le descripteur et les opérations sont internes au C émis.
La syntaxe et les contrats de Vector dans le langage, les
tranches et le nettoyage des éléments non Copy restent ouverts.

## Vector<Int> et Vector<u8> dans le langage

`pool<Vector<Int>>(n)` et `pool<Vector<u8>>(n)` fournissent des
descripteurs de vecteur. `p.new()` crée un préfixe initialisé
vide. `push` initialise une case avant d’augmenter la longueur,
`len()` observe cette longueur et `v[i]` lit la case par copie
avec contrôle des bornes. Le type de la case reste Int ou u8.
Les constantes entières bornées sont admises en contexte u8.
Les appels, retours, transferts et destructions utilisent les
contrats de pools existants. La lecture réserve le vecteur
pendant les effets éventuels du calcul de son indice.

Quatre tests ciblés ont réussi. Ils exercent les deux types
dans des programmes Crust, deux vecteurs d’un même pool et le
noyau C sur les deux fronts. Une région de 1 Mio conserve sa
limite après transfert vers un scope configuré à 2 Mio.
Les 262 144 cases Int tiennent exactement et l’ajout suivant
produit un diagnostic. Une lecture hors limites et cinq
programmes mal typés ou aliasés sont également refusés.
La mutation du C qui transforme un indice invalide en lecture
de la première case est détectée.

Les suites des fondamentaux, tableaux fixes, effets et croissance
sont relancées. Les vecteurs de handles ou de références, les
mutations et extractions de cases, les tranches et les résultats
de capacité restent à intégrer.

## Retrait de cases Copy

`remove(i)` extrait un Int ou un u8 et décale le suffixe selon
l’ordre logique, puis rend la dernière case disponible. La lecture
bornée précède toute mutation. Pour signaler un index invalide, le
prototype réutilise le diagnostic d’indexation. VE3 ne fixe pas
la forme du signalement. La vérification utilise l’accès exclusif
pendant l’évaluation de l’index et pendant le retrait.

Deux tests ciblés réussissent. Le programme Crust passe par des
fonctions qui reçoivent les vecteurs par emprunt mutable et rendent
le type exact de la case. Il vérifie le retrait au milieu, la
réinsertion et le contenu de l’autre vecteur. Les indices −1 et
longueur échouent au runtime. Le retrait avec un emprunt partagé
encore utilisé est refusé à la compilation. Le harnais C exerce
le retrait sur les deux fronts sous UBSan à `-O0` et `-O2`.
Une mutation qui omet le décalage échoue sur le front descendant
aux deux optimisations. Le lot ciblé utilise des séquences
déterministes et leurs résultats attendus.

VE3 reste partielle. Il reste `pop`, `replace`, les handles et
références, ainsi que leurs interactions avec les tranches.

Le lot de régression `test_foundation_rules test_fixed_arrays test_effects
test_growth_runtime` a réussi avec 232 tests. Ce lot couvre les
interactions synchrones existantes de ces quatre suites.

## Extraction de la dernière case Copy

`pop()` rend `Option<Int>` ou `Option<u8>`. Un vecteur vide rend
`None` sans toucher au curseur. Sinon la dernière case est copiée
dans le résultat avant de réduire la longueur et le curseur.
L’accès exclusif requis est celui des autres mutations de Vector.
Le compilateur réutilise le match de résultats existant pour
distinguer Some et None et type la liaison selon le contenu.

Deux tests Crust ciblés réussissent en C11 sous UBSan à `-O2`.
Un modèle indépendant de listes, graine 4201, compare la
longueur après 48 transitions et la valeur de chaque extraction.
Un passage par fonction conserve le type Option des deux types de
cases et permet de réinsérer l’octet extrait. Trois variantes sont
refusées, avec un emprunt encore utilisé, un match incomplet ou
un bras Ok employé sur Option. La mutation qui rend Some(0) au
lieu de None sur vecteur vide est détectée par le modèle.
Le harnais C réussit sous UBSan à `-O0` et `-O2` et couvre
l’extraction sur les deux fronts et la réutilisation du suffixe.
VE3 reste partielle pour replace, les handles et les références.

Le lot de régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 234 tests.

## Remplacement de cases Copy

`replace(i, valeur)` utilise `Result<T,T>` pour Int et u8,
avec `Ok(ancienne)` et `Err(entrante)`. VE3 impose les deux
issues et leurs contenus. Le prototype reprend la notation
Result existante pour les distinguer. L’index et la valeur sont
évalués dans cet ordre, y compris lorsque l’index est invalide.
Sur échec, l’écriture ne commence pas. Sur succès, la case garde
son adresse et la longueur reste inchangée.

Le premier test avec appels imbriqués a révélé une erreur interne
pour un receveur déjà emprunté. La réservation préparée indiquait
les ancêtres du receveur mais omettait le receveur lui-même.
Elle suspend désormais ce dernier pendant l’évaluation des
arguments. Le test accepté passe par un `&mut Vector<Int>` et deux
appels observables. Les refus couvrent une lecture du vecteur
dans le second argument, un emprunt partagé encore actif, une
valeur du mauvais type et un match Option appliqué à Result.

Les neuf tests ciblés sur Vector passent. Les deux cas de bornes
hors plage sont un indice négatif et un indice égal à la longueur.
Le programme Crust vérifie les valeurs restituées, le contenu et
la longueur, ainsi que le cas u8 sur vecteur vide. Le harnais
du front descendant passe sous UBSan à `-O0` et `-O2`.
Une mutation qui signale à tort un succès sur indice invalide
est détectée aux deux optimisations. Les transferts et provenances
des cases non Copy restent à valider.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 236 tests.

## Croissance faillible et lecture de longueur avant nettoyage

`try_push` accepte une case Copy Int ou u8. Le prototype encode
le résultat en `Result<(),T>`. Une capacité épuisée restitue la
valeur entrante. `Vector<u8>.try_extend` accepte un emprunt partagé
de tableau fixe d’octets. Son résultat est
`Result<(),CapacityError>`. L’erreur `CapacityExceeded` laisse
la longueur, le curseur et le préfixe inchangés. Ces signatures
emploient les conventions de Result existantes. Les tranches de
longueur dynamique et la lecture externe restent ouvertes.

Le premier essai sous UBSan a exposé un accès après libération.
Le C généré pour `return v.len()` détruisait d’abord le vecteur,
fermait son pool puis lisait le descripteur. `String.byte_len()`
avait la même émission différée. Les deux lectures sont maintenant
matérialisées avant le nettoyage. Les scénarios de retour de
longueur sur des valeurs locales passent sous UBSan à `-O2`.

Les tests Crust couvrent un échec d’extension à un octet de la
limite, un ajout à la limite exacte, un refus une fois la région
pleine et une extension réussie. Ils refusent un conflit
d’emprunts, deux arguments de type invalide et une liaison de
valeur à la place de `Ok(())`. Un programme Int sous UBSan
affiche 42 après un ajout réussi. Le harnais C de quatre octets
vérifie l’état exact du front descendant avant et après échec,
sous UBSan à `-O0` et `-O2`. La mutation qui avance la longueur
après échec est détectée aux deux optimisations.

La première régression a relevé une incompatibilité de diagnostic
sur l’extraction d’une valeur depuis Ok(()). Le diagnostic dédié
est rétabli. La seconde exécution des quatre suites
`test_foundation_rules test_fixed_arrays test_effects test_growth_runtime`
a réussi avec 240 tests.

## Tranche d’octets empruntée pour une extension

`dst.try_extend(&src[debut..fin])` accepte une tranche de
`Vector<u8>` sans copie intermédiaire. Les bornes sont évaluées
de gauche à droite sous emprunt partagé de la source, pendant
que la destination est réservée en écriture. Les deux extrémités
sont vérifiées contre la longueur initialisée. Une tranche vide
à la fin est valide. La réservation est limitée à cette
instruction. Le descripteur C conserve la direction physique
pour restituer les octets dans l’ordre logique.

Le programme Crust sous UBSan à `-O2` exerce deux appels de
borne, une tranche vide en fin de vecteur et une mutation de la
source après le dernier usage. Quatre bornes invalides sont
diagnostiquées au runtime. Le vérificateur refuse deux variantes
avec alias, une auto-extension et une mutation de la source
depuis une expression de borne. Le harnais C vérifie le contenu
exact dans les deux sens entre fronts opposés, ainsi qu’un refus
de capacité, à `-O0` et `-O2` sous UBSan. La mutation qui perd
la direction du front descendant échoue aux deux optimisations.

Cette étape couvre l’argument direct de try_extend. Il reste à
intégrer la tranche partagée comme valeur empruntée, ses
contrats et la séparation en tranches mutables de VE5.

Le lot de régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 242 tests.

## Tranche d’octets nommée

Une tranche de Vector<u8> peut être liée avec `let`, annotée
`&[u8]`, réaffectée avec `let mut` et passée à `try_extend`.
Son descripteur conserve la provenance du stockage par le
même suivi de prêts que les vues d’octets de String. Le
vérificateur contrôle que la source survit à la destination
lors d’une réaffectation depuis un bloc enfant.

Le test Crust sous UBSan à `-O2` accepte deux extensions
séparées par une mutation de la source après le dernier usage,
une réaffectation depuis un bloc enfant dont la source est
externe et un drop après la dernière extension. Il refuse cinq
contre-exemples, mutation, drop ou reset avant le dernier
usage, réaffectation depuis une source locale au bloc enfant,
et confusion entre `&[u8]` et `&str`. Une mutation qui termine
immédiatement le prêt nommé laisse passer la mutation et le
drop anticipés. Le test la détecte.

La liveness existante reste conservatrice quand une
réaffectation ultérieure est imbriquée. Les signatures de
fonctions, les autres types de case et les tranches mutables
restent ouverts.

Le lot de régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 243 tests.

## Contrats des tranches partagées d’octets

`&[u8]` est accepté en paramètre et en retour de fonction.
Le vérificateur déduit les provenances d’un vecteur reçu
par emprunt ou d’une tranche injectée, puis les applique
au site d’appel. Un relais ne perd pas les provenances.
Le descripteur C conserve la direction et la longueur
lors des passages de fonction, sans copie du contenu.
`try_extend` accepte aussi directement un résultat emprunté.

Quatre tests de tranches passent sous UBSan à `-O2`.
Les nouveaux scénarios exercent les deux chemins d’un retour
conditionnel, un relais, un appel imbriqué et un reset d’un
pool distinct. Le compilateur refuse les retours de sources
locales ou consommées et les opérations invalidantes qui
précèdent le dernier usage. Un contrat de sources distinctes
interdit le reset du pool d’origine dans la fonction consommatrice.
Une mutation qui omet la deuxième provenance au site d’appel
modulaire laisse passer le drop et le reset anticipés.
Le test la détecte sur ces deux rejets manquants.

Les autres types de case, les tranches mutables et la lecture
externe restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 245 tests.

## Indexation d’une tranche partagée d’octets

`vue[i]` produit un u8 par copie. `&vue[i]` emprunte la
case et propage la provenance de la tranche. Le C émis
fige la vue avant d’évaluer l’indice et vérifie les bornes
de la tranche avant tout calcul de pointeur. Le front
descendant traduit l’indice logique à l’intérieur de la vue.

Neuf tests de tranches passent. Le nouveau scénario Crust
sous UBSan à `-O2` couvre la lecture par fonction, l’indexation
directe d’un résultat, le retour d’un emprunt de case et la
réutilisation d’un u8 copié après destruction de la source.
Les indices −1 et longueur déclenchent un diagnostic.
Le vérificateur refuse le drop avant l’usage d’une référence
retournée, le reset de la source pendant l’évaluation de
l’indice et l’emprunt mutable de la case d’une vue partagée.
Le harnais compare les adresses des cases aux deux fronts
sous UBSan à `-O0` et `-O2`. La mutation qui ignore la
direction physique échoue aux deux optimisations.

Les vues d’autres types et la séparation mutable restent
à intégrer.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 246 tests.

## Tranches partagées de Vector<Int>

`&[Int]` accepte les mêmes bornes semi-ouvertes que
`&[u8]`. Les deux types partagent le descripteur C et
la vérification des bornes. Le calcul d’adresse tient compte
de la taille de la case et du sens du front. Le type de
tranche est conservé lors du passage et du retour par contrat.
Une lecture copie l’Int. Un emprunt de case conserve la
provenance et utilise la représentation des références de
cases de tableaux fixes.

Le scénario Crust sous UBSan à `-O2` couvre les deux fronts,
un relais, un appel de lecture et un retour d’emprunt de case.
L’Int copié est affiché après destruction de la source. Un
indice égal à la longueur est diagnostiqué. Le vérificateur
refuse une mutation ou une destruction trop tôt et une
annotation de type de tranche incompatible. Une mutation
qui supprime la taille de case du calcul de l’adresse est
détectée par UBSan avec un accès Int désaligné.

Les tranches mutables et les cases non Copy restent ouvertes.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 247 tests.

## Initialisation sur place d’une case Int

`Vector<Int>.push_new()` initialise la nouvelle case à zéro
avant de publier sa longueur et de rendre `&mut Int`. La
provenance du vecteur est conservée par les retours d’emprunt,
y compris à travers un relais. La réservation porte sur le
vecteur entier pendant l’usage de la référence de case.
Un vecteur plein utilise le diagnostic de capacité de `push`
et aucune référence de case n’est exposée.

Les deux tests ciblés réussissent en C11 sous UBSan à `-O2`.
Ils couvrent l’initialisation sur les deux fronts, deux
écritures par emprunt, la lecture après dernier usage, le
réemploi d’un slot du pool et le dépassement d’une région
de 1 Mio. Un accès en lecture, un ajout, un drop et un reset
avant le dernier usage sont refusés. Le premier essai avec
relais a détecté une perte du marqueur de provenance de
vecteur dans le résumé. La substitution préserve désormais
ce marqueur. La mutation qui initialise à 1 échoue sur les
trois lectures attendues à zéro.

Les cases d’autres types restent ouvertes, dont u8 qui exige
la prise en charge des emprunts mutables d’octets.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 249 tests.

## Initialisation sur place d’une case u8

`Vector<u8>.push_new()` rend un emprunt mutable local vers
une case d’un octet. Il partage avec Int le chemin d’insertion
qui initialise avant de publier la longueur. Le défaut utilisé
pour u8 est zéro, comme pour le défaut numérique Int déjà fixé.
Le contrôle statique conserve le type u8 lors de la lecture
et de l’écriture déréférencées.

Le test Crust sous UBSan à `-O2` lit le zéro initial, écrit la
case du front descendant puis vérifie les octets voisins et
l’ajout après dernier usage via la sortie exacte NUL + LABC.
L’ajout et le drop prématurés sont refusés. Une constante
hors plage u8 est également refusée. La mutation du C émis
qui initialise à 1 produit SOH au lieu de NUL et est détectée.
Les signatures `&mut u8` et les types de case non Copy restent
ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 250 tests.

## Passage et retour d’emprunts mutables u8

Les fonctions acceptent et rendent `&mut u8`. Les arguments
réempruntent une case mutable, le contrat conserve la provenance
du vecteur ou de l’emprunt reçu, et le C utilise un pointeur
vers uint8_t. Une lecture déréférencée copie la valeur u8.

Le test ciblé sous UBSan à `-O2` fait passer une case par un
constructeur et un relais, écrit la case dans une troisième
fonction et lit directement un autre résultat emprunté. Il
vérifie les octets après destruction du vecteur. Le vérificateur
refuse deux arguments mutables sur la même case, le drop et
le reset prématurés et un argument u8 fourni par valeur.
La mutation qui retire la réservation d’un argument mutable u8
laisse passer le double emprunt. Le test la détecte.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 251 tests.

## Partition de split_at_mut dans le runtime

Le noyau C construit les deux vues sur les intervalles
`[0, i)` et `[i, len)` à partir du même descripteur.
Le contrôle des bornes précède leur construction. Les
partitions vides ne calculent aucune adresse de case et
aucun élément n’est déplacé. Les vues partagées réutilisent
le même calcul d’intervalle.

Le harnais C11 sous UBSan à `-O0` et `-O2` compare chaque
adresse à la case logique correspondante pour chaque point
de séparation sur les deux fronts Int et dans une région u8.
Il couvre les vecteurs vides, les deux bornes hors plage et
des écritures de part et d’autre de la séparation descendante.
La mutation qui décale la moitié droite d’une case vers la
gauche conserve les longueurs mais fait se chevaucher les
adresses. Le test la détecte aux deux optimisations.

Le runtime seul ne contrôle pas la durée des prêts. Il reste
à exposer la liaison des deux tranches dans Crust et à vérifier
que le parent demeure suspendu jusqu’au dernier usage des deux.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 252 tests.

## Liaison des deux moitiés mutables

Le prototype expose `let (mut gauche, mut droite) =
v.split_at_mut(i);`. VE5 fixe la partition et la suspension.
Cette liaison locale donne un nom à chaque moitié. Le compilateur
évalue l’indice une fois sous réservation du vecteur et conserve
la preuve de disjonction dans les capacités des deux moitiés.
Les écritures indexées et les réemprunts de cases utilisent
cette preuve. Le vecteur reste réservé jusqu’au dernier usage
de chaque moitié et de ses réemprunts.

Deux tests Crust sous UBSan à `-O2` exercent la séparation sur le
front descendant Int et via un paramètre mutable de Vector<u8>.
Ils vérifient l’ordre d’évaluation, deux emprunts de cases
simultanés, les écritures et la reprise du parent. Cinq
contre-exemples vérifient la lecture et l’écriture prématurées
du parent, le drop, le reset et la destruction de la source
pendant l’évaluation du membre droit. La mutation qui traite
les moitiés comme des emprunts partagés laisse passer une
lecture prématurée et est détectée.

Les moitiés sont des liaisons locales. Le passage et le retour
des tranches mutables elles-mêmes et les cases non Copy restent
ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 254 tests.

## Contrats de tranches mutables

Les signatures acceptent `&mut [Int]` et `&mut [u8]`.
Passer une moitié nommée réemprunte sa capacité. L’argument
préparé garde la preuve de disjonction avec l’autre moitié.
Un résultat d’appel peut initialiser une nouvelle liaison ou
servir d’argument. Une fonction peut aussi retourner une moitié
de vecteur reçu par emprunt mutable. Une simple affectation
depuis le nom d’une moitié est refusée.

Deux tests ciblés sous UBSan à `-O2` exercent un appel à deux
moitiés Int après relais, puis le retour d’une moitié u8 depuis
un vecteur emprunté. Ils vérifient les écritures et la reprise
du parent après le dernier usage. Le vérificateur refuse le
double passage d’une moitié, la réutilisation prématurée de la
moitié ou du vecteur, la copie implicite et le retour depuis un
vecteur consommé. La mutation qui omet la réservation pendant
la préparation des arguments laisse passer le double emprunt
et est détectée.

Le retour groupé des deux moitiés et les cases non Copy restent
ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 256 tests.

## Lecture externe bornée dans le runtime C

Le noyau synchrone lit depuis un descripteur POSIX dans l’espace
libre de Vector<u8>. Il distingue les octets reçus, la fin de
flux, l’espace épuisé et une erreur accompagnée de son code.
La capacité borne l’appel et seuls les octets reçus sont
publiés. Un vecteur plein ne consomme aucun octet. Sur le
front descendant, les octets reçus sont rangés dans l’ordre
logique avant de publier la longueur. La fin de flux et
l’erreur laissent la longueur et le curseur intacts.

Le harnais C11 sous UBSan à `-O0` et `-O2` emploie de vrais
tubes POSIX. Il vérifie une lecture courte, la fin de flux,
EBADF, le remplissage exact de l’espace entre fronts et
la lecture de l’octet restant par une région indépendante.
Les préfixes des deux vecteurs restent intacts. La mutation
qui publie la capacité demandée au lieu du nombre reçu
est détectée aux deux optimisations.

Cette étape utilise la durée synchrone de l’appel natif.
L’API publique, le prêt vérifié au site d’appel Crust et
les interactions avec l’async restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 257 tests.

## Annotation locale A<T>

`let a: A<T> = pool.new(...)` explicite le type du handle.
Le vérificateur exige une allocation du type T dont toutes
les sources possibles sont des pools typés compatibles.
La contrainte reste attachée à un receveur annoté lors de
son remplacement. Le C conserve la représentation par
pointeur de cellule et la provenance stockée dans la cellule.

Deux tests ciblés passent. Sous UBSan à `-O2`, le transfert
entre receveurs garde l’adresse de l’objet entrant. Deux
pools de capacité un réutilisent chacun leur propre slot
après le remplacement puis le drop. Le test observe quatre
destructions pour quatre objets. Le vérificateur refuse une
valeur inline, un autre type, une allocation de datastack et
son transfert dans un receveur annoté. Une mutation qui retire
la vérification des sources accepte les deux cas datastack et
est détectée.

Cette étape couvre l’annotation des liaisons locales. Les
signatures A<T>, les emprunts distincts du handle et de son
contenu, et le stockage de handles dans Vector restent ouverts.

La première régression a détecté deux incompatibilités avec
des structures existantes nommées A. La syntaxe A<T> est
désormais reconnue seulement lorsque le nom est suivi de
`<`. Les deux tests historiques concernés réussissent après
correction.

La régression des fondamentaux, tableaux fixes, effets et
croissance a ensuite réussi avec 259 tests.

## Emprunts du contenu d’un A<Int>

`vref()` et `mut_vref()` produisent respectivement `&Int`
et `&mut Int` sur une allocation issue d’un Pool<Int>. Les
méthodes vérifient le receveur, les provenances et la
mutabilité avant de réutiliser les capacités de prêt
existantes. La mutation agit dans la cellule à son adresse
courante. Les appels acceptent ces résultats directement.

Deux tests ciblés passent. Le scénario C11 sous UBSan à `-O2`
écrit et lit par fonction puis transfère l’allocation et
compare son adresse avant et après. Le vérificateur refuse
l’emprunt mutable concurrent, le drop et le reset prématurés,
la mauvaise arité et la mutation d’un receveur immuable.
La mutation qui retire le contrôle d’écriture à la création
du prêt mutable est détectée.

Les méthodes d’emprunt du handle lui-même, les autres types
de contenu et les signatures A<T> restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 261 tests.

## Emprunts du handle A<Int> et égalité de contenu

`ref()` et `mut_ref()` empruntent le slot du receveur
A<Int>. Le C utilise un pointeur vers le pointeur de cellule.
La provenance retient l’allocation et interdit son remplacement
ou sa destruction tant que le prêt reste actif. Un emprunt du
handle ne satisfait pas une demande de `&Int`. `vequals` reçoit
un emprunt du handle et compare les Int pointés. Son résultat
est de type bool et peut être utilisé dans une condition ou
retourné par une fonction.

Deux tests ciblés passent. Le programme Crust sous UBSan à
`-O2` compare des valeurs égales entre pools, modifie l’une des
valeurs après la fin du premier prêt et vérifie l’inégalité.
Le vérificateur refuse la confusion entre les deux types de
prêt, le drop et le remplacement pendant un prêt, l’accès
direct pendant un prêt exclusif et l’arithmétique sur bool.
La mutation qui compare les adresses au lieu des contenus
est détectée.

Les signatures `&A<T>` et `&mut A<T>`, le remplacement par
l’emprunt mutable et les contenus d’autres types restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 263 tests.

## Remplacement via un emprunt mutable de handle

`*h = <- nouveau` remplace un A<Int> via un emprunt mutable
direct du receveur dans le même scope. La réservation reste
active pendant l’évaluation du remplaçant. Le C matérialise
la valeur entrante, détruit l’ancienne cellule puis écrit le
pointeur dans le slot du handle. La provenance du receveur
et de son emprunt suit la cellule entrante. Les contrats de
résultat et de sources suivent le même changement.

Deux tests ciblés passent. Le programme C11 sous UBSan à
`-O2` vérifie l’ordre de nettoyage de l’appel à droite et
de l’ancien objet. Il réutilise le premier slot avant le
retour, récupère le handle issu du second pool, réinitialise
le premier pool et réutilise le second slot après drop.
Cinq rejets couvrent un prêt partagé, l’absence de transfert,
l’auto-déplacement, le drop et le reset avant le dernier usage
du prêt après remplacement. La mutation qui omet l’écriture
du nouveau pointeur est détectée sous UBSan.

Le remplacement par une référence reçue en paramètre ou
depuis un bloc enfant reste ouvert.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 265 tests.

## Signatures d’emprunt de handle A<Int>

`&A<Int>` et `&mut A<Int>` peuvent être passés et retournés
par fonction. Le C passe le pointeur vers le slot. L’analyse
des arguments réemprunte la capacité existante et restitue
la provenance du slot selon le contrat. Elle distingue
l’emprunt du handle de celui du contenu Int.

Deux tests ciblés passent. Le scénario natif sous UBSan à
`-O2` fait relayer un prêt mutable, puis le réemprunte pour
une comparaison partagée. Il exerce aussi le passage direct
de `ref()` et l’accès au contenu après le dernier usage.
Les rejets couvrent le double prêt mutable, le drop et
le reset prématurés, la confusion avec `&Int` et le retour
d’un prêt vers un slot local. La mutation qui omet la
réservation d’un argument de handle laisse passer un
double prêt et est détectée.

Le remplacement via un handle reçu en paramètre requiert
encore un effet de contrat pour mettre à jour le receveur
chez l’appelant. Les signatures de handles transférés et les
autres types de contenu restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 267 tests.

## Signatures de handles transférés

Les signatures `-> A<T>` et `<- A<T>` conservent la
contrainte de pool dans le contrat consommé par le
vérificateur modulaire. Le compilateur réutilise la
représentation des allocations de T pour le C.
L’entrée et toutes les sorties restent soumises aux
transferts explicites et au contrôle de provenance.

Deux tests ciblés réussissent. Le scénario Int sous UBSan
à `-O2` fait passer un handle par deux fonctions et vérifie
son identité, la valeur lue et le réemploi du slot après
drop. Le vérificateur refuse une entrée issue de datastack
et deux retours dont le contrat ne garantit pas un Pool<Int>.
La mutation qui retire le marqueur du contrat modulaire
laisse passer l’entrée issue de datastack et est détectée.
Un scénario A<String> a également été vérifié statiquement.

Le stockage dans des agrégats et la distinction complète
des receveurs de méthodes restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 269 tests.

## Stockage et destruction des handles de vecteur dans le C

Une case de handle stocke le pointeur de cellule. Celle-ci
porte déjà son pool d’origine. La destruction du vecteur
nettoie le préfixe encore présent en ordre logique inverse
avant de rendre le stockage du vecteur. Les opérations de
déplacement de cases transportent le pointeur et préservent
l’adresse de la cible.

Le harnais C11 sous UBSan à `-O0` et `-O2` remplit le front
descendant avec des cellules de deux pools. Il vérifie la
restitution après ajout ou remplacement refusé, la provenance
après remplacement réussi, remove et pop, puis le transfert
d’une cellule extraite vers l’autre front. Les destructions
rendent les slots à leurs pools. Les cellules extraites
restent vivantes jusqu’à leur nettoyage explicite ou leur
réinsertion. La mutation qui omet la destruction des
éléments est détectée aux deux optimisations.

Le noyau suppose des transferts exclusifs et des pools
encore vivants. Le vérificateur Crust doit encore prouver
ces conditions avant d’exposer ces opérations au langage.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 270 tests.

## Insertion de handles depuis Crust

Le prototype construit des `Vector<A<Int>>` dans un pool
typé. `push(-> valeur)` reçoit un handle d’un Pool<Int> dont
le scope survit au vecteur. La responsabilité de nettoyage
passe à la case et la liaison source cesse d’être utilisable.
Les provenances possibles sont réunies aux jonctions. Un
reset qui toucherait un élément encore stocké est refusé,
y compris lorsque l’effet est connu par un contrat d’appel.

Deux tests ciblés réussissent. Sous UBSan à `-O2`, le
programme insère deux éléments de pools différents, observe
les destructions des éléments avant celle du vecteur puis
réutilise les deux slots d’origine. Le vérificateur refuse
cinq variantes, dont le transfert implicite, la réutilisation
du handle, un pool trop court et deux formes de reset.
La mutation qui perd les provenances lors d’une jonction
laisse passer le reset après le if et est détectée.

Le périmètre actuel couvre les vecteurs et pools d’éléments
locaux. Le passage du vecteur par transfert ou par signature,
les pools d’éléments injectés, les extractions et les emprunts
de cases restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 272 tests.

## Extraction remove de handles

`let a = <- v.remove(i)` extrait un A<Int> et déplace les
cases suivantes sans déplacer les objets. La liaison reçue
reprend la responsabilité du nettoyage. Le vérificateur
conserve la provenance par position quand la longueur est
connue. Un indice dynamique réunit les sources possibles.
Lorsque des chemins se rejoignent avec des longueurs
différentes, il garde une union conservatrice des pools.

Les deux tests ciblés passent sous UBSan à `-O2`. Ils
exercent une extraction dynamique dans une fonction et une
séquence de deux retraits inter-pools avec vérification
des adresses et reset après le drop de l’élément concerné.
Le compilateur refuse l’absence de transfert et deux
resets prématurés. Un indice hors limites est diagnostiqué
au runtime. La mutation qui oublie les sources des cases
restantes est détectée lors de la deuxième extraction.

Les cas où la longueur est inconnue peuvent maintenir une
réservation conservatrice du pool après une extraction.
`pop`, `replace`, les résultats non Copy et les vecteurs
d’emprunts restent ouverts dans le langage.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 274 tests.

## Emprunt d’une case de Vector<A<Int>>

`&v[i]` et `&mut v[i]` empruntent le slot du handle après
vérification de l’indice. Le pointeur C désigne la case
initialisée. Le prêt conserve la provenance du vecteur.
L’accès direct par index est refusé pour éviter une copie
du handle. Un réarrangement attend la fin du prêt. Un prêt
mutable réserve le vecteur aussi en lecture.

Le test Crust sous UBSan à `-O2` exerce les deux modes sur
le front descendant via une fonction recevant `&A<Int>`.
Il retire ensuite la case et vérifie le contenu ainsi que
la longueur du vecteur de l’autre front. Les refus couvrent
la copie implicite, le retrait ou la lecture sous prêt
incompatible et le reset d’un pool d’origine. Un indice hors
limites est diagnostiqué. La mutation qui réduit le prêt
mutable à un prêt partagé laisse passer la lecture
prématurée et est détectée.

Le remplacement via un emprunt mutable de case, les
vecteurs d’emprunts et le suivi de disjonction entre
plusieurs cases de handles restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 275 tests.

## Disjonction des emprunts de cases de handles

Deux indices littéraux différents permettent deux emprunts
exclusifs de cases du même Vector<A<Int>>. Le vérificateur
conserve l’indice dans la chaîne de réemprunts. Il n’utilise
la preuve de disjonction que si elle vaut sur toutes les
provenances de l’emprunt pour la racine examinée. Un indice
dynamique est traité comme potentiellement aliasé. Les
mutations structurelles réservent toujours le vecteur entier.

Les six tests ciblés sur les vecteurs de handles passent.
Le nouveau programme sous UBSan à `-O2` passe deux prêts
mutables à une fonction, compare les deux contenus et retire
ensuite une case. Les variantes avec le même indice ou un
indice calculé sont refusées. Une mutation qui ignore
l’égalité des indices laisse passer le double emprunt de
la même case et est détectée.

La preuve de disjonction de deux indices calculés reste
ouverte. Le remplacement de la case via son emprunt
mutable reste également ouvert.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 276 tests.

## Remplacement d’un handle par emprunt de case

`*h = <- remplaçant` fonctionne lorsque h est un emprunt
mutable d’une case de Vector<A<Int>>. Le prêt reste actif
durant l’évaluation du remplaçant. L’ancienne cellule est
détruite avant la mise à jour du pointeur. Les autres cases
et leurs emprunts disjoints restent valides. La provenance
est remplacée à la position prouvée et réunie aux sources
possibles lorsque la position ou la racine reste incertaine.

Le test sous UBSan à `-O2` vérifie l’ordre de nettoyage avec
un appel sur le membre droit, l’usage d’un prêt vers la
case voisine, le reset du premier pool et l’extraction
du nouveau handle. Les refus couvrent un prêt partagé,
l’absence de transfert, le reset du nouveau pool et un
pool trop court. La mutation qui omet la destruction
laisse un slot vivant et est détectée au reset.

Ce remplacement détruit l’ancien objet. La méthode
`replace` qui le restitue et les pools injectés restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 277 tests.

## Transferts inter-scopes des vecteurs de handles

Les transferts de Vector<A<Int>> entre blocs conservent la
responsabilité de nettoyage et les provenances des cases.
La vérification de destination inclut tous les pools des
éléments. Les jonctions conditionnelles et les résultats de
boucle conservent les positions compatibles et élargissent
les sources lorsque nécessaire.

Deux tests ciblés passent. Le scénario sous UBSan à `-O2`
sort d’une boucle par `break <-`, transfère le vecteur dans
un enfant puis le rend au parent. Il compare l’adresse du
vecteur et extrait les deux valeurs dans leur ordre initial.
Les refus couvrent un pool d’élément local au scope quitté
et un reset qui touche une provenance possible après un if.
La mutation qui retire le contrôle de durée de vie du pool
d’élément laisse passer le transfert dangereux et est détectée.

Les signatures de fonctions avec vecteur de handles et
les pools d’éléments injectés restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 279 tests.

## Passage partagé de vecteurs de handles

Une fonction peut recevoir `&Vector<A<Int>>` et retourner
`&A<Int>` vers une case. Le contrat retient le ou les
vecteurs possibles. Un relais conserve ces provenances.
Le résultat reste un emprunt du slot du handle.

Deux tests ciblés passent sous UBSan à `-O2` pour le chemin
natif. Un retour conditionnel suivi d’un relais réserve
les deux vecteurs possibles. Après le dernier usage, leurs
éléments sont extraits et vérifiés. Les refus couvrent
le retrait prématuré dans chaque vecteur, l’évasion d’une
case de vecteur local et un retrait via un paramètre partagé.
La mutation qui retire la deuxième provenance est détectée
lors du contrôle du retour conditionnel.

Les paramètres mutables, les vecteurs transférés dans les
signatures et les pools d’éléments injectés restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 281 tests.

## Emprunt mutable de vecteur de handles en paramètre

Une fonction recevant `&mut Vector<A<Int>>` peut retourner
`&mut A<Int>` vers une case. Le contrat garde le mode exclusif
et la provenance du vecteur à travers un relais. Le receveur
chez l’appelant peut remplacer le handle au moyen de cet
emprunt. La provenance du nouveau pool remplace celle de
l’ancien quand la case est déterminée.

Le test sous UBSan à `-O2` utilise un index paramétré,
relaye le résultat, remplace la case chez l’appelant,
réinitialise l’ancien pool puis extrait le nouveau handle.
Le vérificateur refuse une lecture, un drop ou un reset
prématuré, ainsi que le retour d’un emprunt mutable à partir
d’un paramètre partagé. La mutation qui affaiblit le mode
du résultat lors d’un appel modulaire est détectée.

Les mutations structurelles à travers le paramètre lui-même
et les signatures de vecteurs transférés restent ouvertes.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 282 tests.

## Passage de vecteurs de handles par transfert

Les signatures `-> Vector<A<Int>>` et `<- Vector<A<Int>>`
transmettent la responsabilité du nettoyage. Le contrat
combine les pools et les positions des vecteurs entrants
qui peuvent fournir le résultat. Le retour conserve
l’adresse du vecteur choisi et les pools de ses éléments.

Deux tests ciblés sous UBSan à `-O2` vérifient le retour
conditionnel puis le relais d’un vecteur, ainsi que la
consommation d’un vecteur et le réemploi du slot d’un
élément. Un reset de chacun des pools possibles est refusé
tant que le résultat peut contenir son élément. La mutation
qui efface les provenances lors de l’application du contrat
est détectée à l’extraction du résultat.

Les mutations structurelles des vecteurs reçus et
l’injection des pools qui fournissent leurs éléments
restent ouvertes.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 284 tests.

## Pop d’un handle dans un match consommant

`match <- v.pop()` distingue Some et None. Le prototype
abaisse ce match direct en un test de longueur, puis retire
la dernière case uniquement dans Some. La liaison de ce bras
reçoit le handle et sa provenance. `Some(_)` nettoie également
l’élément extrait. Le bras None traite le vecteur comme vide.

Deux tests ciblés passent. Sous UBSan à `-O2`, le programme
couvre un vecteur vide, deux pools d’origine, l’adresse
conservée de l’élément extrait, le reset de son pool et
le nettoyage unique du résultat ignoré. Le compilateur
refuse un match sans transfert, un match incomplet et
l’opération sous emprunt actif. Une mutation qui retire
la première case au lieu de la dernière est détectée.

Ce lot couvre la consommation directe des deux variantes.
Le stockage ou le passage d’une Option<A<Int>> comme valeur,
la méthode replace non Copy et la précision des longueurs
après des chemins divergents restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 286 tests.

## Replace de handles dans un match consommant

`match <- v.replace(i, -> nouveau)` reçoit l’ancienne cellule
dans Ok et la cellule entrante dans Err. Le C fige l’indice
puis évalue l’entrant avant d’appeler le remplacement borné.
Le bras Ok met à jour la provenance de la case. Le bras Err
conserve les provenances et le contenu du vecteur. Dans les
deux cas, le bras reçoit la responsabilité du handle rendu,
y compris si la liaison l’ignore.

Deux tests ciblés passent. Sous UBSan à `-O2`, le scénario
compare les adresses des deux résultats, réinitialise
l’ancien pool après le drop dans Ok et extrait le nouveau
contenu. Le vérificateur refuse un transfert implicite,
l’usage de l’ancien nom de l’entrant et l’absence d’un bras.
La mutation qui remplace à l’indice zéro malgré un autre
indice est détectée.

Les résultats non Copy restent consommés directement par
match. Leur stockage et leur passage par fonction restent
ouverts, tout comme try_push non Copy.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 288 tests.

## Try_push de handles dans un match consommant

`match <- v.try_push(-> entrant)` reçoit `Ok(())` si la case
est insérée et `Err(handle)` si le stockage est plein. En
cas de succès, le vecteur prend la responsabilité du
nettoyage et retient le pool entrant. En cas d’échec,
le vecteur reste inchangé et le bras Err reçoit cette
responsabilité. Le nom d’origine n’est plus utilisable.

Les deux tests ciblés passent sous UBSan à `-O2` pour le
chemin natif. La région de 1 Mio est remplie avec 131 072
handles de huit octets sur la cible testée. L’ajout refusé
rend la même adresse et la même valeur, et permet le reset
du pool entrant après drop dans Err. Le vérificateur refuse
l’absence de transfert, une liaison de valeur dans Ok,
l’usage de l’ancien nom et le reset prématuré dans Ok.
La mutation qui omet le pool entrant dans la branche Ok
laisse passer ce reset et est détectée.

Le stockage et le passage des résultats non Copy restent
ouverts. Les pools injectés ne sont pas encore pris en
charge par l’insertion.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 290 tests.

## Push local depuis un handle injecté

Un vecteur local peut recevoir un `A<Int>` passé à la fonction.
Lorsqu'un reset suit l'insertion, le contrat exige que le pool
réinitialisé soit distinct de la provenance de l'élément. La
contrainte s'applique aussi au reset effectué par une fonction
appelée. L'origine du slot et son adresse restent inchangées.

Le test ciblé exécute le C sous UBSan à `-O2`. Il vérifie la
destruction unique de l'élément et le réemploi de son adresse
avec un reset sur un autre pool. L'appel est refusé quand les
pools coïncident, avec un reset direct et avec un relais. Une
mutation en mémoire qui retire la contrainte laisse passer les
deux contre-exemples et fait échouer le test.

L'analyse conserve la contrainte jusqu'à la sortie de la
fonction, y compris après un retrait ou un drop du vecteur.
Cette approximation peut refuser un reset valide après
nettoyage. Les autres insertions et la mutation structurelle
d'un vecteur injecté restent ouvertes.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 291 tests. Un appel supplémentaire
par une fonction relais a aussi vérifié que l'exigence de
sources distinctes se propage jusqu'à l'appelant final.

## Échanges locaux depuis un handle injecté

Un `Vector<A<Int>>` local accepte désormais le transfert d'un handle
reçu par la fonction dans `match <- v.replace(i, -> a)` et
`match <- v.try_push(-> a)`. Le contrat exige que tout reset
postérieur porte sur une autre source. Cette condition protège aussi
le handle rendu au bras Err.

Le test ciblé sous UBSan à `-O2` exécute replace avec un indice
valide puis invalide, et try_push avec de la place. Il vérifie les
valeurs, la longueur, la destruction unique et le réemploi du slot.
Le test de capacité existant exerce Err de try_push avec une
allocation locale. Les quatre contre-exemples combinant opération
et bras sont refusés lorsque le reset par relais cible le pool de
l'entrant. Une mutation qui retire la provenance des échanges fait
accepter les quatre et fait échouer le test.

Un autre test sous UBSan remplit 131 072 cases sur une région de
1 Mio. Le bras Err de try_push restitue le handle injecté avec la
même adresse et la même valeur, et la longueur reste inchangée.
Le pool réutilise le slot après la sortie de la fonction.

Le remplacement d'une case par `*h = <- a`, avec `h` un emprunt
mutable local et `a` un handle injecté, applique la même exigence
de provenance. Le test natif réinitialise l'ancien pool après
remplacement, extrait le nouveau handle sans déplacement et
vérifie son nettoyage unique et le réemploi de son slot. La
mutation supprimant l'exigence laisse passer le reset du pool
entrant. Le refus a également été vérifié avec un emprunt de
case retourné par un appel.

Le suivi reste conservateur après nettoyage, y compris après un
drop dans Err. La mutation structurelle d'un vecteur injecté et
le transport des résultats non Copy restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et croissance
a réussi avec 294 tests. Un essai natif supplémentaire a exercé
`try_push(-> source.new(91))` depuis un pool injecté, puis la
réutilisation de ce pool à l'appelant.

## Retour du handle restitué dans Err

Dans un match consommant sur replace ou try_push, la liaison
de Err conserve les provenances symboliques et l'identité de
l'entrant. Le contrat de fonction peut donc décrire le handle
retourné sans reparcourir le corps à l'appel. Les sources
locales restent interdites en retour.

Le test sous UBSan à `-O2` appelle replace avec deux pools
possibles. Il exécute les deux bras, compare les adresses
retournées à celles des paramètres et vérifie le réemploi
des deux slots. Un reset avant usage est refusé côté appelant.
Le retour de l'entrant alloué dans le pool local est refusé.
Une mutation en mémoire qui attribue une identité neuve au
handle restitué fait échouer la vérification du contrat dans
les deux exécutions. Un essai natif de try_push à pleine
capacité a également rendu le handle à l'appelant avec la
même adresse et la valeur 37.

Le retour depuis Ok de replace et le retour des handles
extraits par pop ou remove demandent encore un suivi des
identités stockées dans les cases. Le transport de l'Option
ou du Result non Copy entier reste ouvert.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 295 tests.

## Copie d'une structure issue d'un pool injecté

`copy(original)` peut allouer dans un pool injecté dont
l'effet d'allocation est déjà établi dans la fonction. Le
contrat conserve le pool d'origine et décrit le résultat
comme un slot neuf. La copie compte comme un accès en écriture
au pool lors de l'évaluation des arguments.

Le test sous UBSan à `-O2` vérifie les adresses distinctes,
la modification indépendante de l'original, le retour de la
copie et le réemploi du slot de l'original. Avec un seul slot,
la copie déclenche un diagnostic. La vérification refuse un
reset du pool avant le dernier usage du résultat et une copie
pendant qu'un autre argument réserve le pool. Une mutation du
C généré qui omet la copie des champs produit Point(0) et
fait échouer le test.

Le pool d'origine connu uniquement par un paramètre objet
demande encore une représentation de cet effet dans le
contrat. Le retour des handles extraits du vecteur demande
un suivi des identités à travers les mutations et jonctions.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 296 tests. Le test ciblé a été
réexécuté après ajout du cas de réservation par un argument.
Un essai natif supplémentaire a confirmé que l'effet
d'allocation remonté par un appel permet aussi de copier et
de retourner une structure issue du même pool injecté.

## Copie depuis le pool d'origine d'un paramètre objet

Le contrat décrit un slot neuf dans le pool d'origine du paramètre
objet. La résolution se propage à travers les relais et conserve les
dépendances des champs copiés. Les écritures implicites de pool sont
propagées même si la fonction ne retourne pas la copie. Le rapport
`effects` expose ces écritures sous `copy_writes`.

Le test sous UBSan à `-O2` passe une vue par emprunt partagé à deux
fonctions successives. Il vérifie les adresses distinctes, la survie
de la copie après destruction de l'original et le réemploi du slot.
Le vérificateur protège la cible partagée et refuse un appel imbriqué
qui copie pendant qu'un argument précédent réserve déjà le pool.
Une mutation supprimant la propagation de l'écriture fait accepter
ce dernier contre-exemple.

Le support se limite aux types de champs déjà pris en charge par la
copie structurelle.

La régression des fondamentaux, tableaux fixes, effets et croissance
a réussi avec 297 tests. Le test CLI a été relancé après l'ajout du
champ JSON. Un essai vérifie le contenu du rapport pour un relais.
Un autre vérifie la propagation depuis une fonction Void, avec un
pool distinct accepté et le même pool refusé.

## Initialisation nommée des champs imbriqués

`pool.new(segment.start.x: expression)` utilise la notation
des chemins de champs pour désigner un champ terminal. Chaque
chemin est résolu dans la disposition aplatie de la structure.
L'instance entière occupe un seul slot. Les champs Int omis
prennent leur défaut et une référence omise est refusée.

Le test sous UBSan à `-O2` vérifie l'ordre des expressions
quand l'ordre écrit diffère de celui de la déclaration. Il
contrôle la valeur et la référence retournées via contrat,
la durée de vie de la cible et le réemploi du seul slot.
Le vérificateur refuse les doublons, les chemins inconnus,
l'initialisation d'une sous-structure entière avec un Int
et un reset pendant l'évaluation des arguments. Une mutation
qui inverse les initialiseurs fait échouer le contrôle
d'ordre. Un essai vérifie que `ints.new(b.point.x)` reste
un appel positionnel.

L'initialisation explicite couvre les champs terminaux
pris en charge. Les valeurs de sous-structure complètes
et les emprunts de sous-structure restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 298 tests.

## Réaffectation d'un champ partagé via un paramètre mutable

Une fonction Void peut modifier un champ `&Int` d'une structure
reçue par `&mut`. Son contrat décrit les cibles encore possibles
à la sortie. Un appel qui écrit sur tous les chemins libère
l'ancienne réservation. Une écriture conditionnelle conserve
les deux provenances. Les relais propagent le même contrat.

Le test sous UBSan à `-O2` exerce le remplacement direct via
relais et les deux sorties d'une mise à jour conditionnelle.
Il vérifie la destruction de l'ancienne cible après remplacement
inconditionnel et le refus de détruire l'une des cibles possibles
avant usage après la jonction. Une cible de durée trop courte
est refusée dans le corps ou chez l'appelant. Un essai séparé
accepte un reset d'un pool distinct après mise à jour et refuse
le reset d'un pool qui fournit la nouvelle cible. La suppression
du résumé d'écriture fait échouer le test, car la réservation
de l'ancienne cible persiste à l'appelant.

Le contrat couvre un porteur unique et un champ partagé dans
une fonction Void. Les champs mutables injectés et la
combinaison d'une mise à jour avec un résultat restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 299 tests. Le test ciblé a aussi été
relancé après ajout du diagnostic pour un porteur non nommé.

## Mise à jour d'un champ partagé et résultat du même appel

Une fonction peut remplacer un champ partagé et retourner un
résultat. Les provenances symboliques du résultat sont résolues
sur les paramètres à l'entrée, avant publication des nouvelles
cibles de champs. Le vérificateur du corps utilise le même état
d'entrée pour contrôler les retours directs d'emprunt.

Le test sous UBSan à `-O2` renvoie l'ancienne cible à travers
un relais et lit la nouvelle cible depuis le porteur. Il vérifie
que l'ancienne cible peut être détruite après le dernier usage du
résultat, mais que chaque cible reste protégée avant son dernier
usage respectif. Une mutation qui résout le retour après la mise
à jour fait échouer la vérification de provenance. Un essai natif
exerce aussi un retour d'allocation contenant l'ancienne référence.

La mise à jour d'un champ mutable injecté et la mutation d'un
porteur dont l'identité est ambiguë restent ouvertes.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 300 tests.

## Réaffectation d'un champ mutable par contrat

Un porteur unique passé par `&mut` peut recevoir un nouveau
`&mut Int` dans l'un de ses champs. Le contrat propage la
réaffectation et la réservation de la nouvelle cible à travers
les fonctions relais. La jonction conditionnelle conserve les
cibles possibles sur chaque chemin.

Le test sous UBSan à `-O2` réutilise l'ancienne cible après
le remplacement certain, écrit via le champ puis reprend le
prêt d'origine après destruction du porteur. Il exerce les
deux sorties d'une mise à jour conditionnelle. Le vérificateur
refuse l'accès via le prêt d'origine, la mutation directe et
le drop de la nouvelle cible avant usage du porteur. Il refuse
aussi de placer la même capacité mutable dans deux champs.
Une mutation supprimant le résumé d'écriture fait accepter
un accès incompatible à la nouvelle cible.

Le cas qui réaffecte le champ mutable puis retourne son
réemprunt dans le même appel reste refusé. Le contrat doit
alors conserver la réservation du chemin et suivre sa cible
après la réaffectation. Les porteurs ambigus restent ouverts.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 301 tests. Un essai supplémentaire
a refusé l'appel de remplacement tant qu'un réemprunt de
l'ancien champ devait encore être utilisé.

## Réemprunt retourné après réaffectation d'un champ mutable

Le contrat résout un réemprunt indirect sur l'état du champ
après réaffectation. Il préserve la réservation du porteur
et du chemin. Les résultats détachés d'un champ partagé
continuent d'utiliser les provenances d'entrée. La même
résolution s'applique aux cases d'un tableau retourné ou
modifié par paramètre.

Le test sous UBSan à `-O2` exerce le retour direct et le
retour en tableau fixe via un relais. Il vérifie la mutation
de la nouvelle cible, l'accès à l'ancienne et au champ frère
ainsi que le refus d'utiliser ou de détruire le porteur
pendant le réemprunt. Un essai natif écrit le réemprunt dans
un tableau fourni par l'appelant. Un autre couvre les deux
branches d'une mise à jour conditionnelle et quatre accès
incompatibles aux cibles possibles. Une mutation qui
réutilise la cible d'entrée fait échouer le contrôle de
provenance au retour.

Les porteurs ambigus restent ouverts. Après une jonction,
la réservation couvre toutes les cibles encore possibles.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 302 tests.

## Sélection d'un porteur mutable

Un retour de fonction peut sélectionner un emprunt de structure.
Un appel suivant peut réaffecter le champ du porteur choisi.
Le C écrit uniquement dans le porteur désigné et le vérificateur
conserve les anciennes et nouvelles cibles de chaque porteur
possible.

Deux exécutions sous UBSan ont vérifié le choix du porteur.
Six destructions prématurées ont été refusées et les cinq tests
ciblés sur les champs ont réussi. La propagation de la mise à
jour à travers une fonction qui sélectionne elle-même le porteur
reste refusée. La régression élargie reste à exécuter.

## Réaffectation après sélection dans une fonction relais

Le contrat d'une fonction relais conserve les dépendances
de chacun de ses paramètres mutables pouvant être le porteur
sélectionné. Il ajoute la nouvelle cible à chaque alternative
et conserve l'ancienne tant que le choix reste incertain.
Le vérificateur suit aussi les cibles des champs de tous les
porteurs possibles pendant un emprunt retourné.

Le test sous UBSan à `-O2` exécute les deux sélections et
vérifie que seul le porteur choisi change. Il refuse six
destructions prématurées, une cible trop courte et la
destruction de la cible du second porteur pendant l'emprunt
sélectionné. Supprimer la propagation dans le résumé fait
accepter trois de ces contre-exemples.

La propagation couvre les porteurs identifiables comme
paramètres mutables du relais. Les identités locales
indirectes et l'affectation directe via un emprunt retourné
restent ouvertes.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 303 tests sur le code final.

## Affectation directe via un emprunt de structure retourné

L'affectation `selected.target = &*target` utilise la même
mise à jour de contrat qu'un appel équivalent. Si plusieurs
paramètres du relais peuvent être le porteur, chacun conserve
son ancienne cible et la nouvelle. Le C écrit uniquement
dans le porteur sélectionné.

Le test sous UBSan à `-O2` exerce les deux sélections.
La destruction de la nouvelle cible avant lecture du porteur
est refusée. Supprimer la propagation des cibles dans le
résumé fait accepter le contre-exemple de destruction.

Les porteurs locaux sélectionnés à l'intérieur d'une fonction
restent à couvrir quand leur identité ne peut pas être liée à
un paramètre.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 303 tests avant le dernier ajustement
qui relit le porteur après l'évaluation du membre droit.
Les six tests ciblés sur les champs passent avec cet ajustement.

## Sélection de porteurs locaux dans le même pool

L'analyse des contrats suit le site de création d'une structure
locale séparément de son pool. Un emprunt retourné par une
fonction de sélection conserve ces sites. Une réaffectation
met à jour les porteurs locaux possibles et conserve leurs
anciennes dépendances lorsqu'ils peuvent être distincts à
l'exécution.

Le test sous UBSan à `-O2` construit deux porteurs dans le
même pool, exécute les deux sélections et retourne le premier
porteur. Il vérifie que la cible propre au second peut être
détruite et que les deux cibles possibles du résultat restent
protégées. Supprimer la propagation locale fait échouer la
vérification du contrat de retour. Un essai natif séparé couvre
les deux branches d'une sélection entre un paramètre mutable
et un porteur local.

L'analyse reste prudente quand un site peut représenter plusieurs
allocations. Elle refuse la mutation indirecte si le porteur
local a été masqué et si sa mise à jour ne peut être suivie.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 304 tests.

## Réaffectation d'un porteur masqué

Le suivi des sites de création inclut les liaisons conservées
par les scopes pendant un masquage. Une réaffectation via un
emprunt retourné met à jour la structure d'origine, qui
redevient accessible sous son nom après le bloc.

Le test sous UBSan à `-O2` masque le nom avec un Int, exécute
les deux chemins d'une réaffectation conditionnelle et lit
la structure retournée après le bloc. Le vérificateur refuse
la destruction prématurée des deux cibles possibles. Une
mutation qui ignore les liaisons masquées refuse le cas valide.
Un essai séparé couvre le porteur transféré en paramètre,
réaffecté via un emprunt et retourné.

L'analyse garde une union conservatrice des anciennes et
nouvelles cibles lors des mises à jour indirectes de sites
locaux, même si l'exécution peut identifier un porteur unique.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 305 tests.

## Coexistence des classes de régions

Un pool de vecteurs retrouve une classe par taille de région.
Les descripteurs de classe restent stables et une classe vide
peut être recyclée pour un nouveau gabarit. Le nombre de
classes enregistrées est borné par le nombre de slots du pool.
Une classe occupée conserve son mapping et ses adresses.

Le test natif des chaînes vérifie deux classes simultanées,
le réemploi à la même adresse dans chaque classe, le recyclage
d'une classe vide pendant que l'autre contient encore une chaîne
UTF-8 et la fermeture des mappings. Il conserve le scénario de
dépassement de capacité. Une mutation qui force le choix de la
première classe fait échouer ce test. Un essai en Crust sous
UBSan exerce deux annotations imbriquées et un transfert de
vecteur, avec les sorties attendues 9 et 17.

Le runtime utilise des plages virtuelles séparées. Chaque classe
réserve jusqu'au nombre total de slots du pool, ce qui peut
augmenter l'espace virtuel réservé quand plusieurs classes sont
actives. Le placement de classes dans une plage commune reste
ouvert.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 305 tests.

## Réserve commune pour les classes de régions annotées

Les classes annotées d'un pool partagent une réserve virtuelle
de 4 Mio. Le placement cherche un intervalle depuis le haut,
respecte l'alignement des slots et garde les régions occupées
à leur adresse. Les classes vides peuvent être recyclées pour
agrandir l'espace disponible. Si le gabarit ou la capacité
disponible empêche le placement, la région dédiée conserve
exactement la limite demandée.

Le test natif vérifie les bornes des deux classes dans la
même réserve, la conservation des octets d'une chaîne pendant
le recyclage d'une autre classe, le réemploi d'un slot et le
repli dédié lorsque la classe de 1 Mio est pleine. Un essai
supplémentaire libère deux classes puis place une région de
3,5 Mio dans la réserve. Une mutation qui place chaque classe
au même sommet fait échouer l'assertion de disjonction.

La taille de 4 Mio est un choix interne du prototype. Les
valeurs non annotées continuent d'utiliser une autre plage.
Le placement commun aux régions et aux deux fronts reste
ouvert.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 305 tests.

## Réserve commune aux régions et aux deux fronts

Le runtime utilise la même réserve virtuelle de 4 Mio pour
les classes annotées et les deux fronts non annotés. Il place
les classes depuis le haut et borne les fronts à la première
classe. Tant qu'un front descendant est vivant, son bord de
départ reste réservé. Sa libération permet de recalculer le
bord à partir des classes encore présentes. Les limites des
régions dédiées restent celles de la demande.

Le test C sous UBSan à `-O0` et `-O2` remplit l'espace entre
les fronts, refuse les ajouts qui dépassent la limite et
vérifie les adresses avant et après la libération d'une
classe puis du front descendant. Une mutation qui ignore
les classes dans le calcul du bord fait échouer le test de
collision. Un essai Crust combine une région annotée
transférée et deux vecteurs non annotés. Un autre vérifie
le repli contigu d'une String quand la réserve est pleine.

La réserve commune et la réserve de repli des valeurs non
annotées ont chacune une capacité interne de 4 Mio. Les
classes sont gérées par pool de vecteurs. La réservation de
slots par le compilateur dans les blocs ancêtres reste un
chantier distinct.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 306 tests.

## Réservation anticipée d'un slot de data stack

Le compilateur repère un Int construit sur une data stack
visible depuis le receveur et exporté par une chaîne de blocs
rectilignes. Il réserve le slot avant les temporaires de
la même stack si la capacité permet aussi leurs constructions.
Le code écrit la valeur et lui donne son nom à l'instruction
de construction. Chaque frontière de transfert reste vérifiée.

Le test sous UBSan à `-O2` couvre deux remontées et deux
temporaires. Il vérifie l'ordre des effets, la position
du slot réservé, la stabilité de l'adresse et la récupération
des temporaires avant la destruction du résultat. La mutation
qui désactive la réservation fait échouer le contrôle de
placement. Un essai avec une stack d'un slot confirme que
le diagnostic de capacité arrive après les deux impressions
prévues, sans réservation qui consommerait le slot du temporaire.

Le plan couvre les constructions Int explicites sur une
data stack. Les branches, boucles, autres types et placements
dont le chemin ne peut être établi suivent le placement existant.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 307 tests.

## Réservation anticipée à travers des branches

Lorsque les deux branches produisent un Int sur la même
data stack et que la condition ne touche pas à cette source,
le compilateur peut réserver un slot commun. Il vérifie la
capacité contre le maximum des temporaires des deux chemins.
Sinon, il peut réserver dans le seul bras pris, après
l'évaluation de la condition.

Le test sous UBSan à `-O2` exécute les deux branches et vérifie
que le C contient un seul appel de réservation et deux
constructions alternatives. L'initialiseur du bras pris
s'exécute après ses temporaires. L'adresse du résultat reste
stable jusqu'au receveur. Un essai à deux slots confirme
le succès du bras court et l'échec du bras long après les
effets attendus. Un autre essai combine une condition à
effet et deux sources distinctes avec réservation dans
le bras exécuté.

Les constructions dans les boucles et les autres types
restent à couvrir.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 308 tests.

## Réservation anticipée sur une sortie de boucle

Pour un `break <- valeur` qui termine un bloc rectiligne,
le compilateur peut réserver le slot du résultat au début
du suffixe qui mène à cette sortie. Le point de réservation
se trouve après les instructions qui peuvent reprendre la
boucle. L'initialiseur reste à son instruction de construction.

Le test sous UBSan à `-O2` exerce deux reprises suivies
d'une sortie. Les temporaires des reprises retrouvent la
même adresse. Le slot exporté précède le dernier temporaire
et garde son adresse après le break. Le test contrôle aussi
l'ordre de destruction. Une mutation qui déplace la
réservation avant le continue fait échouer ce contrôle.
Un essai natif exerce également la sortie dans un bras else.

La réservation couvre un suffixe analysable et les
constructions Int sur data stack. Les chemins complexes
dont les besoins ne sont pas établis gardent le placement
existant.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 309 tests.

## Réservation des descripteurs de valeurs grandissantes

Le compilateur peut réserver le slot du descripteur de
`String` ou de `Vector` avant les temporaires du même
pool. Le runtime ouvre le stockage grandissant à la
construction et applique l'annotation de ce bloc. Le
descripteur garde son adresse pendant le transfert.
La réservation est également disponible pour un Int
dans un pool typé.

Le test sous UBSan à `-O2` couvre String, Vector<Int> et
Vector<A<Int>>. Il vérifie le placement du descripteur,
son adresse après transfert et l'usage de la collection.
Avec un seul slot, la construction du temporaire reste
possible avant le diagnostic de capacité. Le vecteur de
handles nettoie son élément et le pool d'origine réutilise
son slot. Supprimer la destruction des handles du chemin
réservé fait échouer le test.

Le plan réserve le descripteur. Le placement anticipé du
stockage grandissant et les structures et enums sur leurs
pools spécialisés restent ouverts.

La première régression a compté un appel interne du runtime
dans le test qui vérifie les deux constructeurs d'un if.
Après restriction du comptage au main généré, la régression
des fondamentaux, tableaux fixes, effets et croissance a
réussi avec 310 tests.

## Réservation de slots de structures et d'enums

Le plan tient compte de la source et du bras. Il réserve
dans la plage spécialisée du bras et ne compte comme
temporaires concurrents que les allocations de cette
même plage. Les initialiseurs et les écritures de champs
s'exécutent à l'instruction de construction. Le runtime
vérifie que la réservation provient de la source attendue.

Les tests sous UBSan à `-O2` vérifient le placement du
slot, l'adresse stable après transfert, l'ordre des
initialiseurs et la protection d'un champ emprunté.
Avec un slot par bras, la saturation du bras A laisse
le bras B disponible et le diagnostic suit l'initialiseur
de la construction qui échoue. Une mutation qui réserve
dans B pour construire A déclenche le contrôle de source.

Le plan reste limité aux chemins dont la source et les
effets d'initialisation sont établis. Le stockage grandissant
reste ouvert à la construction de son descripteur.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 312 tests. Les cinq tests ciblés
ont été réexécutés avec le contrôle final du slot. Un essai
natif supplémentaire exerce les deux branches d'un if qui
réservent dans des bras différents.

## Réservation anticipée d'une région annotée

Quand les chemins analysés demandent la même limite,
le code peut réserver une région en plus du descripteur.
La classe doit déjà contenir une région vivante et laisser
assez de slots pour le résultat et les temporaires. Cette
vérification n'ouvre aucun mapping. En cas de refus, la
construction suit le placement ordinaire.

Le test C sous UBSan à `-O0` et `-O2` vérifie le refus
d'une autre taille et d'un nombre excessif de temporaires.
Il réserve ensuite une région et vérifie son adresse
après construction et après ajout de texte. Supprimer le
contrôle de capacité fait échouer le test. Un test Crust
exerce le code généré dans une classe de 1 Mio déjà active.

Les classes à créer et les fronts non annotés continuent
d'être ouverts à la construction. Les branches de tailles
différentes peuvent réserver le descripteur commun, mais
ouvrent leur région au moment de construire.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 313 tests.

## Réservation anticipée d'une nouvelle classe de régions

Si la réserve commune est déjà ouverte, le compilateur
peut autoriser la création anticipée d'une classe quand
tous les temporaires du même pool ont le gabarit du
résultat. Le runtime vérifie qu'il reste des slots pour
le résultat et les temporaires. Cette préparation peut
recycler une classe vide sans ouvrir de mapping.

Le test C sous UBSan à `-O0` et `-O2` ouvre une deuxième
classe, réserve le slot du résultat avant celui du
temporaire et vérifie la conservation de l'adresse
après la construction. La classe déjà occupée reste
utilisable. Une mutation qui ignore l'autorisation de
créer la classe fait échouer le test. Un essai Crust
recycle une classe de 2 Mio pour réserver à 1 Mio.

Lorsque la réserve est encore fermée ou que les
temporaires ont des tailles différentes, la création
d'une classe reste à l'instruction de construction.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 313 tests.

## Réservation anticipée à froid d'une région

Le runtime peut préparer la réserve commune et la table des
classes avant la première construction si tous les temporaires
du même pool ont le gabarit du résultat. Les ouvertures
provisoires sont publiées ensemble. Un échec libère les
plages provisoires et laisse la construction suivre son
chemin ordinaire.

Le test C sous UBSan à `-O0` et `-O2` couvre le succès à
froid et injecte un échec à chacune des deux réservations
virtuelles. Il vérifie la libération de la première plage
si la seconde échoue, puis la réussite du placement
ordinaire. Supprimer cette libération fait échouer le test.
Un essai sur du C généré depuis Crust impose un échec
persistant et vérifie que l'impression prévue précède le
diagnostic de la construction.

Les valeurs sans annotation continuent d'ouvrir leur
front à la construction. Les chemins dont les gabarits
diffèrent peuvent réserver dans une classe déjà active,
sans préparer une nouvelle classe.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 314 tests.

## Réservation anticipée d'un front descendant

Un vecteur non annoté qui suit un seul temporaire du même
pool peut réserver le front descendant. Le runtime exige
que les deux fronts soient libres et laisse de la place
au temporaire sur le front montant. La construction
reprend le descripteur et le front réservés. En cas
d'échec, le placement ordinaire s'applique.

Le test C sous UBSan à `-O0` et `-O2` vérifie la direction,
l'identité du front et l'ordre logique des éléments après
croissance. Il teste aussi le refus d'une réservation
anticipée lorsque l'espace est insuffisant et le repli
dédié quand le temporaire consomme le dernier espace.
Une mutation qui réserve le front montant fait échouer
le test. Un test Crust vérifie l'émission du plan, le
transfert et deux ajouts.

Les Strings non annotées exigent une croissance contiguë
vers les adresses croissantes. Elles conservent le
placement ordinaire. Les chemins à plusieurs temporaires
et les fronts déjà occupés conservent aussi ce placement.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 315 tests.

## Réservation anticipée d'une plage dédiée

Sur un chemin non annoté dont les temporaires occupent les
fronts nécessaires, le compilateur peut réserver une plage
dédiée avant la construction du résultat. Un temporaire
String occupe le front montant. Deux temporaires Vector
occupent les deux fronts disponibles. La tentative de
réservation utilise le chemin non fatal et la construction
reprend le placement ordinaire en cas d'échec.

Le test C sous UBSan à `-O0` et `-O2` couvre les deux
modes. Il vérifie que la réservation laisse les fronts
communs aux temporaires et que les ajouts conservent
l'adresse de la plage dédiée. Une mutation qui utilise
la réserve commune pour cette préparation fait échouer
le test. Deux essais Crust vérifient l'émission du plan
et le contenu d'une String et d'un Vector transférés.

Les chemins qui alternent des nombres de temporaires
demandant des placements différents conservent leur
placement ordinaire. Un seul temporaire Vector avec un
front déjà occupé conserve aussi ce chemin.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 316 tests.

## Identité du handle extrait à travers un contrat de résultat

VE3 couvre le retour d’un handle injecté puis inséré dans
un vecteur local. L’analyse de résultat suit les candidats
insérés. Le vérificateur concret conserve les identités des
éléments compatibles avec les sources de la case extraite.
Le C restitue le pointeur du handle extrait.

Trois programmes natifs sous Clang C11 à `-O2` avec
UBSan fatal couvrent `remove`, le bras `Some` de `pop`
et le bras `Ok` de `replace`. Les assertions comparent
l’adresse avant l’appel, l’adresse de retour et l’adresse
réutilisée après `drop`. Le cas `replace` vérifie aussi
que le slot du handle entrant est récupéré au nettoyage
du vecteur. Six variantes sont refusées à la vérification,
trois pour un pool local et trois pour un reset avant le
dernier usage du résultat. Deux paires de sondes supplémentaires
comparent le reset d’un pool distinct au reset du pool du
handle, directement et via un relais.

Une mutation en mémoire qui perd l’identité lors de
`remove` est détectée par la vérification du contrat
avec le diagnostic « allocation neuve absente du résumé
de résultat ». Les assertions d’adresse constituent
l’oracle de ces cas natifs. Aucun nouveau modèle de
référence ni générateur n’a été exécuté pour cette extension.

Le contrat prend l’union des identités insérées dans un
vecteur local. Cela peut refuser l’extraction d’une case
connue si une autre case contient une allocation locale,
ou si la mutation passe par un emprunt. L’extraction
depuis un vecteur injecté et le transport de ses résultats
non Copy restent ouverts.

Contre-exemple reproductible de cette limite. Dans une
fonction recevant `a: -> A<Int>`, pousser `a` dans la
case 0 puis `local.new(23)` dans la case 1 et retourner
`<- v.remove(0)`. Les indices 0 et 1 déclenchent tous
deux le diagnostic de pool local. Seul le refus de
l’indice 1 est attendu par VE3.

La régression des fondamentaux, tableaux fixes, effets et
croissance a réussi avec 316 tests. Le nouveau test
d’extraction a été exécuté séparément et a réussi ses
trois variantes natives et six refus avec Clang 20.1.3.

## Identité par case dans les résultats d’extraction

Le résumé de résultat et le vérificateur concret distinguent
les cases des vecteurs dont la longueur est connue. La
suppression décale les identités avec les éléments. Aux
jonctions de longueurs différentes, le résumé conserve
l’union des candidats. Pour un indice dynamique sur une
longueur connue, chaque case restante peut correspondre
à sa position précédente ou à la suivante. Le match de
`replace` ou `try_push` ne publie l’entrée que dans le
bras de succès.

Sous Clang C11 à `-O2` avec UBSan fatal, les deux variantes
de `remove(0)` restituent la valeur et l’adresse du premier
handle quand la case 1 appartient au même pool ou à un
pool local. Le retour de `remove(1)` reste refusé dans
le second cas. Une mutation qui ignore l’indice lors du
suivi concret échoue sur le cas de deux handles du même
pool, avec « identité entrante absente ». Aucun nouveau
modèle indépendant ni essai généré pour cette extension.

Les résumés n’expriment toujours pas les éléments d’un
vecteur injecté. Le suivi de résultat invalide ses
connaissances sur les cases lorsqu’un alias peut avoir
remplacé un handle. Ces deux cas restent ouverts.

Le test historique `test_drop_requires_move` attendait
l’ancien diagnostic générique du parseur. Le test garde
le programme invalide et vérifie maintenant le diagnostic
spécifique « drop exige un transfert -> explicite ». Ce
test réussit en exécution isolée.

Les sondes du vérificateur couvrent aussi une case 0
remplie par deux branches avec deux handles injectés,
puis l’extraction de cette case et, dans une variante,
la restitution par `pop` du handle décalé. Les deux
sondes sont acceptées.

La régression du prototype, des fondamentaux, des effets,
des résultats et des appels modulaires a réussi avec 419 tests.

## Remplacement par emprunt de case et relais du vecteur

Le résumé de résultat rattache un emprunt direct de case à
la provenance du vecteur local et à son indice littéral
lorsqu’il est connu. L’écriture par cet emprunt remplace
la provenance de la case si le porteur est déterminé.
Une cible ambiguë conserve l’union des candidats
compatibles. Si l’analyse perd la cible de l’emprunt,
elle invalide les informations de cases potentiellement
touchées. Un relais qui retourne un de ses paramètres
vecteurs transmet les informations de cases à l’appelant.

Deux programmes natifs sous Clang C11 à `-O2` avec
UBSan fatal combinent remplacement depuis un bloc enfant,
relais du vecteur par appel, extraction et retour du handle.
Le premier restitue le handle injecté qui remplace une
allocation locale dans la case 0. Le second restitue le
handle de la case 1 après remplacement de la case 0.
Les deux vérifient valeur, adresse, destruction unique
du handle injecté et réemploi de son slot. Les variantes
qui retournent une allocation locale sont refusées.
Une mutation temporaire qui ignore l’écriture de case
fait échouer le premier cas. Aucun nouveau modèle ni
générateur exécuté pour cette extension.

Un emprunt de case renvoyé par un autre appel ne transmet
pas encore son chemin de case à cette analyse. La mutation
structurelle d’un vecteur injecté et le transport des
résultats non Copy restent ouverts.

La suite globale de l’état précédant le suivi par case a
exécuté 1 142 tests. Son seul échec était le libellé
historique de `test_drop_requires_move`. Ce test réussit
dans la régression de 419 tests après correction du
libellé attendu. La sélection de 28 tests `handle_vector`
a réussi avant l’ajout du relais au test de remplacement.
Les deux variantes avec relais ont ensuite réussi en
exécution isolée et la mutation a été redétectée.

Contre-exemple encore ouvert. Une fonction recevant
`v: -> Vector<A<Int>>` et retournant le résultat de
`v.remove(0)` est refusée avec « la source ‘élément
de vecteur’ ne survit pas à ce bloc », même quand le
vecteur de l’appelant contient un seul handle dont le
pool reste vivant. Le résumé de fonction devra nommer
un élément du paramètre et résoudre sa provenance à
partir des cases du vecteur à l’appel.

## Indice d’un emprunt de case renvoyé par appel

Pour un retour d’emprunt qui désigne une case d’un
paramètre vecteur, le contrat conserve le paramètre
et l’indice connu lorsque tous les chemins de retour
concordent. Les appels successifs propagent cette
information. Le vérificateur concret rattache le prêt
au chemin correspondant et contrôle l’indice annoncé
sur les retours de la fonction. Un indice dynamique
ne donne aucune preuve de séparation entre cases.

Le test de remplacement a été exécuté sous Clang C11
à `-O2` avec UBSan fatal pour quatre variantes, deux
par emprunt direct et deux via deux appels. Il vérifie
adresse, valeur, destruction unique et réemploi du slot.
Quatre variantes qui retournent un handle du pool local
sont refusées. Une mutation qui annonce la case 1
pour un corps renvoyant la case 0 est rejetée par le
contrôle du contrat. Aucun nouveau modèle indépendant
ni programme généré n’a été exécuté pour cette extension.

La régression de 287 tests de l’état précédent a réussi.
Les prêts à cibles multiples et le retour d’un élément
extrait d’un vecteur reçu par transfert restent ouverts.

La sélection de 28 tests `handle_vector` passe sur cet
état, y compris les quatre variantes de remplacement.

## Source d’un handle extrait dans les contraintes d’appel

Le cas `target.drop(-> item)` après extraction d’un
vecteur local échouait en vérification symbolique même
quand le pool d’origine était fourni. L’analyse des
contraintes transporte maintenant les actifs par case
lors de l’insertion et de l’extraction. Une extraction
transmet les contraintes de la case, et le bras succès
publie l’élément entrant pour les échanges. Les actifs
qui restent stockés gardent leur historique aux sorties
de bloc. Les résultats de relais d’un vecteur
transmettent les informations des vecteurs d’entrée.

Le programme de régression retire la case 1 d’un vecteur
contenant des handles de deux pools et appelle la
fonction de libération via un relais. Sous Clang C11 à
`-O2` et UBSan fatal, le pool correct permet une
destruction unique du handle et le réemploi de son
adresse. Le mauvais pool est refusé par la contrainte
d’égalité. Une mutation qui efface les actifs du handle
extrait fait rejeter le programme valide en vérification
symbolique. Aucun nouveau modèle de référence ni cas
généré n’a été exécuté pour cette extension.

Un remplacement par alias invalide le suivi des cases
dans l’analyse des contraintes, qui n’a pas encore la
provenance de l’emprunt utilisée par le résumé de résultat.
La provenance symbolique des éléments d’un vecteur
injecté reste à ajouter.

La régression de 267 tests sur les contrats de prêts
de case a réussi avant cette extension. La suite globale
de l’état antérieur au suivi des prêts de case a réussi
avec 1 143 tests.

La sélection de 29 tests `handle_vector` passe. Quatre
sondes du vérificateur confirment aussi que `pop` impose
le pool du dernier élément et que le bras succès de
`replace` impose celui de l’ancien élément. Chacune
des deux opérations accepte le bon pool et rejette
l’autre par la contrainte d’égalité.

## Contrainte de pool après remplacement par emprunt

L’analyse des contraintes rattache les emprunts de cases
à l’identité du vecteur et à l’indice transmis par le
contrat d’appel. Un remplacement certain met à jour la
case. Une cible incertaine conserve les candidats
compatibles ou perd l’information si le porteur ne peut
pas être retrouvé. L’analyse de résultat et celle des
contraintes partagent la mise à jour d’une case connue
ou incertaine.

Le test `test_handle_vector_extraction_infers_drop_pool_through_a_call`
compare l’insertion en case 1 au remplacement de la
case 0 via un emprunt direct ou retourné par une
fonction. Les trois variantes réussissent sous Clang C11
à `-O2` avec UBSan fatal. Elles vérifient le réemploi
du slot et la destruction unique du handle extrait.
Les trois variantes utilisant l’ancien pool échouent
sur la contrainte d’égalité. Une mutation en mémoire
qui ignore la mise à jour de la case fait rejeter les
deux variantes par emprunt. Aucun nouveau modèle
indépendant ni programme généré pour cette extension.

Les 315 tests de la régression de l’état précédent
passent. La sélection de 29 tests `handle_vector`
passe avec les variantes par emprunt. Les deux tests
de contrat ciblés passent après la mutualisation de
la mise à jour. Les emprunts à cibles multiples et
l’extraction depuis un vecteur injecté restent ouverts.

Les 29 tests `handle_vector` ont aussi été rejoués
avec succès après la mutualisation.

## Retour d’un élément d’un vecteur reçu par transfert

Le contre-exemple de la section précédente compile
désormais avec un vecteur reçu comme paramètre mutable
par transfert. Le résumé peut désigner un élément de ce
paramètre. La vérification symbolique donne à ses cases
une source distincte de celle du vecteur. À l’appel,
le contrat résout les sources et les identités d’éléments
sur le vecteur réel. Le code C déplace le pointeur de
la case et le nettoyage du vecteur traite ses autres
éléments. Le contrat transmet aussi les obligations de
source d’origine pour `drop` et de séparation pour
`reset`.

Deux variantes natives sous Clang C11 à `-O2` avec
UBSan fatal couvrent `remove(0)` et `Some` de `pop`
via un relais, sur un vecteur à deux pools d’éléments.
Elles vérifient la valeur, l’adresse de l’élément
retourné, la destruction unique de chaque handle et
la réutilisation de leurs deux slots. Dans chaque
variante, un reset visant un pool du vecteur dans
la fonction est refusé, de même qu’un reset du pool
du résultat avant son dernier usage chez l’appelant.
Deux sondes d’égalité de source acceptent le pool
correct pour `source.drop` sur un vecteur singleton
et refusent l’autre. Une mutation du contrat qui efface
les identités d’entrée est détectée en vérification
symbolique. Aucun nouveau modèle indépendant ou
générateur exécuté pour cette extension.

Le contrat approxime une extraction par l’ensemble
des cases initiales du paramètre. Cela peut refuser
une opération sur un autre pool du même vecteur
même si l’indice choisi est connu. Les autres
mutations structurelles du vecteur injecté et
l’extraction par emprunt restent à traiter.

La régression de 270 tests de l’état précédent passe.
Les 30 tests `handle_vector` passent avec les nouveaux
cas de transfert. La régression élargie de ce cycle est
en cours.

## Indice d’origine dans les contrats d’extraction

Le résultat de `remove(i)` sur un vecteur reçu par
transfert peut maintenant désigner son indice littéral
dans le vecteur initial. L’analyse remonte les décalages
dus aux suppressions littérales précédentes et transmet
l’indice à travers un relais. Une suppression dynamique
ou une jonction d’historiques différents revient à
l’ensemble des éléments. Les appels dont les cases sont
connues résolvent les sources et les identités d’après
l’indice, y compris dans le vérificateur modulaire.

Les essais natifs sous Clang C11 à `-O2` avec UBSan
fatal restituent la première case ou la case qui se
décale après une première suppression. Dans chaque
cas, ils réinitialisent le pool de l’autre handle avant
le dernier usage du résultat et vérifient adresse,
destruction unique et réemploi des deux slots. `pop`
reste couvert avec la provenance de l’ensemble des
éléments. Une mutation qui annonce le mauvais indice
est rejetée lors de la compilation avec deux handles
du même pool. La vérification symbolique d’un corps
sans appel concret continue d’utiliser un élément
symbolique commun et ne distingue pas ces indices.
Aucun nouveau modèle indépendant ni essai généré
pour cette extension.

Un contre-exemple a montré qu’une fonction pouvait
restituer le vecteur après une suppression alors que
son contrat annonçait encore les cases d’entrée.
Le vérificateur refuse cette restitution tant que
le contrat ne décrit pas les transformations de cases.
Les contraintes d’égalité ou de séparation internes
à la fonction continuent également de considérer tous
les pools possibles des éléments injectés.

La régression de 316 tests de l’état précédent a réussi.
Les 30 tests `handle_vector` passent avec l’indice
d’origine. La régression élargie de ce cycle est en
cours.

## Dernière case d’un vecteur reçu par transfert

Le contrat de `pop` peut maintenant désigner la dernière
case parmi celles qui restent. Il mémorise les indices
d’origine retirés par des `remove` littéraux et le nombre
de retraits en fin de vecteur. Les appels avec des cases
connues résolvent cette sélection. Si un retrait dynamique
ou une jonction rend l’historique incertain, le contrat
conserve l’ensemble des cases possibles.

Cinq variantes natives sous Clang C11 à `-O2` avec UBSan
fatal couvrent les deux opérations, dont `pop` seul,
`pop` après retrait de la dernière case et deux `pop`
successifs. Après le retour par relais, chaque variante
réinitialise le pool de l’autre case avant le dernier
usage du résultat, puis compare les adresses et vérifie
la destruction unique des deux handles. Une mutation
qui oublie le premier retrait en fin de vecteur fait
rejeter la variante de deux `pop` à cause du reset
du pool disjoint.

Une liste de référence indépendante a été comparée à
l’historique symbolique sur 10 158 états. Les suites
exhaustives de suppressions valides sur les longueurs
0 à 6 mélangent suppressions littérales et retraits en
fin de liste. À chaque état, les indices encore valides
et la dernière case concordent. Cette comparaison
porte sur le calcul d’indice. Le code C a été exercé
par les variantes natives décrites ci-dessus.

Les 316 tests de la régression de l’état précédent et
les 30 tests ciblés de cet état réussissent. La régression
élargie de cet état est en cours. Les contraintes de pool
internes à une fonction restent agrégées pour les
éléments injectés. La restitution d’un vecteur après
mutation reste ouverte.

## Une perte de précision ne masque plus une extraction

Un appel recevant un `&mut A<Int>` peut effacer
l’inventaire des cases dans l’analyse de résultat. Avant
la correction, une extraction dans cet état omettait
également de marquer le vecteur comme modifié. Les deux
points d’entrée `verify_program` et `compile_source`
acceptaient alors de restituer le vecteur avec son
contrat de cases initial. Dans le contre-exemple, la
suppression décale un handle du pool `q` vers la case
0. Chez l’appelant, l’ancienne provenance de cette case
autorise à tort un reset de `q` avant la lecture du
handle extrait.

L’extraction marque désormais la modification même
lorsque l’inventaire est inconnu. Les deux points
d’entrée refusent le contre-exemple à l’inférence
du contrat. Une mutation temporaire qui restaure
l’ancien comportement fait échouer les deux
assertions de rejet. Le C du contre-exemple a été
généré avant correction et n’a pas été exécuté.
Les variantes natives de retour du handle extrait
continuent à passer sous UBSan. Aucun nouveau modèle
indépendant ni essai généré pour cette correction.

Les 316 tests de la régression précédente passent.
La régression avec le nouveau contre-exemple est
en cours. Le contrat des vecteurs modifiés reste
à implémenter pour pouvoir accepter leur restitution.

La sélection de 48 tests liés aux vecteurs passe sur cet état.

## Restitution du vecteur après suppression déterminée

Le contrat d’un vecteur retourné décrit les cases
retirées du paramètre d’entrée lorsque leur historique
est déterminé. Les relais composent les retraits
littéraux et les retraits de fin de vecteur. Le
vérificateur applique cette transformation aux
sources et aux identités chez l’appelant. Pendant
la génération C, il compare les cases connues du
contrat aux cases constatées sur chaque retour.

Deux variantes natives sous Clang C11 à `-O2` avec
UBSan fatal couvrent la restitution par un relais
après `remove(0)` ou `pop`. Le reset du pool du
handle retiré est accepté. Le reset du pool encore
représenté dans le vecteur est refusé. Les essais
natifs vérifient l’adresse du handle restant, la
destruction unique des deux handles et le réemploi
des deux slots. Le contre-exemple de la section
précédente reste refusé. Une mutation qui annonce
la suppression de la mauvaise case dans un vecteur
de deux handles du même pool est détectée en
comparant les identités au contrat lors de la
génération C.

Une liste de référence indépendante a été comparée
à 7 786 compositions de suppressions. L’essai
énumère des séquences valides de `remove` et
`pop` sur des vecteurs de longueur 0 à 5 et
compare les cases restantes à chaque découpage
de la séquence entre deux historiques.

Les 317 tests de la régression précédente passent.
Les historiques incertains restent refusés à la
restitution. Les contraintes internes par indice
et les mutations autres que les suppressions
restent ouvertes pour les vecteurs injectés.
Les 49 tests liés aux vecteurs passent sur cet état.
La régression élargie est en cours.

## Restitution après suppression à indice incertain

Une suppression dynamique ou une jonction entre
historiques différents peut maintenant produire un
vecteur restituable. Son contrat abandonne les
positions précises et conserve l’ensemble des pools
et identités possibles. Le cas où un effet opaque
fait perdre tout l’inventaire des éléments reste
refusé.

Quatre variantes natives sous Clang C11 à `-O2`
avec UBSan fatal couvrent une suppression dynamique
et une suppression par deux branches. Pour chaque
forme, les deux indices retirent chacun un handle
différent, puis le programme extrait le survivant,
vérifie sa valeur et son adresse, et confirme la
destruction unique des deux handles. Les quatre
variantes qui réinitialisent le pool du survivant
avant son dernier usage sont refusées. Une mutation
qui fait passer le résultat pour un vecteur inchangé
réintroduit l’acceptation du reset dangereux et est
détectée. Aucun nouveau modèle indépendant n’a été
exécuté pour cette extension.

La régression de 318 tests de l’état précédent
réussit. Les contraintes internes par indice
et les autres mutations d’un vecteur injecté
restent ouvertes. Avec une provenance agrégée,
un reset du pool de l’élément retiré peut rester
refusé jusqu’à la fin du dernier usage.
La sélection de 50 tests liés aux vecteurs passe.
Les variantes par branche ont également été rejouées
dans le test ciblé. La régression élargie est en cours.

## Écriture dans un vecteur reçu puis consommé

La vérification autorise les écritures dans un
vecteur de handles reçu par transfert. Le vecteur
appartient alors au scope de la fonction, qui peut
le consommer ou le laisser se nettoyer à sa sortie.
L’insertion conserve la vérification de durée de
vie du pool de l’élément. Le contrat refuse encore
la restitution du vecteur après une écriture qui
change son contenu. Les écritures dans un vecteur
reçu par emprunt restent ouvertes.

Quatre variantes natives sous Clang C11 à `-O2`
avec UBSan fatal couvrent `push`, `try_push`,
`replace` et le remplacement à travers un emprunt
mutable de case. Les quatre vérifient la destruction
unique des deux handles et le réemploi de leurs
slots. Le reset du pool du handle entrant est
refusé, ainsi que la restitution du vecteur
écrit. Une insertion depuis un pool déclaré dans
un bloc enfant est refusée. Une mutation qui
supprime la vérification de destination accepte
cette dernière variante et est détectée. Aucun
nouveau modèle indépendant ni essai généré pour
cette extension.

Les 319 tests de la régression précédente
réussissent. La régression de cet état est en cours.
Les 51 tests liés aux vecteurs passent sur cet état.

## Restitution du vecteur après insertion d’un handle reçu

Le contrat décrit désormais les handles reçus en
paramètres qui peuvent se retrouver dans le vecteur
restitué. Il combine leurs pools et identités avec
ceux des éléments d’entrée encore possibles. Cette
information traverse les appels relais. Après une
écriture, l’ordre des cases est approximé par
l’ensemble des éléments possibles. Le vérificateur
du corps compare les identités constatées à celles
du contrat, en plus des pools.

Quatre variantes natives sous Clang C11 à `-O2`
avec UBSan fatal couvrent `push`, `try_push`,
`replace` et l’écriture via un emprunt de case.
Après le relais, chaque variante extrait le handle
inséré et vérifie son adresse, sa valeur, la
destruction unique des deux handles et le réemploi
du slot inséré. Le reset de son pool est refusé
aussi bien pendant son stockage qu’après extraction
avant son dernier usage. Le retour d’une allocation
créée dans un pool local à la fonction est refusé.
Une mutation qui omet le paramètre inséré fait
rejeter les quatre cas natifs au contrôle du contrat.
Aucun nouveau modèle indépendant ni essai généré
n’a été exécuté pour cette extension.

Les 320 tests de la régression précédente passent.
La restitution après insertion d’une allocation
créée dans un pool injecté, les positions précises
après écriture et les écritures dans un vecteur reçu
par emprunt restent ouvertes.
Les 52 tests liés aux vecteurs passent sur cet état.
La régression élargie est en cours.

## Restitution avec un handle neuf issu d’un pool injecté

Le contrat du vecteur retourné décrit désormais les
pools reçus en paramètres qui peuvent fournir un
handle neuf. Le relais substitue les pools effectifs.
La vérification modulaire représente une identité
neuve possible par pool ajouté. Pendant la génération
C, la vérification distingue les identités entrantes
des identités nouvellement créées, contrôle les pools
annoncés et conserve les identités produites. Un pool
local à la fonction reste exclu du contrat de retour.

Deux variantes natives sous Clang C11 à `-O2` avec
UBSan fatal couvrent l’ajout et le remplacement par
emprunt de case, puis le retour par relais. Elles
vérifient l’adresse, la valeur, la destruction unique
du handle créé et le réemploi du slot. Les quatre
variantes qui réinitialisent son pool pendant le
stockage ou avant le dernier usage après extraction
sont refusées. Une mutation qui omet le pool neuf
fait rejeter les deux cas valides. Aucun nouveau modèle
indépendant ni essai généré pour cette extension.

Les 321 tests de la régression précédente passent.
Les positions après écriture restent approximées.
La mutation d’un vecteur reçu par emprunt reste
ouverte.

La première exécution ciblée de cette extension a
signalé quatre erreurs de fusion de métadonnées sur
des vecteurs rendus inchangés. La fusion d’ensembles
s’applique désormais seulement aux contrats qui
annoncent des ajouts. Les suites de validation ont
été relancées sur la correction.
La sélection corrigée de 53 tests liés aux vecteurs
réussit. La régression élargie corrigée est en cours.

## Retour d’un vecteur neuf construit dans un pool injecté

Les signatures acceptent `Pool<Vector<A<Int>>>` en
emprunt. Un vecteur construit dans ce pool peut être
restitué avec ses handles. Le contrat transporte les
paramètres qui fournissent des handles et les pools
injectés qui fournissent des allocations neuves. Le
relais préserve également la variante de construction
du vecteur. Les pools locaux à la fonction restent
interdits dans ce résultat.

Le cas natif sous Clang C11 à `-O2` avec UBSan
fatal construit un vecteur avec un handle reçu par
transfert et un handle neuf issu d’un second pool.
Après un relais, il extrait les deux handles et
contrôle leur valeur, leur adresse, leur destruction
unique et le réemploi de leurs slots. Le reset
est refusé pour chacun des deux pools pendant
le stockage, et pour le pool du second handle
avant son dernier usage après extraction. Le retour
avec un handle issu d’un pool local est refusé.
Une mutation qui efface les deux sources d’éléments
du contrat de construction est détectée. Aucun
nouveau modèle indépendant ni essai généré pour
cette extension.

La régression de 322 tests de l’état précédent passe.
Les positions exactes des cases et le déplacement
d’éléments entre vecteurs injectés restent ouverts.
Les 54 tests liés aux vecteurs passent. Les tests
de construction et de suppression déterminée ont
également été rejoués après clarification du code
de calcul des métadonnées. La régression élargie
est en cours.

## Retour d’un vecteur contenant un handle d’un vecteur donneur

Le contrat peut désigner un élément extrait d’un autre
vecteur reçu par transfert. Il conserve son sélecteur
d’origine, le compose à travers les relais et le résout
sur les cases connues du donneur chez l’appelant. Le
vecteur de destination conserve les identités et les
pools possibles de ses propres éléments et de ceux
qu’il a reçus. La position du handle dans le vecteur
de destination reste approximée.

Deux variantes natives sous Clang C11 à `-O2` avec
UBSan fatal couvrent le transfert de la première case
par `remove` et de la dernière par `pop`. Elles
contrôlent l’adresse et la valeur du handle déplacé,
la destruction unique des deux handles du donneur
et le réemploi de leurs slots. Le reset du pool
du handle conservé est refusé avant son dernier
usage. Celui du handle détruit lors du nettoyage
du donneur est accepté. Une mutation qui efface
le donneur du contrat est détectée dans les deux
variantes. Aucun nouveau modèle indépendant ni
essai généré n’a été exécuté pour cette extension.

La régression de 323 tests de l’état précédent et
les 55 tests liés aux vecteurs de cet état passent.
La régression élargie de cet état est en cours.

## Cases connues d’un vecteur neuf restitué

Le contrat conserve désormais la provenance de chaque
case d’un vecteur neuf quand son inventaire est connu.
Les relais résolvent chaque case à partir des paramètres,
des éléments d’un donneur ou des pools injectés. Le mode
modulaire représente les allocations neuves dans les cases
correspondantes. Pendant la génération C, le vérificateur
contrôle les identités et les sources annoncées pour les
retours dont l’ordre est connu.

Le test de construction sous Clang C11 à `-O2` et
UBSan fatal extrait deux handles de pools distincts.
Il détruit le premier, réinitialise son pool, puis
lit le second. Les adresses, les destructions uniques
et le réemploi des deux slots sont vérifiés. Le reset
du pool du second handle avant son dernier usage
reste refusé. Une mutation qui inverse l’ordre des
cases annoncées est détectée pendant la génération C.
Aucun nouveau modèle indépendant ni essai généré
n’a été exécuté pour cette extension.

L’écriture dans un vecteur reçu continue de publier
un ensemble de provenances possibles. La précision
par case après ces écritures et la mutation d’un
vecteur reçu par emprunt restent ouvertes.
Les 55 tests liés aux vecteurs passent sur cet état.
La régression élargie de cet état est en cours.
La régression de 324 tests de l’état précédent réussit.

## Cases ajoutées en fin d’un vecteur reçu par transfert

Un contrat peut conserver les cases du vecteur d’entrée
et décrire les cases ajoutées en fin par des `push`
déterminés. Le relais compose l’historique et résout les
pools et identités du suffixe. Quand les cases d’entrée
sont connues, le résultat garde leurs positions ainsi que
celles du suffixe. Lorsque l’historique des ajouts est
perdu, le contrat conserve l’ensemble des provenances.

Le cas natif sous Clang C11 à `-O2` avec UBSan fatal
ajoute un handle issu d’un autre pool, restitue le vecteur
par relais et extrait le handle ajouté. Après destruction
du vecteur, le reset du pool des anciennes cases est
autorisé avant la lecture du handle extrait. Son adresse
et son réemploi restent vérifiés. Le reset de son propre
pool reste refusé. Une mutation qui efface les positions
du suffixe est détectée par le refus à tort du reset
du pool disjoint. Aucun nouveau modèle indépendant ni
essai généré n’a été exécuté pour cette extension.

Les remplacements et les jonctions de formes différentes
restent approximés. Une extraction suivant un ajout
dans le corps de la fonction peut également faire perdre
la précision des positions d’entrée. Les mutations via
un paramètre emprunté restent ouvertes.

Les 324 tests de la régression précédente et les
55 tests liés aux vecteurs passent. Le cas avec reset
du pool disjoint a aussi été exécuté isolément.
La régression élargie de cet état est en cours.

## Cases remplacées dans un vecteur reçu par transfert

Le contrat peut décrire le remplacement déterminé
d’une case littérale et préserver les positions des
autres cases. La mise à jour est résolue après les
suppressions décrites par le contrat et avant les
ajouts de fin. Les relais réutilisent cette information.
Quand les positions sont connues, les pools annoncés
sont ceux des cases restantes.

Deux variantes sous Clang C11 à `-O2` avec UBSan
fatal couvrent l’écriture par emprunt de case et
le bras succès de `replace` dont l’autre bras diverge.
Après le relais, le reset du pool de l’ancien handle
est autorisé pendant que le vecteur est vivant.
Les resets des deux pools encore représentés dans
le vecteur sont refusés. Les variantes extraient
les deux cases et vérifient adresses et valeurs.
Elles réinitialisent aussi le pool du handle
remplaçant après sa destruction, avant de lire
le handle voisin. Une mutation qui efface les
positions remplacées fait refuser à tort le reset
du pool de l’ancien handle dans les deux variantes.
Aucun nouveau modèle indépendant ni essai généré
n’a été exécuté pour cette extension.

Les 324 tests de la régression précédente passent.
Les écritures dont les branches modifient des cases
différentes et les paramètres empruntés restent
ouverts. Une suppression après un remplacement
peut encore effacer la précision du contrat.
Les 56 tests liés aux vecteurs passent sur cet état.
La régression élargie est en cours.

## Provenance par case aux jonctions de remplacements

Lorsque les chemins conservent la même forme de vecteur,
la jonction réunit les provenances des cases
correspondantes. Pour une case laissée intacte sur
un chemin, le contrat inclut sa provenance d’entrée.
Cette règle s’applique à la même case remplacée sur
plusieurs chemins et aux remplacements de cases
différentes. Les historiques de suppressions ou de
longueurs différents restent approximés.

Quatre variantes natives sous Clang C11 à `-O2`
avec UBSan fatal exercent les deux formes de jonction
et les deux chemins de chacune, via un relais. Elles
contrôlent la valeur de la première case et la
possibilité de réinitialiser un pool disjoint avant
sa lecture. Une variante par chemin refuse le
reset d’un pool encore possible pour cette case.
Une mutation qui efface la précision à la jonction
fait refuser les quatre cas valides.

Un modèle par listes compare 440 jonctions de trois
chemins sur des longueurs de 1 à 5. Chaque chemin
peut laisser le vecteur intact ou remplacer une
case. Les ensembles par case concordent avec
l’union calculée indépendamment par le modèle.

Les 325 tests de la régression précédente et les
57 tests liés aux vecteurs de cet état passent.
La régression élargie de cet état est en cours.

## Origine neuve autorisée par case

Le contrôle du contrat de résultat autorisait une
identité neuve provenant d’un pool annoncé dans
n’importe quelle case du vecteur. Un contrat muté
pouvait donc substituer une allocation neuve à un
handle d’entrée annoncé pour une autre case du même
pool. La génération C acceptait ce contrat muté.

Le contrôle conserve désormais les pools autorisés
à fournir une identité neuve pour chaque case
connue. Un résultat à positions inconnues continue
de vérifier les sources et les identités possibles
pour le vecteur entier.

Le nouveau test compile et exécute sous Clang C11
à `-O2` avec UBSan fatal le corps valide, qui
détruit son handle d’entrée puis crée deux handles
dans le même pool. Il vérifie que le vecteur contient
deux cases. Le même test injecte le contrat erroné
et vérifie que la compilation le refuse au contrôle
des cases. Aucun nouveau modèle indépendant ni
essai généré n’a été exécuté pour cette correction.

La régression précédente de 326 tests réussit. Les
57 tests liés aux vecteurs et le nouveau test ciblé
réussissent. La régression élargie est en cours.

## Décalage des remplacements après suppression

Une suppression à indice littéral décale les remplacements
déjà enregistrés. Un remplacement de la case supprimée
est retiré de l’historique. La composition applique aussi
ces décalages quand la suppression est effectuée après
un appel qui avait remplacé une case. Le contrat des
cases connues se fonde sur les remplacements encore
présents.

Deux variantes sous Clang C11 à `-O2` avec UBSan fatal
remplacent la case 1 puis suppriment la case 0, dans
la même fonction ou dans deux fonctions successives.
Le reset de l’ancien pool est autorisé pendant que
le nouveau handle est encore stocké. Le reset du
nouveau pool est refusé. Les essais vérifient la
valeur et l’adresse du handle conservé. Une mutation
qui efface le suivi du remplacement lors de la
suppression fait rejeter les deux variantes.

Un modèle de référence par listes concorde sur
1 211 états, avec jusqu’à trois opérations sur des
longueurs de 0 à 4. Il couvre remplacement, suppression
simple et composition de deux indices supprimés.

Un retrait en fin après remplacement ou une suppression
après ajout peut encore perdre l’ordre. La vérification
symbolique agrégée peut également conserver la trace
d’un pool local dont le handle a déjà été extrait et
détruit, et refuser la restitution dans ce cas.

Les 327 tests de la régression précédente et les
58 tests liés aux vecteurs de cet état réussissent.
La régression élargie est en cours.

## Identités vivantes après une jonction de longueurs

Le vérificateur conservait les identités de tous les
handles insérés dans le vecteur, même quand ses cases
connues prouvaient qu’un handle avait été détruit.
Une jonction de longueurs différentes abandonnait les
positions et réutilisait cet ensemble historique.
Dans le contre-exemple, le handle détruit appartenait
au même pool que le handle restant. La vérification
symbolique refusait le retour de `pop` avec le
diagnostic « identité entrante absente du résumé ».

Les opérations qui connaissent les cases recalculent
désormais l’ensemble des identités encore présentes.
Les vecteurs à positions inconnues gardent une
approximation conservative.

Deux variantes sous Clang C11 à `-O2` avec UBSan fatal
couvrent les branches avec et sans handle restant.
Elles vérifient la valeur, l’adresse du résultat
et la destruction unique du handle retiré avant
la jonction. Le reset du pool du résultat avant
son dernier usage est refusé dans chaque variante.
Une mutation qui conserve l’identité morte lors
de la suppression reproduit le faux refus sur
les deux chemins. Aucun nouveau modèle indépendant
ni essai généré n’a été exécuté pour cette correction.

Les 328 tests de la régression précédente et les
59 tests liés aux vecteurs de cet état réussissent.
La régression élargie est en cours.

## Push via un paramètre vecteur emprunté

Une fonction peut ajouter des handles à un
`&mut Vector<A<Int>>`. Le contrat décrit les cases
ajoutées pour chaque paramètre modifié. Le nombre
d’ajouts doit être identique sur les chemins qui
reviennent. Les relais composent ces ajouts. Le
vérificateur applique les nouvelles cases au vecteur
de l’appelant et exige que leurs pools survivent au
scope de ce vecteur. Le contrôle du corps compare
aussi les identités et, lorsque les cases sont
connues, le nombre d’ajouts annoncé.

Le test natif sous Clang C11 à `-O2` avec UBSan fatal
ajoute un handle reçu par transfert au travers
d’un relais, puis vérifie l’adresse, la destruction
unique et le réemploi de son slot. Le reset du
pool de la nouvelle case est refusé pendant le
stockage. Un appel qui tente d’insérer un handle
issu d’un pool de bloc enfant dans un vecteur
ancêtre est également refusé. Une mutation qui
supprime l’ajout du contrat du relais est détectée
en vérification symbolique. Aucun nouveau modèle
indépendant ni essai généré pour cette extension.

Les 329 tests de la régression précédente passent.
Les nombres variables d’ajouts et les autres
mutations d’un vecteur emprunté restent ouverts.

Les 60 tests liés aux vecteurs passent. Le test du relais
a également été rejoué après l’ajout du contrôle de
l’ordre des cases dans les appels de forme connue.
La régression élargie est en cours.

## Nombre variable d’ajouts via un emprunt mutable

Le contrat d’un vecteur emprunté peut annoncer un
ensemble de handles potentiellement ajoutés sans
fixer leur nombre. Les relais propagent cette
information. Chez l’appelant, les positions deviennent
inconnues et les pools possibles des nouvelles cases
restent protégés. Ce contrat sert aussi pour
`try_push`, dont le bras d’erreur conserve le
handle entrant jusqu’à son nettoyage.

Trois variantes natives sous Clang C11 à `-O2`
avec UBSan fatal couvrent les deux chemins de
`push` conditionnel et le succès de `try_push`.
Elles vérifient longueur, destruction unique
et réemploi du slot. Le reset du pool d’un handle
potentiellement stocké est refusé dans les trois
variantes. Une mutation qui annonce un nombre
d’ajouts fixe est détectée au contrôle du corps
du relais.

Deux sondes natives supplémentaires sous UBSan
vérifient trois ajouts en boucle et le bras
d’erreur de `try_push` à capacité. Dans ce dernier
cas, l’adresse du handle rendu est préservée,
la longueur reste de 131 072 et le slot est
réutilisable après nettoyage. Aucun nouveau
modèle indépendant ni essai généré pour
cette extension.

Les 330 tests de la régression précédente
réussissent. `replace`, `remove` et `pop` via un
paramètre emprunté restent ouverts.
Les 61 tests liés aux vecteurs réussissent sur
cet état. La régression élargie est en cours.

## Remplacement via un paramètre vecteur emprunté

Le contrat de mutation peut annoncer le remplacement
d’une case d’un `&mut Vector<A<Int>>`. À l’appel, le
vérificateur applique la mise à jour aux cases connues
et contrôle la durée de vie des pools. Lorsque les
chemins peuvent garder l’ancienne case ou la remplacer,
l’approximation conserve les deux provenances.

Deux variantes natives sous Clang C11 à `-O2` avec
UBSan fatal couvrent l’écriture par emprunt de case
et le retour par le bras succès de `replace`. Elles
passent par un relais. Le reset du pool de l’ancien
handle est accepté, celui du nouveau est refusé tant
que le handle est stocké. Elles contrôlent l’adresse,
la valeur, la destruction unique et le réemploi du
slot du nouveau handle. Lorsque les deux bras de
`replace` peuvent revenir, le reset de l’ancien
pool est également refusé. Une mutation qui omet
la mise à jour du contrat du relais est détectée
dans les deux variantes. Aucun nouveau modèle
indépendant ni essai généré pour cette extension.

La régression de 331 tests de l’état précédent
réussit. Les suppressions via un paramètre
emprunté restent ouvertes.
Les 62 tests liés aux vecteurs réussissent sur
cet état. La régression élargie est en cours.

## Extraction via un paramètre vecteur emprunté

Le contrat de mutation décrit les suppressions dans
un `&mut Vector<A<Int>>`, en plus du contrat du
handle extrait. Les relais composent les deux.
Chez l’appelant, les cases restantes et leurs pools
sont mis à jour si les indices sont connus. Quand
les chemins divergent, le contrat garde les pools
possibles. Le contrôle du corps détecte une
suppression non annoncée même lorsque les positions
d’entrée sont inconnues.

Deux variantes natives sous Clang C11 à `-O2`
avec UBSan fatal couvrent `remove(0)` et `pop`
par un relais. Elles vérifient les adresses et
valeurs du handle extrait et du handle restant,
ainsi que leurs destructions uniques. Le reset
du pool extrait est permis après destruction du
résultat, mais refusé avant son dernier usage.
Le reset du pool de la case encore stockée est
refusé. Une mutation qui omet la suppression du
contrat du relais est détectée dans les deux cas.

Deux sondes natives supplémentaires sous UBSan
exercent `pop` sur un vecteur vide et non vide
quand les deux bras peuvent revenir. Aucun nouveau
modèle indépendant ni essai généré pour cette
extension. Les 332 tests de la régression précédente
passent.

Les 63 tests liés aux vecteurs réussissent.
La régression élargie est en cours.

## Emprunt du contenu d’un handle typé

`vref()` et `mut_vref()` empruntent désormais le
contenu d’une allocation typée avec le type exact
du pool. Les analyseurs utilisent les mêmes règles
d’emprunt que pour les autres expressions de
référence. Le vérificateur conserve l’identité
de l’allocation et vérifie sa provenance avant
de produire l’emprunt.

Un cas natif sous Clang C11 à `-O2` avec UBSan fatal
vérifie une structure Point à travers des appels,
un Vector<Int> et une String UTF-8. Il compare
l’adresse du Point avant et pendant l’emprunt
et contrôle les trois valeurs après modification.
Les variantes avec drop ou reset avant le dernier
usage d’un emprunt de Point sont refusées. Une
mutation qui limite à nouveau l’emprunt au contenu
Int est détectée. Aucun nouveau modèle indépendant
ni essai généré pour cette extension.

La régression de 333 tests de l’état précédent
réussit. Les emprunts du handle lui-même via
`ref()` ou `mut_ref()` restent spécialisés pour
A<Int>. Le transport hors match des résultats
non Copy reste ouvert.

Les 57 tests sélectionnés par `handle` réussissent.
La régression élargie est en cours.

## Emprunts et remplacement de handles typés

`ref()` et `mut_ref()` conservent désormais le type
du handle pour les allocations typées. Les paramètres
et résultats empruntés distinguent `&A<Point>` et
`&A<Other>`, même si le C représente les deux par un
pointeur de case. La réaffectation via un emprunt
mutable direct du handle local vérifie le type du
remplaçant avant de détruire l’ancienne allocation.

Le test natif sous Clang C11 à `-O2` avec UBSan fatal
remplace un `A<Point>`, compare l’adresse du
remplaçant avant et après affectation, puis vérifie
le réemploi de l’ancien slot. Il relaie ensuite un
emprunt partagé à travers deux signatures.
Le test refuse un handle de remplacement d’un autre
type, un argument `&A<Other>` et une destruction
avant le dernier usage de l’emprunt relayé. Une
mutation qui efface le type des cases fait accepter
l’argument invalide et est détectée. Aucun nouveau
modèle indépendant ni essai généré pour cette
extension.

Les 334 tests de la régression précédente passent.
La réaffectation du handle à travers un paramètre
emprunté reste ouverte. La comparaison `vequals`
reste spécialisée pour Int.
Les 58 tests sélectionnés par `handle` passent.
La régression élargie est en cours.

## Comparaison de contenu des handles d’agrégats

`vequals` accepte les structures et enums dont les
champs sont des Int. La comparaison vérifie le type
du handle, compare le tag avant les champs et ne lit
que les champs de la variante active. Les méthodes
déclarées par un type gardent la priorité sur les
méthodes intégrées du handle.

Le test natif sous Clang C11 à `-O2` avec UBSan
fatal compare des Points issus de pools différents,
des champs différents et des variantes d’enum ayant
le même contenu entier. Il refuse un emprunt d’un
autre type nominal. Une mutation qui substitue la
valeur au tag fait déclarer deux variantes distinctes
égales et est détectée. Aucun nouveau modèle
indépendant ni essai généré pour cette extension.

La régression de l’état précédent a exécuté 335
tests et a trouvé deux erreurs de résolution sur
des méthodes utilisateur nommées `ref`. Après
correction, les deux cas ont été rejoués avec succès.
Les comparaisons de chaînes, de vecteurs et de
champs contenant des références restent ouvertes.

Les 69 tests ciblant handles, méthodes et
`vequals` passent. La régression élargie de
cet état est en cours.

## Comparaison de contenu des chaînes et vecteurs

La règle H3 est inchangée. `vequals` compare les contenus de
`String`, `Vector<Int>` et `Vector<u8>` de même type. Le C vérifie
les longueurs et parcourt les seuls éléments initialisés par index logique,
dans les deux sens de croissance. Les Int sont comparés par valeur et les
octets par contenu. Les emprunts suivent les vérifications existantes.

Les trois tests ciblés par `-k vequals` passent. Le scénario Crust natif
compare des chaînes vides et UTF-8, des Int dans des ordres opposés et des
octets contenant un zéro. Il refuse la comparaison de vecteurs de types
différents et le reset du pool avant le dernier usage d'un emprunt du
handle. Le scénario C supplémentaire vérifie explicitement le placement
sur deux fronts opposés, les longueurs différentes, puis l'égalité et
l'inégalité de deux séquences non palindromiques. Il passe sous Clang
20.1.3 en C11 à `-O0` et `-O2`, avec UBSan fatal. Une mutation temporaire
qui parcourt les adresses dans l'ordre physique fait échouer l'assertion
d'égalité aux deux niveaux d'optimisation.

La régression du cycle précédent a passé 336 tests. Le scénario C
emploie des valeurs attendues fixées à la main. Aucun nouveau modèle
indépendant ni essai généré pour l'égalité. La comparaison des vecteurs
de handles et des agrégats contenant des références reste ouverte.

L'essai combinant ASan et UBSan a dépassé 10 secondes sur les trois
exécutions. Un binaire témoin réduit à `int main(void) { return 0; }`,
compilé avec les mêmes sanitizers, dépasse aussi 5 secondes dans cet
environnement. Cet essai ASan est non concluant.

Pour le prochain écart H2, un appel à `swap(h: &mut A<Int>,
replacement: -> A<Int>)` avec `*h = <- replacement;` dans le corps est
encore refusé à l'affectation. Le cas place les allocations dans deux
pools, puis réinitialise l'ancien pool et lit le receveur. Il faudra
propager la provenance du remplaçant au receveur dans le contrat,
avant de pouvoir vérifier ce cas jusqu'au C.

La régression élargie (fondations, résultats, contraintes, effets, appels
modulaires et runtime de croissance) passe ses 355 tests en 139,901 s.
La découverte complète a été lancée avec
`python3 -m unittest discover -s tests`. Son journal est
`/tmp/crust-h3-vequals-sequences-full.log`.

## Remplacement de handle local par réemprunt

Pour H2, un réemprunt explicite `&mut *h` d'un handle local peut
remplacer l'allocation. Le receveur et la chaîne d'emprunts conservent le
même emplacement de handle. Après évaluation du remplaçant et destruction
de l'ancien objet, la chaîne suit la nouvelle allocation. Les analyses de
résultats et de contraintes propagent le changement de provenance aux
emprunts du même handle local.

Le test Clang C11 à `-O2` avec UBSan fatal remplace via le réemprunt,
reprend le parent après le dernier usage de l'enfant et retourne le
handle. Deux pools de capacité un vérifient le réemploi du premier slot
dans la fonction, la lecture après reset du premier pool, puis le
réemploi du second slot après drop. Deux variantes sont refusées, l'accès
au parent si l'enfant doit encore servir et le reset du second pool avant
le dernier usage du parent. Une mutation temporaire laisse le parent sur
l'ancienne allocation et provoque « allocation empruntée libérée ».
Les 59 tests ciblés par `-k handle` passent. La régression des résultats,
contraintes, effets, appels modulaires, réaffectations et provenances passe
ses 140 tests. Aucun nouvel oracle indépendant ni essai généré pour H2.

La découverte complète précédente a révélé une régression E6 sur le test
`test_borrowed_container_updates_cross_function_contracts`.
`v.mut_ref()` était résolu comme un emprunt de handle par l'analyse de
contraintes, même si `v` était un tableau fixe de références. La résolution
distingue maintenant les types de tableau des allocations. Le test
existant rejoué passe et couvre la permutation relayée, les écritures
vers les cibles permutées et un conflit d'emprunt.

La découverte complète du nouvel état a été lancée avec
`python3 -m unittest discover -s tests` (journal
`/tmp/crust-h2-full.log`). Le remplacement à travers un paramètre
`&mut A<T>` reste ouvert. Il nécessite un effet de contrat applicable au
receveur de l'appelant, y compris quand le corps fournit plusieurs
provenances possibles.

## Résumé des écritures via un paramètre de handle

La règle H2 est inchangée. `FunctionResult.handle_writes` enregistre,
par paramètre mutable, les provenances possibles du handle à la sortie
de la fonction. Le résultat symbolique inclut l'allocation d'entrée
quand un chemin retourne sans remplacement. Un appel relayé substitue
les paramètres effectifs dans les alternatives. Un pool déclaré dans
le corps ne peut pas fournir un remplaçant au receveur injecté.

Deux tests ciblent l'analyse symbolique. Le premier vérifie les trois
alternatives attendues (handle inchangé, allocation transférée et
allocation neuve d'un pool injecté) dans le résumé direct et dans celui
du relais. Le second vérifie le refus du pool local. Une mutation
temporaire efface l'alternative inchangée et fait échouer les deux
assertions du premier test. La régression du cycle précédent pour les
tableaux fixes et les lignes de références passe ses 90 tests en
72,978 s.

Cette passe n'applique pas encore l'effet au receveur chez l'appelant.
Elle ne valide ni le nettoyage de l'ancien objet en C ni les
interactions entre remplacement et reset dans un même contrat. La
fonction avec remplacement via paramètre reste refusée par le
vérificateur concret. Les tests symboliques utilisent des alternatives
attendues écrites à la main.

Les 59 tests ciblant les handles passent avec le nouveau résumé, ainsi
que les 27 tests de `test_results`, dont les deux nouveaux cas
symboliques.

## Application du contrat d'écriture sur un handle injecté

Le vérificateur applique `handle_writes` au receveur de l'appelant et
contrôle la durée de vie de chacun des pools possibles. Pour `&mut A<Int>`,
le C évalue le remplaçant, détruit l'ancien objet, puis écrit dans le même
emplacement de handle. La vérification du corps contrôle les provenances
observées à chaque sortie contre celles annoncées par le résumé.
L'analyse des contraintes propage aussi le changement aux emprunts
du handle dans la fonction appelante.

Deux tests natifs exécutés avec Clang C11 à `-O2` et UBSan fatal
couvrent le remplacement inconditionnel à travers deux appels depuis
un bloc enfant, puis les deux sorties du remplacement conditionnel.
Les assertions contrôlent l'adresse du remplaçant, la destruction de
l'ancien objet, le reset de l'ancien pool après remplacement certain et
la réutilisation du slot du remplaçant après drop. Trois variantes sont
refusées, le reset du nouveau pool avant une lecture, le reset de
l'ancien pool si l'appel peut garder l'ancien handle, et le transfert
depuis un pool qui meurt avec le bloc enfant. Une mutation temporaire du
C qui omet la destruction laisse une allocation vivante et le test
échoue à la fermeture du pool. Aucun nouveau modèle indépendant ni
test généré pour cette passe.

La règle H2 conserve sa portée générique. L'application actuelle est
limitée à `A<Int>`. Les autres contenus exigent de transporter leurs
métadonnées, dont les emprunts stockés et les éléments d'un vecteur.
Les appels combinant remplacement et reset d'un pool du handle dans
un même contrat restent refusés. Les ordres de réception variables qui
nécessitent un ordre de nettoyage dynamique restent ouverts.

La découverte complète antérieure a exécuté 1 168 tests et trouvé la
régression E6 déjà corrigée. Une régression élargie de cet état est
en cours dans `/tmp/crust-h2-injected-regression.log`.

## Remplacement injecté des contenus sans emprunts stockés

Le mécanisme H2 s'applique aux structures et enums sans champs empruntés,
à `String`, à `Vector<Int>` et à `Vector<u8>`. Le contrat retient
les variantes des allocations transférées et admet les variantes
déclarées pour une allocation neuve. Le corps vérifie les variantes
effectives à la sortie. Un seul chemin d'emprunt reste exploitable
lorsqu'il est représenté par une liste d'alternatives après un `if`.

Cinq cas natifs sous Clang C11 à `-O2` et UBSan fatal couvrent le relais,
l'adresse stable du remplaçant et la lecture après le reset de l'ancien
pool. Les cinq variantes qui réinitialisent le nouveau pool avant usage
sont refusées. Les vecteurs et la chaîne continuent de croître après le
transfert. Deux exécutions de l'enum conditionnel couvrent le chemin
inchangé et l'allocation neuve après une jonction. Une mutation qui
conserve les anciennes variantes provoque un écart détecté entre le
corps et son contrat. Aucun nouveau modèle indépendant ni essai généré
pour cette extension.

La découverte complète précédant les écritures via paramètre a passé
1 169 tests. La régression de la première implémentation sur
`&mut A<Int>` a passé 382 tests. La régression de l'extension typée est
en cours dans `/tmp/crust-h2-typed-regression.log`.

Les champs qui stockent des emprunts et `Vector<A<Int>>` exigent encore
un résumé de leurs dépendances ou de leurs éléments. L'interaction entre
reset et remplacement dans un même appel reste ouverte.

## Emprunts stockés dans un remplaçant transféré

Pour H2, l'écriture via `&mut A<View>` propage les dépendances et les
réservations de l'allocation transférée au receveur. Le corps doit
respecter les cibles autorisées par le contrat. Le pool de stockage et
les cibles empruntées doivent survivre au receveur. Quand le
remplacement est certain, les dépendances de l'ancien objet sont
retirées. Quand l'objet initial peut rester, ses dépendances restent
dans le résumé.

Deux exécutions natives sous Clang C11 à `-O2` avec UBSan fatal
exercent un relais sur des champs `&Int` et `&mut Int`. Dans le cas
partagé, le reset de l'ancienne cible est permis et la nouvelle reste
lisible. Dans le cas mutable, l'ancienne cible redevient modifiable
après remplacement, et la nouvelle après le drop du receveur. Quatre
variantes vérifient les refus pour un reset ou un drop de la nouvelle
cible, une cible locale qui meurt avant le receveur et une écriture
directe pendant l'emprunt mutable. Une mutation qui efface les
dépendances pendant l'application du contrat est détectée par le
diagnostic de provenance de champ manquante.

La régression de l'extension typée précédente a passé 344 tests.
La régression de cet état est en cours dans
`/tmp/crust-h2-field-regression.log`. Aucun nouveau modèle
indépendant ni essai généré pour cette extension. La construction
du remplaçant avec des champs empruntés dans le corps, et la
modification de champs au-delà des provenances d'entrée, nécessitent
encore un résumé par champ. Les vecteurs de handles restent ouverts.

## Résumé par champ du remplaçant injecté

Pour H2, le contrat décrit les cibles possibles de chaque champ du
handle à la sortie. Un relais substitue les cibles effectives. Le
vérificateur vérifie les cibles et réservations produites par le corps,
puis applique le résumé au receveur et vérifie que les cibles survivent
à ce dernier. Une cible locale au corps ne peut pas sortir dans le
remplaçant.

Deux exécutions Clang C11 à `-O2` avec UBSan fatal couvrent un
remplaçant construit avec un champ `&mut Int` et un objet transféré
dont le champ change avant le transfert. Dans les deux cas, le
remplacement passe par un relais. Les anciennes cibles redeviennent
modifiables, le nouveau champ reste lisible et sa cible redevient
modifiable après drop. Les deux variantes qui écrivent trop tôt dans
la nouvelle cible sont refusées, de même qu'une cible locale au
corps. Une mutation qui retire les champs du résumé fait échouer la
vérification de provenance du corps avant génération du C.

La régression du transfert de champs déjà initialisés a passé
345 tests. La régression de cet état est en cours dans
`/tmp/crust-h2-field-effects-regression.log`. Aucun nouveau modèle
indépendant ni essai généré dans cette passe. Le remplacement des
vecteurs de handles et l'ordre entre reset et remplacement dans un
même appel restent ouverts.

## Remplacement injecté d'un vecteur de handles transféré

Pour H2 et VE3, le remplacement via `&mut A<Vector<A<Int>>>` applique
au receveur l'inventaire du vecteur transféré. Le contrat réutilise les
métadonnées de provenance et d'identité par case. La vérification du
corps compare les identités observées avec celles du contrat. Les pools
des éléments doivent survivre au receveur.

Un essai natif sous Clang C11 à `-O2` avec UBSan fatal remplace via deux
appels un vecteur qui contient un handle par un vecteur dont les deux
handles viennent de pools distincts. Il réinitialise les anciens
pools, extrait et détruit le premier élément, réinitialise son pool et
lit le second. Deux variantes refusent le reset prématuré de chacun des
pools encore représentés dans le vecteur. Une mutation qui inverse les
identités par case dans le contrat est détectée à la vérification du
corps. Aucun nouveau modèle indépendant ni essai généré.

La régression précédente a passé 346 tests. La régression de cette
passe est en cours dans `/tmp/crust-h2-vector-writes-regression.log`.
La construction d'un vecteur remplaçant dans le corps et le transport
d'un inventaire transformé par ce corps restent à couvrir.

## Remplacement injecté par un vecteur neuf

Pour H2 et VE3, le contrat d'un vecteur remplaçant construit dans le
corps transporte l'inventaire déterminé des cases. Le relais substitue
les pools et les handles reçus. La vérification du corps contrôle la
provenance de chaque case et distingue les identités déjà présentes
des allocations créées dans l'appel.

L'essai natif Clang C11 à `-O2` avec UBSan fatal construit un
`Vector<A<Int>>` à deux cases, l'une neuve et l'autre transférée.
Il traverse deux appels, réinitialise l'ancien pool du vecteur,
extrait la première case et réinitialise son pool après le drop.
La seconde case conserve son adresse et sa valeur. Deux variantes
refusent de réinitialiser prématurément un pool d'élément. Une
troisième refuse un élément issu d'un pool local au corps.
Une mutation qui inverse les cases du contrat est détectée avant
génération du C. Aucun nouveau modèle indépendant ni essai généré.

La régression de cet état est en cours dans
`/tmp/crust-h2-fresh-vector-regression.log`. Les inventaires
transformés sur un vecteur reçu et les vecteurs neufs dont les
cases sont indéterminées restent à couvrir.

## Remplacement injecté après transformation d'un vecteur reçu

Pour H2 et VE3, le contrat de remplacement réutilise le résumé
d'inventaire des retours de vecteurs. L'analyse transporte les
suppressions, les remplacements de cases et les ajouts. Les deux
formes d'appel partagent maintenant le calcul symbolique de
l'inventaire et l'application des contraintes de provenance.

Le cas natif sous Clang C11 à `-O2` et UBSan fatal supprime la première
case d'un vecteur reçu, détruit son handle, ajoute une allocation
neuve puis transmet le vecteur à travers un relais. Le pool de la case
supprimée peut être réinitialisé. La case décalée conserve son adresse
et sa valeur. Deux variantes refusent le reset d'un pool encore
représenté dans le vecteur. Une mutation qui omet la suppression dans
le contrat est détectée par le vérificateur de provenance.
L'ajout après suppression est le cas natif de cette passe. Le
remplacement par indice et les inventaires neufs indéterminés restent
à éprouver sur cette forme d'appel. Aucun nouveau modèle indépendant.

La régression antérieure sur le remplacement de vecteurs transférés
a passé 347 tests. La régression de cette passe est en cours dans
`/tmp/crust-h2-transformed-vector-regression.log`.

## Remplacement par indice et inventaire neuf conditionnel

Pour H2 et VE3, le remplacement via un handle utilise désormais le
même résumé de vecteur pour un inventaire neuf exact ou conditionnel.
Quand la longueur diffère entre chemins, le résumé conserve
l'ensemble des pools possibles sans prétendre connaître les cases.
Les identités symboliques des éléments neufs restent associées à
leurs pools même sans position déterminée.

Sous Clang C11 à `-O2` avec UBSan fatal, le remplacement littéral de
la première case conserve l'adresse de la case voisine à travers
un relais. Le pool de l'ancien élément est réinitialisable, puis
celui de l'élément extrait après drop. Un reset du pool de la case
voisine est refusé. Un vecteur neuf contenant zéro ou un élément
selon le chemin est exécuté sur les deux branches. Son pool
d'élément reste protégé jusqu'au drop du vecteur. Une mutation qui
omet ce pool dans le résumé est détectée. Les neuf tests ciblés
par `-k handle_replacement` passent. Aucun nouveau modèle indépendant
ni essai généré.

La régression élargie est en cours dans
`/tmp/crust-h2-conditional-vector-regression.log`. La prise en charge
d'un inventaire conditionnel dépend de provenances symboliques
vérifiables. L'ordre entre reset et remplacement dans un même appel
reste ouvert.

## Affectation d'un handle emprunté depuis un bloc enfant

Pour H2, un bloc enfant peut remplacer le contenu d'un handle
emprunté qui demeure dans un bloc ancêtre. Les pools et les
dépendances du remplaçant doivent survivre au receveur. Le C
évalue le remplaçant, détruit l'ancien objet et actualise à la
fois l'emplacement emprunté et, s'il diffère, le pointeur que le
bloc ancêtre utilise pour le nettoyage.

Trois exécutions Clang C11 à `-O2` avec UBSan fatal couvrent une
affectation via réemprunt, l'adresse stable, le drop et la
réutilisation du slot, puis les deux branches d'une affectation
conditionnelle. Le compilateur refuse le pool local à l'enfant,
le reset prématuré du nouveau pool et le reset de l'ancien pool
quand un chemin conserve le handle d'entrée. Les tests de reset
portent sur le compilateur synchrone historique. Une mutation qui
supprime l'actualisation du pointeur de nettoyage déclenche une
seconde destruction de l'ancien objet, détectée par UBSan.
Aucun nouveau modèle indépendant ni essai généré.

La régression de la transformation de vecteur a passé 349 tests.
La régression de cette passe est en cours dans
`/tmp/crust-h2-ancestor-regression.log`. Les ordres de réception
variables entre plusieurs objets restent ouverts.

## Nettoyage après remplacement dans une branche appelante

Un appel à une fonction qui remplace le handle dans une seule branche
pouvait laisser le pointeur de nettoyage sur l'ancien objet. La
jonction rétablissait son expression C d'entrée, alors que le
remplacement avait seulement modifié l'emplacement emprunté. Le
contre-exemple produit une seconde destruction et un accès à un
pointeur nul sous UBSan. Le C actualise maintenant le pointeur de
nettoyage après le retour, à partir de l'argument mutable préparé.

Quatre exécutions sous Clang C11 à `-O2` avec UBSan fatal couvrent les
deux branches et les formes d'appel Void et Int. Elles vérifient
la valeur du receveur et la trace exacte de destruction. Une
mutation qui retire l'actualisation reproduit la seconde
destruction dans les deux formes d'appel. Le test vérifie aussi
le refus d'une jonction qui inverse l'ordre de réception de deux
objets. Ce refus est prévu par T9 et L3 pour le prototype. Le
rapport précédent présentait à tort cet ordre incompatible
comme une fonctionnalité à implémenter. Aucun nouveau modèle
indépendant ni essai généré.

La régression de l'inventaire conditionnel a passé 350 tests.
La suite ciblée sur les handles est en cours dans
`/tmp/crust-h2-call-join-targeted.log`.

La suite des handles a passé 71 tests. La sélection
`handle_replacement` exécutée après l'ajout du cas T9 a passé 11 tests.

## Receveurs consommants typés et restitution du handle

L'audit H3 confirme que l'implémentation existante distingue
`self: -> A<Point>` et `self: -> Point` dans le contrat. Un nouveau
test vérifie les marqueurs de paramètre et de résultat, puis exécute
la restitution à travers une méthode et une fonction relais. Sous
Clang C11 à `-O2` avec UBSan fatal, le handle restitué garde son
adresse, le transfert final détruit exactement une fois le Point
et le pool de capacité un réutilise le même emplacement.

Le test refuse l'appel sans flèche, l'accès à l'ancien nom après
le transfert et une restitution typée dont le receveur ne promet
pas l'origine dans un pool typé. Une mutation qui retire le marqueur
du receveur lors de l'abaissement de l'implémentation fait échouer la
vérification de la restitution. Aucun changement de sémantique
ni nouveau modèle indépendant. La sélection `-k method` a passé
11 tests et le nouveau cas a été rejoué après l'ajout du troisième
refus. La régression du remplacement depuis un enfant a passé
371 tests.

## Restitution d'un import après remplacement du handle

T6–T8 distinguent la restitution de l'objet importé du transfert d'un
autre objet vers un receveur explicite. Le remplacement via
`&mut A<Int>` conservait la représentation du slot et pouvait ainsi
réactiver l'accès du parent pour un objet différent. Le compilateur
associe désormais à chaque import la révision du handle à son entrée.
Un remplacement possible empêche la restitution implicite. La
vérification opaque refuse aussi le remplacement d'un handle dont
l'export est déjà marqué, comme le faisait le vérificateur du corps.

Deux exécutions Clang C11 à `-O2` avec UBSan fatal couvrent le
remplacement avant l'import suivi d'une restitution normale, puis
le remplacement après l'import avec un nouveau receveur explicite.
Le cas sans receveur produit un avertissement et l'ancien accès
reste indisponible. Les deux points d'entrée refusent le remplacement
après marquage de l'export. Une mutation qui supprime la mise à jour
de la révision réactive à tort la restitution et est détectée.
Les 18 tests ciblés sur les transferts passent. La régression élargie
est en cours dans `/tmp/crust-h2-import-full-regression.log`.
Aucun nouveau modèle indépendant ni essai généré.

## Remplacement à travers une reprise de boucle et un retour

Pour H2, le remplacement via un emprunt mutable déclaré avant la
boucle a été vérifié sur plusieurs reprises `continue`, une sortie
`break` et un retour de fonction. Le test Clang C11 à `-O2` avec
UBSan fatal alterne entre deux pools, lit la dernière valeur, la
détruit et réutilise le slot libéré. Il vérifie la trace complète
des destructions. Les deux resets historiques avant la lecture sont
refusés, car le résultat peut provenir des deux pools. Une mutation
qui omet l'un de ces pools dans le résumé est détectée à la
vérification du résultat.

Le comportement existant est couvert par une nouvelle régression
sans changement du compilateur. Aucun nouveau modèle indépendant ni
essai généré. La sélection sur les boucles est en cours dans
`/tmp/crust-h2-loop-handle-regression.log`.

La sélection sur les boucles a passé ses 37 tests en 15,770 s.

## Déclaration compacte de transfert T6

Le parseur accepte `let <- nom = expression;` et abaisse le nom nu
en dernière position du même bloc vers le transfert explicite déjà
vérifié. La déclaration exige une allocation. Le marqueur demeure
attaché à la déclaration locale et ne rend pas le nom accessible
depuis le parent ou transférable par un nom nu dans un autre bloc.

Deux exécutions Clang C11 à `-O2` avec UBSan fatal vérifient le
retour de fonction, la réception d'un bloc et d'un `if`, la
conservation d'adresse et le réemploi du slot si aucun receveur
n'existe. Le vérificateur refuse les scalaires et sources marqués,
la visibilité du nom dans le parent, la sortie d'un pool local,
la reprise du marqueur dans un autre bloc et le résultat reçu sans
usage explicite. Une mutation qui supprime l'abaissement du nom
final est détectée. Aucun nouvel oracle indépendant ni essai généré.

La régression élargie précédente a passé 386 tests. La régression
de cette passe est en cours dans `/tmp/crust-t6-compact-regression.log`.

## Réemprunt explicite d'une tranche mutable

Pour VE5 et TX8, `&*vue` crée une tranche partagée depuis une
tranche mutable de Vector et `&mut *vue` crée un réemprunt mutable.
La vue conserve l'intervalle et l'ascendance de son emprunt. Le
vérificateur peut donc suspendre les écritures en conflit tout en
laissant utilisable une moitié disjointe.

Deux scénarios Clang C11 à `-O2` avec UBSan fatal passent. Une
moitié d'octets est convertie en vue UTF-8 à travers le retour
d'une fonction, et l'autre moitié est modifiée pendant l'emprunt.
Les écritures dans la première moitié et la croissance du vecteur
sont refusées pendant la vue. Un réemprunt mutable de la première
moitié redevient possible après le dernier usage. Le cas Int
exerce une vue partagée nommée, un appel et la reprise de l'écriture.
Une mutation qui efface le chemin d'emprunt est détectée. Aucun
nouveau modèle indépendant ni essai généré.

La régression TX16 a passé 276 tests. La régression de cette passe
est en cours dans `/tmp/crust-ve5-reborrow-regression.log`. Le
transport des deux moitiés dans un résultat groupé reste ouvert.

## Relais et sous-tranches de vues de vecteur

VE5 accepte `&*vue` sur une tranche déjà partagée. Le réemprunt
conserve son mode et sa provenance à travers les appels. Une vue
partagée ou mutable peut fournir une sous-tranche partagée avec
`&vue[debut..fin]`. Les bornes sont évaluées de gauche à droite
pendant que la vue source est réservée. Le C valide les bornes
par rapport à la tranche source et conserve son orientation.

Sous Clang C11 à `-O2` avec UBSan fatal, le test Int relaie une
moitié partagée, en renvoie une sous-tranche sur le front descendant
et écrit dans la moitié disjointe. L'écriture dans la moitié
empruntée et la conversion vers un emprunt mutable sont refusées.
Une borne trop grande échoue à la garde native. La mutation qui
utilise le décalage montant sur le front descendant est détectée.
Le test de réemprunt sur les octets passe également. Aucun nouveau
modèle indépendant ni essai généré.

La régression élargie est en cours dans
`/tmp/crust-ve5-subslice-regression.log`. Le retour des deux moitiés
dans un même résultat reste ouvert.

La régression du premier réemprunt (342 tests, 31 échecs) a
exposé un défaut hérité de TX8. Le champ C `descends` manquait
dans les initialiseurs contigus, ce que `-Werror` refuse.
Les initialiseurs du runtime et des littéraux générés ont été
corrigés. Un littéral UTF-8 a été compilé et exécuté avec les
options strictes de la suite. La suite des contrats rejoue cet
état dans `/tmp/crust-ve5-strict-regression.log`.

Les 82 tests des contrats rejoués passent. La régression élargie
avec les initialiseurs corrigés est en cours dans
`/tmp/crust-ve5-subslice-current.log`.

## Récupération du stockage des vecteurs de handles

La couverture de GR2 et VE2 vérifie maintenant le recul des
curseurs d'un `Vector<A<Int>>` après destruction de ses éléments.
Le test C étendu contrôle le retour du curseur haut, la stabilité
de l'adresse et du curseur du front bas encore vivant, puis le
réemploi de la case haute. Une seconde phase vérifie le réemploi
de la première case d'une région partagée et le retour des slots
aux pools d'origine. Il passe avec Clang C11 sous UBSan fatal à
`-O0` et `-O2`. Une mutation qui rend le stockage avant la
destruction des handles est détectée aux deux niveaux.

Le test Crust vérifie l'ordre exact de destruction de deux
handles appartenant à des pools distincts. Une mutation qui
parcourt les éléments dans l'ordre inverse de cet ordre attendu
échoue. Cette passe étend la vérification du runtime existant.
Les autres familles d'éléments non Copy et les vecteurs
d'emprunts restent à couvrir.

La régression de croissance et UTF-8 a passé 22 tests en 36,127 s.

## Expressions Bool à court-circuit

F4 accepte maintenant `&&` et `||` dans les expressions Bool,
dont une déclaration, un argument et un retour de fonction.
L'abaissement vers une expression conditionnelle réutilise la
vérification des branches, la jonction des effets et le nettoyage
du chemin exécuté. `&&` garde la priorité sur `||`. Les deux
opérandes doivent être Bool dans cette forme.

Les six tests ciblés sur le court-circuit passent avec Clang C11
à `-O2` sous UBSan fatal. Le nouveau cas vérifie la trace exacte
des appels évalués, le refus des opérandes Int et le refus
d'un accès après un déplacement conditionnel. Une mutation qui
force l'évaluation de l'opérande droit de `&&` est détectée.
Aucun nouvel oracle indépendant ni essai généré.

La régression élargie est en cours dans
`/tmp/crust-f4-bool-values-regression.log`. Les comparaisons
restent reconnues dans la grammaire des conditions.

La régression élargie VE5 avec les initialiseurs corrigés a passé 360 tests.

## Comparaisons comme valeurs Bool

Les comparaisons peuvent fournir une valeur Bool dans les
expressions. Elles sont évaluées avant `&&` et `||`, après
l'arithmétique, et les opérandes restent évalués de gauche
à droite. Le parseur distingue une condition parenthésée
d'une expression parenthésée suivie d'une comparaison ou
d'une opération arithmétique. Le vérificateur de conditions
reste commun pour les types et les effets.

Le scénario Clang C11 à `-O2` sous UBSan fatal vérifie les
comparaisons dans une déclaration, un argument et un retour.
Il vérifie aussi les conditions parenthésées et la trace
du court-circuit. Les comparaisons entre Int et Bool et
l'ordre entre deux Bool sont refusés. Une mutation qui inverse
le résultat d'une comparaison comme valeur est détectée.
Aucun nouveau modèle indépendant ni essai généré.

La régression des conditions et appels est en cours dans
`/tmp/crust-f4-compare-control.log`. La découverte complète
a été lancée dans `/tmp/crust-f4-compare-full.log`.

## Accès après une expression parenthésée dans une condition

Le parseur terminait une condition au premier groupe parenthésé
même quand un accès par méthode ou par indice suivait. Il reprend
désormais l'analyse de l'expression dans ce cas. Le test élargi
exécute un `if` sur `("é").byte_len()` et un `while` sur
`(values)[0]` sous Clang C11 à `-O2` avec UBSan fatal. Une
mutation qui retire la détection du suffixe reproduit le refus
du programme valide. Aucun nouveau modèle indépendant.

La découverte complète lancée au cycle précédent suit l'état
antérieur à cette correction. La sélection sur le court-circuit
rejoue le code corrigé dans `/tmp/crust-f4-postfix-short-circuit.log`.

La sélection ciblée sur le court-circuit a passé 7 tests.

## Conservation locale du résultat non Copy de pop

VE3 accepte `let saved = <- v.pop();` pour `Vector<A<Int>>`.
Le vecteur est modifié à l'évaluation de la déclaration.
Le résultat local conserve la provenance du handle possible
et en assure le nettoyage au drop explicite ou à la sortie
du scope. Le C arme le nettoyage seulement si le résultat
contient un handle. Une jonction conserve cette garde.

Sous Clang C11 à `-O2` avec UBSan fatal, le test exécute les
chemins Some et None avec nettoyage automatique puis explicite.
Il vérifie que le vecteur est déjà vide, qu'un seul handle est
détruit et que le slot peut être réutilisé après drop. Le reset
prématuré, la copie et le double drop sont refusés. Une mutation
qui traite la garde comme toujours vraie après une jonction
déclenche un accès nul sous UBSan. Aucun nouveau modèle indépendant.

Les 94 tests de contrôle précédents passent. La régression de
cette passe est en cours dans `/tmp/crust-ve3-buffered-pop-regression.log`.
Le match différé du résultat local, les retours interfonctions et
les résultats non Copy de replace et try_push restent ouverts.

## Match différé du résultat non Copy de pop

Le match consommant d'un résultat local de pop sélectionne le bras à
partir du discriminant déjà calculé. Some transfère le handle au bras
avec sa provenance et désarme le nettoyage du résultat d'origine.
None consomme le résultat vide.

Deux tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le nouveau test extrait un handle, insère dans le vecteur un handle
issu d'un autre pool, puis consomme le résultat conservé. Il vérifie
l'adresse de la cible, le réemploi du slot, le contenu restant du
vecteur, le bras None et la destruction unique de chaque handle.
Le reset avant le match, le match sans transfert explicite et la
seconde consommation sont refusés. Forcer le discriminant à Some
fait échouer le test sur le résultat vide avec le diagnostic
`pop de handle : aucun élément possible`. Aucun nouveau modèle indépendant.
Le transport interfonction et les résultats locaux non Copy de
replace et try_push restent ouverts.

La notation F2 `match (-> saved)` est couverte en expression et en
instruction. Un bras `_` peut compléter un bras explicite. La forme
avec le seul bras `_` et la consommation depuis un scope ancêtre
restent ouvertes. La régression précédente sur le résultat local
avant ajout du match a passé 343 tests. Une nouvelle découverte
complète est en cours sur le code final dans
`/tmp/crust-ve3-named-pop-final.log`.

## Bras couvrant toutes les variantes du résultat de pop

`match (-> saved) { _ => { ... } }` consomme le résultat local et
détruit le handle présent avant le corps du bras. Le cas vide passe
par le même corps sans détruire de cellule. Le test natif exécute
les deux chemins sous Clang C11 à `-O2` avec UBSan fatal. Une allocation
dans le bras réutilise l'unique slot du pool. Un second drop du résultat
et un bras `_` ajouté après Some et None sont refusés.

Les 3 tests ciblés passent. Une mutation qui supprime le nettoyage
de la charge optionnelle provoque `pool capacity exceeded` dans le
bras quand le pop a produit Some. Aucun nouveau modèle indépendant.
Les 58 tests filtrés sur match ont passé avant l'ajout du bras unique.
La régression après cet ajout tourne dans
`/tmp/crust-ve3-wildcard-regression.log`. Le transfert descendant
du résultat et le transport interfonction restent ouverts.

## Déplacement local et transfert descendant du résultat de pop

`let moved = <- saved;` conserve la garde et la provenance du résultat
et invalide la liaison initiale. `moved ->;` à l'entrée du bloc rattache
le nettoyage de la charge éventuelle à l'enfant direct. Une seconde
entrée explicite permet de poursuivre vers le petit-enfant.

Le test natif couvre Some, None et un résultat statiquement vide sous
Clang C11 à `-O2` avec UBSan fatal. Le pool d'un slot peut servir à
nouveau après le match et le handle est détruit une seule fois. Le
test refuse le saut de scope, la réutilisation des deux anciens accès
et un reset avant la consommation. Une mutation supprimant le contrôle
du parent direct accepte le saut et fait échouer le test. Aucun
nouveau modèle indépendant. Le retour du résultat entier vers le parent
et le transport entre fonctions restent ouverts.

Les quatre tests ciblés sur le résultat local de pop passent. La
régression complète de cette version tourne dans
`/tmp/crust-ve3-option-down-regression.log`.

## Réception du résultat de pop depuis un bloc enfant

Le `<- saved` final d'une expression bloc transfère le résultat entier
vers son receveur. Le bilan de sortie déplace le nettoyage éventuel sans
modifier le discriminant ni la garde. Le test sous Clang C11 à `-O2`
avec UBSan fatal couvre deux receveurs successifs, Some, None et un
résultat statiquement vide. Il vérifie la destruction unique et le
réemploi du slot. Le compilateur refuse un pool trop court, un reset
avant consommation, le point-virgule final et un receveur inutilisé.
Le test descendant vérifie aussi qu'un drop de None connu requiert
un transfert explicite depuis le parent.

Une mutation qui retire le résultat optionnel du bilan détruit son
handle dans l'enfant et échoue à la vérification du programme valide.
Aucun nouveau modèle indépendant. La restauration de l'accès initial
sans nouveau receveur, les résultats de branche et le transport
interfonction restent ouverts. La régression complète tourne dans
`/tmp/crust-ve3-option-up-regression.log`.

## Restauration de l'accès initial au résultat de pop

Dans un bloc ordinaire, `saved ->;` suivi d'un marquage `<- saved;`
restitue l'accès initial au parent si le résultat importé est encore
disponible au bilan. Un déplacement local conserve l'identité de cet
import. Pour None connu, le compilateur suit le résultat même sans
cellule à nettoyer. Une réception dans une nouvelle variable conserve
l'ancien accès invalide.

Les 6 tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le nouveau test vérifie l'adresse du handle, sa destruction unique,
le retour de None connu et le refus d'un reset prématuré. Il refuse
aussi le double marquage et la réutilisation après consommation ou
réception sous un nouveau nom. Une mutation qui restaure un None
marqué même après son drop fait échouer le test. Aucun nouveau modèle
indépendant. Les résultats de branche et le transport interfonction
restent ouverts.

Les tests du noyau sur cette version tournent dans
`/tmp/crust-ve3-option-restore-core.log`.

## Résultat de pop à la jonction d'une expression if

La branche peut produire `<- saved` ou `<- v.pop()`. Le C transmet
le couple discriminant et handle de la branche exécutée. Les sources
possibles sont réunies dans le vérificateur et la garde du receveur
suit le discriminant réel.

Sous Clang C11 à `-O2` avec UBSan fatal, le test exécute un `else if`
avec Some issu de chacun de deux pools et un chemin None. Il vérifie
le match et le drop, le réemploi des slots et la destruction unique.
Le compilateur refuse un reset prématuré de chacun des pools et un
bras de type différent. Une mutation qui arme la garde du receveur
indépendamment du discriminant déclenche UBSan lors du drop de None.
Aucun nouveau modèle indépendant. Le passage entre fonctions et les
résultats de boucle restent ouverts. Les 133 tests du noyau ont passé
sur la version précédente.

Les sept tests ciblés sur le résultat de pop passent. La sélection
des tests de régression if tourne dans `/tmp/crust-ve3-option-if-regression.log`.

## Résultat de pop aux sorties de boucle

`break <- kept;` et `break <- v.pop();` transmettent le résultat
au receveur de `loop`. Le résultat contient le discriminant et la
provenance du handle éventuel. `continue` nettoie le résultat
abandonné dans l'itération avant de reprendre.

Le test natif sous Clang C11 à `-O2` avec UBSan fatal reprend une
itération sur un pool d'un seul slot, puis exerce les sorties Some
et None. Il vérifie les destructions et le réemploi. Il refuse un
pool qui ne survit pas à la boucle, un accès extérieur déplacé
sans transfert, un reset prématuré et des types de sortie différents.
Une mutation qui saute le nettoyage avant `continue` provoque
`pool capacity exceeded`. Aucun nouveau modèle indépendant.
La régression des boucles tourne dans
`/tmp/crust-ve3-option-loop-regression.log`. Le transport entre
fonctions reste ouvert.

## Retour du résultat de pop par contrat de fonction

La signature `-> <- Option<A<Int>>` expose un retour transféré. Le
contrat décrit les sources possibles du handle. Le C transmet le
discriminant et le pointeur, puis réarme chez l'appelant la garde
qui correspond à Some.

Le test sous Clang C11 à `-O2` avec UBSan fatal passe par deux fonctions
et couvre un retour anticipé de Some et un retour final de None.
Il vérifie l'identité du handle, sa destruction unique et le refus
d'un reset prématuré ou d'une provenance issue d'un pool local.
Retirer la provenance du contrat fait échouer la vérification.
Aucun nouveau modèle indépendant. Les 61 tests de boucle passent
sur la version précédente. Les paramètres transférés de type
Option<A<Int>> et les résultats non Copy de replace et try_push
restent ouverts.

Les neuf tests ciblés sur le résultat de pop passent. La régression
des appels modulaires tourne dans `/tmp/crust-ve3-option-call-regression.log`.

## Paramètre transféré de type Option<A<Int>>

Un paramètre `saved: -> Option<A<Int>>` reçoit le discriminant,
la provenance et la responsabilité de nettoyer le handle éventuel.
L'argument explicite invalide le nom source. Le handle reste protégé
pendant l'évaluation des arguments suivants.

Le test sous Clang C11 à `-O2` avec UBSan fatal transfère un Some nommé
et un None produit par une expression d'argument. La fonction relais
rend l'option entière à son appelant. Le test vérifie l'adresse, une
seule destruction et le réemploi du slot. Il refuse le passage sans
flèche, la réutilisation du nom, le saut de scope et un reset pendant
l'évaluation d'un argument suivant. La mutation qui omet la protection
de l'argument est détectée. Aucun nouveau modèle indépendant.
Les 28 tests d'appels modulaires ont passé sur la version précédente.
Les formes locales non Copy de replace et try_push restent ouvertes.

Sur cette version, les dix tests ciblés sur le résultat de pop et les
28 tests d'appels modulaires passent.

## Résultats locaux non Copy de replace et try_push

Une liaison `let saved = <- v.replace(...);` ou
`let saved = <- v.try_push(...);` évalue l'opération à la déclaration.
Elle conserve le résultat indépendamment des opérations suivantes
sur le vecteur. Un `match (-> saved)` consomme le résultat, et `drop`
ou la fin de bloc détruit son handle éventuel. La garde de try_push
est armée pour Err.

Les deux tests natifs passent sous Clang C11 à `-O2` avec UBSan fatal.
Le premier vérifie les deux issues de replace, l'identité après
destruction du vecteur et le refus des resets et copies prématurés.
Le second vérifie un succès puis un vecteur plein, le maintien de
la longueur, l'identité du handle restitué et le réemploi du slot.
La mutation inverse la garde de try_push et provoque un nettoyage
prématuré. Aucun nouveau modèle indépendant. La régression des
vecteurs de handles tourne dans `/tmp/crust-ve3-buffered-exchange-regression.log`.

La provenance du résultat local de replace reste une union au
sein des bras nommés. Les transferts de ces Result entre scopes et
fonctions ainsi que leur jointure comme valeurs restent ouverts.

## Provenance par bras et transferts de bloc des résultats locaux

Pour un résultat de replace conservé, les deux provenances protègent
le résultat avant le match. Ok récupère la provenance de l'ancienne
case et Err celle du handle entrant. Le déplacement local et les
transferts entre blocs préservent les deux entrées. La provenance
des cases du vecteur reste conservatrice après une opération dont
l'issue est inconnue.

Sous Clang C11 à `-O2` avec UBSan fatal, le nouveau test passe par un
enfant puis revient dans un nouveau receveur. Il détruit le vecteur
et vérifie dans chaque bras qu'un reset du pool disjoint réussit.
Le reset du pool du handle et la réutilisation de l'ancien nom sont
refusés. Remplacer les deux entrées par leur union fait échouer le
test. Aucun nouveau modèle indépendant. La régression élargie
tourne dans `/tmp/crust-ve3-exchange-provenance-regression.log`.
Les jonctions de Result et leur passage entre fonctions restent ouverts.

## Jonctions if et loop des résultats locaux de vecteur

Le receveur réunit les sources de Ok entre elles et celles de Err
entre elles. Le C reçoit le résultat de la branche exécutée. Pour
try_push, seul Err arme la garde du receveur. Le compilateur vérifie
le même type sur chaque chemin qui atteint le receveur.

Le test exécute sous Clang C11 à `-O2` avec UBSan fatal les quatre
combinaisons de branche et d'issue pour if et loop. Il vérifie les
resets disjoints après la destruction du vecteur et le refus du reset
du pool du second chemin. Une mutation qui inverse Ok et Err fait refuser le reset disjoint
dans les deux formes. Un test de try_push
vérifie aussi le drop d'un succès reçu après un if. Aucun nouveau
modèle indépendant. Les 58 tests de vecteurs ont passé sur la version
précédente. La régression des boucles tourne dans
`/tmp/crust-ve3-exchange-loop-regression.log`.

Le passage du Result entier entre fonctions reste ouvert. Un
contre-exemple avec des pools injectés montre aussi que le suivi
historique des insertions peut encore refuser un reset disjoint après
la destruction du vecteur local. Le même exemple sans reset passe.

Les 14 tests de résultats conservés passent. Une mutation limitée
au vérificateur concret, qui écarte le second chemin, survit au test
car l'analyse des contraintes refuse déjà le reset avant cette étape.
Ce test ne mesure donc pas isolément cette perte de provenance dans
le vérificateur concret.

## Retour des Result non Copy par contrat

Les signatures `-> <- Result<A<Int>, A<Int>>` et
`-> <- Result<(), A<Int>>` décrivent un résultat transféré. Le
contrat publie les provenances possibles séparément pour Ok et Err.
Le backend vérifie ces provenances contre les retours du corps et
le receveur reprend la responsabilité du nettoyage.

Le nouveau test sous Clang C11 à `-O2` avec UBSan fatal vérifie un
retour anticipé et un retour final de replace par une fonction
relais. Il accepte le reset du pool disjoint chez l'appelant et
refuse le reset du pool du handle ou le retour depuis un pool
local. Il vérifie aussi le nettoyage d'un try_push réussi après
retour et le réemploi du slot. Une mutation qui inverse les bras
du contrat est détectée par le vérificateur. Aucun nouveau modèle
indépendant. Les 61 tests de boucle ont passé sur la version
précédente. Le transfert de ces Result en paramètre et le retour
interfonction de Err à capacité pour try_push restent à vérifier.

Les 15 tests ciblés et les 28 tests d'appels modulaires passent sur
la version du retour de Result.

## Paramètres transférés pour les Result de vecteur

Les paramètres `-> Result<A<Int>, A<Int>>` et `-> Result<(), A<Int>>`
reçoivent le résultat entier. Le contrat d'un relais désigne chaque
charge par son bras d'origine. L'évaluation d'un argument suivant
protège toujours le handle éventuel du Result déjà préparé.

Les 16 tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le test à capacité remplit un vecteur de 131 072 handles puis vérifie
que Err traverse le retour et un paramètre relais. Le handle garde
son adresse, est détruit une seule fois et libère son slot. Le
compilateur refuse un reset pendant l'évaluation d'un autre argument,
un transfert au mauvais type et la réutilisation du nom consommé.
Une mutation qui inverse les deux bras dans le contrat du relais
est rejetée. Aucun nouveau modèle indépendant.

La découverte complète antérieure sur la version du transfert montant
de pop a passé 1 198 tests. La découverte de la version courante tourne
dans `/tmp/crust-ve3-exchange-argument-full.log`. La précision du reset
sur des pools injectés après destruction d'un vecteur reste ouverte.

## Reset d'un pool injecté après le nettoyage du vecteur local

L'analyse des contraintes rattache les insertions d'un vecteur local
identifié à ce vecteur. Elle retire cette protection après son drop
lorsqu'aucun autre accès suivi ne peut le désigner, ou à la sortie
du bloc lorsque le vecteur disparaît. Les insertions dont le porteur
reste ambigu conservent le suivi conservateur.

Le test sous Clang C11 à `-O2` avec UBSan fatal couvre Ok et Err avec
des pools injectés, après drop explicite et après break. Il vérifie
qu'un reset du pool disjoint passe et que le reset du pool du handle
ou d'un pool encore utilisé par le vecteur est refusé. Revenir au
suivi historique sans porteur fait échouer les deux variantes.
Aucun nouveau modèle indépendant. Les sélections de régression
sont consignées dans `/tmp/crust-ve3-live-vector-constraints.log`
et `/tmp/crust-ve3-live-vector-foundations.log`.

Les 27 tests de contraintes et les 17 tests ciblés sur les résultats
conservés passent sur cette version.

## Bras résiduel des Result de vecteur nommés

Dans un match consommant, un bras `_` peut couvrir le résultat
restant après Ok ou Err. Le bras libère la charge ignorée avant
son corps et consomme aussi un succès sans handle. Un bras
résiduel après les deux variantes est refusé.

Sous Clang C11 à `-O2` avec UBSan fatal, le test exerce les deux
positions du bras résiduel pour replace. Il réutilise immédiatement
le slot de la charge ignorée et vérifie le refus d'une seconde
consommation. Il couvre aussi le succès de try_push, dont le
handle reste dans le vecteur jusqu'à sa destruction. Une mutation
qui omet le nettoyage provoque `pool capacity exceeded` dans les
deux positions. Aucun nouveau modèle indépendant. Cette passe
couvre la forme nommée `match (-> saved)`. Les formes immédiates
`match <- v.replace(...)` et `match <- v.try_push(...)` conservent
leur restriction aux deux bras explicites.

Les 18 tests ciblés sur les résultats conservés passent sur cette
version.

## Bras résiduel et unique des matchs immédiats

Les matchs immédiats sur pop, replace et try_push appliquent
l'exhaustivité F2. Un bras `_` couvre les variantes restantes
et détruit le handle ignoré avant son corps. La publication dans
le vecteur garde la distinction entre succès et échec. Les
diagnostics existants vérifient encore le transfert explicite et
refusent un bras résiduel inaccessible.

Le nouveau test sous Clang C11 à `-O2` avec UBSan fatal couvre un
try_push réussi, les deux issues de replace, et pop sur un vecteur
plein puis vide. Le corps du bras réutilise des pools d'un slot.
Le test a également révélé que le compilateur tentait d'utiliser
le nœud de résultat d'un match immédiat comme clé de liaison.
Le nettoyage des noms internes se limite désormais aux déclarations.
Une mutation qui saute la destruction du handle ignoré provoque
`pool capacity exceeded`. Aucun nouveau modèle indépendant.
La régression des vecteurs de handles est en cours dans
`/tmp/crust-ve3-immediate-wildcard.log`.

## Handle sélectionné par une expression de match immédiat

Une expression `match <- v.replace(...)` peut transmettre le handle
du bras atteint à son receveur avec `<- item`. La jonction transmet
la valeur déjà préparée par chaque bras et garde le nettoyage dans
le scope du receveur. Le vecteur peut ensuite être détruit.

Le test natif sous Clang C11 à `-O2` avec UBSan fatal couvre Ok et Err.
Il compare l'adresse du résultat à celle de l'ancienne case ou de
l'entrant, puis lit le handle après destruction du vecteur. Il refuse
un reset de chaque provenance possible et le mélange d'un handle et
d'un Int. Une mutation qui applique au résultat interne les restrictions
d'une expression de branche ordinaire reproduit le refus du transfert.
Les deux tests ciblés passent. Aucun nouveau modèle indépendant.
La sélection élargie des matchs tourne dans
`/tmp/crust-ve3-immediate-match-value.log`.

## Lecture externe bornée depuis Crust

`Vector<u8>.read_fd(fd)` reçoit un descripteur POSIX Int. Le
résultat choisi pour le prototype est `Result<Int, ReadError>`
avec le nombre d'octets reçus dans Ok et les variantes EndOfStream,
CapacityExceeded et Io. Le code système détaillé reste dans le
runtime. Une lecture est bornée par l'espace disponible et INT_MAX
pour représenter le nombre d'octets dans Int. L'accès en écriture
est vérifié avant l'appel synchrone.

Le test natif sous Clang C11 à `-O2` avec UBSan fatal passe par une
fonction recevant un emprunt mutable. Il couvre trois octets, un
descripteur invalide, la fin du flux et la capacité exacte d'une
région de 1 Mio. Il vérifie les longueurs publiées et le refus
d'un accès pendant un emprunt partagé encore utilisé. Ajouter
un octet non reçu à la longueur fait échouer le test. Aucun
nouveau modèle indépendant. La régression du runtime de croissance
est consignée dans `/tmp/crust-ve4-read-runtime.log`.

Le test Crust ciblé et les 18 tests du runtime de croissance passent.

## Réservation du vecteur pendant la préparation de read_fd

Le contre-exemple `v.read_fd(close(-> v))` était accepté alors que
l'argument pouvait détruire le vecteur avant la lecture. Le compilateur
réserve maintenant le receveur pendant l'évaluation du descripteur,
comme pour les autres opérations sur le vecteur. L'analyse de
contraintes vérifie aussi l'usage du receveur après cette évaluation.

Les deux tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le test ajoute un reset de pool disjoint dans l'argument et refuse
le même reset si le vecteur provient de ce pool, ainsi que le
transfert du receveur. Supprimer la vérification d'usage après
l'argument fait accepter le reset aliasé par contrat. Aucun nouveau
modèle indépendant. Les 27 tests de contraintes passent. La
découverte complète antérieure sur la version du transfert de Result
en paramètre a passé 1 209 tests.

## Dernier usage du receveur après les arguments des méthodes de vecteur

Le vérificateur modulaire acceptait `v.remove(clear(p))` avec un
pool `p` qui contenait le vecteur. L'analyse des contraintes
retenait la consultation initiale du receveur, puis le reset dans
l'argument, sans enregistrer l'usage du vecteur par l'opération.
Elle vérifie maintenant cet usage après l'évaluation des opérandes.

Les tests natifs sous Clang C11 à `-O2` avec UBSan fatal exercent
remove, l'indexation, replace et push. Les quatre opérations
acceptent le reset disjoint et refusent le reset du pool du
receveur par contrat. Omettre l'usage final fait accepter les
quatre contre-exemples. Les trois tests ciblés et les 27 tests
de contraintes passent. Aucun nouveau modèle indépendant.

## Dernier usage du receveur UTF-8 après les arguments

Le vérificateur modulaire acceptait `s.replace_byte(clear(p), 0x61)`
lorsque `p` contenait le String. L'analyse des contraintes vérifie
maintenant l'usage final du receveur des opérations UTF-8 qui
évaluent un indice, une borne ou un autre argument.

Le test sous Clang C11 à `-O2` avec UBSan fatal couvre replace_byte,
la découpe et char_at sur la vue empruntée. Les trois scénarios
acceptent un pool disjoint et refusent un pool aliasé. Supprimer
l'usage final fait accepter les trois contre-exemples. Aucun nouveau
modèle indépendant. La sélection String est consignée dans
`/tmp/crust-string-operand-regression.log`.

Les 14 tests de la sélection String passent sur cette version.

## Adresse de case de tranche pendant l'évaluation du RHS

Le vérificateur modulaire acceptait `view[0] = clear(p)` lorsque
le reset de `p` pouvait libérer la tranche. Une expression de
lecture produit un scalaire copié. Une affectation, elle, conserve
l'adresse de la case jusqu'à l'écriture. L'analyse des contraintes
vérifie la provenance de cette adresse après le RHS.

Le test sous Clang C11 à `-O2` avec UBSan fatal accepte un reset
disjoint et vérifie la nouvelle valeur de la case. Il refuse le
même reset sur le pool de la tranche, tout en acceptant le retour
d'une valeur déjà copiée avant reset. Une mutation qui perd la
provenance de l'adresse fait accepter le contre-exemple. Aucun
nouveau modèle indépendant. La régression des tranches tourne
dans `/tmp/crust-ve5-slice-write-regression.log`.

Les 15 tests de la sélection des tranches passent sur cette version.

## Références contenues dans les arguments d'un appel imbriqué

Le vérificateur modulaire pouvait accepter un reset dans un
argument suivant alors qu'un tableau de références déjà préparé
désignait des allocations du pool. L'analyse des contraintes
vérifie désormais les cibles du tableau à l'entrée de l'appel,
en parcourant aussi les lignes imbriquées.

Le test natif sous Clang C11 à `-O2` avec UBSan fatal couvre
un tableau copié, un tableau emprunté et un tableau de lignes
contenant des références. Dans les trois cas, un pool disjoint
est accepté et le pool des cibles est refusé. Une mutation qui
omet ce contrôle fait accepter les trois contre-exemples.
Aucun nouveau modèle indépendant. Les régressions des tableaux
fixes et des lignes imbriquées tournent dans
`/tmp/crust-array-call-lifetime-fixed.log` et
`/tmp/crust-array-call-lifetime-nested.log`.

## Passage de None connu dans un corps de fonction

Le contrat accepte une option vide préparée dans un corps de
fonction. L'absence de charge retire l'obligation de provenance
pour ce paramètre. La liaison reste consommée par le transfert.

Le test natif sous Clang C11 à `-O2` avec UBSan fatal vérifie un
None obtenu par retour d'appel et un None obtenu par pop direct.
Il passe les deux par un relais, puis les consomme avec match ou
drop. Seuls les deux vecteurs sont détruits. Réutiliser un nom
déplacé reste refusé. Rétablir l'exigence d'une allocation fait
échouer le test. Aucun nouveau modèle indépendant. Les onze tests
de pop conservé passent. La passe précédente sur les arguments a
aussi passé 68 tests de tableaux fixes et 22 de lignes imbriquées.

## Résultat de vecteur produit directement en fin de bloc

Une expression bloc peut terminer par `<- v.pop()`,
`<- v.replace(...)` ou `<- v.remove(...)`. Le bilan transfère
le résultat vers son receveur et vérifie que le pool survit.
Le parseur exige une position finale sans point-virgule.

Le test sous Clang C11 à `-O2` avec UBSan fatal vérifie l'adresse
de l'ancien handle de replace, les issues Some et None de pop
et la valeur extraite par remove. Il refuse le point-virgule et
un pool créé dans le bloc. Omettre le transfert de Result dans
le bilan fait détruire le handle dans l'enfant et échoue à la
vérification. Aucun nouveau modèle indépendant. La sélection
élargie est consignée dans `/tmp/crust-ve3-direct-block-results.log`.

Les 20 tests de la sélection passent sur cette version.

## Annotations locales des résultats non Copy de vecteur

Le receveur local peut préciser le type exact d'un Option ou
d'un Result de handles. Le compilateur distingue
`Option<A<Int>>`, `Result<A<Int>, A<Int>>` et
`Result<(), A<Int>>`, indépendamment du discriminant runtime.
L'annotation n'affecte ni le transfert ni le nettoyage.

Les tests sous Clang C11 à `-O2` avec UBSan fatal couvrent les
annotations de Some, None, replace et try_push. Le remplacement
d'un type de charge par un type incompatible est refusé. Une
mutation qui retire la comparaison accepte les deux contre-exemples.
Aucun nouveau modèle indépendant. La régression est consignée dans
`/tmp/crust-ve3-result-annotations.log`.

Les 20 tests de la sélection passent sur cette version.

## Subdivision d'une tranche mutable

Le prototype accepte `slice.split_at_mut(i)` sur une tranche
mutable, avec la même liaison à deux noms que pour un vecteur.
Les nouvelles moitiés conservent leur ascendance. Une moitié
du premier split reste disjointe des deux sous-tranches de
l'autre côté. Le parent direct reste suspendu jusqu'au dernier
usage de ses enfants.

Le test natif sous Clang C11 à `-O2` avec UBSan fatal écrit dans
trois zones, dont deux sur une subdivision du front descendant.
Il vérifie la reprise des accès, le refus de reset et d'écriture
via le parent encore emprunté, ainsi qu'une borne hors tranche.
Il renvoie aussi une sous-tranche depuis une fonction et utilise
l'autre moitié chez l'appelant. Effacer l'orientation du front
est détecté. Aucun nouveau modèle indépendant. La régression
tourne dans `/tmp/crust-ve5-subsplit-regression.log`. Le retour
groupé des deux moitiés reste ouvert.

## Retour groupé des deux moitiés de split_at_mut

La notation retenue pour le prototype est
`-> (&mut [Int], &mut [Int])` et son équivalent pour u8.
Le receveur déstructure avec `let (mut left, mut right) = ...;`.
Le contrat transmet la provenance du stockage. Le receveur
reconstruit deux emprunts disjoints pour les champs de VectorSplit.
La paire est réservée à ce résultat de séparation et à son relais.

Sous Clang C11 à `-O2` avec UBSan fatal, le test Int transmet les
deux moitiés à travers deux appels, écrit dans chacune, puis
réutilise le vecteur. Il refuse sa mutation ou son reset tant que
les vues servent et le retour depuis un vecteur local. Le test u8
écrit les deux côtés et valide le texte résultant. Supprimer la
disjonction à la réception fait refuser le programme valide.
Aucun nouveau modèle indépendant. Les 19 tests de tranches et
splits passent. La découverte antérieure sur la protection du
receveur des méthodes de vecteur a passé 1 216 tests.

## Jonction conditionnelle des paires de tranches

Une expression if peut produire une paire issue de split_at_mut
dans chaque branche qui continue. Le C sélectionne la paire entière.
Le vérificateur réunit les racines possibles et conserve la disjonction
des moitiés reçues. Le même résultat peut être rendu à l'appelant.

Sous Clang C11 à `-O2` avec UBSan fatal, le test exerce les deux
choix de vecteur en liaison locale et via une fonction. Les deux
écritures visent le même vecteur choisi, et le vecteur non choisi
reste intact. Le reset de chacune des sources possibles et le
retour d'une paire issue d'un vecteur de branche sont refusés.
Une mutation qui émet deux fois la moitié gauche est détectée.
Aucun nouveau modèle indépendant. La régression des tranches
tourne dans `/tmp/crust-ve5-pair-if.log`. Les paires ne sont pas
encore prises en charge comme résultats de break.

## Paire de tranches comme résultat d'une boucle

`break v.split_at_mut(i);` transmet la paire au receveur de loop.
Les racines de tous les chemins de sortie sont protégées. La
paire de la branche exécutée garde ses deux moitiés disjointes.
Les vues d'une itération abandonnée se terminent avant continue.

Sous Clang C11 à `-O2` avec UBSan fatal, le test reprend une
itération, puis vérifie deux sorties qui désignent des vecteurs
distincts. Il refuse le reset de chacune des sources possibles,
une sortie d'un autre type et une paire empruntée à un vecteur
créé dans l'itération. Inverser les moitiés dans le C d'un break
fait échouer le test. Aucun nouveau modèle indépendant. Les 20
tests de tranches et splits de la version précédente passent.
La régression des boucles tourne dans
`/tmp/crust-ve5-pair-break-loop.log`.

## Sélection d'une paire de tranches par match

Un match sur un enum peut produire une paire de tranches dans
chaque bras continuant. Le code C choisit la paire entière. Le
compilateur conserve les racines possibles et la disjonction
des deux vues. Les formes consommante, partagée et mutable
sont couvertes quand les bras produisent directement une
séparation ou appellent une fonction qui en retourne une.

Sous Clang C11 à `-O2` avec UBSan fatal, le test choisit chacun
de deux vecteurs par contrat de fonction. Il vérifie les deux
écritures dans le vecteur choisi et le refus d'un reset prématuré.
Une mutation qui duplique une moitié est détectée dans les trois
modes. Aucun nouveau modèle indépendant. Les 61 tests de boucle
ont passé sur la version précédente. La régression élargie des
matchs tourne dans `/tmp/crust-ve5-pair-match.log`.

## Paire de tranches en résultat de bloc

Un bloc expression peut fournir directement une paire de
split_at_mut ou appeler une fonction qui en fournit une.
Le stockage des deux moitiés doit survivre au bloc. Le receveur
déstructure la paire et hérite de ses deux emprunts disjoints.

Sous Clang C11 à `-O2` avec UBSan fatal, le test calcule l'indice
dans le bloc, transmet la paire et vérifie les deux écritures.
Il refuse une mutation du vecteur tant que les vues servent,
une séparation sans receveur et la sortie depuis un vecteur
local même lorsque les deux vues restent inutilisées. Omettre
le contrôle de durée de vie fait accepter ce dernier cas.
Aucun nouveau modèle indépendant. La sélection des paires
est consignée dans `/tmp/crust-ve5-pair-block.log`.

Les cinq tests de paires passent. Les 64 tests de la sélection des
matchs ont passé sur la version précédente.

## Stockage local d'emprunts partagés dans Vector<&Int>

Un Vector<&Int> commence vide. push copie une référence partagée
vers une allocation Int et l'indexation récupère une référence
vers la cible. Les cases occupent des pointeurs dans le runtime
et leur destruction libère le stockage du vecteur. Le vérificateur
suit les cibles empruntées pour les emprunts actifs, les sorties
de scope et les contrats de reset.

Sous Clang C11 à `-O2` avec UBSan fatal, le test compare l'adresse
originale à celle obtenue par indexation et lit la cible après
drop du vecteur. Il exerce aussi le retour d'une référence par
contrat depuis un vecteur local. Le reset disjoint est accepté
et les resets, drops, mutations ou insertions incompatibles sont
refusés. Une mutation qui détruit les cibles depuis le runtime
fait échouer le test. Aucun nouveau modèle indépendant. La
régression des vecteurs tourne dans `/tmp/crust-ve1-ref-vector.log`.

Ce premier sous-ensemble couvre la construction, push, len,
l'indexation et le nettoyage de Vector<&Int> local. Le passage
du vecteur entier entre fonctions, les emprunts mutables et les
autres opérations de réarrangement restent ouverts.

## Extraction dans Vector<&Int>

`remove(i)` retire une case, décale les suivantes et restitue
une référence partagée vers la cible. `*v[i]` lit directement
la cible d'une case. Le vérificateur conserve encore une union
conservatrice des cibles du vecteur après remove.

Les deux tests ciblés passent sous Clang C11 à `-O2` avec UBSan
fatal. Le nouveau test vérifie l'ordre, la longueur, l'adresse,
le refus du reset pendant l'usage du résultat et le diagnostic
d'indice hors bornes. Remplacer l'extraction par une lecture
fait échouer le test. Aucun nouveau modèle indépendant. Les 84
tests de vecteurs ont passé sur la version de l'insertion.
La découverte précédente du retour groupé de paires a passé
1 223 tests. Le suivi précis des cibles restantes, les autres
réarrangements et le passage de ces vecteurs restent ouverts.

## Suivi par case des cibles de Vector<&Int>

Quand les positions sont connues, une lecture littérale sélectionne
les cibles de la case et remove retire sa contribution aux emprunts
du vecteur. À indice dynamique, les cases adjacentes fournissent
les alternatives possibles après décalage. Quand la longueur ou
l'identité du porteur est ambiguë, le suivi conserve une union.

Les trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan
fatal. Le nouveau scénario modifie la cible retirée puis lit le
vecteur, et exerce aussi le reset de son pool et le réemploi.
Le scénario par contrat refuse le reset de la cible encore dans
le vecteur et accepte celui de la cible retirée après sa dernière
lecture. Conserver les anciennes dépendances fait refuser le cas
valide et la mutation est détectée. Aucun nouveau modèle indépendant.

## Prêt partagé de Vector<&Int> à une fonction

Le paramètre partagé expose les cibles des cases dans le contrat.
Le retour de l’une de ces références conserve ses cibles et leurs
réservations sans retenir le vecteur lui-même. Un relais transmet
la contrainte de séparation entre le pool réinitialisé et les pools
des cibles encore utilisées.

Deux scénarios natifs passent sous Clang C11 à `-O2` avec UBSan
fatal. Le premier conserve l’adresse après deux appels et la
destruction du vecteur. Il refuse le reset de chacun des deux pools
cibles dans l’appel, le reset ou le drop avant le dernier usage du
retour et la mutation via le paramètre partagé. Le second permet
un reset après la dernière lecture dans la fonction et le refuse
si l’appelant relit ensuite le vecteur.

Deux mutations en copies temporaires ont été détectées. Omettre
la propagation de la source des cases dans le relais retire la
contrainte attendue. Remplacer la cible retournée par le vecteur
fait échouer la vérification du corps. La première mutation
survivait au scénario natif seul, d’où le contrôle supplémentaire
du contrat inféré. Les 86 tests du lot précédent sur les vecteurs
et fondations ont terminé avec succès. Aucun modèle indépendant
n’a été ajouté pour ce changement.

Le contrat couvre l’union des cases, même si l’appelant connaît
l’indice. Un appel qui retourne une référence à partir d’un
vecteur statiquement vide reste refusé faute de cible possible.
Les interfaces mutables ou transférées et les vecteurs de
références mutables restent ouverts.

Le lot ciblé du cycle compte 86 tests de contraintes, champs
d’emprunt, appels modulaires et vecteurs d’emprunts. Il passe,
ainsi que le test séparé sur le modèle de liste de `pop` pour
les types Copy. Ce dernier couvre le noyau du vecteur et ne
modélise pas la propagation des cibles à travers les appels.

## Indice hors limites dans Vector<&Int>

Un vecteur local dont l’inventaire est vide suit la règle VE3
et le diagnostic de bornes du runtime. Le vérificateur évalue
d’abord l’indice, puis le C émet l’arrêt prévu. Avec un inventaire
inconnu, la vérification de bornes reste dans le runtime du vecteur.

Le lot de 29 tests ciblant les bornes et les appels modulaires
passe. Sous Clang C11 à `-O2` avec UBSan fatal, les quatre scénarios
contrôlent une lecture et un remove sur un vecteur vide, un indice
hors limites sur un vecteur non vide et une lecture d’un vecteur vide
reçu par emprunt. L’effet de l’expression d’indice précède l’arrêt.
La mutation qui rétablit le rejet statique échoue sur les deux
scénarios locaux vides. Aucun nouveau modèle indépendant.

Limite maintenue pour les appels dont le contrat retourne un emprunt
et dont le vecteur réel ne fournit aucune cible. Ces appels sont
encore rejetés au moment de résoudre le résultat du contrat.

La régression complète démarrée au cycle précédent a signalé
une divergence de diagnostic pour un bloc qui tente de rendre
implicitement une allocation. Le programme était bien rejeté
avec une indication d’utiliser `<-`. Le test attend désormais
ce diagnostic. Sa réexécution ciblée passe.

## Retour d’emprunt via un vecteur statiquement vide

Un contrat de retour direct ignore une projection `.items`
démontrée vide. Si aucune autre cible de retour ne subsiste,
l’appel ne revient pas. Le C conserve l’appel et ses effets
avant le diagnostic de bornes. Une autre cible possible dans
le contrat reste disponible et son emprunt reste protégé.

Trois exécutions sous Clang C11 à `-O2` avec UBSan fatal couvrent
le retour alternatif, l’arrêt après un relais conditionnel et
l’arrêt après un appel direct. Les deux arrêts affichent la trace
de la fonction avant le diagnostic d’indice. Le reset du pool
de la cible alternative avant son dernier usage reste refusé.
Une mutation qui rétablit l’exigence d’une cible sur la
projection vide fait échouer le test. Aucun nouveau modèle
indépendant.

La preuve exploite un inventaire précisément vide. L’analyse
garde l’union des cibles quand l’inventaire est incertain.
Les retours de conteneurs qui renferment un emprunt suivent
leur vérification habituelle.

Le lot de 62 tests des retours directs, des appels modulaires
et des vecteurs d’emprunts passe. Le scénario de refus du reset
de la cible alternative a aussi été relancé séparément.

## Retour de case littérale dans Vector<&Int>

La projection d’une case littérale figure dans le résumé de
retour et traverse les relais. L’appelant résout la cible et
les réservations de cette case lorsque l’inventaire est connu.
L’indice dynamique et l’inventaire inconnu conservent l’union.

Sous Clang C11 à `-O2` avec UBSan fatal, deux relais conservent
l’adresse de la case zéro après destruction du vecteur et reset
du pool de la seconde case. Le reset du pool de la première
case est refusé avant le dernier usage de la référence retournée,
y compris via un appel. La mutation qui résout le résultat sur
toutes les cases fait refuser le scénario valide.

La précision concerne la résolution du résultat. Un reset
dans un corps générique peut encore imposer une contrainte sur
toutes les cases. Aucun modèle indépendant n’a été ajouté.

Les trois tests natifs ciblés sur les projections littérales,
dynamiques et vides passent sur l’état courant.

## Reset interne après extraction d’un prêt de case littérale

Le symbole de source de la case accompagne le prêt extrait
dans le corps de fonction. Le résumé de reset et ses relais
conservent ce symbole. À l’appel, un inventaire connu permet
de résoudre la source de la case. Un inventaire inconnu
conserve l’union des cibles.

Les trois tests ciblés passent sur l’état courant. Sous Clang
C11 à `-O2` avec UBSan fatal, un appel relayé copie la valeur
de la case zéro après le reset du pool de la case voisine.
La même opération avec le pool de la case zéro est refusée
par le contrat. Le reset d’une cible d’indice dynamique reste
refusé. La mutation qui remplace le symbole de la case par
celui du vecteur entier fait refuser le scénario valide.
Aucun nouveau modèle indépendant.

La précision porte sur la référence extraite. Un usage
ultérieur du vecteur reste soumis à la validité des cibles
qu’il contient. Les 300 tests du lot fondations et les 90 du
lot contrats et retours du cycle précédent sont terminés
avec succès.

Le lot courant de 90 tests des contraintes, retours directs,
appels modulaires et vecteurs d’emprunts passe également.

## Pop local de Vector<&Int>

`pop()` produit `Option<&Int>`. Une extraction retire la
dernière case et laisse la cible à son adresse. Le résultat
local protège cette cible jusqu’au dernier usage. Avec un
inventaire inconnu, l’analyse conserve l’union des cibles.

Les deux nouveaux tests passent sous Clang C11 à `-O2`
avec UBSan fatal. Ils couvrent Some et None, la lecture de
la case restante, le reset du pool de cette case après
destruction du vecteur, le refus de reset et de drop de
la cible extraite avant le match et le retour de l’emprunt
extrait via deux fonctions. La mutation qui supprime
le suivi de la cible dans l’option fait échouer le cas Some.
Aucun nouveau modèle indépendant.

Le lot de régression ciblé de 64 tests passe. La précédente
suite complète a terminé avec 1 échec sur 1 231 tests, le
diagnostic de transfert déjà corrigé et revérifié séparément.
Une nouvelle suite complète a démarré sur l’état courant.
Le résultat Option reste local. Les paramètres et retours
d’Option ainsi que replace et try_push restent ouverts.

## Remplacement local dans Vector<&Int>

`replace(index, référence)` produit un `Result<&Int,&Int>`
local. Le succès remplace la case et rend sa référence
précédente. Un indice invalide rend la référence entrante
et laisse les cases intactes. L’indice est évalué avant
l’entrant. Un indice dynamique conserve une union des
cibles possibles, dans le résultat et par case.

Deux exécutions sous Clang C11 à `-O2` avec UBSan fatal
vérifient les bras Ok et Err, les valeurs dans la case et
dans le résultat, et un reset disjoint après destruction
du vecteur. Les deux resets qui invalideraient le résultat
avant le match sont refusés. La mutation qui attribue la
référence entrante au résultat du succès fait refuser un
scénario valide. Aucun nouveau modèle indépendant.
Le résultat complet reste local et try_push reste ouvert.

Le lot de régression des retours directs, des appels modulaires
et des vecteurs d’emprunts passe sur 66 tests.

## Insertion conditionnelle dans Vector<&Int>

`try_push(référence)` rend `Result<(),&Int>` local. Le succès
publie la référence. Le refus à capacité maximale restitue
l’entrante dans Err et conserve les cases du vecteur.

Deux exécutions sous Clang C11 à `-O2` avec UBSan fatal couvrent
une région de 1 Mio avec zéro puis 131 072 cases avant
l’appel. Le test vérifie le discriminant, la longueur, la
première case et la référence restituée, ainsi que le refus
de reset tant que le résultat peut être utilisé. Remplacer
l’appel C par le push qui arrête à capacité fait échouer le
cas Err. Aucun nouveau modèle indépendant.

L’analyse conserve l’union des cibles possibles du vecteur
après l’appel. Elle ne sépare pas encore les inventaires
d’Ok et d’Err, et le résultat complet reste local.

Le lot de 94 tests des contraintes, retours directs, appels
modulaires et vecteurs d’emprunts passe.

## Paramètre Vector<&Int> reçu par transfert

Le vecteur reçu avec `->` peut être modifié et détruit dans
la fonction. Le contrat d’un emprunt retourné se résout sur
les cibles présentes à l’entrée, même après extraction et
destruction du vecteur. Un paramètre transféré part d’un
inventaire abstrait en union afin que des suppressions
conditionnelles ne soient pas confondues avec les indices
d’entrée.

Deux tests passent sous Clang C11 à `-O2` avec UBSan fatal.
Ils couvrent le retour après extraction et destruction via
deux appels, le réemploi du slot de vecteur, l’adresse de la
cible, le refus d’accès au vecteur déplacé et le refus de
reset de la cible. Une suppression conditionnelle peut
décaler la seconde case vers la première et garde les
deux pools protégés par le contrat. La mutation qui résout
le contrat sur l’inventaire de sortie fait échouer le scénario
d’extraction. Aucun nouveau modèle indépendant.

Les paramètres mutables sans transfert et le retour du
vecteur entier restent ouverts. Le retour d’une référence
depuis un vecteur transféré reste conservateur sur les cases
d’entrée.

Le lot de 95 tests des contraintes, retours directs, appels
modulaires et vecteurs d’emprunts a passé avant l’ajout du cas
de décalage conditionnel. Les deux cas de transfert ont été
exécutés ensemble après cet ajout.

## Retour du vecteur Vector<&Int> entier

Un retour `<- Vector<&Int>` transporte le pool du vecteur
et les dépendances des cases. La vérification compare les
dépendances de chaque état de retour à celles du contrat.
Le relais d’un vecteur vide conserve un inventaire vide.

Le scénario natif passe sous Clang C11 à `-O2` avec UBSan
fatal. Une fonction construit dans un pool injecté, puis
un relais retransfère le vecteur. La cible garde son adresse
après extraction et destruction du porteur. Les resets
des pools du porteur et de la cible avant usage, ainsi
qu’une cible locale qui tenterait de sortir avec le vecteur,
sont refusés. Le même scénario transmet un vecteur vide.
La mutation qui supprime les dépendances côté appelant est
détectée. Aucun nouveau modèle indépendant.

Un retour opaque non vide conserve une union des cibles.
L’inventaire précis des cases à travers un retour de vecteur
et les paramètres mutables sans transfert restent ouverts.

## Paramètre mutable de Vector<&Int>

Les mutations d’un vecteur de références partagées reçu par
`&mut` figurent dans le contrat et se transmettent par relais.
L’appel met à jour les dépendances de l’appelant. La vérification
du corps contrôle que chaque chemin de retour est couvert par
les cibles annoncées dans le contrat.

Le scénario sous Clang C11 à `-O2` avec UBSan fatal couvre
push par deux appels puis remove et retour de la référence.
La longueur tombe à zéro et la référence reste lisible.
Le reset avant lecture et l’insertion d’une référence trop
courte sont refusés. Supprimer le résumé de mutation fait
échouer le contrôle du corps. Aucun nouveau modèle indépendant.

Le contrat de mutation conserve une union des cibles.
Il perd l’ordre des cases et peut conserver une cible
retirée lorsque l’effet ne permet pas de l’exclure.
La suite complète précédente s’est terminée avec 1 237 tests
réussis. Le lot précédent sur les retours de vecteurs a
également terminé avec 124 tests réussis.

Le lot de 125 tests ciblés a passé avant les derniers
ajustements du suivi des cibles. Les deux régressions
natives sur la mutation et le retour du vecteur ont
été relancées après ces ajustements.

## Inventaire par case d’un vecteur de références retourné

Le contrat conserve les cases dans l’ordre quand tous les
chemins de retour ont un inventaire connu et de même
longueur. Les appels successifs résolvent cet inventaire
sur leurs arguments. Le vérificateur compare chaque case
effective aux cibles annoncées.

Les deux tests de retour ciblés passent sous Clang C11 à
`-O2` avec UBSan fatal. Après deux appels, le nouveau
scénario extrait la première case, réinitialise son pool
et relit la case restante. Réinitialiser le pool de la
case restante est refusé. Inverser l’ordre annoncé dans
le contrat fait échouer la comparaison des cibles.
Aucun nouveau modèle indépendant.

Une longueur inconnue ou variable conserve une union.
Le relais d’un paramètre transféré à inventaire abstrait
reste dans ce cas, même si son appelant connaît l’ordre.

Le lot courant de 126 tests des contrats, des champs
empruntés et des vecteurs d’emprunts passe.

## Aller-retour d’un Vector<&Int> transféré

Lorsqu’une fonction restitue le même vecteur sans écrire
ni retirer de case, son contrat conserve l’inventaire de
l’argument. Les relais propagent cette propriété uniquement
si chacun conserve l’inventaire.

Sous Clang C11 à `-O2` avec UBSan fatal, deux relais
conservent les deux cases. Le retrait de la première
permet de réinitialiser son pool et de lire la seconde.
Le reset de la cible restante est refusé. Le test négatif
distingue aussi un relais qui supprime la première case.
Il lit la case décalée, détruit le vecteur, puis tente
de réinitialiser le pool de la référence encore vivante.
La mutation qui ignore la modification faisait passer
ce reset au vérificateur. Le test renforcé la détecte.
Aucun nouveau modèle indépendant.

Un retour après modification d’un inventaire d’entrée
inconnu reste traité par union. Une nouvelle suite
complète a démarré sur l’état courant.

Le lot de 127 tests des contraintes, retours, appels
modulaires, champs et vecteurs d’emprunts passe.

## Stockage local d’emprunts mutables dans Vector<&mut Int>

`push(-> emprunt)` déplace la liaison mutable dans une case.
Le vecteur porte l’exclusivité jusqu’au dernier usage.
`<- v.remove(indice)` extrait la référence, avec un indice
littéral, un inventaire connu et des cibles disjointes des
cases restantes. La cible conserve son adresse.

Deux scénarios passent sous Clang C11 à `-O2` avec UBSan
fatal. Ils vérifient deux extractions et mutations, le reset
de chaque pool après le dernier usage, l’exclusivité avant
extraction et le retour d’un emprunt extrait depuis une
fonction. Réutiliser la liaison déplacée, lire la cible,
réinitialiser son pool ou omettre le transfert est refusé
dans les scénarios correspondants. La mutation qui traite
le prêt détenu par le vecteur comme partagé laisse passer
la lecture de la cible et est détectée. Aucun nouveau
modèle indépendant.

Les indexations par réemprunt, les extractions avec indice
dynamique, les autres opérations et les signatures du
vecteur entier restent ouvertes.

Le lot de 101 tests des contraintes, retours directs,
appels modulaires et vecteurs d’emprunts passe.
Le test de retour du prêt a été exécuté séparément.

## Réemprunt par index dans Vector<&mut Int>

`&*v[i]` et `&mut *v[i]` réempruntent la cible sans retirer
sa case. Un prêt partagé empêche la destruction ou la
mutation du vecteur. Un prêt mutable suspend aussi les
lectures par le vecteur. Le dernier usage libère ces
réservations. `*v[i]` lit la cible via un prêt partagé
limité à l’expression.

Le scénario natif passe sous Clang C11 à `-O2` avec UBSan
fatal. Il vérifie l’adresse, l’écriture par le prêt, la
reprise des lectures du vecteur, puis de la cible après
destruction du vecteur. Les variantes refusent un accès
concurrent, un reset et la destruction du porteur pendant
un prêt partagé ou mutable. Une mutation sans réservation
du porteur accepte la destruction pendant le prêt partagé.
Aucun nouveau modèle indépendant.

La réservation mutable porte encore sur le vecteur entier,
même si deux indices désignent des cases disjointes.

Le lot de 103 tests des contraintes, retours directs, appels
modulaires et vecteurs d’emprunts passe. Le refus de
destruction pendant le prêt partagé a ensuite été relancé.

## Réemprunts simultanés de cases disjointes

Une réservation de case de `Vector<&mut Int>` mémorise
l’ensemble des cibles possibles. L’accès à une autre case
est permis quand les ensembles sont disjoints. La destruction
et les mutations de structure restent réservées. L’invariant
exécutable vérifie les paires de prêts actifs, y compris
lorsque plusieurs prêts proviennent du même vecteur.

Le scénario natif sous Clang C11 à `-O2` avec UBSan fatal
garde deux prêts mutables actifs vers deux allocations du
même pool. Il modifie les deux cibles et relit les cases
après les derniers usages. Le même indice, un indice
dynamique potentiellement aliasé et la destruction pendant
les prêts sont refusés. Retirer le filtrage par cible fait
refuser le scénario valide. Aucun nouveau modèle indépendant.

Un indice dynamique qui ne permet pas de prouver la
disjonction conserve l’ensemble des cibles possibles.

## Écriture directe dans une cible de Vector<&mut Int>

`*v[i] = expression` évalue l’indice et vérifie les bornes
avant d’évaluer la partie droite. Une réservation partagée
garde la destination valide pendant l’évaluation. Le
vérificateur exige ensuite l’accès exclusif à la cible,
ce qui permet de terminer un prêt partagé utilisé pour
la dernière fois à droite.

Deux exécutions sous Clang C11 à `-O2` avec UBSan fatal
vérifient l’ordre des effets et l’arrêt hors limites avant
la partie droite. Le reset de la cible pendant l’évaluation
et la conservation d’un prêt partagé après l’écriture sont
refusés. Une mutation du C généré qui inverse l’ordre
des effets est détectée. Aucun nouveau modèle indépendant.

Le lot de 172 tests du cycle précédent a terminé avec
succès. La suite complète démarrée au cycle des retours
sans mutation a terminé avec 1 245 tests réussis. Elle
précède l’implémentation des vecteurs de prêts mutables.

Une nouvelle suite complète a démarré après l’ajout des
écritures directes.

Le lot courant de 173 tests de sûreté, contrats, champs
et vecteurs d’emprunts passe.

## Pop local de Vector<&mut Int>

`<- v.pop()` rend un `Option<&mut Int>` qui porte
l’exclusivité de la dernière case extraite. Le match
consomme l’option, et Some remet le prêt à son bras.
Abandonner l’option libère le prêt sans détruire la cible.

Sous Clang C11 à `-O2` avec UBSan fatal, les scénarios
couvrent Some, None, la modification de la cible et
l’abandon du résultat par le bras `_`. L’accès direct à
la cible et le reset de son pool avant le match sont
refusés. La réutilisation du résultat consommé est
également refusée. La mutation qui rend le prêt de
l’option partagé accepte à tort l’accès direct et est
détectée. Aucun nouveau modèle indépendant.

Le pop exige un inventaire connu et des cibles disjointes
des cases restantes. L’option mutable entière reste locale.

## Remplacement local d’une référence mutable

`<- v.replace(i, -> prêt)` rend un
`Result<&mut Int,&mut Int>`. Le succès déplace l’ancienne
référence dans Ok. L’échec conserve les cases et déplace
la référence entrante dans Err. Dans les deux cas, la
liaison entrante est consommée et le résultat porte
l’exclusivité jusqu’au match ou à son abandon.

Sous Clang C11 à `-O2` avec UBSan fatal, trois exécutions
couvrent l’indice valide, l’indice invalide et le match
immédiat. Les scénarios vérifient les valeurs de la case
et de la cible rendue, l’invalidation de la liaison
entrante et le refus d’accès direct ou de reset avant
le match. La mutation qui rend le prêt du résultat
partagé laisse passer l’accès direct et est détectée.
Aucun nouveau modèle indépendant.

Le remplacement exige un indice littéral, un inventaire
connu et la disjonction de la case extraite. Le résultat
entier reste local. Le lot précédent sur pop et les
contrats a terminé avec 131 tests réussis.

## Insertion conditionnelle d’une référence mutable

`<- v.try_push(-> prêt)` rend `Result<(),&mut Int>`. Le
résultat réserve le vecteur jusqu’au match. Ok confirme
l’insertion. Err rétablit l’inventaire précédent et donne
le prêt entrant au bras. Un résultat abandonné conserve
l’union des cibles possibles pour le vecteur.

Sous Clang C11 à `-O2` avec UBSan fatal, le test couvre
le succès avec match différé et immédiat. Pour exercer
l’échec à capacité sans créer 131 072 prêts distincts,
le test réduit à une case le budget du vecteur dans le C
généré. La routine de capacité et l’écriture restent
celles du runtime. Err rend le prêt mutable et conserve
la longueur et la première case. Les resets du pool
du vecteur ou du prêt entrant et les accès prématurés
sont refusés. Supprimer la réservation laisse passer
l’accès au vecteur avant le match. Aucun nouveau modèle
indépendant.

Le résultat entier reste local. La jonction de longueurs
différentes conserve une union des cibles. Le lot du
cycle précédent sur le remplacement et les contrats
a terminé avec 165 tests réussis.

## Lecture et écriture à travers un paramètre Vector<&mut Int>

Un paramètre `&Vector<&mut Int>` autorise la lecture de ses
cibles. `&mut Vector<&mut Int>` autorise également leur
mutation. Le contrat porte les pools des cibles à travers
les appels et relais. Les modifications de structure
exigent encore un contrat dédié.

Le scénario sous Clang C11 à `-O2` avec UBSan fatal réinitialise
un pool disjoint, écrit la cible via deux appels puis la lit
deux fois. Le reset du pool de la cible, l’écriture via
un paramètre partagé et la mutation de structure sont refusés.
La mutation qui omet le symbole de source des cases est
détectée par le contrôle du contrat inféré. Elle survivait
au test natif seul, car la contrainte sur le vecteur protège
aussi ses cibles. Aucun nouveau modèle indépendant.

Le lot de 171 tests du cycle précédent a terminé avec succès.
La suite complète lancée au cycle des écritures directes a
terminé avec 1 250 tests réussis. Elle précède l’implémentation
des dernières opérations transférantes et de ces paramètres.

## Transfert et retour du vecteur de prêts mutables entier

Un `Vector<&mut Int>` peut être reçu par `->` et rendu avec
`<-`. Le contrat conserve les cibles, l’ordre connu et
l’exclusivité. Le stockage d’un prêt injecté conserve
aussi sa filiation. Après extraction, le prêt parent
reprend au dernier usage de l’extrait.

Le scénario sous Clang C11 à `-O2` avec UBSan fatal couvre
la construction dans un pool injecté, un relais, une
extraction et la reprise du prêt parent. L’adresse reste
stable et le reset du pool libéré permet encore de lire
l’autre case. La cible locale, le reset prématuré, l’accès
à la cible ou au prêt parent et l’accès au vecteur déplacé
sont refusés. La mutation qui perd le parent lors de
l’insertion est détectée par l’invariant d’exclusivité.
Aucun nouveau modèle indépendant.

Le lot de 177 tests du cycle des paramètres empruntés a
terminé avec succès. La mutation de structure via un
emprunt injecté reste ouverte, ainsi que les extractions
qui exigent un inventaire connu.

## Insertion via un paramètre mutable Vector<&mut Int>

`push` et `try_push` mettent à jour les dépendances du
vecteur chez l’appelant, y compris à travers un relais.
Le contrat conserve le parent du prêt injecté et vérifie
que la cible survit au vecteur.

Deux tests passent sous Clang C11 à `-O2` avec UBSan fatal.
Ils couvrent push relayé, reprise du prêt parent après
destruction du vecteur, et try_push sur Ok et Err avec une
région C réduite à une case pour le second scénario.
Ils refusent une cible locale trop courte, un accès
concurrent, une seconde insertion du même prêt et un
reset prématuré. La mutation qui omet le résumé du push
est détectée par le contrôle du corps. Aucun nouveau
modèle indépendant.

Le contrat garde une union des cibles après insertion.
Il ne conserve pas encore l’ordre des nouvelles cases
ni le lien entre le résultat de try_push et l’inventaire
de l’appelant. Les extractions et remplacements via un
paramètre emprunté restent ouverts. Le lot précédent
a terminé avec 178 tests réussis. Une nouvelle suite
complète a démarré.

Le lot de 179 tests a passé sur push et les autres opérations
déjà présentes. Le cas try_push via un paramètre a été relancé
séparément avec le test de push après son ajout.

## Retour de réemprunt depuis un vecteur injecté

Le retour de `&*v[i]` ou de `&mut *v[i]` depuis un
`Vector<&mut Int>` emprunté conserve la cible et réserve
le porteur. Le contrat propage l’indice littéral à travers
les relais. Une autre case peut être réempruntée si ses
cibles sont disjointes.

Le scénario sous Clang C11 à `-O2` avec UBSan fatal couvre
le retour mutable relayé, un second prêt disjoint et le
retour partagé. Il refuse un accès à la même case, un
reset du pool du porteur et la destruction du vecteur
pendant l’un ou l’autre prêt. Le retour mutable via un
paramètre partagé est refusé. La mutation qui supprime
la réservation dans le contrat est détectée lors de la
comparaison avec le corps. Aucun nouveau modèle indépendant.

Cette résolution utilise l’inventaire d’entrée. Un retour
de case après modification de structure du porteur et le
transport du réemprunt dans un résultat agrégé restent
ouverts.

## Indices calculés et issue déterminée sur un vecteur mutable

Une extraction avec indice calculé est admise quand le
vecteur a au plus une case connue. Le succès ne peut
laisser aucune case concurrente, et l’échec conserve
le diagnostic de bornes. Un remplacement sur vecteur
vide évalue également l’indice calculé et restitue
toujours le prêt entrant.

Sous Clang C11 à `-O2` avec UBSan fatal, trois exécutions
couvrent le retrait de la seule case, l’arrêt hors limites
et le remplacement sur vecteur vide. Elles vérifient
l’évaluation unique de l’indice. Le reset pendant le prêt
extrait et l’extraction dynamique avec plusieurs cases
possibles restent refusés. Une mutation qui laisse le
prêt extrait dans l’inventaire fait échouer l’invariant
d’exclusivité. Aucun nouveau modèle indépendant.

Le lot de 181 tests du cycle précédent sur les retours
de réemprunts a terminé avec succès. Le lot courant
élargi est en cours.

## Ordre des cases après push via un paramètre

Quand tous les chemins ajoutent le même nombre de cases
en fin de vecteur, le contrat décrit ce suffixe dans
l’ordre. Un relais compose les ajouts. Si l’appelant
connaît ses cases, il peut les suivre après l’appel.
Le vérificateur compare cet inventaire au corps généré.

Sous Clang C11 à `-O2` avec UBSan fatal, le scénario
ajoute un prêt via deux appels, extrait la première case,
réinitialise son pool et lit la case ajoutée. Le reset
du pool de la case restante est refusé. Un ajout
conditionnel dont le nombre varie perd cette précision.
La mutation qui oublie l’inventaire après l’appel fait
refuser le scénario valide. Aucun nouveau modèle
indépendant.

Le lot précédent sur les indices calculés a terminé
avec 126 tests réussis. Le lot courant élargi est en cours.

## Arithmétique Int32 avec constantes immuables

Le vérificateur réutilise le calcul constant du parseur
pour les opérandes Int immuables dont la valeur est établie.
Un diviseur nul connu est refusé même si le numérateur
est inconnu. Les opérandes dynamiques restent évalués de
gauche à droite et contrôlés dans le runtime.

Le lot de 13 tests d’arithmétique et de court-circuit passe.
Il comprend le modèle de division et de reste et les
exécutions sous Clang C11 à `-O2` avec UBSan fatal. Le nouveau
test couvre une chaîne de constantes, un débordement, un
diviseur constant dans un corps de fonction, le masquage
et la réaffectation d’une variable mutable. La mutation
qui oublie les constantes manque les trois diagnostics
statiques.

La propagation se limite aux valeurs Int immuables connues
dans le corps analysé. Elle ne déduit pas la valeur d’un
paramètre ni celle d’une variable mutable à partir des
branches. Le lot de 171 tests du cycle des ajouts par
contrat a terminé avec succès.

## Constantes immuables comme indices

Un indice Int immuable connu sert à vérifier les bornes
d’un tableau à la compilation. Dans un vecteur de prêts
mutables, il permet de distinguer deux cibles et de
résoudre les effets d’un retrait ou d’un remplacement.
Les indices réellement dynamiques gardent les contrôles
du runtime et les contraintes de disjonction.

Les scénarios ciblés sous Clang C11 à `-O2` avec UBSan
fatal couvrent un indice immuable hors bornes, le
réemprunt de deux cases disjointes et un remplacement
suivi d’un retrait. Le test de disjonction refuse encore
le même indice et une variable mutable d’indice dont
la disjonction est indémontrable. La mutation qui perd
l’indice immuable fait refuser le cas valide. Aucun
nouveau modèle indépendant. La régression des tableaux
fixes et des vecteurs d’emprunts est en cours.

## Remove dynamique de prêts mutables

`<- v.remove(i)` peut maintenant retirer un prêt d’un
vecteur de plusieurs cases, y compris via un paramètre
`&mut Vector<&mut Int>`. Le prêt extrait conserve les
cibles possibles. Si elles chevauchent l’inventaire
abstrait restant, la réservation du porteur empêche
un accès concurrent jusqu’au dernier usage du prêt.
Le contrat de mutation met à jour les dépendances
du vecteur chez l’appelant.

Les deux scénarios ciblés passent sous Clang C11 à `-O2`
avec UBSan fatal. Ils couvrent le retrait local et le
retrait via fonction, la mutation de la cible extraite
et la lecture de la case restante. Le reset, le drop
et la lecture potentiellement concurrente sont refusés.
Supprimer la réservation fait échouer l’invariant
d’exclusivité. Aucun nouveau modèle indépendant.

Un chevauchement abstrait peut encore empêcher de détruire
le vecteur ou de retourner le prêt extrait. Les contrats
sur inventaire inconnu conservent l’union des cibles.
Le lot précédent sur les indices a terminé avec 85 tests
réussis. La suite complète lancée au cycle des insertions
a terminé avec 1 257 tests réussis et précède ce changement.

## Pop via un vecteur de prêts mutables injecté

`pop` est accepté sur un inventaire abstrait, y compris
à travers un paramètre mutable. Lorsque les cibles
possibles chevauchent les cases restantes, l’option
réserve le vecteur. Some transmet cette réservation
au prêt extrait. None libère l’option.

Les scénarios ciblés passent sous Clang C11 à `-O2`
avec UBSan fatal. Le relais extrait puis modifie une
cible, reprend l’accès au vecteur et exerce None sur
l’appel suivant. L’accès au vecteur avant le match est
refusé. Supprimer la réservation fait échouer
l’invariant d’exclusivité. Aucun nouveau modèle
indépendant.

La régression précédente a signalé deux assertions
devenues obsolètes après la propagation des indices
immuables et l’ouverture de remove sur inventaire
inconnu. Les tests vérifient maintenant un indice
réellement dynamique et le refus d’un reset sur
l’inventaire conservateur. Les deux cas corrigés
et le cas de pop injecté repassent. Le lot élargi
courant est en cours.

## Replace dynamique via un vecteur mutable injecté

`<- v.replace(i, -> prêt)` accepte un indice ou un inventaire
inconnu, y compris via un paramètre emprunté. Le résultat
réserve le vecteur tant que l’issue reste indéterminée.
Sur Ok, le bras reçoit l’ancienne référence et peut garder
la réservation si les cibles abstraites se chevauchent.
Sur Err, l’inventaire précédent est rétabli et le bras
reçoit la référence entrante.

Les trois tests ciblés passent sous Clang C11 à `-O2`
avec UBSan fatal. Les scénarios injectés exercent les
deux indices, modifient la cible reçue, puis relisent le
vecteur et les cibles. Un accès au porteur avant le match
et un remplacement via un paramètre partagé sont refusés.
La mutation qui omet la restauration sur Err échoue sur
l’invariant d’exclusivité. Aucun nouveau modèle indépendant.

Après un appel opaque, les inventaires ambigus restent
traités par union. Le résultat complet reste local.
Le lot précédent sur pop a terminé avec 186 tests
réussis. Le lot élargi courant est en cours.

## Indirections partagées typées dans les structures

Un champ `&Structure` occupe une case de taille pointeur.
Le calcul de disposition ne suit pas cette arête, ce
qui autorise les définitions mutuellement récursives
par référence. Les cycles de champs contenus restent
refusés. Une chaîne de références locale protège
transitivement ses cibles actives.

Le scénario sous Clang C11 à `-O2` avec UBSan fatal
vérifie les champs scalaires situés avant et après un
pointeur et parcourt deux indirections. Le reset, le
drop et la mutation de la cible transitive sont refusés.
Les déclarations de cycles directs et de cibles inconnues
sont refusées. La mutation qui coupe le suivi transitif
survivait quand la cible intermédiaire avait un drop
explicite. Le scénario négatif renforcé laisse seulement
le porteur extérieur actif et détecte la mutation,
dont une écriture qui passait à tort. Aucun nouveau
modèle indépendant.

Cette étape couvre les références partagées entre
structures locales. Les cibles avec champs mutables,
le remplacement de la référence, les signatures
interfonctions, les variantes récursives et les
indirections propriétaires restent ouverts.
Le lot précédent sur replace a terminé avec 187 tests
réussis. Le lot ciblé des structures est en cours.

## Enums récursifs par référence partagée

Une variante peut contenir `&Enum`, y compris une
référence vers son propre type. Une variante terminale
permet de construire une chaîne finie. Les matchs
imbriqués suivent les références typées et gardent
l’union des variantes des cibles après une jonction.

Les tests sous Clang C11 à `-O2` avec UBSan fatal
parcourent deux liens jusqu’à une variante terminale
et exercent les deux cibles d’un choix conditionnel.
Le reset et le drop de la cible transitive sont refusés,
ainsi que le champ récursif stocké directement.
La mutation qui ne garde que la première cible produit
une erreur de tag dans le scénario valide. Aucun
nouveau modèle indépendant.

Les références typées restent locales. Les contrats
interfonctions, les indirections propriétaires et
les références vers un type contenant des champs
mutables restent ouverts. Le lot du cycle précédent
sur les structures a terminé avec 137 tests réussis.

Le lot de 135 tests du compilateur et des deux cas d’enums
récursifs passe. La régression élargie des matchs et champs
empruntés est en cours.

## F1 — Provenance des références dans les chaînes locales aux fonctions

La construction de chaînes locales par référence partagée est admise dans
les fonctions. Le contrat suit la provenance du champ projeté à travers
les intermédiaires. La lecture d’un emprunt après un reset dans le corps
impose de séparer le pool du reset et le pool de la cible. Un emprunt partagé
détaché peut être retourné si sa cible survit au retour. La copie d’un
intermédiaire conserve cette provenance.

Trois exécutions natives donnent `7` sous Clang C11 à `-O2` avec UBSan
fatal. Cinq variantes sont refusées par le vérificateur. Elles exercent le
reset du pool de la cible dans la fonction ou chez l’appelant, le retour
d’une cible locale et le remplacement d’un champ intermédiaire emprunté.
La suppression temporaire des chemins imbriqués dans l’analyse des
contraintes laisse passer le reset interdit dans la fonction. La même
mutation dans l’analyse des résultats fait refuser le retour valide.
Les deux mutations sont détectées.

Le lot des contrats et des appels modulaires passe avec 105 tests, dont
les exigences de pool comparées à leur modèle existant. Aucun oracle
indépendant spécifique aux chaînes typées n’a été exécuté. La régression
élargie du cycle précédent sur les enums a terminé avec 200 tests réussis.
La suite complète de ce cycle est lancée, avec résultat encore à relever.

Les signatures contenant des champs typés, les indirections propriétaires
et les références typées mutables restent ouvertes. Un match imbriqué
avec retour depuis un bras sur un enum récursif local reste également
refusé. Ce chemin n’est pas couvert par les résultats sur les structures.

## F1 et F2 — Effets des méthodes sur une projection et retour de match

Le programme avec `Leaf.read` et `Other.read` révélait un refus dans
l’analyse des effets. Une projection de champ typé perdait le type de
son receveur. L’analyse récupère maintenant le type depuis la déclaration
du champ. Le contrat de l’appelant contient l’allocation sur le pool Int
injecté. La mutation qui retire cette résolution reproduit le refus du
programme valide et le test la détecte.

Un second programme construit une chaîne locale d’enum, effectue le reset
avant un match imbriqué et retourne une copie Int depuis le bras terminal.
Les deux programmes valides donnent `7` sous Clang C11 à `-O2` avec UBSan
fatal. Avec le pool de la cible à la place du pool distinct, le second
programme est refusé par le contrat de l’appelant.

Le retour d’un emprunt lié par un match depuis un porteur local reste
refusé. Le reset placé directement dans un bras de match par lecture
reste également refusé par la restriction actuelle du vérificateur.
Aucun modèle indépendant spécifique aux projections typées n’a été ajouté.

La régression ciblée passe avec 108 tests. Elle comprend les deux nouveaux
cas, le cas existant des receveurs issus du contrôle de flux, les contrats
d’appel et la comparaison des exigences de pool à leur modèle existant.

## F1 — Paramètre partagé d’une structure à références typées

Le vérificateur représente les emprunts des paramètres partagés à
structures acycliques par des chemins de champs. Le contrat de résultat
détache l’emprunt terminal du porteur et conserve le chemin vers la
cible. Les contraintes résolvent ce chemin sur les arguments réels.
Le cas ciblé exerce trois appels successifs et vérifie que le dernier
contrat conserve précisément `.leaf/.data` comme source à séparer du reset.

Sous Clang C11 à `-O2` avec UBSan fatal, le programme donne `7` avec
un pool distinct et donne aussi `7` lorsque les deux porteurs sont
détruits avant la lecture du résultat. Deux variantes qui réinitialisent
le pool de la cible sont refusées, l’une dans la chaîne d’appels et
l’autre après le retour. La mutation qui ne substitue que la première
composante du chemin a d’abord survécu au test à un seul niveau de
vérification. Le relais supplémentaire et l’assertion sur son contrat
détectent désormais la mutation.

Les signatures récursives et les signatures à liens vers des enums, les
paramètres mutables ou transférés de ce type et les retours d’agrégats
à références typées restent ouverts. Aucun modèle indépendant spécifique
aux chemins de champs n’a été exécuté.

La régression ciblée passe avec 163 tests. Elle inclut les contrats,
les exigences de pool avec leur modèle, et les champs empruntés partagés
et mutables existants. Le test du contrat renforcé par le relais a été
réexécuté séparément.

## F1 et F2 — Contrats des agrégats acycliques transférés et enums empruntés

Les paramètres empruntés en lecture ou transférés acceptent les liens
partagés acycliques, y compris entre structures et enums. Un match en
lecture peut lier un champ lu sur une structure projetée. Un match
consommant peut retourner l’emprunt terminal d’un champ imbriqué.
La résolution concrète ignore les chemins dont une variante est absente.
L’analyse de résultats élimine aussi le chemin impossible lorsque la
variante du constructeur local est connue.

Le test Clang C11 à `-O2` avec UBSan fatal lit les deux variantes, passe
les porteurs par un relais qui les consomme, puis lit les deux cibles.
La trace compte une destruction par instance. Le reset du premier pool
après le dernier usage de son emprunt conserve la lecture du second.
La spécialisation sur le constructeur terminal local conserve le retour
de l’emprunt reçu en paramètre. Deux resets prématurés sont refusés.
Les mutations qui réintroduisent les chemins impossibles dans la
résolution concrète ou dans l’analyse de résultats sont détectées.
Aucun oracle indépendant spécifique au filtrage des chemins d’enum.

Les paramètres mutables, les signatures traversant des cycles et les
retours d’agrégats à champs typés restent ouverts. La spécialisation
symbolique testée concerne la variante à la racine. La suite complète
précédemment lancée et le lot de régression de ce cycle sont en cours.

La suite complète du point de départ de ce lot a terminé avec
1269 tests réussis. Le lot ciblé de 163 tests passe pour l’extension
aux agrégats acycliques. Le test renforcé par le constructeur
terminal local a été réexécuté séparément après le correctif symbolique.

## F1 et F2 — Paramètres mutables à références acycliques

Un paramètre mutable peut recevoir un agrégat avec des liens partagés
acycliques. Les écritures scalaires et le remplacement des champs
`&Int` existants passent par les mécanismes usuels. Le relais d’appel
transmet la mise à jour du champ direct et conserve la provenance
indépendante de l’emprunt imbriqué retourné.

Sous Clang C11 à `-O2` avec UBSan fatal, le premier programme affiche
`3, 2, 7` après le reset de l’ancienne cible. Les resets prématurés
des deux cibles restantes sont refusés. La mutation qui omet
l’application de la mise à jour contractuelle réintroduit le refus du
reset valide et le test la détecte. Le second programme affiche
`7, 9, 9` avec un match mutable sur deux variantes. Il vérifie la
séparation entre le lien partagé typé et le champ mutable Int, ainsi
que le refus d’une lecture directe prématurée du second.

Le remplacement d’un lien typé, les références typées mutables, les
signatures récursives et les retours d’agrégats restent ouverts.
Aucun modèle indépendant spécifique à ces paramètres n’a été ajouté.
Une nouvelle suite complète est en cours.

## F1 — Retour transféré d’un agrégat à références acycliques

Le contrat conserve les chemins imbriqués pour l’analyse du résultat.
Le vérificateur concret attache au slot ses dépendances directes et
atteint les cibles imbriquées en parcourant ces dépendances. L’emprunt
terminal partagé reste détachable à travers la construction, le retour
transféré et les relais d’appel.

Deux programmes passent sous Clang C11 à `-O2` avec UBSan fatal. Le
premier affiche `7, 7`, détruit les deux agrégats et réutilise un pool
de capacité un. La seconde lecture survit à la destruction du porteur
intermédiaire. Le second programme affiche `7, 0` pour deux variantes
retournées et détruit chacune une fois. Le vérificateur refuse un
reset prématuré du pool terminal et la fuite d’un porteur local.
La mutation qui omet la conversion des champs imbriqués en provenance
détachée est détectée. La mutation qui ajoute les dépendances imbriquées
aux dépendances directes concrètes survit à ce scénario. Les cibles
du test restent aussi atteignables par les dépendances directes.

Aucun oracle indépendant spécifique à ces retours n’a été exécuté.
Les retours directs d’emprunts vers ces agrégats, les signatures
récursives et le remplacement des liens typés restent ouverts.
La régression ciblée du cycle précédent a terminé avec 163 tests
réussis. Le lot des contrats de ce cycle et la suite complète
lancée avant ce changement sont en cours.

Le lot de contrats et d’emprunts a terminé avec 164 tests réussis.
Le cas de retour conditionnel d’enum a été exécuté séparément.

## F1 — Retour direct d’un emprunt vers un agrégat acyclique

Les retours directs partagés et mutables acceptent les agrégats acycliques.
Les contrats propagent les champs de l’agrégat retourné. Pour un retour
détaché, ils projettent ces champs sous le chemin du porteur d’origine.
Le lien retourné peut être relayé, puis projeté à nouveau.

Trois programmes passent sous Clang C11 à `-O2` avec UBSan fatal.
Le premier affiche `7` après la destruction de trois porteurs. Les
deux variantes avec reset prématuré sont refusées, dans l’appel et
chez l’appelant. Le deuxième affiche `7, 4` et vérifie que l’accès
direct au porteur mutable est refusé avant le dernier usage. Le
troisième affiche `7, 0` à travers un retour partagé d’enum et vérifie
les destructions des deux variantes.
Supprimer la projection imbriquée dans les contraintes fait perdre
le diagnostic contractuel de séparation des pools et déplace le
refus à la vérification concrète. La supprimer dans l’analyse des
résultats fait refuser un retour valide. Les deux mutations sont
détectées par le test. Aucun oracle indépendant dédié à ces retours.

Un contre-exemple supplémentaire avec `return &link` et un porteur
alloué dans un pool local est refusé avec le diagnostic de cible non
durable. La régression élargie des contrats et la suite complète
précédente sont encore en cours.

## F1 et ST10 — Remplacement d’un lien partagé typé

L’affectation d’un champ `&T` change la cible et ses dépendances
imbriquées. Le vérificateur exige un emprunt du type exact, contrôle
la durée de vie de la cible et refuse de former un cycle de dépendances
entre allocations. Le réemprunt explicite `&*replacement` fonctionne
sur un agrégat. Le contrat propage l’écriture depuis une fonction Void
et le relais peut retourner l’emprunt terminal de la nouvelle cible.

Le test sous Clang C11 à `-O2` avec UBSan fatal affiche `9` après
destruction de l’ancien porteur et reset de l’ancien pool. Il refuse
le reset prématuré du nouveau pool et la réaffectation à une cible
locale trop courte. Le contre-exemple `Node → Edge.Next → Node`
a été accepté durant l’extension initiale. Le contrôle du graphe
le refuse maintenant. Les deux mutations, omission de ce contrôle
et perte des chemins imbriqués de la mise à jour, sont détectées.
Aucun oracle indépendant spécifique à ces écritures.

Les liens typés mutables, les contrats de types récursifs et
les indirections propriétaires restent ouverts. La régression du
cycle précédent sur les retours empruntés passe avec 164 tests.
Le lot sur le remplacement et la suite complète lancée avant
ce cycle sont encore en cours.

## ST10 — Couverture du contrat sur les sorties d’une mise à jour conditionnelle

Le vérificateur compare les cibles de chaque champ des structures
typées injectées en mutable à celles promises par leur contrat.
La comparaison couvre les retours explicites et la fin normale.
Le test conditionnel remplace le lien avant un retour anticipé sur
un chemin et conserve l’ancienne cible sur l’autre. Le relais
retourne l’emprunt terminal après la jonction.

Les deux chemins passent sous Clang C11 à `-O2` avec UBSan fatal,
avec les sorties respectives `9` et `7`. Les deux resets prématurés
sont refusés chez l’appelant. Une mutation qui réduit les cibles
possibles du champ à une seule est détectée dans le corps par
le contrôle de couverture du contrat. Aucun modèle indépendant
spécifique à ces branches n’a été exécuté.

Le lot précédent sur le remplacement de champs a terminé avec
163 tests réussis. Le lot élargi de ce cycle et la suite complète
lancée sur un instantané antérieur sont encore en cours.

## F1, F2 et ME — Effets d’une méthode sur une projection de match

L’analyse des effets donnait le type Int à toute liaison de bras.
Elle utilise désormais le type déclaré du champ et, pour une
projection empruntée, le type de sa cible. Deux méthodes homonymes
exercent la résolution. Le contrat de la fonction qui contient le
match rapporte le reset et l’allocation Int sur le pool injecté.

Le programme affiche `7` sous Clang C11 à `-O2` avec UBSan fatal.
Passer le pool de la cible de l’emprunt est refusé par la contrainte
de sources distinctes. Réintroduire Int pour les projections
reproduit le refus du cas valide. La mutation est détectée.
La suite des effets passe avec 20 tests et le lot précédent sur
la mise à jour conditionnelle avec 164 tests. Aucun modèle
indépendant dédié aux projections de match.

Le lot d’interactions avec les contrats et exigences de pool a
également terminé avec 81 tests réussis.

La suite complète de l’instantané précédent a terminé avec
1275 tests réussis. Une nouvelle suite complète est lancée sur
l’état incluant les retours, remplacements et effets de match.

## F1 et F2 — Emprunt typé retourné par projection de match

Le contrat conserve les champs imbriqués d’une projection partagée
retournée. Lorsqu’un argument peut désigner plusieurs porteurs, la
résolution concrète considère chaque variante atteignable et réserve
chaque porteur jusqu’au dernier usage de la projection.

Deux exécutions sous Clang C11 à `-O2` avec UBSan fatal affichent
respectivement `7` et `9`. L’appel avec un reset de l’un ou l’autre
pool terminal est refusé. La destruction d’un porteur possible avant
le dernier usage est refusée. La mutation qui ne résout que le
premier porteur supprime ce dernier refus et fait aussi échouer le
contrôle du contrat dans les cas valides. Le test détecte la mutation.
Aucun modèle indépendant dédié à la résolution des porteurs.
Le lot de régression et la suite complète précédente sont en cours.

## F2 — Tableau retourné avec une projection de match à porteurs multiples

La résolution des cases retournées et des vues de tableau passe
par le contrat de retour direct pour écarter les variantes
inaccessibles. Le filtrage précédent ne consultait que la première
allocation du porteur. Dans le contre-exemple, une fonction reçoit
l’emprunt de l’une de deux variantes et retourne la projection dans
une case de tableau.

Les deux chemins donnent `7` et `9` sous Clang C11 à `-O2` avec
UBSan fatal. Le reset de chacun des pools candidats est refusé tant
que la case est encore utilisée. La mutation qui filtre selon la
première allocation réintroduit un faux refus de provenance et
laisse passer un reset. Le test détecte la mutation.
Le lot précédent sur les retours directs de projection passe avec
140 tests. Le lot consacré aux tableaux et la suite complète
précédente sont en cours. Aucun modèle indépendant dédié à ce cas.

## F2 et ST10 — Projection de match conservée dans un agrégat retourné

La résolution du contrat d’un agrégat transféré examine chaque
porteur possible, avec ses variantes et réservations. Elle conserve
aussi les dépendances des mises à jour de champs qui empruntent
cette même voie de résolution. Le contre-exemple initial échouait
avec une cible absente du contrat de résultat sur le second bras.

Les deux variantes passent sous Clang C11 à `-O2` avec UBSan fatal
et donnent `7` et `9`. Les resets de chacun des pools cibles et
la destruction prématurée du second porteur sont refusés. La
mutation qui limite la résolution au premier porteur reproduit
l’échec des chemins valides et laisse passer deux cas invalides.
Aucun modèle indépendant dédié à ce cas.
Le lot précédent sur les tableaux a terminé avec 121 tests
réussis. Le lot de ce cycle et la suite complète précédente
sont en cours.

## F2 — Projection partagée typée en résultat d’un match expression

Le contrôle de fin de bras du match mutable accepte une projection
partagée vers un agrégat. Il conserve le type nominal jusqu’à la
jonction. Le test compare les deux formes, `match &link` et
`match &mut link`. La première était déjà acceptée avant ce changement.

Les deux programmes affichent `7` sous Clang C11 à `-O2` avec UBSan
fatal et refusent la destruction prématurée du porteur. La variante
qui mélange deux types nominaux est refusée. Restaurer le filtre
limité à Int fait échouer le cas mutable. La mutation est détectée.
Aucun modèle indépendant dédié à ces expressions.

Le lot précédent sur les projections stockées dans un agrégat
retourné passe avec 141 tests. Le lot de ce cycle et la suite
complète précédente sont en cours.

## F2 et F3 — Retour de fonction depuis un bras d’une expression match

Un `return` dans un bras passe par le vérificateur des retours de
fonction. La contrainte de type de la jonction s’applique aux
valeurs des bras continuants. Le contre-exemple utilisait un
champ de structure comme Int de retour dans un bras, et un
emprunt d’agrégat comme résultat du match dans l’autre.

Le programme affiche `7, 9, 13` sous Clang C11 à `-O2` avec UBSan
fatal. Le retour anticipé détruit le temporaire une seule fois
et son slot est réutilisé. Le remplacement du retour Int par
un emprunt est refusé. La mutation qui réintroduit le filtre
sur les retours des bras fait refuser le programme valide.
Aucun oracle indépendant spécifique à ce cas.

Le lot précédent sur les projections typées en résultat
d’expression a terminé avec 140 tests réussis.

Le lot match a révélé une régression du cycle des projections
typées. Un champ partagé issu d’un `match &mut` doit conserver la
réservation exclusive du porteur jusqu’à son dernier usage.
L’analyse des résultats restaure cette réservation et conserve
en plus les champs imbriqués lorsqu’une telle projection est
retournée. Le cas de régression et les deux tests ciblés passent.
Le lot match complet est relancé.

## F1 et F2 — Champ mutable typé et projection locale

Une structure ou un enum peut stocker un champ `&mut T` vers un
agrégat sans champ mutable. Le mode du champ est conservé lors de
la construction, du contrôle d’accès et de la projection. Un bras
`match &mut` peut écrire un champ de la structure projetée.
Une structure qui contient cette capacité reste non copiable.

Le scénario local dans une fonction affiche `9` sous Clang C11
à `-O2` avec UBSan fatal. La lecture et l’écriture directes de la
cible, le reset prématuré, l’écriture via match partagé et la
copie du porteur sont refusés. La mutation qui traite le champ
typé comme partagé laisse passer un accès direct et le test la
détecte. Aucun modèle indépendant dédié à ces projections.

Les contrats qui traversent un champ mutable typé, les
réemprunts directs de tels champs, et les liens vers des agrégats
ayant eux-mêmes des champs mutables restent ouverts.
Le lot précédent passe avec 71 tests de match. La suite complète
de l’instantané antérieur passe avec 1284 tests. Le lot de match
de ce cycle est en cours.

## F1 et F2 — Contrat de retour d’une projection mutable typée

Les signatures acycliques peuvent traverser un champ `&mut T`.
Le contrat de retour d’un match mutable réserve le porteur et la
cible, y compris lors d’un relais. La résolution consulte les
variantes de chaque porteur potentiel.

Le programme sous Clang C11 à `-O2` avec UBSan fatal affiche `9`.
Le vérificateur refuse deux lectures prématurées, la destruction
du porteur et les resets de chacun des deux pools. La mutation
qui supprime la réservation du porteur est détectée par le contrôle
du contrat de résultat. Le lot du cycle précédent passe avec
72 tests de match. Aucun modèle indépendant dédié.

Un appel dont le paramètre mutable peut désigner plusieurs
porteurs échoue encore au contrôle d’exclusivité dans le cas
essayé. Le résultat valide attesté ici a un seul porteur. Les
réemprunts directs de champs mutables typés restent ouverts.
La régression de ce cycle est en cours.

## F2 — Réemprunt mutable depuis des porteurs alternatifs

Le générateur créait une seule réservation de bras pour un sujet
à plusieurs porteurs possibles. Le second champ projeté était
alors traité comme un nouvel emprunt concurrent de la capacité
du porteur. Chaque porteur possible reçoit maintenant sa propre
réservation de bras, transmise à la projection.

Les deux chemins passent sous Clang C11 à `-O2` avec UBSan fatal.
Les sorties `9, 8` et `7, 9` montrent que seule la cible sélectionnée
est modifiée. Le vérificateur refuse de détruire le second porteur
ou de réinitialiser l’un des deux pools cibles avant le dernier
usage. La mutation qui ne réserve que le premier porteur rétablit
l’échec à la génération C. Le test la détecte. Aucun modèle
indépendant dédié à cette réservation.
La régression précédente des contrats mutables passe avec 113 tests.
Le lot match et la suite complète sur ce changement sont en cours.

## F1 et ST11 — Réemprunt direct d’un champ mutable typé

Les expressions `&mut *porteur.champ` et `&*porteur.champ`
conservent le type de l’agrégat cible et les réservations du
porteur. Le contrat réutilise la provenance de champ projeté
pour transmettre un réemprunt nominal à travers un appel.

Sous Clang C11 à `-O2` avec UBSan fatal, le réemprunt local mutable
et son relais affichent `9`. Le réemprunt local partagé affiche
`7, 7`. Les deux formes mutables refusent la destruction prématurée
du porteur et l’écriture directe de la cible. La mutation qui
supprime l’ascendance des réservations fait refuser les trois cas
valides et le test la détecte. Aucun modèle indépendant spécifique.

La réservation nominale est au niveau du porteur. Les accès
disjoints à d’autres champs du porteur sous ce réemprunt restent
à traiter. Le lot précédent passe avec 73 tests de match.
Le lot de ce cycle et la suite complète précédente sont en cours.

## ST6 et ST11 — Réservations distinctes pour les réemprunts nominaux

Un réemprunt direct d’un champ mutable typé réserve le champ
identifié par son chemin. Deux champs distincts du même
porteur peuvent être réempruntés simultanément. Un champ
scalaire distinct reste accessible. La réservation continue
de protéger le porteur contre la destruction et les accès
au champ déjà réemprunté.

Les formes locale et retournée par appel affichent `3, 9, 10`
sous Clang C11 à `-O2` avec UBSan fatal. Chacune refuse un second
réemprunt exclusif du même champ et une écriture directe sur
la cible du champ voisin qui est encore retenue par le porteur.
Le cas retourné révélait qu’une ascendance de porteur redondante
masquait cette protection du voisin. Le correctif conserve cette
ascendance via la réservation du champ. La mutation qui rétablit
la sélection de toutes les cibles du porteur est détectée.
Aucun modèle indépendant dédié à ce cas.

Le lot précédent a terminé avec 139 tests réussis. Le lot de ce
cycle et la suite complète lancée précédemment sont en cours.

## ST10 et ST11 — Réemprunt retourné après remplacement d’un champ mutable

Le contrat de retour d’un réemprunt nominal de champ résout
sa cible dans l’état après la mise à jour. Les champs imbriqués
de la nouvelle cible sont conservés lors d’un relais. Les
projections détachées de champs d’entrée continuent de désigner
leur cible initiale.

Le scénario sous Clang C11 à `-O2` avec UBSan fatal affiche
`7, 9, 2`. Il confirme que l’ancienne cible conserve sa valeur,
que seule la nouvelle cible est modifiée et que l’emprunt
terminal protège le nouveau pool. Le reset de l’ancien pool
réussit après la destruction de son porteur. Celui du nouveau
pool est refusé. La mutation qui relit les dépendances d’entrée
réintroduit le diagnostic de cible absente du contrat.
Aucun modèle indépendant dédié à ce cas.

Le lot précédent passe avec 140 tests. Le lot de ce cycle et la
suite complète précédente sont en cours.

## ST10, ST11 et P — Reset après remplacement dans une fonction

Pour un agrégat nominal mis à jour par contrat, le symbole
de l’allocation racine ne désigne que la racine. Les symboles
de champs portent les cibles. Le contrôle de vivacité à la
sortie d’un appel opaque suit les dépendances après la mise
à jour. Les contraintes d’ordre continuent de contrôler les
usages dans le corps, y compris avant le remplacement.

Sous Clang C11 à `-O2` avec UBSan fatal, le programme réinitialise
l’ancien pool à l’intérieur du relais, affiche `9, 9` et détruit
l’ancienne cible une seule fois. Réinitialiser le pool de la
nouvelle cible, déplacer le reset avant le remplacement ou
réutiliser l’ancienne cible après l’appel est refusé.
Les mutations qui rétablissent les cibles d’entrée dans le
symbole racine ou dans le contrôle de vivacité sont détectées.
Aucun oracle indépendant dédié à cet ordre d’opérations.

Le lot précédent passe avec 140 tests. La nouvelle régression
et la suite complète antérieure sont en cours.

La première régression de 163 tests a révélé 24 erreurs
`KeyError` dans les appels opaques dont les tests retirent le
résumé séparé. Le contrôle reçoit maintenant les mises à jour
du contrat déjà sélectionné. Deux tests opaques représentatifs
et le nouveau scénario passent après correction. Le lot de
163 tests est relancé.

## F1 et ST11 — Chaîne acyclique de champs mutables typés

Un champ mutable typé peut cibler un agrégat qui contient
lui-même un champ mutable. Le contrôle attribue chaque capacité
héritée au porteur qui stocke effectivement l’emprunt, afin de
la compter une seule fois. Un réemprunt plus profond reprend
la capacité déjà réservée au lieu d’introduire un conflit
avec sa propre ascendance.

Les parcours local et avec un premier réemprunt retourné par
fonction affichent `9` sous Clang C11 à `-O2` avec UBSan fatal.
Les deux refusent la lecture directe de la cible terminale,
le déplacement prématuré du porteur intermédiaire et le reset
du pool terminal. La mutation qui compte à nouveau la réservation
ancêtre comme concurrente fait refuser les deux programmes
valides. Aucun modèle indépendant dédié.

Le stockage d’un lien partagé vers un porteur de champs
mutables et les signatures récursives restent ouverts. Le lot
de 163 tests relancé après le correctif des appels opaques
passe intégralement. Le lot de ce cycle est en cours.

## F1 et ST11 — Lien partagé vers un agrégat à champ mutable

Un lien partagé peut cibler un agrégat qui stocke une capacité
mutable. Une copie du lien et un relais d’appel peuvent suivre
ce chemin en lecture. L’accès à un champ scalaire par le nom
d’origine vérifie désormais aussi si un réemprunt partagé
descend d’une capacité exclusive stockée.

Sous Clang C11 à `-O2` avec UBSan fatal, la copie et le relais
affichent `7, 7`. Le programme ne relit la cible par son nom
d’origine qu’après libération des porteurs. Le vérificateur
refuse la lecture et l’écriture directes prématurées, la
promotion du réemprunt partagé en mutable, le déplacement
du porteur intermédiaire et le reset prématuré de son pool.
La mutation qui supprime le contrôle d’exclusivité pour la
lecture directe laisse passer le contre-exemple.
Aucun modèle indépendant dédié à ce parcours.

La régression précédente passe avec 140 tests. La suite
complète de l’instantané antérieur passe avec 1292 tests.
La nouvelle régression ciblée est en cours.

## F1 et ST11 — Retour d’un réemprunt mutable sur plusieurs niveaux

Le contrat compose les chemins de champs d’un réemprunt de
réemprunt. Il compose aussi les chemins lors d’un appel sur
la projection d’un autre appel. Le vérificateur résout chaque
segment et conserve l’ascendance des réservations.

Les formes directe et relayée affichent `9` sous Clang C11 à
`-O2` avec UBSan fatal. Chacune refuse la destruction de l’un
ou l’autre porteur et le reset du pool terminal avant le
dernier usage. La mutation qui efface le préfixe du chemin
fait refuser le programme valide. Aucun modèle indépendant
dédié. Le scénario exerce des segments mutables de structures
acycliques. Les chemins mêlant détachement et réservation,
les signatures récursives et les indirections propriétaires
restent à couvrir.

Le lot précédent passe avec 141 tests. La régression de ce
cycle est en cours.

## F1 et ST11 — Retour avec préfixe détaché et suffixe réservé

Le contrat représente le préfixe détaché d’un chemin de retour
partagé. La résolution suit ce préfixe sans réserver son porteur,
puis réserve les porteurs du suffixe. Le relais transmet le
chemin composé et les contraintes d’ordre gardent les cibles
du suffixe.

Deux scénarios sous Clang C11 à `-O2` avec UBSan fatal affichent
`7`. Le premier réinitialise le pool du porteur initial dans
un relais. Le second détruit directement ce porteur. Le
vérificateur refuse encore la destruction du porteur
intermédiaire et le reset du pool terminal. La mutation qui
réserve également le préfixe refait échouer le reset valide.
Aucun modèle indépendant dédié à ces chemins.

Les chemins avec détachement après une réservation et le
stockage de ces chemins mixtes dans les agrégats retournés
restent à couvrir. Le lot précédent passe avec 140 tests.
La régression de ce cycle est en cours.

## F1 — Stockage d’un réemprunt à préfixe détaché dans un retour transféré

Un agrégat transféré peut conserver un réemprunt partagé dont
le chemin comporte un préfixe détaché et un suffixe réservé.
Le contrat de résultat propage cette distinction à travers le
stockage dans un champ et les relais. La résolution réutilise
le contrat du retour direct pour obtenir les cibles et leurs
réservations.

Sous Clang C11 à `-O2` avec UBSan fatal, la lecture donne `7`
après reset du pool du premier porteur dans une fonction,
et après destruction de ce porteur chez l’appelant. La
destruction du porteur intermédiaire et le reset du pool
terminal sont refusés. La mutation qui perd le préfixe dans
le contrat de l’agrégat fait échouer le reset valide.
Aucun oracle indépendant dédié. Le détachement après une
réservation reste ouvert.

Le lot précédent passe avec 140 tests. La régression ciblée
et une nouvelle suite complète sont lancées.

## F1 et ST11 — Détachement après la traversée d’un lien mutable

Un retour partagé peut suivre un lien mutable intermédiaire
et détacher la cible du dernier champ partagé. La résolution
du contrat suit les liens intermédiaires pour localiser ce
champ. Elle conserve l’ascendance du dernier champ et exige
toujours que ce dernier fournisse une capacité partagée.

Le test avec relais affiche `7` sous Clang C11 à `-O2` avec
UBSan fatal après destruction des deux porteurs intermédiaires.
Le reset du pool terminal est refusé. La mutation qui rétablit
l’exigence d’un lien partagé à chaque étape fait refuser le
programme valide. Aucun oracle indépendant dédié.
Le lot précédent passe avec 140 tests. Le nouveau lot ciblé
et la suite complète lancée précédemment sont en cours.

## F1 et ST11 — Réemprunt exclusif imbriqué stocké dans un agrégat retourné

Un agrégat transféré peut conserver un réemprunt mutable
dont le contrat réserve plusieurs porteurs. La résolution
reprend le chemin du retour direct, contrôle le mode du
champ et attache ses réservations au résultat transféré.

Sous Clang C11 à `-O2` avec UBSan fatal, le scénario relaie
l’agrégat, réemprunte son champ, modifie la cible et affiche
`9` après destruction des porteurs. Le vérificateur refuse
la destruction de chacun des deux porteurs d’origine,
la lecture directe de la cible et le reset de son pool
avant le dernier usage. La mutation qui omet la résolution
du chemin exclusif imbriqué est détectée. Aucun oracle
indépendant dédié.

La régression précédente passe avec 141 tests. Le nouveau
lot ciblé et la suite complète précédente sont en cours.

## F2 et ME — Méthode Void appelée sur une projection typée de match

Le bras d’un match peut appeler une méthode Void sur une
structure projetée. La validation du corps sélectionne
le chemin de vérification général. L’appel vérifie ensuite
le mode du receveur et le contrat de la méthode.

Le scénario Clang C11 à `-O2` avec UBSan fatal affiche `9`
après écriture par la méthode et libération du porteur.
Le vérificateur refuse l’appel mutable via un match partagé
et l’abandon du résultat d’une méthode Int. La mutation qui
rétablit l’ancien filtre des instructions de bras fait
refuser le programme valide. Aucun oracle indépendant dédié.
Le lot précédent passe avec 140 tests. La régression match
et la suite complète précédente sont en cours.

## F2 et ME — Réemprunt retourné par une méthode dans un bras

Un bras peut recevoir le résultat d’une méthode appelée sur
une projection typée. La réservation du porteur reste active.
Le vérificateur compte une seule fois la réservation commune
au bras et à la vue de champ retournée par la méthode.

Le scénario sous Clang C11 à `-O2` avec UBSan fatal affiche
`9, 10`. La vue mutable modifie le champ, puis la projection
reprend l’accès après le dernier usage de la vue. Écrire par
la projection plus tôt ou appeler la méthode via un match
partagé est refusé. La mutation qui réintroduit le double
comptage fait échouer le scénario valide. Aucun oracle
indépendant dédié.

Le lot précédent passe avec 74 tests de match. Le nouveau
lot et la suite complète précédente sont en cours.

## F2 et ME — Résultat d’une méthode comme valeur d’un bras

Un appel de méthode sur une projection typée peut fournir
directement la valeur d’un bras. La jonction vérifie les types
et les modes, et le contrat de l’appelant conserve les effets
de la méthode.

Les deux variantes donnent `7, 9` sous Clang C11 à `-O2`
avec UBSan fatal. Passer le pool de la cible encore empruntée
au reset de la méthode est refusé. Mélanger un Int et un emprunt
comme valeurs des bras est refusé. La mutation qui remet en
place le filtre des résultats de bras est détectée.
Aucun oracle indépendant dédié. Le retour d’un emprunt au
stockage d’un champ à travers cette projection est encore refusé
dans le scénario essayé.

Le lot précédent passe avec 75 tests de match. Le lot de
ce cycle et la suite complète précédente sont en cours.

## F2, ST14 et ME — Retour du stockage d’un champ via une projection

Le contrat compose le chemin du receveur projeté avec le
champ de stockage emprunté par la méthode. Le vérificateur
résout le porteur intermédiaire et attache son ascendance à
la vue du champ. Le relais conserve ces informations.

Sous Clang C11 à `-O2` avec UBSan fatal, l’écriture par
l’emprunt retourné donne `11`. La destruction du porteur,
l’écriture directe et le reset prématuré du pool sont
refusés. Le reset est aussi refusé par le contrat lorsqu’il
est tenté dans un autre relais. La mutation qui ignore le
chemin du receveur fait refuser le scénario valide.
Aucun oracle indépendant dédié. Le lot précédent passe avec
76 tests de match. La nouvelle régression est en cours.

## F2, ST11 et ME — Réemprunt d’un champ indirect via une projection

Un contrat de méthode peut retourner le réemprunt d’un
champ `&mut Int` depuis une projection typée. La résolution
compose le chemin du receveur et la vue de champ indirecte,
qui protège le stockage et la cible.

Le scénario avec relais affiche `11` sous Clang C11 à `-O2`
avec UBSan fatal. L’écriture directe, la destruction du
porteur et le reset des pools de la structure projetée et
de la cible sont refusés. La mutation qui retire le support
du chemin indirect rétablit le refus du scénario valide.
Aucun oracle indépendant dédié. Le lot précédent passe
avec 140 tests. Le lot de ce cycle et la suite complète
précédente sont en cours.

## F2, ST14 et ME — Composition de chemins de champs au relais

Un appel sur une projection peut relayer un résultat dont le
contrat comporte déjà un chemin vers un champ. La composition
préserve la distinction entre le préfixe détaché et les
porteurs réservés. Une vue de champ comptabilise désormais
une réservation partagée du porteur en mode partagé.

Les scénarios Clang C11 à `-O2` avec UBSan fatal donnent `7`
pour le retour partagé après destruction du premier porteur
et `11` pour le réemprunt indirect à plusieurs niveaux.
Le premier refuse la destruction prématurée du porteur
intermédiaire et le reset du pool de la cible. Le second
protège aussi le porteur ajouté par le relais. Les mutations
qui perdent la composition mixte ou traitent la réservation
partagée comme mutable sont détectées.
Aucun oracle indépendant dédié.

Le lot précédent passe avec 140 tests. Le lot de ce cycle
et la suite complète antérieure sont en cours.

## H3 et F4 — Vivacité du receveur de vequals

La comparaison utilise le receveur après l’évaluation de
l’argument. L’analyse des contraintes enregistre maintenant
cet usage. Le contre-exemple passait la vérification opaque
alors que la génération spécialisée refusait le reset
du receveur transféré dans l’appel qui fournit l’argument.

Avec un pool distinct, le scénario Clang C11 à `-O2` avec UBSan
fatal affiche `1` et détruit chaque allocation une fois.
Réinitialiser le pool du receveur ou de l’argument encore
emprunté est refusé dès la vérification. La mutation qui omet
l’usage du receveur après l’argument laisse passer le premier
contre-exemple. Aucun modèle indépendant dédié à ce cas.
La règle de comparabilité des agrégats à champs référence
demande une décision sur la sémantique de ces champs.

Le lot précédent passe avec 177 tests. La suite complète de
l’instantané antérieur passe avec 1301 tests. Les quatre tests
ciblés vequals passent.

## F4 et tableaux de références — Vivacité pendant la construction

Les références préparées pour un littéral de tableau restent
nécessaires jusqu’à la fin de l’évaluation des éléments. Le
contrat enregistre désormais cet usage après les effets de
l’ensemble des expressions. Le contre-exemple réinitialisait
le pool du premier élément en calculant le second. Sans le
correctif, le refus intervenait seulement lors d’un accès
ultérieur à la case invalide.

Sous Clang C11 à `-O2` avec UBSan fatal, le programme valide
avec un pool distinct affiche `7, 9`. Les deux appels qui
réinitialisent le pool de l’un des éléments sont refusés par
la contrainte de sources distinctes. La mutation qui omet
l’usage final fait disparaître ce contrôle contractuel et le
test la détecte. Aucun modèle indépendant dédié à ce cas.
La régression des tableaux et arguments est en cours.

## F4 — Effets pendant le calcul de l’indice d’une ligne

Une projection de ligne de références utilise les cibles de
la ligne après l’évaluation de l’indice. Le contrat enregistre
cet usage pour les lignes stockées directement et les lignes
elles-mêmes empruntées.

Les deux scénarios donnent `7` sous Clang C11 à `-O2` avec
UBSan fatal lorsque le calcul d’indice réinitialise un pool
distinct. Réinitialiser le pool de la cible est refusé par la
contrainte de sources distinctes. Dans le cas de la ligne
empruntée, la mutation qui omet l’usage postérieur déplace
le diagnostic vers le contrôle concret de la durée de vie.
Le test détecte cette perte du contrôle contractuel.
Aucun oracle indépendant dédié.

Le lot précédent sur la construction de tableaux passe
avec 181 tests. La régression de ce cycle est en cours.

La première régression a révélé deux faux refus lorsque le
reset d’une case précédait l’expression d’index et qu’une
autre case restait seule utilisée. Le contrôle de projection
ne considère désormais que les effets apparus pendant le
calcul de l’indice. Les deux tests de dernier usage et le
contre-exemple ciblé passent. Le lot élargi est relancé.

## F1 — Disposition des définitions récursives via A<T>

Les définitions peuvent rompre un cycle par un champ `A<T>`.
La disposition C réserve une case de taille pointeur pour
ce champ et vérifie que le type cible existe. Les cycles
stockés directement restent refusés.

Le test inspecte deux ordres de champs dans les tailles de
slots du C généré. La mutation qui remet une taille Int
pour le handle est détectée. Le programme crée les pools,
construit la variante terminale et affiche `7` sous Clang C11
à `-O2` avec UBSan fatal. Le compilateur refuse le cycle
direct, le type de handle inconnu et la construction d’un
champ propriétaire. Le stockage, la projection et le
nettoyage propriétaire restent à implémenter.
Aucun modèle indépendant spécifique à cette disposition.

La régression du calcul d’indice des lignes passe avec
161 tests. Le lot des types récursifs est en cours.

## F1 et H1 — Stockage et nettoyage locaux des champs propriétaires

Un champ `A<T>` reçoit un transfert explicite. Le pointeur
reste celui du slot d’origine. L’agrégat suit les pools de
ses enfants et de leurs descendants propriétaires, ce qui
empêche de transférer l’agrégat hors de leur portée ou de
réinitialiser un pool qui contient encore une cible stockée.
Le runtime détruit les enfants avant le porteur et récupère
chaque slot auprès de sa source.

Sous Clang C11 à `-O2` avec UBSan fatal, une chaîne d’enums
est détruite de la feuille à la racine et réutilise le slot
terminal. Le reset d’un pool de structures détruit également
l’enfant dans un autre pool. Le vérificateur refuse la
réutilisation d’une liaison transférée, le reset prématuré
du pool enfant, la copie d’un porteur et un transfert
au-delà du pool enfant. La mutation qui supprime la
destruction des champs épuise le pool terminal et est détectée.
Aucun modèle indépendant dédié aux champs propriétaires.

La construction validée est locale hors fonction, avec des
enfants sans dépendances empruntées. Les contrats, les
projections, les remplacements et le reset conjoint d’un
pool commun au porteur et à ses enfants restent à traiter.
Le nettoyage C parcourt récursivement les champs propriétaires.
La régression des handles est en cours.

## F1, F2 et H1 — Projection empruntée d’un champ propriétaire

Un match partagé ou mutable peut emprunter la cible d’un
champ `A<T>`. Le porteur conserve le nettoyage. Les jonctions
conservent les enfants possibles et la projection suit le
scope du porteur après transfert.

Les deux chemins sous Clang C11 à `-O2` avec UBSan fatal
donnent `7, 9` et `8, 9`. Chacun détruit une seule fois
l’enfant sélectionné. Le vérificateur refuse la destruction
du porteur, les resets prématurés des pools candidats et
l’extraction du champ dans un match consommant. La mutation
qui omet le rattachement au scope du porteur fait refuser
les deux chemins valides. Aucun oracle indépendant dédié.

Le lot précédent sur les handles passe avec 96 tests. Le
lot match est en cours. La projection directe par champ et
les contrats des agrégats propriétaires restent ouverts.

## H1, H2 et ST15 — Emprunt direct et remplacement d’un champ propriétaire

Les expressions `&*porteur.champ` et `&mut *porteur.champ`
empruntent la cible d’un champ propriétaire. Un Int peut être
lu par copie avec `*porteur.champ`. Un porteur local direct
peut remplacer son champ par transfert explicite. La nouvelle
allocation est évaluée avant la destruction de l’ancienne.
Un emprunt d’un autre champ reste utilisable.

Sous Clang C11 à `-O2` avec UBSan fatal, le remplacement lit
l’ancienne valeur, conserve la vue du champ voisin, détruit
l’ancienne cible une seule fois et réutilise son slot avant
reset. Un emprunt actif du champ remplacé bloque l’écriture.
Avec un seul slot dans le pool commun, la nouvelle allocation
échoue avant la destruction de l’ancienne. Supprimer la
destruction dans une copie du compilateur épuise le pool
lors du réemploi et la mutation est détectée.
Aucun oracle indépendant dédié.

Le remplacement via un porteur emprunté, les enfants à
dépendances empruntées et les contrats propriétaires restent
ouverts. Le lot match précédent passe avec 80 tests.
La régression du remplacement est en cours.

Le lot des valeurs propriétaires passe avec 18 tests. Un
essai supplémentaire remplace la vue voisine par un emprunt
mutable et affiche `10, 9, 12, 11` sous UBSan.

## H1 et ST15 — Remplacement d’un champ propriétaire via un emprunt local

Un emprunt mutable vers un porteur suivi peut remplacer
son champ `A<T>`. Lorsque l’emprunt peut désigner plusieurs
porteurs, le vérificateur conserve pour chacun l’ancienne
cible et la nouvelle possibilité. Le C ne remplace et ne
nettoie que le champ sélectionné à l’exécution.

Les deux chemins sous Clang C11 à `-O2` avec UBSan fatal
affichent `9, 8` et `7, 9`. La cible transférée est détruite
une fois dans chaque exécution. Les trois resets prématurés
sont refusés. La mutation qui écrase les anciennes
provenances dans tous les porteurs laisse passer deux
resets et le test la détecte. Aucun modèle indépendant dédié.

Le remplacement d’un champ dans un enfant propriétaire
projeté reste refusé tant que ses métadonnées ne sont pas
suivies dans les états de jonction. Les contrats de fonctions
pour les agrégats propriétaires restent ouverts.

## F1 et H1 — Enfant propriétaire avec dépendances empruntées

Un champ `A<T>` peut recevoir un enfant qui porte des
emprunts. L’analyse suit les arêtes de propriété pour
retrouver les porteurs des emprunts partagés ou exclusifs.
Le remplacement refuse un cycle formé par une arête de
propriété et un emprunt de retour vers le porteur.

Sous Clang C11 à `-O2` avec UBSan fatal, le scénario partagé
lit encore `7` après destruction de l’enfant et de son
porteur. La cible externe est détruite une seule fois par son
propre receveur. Le scénario mutable affiche `9` après
réemprunt à travers le champ propriétaire. Les resets et
accès directs prématurés sont refusés. La mutation qui
ignore les enfants dans le graphe perd le contrôle du reset
et accepte le cycle. Aucun oracle indépendant dédié.

Le lot précédent passe avec 19 tests. La régression de ce
cycle est en cours. Les contrats des agrégats propriétaires
et le remplacement dans un enfant propriétaire projeté
restent ouverts.

## H1 et ST15 — Remplacement dans un enfant propriétaire projeté

Les instantanés du vérificateur suivent aussi les enfants
propriétaires. Une jonction réunit leurs champs possibles.
Le contrôle des resets et des durées de vie consulte les
pools de la chaîne d’enfants depuis le porteur racine.

Sous Clang C11 à `-O2` avec UBSan fatal, le remplacement
conditionnel affiche `9` ou `7` selon le chemin. Le
vérificateur refuse le reset de chacun des deux pools
candidats. Après un remplacement inconditionnel, le reset
de l’ancien pool est accepté. La mutation qui ne retient
qu’un état de l’enfant laisse passer un reset et le test
la détecte. Aucun modèle indépendant dédié.

Le lot précédent passe avec 21 tests. La nouvelle régression
passe avec 22 tests. Les contrats propriétaires et les interactions
des remplacements imbriqués avec le point fixe des boucles
restent à valider.

## F3 et H1 — Remplacement imbriqué sur une reprise de boucle

Un remplacement de `A<Leaf>` dans un enfant projeté pouvait changer la
cible de l’emprunt stocké tout en conservant les mêmes pools. Avec une
jonction avant la boucle, le vérificateur s’arrêtait au premier passage
abstrait et autorisait une écriture dans la nouvelle cible après le
`break`, alors que la racine la retenait encore.

Le point fixe compare désormais la provenance des champs propriétaires
par chemin de champ, avec leurs dépendances et variantes. Les nouvelles
allocations sont comparées par leurs propriétés suivies pour éviter de
faire diverger l’analyse à cause des identifiants créés à chaque passage.

La régression couvre deux reprises par `continue`, la sortie par
`break`, le refus de l’écriture avant le drop de la racine et
l’acceptation après. Le cas accepté imprime `12` et détruit trois
instances de `Leaf` sous Clang C11 à `-O2` avec UBSan fatal. Retirer
l’état propriétaire de la comparaison reproduit le défaut
(`Error not raised`). Aucun modèle indépendant dédié à ce cas.
Les contrats des agrégats propriétaires restent ouverts.

Le lot ciblé sur les champs propriétaires passe avec 23 tests.

## F2 et H1 — Extraction d’un champ A<T> par match consommant

Le vérificateur refusait de lier un champ propriétaire dans un bras
consommant, alors que F2 transmet les valeurs déplacées au bras.
Le bras reçoit désormais l’allocation et ses provenances possibles.
Le C détache le champ avant de détruire l’enum. Les champs ignorés
restent attachés et sont détruits avec lui.

Deux chemins exécutés sous Clang C11 à `-O2` avec UBSan fatal rendent
respectivement `7` et `9`, puis réutilisent le slot du champ ignoré.
Les traces confirment une destruction par allocation et le vérificateur
refuse l’accès à l’enum consommé. Un autre programme conserve un emprunt
dans le champ extrait. Il imprime `7` puis `9` après le drop et la
mutation. La mutation avant le drop est refusée. Supprimer le détachement
dans le C généré fait échouer les deux chemins sous UBSan.
Aucun modèle indépendant dédié à cette extraction.

Un bras qui quitte par `continue` ou `break` détruit aussi son champ
nommé avant de quitter. Le pool de capacité un est réutilisé dans
l’itération suivante puis après la boucle, avec la sortie `0, 1, 9`.
Le lot match passe avec 81 tests avant l’ajout de ce dernier cas.
Le lot match consommant qui inclut ce cas passe avec 18 tests.
Les signatures de fonctions qui portent ces agrégats restent ouvertes.

## B4c, F2 et H1 — Champ propriétaire local à une fonction

Une fonction peut créer un agrégat local avec un champ `A<T>`.
L’analyse des résultats suit la valeur propriétaire jusqu’au
`match` consommant, y compris à travers les jonctions. L’analyse des
contraintes conserve le pool du champ tant que l’agrégat peut le détenir,
y compris lorsque le dernier usage du champ est le nettoyage implicite.

Les trois régressions ciblées passent sous Clang C11 à `-O2` avec UBSan
fatal. Un relais restitue la même adresse et le même contenu, avec une
seule destruction. Un résultat conditionnel affiche `7` ou `9` selon
le pool sélectionné et le vérificateur refuse un reset prématuré de
chacun des pools possibles. Un reset interne sur un pool distinct est
accepté, puis le slot du champ détruit est réutilisé. Le contrat refuse
le même appel si le pool à réinitialiser fournit le champ. Une mutation
supprimant la rétention du pool dans le contrat laisse passer ce cas
(`Error not raised`). Aucun modèle indépendant dédié.

Les paramètres et résultats dont le type est lui-même un agrégat à
champs propriétaires restent ouverts.

## B4 et H1 — Paramètre partagé d’agrégat propriétaire

Le vérificateur construit un inventaire symbolique des champs `A<T>`
pour un paramètre partagé d’agrégat acyclique dont les feuilles sont
des `Int`. Les chemins de champs servent à résoudre les contraintes
de pools. Le relais peut projeter un champ imbriqué puis passer son
emprunt à une autre fonction.

Sous Clang C11 à `-O2` avec UBSan fatal, le relais affiche `7`, puis
le slot de la feuille est réutilisé après la destruction de la racine
et affiche `9`. Une tentative de consommer l’emprunt est refusée.
Le reset du pool de la feuille est rejeté par la contrainte du contrat
du relais. Une mutation qui ignore les champs propriétaires lors de
la résolution d’une contrainte perd ce diagnostic au contrat. Le
contrôle générique des handles stockés refuse encore ce cas au niveau
de l’appel. Aucun modèle indépendant dédié.

Le lot contraintes, effets et retours du cycle précédent a terminé
avec 104 tests réussis. Le même lot a été relancé sur ce cycle.
Les paramètres mutables ou transférés, les résultats d’agrégats
propriétaires et les signatures récursives restent ouverts.

## B4, F2 et H1 — Transfert et restitution d’un agrégat propriétaire

Le modèle symbolique de champs `A<T>` acycliques à feuilles `Int`
sert aussi aux paramètres transférés. Une fonction peut consommer
l’agrégat, extraire un champ par match et le nettoyer dans le bras.
Pour restituer l’agrégat entier, le contrat identifie le paramètre
transféré. La vérification du corps compare l’identité des champs
sur chaque chemin de retour. Un relais transmet cet inventaire.

Sous Clang C11 à `-O2` avec UBSan fatal, le scénario consommant
affiche `7` puis `9` et réutilise le slot de la feuille après une
seule destruction. Un emprunt encore actif et un reset du pool de
la feuille sont refusés. Le scénario de restitution conserve
l’adresse de l’agrégat, transmet une mutation de son champ scalaire,
garde le pool de l’enfant protégé et réutilise son slot après drop.
Effacer l’inventaire au retour d’un appel opaque fait échouer le
relais au contrôle de restitution. Aucun modèle indépendant dédié.

Les trois tests ciblés, dont celui du paramètre partagé, passent.
Le lot contraintes, effets et retours lancé au cycle précédent
a terminé avec 104 tests réussis. Les paramètres mutables,
les résultats neufs ou à champs remplacés et les signatures
récursives restent ouverts. Pour le reset historique, les contraintes
d’un paramètre propriétaire sont conservatrices sur l’ordre
de nettoyage de ses champs.

Le lot match consommant passe avec 18 tests sur ce cycle.
La suite complète lancée au cycle F3/H1 (avant les derniers travaux
de contrats) a terminé avec 1 322 tests réussis en 737,673 secondes.

## B4 et H1 — Mutation du contenu d’un agrégat propriétaire emprunté

Les paramètres `&mut T` peuvent projeter les champs `A<T>` des
agrégats acycliques à feuilles `Int` et modifier leur contenu.
Le vérificateur contrôle les écritures de la fonction sur l’inventaire
symbolique. Le contrat conserve les allocations et leurs pools.
Le remplacement d’un handle dans un porteur emprunté reste refusé,
y compris dans un champ imbriqué, tant que le contrat ne transporte
pas la modification de provenance.

Le lot des trois tests de paramètres propriétaires passe sous Clang
C11 à `-O2` avec UBSan fatal. Le relais mutable conserve l’adresse
de la feuille et affiche `9`. Un emprunt partagé réutilisé après
l’appel bloque l’accès mutable. Un contre-exemple tente de remplacer
un champ imbriqué via un appel, puis de réinitialiser son nouveau pool
avant une lecture. Retirer le contrôle de remplacement fait accepter
ce programme par le vérificateur opaque (`Error not raised`).
Aucun modèle indépendant dédié. La suite complète lancée au cycle
précédent est en cours.

## B4c et H1 — Retour d’un agrégat neuf à champs A<Int>

Le contrat d’un résultat neuf peut maintenant décrire la provenance
de chaque champ propriétaire direct de type `A<Int>`. Les alternatives
peuvent désigner un paramètre transféré ou une nouvelle allocation
d’un pool injecté. Le vérificateur contrôle les champs de chaque
sortie, puis propage leur inventaire à travers les appels et relais.

Les deux exécutions sous Clang C11 à `-O2` avec UBSan fatal affichent
`7, 9` ou `8, 9` selon le chemin. Elles détruisent l’allocation
transférée une seule fois et réutilisent son slot. Deux contre-exemples
refusent le reset de chacun des pools possibles avant la lecture.
Retirer une alternative du contrat fait échouer le contrôle du corps
avec le diagnostic de provenance de champ absente. Le test de retour
neuf et les régressions ciblées sur la restitution et l’extraction
passent. Aucun modèle indépendant dédié.

Le retour d’un agrégat neuf dont un champ possède lui-même d’autres
champs propriétaires reste ouvert. Le remplacement d’un champ dans
un paramètre mutable reste également ouvert.

## B4c et H1 — Retour neuf avec champs propriétaires imbriqués

Le contrat de résultat suit récursivement les champs propriétaires
créés dans des pools injectés. Le vérificateur compare les champs et
leurs provenances à chaque niveau du résultat. Le relais et la
reconstruction côté appelant conservent cet inventaire.

Sous Clang C11 à `-O2` avec UBSan fatal, le scénario lit `7` dans
la feuille retournée, remplace cette feuille localement, lit `8`,
puis réutilise le slot libéré pour `9`. Les resets prématurés du
pool de l’enfant, de la feuille initiale et de la feuille remplaçante
sont refusés. Le reset du pool de la feuille initiale après
remplacement est accepté. Supprimer la reconstruction récursive
déclenche une erreur de provenance dans le corps de la fonction.
Les trois tests ciblés de retour passent. Aucun modèle indépendant
dédié à cette interaction.

Le passage d’un agrégat reçu par transfert dans un champ de résultat
neuf et le remplacement d’un handle à travers un appel restent ouverts.

## B4c et H1 — Agrégat transféré comme enfant d’un résultat neuf

Le contrat peut désigner un paramètre transféré comme source d’un
champ propriétaire. L’inventaire du paramètre est transmis avec
ses descendants, y compris les alternatives que l’appelant a
établies avant l’appel. Le vérificateur compare le résultat du corps
à cet inventaire récursif.

Les trois tests ciblés de retours neufs passent sous Clang C11
à `-O2` avec UBSan fatal. Dans le nouveau cas, les deux branches
lisent respectivement `7` ou `8` à travers l’enfant. Son adresse est
identique avant le transfert et après le relais. Le drop rend le
slot disponible. Trois contre-exemples refusent le reset du pool
de l’enfant et de chacun des deux pools candidats de sa feuille.
Supprimer les descendants du contrat fait échouer la vérification
du corps. Aucun modèle indépendant dédié à ce cas.

Un champ agrégat restitué par ce mécanisme correspond à un seul
paramètre identifié. La combinaison dans ce même champ d’une
alternative paramètre et d’une alternative agrégat neuf reste
ouverte, ainsi que le remplacement de handle via un appel mutable.

## B4c et H1 — Champ à alternatives propriétaire transférée et neuve

Un même champ du résultat peut désormais contenir un agrégat reçu
par transfert ou un agrégat neuf. Les appels et relais propagent
les provenances de chaque alternative et de leurs descendants.
La vérification du corps contrôle l’union par champ pour accepter
également les états déjà joints.

Les quatre tests ciblés passent sous Clang C11 à `-O2` avec UBSan
fatal. Le nouveau scénario lit `7` à l’adresse d’entrée ou `8` à
une nouvelle adresse, selon la branche. Le slot est réutilisable
après destruction. Les quatre resets prématurés possibles sont
refusés, pour les deux pools d’enfants et les deux pools de feuilles.
Omettre l’alternative transférée provoque une erreur de provenance
pendant la vérification du corps. Aucun modèle indépendant dédié.

Le remplacement d’un handle dans un agrégat emprunté via un appel
et les signatures récursives restent ouverts.

## B4 et H1 — Remplacement direct d’un champ A<Int> par appel mutable

Le contrat décrit le remplacement d’un champ direct par une
allocation issue d’un pool injecté. Une branche qui laisse le champ
intact conserve explicitement la provenance d’entrée. Le vérificateur
contrôle les états de sortie du corps et applique les alternatives
lors d’un appel opaque, y compris dans un relais.

Sous Clang C11 à `-O2` avec UBSan fatal, les trois exécutions ciblées
couvrent le remplacement inconditionnel et les deux branches du
remplacement conditionnel. Le reset de l’ancien pool est accepté
après remplacement inconditionnel. Les deux pools restent protégés
dans le cas conditionnel. Le slot de remplacement est réutilisé
après drop. Supprimer l’application du contrat dans un appel opaque
fait échouer la vérification du relais. Aucun modèle indépendant
dédié. La suite complète lancée avant ces changements a terminé
avec 1 331 tests réussis en 628,309 secondes.

Les écritures imbriquées et les champs qui reçoivent un agrégat
restent ouverts. Le suivi des resets historiques reste conservateur
après un remplacement par appel.

## B4 et H1 — Remplacement par un agrégat dans un champ direct

Un appel mutable peut remplacer un champ propriétaire direct par un
agrégat neuf ou par un agrégat reçu en paramètre transféré. Le contrat
et le relais conservent les pools des descendants du remplaçant.

Sous Clang C11 à `-O2` avec UBSan fatal, les deux variantes exécutées
affichent `8` puis `9`. Elles détruisent une seule fois l’ancienne
feuille, autorisent le reset de son pool et réutilisent le slot de la
nouvelle feuille après drop. Le reset prématuré du nouveau pool et
l’installation d’une feuille issue d’un pool local à la fonction
sont refusés. Ce dernier cas révélait un accès hors limites dans
l’analyse symbolique, corrigé en validant les descendants avant
de publier le contrat. Supprimer la reconstruction récursive fait
échouer le contrôle de provenance. Trois tests ciblés passent et
le lot contraintes, effets et retours du cycle précédent compte
71 succès. Aucun modèle indépendant dédié.

Le remplacement via un chemin de champs imbriqués du receveur
emprunté reste ouvert.

## B4 et H1 — Remplacement à travers un chemin propriétaire imbriqué

Le contrat mémorise le chemin du champ depuis le paramètre mutable.
Une projection nommée conserve ce chemin dans un relais. Le vérificateur
résout le porteur dans l’inventaire de l’appelant, applique la mise à
jour et vérifie l’état des champs après le corps de la fonction.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le nouveau scénario libère l’ancienne feuille, accepte le reset
de son pool et affiche `8` puis `9` après réemploi du slot.
Le reset du nouveau pool est refusé, pour une écriture imbriquée
directe et pour un relais qui transmet l’emprunt projeté.
Supprimer le chemin de projection fait échouer la vérification
du relais. Aucun modèle indépendant dédié. La suite complète
a été relancée sur cette version.

La résolution exige encore un porteur unique. Les effets qui
remplacent à la fois un champ ancêtre et un de ses descendants
sur des chemins différents restent ouverts.

## B4 et H1 — Remplacement par appel avec porteurs alternatifs

Le contrat applique un remplacement possible à chacun des porteurs
candidats. Tant que le vérificateur ne sait pas quel porteur sera choisi,
il conserve aussi les champs d’origine. La durée de vie du remplaçant
est contrôlée pour chaque destination.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le test des porteurs alternatifs exécute les deux branches, chacune
avec une affectation directe puis avec un appel. Les traces montrent
une seule destruction du remplaçant par exécution. Les resets des
deux pools initiaux et du pool de remplacement sont refusés avant
lecture. Retirer la conservation des anciens champs fait échouer le
contrôle du corps et laisse passer les deux resets initiaux dans le
vérificateur opaque. Aucun modèle indépendant dédié.

La suite complète précédente est toujours en cours. Les effets
chevauchants entre un champ et ses descendants restent ouverts.

## B4 et H1 — Effets chevauchants sur un champ et ses descendants

Une fonction peut remplacer un enfant puis remplacer un champ
de l’enfant qu’elle vient d’installer. Elle peut aussi remplacer
l’enfant sur une sortie et ne remplacer que sa feuille sur une
autre. Les inventaires attendus composent les effets imbriqués.
Une sortie qui a déjà détruit un porteur ne déclenche plus
d’exception interne lors de la comparaison des inventaires.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le scénario séquentiel affiche `9` et accepte le reset des deux
pools devenus libres. Le scénario à deux sorties affiche `8`
ou `9`, accepte le reset du pool de la feuille initiale sur les
deux branches et refuse le reset des deux pools candidats de
la nouvelle feuille. Supprimer la composition de l’effet
descendant fait échouer le contrôle de provenance. Aucun modèle
indépendant dédié.

Les effets chevauchants qui se rejoignent avant une sortie commune
restent ouverts, ainsi que leur propagation générale dans les relais.

## B4 et H1 — Jonction des remplacements chevauchants et relais

L’analyse garde des états distincts lorsque la jonction réunit
un enfant d’entrée et un remplaçant. Les écritures de descendants
restent rattachées à l’enfant qu’elles affectent. Un relais compose
d’abord les effets descendants sur l’inventaire d’entrée, puis le
remplacement éventuel de son ancêtre.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le scénario à sortie commune passe par un relais et affiche `8`
ou `9` selon la branche. Les deux exécutions acceptent le reset du
pool initial. Les resets des deux pools candidats sont refusés.
Supprimer la distinction entre enfant d’entrée et remplaçant
fait échouer la vérification de provenance. Aucun modèle
indépendant dédié. La suite complète lancée plus tôt est en cours.

## F1, B4c et H1 — Retour neuf d’une valeur finie de type récursif

Un type récursif par champs `A<T>` est admis comme résultat neuf
si le contrat décrit les valeurs construites par un inventaire fini.
Le vérificateur suit l’arbre de résultat et ses variantes à travers
le relais. La vérification du type termine sur les cycles déclarés,
et celle de la valeur inspecte les champs réellement construits.

Les trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
La nouvelle régression exécute une variante terminale et une chaîne
de trois nœuds. Les sorties sont `5, 9` et `7, 9`. La trace montre
la destruction de la feuille avant les nœuds et le slot terminal
est réutilisable. Les resets des deux pools sont refusés tant que
la chaîne reste accessible. Supprimer le suivi récursif du résultat
fait échouer la vérification de provenance. Aucun modèle indépendant
dédié. Les paramètres récursifs et les résultats dont la forme
symbolique est de profondeur non bornée restent ouverts.

## F1, B4 et H1 — Paramètres propriétaires récursifs

Une signature admet un paramètre récursif par `A<T>` en emprunt
partagé ou par transfert. L’inventaire symbolique s’arrête au
premier type répété sur chaque chemin. Il permet de lire la variante
et les champs scalaires à cette profondeur, ainsi que de restituer
ou de détruire la valeur entière. Le runtime nettoie l’arbre réel.
Les resets de sources injectées sont refusés dans ces fonctions,
y compris si l’effet provient d’un appel.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
La nouvelle régression lit `7` après projection, restitue une
chaîne de trois nœuds à la même adresse, puis détruit la chaîne
de la feuille vers la racine et réutilise le slot pour `9`.
Le vérificateur refuse le reset de la feuille avant destruction.
Retirer le contrôle des effets de reset laisse passer une signature
qui réinitialise un pool potentiellement partagé avec un descendant
non suivi. Aucun modèle indépendant dédié. Les paramètres mutables
et les projections au-delà de la première répétition restent ouverts.

## F1 et B4 — Projection partagée récursive à la demande

La vérification symbolique crée des vues partagées lorsqu’un
corps projette un champ au-delà du premier type répété. Chaque
projection est identifiée par son porteur et son champ. Ces
vues ne rejoignent pas l’inventaire de destruction, et le C
généré utilise les champs de l’objet réel.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan
fatal. Le test de paramètre inspecte maintenant une chaîne de
trois nœuds et lit la valeur de la feuille, puis vérifie le
relais par transfert, la destruction et le réemploi du slot.
Désactiver la projection à la demande fait refuser la lecture
imbriquée au contrôle du corps. Aucun modèle indépendant dédié.

Les projections mutables, l’extraction consommante au-delà de
l’inventaire initial et les resets de pools injectés restent
hors de cette couverture.

## F2, B4 et H1 — Extraction consommante récursive

Un match consommant dans une fonction peut détacher un champ
propriétaire au-delà du premier type répété. Le corps reçoit une
allocation suivie dans le scope du bras et peut la consommer à
son tour. La provenance symbolique des projections possibles
continue avec l’enfant détaché.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le nouveau scénario consomme trois nœuds, lit `7`, puis réutilise
le slot terminal pour `9`. Les traces montrent une destruction
par nœud. Un accès à la racine après son transfert est refusé.
Supprimer la propagation de l’inventaire de projection fait
échouer le contrôle de la deuxième extraction. Aucun modèle
indépendant dédié. Le retour du champ récursif extrait et les
projections mutables restent ouverts.

## F2, B4 et H1 — Mutation en place à travers un paramètre récursif

Un paramètre récursif peut être emprunté avec `&mut`. Les projections
du match suivent à la demande les champs propriétaires au-delà du
premier type répété. Elles autorisent les écritures dans le contenu
sous le contrôle de l’emprunt. L’inventaire de nettoyage reste
attaché au porteur.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le nouveau cas modifie la feuille à travers un relais, lit `9`
à son adresse initiale et observe une seule destruction. Un emprunt
partagé utilisé après l’appel bloque cet accès mutable. Désactiver
la projection profonde pour le match mutable fait échouer le test.
Aucun modèle indépendant dédié. La suite complète lancée au cycle
des contrats imbriqués a terminé avec 1 339 tests réussis en
631,727 secondes. Le remplacement de handles récursifs en profondeur
et le retour de l’enfant extrait restent ouverts.

## F2, B4c et H1 — Retour d’un enfant propriétaire extrait

Le contrat peut identifier le résultat par un chemin de champ
dans un paramètre transféré. Le relais propage le chemin. Le
vérificateur retrouve les provenances de l’enfant et son
inventaire propriétaire chez l’appelant.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le nouveau scénario consomme un porteur, renvoie son enfant
récursif à la même adresse, lit `7` et réutilise le slot terminal
pour `9` après drop. Le reset prématuré du pool d’un descendant
est refusé. Remplacer le chemin par un champ inexistant fait
échouer le contrôle de provenance. Aucun modèle indépendant dédié.
Les compositions de plusieurs extractions, l’installation d’un
résultat extrait dans un autre contrat et le remplacement profond
d’un handle récursif restent à valider.

## F2 et B4c — Composition des extractions récursives

Une jonction entre un enfant extrait et une allocation neuve
conserve l’identité symbolique de chaque origine récursive. Une
seconde extraction peut retrouver le même descendant à partir du
chemin du contrat et de l’inventaire du corps.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le nouveau scénario extrait deux fois dans une chaîne et restitue
sa feuille à la même adresse avec la valeur `7`. L’autre scénario
part d’une valeur terminale, crée deux remplaçants successifs et
affiche `9` dans un pool de capacité un. Revenir à une identité
symbolique fondée sur l’ensemble joint des origines fait échouer
la vérification du relais. Aucun modèle indépendant dédié.

L’installation d’un enfant extrait dans un autre contrat et le
remplacement profond d’un handle récursif restent ouverts.

## F2, B4 et B4c — Réinstallation d’un enfant extrait

Un contrat de résultat ou de mise à jour mutable peut désormais
identifier un champ installé par le chemin d’extraction dans un
paramètre transféré. La copie de l’inventaire recalcule les pools
des descendants à partir de l’arbre.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Le nouveau scénario insère l’enfant dans un résultat neuf ou
remplace un champ d’un paramètre mutable. Les deux chemins lisent
`7` à l’adresse d’origine. Le remplacement libère l’ancien pool,
et le reset du pool de la feuille encore contenue est refusé.
Supprimer le recalcul des pools descendants fait échouer le contrôle
du contrat. Aucun modèle indépendant dédié. La suite complète
a été relancée. Le remplacement d’un champ via une projection
récursive profonde reste ouvert.

## F2, B4 et H1 — Remplacement depuis un bras de match mutable

Le contrat d’une fonction recevant un enum par `&mut` peut suivre
le champ propriétaire projeté par un bras, puis remplacer un champ
du porteur projeté. Un relais conserve le chemin de variante.
L’appel ignore le chemin si la variante requise est absente
de l’inventaire de l’argument.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
Avec la variante terminale, le remplacement détruit une fois
l’ancienne feuille, affiche `8` et protège le nouveau pool contre
un reset. Avec la variante maillon, le même appel laisse le champ
intact et autorise le reset du pool de remplacement. Supprimer
le filtrage par variante fait refuser ce dernier appel.
Aucun modèle indépendant dédié.

La jonction reste conservatrice sur l’ancien pool lorsque la variante
terminale est possible. Le remplacement au-delà du premier type
répété dans un paramètre récursif reste ouvert.

## F2, B4 et H1 — Remplacement au-delà du premier type répété

L’analyse du contrat développe les chemins propriétaires demandés
par les projections mutables. Le vérificateur matérialise ces
chemins dans l’inventaire symbolique avant de contrôler les états
de sortie. Aux jonctions, un chemin découvert dans une branche
conserve sa provenance d’entrée dans les branches qui l’ignorent.

Trois tests ciblés passent sous Clang C11 à `-O2` avec UBSan fatal.
La régression de match mutable modifie une feuille située après
un type répété, à travers un relais, et affiche `9`. Elle vérifie
la destruction unique de l’ancienne feuille et refuse le reset
du nouveau pool. Sans la complétion des chemins d’entrée à la
jonction, la comparaison du corps au contrat échoue.
Aucun modèle indépendant dédié. La suite complète précédente est en cours.

## PR1 — Retrait de reset du profil par défaut de la CLI

Les commandes `check`, `effects`, `emit-c`, `build` et `run`
refusent désormais l’opération collective de source `reset()`
dans le profil par défaut. Le contrôle s’applique aussi au corps
d’une fonction inutilisée. L’exemple principal passe par `drop`
et la fermeture du scope. Les exemples historiques restent
reproductibles avec `--legacy-reset`.

Les six tests CLI ciblés passent, ainsi que le test historique
des contraintes via `effects`. La régression vérifie le refus
dans les cinq commandes et exécute le remplacement d’une valeur
dans un pool de capacité un par drop puis allocation. Le binaire
affiche `9`, puis les traces confirment le nettoyage de chaque
valeur et le réemploi du slot. L’exemple principal affiche `42`.
Supprimer le contrôle PR1 dans une copie du compilateur fait
accepter l’exemple reset historique sans option.

Les API Python conservent le profil historique par défaut pour
la suite de régressions. Elles appliquent PR1 avec
`allow_legacy_reset=False`. Le retrait de l’ancien runtime
et la migration des exemples et tests historiques restent ouverts.

## PR1 — Séparation des fonctions C de reset

Le runtime du profil par défaut émis par la CLI ne contient plus
`source_reset` ni `cell_drop_for_reset`. Les fonctions de reset sont
ajoutées pour le profil historique. La fermeture et les destructions
ordinaires utilisent le même runtime de base dans les deux profils.

Les six tests CLI passent. L’oracle direct de pools exécute
3 000 opérations par profil sous UBSan fatal, contrôle les listes
et les slots à chaque étape, puis valide leur nettoyage final.
L’exemple historique s’exécute encore avec l’option et réutilise
l’adresse de son allocation. Forcer l’ajout du fragment historique
fait réapparaître les deux fonctions dans le C par défaut, ce que
la régression de la CLI détecte.

Les fonctions Python conservent le profil historique par défaut.
La migration de leurs appels et la suppression de la compatibilité
historique restent ouvertes.

## PR1 — Profil Python par défaut

`Compiler`, `verify_program`, `compile_program` et `compile_source`
appliquent PR1 par défaut. Les suites et outils de validation
qui contiennent des programmes historiques activent explicitement
`allow_legacy_reset=True`. Les oracles historiques gardent leurs
programmes, diagnostics et sorties attendues.

Les tests ciblés Python et CLI passent. Les entrées refusent le
même programme historique par défaut et l’acceptent sur demande.
Le C par défaut omet les fonctions de reset. L’oracle indépendant
de pools passe aussi sous UBSan fatal dans les deux profils.
Restaurer le profil historique par défaut pour `verify_program`
fait échouer la régression (`Error not raised`).
La suite complète a été lancée après le changement de profil.
Le code historique reste disponible par option explicite.

### Correctif de l’adaptation de la suite historique PR1

La suite complète a révélé que les adaptateurs de profil historique
avaient perdu le nom des fonctions, utilisé par les sous-tests.
Les adaptateurs conservent désormais ces métadonnées avec
`functools.update_wrapper`. Les suites touchées ont été relancées.

Le test CLI historique `effects` demande désormais explicitement
`--legacy-reset`. La suite complète lancée avant le changement
de profil PR1 avait terminé avec 1 347 tests réussis.
