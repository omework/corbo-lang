[English](STORAGE_REQUIREMENTS_CYCLE.md)

# Exigences de stockage déduites des types et conservées dans les contrats

## Problème et règles

Ce lot applique les types distincts T et A<T>, les copies ST17/ST18, T1/T6,
les contrats de fonctions, L7 et AS9/AS12, ainsi que les brouillons 03/05/07.
Il ne change aucune règle normative.

`validation/open-async-local-only-copy-annotation.crust` est maintenant accepté
par les deux étapes et affiche 7. Le corps de `leaf(p:&Point)` contient
`let q:Point=duplicate(p)`. Cette annotation impose que la copie soit locale,
et donc que la provenance du paramètre de cette opération soit locale. Un
appel avec une valeur de pool ne satisfait pas cette exigence et reste refusé.
L'annotation n'est pas supprimée pour rendre le programme compilable.

Inversement, `let q:A<Point>=duplicate(p)` impose une provenance de pool. Deux
exigences contradictoires sur la même source sont refusées. Les contraintes
proviennent des opérations et des types écrits ; elles ne convertissent ni
ne déplacent une allocation vers une autre source.

## Implémentation

`storage_requirements.py` réutilise le flot d'assets du module de contraintes,
avec des points d'observation pour les annotations, les retours A<T> explicites
et les appels. Une obligation sur un paramètre racine devient une entrée
`(index, local|pool)` du contrat. Les sources déjà connues sont contrôlées
immédiatement. Les sources possibles d'un résultat sont toutes examinées.

Les obligations sont propagées jusqu'à stabilisation entre fonctions
synchrones, fabriques de tâches et fonctions async. Chaque appel consulte le
contrat de son callee. Le corps du callee n'est pas réanalysé au site d'appel.
Les contrats synchrones publient ces obligations dans
`FunctionContract.storage_requirements`; les déclarations async les conservent
dans le champ correspondant. Les corps symboliques sont vérifiés avec les
exigences déduites de leurs paramètres, au lieu de supposer une source de pool.

La représentation async ordinaire utilise maintenant le minimum de paramètres
locaux exigé par son contrat. Les autres instanciations compatibles peuvent
encore sélectionner les variantes statiques du lot précédent. Tous les appels,
y compris ceux sans paramètre local, contrôlent les exigences avant sélection.
Les variantes conservent un seul pool nominal d'états.

L'analyse des exigences est activée pour les corps contenant une annotation
pertinente ou un appel qui porte déjà une obligation, puis se propage au point
fixe. Cela évite d'imposer une deuxième validation incomplète à des expressions
sans rapport avec ces exigences. Le vérificateur ordinaire reste systématique.
Le flot complémentaire traverse await et Select, en conservant les sources
possibles des résultats. Il ne remplace pas l'analyse de durée de vie, de
réservation ou de nettoyage de ces opérations.

Une correction de placement synchrone était aussi nécessaire : un retour
calculé explicitement marqué (`return <-duplicate(a)`) dans une branche peut
recevoir directement une réservation de stockage local. Le plan ne se limite
plus à `return <-nom`. Les deux branches de copie sont exécutées dans les tests.

## Preuves exécutées

`tests/test_storage_requirements.py` contient dix méthodes. Le passage final
O0 réussit en 4,894 s, avec **12 exécutions natives** et **9 programmes invalides**
refusés aux deux étapes (**18 contrôles**). La baseline finale O2 des mutations
réussit en 5,286 s. Les exécutions C utilisent Clang C11, pthread,
Wall/Wextra/Werror, Wno-unused-function et UBSan fatal.

- Le programme enregistré, avec inspection de son contrat async.
- Appel local admis et appel de pool refusé pour une annotation T ; inverse
  pour une annotation A<T>.
- Obligation issue d'un helper synchrone puis relayée par deux tâches.
- Deux niveaux de fabriques synchrones, avec vérification des contrats et
  refus du même appel sur une source incompatible.
- Deux sources possibles de copie : les deux paramètres doivent être locaux ;
  les branches true/false sont exercées avec un discriminant Int.
- Exigences contradictoires refusées.
- Capture suivie d'attente puis drop admise ; drop avant attente refusé.
- Modèle indépendant des quatre combinaisons local/pool sur deux paramètres :
  quatre exécutions admises et quatre voisins dont la première source est
  inversée et doit être refusée. Les obligations attendues sont écrites depuis
  ce modèle, pas calculées par le compilateur.
- Copie annotée combinée avec Select, yield, await et conversion de u8 vers Int.

Les journaux finaux sont `validation/storage-requirements-counted-o0.log` et
`validation/storage-requirements-mutations-final-o2.log`.

La régression de **108 méthodes** réussit en 54,934 s dans
`regression-corrected-o2.log`. La sélection async élargie de **97 méthodes**
réussit en 78,094 s dans `async-regression-final-o2.log`. Ces deux passages
précèdent le dernier complément du flot Select de l'analyse des exigences.
Une sélection de **46 méthodes** passe ensuite en 44,558 s sur le code final :
tests ciblés, Select source et résultats Select, dans
`selection-final-o2.log`. Tous ces journaux ont le préfixe
`validation/storage-requirements-`. Les premiers 22 tests ciblés/interactions
ont également passé dans `targeted-third-o0.log`.

`py_compile` réussit. Les diffs des cinq modules sont archivés dans
`validation/storage-requirements-*.py.patch`, par rapport au snapshot
`/tmp/crust-before-storage-requirements/`; le nouveau module est un ajout.
Tous les processus cités sont terminés et leurs résultats récupérés.

## Mutations et chronologie

Les six fautes de `tests/run_storage_requirement_mutations.py` sont détectées :
omission d'une annotation, perte de propagation par appel, arrêt après un seul
passage, oubli de publier l'obligation dans le contrat synchrone, conservation
de la seule première source possible, et oubli du stockage local dans les
entrées symboliques. Plusieurs détections sont des refus de programmes valides ;
d'autres constatent un contrat incomplet. Ce ne sont pas des corruptions mémoire
exécutées et cette campagne finie n'est pas une mesure globale de couverture.

Les échecs initiaux restent conservés :

- `regression-initial-o0.log` : huit assertions de diagnostics échouaient,
  bien que les programmes invalides soient refusés ; les diagnostics précisent
  maintenant la distinction T local / allocation A<T>, sans affaiblir les tests.
- `suite-initial-o0.log` : propagation manquante à travers await, et fixture
  utilisant Bool dans une signature synchrone qui attend une autre notation.
  La fixture emploie désormais un discriminant Int avec les deux branches.
- `suite-second-o0.log` : le vérificateur acceptait les deux provenances,
  mais le backend refusait le retour calculé d'une copie locale ; placement corrigé.
- `regression-o2.log` : trois erreurs et un échec, dus aux valeurs inconnues
  traversant await dans la passe supplémentaire ; les résultats propriétaires
  simples et imbriqués sont maintenant conservés.
- `async-regression-o2.log` : trois échecs de typage d'expressions sans obligation
  de stockage, révélant l'application trop large de la passe supplémentaire.
  Le déclenchement est limité aux dépendances pertinentes, et le flot Select
  est couvert lorsqu'une annotation de stockage est effectivement présente.

Les journaux intermédiaires et les deux campagnes de mutations restent disponibles.

## Limites et prochain travail

Le journal `validation/storage-requirements-remaining.log` confirme la fermeture
du cas de copie annotée. Deux programmes valides restent refusés :

- `open-async-fresh-local-result-destination.crust` : une tâche crée une nouvelle
  copie locale, puis la retourne. Il faut injecter une destination extérieure
  à son état, plutôt que fermer le stockage contenant le résultat.
- `open-async-return-replaced-owned-field.crust` : restitution d'un graphe après
  remplacement d'un champ propriétaire ; ses sources doivent être actualisées.

Les obligations de ce lot portent sur les paramètres racines des structures
prises en charge. Une exigence portant sur une projection de stockage non
représentée est refusée explicitement, sans déduire une promotion implicite.
Le flot réunit conservativement les sources possibles ; les corrélations plus
précises et les signatures générales restent ouvertes.

Aucun nouveau résultat ASan/TSan ni preuve générale de sûreté n'est revendiqué.
Les tests et modèles sont finis. L'objectif complet des sept brouillons reste
ouvert.
