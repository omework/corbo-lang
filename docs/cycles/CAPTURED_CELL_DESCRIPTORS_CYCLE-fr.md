[English](CAPTURED_CELL_DESCRIPTORS_CYCLE.md)

# Descripteurs des emprunts Int capturés

## Règles et frontière corrigée

Aucune règle normative modifiée. Ce lot poursuit B4, ST8/ST11–ST13,
AS2/AS12/AS13 et RT6/RT8 : une capture par emprunt conserve sa cible, sans
copie de l'allocation ni transfert de sa destruction à la tâche. Le stockage
de cet emprunt dans un objet local doit aussi fonctionner après suspension.

`validation/open-async-captured-stored-reference.crust` crée une allocation,
la capture dans un relais async puis dans un enfant qui appelle un auxiliaire
synchrone construisant une View. La version antérieure refusait les deux
entrées de compilation faute de descripteur dans l'état. La reproduction
charge explicitement les trois modules antérieurs depuis une copie isolée :
`validation/captured-cell-descriptors-recorded-baseline.log`.
Le programme est désormais compilé et exécuté avec la valeur 7, destruction
de View puis de n : `captured-cell-descriptors-recorded-final.log` et C voisin.

Chaque tâche porte un ensemble d'indices de paramètres exigeant un Cell.
Cet ensemble augmente lorsque le corps stocke une référence capturée, ou
quand un enfant exige ce descripteur. L'abaissement est répété jusqu'à stabilité
de tous les ensembles, qui sont finis. Les contrats synchrones sont recalculés
entre les passes : une fabrique de handles doit publier la même exigence pour
son propre paramètre. Les signatures C, les appels et les membres d'état sont
émis avec la même liste stabilisée. L'ordre de déclaration des tâches ne doit
pas déterminer les programmes exécutables.

Les captures concernées ajoutent un `Cell *` au pointeur de contenu existant.
Les captures qui ne stockent pas de référence ne reçoivent pas ce membre.
L'argument conserve le descripteur d'origine à la création, puis à travers
les enfants, les réemprunts et les fabriques synchrones. La sélection entre
plusieurs provenances utilise le pointeur évalué et les cibles suivies.
Le descripteur n'est pas une allocation supplémentaire et n'est pas détruit
par le nettoyage de la capture empruntée. Les contrôles de durée de vie et
d'exclusivité restent ceux des prêts existants.

## Validation exécutée

Commandes finales ciblées :

```
CRUST_TEST_OPT=-O0 PYTHONPATH=tests python3 -m unittest test_captured_cell_descriptors test_cell_reference_bridges -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_captured_cell_descriptors test_cell_reference_bridges -v
```

Les 27 méthodes passent à O0 en 32,296 s et O2 en 32,585 s, journaux
`validation/captured-cell-descriptors-complete-o{0,2}.log`. Elles comprennent
les quatorze méthodes du lot précédent et treize nouvelles méthodes. Le C
est exécuté avec Clang C11, pthread, avertissements fatals et UBSan fatal.

Les nouveaux cas couvrent captures partagées et mutables, identité d'adresse,
cinq relais dans les deux ordres de déclaration, paramètre non premier,
choix de cibles, fabriques synchrones relayées, lancement refusé, thread natif,
tâche détruite inactive et réemploi du slot. Une récursion de quatre instances
avec capacité explicite conserve le descripteur et détruit une seule fois n.
Les résultats partagés et mutables protègent la cible jusqu'au dernier usage.

Un modèle indépendant de huit scénarios distingue le résultat scalaire du
résultat emprunté, la destruction avant/après join, et drop/reset. Deux cas
sont exécutés, six refusés par les deux entrées du compilateur. Les reset
emploient uniquement `allow_legacy_reset=True` pour vérifier la provenance
historique ; l'API publique reste retirée. Le modèle de seize scénarios du
lot précédent est également réexécuté, sans changement de ses attentes.

La régression O2 `test_sync_handle_bridges test_sync_borrow_calls
test_native_blocks test_async_capacity test_async_structure_effects` passe
72 méthodes en 67,036 s : `captured-cell-descriptors-regression.log`.
La sélection O2 `test_function_bodies test_type_features test_builtin_features
test_nested_plain_results test_async_struct_captures test_async_struct_reference_fields`
passe 102 méthodes en 70,371 s : `captured-cell-descriptors-contract-regression.log`.
Ces sélections ne constituent pas un passage de la suite globale.
La compilation Python des modules et des nouveaux tests réussit.

`python3 tests/run_captured_cell_descriptor_mutations.py` détecte cinq fautes
isolées : perte de l'exigence de capture, arrêt avant stabilisation, perte de
l'exigence dans une fabrique synchrone, descripteur nul dans l'état et mauvaise
cible du choix conditionnel. Journal : `captured-cell-descriptors-mutations.log`.
Les trois premières sont observées par contrat ou compilation, les deux
dernières à l'exécution. Cela ne prouve pas l'absence d'autres fautes ni la
correction générale du scheduler.

## Erreurs intermédiaires et distinction normative

Un premier essai de génération de la fabrique extrayait `*capture_cell_0` au
lieu du nom du paramètre C. La déclaration générée a été corrigée avant les
suites ciblées. Le premier journal ciblé conserve huit échecs de sous-tests :
six diagnostics de reset non reconnus par le motif du test, et deux essais
d'emprunt d'un scalaire local refusés plus tôt par la grammaire/sémantique
existante. Les tests de représentation inline emploient maintenant des cases
de tableaux valides ; les diagnostics de reset sont vérifiés explicitement.

Le complément mutable comportait d'abord un motif `Ok(mut v)` non pris en
charge. Après correction de cette fixture, il révélait surtout une mauvaise
attente : retourner `&mut *w.data` depuis un porteur w local viole ST12, qui
retient le porteur autant que la cible. Ce programme reste testé comme refusé.
Le voisin admis termine le réemprunt local, détruit w puis retourne le paramètre
mutable d'origine. Aucun contrôle de porteur n'a été supprimé.

Les passes intermédiaires de 25 méthodes et les compléments sont conservés
séparément des passes finales de 27 méthodes. Le test historique qui attendait
le refus de toute capture Int a été remplacé par les tests d'acceptation de ce
lot ; le refus des pointeurs inline sans descripteur reste exercé.

## Limites et prochaine frontière

Les cibles inline sans Cell, notamment les éléments de tableaux utilisés dans
ces champs, restent une limite de représentation. La généralisation des types
et agrégats reste ouverte. Les remplacements des dépendances de champs
extérieurs depuis les états async sont toujours refusés : leur contrat est
inféré, mais son application aux états, handles et appelants après attente
reste à implémenter. Ce lot ne lève pas ce contrôle.

Pas de passage global de toutes les suites, pas de nouvelle preuve ASan/TSan
ni de comparaison entre compilateurs C indépendants. Les patches sont sous
`validation/captured-cell-descriptors-*.patch`. L'objectif global reste ouvert.
