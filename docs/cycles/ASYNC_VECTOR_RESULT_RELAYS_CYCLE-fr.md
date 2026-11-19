[English](ASYNC_VECTOR_RESULT_RELAYS_CYCLE.md)

# Cycle — Relais des Result contenant un vecteur async

## Règles et périmètre

Suite de ASYNC_VECTOR_PUBLIC_HANDLES_CYCLE.md. AS8–AS12, H1–H3, VE1–VE4,
F2–F4, B1–B5/B4c et D1–D3 restent inchangées. AGENTS, guidelines et index des
décisions relus ; les règles normatives de restitution et provenance ont été
consultées. Pas de nouvel arbitrage ni de modification normative.

Un Result reçu après l’attente d’une tâche peut être transféré explicitement à
une fonction qui le restitue. Son enveloppe ne change ni les sources du vecteur,
ni les emprunts portés par ses éléments, ni la responsabilité de nettoyage.

## Défauts et corrections

Le programme enregistré dans `validation/open-async-vector-result-relay.crust`
échouait aux deux entrées sur l’invariant d’inventaire des pools d’éléments.
Le paramètre Result contenant un vecteur reçoit maintenant le même inventaire
symbolique que sa charge propriétaire. Les chemins de vérification par contrat
et de génération C restituent les métadonnées de stockage et les prêts des
charges, y compris des descendants possédés.

Un relais supplémentaire révélait ensuite un reclassement de join_owned en
owned par l’analyse des résultats. Le mode déclaré est désormais conservé.
Les paramètres Result de l’analyse de contraintes et de provenances conservent
aussi l’inventaire des éléments. Aucun invariant interne n’a été désactivé.

Le diagnostic d’argument sans flèche conserve « mode attendu » et précise
maintenant qu’un transfert -> explicite est requis pour les modes propriétaires.

## Scénarios exécutés

Cinq nouvelles méthodes : **6 exécutions C**, dont une avec échec de soumission
injecté, et **7 programmes invalides** vérifiés par verify_program et
compile_source, soit 14 contrôles de refus.

- Relais direct après wait, résultat nommé avant consommation ; destruction
  anticipée de la cible refusée, argument sans -> refusé.
- Deux relais successifs ; le résultat garde sa charge et son prêt.
- Champ &mut Int : drop, lecture et écriture incompatibles après relais refusés.
- Item possédant Inner empruntant n : valeur 7, une destruction Inner.
- Vecteur vide : longueur zéro ; échec de lancement : Err et une destruction
  Item, sans exécuter la tâche.

Les quatorze méthodes des deux lots précédents sont rejouées : **19 méthodes,
7,559 s, code 0**, O0/UBSan fatal. Au total, cette passe représente 19 exécutions
C et 22 invalides aux deux entrées. Les invalides ne sont pas exécutés.
Harnais C11/pthread, Wall/Wextra/Werror, UBSan non récupérable.

Journaux `validation/async-vector-result-relays-targeted-*-o0.log` :

- first : 19 méthodes, 7,232 s, échec. Deux contrôles refusaient correctement le
  programme sans flèche mais le diagnostic ne précisait pas le transfert ;
  diagnostic enrichi. Le relais successif perdait le mode du Result.
- second : 19 méthodes, 7,074 s, échec : inventaire symbolique des éléments
  absent dans l’analyse des contraintes du relais successif.
- third : 19 méthodes, 7,559 s, succès.

## Régression

Terminée : **289 méthodes, 240,778 s, code 0**, O2/UBSan fatal.
Journal : `validation/async-vector-result-relays-regression-o2.log`.
Sélection dans `validation/async-vector-result-relays-test-selection.txt`.
Empreintes du manifeste confirmées après la passe : compilateur et tests
inchangés durant son exécution. Modèles existants de stockage, durée de vie
et Select rejoués, sans nouveau modèle indépendant des graphes de résultat.

## Artefacts et limites

Snapshot : `/tmp/crust-before-async-vector-result-relays`.
Patches et empreintes : `validation/async-vector-result-relays-changes.json`.
Test : `tests/test_async_vector_result_relays.py`.
C du cas direct : `validation/async-vector-result-relays.c`.

Les trois journaux exploratoires first/second/third conservent les refus avant
les corrections successives. Les graphes restent conservatifs par chemin []
et provenance. Pas de nouveau modèle indépendant, ni campagne de mutations,
ASan ou TSan ; les modèles existants sont inclus dans la régression sélectionnée.
Reset reste retiré. Ce lot ne constitue pas une preuve générale de sûreté.

Prochain cas : `validation/open-async-vector-result-capture.crust/.log`.
Capturer le Result dans une nouvelle tâche qui le restitue perd encore les
éléments du vecteur à la réception (remove le croit vide), aux deux entrées.
C’est un écart d’implémentation d’une règle déjà retenue. L’objectif global reste
ouvert, avec les autres écarts de la checklist.
