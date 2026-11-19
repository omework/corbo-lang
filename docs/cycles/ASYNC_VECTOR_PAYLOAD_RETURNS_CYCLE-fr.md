[English](ASYNC_VECTOR_PAYLOAD_RETURNS_CYCLE.md)

# Cycle — Retours async de vecteurs et dépendances des éléments

## Règles et périmètre

Suite de ASYNC_VECTOR_PAYLOAD_CONTRACTS_CYCLE.md. H1–H3, VE1–VE4,
B1–B5/B4c, D1–D3, F2–F4 et AS8–AS12 restent inchangées. Consignes et
VALIDATION_GUIDELINES relues ; tests centrés sur les cas retenus et leurs
régressions directes, sans nouvelle campagne adversariale.

Un vecteur transféré comme résultat async conserve les pools de ses éléments,
leurs descendants possédés et leurs emprunts. La fin de l’état async ne détruit
pas le résultat reçu. Les mêmes contraintes s’appliquent après await ou join.

## Défauts corrigés

Le cas `validation/open-async-vector-payload-return.crust` était refusé à la
signature. L’admission seule ne suffisait pas : le receveur perdait les sources
des éléments, puis remove le considérait vide. Le graphe de stockage du résultat
inclut maintenant le chemin virtuel `[]` et ses descendants. La réception et
l’extraction depuis Result restaurent les sources, les charges et leurs prêts.

L’analyse de contraintes reconstruit aussi les charges du vecteur reçu au lieu
de conserver seulement des champs aplatis. Le test Item possédant Inner qui
emprunte n a révélé cette perte : le paramètre Inner était ensuite refusé.
Cette correction conserve le graphe dans les vérifications par contrats.

Aucune nouvelle métadonnée d’emprunt n’est ajoutée au runtime. Les changements
concernent async_lowering.py, async_result_storage.py, crust.py et constraints.py.
Aucune règle normative n’a été modifiée.

## Scénarios ciblés exécutés

Dix méthodes : **9 exécutions C natives**, **9 programmes invalides** contrôlés
chacun par verify_program et compile_source, soit 18 contrôles de refus.

- Retour via join, résultat nommé puis consommé ; drop anticipé de la cible refusé.
- Fabrique synchrone de tâche, puis retour du vecteur.
- Await dans un parent async, suspension et extraction après réception.
- Retour d’un vecteur vide : longueur zéro.
- Champ mutable : lecture ou écriture concurrente de la cible après join refusée.
- Élément possédant Inner empruntant n ; valeur 7 et exactement une destruction Inner.
- Construction du vecteur dans la tâche à partir de pools injectés.
- Deux transferts async successifs avec await et suspension intermédiaires.
- Éléments A<Int> sans champs : leur stockage est également conservé.
- Résultat sortant du scope du pool de ses éléments : refus.

Harnais C11, pthread, Wall/Wextra/Werror, UBSan fatal. La passe ciblée O0
`validation/async-vector-payload-returns-targeted-fourth-o0.log` termine avec
**10 méthodes, 4,015 s, succès**. Les premières passes de sept méthodes ont
révélé le défaut du descendant Inner ; la troisième passe le corrige.
Les petits journaux exploratoires first/second/third-o0 ne prouvent pas le
niveau O0 : le harnais y utilisait son défaut O2. Les passes targeted ont
explicitement fixé CRUST_TEST_OPT=-O0.

## Régression

Régression terminée : **280 méthodes, 236,594 s, code 0**, O2/UBSan fatal.
Sélection dans `validation/async-vector-payload-returns-test-selection.txt`,
sortie dans `validation/async-vector-payload-returns-regression-o2.log`.
Le compilateur est resté inchangé pendant cette passe. Les modèles existants
de stockage, de durée de vie et de Select ont été rejoués ; ils ne constituent
pas un nouveau modèle indépendant du graphe de résultat.

## Artefacts et limites

- C du cas de retour : `validation/async-vector-payload-returns.c`.
- Snapshot : `/tmp/crust-before-async-vector-payload-returns`.
- Patches et empreintes : `validation/async-vector-payload-returns-changes.json`.
- Test : `tests/test_async_vector_payload_returns.py`.

Le graphe des éléments est conservatif par chemin `[]` et provenance, sans
corrélation complète indice/branche/cible. Les signatures, captures et enveloppes
async générales restent à raccorder selon leurs formes. Aucun nouveau modèle
indépendant de ce graphe, aucune nouvelle campagne de mutations, ASan ou TSan.
Le cas suivant est enregistré dans
`validation/open-async-vector-payload-handle-return.crust/.log` : une fonction
recevant runtime::Handle<A<Vector<A<Item>>>> et retournant son join est
refusée aux deux entrées (forme de résultat du contrat Handle non raccordée).
Il s’agit d’un écart d’implémentation, sans nouvel arbitrage de sémantique.

Reset reste retiré. Ces résultats ne constituent ni une preuve générale de
sûreté ni une clôture de l’objectif global.
