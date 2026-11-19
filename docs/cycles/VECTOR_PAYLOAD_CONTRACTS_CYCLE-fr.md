[English](VECTOR_PAYLOAD_CONTRACTS_CYCLE.md)

# Cycle — Contrats des éléments de vecteurs empruntants

## Règles et portée

Suite de VECTOR_PAYLOAD_GRAPHS_CYCLE.md, selon H1–H3, VE1–VE4, B1–B5,
B4c, D1–D3, F2–F4 et les règles de destruction. Aucun changement normatif.
Les instructions AGENTS.md et VALIDATION_GUIDELINES.md, l'index des sept
brouillons et les règles concernées ont été lus dans cette session.

Ce lot raccorde les paramètres synchrones Vector<A<Item>> dont Item contient
des références ou des descendants propriétaires. Une fonction peut extraire
un objet et le retourner, insérer un objet reçu ou construit avec des pools
injectés, ou remplacer un élément. L'appelant conserve les dépendances à partir
du contrat. Les enveloppes Option/Result complexes, les retours de vecteurs
complexes entiers, certaines projections et l'intégration async restent ouverts.

## Implémentation

- Un paramètre vecteur dispose d'un graphe symbolique de ses éléments. Le chemin
  interne `[]/…` désigne les champs des contenus possibles ; il n'introduit
  aucune nouvelle notation source ni promotion de durée de vie.
- Les analyses de résultats et de contraintes reconstruisent les champs actifs
  à partir des éléments encore possibles. Les champs propriétaires et les cibles
  empruntées restent distincts de l'allocation du vecteur.
- Les contrats de mutation ajoutent `vector_write_payloads` à l'inventaire
  existant des insertions/remplacements/suppressions : type du contenu,
  provenance, références et descendants possédés. Les contrats sans graphe
  supplémentaire ne reçoivent pas cette information inutilement.
- L'application d'un contrat résout ces graphes avec les allocations réelles et
  vérifie leur destination. Les pools des descendants et les cibles empruntées
  doivent survivre au vecteur receveur.
- Les descendants d'un résultat extrait sont résolus **avant** de publier la
  suppression dans le vecteur. Sinon, le chemin qui permet de retrouver le
  descendant disparaît et la projection ultérieure est refusée à tort.
- Les règles existantes de retour d'agrégat propriétaire reconnaissent désormais
  une extraction d'un vecteur mutable/transféré comme provenance propriétaire.
  Cela n'autorise pas le déplacement d'un champ à travers une référence partagée.

Le runtime et la représentation C restent inchangés : les objets gardent leur
adresse et leurs pools. L'enrichissement concerne les analyses statiques et
leurs résumés. Le code C natif est toujours exécuté dans les tests d'admission.

## Scénarios ciblés

Dix méthodes, **15 exécutions C** passant d'abord par verify_program et
compile_source, et **22 programmes invalides** refusés aux deux entrées.
Deux vérifications supplémentaires isolent l'appelant : une admission et un
refus, avec les seuls contrats et descriptions de types, sans corps de fonction
ni tables de résultats d'inférence. Elles ne sont pas des exécutions C.

- Extraction et retour direct, puis relais supplémentaire ; la cible reste
  protégée chez l'appelant et le vecteur vide peut mourir avant l'objet extrait.
- Insertion d'une allocation fraîche depuis un pool injecté, directement et
  via un relais ; drop de la cible refusé avant extraction et avant lecture.
- Insertion d'un handle transféré : flèche obligatoire, responsabilités et
  dépendances conservées.
- Référence mutable stockée : lecture et mutation de la cible refusées tant
  que le vecteur doit encore servir.
- Insertion depuis un scope enfant refusée lorsque sa cible ne survit pas au
  vecteur parent, même si le pool d'Item survit.
- Item possédant Inner, qui emprunte Int : insertion par transfert, retour via
  deux fonctions, lecture du descendant, nettoyage unique et réemploi du pool.
- Construction du même graphe dans une fonction avec deux pools injectés ; les
  sources d'Item, d'Inner et la cible Int sont conservées séparément.
- Insertion conditionnelle empruntant l'une de deux cibles : les deux variantes
  sont exécutées ; le contrat retient les deux cibles possibles.
- Remplacement dans une fonction avec index valide/invalide, résultat consommé
  immédiatement ; l'élément conservé garde son propre emprunt.
- Pop consommé dans la fonction puis retour de son objet : prêt conservé après
  sortie du bras.

## Défauts rencontrés et limites de précision

Le premier essai a buté sur l'ancien refus des agrégats propriétaires retournés
qui ne provenaient pas d'un paramètre transféré. Les extractions d'éléments de
vecteurs sont maintenant reconnues comme provenance de transfert, avec le
graphe de champs attendu.

Le second essai a révélé l'ordre incorrect décrit plus haut : les métadonnées
d'Inner étaient recherchées après la suppression de leur entrée dans le vecteur.
Le résultat est maintenant résolu avant la publication de cette mutation.
Les contrôles internes de provenance et de disposition des champs restent actifs.

La régression a détecté deux refus incorrects de retours replace : les éléments
symboliques portent maintenant leurs variantes, mais le contrat de Result
n’en résolvait aucune. La résolution utilise désormais le type du contenu
pour décrire ces variantes ; le contrôle de variantes reste actif et les
attentes des tests existants restent inchangées.

Les chemins `[]/…` joignent les contenus possibles ; le contrat ne prétend pas
conserver toutes les corrélations entre un indice, une variante et ses références.
Une union conservative peut encore refuser certains programmes valides. Les
cycles propriétaires, tous les enums et toutes les projections de collections
ne sont pas couverts par les scénarios de ce lot.

## Preuves d'exécution

- Premier cas enregistré : code 0, sortie 7, traces Item/v/n dans
  `validation/vector-payload-contracts-first-o0.log`.
- Probes d'insertion et relais : trois admissions C et deux programmes invalides
  aux deux entrées, `validation/vector-payload-contracts-probes-o0.log`.
  Ces probes ne sont pas ajoutés aux comptes de la suite ciblée.
- Premier ciblé O0 : sept méthodes, 4,889 s, code 1, un échec.
- Deuxième ciblé O0 : sept méthodes, 4,889 s, code 1, un échec de descendant.
- Troisième ciblé O0 : sept méthodes, 5,649 s, code 0.
- Ciblé final O0 : dix méthodes, 6,780 s, code 0,
  `validation/vector-payload-contracts-targeted-fourth-o0.log`.
- Contrôle après correction de la régression : 19 méthodes O0, 19,768 s, code 0,
  `validation/vector-payload-contracts-corrected-o0.log`.
- Première régression O2 : 145 méthodes, 143,117 s, code 1, deux refus incorrects
  sur les retours replace ; journal `validation/vector-payload-contracts-regression-o2.log`.
- Régression finale O2 : **145 méthodes, 144,001 s, code 0**, sélection dans
  `validation/vector-payload-contracts-test-selection.txt` et journal
  `validation/vector-payload-contracts-regression-final-o2.log`.

C11, pthread, Wall/Wextra/Werror, UBSan fatal. Les journaux en échec sont conservés.
Les preuves source/C/contrats d'une insertion puis extraction sont dans
`validation/vector-payload-contracts-insert.crust`, `.c` et `.json`.

## Suite et critères non atteints

`validation/open-vector-payload-option-contract.crust` décrit le prochain cas
valide : retourner directement Option<A<Item>> depuis une fonction qui reçoit
le vecteur. Il reste explicitement refusé aux deux entrées ; le journal associé
conserve le diagnostic. Cette limitation est une étape d'implémentation, pas une
nouvelle règle normative. Les signatures Result et les retours de vecteurs
complexes entiers restent également à raccorder, puis les captures/résultats async.

Les modèles existants rejoués restent inchangés : huit combinaisons de durées
de vie imbriquées (une admise, sept refusées) et quatre combinaisons de stockage
(quatre admissions et quatre refus). Ils ne modélisent pas les nouveaux graphes
de vecteurs.

Reset reste retiré du profil normal. Aucun nouveau modèle indépendant ni
campagne de mutations n'est ajouté ici ; le laboratoire adversarial demandé
par l'utilisateur reste distinct. Les résultats sont des preuves pour les cas
exécutés, pas une preuve générale de sûreté ni une clôture de l'objectif global.

## Traçabilité

Snapshot avant lot : `/tmp/crust-before-vector-payload-contracts`.
Patches exacts et empreintes : `validation/vector-payload-contracts-changes.json`.
