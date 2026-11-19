[English](ASYNC_LOCAL_PARENT_CYCLE.md)

# Placement des structures locales dans le scope parent async

## Règles et périmètre

Ce lot applique les brouillons 03 et 05, les transferts explicites T1/T3/T5/T6,
la stabilité V5, le nettoyage L1/L2/L6/L7, les règles de copie ST17/ST18 et
AS8/AS9/AS12. Il ne modifie aucune règle normative.

Le programme `validation/open-async-local-helper-parent-transfer.crust`,
refusé au cycle précédent, est maintenant exécutable. Une structure locale
produite par un helper synchrone peut sortir d'un bloc async et rester vivante
dans son parent. Les blocs imbriqués, if, match builtin, boucles à résultat,
continue, break et retours anticipés sont exercés. Les copies et les relais de
paramètres sont suivis, y compris la copie rendue par une méthode.

Le remplacement d'un receveur parent est également raccordé : résultat d'appel
direct ou de bloc, construction nommée dans l'enfant puis `r = <-q`, branche
conditionnelle, et mises à jour depuis les itérations. Si une construction peut
rejoindre deux receveurs de profondeurs différentes, la destination qui englobe
les deux est conservée. Les obligations d'emprunt et de transfert explicite
restent vérifiées séparément du placement.

## Implémentation et invariants

`async_local_placement.py` suit les producteurs des résultats locaux dans le
corps de l'appelant. Les appels sont décrits par leurs contrats, sans reparcourir
le corps des helpers. Un résultat copié a une nouvelle construction ; un relais
de paramètre conserve la construction de son argument. Les écritures dans les
receveurs déjà présents sont aussi reliées à leurs producteurs.

Le générateur ouvre la plage de la data stack du parent avant l'évaluation du
bloc concerné et transmet cette destination à l'appel producteur. Le bridge
réserve sa cellule à l'entrée du helper et le helper construit directement dans
cette cellule. Aucune allocation vivante n'est déplacée après construction.
Les temporaires non transférés de l'enfant utilisent sa propre plage. Une
branche qui retourne sans construire le résultat laisse une plage parent vide,
qui est fermée par son nettoyage normal ; elle ne crée pas un objet fictif.

Un plan intérieur ne remplace pas une destination extérieure déjà établie.
Pour plusieurs receveurs, la comparaison des profondeurs évite de choisir une
source plus courte. Le plan ne promeut pas les allocations possédées dans les
champs : leurs pools doivent toujours survivre au résultat. Les constructions
inconnues du plan restent soumises au vérificateur ordinaire.

Deux corrections supplémentaires étaient nécessaires :

- Une copie locale depuis un argument possédé conservait à tort la stack de
  l'original dans les sources du résultat. La racine neuve retient maintenant
  sa destination ; les champs sont parcourus séparément et gardent leurs pools.
- Le `<-` final d'un bloc avait été retiré trop tôt des instructions analysées.
  Une réaffectation conditionnelle était alors refusée pour absence d'usage,
  malgré ce transfert final. Le marqueur reste visible à l'analyse de durée
  d'utilisation, sans être exécuté deux fois par le backend.

La forme `r = <-{ ... <-p };` est aussi normalisée vers le chemin de transfert
de bloc, tout en conservant l'évaluation de la nouvelle valeur avant la
destruction de l'ancienne.

## Preuves exécutées

Les tests sont dans `tests/test_async_local_parent.py`. Les exécutions C
utilisent Clang C11, pthread, Wall/Wextra/Werror, Wno-unused-function et UBSan
bloquant. Les niveaux O0/O2 sont explicitement sélectionnés.

- **14 méthodes ciblées** passent à O0 en 17,182 s : **29 exécutions natives**,
  **cinq programmes invalides** refusés aux deux stages (**10 contrôles**).
  Journal : `validation/async-local-parent-complete-counted-o0.log`.
- La baseline finale O2 des mêmes quatorze méthodes passe en 17,445 s dans
  `validation/async-local-parent-mutations-complete-o2.log`.
- Une régression élargie de **148 méthodes** passe en 172,746 s avant les
  derniers compléments de méthodes et de receveurs nommés :
  `validation/async-local-parent-regression-o2.log`. Elle couvre les résultats
  locaux/propriétaires, les captures, les appels sync, les sorties de boucle,
  les expressions divergentes, Select et les contraintes de sources.
- La sélection finale de **51 méthodes** passe à O2 en 49,433 s sur le code
  final : résultats locaux, placement parent, bridges de structures et appels
  propriétaires. Journal : `validation/async-local-parent-regression-named-o2.log`.
  Le dernier test à deux receveurs est ajouté après le chargement de cette
  sélection ; il passe séparément à O0 et dans la baseline finale O2.
- `py_compile` réussit pour les modules et tests concernés. Les diffs sont
  archivés dans `validation/async-local-parent-*.py.patch`, par rapport à
  `/tmp/crust-before-async-local-parent/`. Le nouveau module est archivé comme
  ajout, sans état antérieur fictif.

Les sondes C ne suivent pas seulement les valeurs affichées. Elles observent
les cellules créées et les sources fermées dans le C généré :

1. Avant le transfert, temporaire et résultat occupent des stacks distinctes.
   Après la sortie enfant, sa source a zéro cellule vivante et un curseur à
   zéro ; le résultat parent conserve son adresse et sa valeur. La terminaison
   et le nettoyage suspendu détruisent chacun les deux valeurs exactement une fois.
2. Le modèle d'une boucle de trois itérations attend une fermeture enfant par
   itération et une fermeture parent finale. Les continue détruisent la valeur
   non retournée ; l'itération suivante réutilise exactement la même cellule
   parent, avec un curseur et un nombre de cellules vivantes constants. Après
   break, cette cellule reste vivante jusqu'à sa destruction chez le receveur.

Ces sondes détiennent exclusivement une tâche non lancée. Elles n'introduisent
aucune annulation publique. Les tests source passent aussi par le scheduler.
Le chemin Err d'un match est exercé en injectant un refus de lancement de la
tâche enfant ; sa construction alternative produit la bonne valeur et se nettoie.

Les voisins invalides couvrent un pool de champ trop court, un drop pendant un
prêt encore utilisé, un transfert absent, une lecture après move et un argument
propriétaire non marqué. Le placement ne rend aucun de ces programmes valide.

## Mutations et chronologie conservée

`tests/run_async_local_parent_mutations.py` modifie des copies temporaires en
gardant les oracles source et C inchangés. La campagne finale détecte **huit
fautes** : choix d'une destination trop courte, oubli de la destination d'un
receveur nommé, absence de placement parent, écrasement du plan extérieur,
perte des pools des champs, omission de fermeture de stack, rétention de la
stack de l'original copié et disparition de l'usage représenté par le `<-` final.
Journal : `validation/async-local-parent-mutations-complete-o2.log`.

Plusieurs mutations sont détectées par refus d'un programme valide ; celle
des champs fait accepter un programme invalide, sans exécuter ce programme.
L'omission de fermeture échoue sur les observations C. Ces formes de détection
ne sont pas présentées comme équivalentes ni extrapolées à tous les défauts.

La première campagne de six mutations et les cinq mutations du lot précédent
ont également été exécutées avec succès avant les derniers compléments :
`validation/async-local-parent-mutations-o2.log` et
`validation/async-local-parent-previous-mutations-o2.log`. Les campagnes
intermédiaires `mutations-final-o2` et `mutations-named-o2` sont conservées.
Après ajout du suivi des affectations nommées, la faute correspondante cible
ce plan préalable, plutôt que le seul traitement direct d'une réaffectation.

Les échecs initiaux restent disponibles :

- `suite-initial-o0` : copie retenant la source de l'original et enveloppe
  explicite de transfert de bloc non raccordée.
- `probes-o0` : collision de noms C dans la sonde (`Cell *result` et `int result`),
  corrigée dans le harnais sans modifier l'oracle d'identité.
- `expanded-o0` : même défaut du harnais et usage final perdu dans une branche.
- `named-o0` : une fixture conditionnelle omettait `q ->;` à l'entrée de ses
  bras ; les marqueurs ont été ajoutés conformément aux règles existantes.

Les journaux de correction et les sélections intermédiaires de 50 méthodes
restent conservés avec le préfixe `validation/async-local-parent-`.

## Écarts encore ouverts

Les diagnostics actuels figurent dans
`validation/async-local-parent-remaining-final.log` :

- `open-async-local-named-parent-replacement.crust` est désormais accepté par
  les deux stages et exécuté dans la suite, alors que le journal intermédiaire
  `remaining.log` conservait son refus avant le complément d'affectations.
- `open-async-local-loop-updated-parent-result.crust` reste refusé : une variable
  locale est réaffectée par une boucle statement, puis transférée hors du bloc
  englobant. Il faut calculer les provenances de résultat jusqu'à stabilisation
  à travers cette boucle. Le refus actuel n'est pas une règle du langage.
- `open-async-local-helper-child-capture.crust` reste refusé : la provenance
  local/pool ne traverse pas encore les signatures d'états enfants. Le retour
  d'une valeur locale hors de la tâche exige aussi un stockage de destination
  extérieur à son état.

Les graphes généraux avec emprunts, la construction directe dans les états et
la restitution après remplacement d'un champ propriétaire restent les écarts
des cycles antérieurs. Les modèles de ce lot sont finis ; ils ne constituent
pas une preuve générale de sûreté. Aucun nouveau résultat ASan/TSan n'est
revendiqué. Tous les processus cités sont terminés ; l'objectif global reste
ouvert.
