[English](INLINE_VECTOR_POP_CYCLE.md)

# Cycle — Pop des structures en ligne dans Vector<T>

## Règles et portée

VE1–VE3, H1, T4/T5/T6, B1–B5, U1, ST15/ST17/ST18 et AS2/AS8/AS11–AS13
restent inchangées. AGENTS.md, VALIDATION_GUIDELINES.md et l’index des brouillons
ont été relus ; la spécification complète a été lue dans le travail continu.
Le périmètre de ce lot est l’extraction optionnelle des structures en ligne,
avec les signatures synchrones/async et les champs déjà représentés.
Aucun nouvel arbitrage ni changement normatif.

## Baseline et réalisation

Le snapshot `/tmp/crust-before-inline-vector-pop` conserve les modules initiaux.
`validation/inline-vector-pop.crust` était refusé aux deux entrées ;
`validation/inline-vector-pop-baseline.log` conserve le diagnostic.

`pop()` retourne désormais `Option<T>` pour Vector<T> local, distinct de
`Option<A<T>>` pour un vector de handles. Le Some possède un porteur sur la
stack implicite. Le C généré prépare son stockage puis copie la dernière case
et réduit la longueur ; None ne construit pas de porteur. Les slots éventuels
réservés à l’avance sont gérés par le placement existant. Les objets désignés
par des champs A<T> ne changent pas d’adresse. Le nettoyage des champs est
transmis au résultat, qui reste utilisable après destruction du vector.

Les provenances et emprunts de la case sont conservés par les contrats. Les
signatures, annotations, wrappers Result et handles publics distinguent le
stockage local du stockage en pool même si leur ABI C utilise un Cell *.
L’extraction de chaque enveloppe transmet le graphe de champs et les capacités.

## Défauts rencontrés

Les journaux `validation/inline-vector-pop-*` conservent les étapes intermédiaires :

- Le premier ciblé échouait sur deux écritures à travers un binding de motif
  immuable et sur le pont synchrone appelé depuis async. Les fixtures utilisent
  désormais un receveur `let mut` explicite ; le pont conserve le stockage local
  et les métadonnées de champs.
- Le deuxième ciblé isolait encore une provenance symbolique dans ce pont.
  Le troisième passe : 14 méthodes, 7,724 s.
- Le retour d’une tâche restait interprété comme Option<A<T>>. Après correction
  des wrappers, l’ouverture du Result perdait les champs empruntés/propriétaires.
  La reconstruction reprend maintenant leur descripteur complet.
- Les contrats publics puis leur normalisation perdaient la projection des
  emprunts du résultat. Les corrections préservent cette projection séparément
  des captures libérées au join. Les variantes avec mutation prématurée restent
  refusées. Les quatrième à septième passages documentent ces écarts et une
  accolade erronée dans la fixture await, corrigée sans modifier l’attendu.

## Ciblé exécuté

`validation/inline-vector-pop-targeted-final.log` : **20 méthodes, 9,770 s,
code 0**, O0/UBSan. **27 exécutions C réussies**, **16 variantes invalides**
contrôlées par verify_program et compile_source.

Some/None, ordre LIFO, drop direct, structures vides, boucle et réemploi du
pool, champs propriétaires nettoyés une fois, références partagées et mutables,
réservation de la case restante, relais synchrones, appels depuis async,
retours par await/join, attente async d’une exécution lancée, handle public et
relais de Result sont exercés. Les refus couvrent T/A<T>, l’usage après drop,
l’ignorance d’un résultat propriétaire et la mutation avant dernier usage.
Reset reste retiré du profil courant ; ce lot utilise drop et les scopes.

## Régression et intégrité

Premier passage O2/UBSan : **361 méthodes, 246,143 s, code 1**,
349 succès, trois échecs et neuf erreurs. Les 69 empreintes compilateur/tests
restent identiques pendant le passage (`-integrity.log`).

Les neuf erreurs Select venaient de deux déstructurations de signature modifiées
trop largement dans ce lot. Elles sont restaurées ; le stockage ajouté ne concerne
que la signature de l’attente qui en a besoin. Les trois échecs d’options publiques
vides venaient de l’exigence nouvelle T/A<T> appliquée à un ensemble de sources
vide. La signature de retour vérifiée conserve pourtant ce type. Une projection
commune du stockage du résultat reprend cette distinction, sans inventer de source
ni de charge vivante. Elle est utilisée à la normalisation du handle et au contrôle
des arguments. Le premier rejeu isolé conservait trois échecs au second point de
contrôle ; le second réussit : **quatre méthodes, 3,689 s**, code 0.

Rejeu O2/UBSan : **173 méthodes, 155,584 s, code 0**, dans
`validation/inline-vector-pop-replay.log`. Il comprend les modules des douze
échecs, les 20 tests ciblés et les tests Select de source, contrats, résultats,
stockage et placement. Les 46 empreintes du rejeu restent inchangées.
Les résultats des 361 méthodes sélectionnées sont disponibles après correction,
mais il ne s’agit pas d’un unique passage de 361 méthodes vert sur la version
finale. Les modifications postérieures au premier passage concernent uniquement
les deux déstructurations Select et le contrôle commun du type d’une option vide.
La sélection principale est
conservée dans `validation/inline-vector-pop-selection.json`, ses empreintes dans
`-start.json`, le diff dans `validation/inline-vector-pop.patch` et son manifeste
dans `-changes.json`. Les sélections/empreintes du rejeu utilisent le préfixe
`validation/inline-vector-pop-replay-`. Aucun test existant n’a été affaibli.

C conservé dans `validation/inline-vector-pop.c` et
`validation/inline-vector-pop-async-return.c`. Le premier montre le pop suivi du
drop du vector puis de la lecture/destruction de Some. Le second place le porteur
dans `frame->result_storage`, transfère le résultat et remet à NULL le pointeur
intermédiaire avant le nettoyage de la tâche. Les exécutions et traces complètent
cette inspection ; celle-ci ne remplace pas les vérifications dynamiques.

## Limites

Les résultats portent sur les cas exécutés et les types représentés ; ils ne
constituent pas une preuve générale de sûreté. Le suivi des positions et des
sources après certaines branches/appels reste conservateur. Replace, try_push,
tranches, push_new et les graphes généraux des structures en ligne restent
ouverts. Les tests natifs utilisent C11, pthread, Wall/Wextra/Werror et UBSan
fatal via le harnais du projet. Pas de campagne de mutation ou de recherche
adversariale étendue dans ce lot ; l’audit indépendant n’est pas présumé.


## Suite du chantier

Le prochain écart VE3 est reproduit dans `validation/inline-vector-replace.crust` :
replace d’une case Point doit rendre l’ancien Point (ou l’entrant en cas d’index
invalide), mais les deux entrées refusent encore ce programme. Le journal
`validation/inline-vector-replace-baseline.log` conserve le diagnostic.
Le présent cycle clôt son lot pop testé, pas l’objectif global.
