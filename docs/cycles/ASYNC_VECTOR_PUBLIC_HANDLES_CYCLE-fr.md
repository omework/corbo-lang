[English](ASYNC_VECTOR_PUBLIC_HANDLES_CYCLE.md)

# Cycle — Vecteurs retournés par les contrats publics de handles

## Règles et portée

Suite de ASYNC_VECTOR_PAYLOAD_RETURNS_CYCLE.md. AS8–AS12, H1–H3, VE1–VE4,
F2–F4, B1–B5/B4c et D1–D3 restent inchangées. Consignes et guidelines lues.
Un runtime::Handle<A<Vector<A<Item>>>> reçu par transfert doit pouvoir être
attendu par une fonction. Le Result retourné conserve les dépendances de ses
éléments, y compris après le passage par un relais de handles.

## Écarts corrigés

Le programme `validation/open-async-vector-payload-handle-return.crust` était
refusé aux deux entrées : forme publique du résultat non raccordée. La signature
publique et la reconnaissance des enveloppes Result acceptent maintenant cette
charge de vecteur. Le graphe symbolique du handle décrit les éléments via [] et
les descendants possédés. Les projections distinguent les prêts partagés et
mutables jusque dans les éléments.

Les représentations de résultat dans l’analyse de provenance et l’analyse de
contraintes reconstruisent les charges et les sources du vecteur. La réception
par contrat et le chemin de génération C conservent ces mêmes informations.
Avant cette correction, le résultat était considéré vide par remove ; puis le
chemin vérifié par contrats passait alors que compile_source perdait encore
les éléments. Les deux entrées passent désormais les tests ciblés.

Le contrôle interne des sources d’éléments d’un Result contenant un vecteur
reste actif ; le contournement historique utilisé pour d’autres charges ne lui
est pas appliqué. Aucun invariant n’a été désactivé et aucune règle normative
n’a été modifiée.

## Validation ciblée

Quatre nouvelles méthodes : **4 exécutions C natives**, **6 invalides** vérifiés
chacun par verify_program et compile_source, soit 12 contrôles de refus.

- Handle public reçu par une fonction wait qui renvoie son join.
- Relais transférant le handle avant wait.
- Élément Item possédant Inner empruntant n.
- Élément portant &mut Int : drop, lecture et écriture incompatibles après wait
  refusés avant consommation du résultat.

Les dix méthodes du lot précédent sont rejouées avec les quatre nouvelles :
**14 méthodes, 6,200 s, code 0**, O0/UBSan fatal, dans
`validation/async-vector-public-handles-targeted-second-o0.log`.
Cela représente 13 exécutions C et 15 invalides aux deux entrées au total.
Harnais C11/pthread, Wall/Wextra/Werror ; les invalides ne sont pas exécutés.

Première passe : 14 méthodes, 5,691 s, trois échecs. Deux provenaient du même
programme de test : le remplacement textuel n’insérait pas le drop anticipé
dans le relais de handle, donc le programme effectivement testé était valide.
Le générateur a été corrigé pour insérer le cas invalidant voulu, sans changer
son oracle. Le troisième révélait une perte du descendant Inner dans l’analyse
de contraintes ; elle a été corrigée.

## Régression

Terminée : **284 méthodes, 277,479 s, code 0**, O2/UBSan fatal.
Journal : `validation/async-vector-public-handles-regression-o2.log`.
Sélection : `validation/async-vector-public-handles-test-selection.txt`.
Les empreintes du manifeste ont été contrôlées pendant cette passe : compilateur
et tests inchangés. Les modèles existants de stockage, durée de vie et Select
sont rejoués, sans nouveau modèle indépendant du graphe de résultat.

## Artefacts et limites

Snapshot : `/tmp/crust-before-async-vector-public-handles`.
Patches et empreintes des cinq modules modifiés et du test :
`validation/async-vector-public-handles-changes.json`.
Les journaux first à sixth conservent les étapes de raccordement du cas minimal.

Le suivi des éléments reste conservatif par chemin [] et provenance. Ce lot
ne valide pas toutes les enveloppes, captures ni signatures async. Pas de
nouveau modèle indépendant, mutation, ASan ou TSan. Les modèles antérieurs
sont inclus dans la régression sélectionnée. Reset reste retiré. L’objectif
global et les autres écarts de la checklist restent ouverts.

Prochain raccordement reproduit : `validation/open-async-vector-result-relay.crust/.log`.
Après wait, transmettre le Result lui-même à une fonction qui le restitue
échoue aux deux entrées sur l’inventaire des pools d’éléments du contrat.
La règle de transfert est déjà retenue ; ce programme minimal reste à corriger.
Le C du cas direct est conservé dans `validation/async-vector-public-handles.c`.
