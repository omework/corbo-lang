[English](ASYNC_VECTOR_PAYLOAD_GRAPHS_CYCLE.md)

# Cycle — Graphes des éléments de vecteurs dans les états async

## Portée et règles

Suite de VECTOR_PAYLOAD_CONTAINERS_CYCLE.md. H1–H3, VE1–VE4, B1–B5/B4c,
D1–D3, F2–F4, AS2/AS5/AS8–AS14 restent inchangées. AGENTS.md,
VALIDATION_GUIDELINES.md, l’index des brouillons et les règles concernées ont été
consultés. Ce lot raccorde des règles déjà retenues ; aucun changement normatif.
La validation suit les cas énumérés et les régressions directement concernées.

Les vecteurs de handles peuvent capturer des objets à champs empruntés et des
descendants propriétaires. L’état utilise toujours les Cell et destructeurs
existants. Les métadonnées ajoutées sont statiques ; ni adresse déplacée ni
graphe d’emprunts ajouté au runtime.

## Implémentation

- Les chemins de références propriétaires traversent aussi les éléments de
  Vector<A<T>>, sous la projection virtuelle `[]/`. Le parcours concret des
  dépendances descend dans les charges effectivement présentes.
- Les contrats de fabriques et relais de tâches conservent ces références avec
  leur mode, ainsi que les pools des éléments, distincts du pool du vecteur.
- Le backend async conserve les prêts des valeurs insérées dans le vecteur.
  Remove/pop les transmettent à la charge extraite. Replace/try_push décrivent
  séparément les prêts des charges Ok et Err ; l’extraction sélectionne le bras.
- Le match d’une option vide efface les prêts du résultat vide. Les chemins
  d’un vecteur concrètement vide sont absents : un contrat générique ne leur
  invente pas une cible à la réception.
- Les captures et transferts vers une tâche enfant conservent les mêmes prêts.
  Une tâche inactive détruite nettoie ses captures sans exécuter son corps.

Les graphes locaux de vecteurs sont joints de manière conservative. La suppression
n’établit pas systématiquement quelle cible a disparu d’un vecteur encore vivant.
Les tests détruisent le vecteur avant de vérifier la libération des prêts restants.
La précision générale par indice/branche reste à compléter.

## Défauts rencontrés et corrigés

Lever seulement la restriction de signature permettait de compiler le cas admis,
mais perdait les prêts lors d’une capture et d’une insertion locale. Les variantes
avec drop anticipé ou accès concurrent à une cible mutable étaient acceptées.
Elles n’ont pas été exécutées. Les tests les refusent maintenant aux deux entrées.

Une fabrique conservait le pool du vecteur mais perdait celui d’un élément : une
tâche pouvait sortir du bloc de ce pool. L’inférence inclut désormais le stockage
des charges. À l’inverse, un vecteur vide était refusé par le contrat générique,
faute de cible de champ : les chemins prouvés absents sont désormais reconnus.

L’option vide conservait un prêt fictif après match. La consommation de None le
retire. Les champs de la charge Some sont transmis au receveur avant consommation.

## Tests ciblés

Douze méthodes : **15 exécutions C**, **18 programmes invalides** vérifiés avec
verify_program et compile_source (36 vérifications de refus).

- Capture propriétaire directe et fabrique ; drop avant join refusé.
- Vecteur local puis élément extrait : lecture après destruction du vecteur,
  suspension, nettoyage et réemploi ; drop de la cible avant extraction et après
  destruction du vecteur refusé.
- Champs &mut Int dans capture et vecteur local : accès concurrents refusés.
- Item possédant Inner empruntant Int : lecture par un helper et nettoyage.
- Relais d’une tâche inactive : corps non exécuté, deux destructions Item avec
  réemploi ; cible protégée jusqu’à destruction de la tâche.
- Vecteur capturé par &mut : extraction après suspension et attente.
- Pool des éléments trop court : refus direct et à travers une fabrique.
- Pop puis match : la référence survit à la destruction du vecteur et à yield.
- Replace avec indice valide/invalide : sorties 7/8, cible du résultat protégée.
- Parent async transférant le vecteur à un enfant : cible protégée jusqu’à await.
- Vecteur vide direct et par fabrique : longueur 0, sans dépendance fictive.
- Try_push réussi : Ok(()) ne conserve pas une charge fictive, le vecteur garde
  la référence de la valeur effectivement insérée.

Les fixtures intermédiaires ont été corrigées : flèche de champ `<-`, accès au
descendant par helper, absence de double drop et consommation locale au bon scope.
Les premiers refus dus à ces erreurs de fixture ne prouvaient pas la protection
recherchée. Les oracles finaux utilisent les mêmes invariants, sans les affaiblir.

## Exécutions

Journaux `validation/async-vector-payload-graphs-*` :

- first-o0 : le cas admis historique s’exécute ; son premier refus comportait
  encore un double drop et ne prouvait donc pas le refus au bon endroit.
- targeted-first : quatre méthodes, 2,783 s, échec ; pertes de prêts et fixtures.
- targeted-second : quatre méthodes, 2,505 s, échec ; fabrique et fixture imbriquée.
- targeted-third : quatre méthodes, 2,863 s, succès.
- targeted-fourth : huit méthodes, 3,752 s, échec ; source de l’élément et fixture pop.
- targeted-fifth : huit méthodes, 3,805 s, échec ; fixture pop hors du bon scope.
- targeted-sixth : huit méthodes, 3,559 s, échec ; prêt fictif après None.
- targeted-seventh : neuf méthodes, 4,789 s, échec ; tentative de double consommation
  de None, corrigée dans son opération de consommation existante.
- targeted-eighth : dix méthodes, 5,433 s, succès.
- targeted-ninth : douze méthodes, 6,270 s, échec ; vecteur vide en fabrique.
- targeted-tenth-o0 : **12 méthodes, 6,901 s, code 0**.
- regression-o2 : **264 méthodes, 260,741 s, code 1** ; huit sous-échecs du
  test qui attendait encore le refus des quatre formes de vecteurs, et deux
  sous-échecs d’une fixture Mixed/A<Mixed> antérieure au lot.
- baseline-mixed-fixture : même test exécuté avec le snapshot du compilateur
  d’avant ce lot, une méthode, 0,167 s, mêmes deux sous-échecs.
- corrected-o2 : **14 méthodes, 11,408 s, code 0** : les douze méthodes ciblées
  et les deux méthodes historiques corrigées. Le compilateur n’a pas changé
  entre la régression et ce complément. La première fixture exécute désormais
  ses quatre formes admises (captures et pools locaux vides). La seconde
  annonce A<Mixed> pour sa valeur en pool ; son modèle conserve les huit
  dispositions de durées de vie et les deux voies d’appel.

Il s’agit d’une régression complétée par le rejeu des fixtures corrigées, pas
 d’une passe monolithique de 264 tests annoncée verte. La sélection exacte est
 dans le fichier test-selection.txt associé.

Harnais : C11, pthread, Wall/Wextra/Werror, UBSan fatal, O0 puis O2.
Les modèles antérieurs de durées de vie (huit dispositions) et de stockage
(quatre configurations) sont inclus dans la régression. Ils ne sont pas des
modèles indépendants nouveaux des graphes de vecteurs async. Pas de nouvelle
campagne de mutations, ASan ou TSan dans ce lot.

Snapshot : `/tmp/crust-before-async-vector-payload-graphs`. Patches et empreintes :
`validation/async-vector-payload-graphs-changes.json`. L’ancien refus de
`open-async-vector-payload-graph.crust` reste conservé comme preuve historique.

## Écart suivant identifié

`validation/open-async-vector-payload-sync-call.crust/.log` décrit une insertion
par fonction synchrone appelée depuis async. Le programme admis et sa variante
avec destruction prématurée de la cible sont actuellement acceptés aux deux
entrées. Le programme invalide n’a pas été exécuté. Les effets de graphe des
écritures de vecteurs ne sont pas encore publiés dans l’état async au retour
de cet appel. Cette correction reste nécessaire ; le lot ne prouve donc pas
la sûreté de tous les appels mêlant fonctions et collections async.

Retours async de conteneurs entiers, références nominales et compositions
récursives générales restent ouverts. Reset demeure retiré du profil normal.
L’objectif global reste actif, sans revendication de sûreté générale.
