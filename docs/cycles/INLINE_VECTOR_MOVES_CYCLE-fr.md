[English](INLINE_VECTOR_MOVES_CYCLE.md)

# Cycle — Transferts nommés vers Vector<T>

## Règles et périmètre

VE1/VE2, H1, T1/T4/T5, B1–B5 et AS2/AS8 restent inchangées.
AGENTS.md, VALIDATION_GUIDELINES.md et l’index des sept brouillons ont été
relus avant la validation, ainsi que les règles pertinentes de
LANGUAGE_RULES.md, FOUNDATIONS_AND_VECTORS.md et STRUCTURES_METHODS.md.
La spécification complète a été lue dans le travail continu précédent.
Aucun arbitrage ni changement normatif dans ce lot.

Une valeur locale nommée peut être transférée par `v.push(->point)` dans
un Vector<Point>. Son ancien accès devient inutilisable. Un A<Point>
n’est pas converti implicitement en Point ; les emprunts actifs interdisent
le déplacement. Le transfert depuis un scope extérieur exige les étapes
explicites déjà retenues.

Le périmètre reste celui des structures à feuilles Int, imbriquées ou vides.
Les autres champs, opérations et vues restent ouverts ; ce lot ne clôt pas VE1–VE6.

## Défauts et implémentation

Les deux programmes minimaux sync/async étaient refusés parce que push
n’acceptait que la forme AST des constructions/copies, pas le transfert d’un
nom. Le journal inline-vector-moves-baseline.log conserve ces refus.

Le vérificateur et l’abaissement async reconnaissent désormais le transfert
nommé, vérifient sa provenance locale et invalident son ancien accès.
Le vecteur reçoit les octets des champs, puis le stockage de la valeur
consommée est nettoyé. Aucun changement du runtime C.

L’analyse de contrats déduit l’exigence de stockage local de l’argument de
push à partir du type réel du receveur Vector<T>. Elle réutilise les valeurs
déjà évaluées : aucune seconde évaluation de l’argument transféré. Cette
exigence se propage aux relais synchrones et aux captures async. Les tests
vérifient aussi le contenu des contrats et le refus d’un A<Point> appelant.

Les tests ont révélé deux raccordements manquants supplémentaires : le
réemprunt explicite `&mut *v` dans le relais, et la représentation Cell du
vector emprunté dans le pont C d’un appel synchrone depuis une tâche.
Ils sont corrigés sans rendre les emprunts implicites.

## Validation ciblée

Sept méthodes de tests/test_inline_vector_moves.py : **15 exécutions C** et
**19 programmes invalides**, chacun vérifié avec verify_program et
compile_source. Passage final O0/UBSan : **7 méthodes, 5,287 s, code 0**,
validation/inline-vector-moves-targeted-fourth.log.

- Ancien nom lu/détruit après transfert et flèche manquante refusés.
- Dernier usage de l’emprunt avant push accepté ; usage après push refusé.
- Relais synchrone appelé depuis main ou une tâche ; exigences locales
  enregistrées dans les deux contrats ; A<Point> refusé.
- Capture propriétaire d’un Point avec vector emprunté mutablement,
  suspensions avant/après insertion ; ancien Point et vector réservé refusés.
- Entrée explicite dans un bloc enfant ; valeur créée dans le bloc enfant ;
  absence de transfert descendant refusée.
- Extraction puis transfert entre deux vectors dans une boucle, nettoyage
  et réemploi du pool ; structures imbriquées et vides.

Les passages ciblés précédents sont conservés : premier (deux échecs de
stockage), deuxième (réemprunt refusé), troisième (pont C non raccordé).
Les attentes des programmes n’ont pas été modifiées pour suivre ces refus.

Compilation native par le harnais existant : C11, pthread,
Wall/Wextra/Werror, UBSan fatal ; optimisation O0 en ciblé et O2 en régression.
Les refus statiques ne sont pas exécutés nativement.

## C généré et traçabilité

Les fichiers validation/inline-vector-moves-sync.c et -async.c sont conservés.
Dans le cas synchrone, vector_push lit les champs avant cell_drop de la source ;
la copie ensuite extraite survit au drop du vecteur. Dans le cas async, le
champ propriétaire de l’état est remis à NULL avant l’insertion ; le temporaire
est détruit puis remis à NULL, empêchant son second nettoyage à la fin de
l’état. Ces inspections ne prouvent pas tous les chemins possibles.

Snapshot initial : /tmp/crust-before-inline-vector-moves.
Diff et empreintes : validation/inline-vector-moves.patch et -changes.json.
Sélection de régression : validation/inline-vector-moves-test-selection.txt.
Empreintes avant régression : validation/inline-vector-moves-regression-start.json.

## Régression et limites

Le premier passage O2/UBSan a exécuté 126 méthodes en 77,308 s (code 1).
Un test a échoué aux deux entrées uniquement sur le texte du diagnostic :
le contrôle de stockage refusait correctement A<Point>, mais affichait des
noms génériques T/A<T>. Le diagnostic indique maintenant aussi le type nominal.
L’attente du test existant reste inchangée. Journal :
validation/inline-vector-moves-regression.log ; empreintes inchangées pendant
ce premier passage dans -first-integrity.log.

La même sélection a réussi après cette précision du diagnostic : **126 méthodes,
77,073 s, code 0**, validation/inline-vector-moves-regression-final.log.
Les **44 empreintes** du compilateur et des modules sélectionnés sont restées
inchangées pendant ce passage (-regression-final-start.json, -integrity.log).
La sélection couvre les trois lots précédents de structures en ligne, les
contrats de stockage, captures locales async, contrats de charges de vecteurs,
vecteurs de handles sync/async, type features, retours stricts T/A<T> et le
match consommant de join. Le modèle cartésien indépendant des signatures de
type features, déjà présent dans cette sélection, a également réussi.
Aucune campagne de mutations ou recherche adversariale étendue dans ce lot,
conformément à la priorité utilisateur. Aucun nouvel oracle indépendant du
modèle de stockage ; les sorties attendues, diagnostics et inspections C
couvrent les cas énumérés. Aucun résultat supposé du lab indépendant.
Les passages réussis ne constituent pas une preuve générale de sûreté.
