[English](INLINE_VECTOR_BORROWS_CYCLE.md)

# Cycle — Champs empruntés des structures dans Vector<T>

## Règles et périmètre

VE1–VE3, H1, T1/T4/T5/T6, B1–B5, ST17/ST18 et AS2/AS8/AS11–AS13
restent inchangées. AGENTS.md, VALIDATION_GUIDELINES.md et l’index des sept
brouillons ont été relus, ainsi que les règles pertinentes ; la spécification
complète avait été lue dans le travail continu. Aucun nouvel arbitrage ni
changement normatif. Reset reste exclu par défaut selon PR1.

Ce lot étend les structures en ligne aux champs Int, &Int et &mut Int,
y compris les feuilles de structures imbriquées. Les champs propriétaires,
références nominales générales, autres opérations et tranches restent ouverts.

## Défaut initial et implémentation

Les fixtures inline-vector-borrows-sync.crust et -async.crust étaient refusées
aux deux entrées ; baseline dans validation/inline-vector-borrows-baseline.log.

Les cases contiennent les octets des champs et les pointeurs empruntés, sans
prendre en charge la destruction des cibles. La représentation et les primitives
C existantes sont réutilisées. Le transfert invalide la source et nettoie son
ancien stockage ; sa durée de vie physique ne devient pas une dépendance du
vector. En revanche les cibles empruntées doivent survivre au receveur.

Le vérificateur suit les graphes d’emprunts par case. Remove transmet ces
emprunts au nouveau porteur ; copy copie les références partagées et refuse
les références mutables. Les analyses de résultats et de contraintes conservent
les champs, les effets d’insertion/extraction et les réemprunts des vectors.
Le pont C des appels synchrones depuis async construit le même graphe symbolique.

L’abaissement async conserve aussi les emprunts stockés. Les positions locales
connues permettent de relâcher seulement la case extraite. Les branches qui
n’établissent pas les mêmes positions, ainsi que les appels mutateurs, font
revenir à l’ensemble conservateur des cibles. Les snapshots de contrôle
conservent cet état ; on n’utilise pas un inventaire périmé après un appel.
Cette perte de précision peut encore refuser certains programmes valides.

## Défauts rencontrés pendant l’implémentation

Les premiers tests ont mis en évidence la perte des graphes dans les relais
par réemprunt, puis dans les paramètres du pont C. Ces chemins sont raccordés.
Un cas négatif async via un relais était masqué par un usage direct du nom
après drop. En retirant cet usage indépendant, le mauvais programme était
accepté aux deux entrées (inline-vector-borrows-contract-second.log).
Le chemin de l’argument vector était traité comme un pointeur scalaire par
l’extracteur de métadonnées ; le chemin d’emprunt d’agrégat est maintenant
utilisé et le refus ciblé passe. L’attente négative a été conservée.

Deux fixtures ont été corrigées : mutation via un réemprunt explicite nommé
plutôt qu’une méthode de champ non prise en charge, et lectures explicites
`*number` dans le code async. Le test de cible enfant utilise aussi la variable
extérieure pour ne pas être arrêté d’abord par U1. Ces ajustements n’altèrent
pas les comportements mémoire attendus.

## Tests ciblés exécutés

19 méthodes, **20 exécutions C réussies** et **32 variantes invalides** aux
deux entrées verify_program/compile_source. Passage O0/UBSan :
**19 tests, 8,776 s, code 0**, inline-vector-borrows-targeted-twelfth.log.
Les dernières précisions de diagnostic sont incluses dans la régression finale
terminée avec succès.

Cas : copies partagées après destruction du vector, extraction mutable,
interdiction de copier un champ mutable, deux cases et libération séparée,
cibles de scopes enfants, insert/take/relais, suspensions après drop du vector,
branches et boucles avec réemploi, champs imbriqués, résultat reçu dans le parent,
capture propriétaire et résultat local obtenu par join avec champ partagé ou mutable.

Refus : destruction/mutation des cibles avant le dernier usage, accès concurrent
à la cible mutable, copie interdite, cible trop courte, cible détruite avant
join ou avant usage du résultat extrait.

## Inspection C

C conservé pour les fixtures sync, async et capture. Les layouts empruntés
utilisent le code de champ 1 et sizeof(Cell *). Vector reçoit directement les
champs via vector_push ; le Cell local est nettoyé ensuite. Remove écrit dans
le nouveau Cell local ; le vector peut être détruit avant de lire le pointeur
emprunté de ce résultat. cell_drop ne détruit récursivement que les champs
propriétaires de code 2. Les cibles restent nettoyées séparément par leur scope.
Cette inspection complète les exécutions sans prouver tous les chemins.

## Régression, traçabilité et limites

Le premier passage O2/UBSan a exécuté **192 méthodes en 148,300 s**, avec deux
échecs : construction locale fraîche dans un vector injecté et capture locale
async. La propagation des écritures traitait à tort le slot local d’origine
comme un pool à retenir. Le slot inline garde désormais son propre stockage ;
les champs empruntés sont conservés séparément. Les analyses savent aussi
représenter les constructions fraîches de ces cases dans les effets d’appels.
La reproduction isolée est dans inline-vector-borrows-regressions-minimal.log.
Les deux cas sont conservés dans les tests existants ; un nouveau test couvre
la construction fraîche empruntante injectée, puis deux copies via fonction.

Le premier complément a exécuté **85 méthodes en 94,817 s**, avec un échec de
compilation d’une fixture C de Select. Son appel passait Cell * là où l’ABI
actuelle attend CrustStructureView. Le même échec est reproduit avec les fichiers
Python du snapshot initial : inline-vector-borrows-control-baseline.log.
Les deux arguments sont adaptés par structure_reference_for ; toutes les
assertions de sélection, de champs et de nettoyage sont conservées. La version
initiale reconstruite de cette fixture a la même empreinte que celle enregistrée
avant le premier complément. Les deux premiers passages ont conservé leurs
empreintes de compilateur/tests, consignées dans les journaux -first-integrity.log.

Ciblé complémentaire après corrections : **20 tests, 9,245 s, code 0** dans
-targeted-eleventh.log (17 tests du lot à ce stade et trois régressions).
Les 19 tests propres au lot ont ensuite réussi dans -targeted-twelfth.log.
Le passage intermédiaire -targeted-tenth.log conserve le défaut de résolution
d’une origine locale neuve corrigé ensuite.

Rejeux finaux O2/UBSan terminés, tous deux code 0 :
- sélection principale : **194 méthodes, 151,310 s**, -regression-final.log ;
- complément : **85 méthodes, 95,054 s**, -control-final.log.

Les empreintes compilateur/tests des deux sélections sont inchangées entre
leur lancement et leur fin ; journaux -regression-final-integrity.log et
-control-final-integrity.log. Les corrections ont été faites entre les passes,
jamais pendant leur exécution.

Snapshot initial /tmp/crust-before-inline-vector-borrows ; diff et empreintes
dans validation/inline-vector-borrows.patch et -changes.json. Les listes de
sélection et empreintes avant exécution sont conservées dans le même dossier.
C natif compilé par le harnais existant en C11, pthread, Wall/Wextra/Werror,
UBSan fatal. Les refus statiques ne sont pas exécutés nativement.
Aucune campagne de mutations ou recherche adversariale étendue dans ce lot,
conformément à la priorité utilisateur ; aucun résultat supposé du lab externe.
Les tests ne prouvent pas la sûreté générale ni la complétude de VE1–VE6.
