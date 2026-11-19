[English](INLINE_VECTOR_NOMINAL_CYCLE.md)

# Cycle — Références nominales dans les cases de Vector<T>

## Règles et périmètre

VE1–VE3, ST7/ST11–ST18, B1–B5, T4/T5/T6 et AS2/AS8/AS11–AS13
restent inchangées. Les consignes de validation et l’index des brouillons ont
été relus dans cette continuation, ainsi que FOUNDATIONS_AND_VECTORS.md et
STRUCTURES_METHODS.md. La spécification complète a été lue dans le travail
continu. Aucun choix normatif nouveau ni modification de règle.

Le lot précédent a raccordé les graphes d’emprunts dans les cases en ligne.
Ce lot raccorde leur représentation existante pour les références nominales,
notamment les cibles entières et sous-structures. Les champs propriétaires
et les autres opérations de vector restent ouverts.

## Implémentation et baseline

validation/inline-vector-nominal.crust était refusé par verify_program et
compile_source pour une restriction explicite de layout : baseline conservée
sous le même préfixe. Le snapshot initial est dans
/tmp/crust-before-inline-vector-nominal, sans duplication des caches Python.

Les deux générateurs acceptent désormais les champs références déjà représentés.
Le chemin async exige aussi que la structure appartienne aux layouts reconnus.
La copie des références mutables reste refusée. Le suivi des dépendances,
les contrats et les graphes de capture du lot précédent sont réutilisés.
Aucune conversion entre T et A<T>, aucune allocation de cible, aucun changement
runtime n’est introduit.

## Vérifications exécutées

Ciblé O0/UBSan : **11 méthodes, 4,833 s, code 0**, soit 11 exécutions C
réussies et 20 variantes invalides vérifiées aux deux entrées.
Journal : validation/inline-vector-nominal-targeted.log.
Le premier passage avait aussi découvert neuf tests importés du lot précédent :
20 méthodes, 8,771 s, code 0. L’import du module a été corrigé pour que le
nouveau ciblé n’exécute que ses propres classes, sans changer les assertions.

Cas admis : référence nominale entière et intérieure, copy/remove, destruction
du porteur et du vector avant lecture de la cible, champ distinct mutable,
réemprunt mutable, construction dans un enfant, structure imbriquée, insertion
injectée, copie/retour et relais de remove, corps async avec yield, capture
propriétaire et résultat extrait par join, réemploi du slot de vector.

Cas refusés : mutation/destruction de la cible avant dernier usage, destruction
du porteur pendant un réemprunt mutable, copie d’un champ mutable, cible enfant
trop courte, destruction de la cible avant join et avant lecture du résultat.

Régression O2/UBSan : **121 méthodes, 79,234 s, code 0**, dans
validation/inline-vector-nominal-regression.log. Les 44 empreintes du compilateur
et des tests sont inchangées pendant le passage, contrôle consigné dans
-integrity.log. La sélection et les empreintes initiales sont conservées dans
-selection.txt et -start.json. Le diff du lot et les empreintes avant/après
sont dans -nominal.patch et -nominal-changes.json.

Les familles rejouées couvrent les vectors en ligne, leurs contrats et captures,
les références nominales stockées, les retours async et les projections récursives.
Aucun échec nouveau dans cette sélection.

## Inspection de la traduction

Le C conservé dans validation/inline-vector-nominal.c utilise
sizeof(CrustStructureView) pour chaque référence nominale et le code de champ
3. Le descripteur garde la racine et le décalage d’une cible intérieure. Les
cases reçoivent les octets du layout ; remove les restitue dans une structure
locale. Les accès aux champs passent par les primitives memcpy existantes ;
les cases ne sont pas déréférencées en tant que tableaux C de descripteurs.
Le nettoyage des porteurs ne détruit pas les cibles empruntées. Les tests sur
sous-structures vérifient le décalage et la réservation des chemins.

## Limites

Les preuves portent sur les cas énumérés, sans preuve générale de sûreté.
Le suivi conservateur des positions après certains appels/branches reste celui
du lot précédent. Les références récursives et tous les types nominaux ne sont
pas déclarés couverts par ces exemples. Les champs propriétaires, pop/replace,
try_push, tranches et push_new de structures en ligne restent à raccorder.
Reset reste retiré par défaut. Pas de campagne de mutations ni de recherche
adversariale étendue ; aucun résultat du lab indépendant n’est supposé.
C natif C11/pthread, Wall/Wextra/Werror et UBSan fatal via le harnais existant.

## Prochain écart reproduit

validation/inline-vector-owned.crust contient Item{value:A<Int>}, un push,
un remove, la destruction du vector puis celle du résultat et le réemploi du
pool Int. Les deux entrées le refusent encore explicitement :
validation/inline-vector-owned-baseline.log. Ce cas demeure ouvert ; le nettoyage
des descendants devra être transféré avec la case, sans détruire les enfants
lors de la libération du porteur local consommé.
