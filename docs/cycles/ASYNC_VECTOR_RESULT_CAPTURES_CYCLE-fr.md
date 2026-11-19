[English](ASYNC_VECTOR_RESULT_CAPTURES_CYCLE.md)

# Cycle — Captures et réceptions imbriquées de Result de vecteurs

## Règles et portée

Suite de ASYNC_VECTOR_RESULT_RELAYS_CYCLE.md. AS8–AS12, H1–H3, VE1–VE4,
F2–F4, B1–B5/B4c, D1–D3 et T4 restent inchangées. Consignes et guidelines
lues dans le travail continu ; AGENTS et index des décisions relus. Les règles
normatives de restitution, provenance et transfert descendant ont été consultées.

Un Result transféré dans l’état d’une tâche peut être restitué. L’attente ajoute
une enveloppe Result ; la consommation des enveloppes conserve les sources et
les prêts de la charge, ainsi que sa responsabilité de nettoyage. Le passage
par une branche ou une sortie de boucle ne doit pas perdre ce graphe.

## Défauts et corrections

Le cas `validation/open-async-vector-result-capture.crust` perdait les éléments
au receveur. La trace montre que le join portait bien l’inventaire [] ; celui-ci
était perdu à la réunion des branches du match, laquelle ne conservait que les
champs propriétaires ordinaires. Cette réunion conserve désormais aussi les
métadonnées des éléments de vecteurs.

Le déballage d’une enveloppe intermédiaire ne conservait que les prêts directs
du porteur. Les prêts des éléments et descendants sont maintenant restitués,
avec leurs chemins, lors du déballage, de la réunion de branches et de la
réception d’un résultat de boucle.

Le test d’enveloppes successives a révélé un deuxième point : le backend async
ne collectait les prêts par champ que pour une capture owned, sans le faire
pour un Result propriétaire. Ces modes sont maintenant pris en charge lors du
transfert de l’argument à la tâche enfant.

Aucune modification normative ni du runtime ; aucun invariant désactivé.

## Scénarios ciblés exécutés

Sept méthodes nouvelles : **9 exécutions C**, dont un échec de soumission
injecté, et **9 programmes invalides** aux deux entrées du compilateur,
soit 18 contrôles de refus. Les invalides ne sont pas exécutés.

- Capture d’un Result après join, restitution et réception par match.
- Champ mutable : drop, lecture et écriture incompatibles refusés après réception.
- Item possédant Inner empruntant n ; valeur 7, une destruction Inner.
- Plusieurs enveloppes successives, avec spawn et await dans la tâche parent.
- Réception du Result par if et par break de boucle, avec transfert descendant
  explicite selon T4 ; prêts conservés après réception.
- Destruction d’une tâche inactive : corps non exécuté, charge nettoyée, slot de
  capacité 1 réutilisé ; deux destructions Item avec la nouvelle allocation.
- Vecteur vide : longueur zéro. Échec du second lancement : retour anticipé
  depuis Err, une destruction Item et aucune sortie standard.

Harnais C11/pthread, Wall/Wextra/Werror, UBSan fatal. Journaux sous
`validation/async-vector-result-captures-` :

- targeted-first-o0 : 25 méthodes, 10,304 s, échec du snippet if qui omettait
  l’injection `first ->;` exigée par T4. Snippet corrigé, règle conservée.
- targeted-second-o0 : 25 méthodes, 10,507 s, succès ; six nouvelles méthodes
  et dix-neuf méthodes des lots précédents.
- targeted-third-o0 : sept méthodes, 3,275 s, échec du nouveau cas d’enveloppes
  successives ; prêts absents de la capture du Result dans le backend async.
- targeted-fourth-o0 : **sept méthodes, 4,013 s, code 0**, après correction.

## Régression

Terminée : **296 méthodes, 244,806 s, code 0**, O2/UBSan fatal.
Journal : `validation/async-vector-result-captures-regression-o2.log`.
Sélection : `validation/async-vector-result-captures-test-selection.txt`.
Les empreintes du manifeste sont confirmées après la passe : compilateur et
tests inchangés pendant son exécution. Les modèles existants de stockage,
durée de vie et Select ont été rejoués, sans nouveau modèle indépendant.

## Artefacts et limites

Snapshot : `/tmp/crust-before-async-vector-result-captures`.
Patches et empreintes : `validation/async-vector-result-captures-changes.json`.
C du cas direct : `validation/async-vector-result-captures.c`.
Test : `tests/test_async_vector_result_captures.py`.

Les graphes sont conservatifs par chemin [] et provenance ; ce lot n’établit
pas une corrélation générale entre indices, branches et cibles. Pas de nouveau
modèle indépendant, campagne de mutations, ASan ou TSan. Les modèles existants
sont inclus dans la régression. Reset reste retiré. Les autres écarts de la
checklist restent ouverts ; ces résultats ne prouvent pas la sûreté générale.

## Prochains raccordements et contrôles d’inventaire

Les contrôles suivants n’ont exécuté que verify_program et compile_source :

- `open-async-vector-result-consumer.crust/.log` : consommation du Result dans
  une tâche, acceptée aux deux entrées ; exécution native non vérifiée ici.
- `open-vector-nominal-reference-payload.crust/.log` et sa variante
  `open-async-vector-nominal-reference-payload.crust/.log` : élément portant
  &Point, acceptés aux deux entrées ; ne prouvent pas leur exécution native.
- `open-inline-struct-vector.crust/.log` : Vector<Point> contenant la valeur
  directement, refusé aux deux entrées (« allocation Int »). VE1 distingue
  explicitement valeur et handle ; ce support reste à implémenter. Il n’est
  pas remplacé par Vector<A<Point>>.

Précision du cycle suivant : cet exemple historique comportait aussi une copie
implicite interdite par ST17. INLINE_STRUCT_VECTORS_CYCLE.md utilise copy(v[0])
et raccorde le premier périmètre de stockage direct, sans remplacer ce type
par un vecteur de handles.
