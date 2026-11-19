[English](VECTOR_PAYLOAD_OPTIONS_CYCLE.md)

# Cycle — Options d’éléments contenant des emprunts

## Portée normative

Suite de VECTOR_PAYLOAD_CONTRACTS_CYCLE.md. H1–H3, VE2–VE3, B1–B5/B4c,
D1–D3, F2–F4 et U1 restent inchangés. AGENTS.md et les guidelines ont été
relus, ainsi que l’index des sept brouillons, les fondamentaux des vecteurs et
les règles de contrats concernées. Les contrôles restent centrés sur les cas
énumérés et les régressions directes, conformément à la priorité utilisateur.

Ce lot raccorde les paramètres et résultats synchrones Option<A<Item>> lorsque
Item possède des références Int ou des descendants propriétaires représentables.
La responsabilité de nettoyage, les cibles empruntées et les sources des
objets possédés survivent au retour, au relais et au match consommant.
Aucun changement de représentation C ni de runtime.

## Implémentation et défauts rencontrés

Les paramètres symboliques d’options reçoivent leurs descendants propriétaires.
La réception d’un résultat optionnel reconstruit depuis le contrat ses références,
variantes et descendants, dans le vérificateur opaque comme dans la génération C.
Les contrôles existants de destination et de disposition restent actifs.

Un résultat statiquement vide ne reçoit pas de graphe fictif. La projection
`[]` d’un vecteur établi vide peut ne fournir aucune cible : ce fait correspond
à l’absence de charge, sans promotion d’une allocation.

Le cas vide imbriqué a révélé un refus dans l’analyse de contraintes : elle
parcourait le bras Some alors que les provenances établissaient None, puis
exigeait une allocation Inner pour un appel inaccessible. L’absence de charge
est maintenant propagée par pop et les contrats d’options. Le match abaissé
utilise ce fait pour les instructions et les expressions. Les autres étapes
continuent leurs vérifications et les corps des fonctions sont vérifiés avec
leurs paramètres symboliques ; aucun contrôle d’emprunt n’est supprimé.

## Scénarios exécutés

Sept méthodes ciblées : **13 exécutions C**, chacune précédée de verify_program
et compile_source, et **13 programmes invalides** refusés par ces deux entrées.

- Some et None, retour direct et relais d’une option transférée.
- Drop de la cible refusé avant le match et avant l’usage dans Some.
- Destruction du vecteur vide avant consommation de son ancien élément.
- Objet empruntant une cible trop courte refusé ; le pool doit survivre au
  résultat transféré vers un parent.
- Flèche obligatoire, usage explicite obligatoire, double consommation refusée.
- Référence mutable contenue : lecture ou écriture directe de la cible refusée
  avant le dernier usage du résultat.
- Item possédant Inner qui emprunte Int : retour, relais, lecture et destruction
  unique ; variante vide, y compris match produisant une valeur Int.
- Consommateur retournant l’objet reçu ou une allocation de secours issue d’un
  pool injecté ; les deux chemins sont exécutés et protègent la cible.

Les traces vérifient le nombre de destructions Item/Inner ; les pools de petite
capacité et les scénarios du lot précédent sont rejoués en régression.
Reset reste retiré du profil normal, sans réintroduction par ce lot.

## Exécutions et artefacts

- Baseline : cinq méthodes, 0,013 s, neuf échecs/sous-échecs attendus dus aux
  gardes d’implémentation, `validation/vector-payload-options-baseline-o0.log`.
- Premier essai : cinq méthodes, 2,868 s, deux échecs (garde des descendants et
  dépendances fictives de None), `vector-payload-options-first-o0.log`.
- Deuxième : cinq méthodes, 3,882 s, code 0.
- Troisième : sept méthodes, 4,751 s, code 0.
- Ajout du cas vide imbriqué : sept méthodes, 5,209 s, code 1 ; journal
  `vector-payload-options-final-o0.log` conservé malgré son nom historique.
- Après correction : sept méthodes, 5,326 s, code 0, journal fourth.
- Ciblé final O0 : **sept méthodes, 5,724 s, code 0**,
  `validation/vector-payload-options-targeted-final-o0.log`.
- Régression O2 : **152 méthodes, 150,976 s, code 0**, sélection
  `validation/vector-payload-options-test-selection.txt`, journal
  `validation/vector-payload-options-regression-o2.log`.

C11, pthread, Wall/Wextra/Werror et UBSan fatal. Le cas précédemment refusé
`validation/open-vector-payload-option-contract.crust` est désormais exécuté
par le test direct. Son ancien journal reste une preuve historique du refus.
Le C et le résumé actuel sont archivés dans `validation/vector-payload-options.c`
et `validation/vector-payload-options-contract.json` : le résultat Item conserve
`.value -> v[]/.value`, ainsi que la suppression du dernier élément.

Snapshot avant lot : `/tmp/crust-before-vector-payload-options`.
Patches exacts et empreintes des deux modules et du test :
`validation/vector-payload-options-changes.json`.

## Limites et suite

Les options contenant des références nominales typées, les cycles et toutes
les corrélations de variantes/provenances ne sont pas déclarés couverts. Les
unions conservatrices peuvent encore refuser des compositions valides.
Les échanges Result de charges empruntantes, les retours de conteneurs entiers
et leur intégration async restent ouverts. Le prochain cas minimal est
`validation/open-vector-payload-exchange-contract.crust` ; les deux entrées
le refusent encore explicitement, journal associé conservé.

Les modèles existants ont été rejoués : huit combinaisons de durées de vie
imbriquées (une admise, sept refusées), quatre combinaisons de stockage
(quatre admissions et quatre refus). Leurs prédictions restent inchangées.
Pas de nouveau modèle indépendant ni de campagne de mutations ; ces modèles
ne prouvent pas les graphes d’options. Aucun résultat n’est présenté comme preuve générale de
sûreté ou comme clôture de l’objectif global.
