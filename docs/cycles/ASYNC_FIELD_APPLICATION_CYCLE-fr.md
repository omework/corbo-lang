[English](ASYNC_FIELD_APPLICATION_CYCLE.md)

# Application des modifications de champs après join

## Périmètre

Aucune règle normative modifiée. Ce lot raccorde une partie de ST10/ST13,
B1/B2/B4/B5 et AS12/AS13 à des programmes C exécutables. Une fonction async
à résultat scalaire ou Void peut appeler un auxiliaire synchrone qui remplace
un champ `&Int` d'une structure injectée par `&mut`. La nouvelle cible doit
provenir d'un paramètre Int emprunté injecté, avec un descripteur Cell durable.
Les méthodes et les blocs de thread natif suivent ce même raccordement.

La tâche conserve les modifications différées dans ses métadonnées statiques.
Sa création et sa destruction inactive n'appliquent aucune écriture. Le lancement
transmet ces métadonnées au handle. Après join, les dépendances du porteur
réunissent les cibles finales possibles et les anciennes cibles : le lancement
peut avoir échoué. La durée de vie des nouvelles cibles est confrontée au scope
du porteur avant publication de ces dépendances. Une adresse n'est ni déplacée
ni remplacée par une copie pour contourner cette vérification.

Dans l'état async, un champ modifié conserve les prêts de ses nouvelles cibles.
Une jonction conditionnelle réunit les alternatives ; une branche sans écriture
conserve le champ initial. Les reprises de boucle gardent leur contrôle strict
et ne bénéficient pas implicitement de cette extension. Un emprunt détaché
avant remplacement conserve le descripteur de la cible initiale, enregistré
à la création de l'état, plutôt que celui du champ courant.

## Contre-exemples et corrections

Le programme `validation/open-async-sync-field-replacement.crust`, auparavant
refusé, produit maintenant `9\n9\n`. Avec échec du premier lancement injecté,
il produit `7\n` : le champ initial est conservé.

L'audit des reconstructions de handles a trouvé une perte de métadonnées dans
le match d'enum. Le programme conservé dans
`validation/counterexample-async-enum-match-field-effect.crust` était accepté
par verify et compile avec un drop de la nouvelle cible avant lecture du champ.
Il n'a pas été exécuté dans cet état invalide. La réunion des valeurs du match
conserve maintenant les modifications différées ; le programme est refusé.
Les voisins admis s'exécutent pour les deux variantes, en match emprunté et
consommant. Le compilateur peut exclure une variante connue : sa cible non
sélectionnée peut être détruite. Le premier test exigeait à tort de la retenir ;
son attente a été corrigée d'après les chemins effectivement possibles.

Cette sélection statique exposait aussi un alias C inutilisé dans un bras
supprimé. L'émission marque désormais l'alias C comme utilisé sans modifier
le contrôle Crust d'usage explicite. La forme consommante du test a été corrigée
de `match <-choice` vers la syntaxe existante `match (->choice)`.
Les échecs intermédiaires sont conservés dans `async-field-application-enum.log`.

## Vérifications exécutées

Les tests sont dans `tests/test_async_field_application.py`. Ils exercent :

- remplacement suivi de yield et join ; échec de lancement et tâche inactive ;
- drop et mutation des anciennes/nouvelles cibles avant ou après destruction
  du porteur, avec réemploi du slot ;
- cible d'un scope enfant refusée après attente et capture inactive admise ;
- nouveau réemprunt et emprunt détaché avant remplacement, passés à un helper
  qui stocke lui-même la référence ;
- deux remplacements successifs, branches conditionnelles avec ou sans écriture,
  choix de handles de types concrets identiques ou différents ;
- match builtin, match enum emprunté/consommant, résultat de boucle après continue ;
- méthodes, bloc natif et reset historique derrière l'option explicite ;
- refus explicites des frontières encore non raccordées.

Le modèle indépendant de rétention comporte huit scénarios : tâche inactive
ou attendue, porteur détruit ou vivant, destruction de l'ancienne ou nouvelle
cible. Cinq programmes sont admis et exécutés, trois refusés par les deux entrées.
Ces nombres concernent le modèle, pas le total de programmes de toute la suite.

Commandes finales :

```
CRUST_TEST_OPT=-O0 PYTHONPATH=tests python3 -m unittest test_async_field_application -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_async_field_application test_async_structure_effects -v
```

Les 16 méthodes passent à O0 en 22,877 s ; les 41 méthodes réunies passent à O2
en 24,375 s. Journaux : `validation/async-field-application-final-o{0,2}.log`.
Les tests natifs compilent avec Clang C11, pthreads, avertissements bloquants
et UBSan fatal. Les méthodes d'analyse de contrats ne sont pas comptées comme
autant de programmes C exécutés. Les modèles antérieurs 125/16 cas sont repris
par le module de contrats. La compilation Python des fichiers modifiés réussit.

La première sélection de régression passait 107 méthodes en 63,316 s, avant
la correction du match enum et l'extension des branches conditionnelles :
`validation/async-field-application-regression.log`. Une sélection finale
complémentaire passe 112 méthodes en 99,794 s après toutes les corrections :
`validation/async-field-application-final-regression.log`. Elle reprend les
descripteurs capturés, les helpers stockant des références, les captures de
structures, les relais de handles, les blocs natifs, les références de boucles
et de liaisons locales, et les sorties de boucles dans les expressions async.
Ces sélections se recouvrent ; elles ne constituent pas une passe globale de
toute la suite. Les patches des deux modules depuis le début du lot sont
conservés dans `validation/async-field-application-*.py.patch`.

## Mutations et limites

`tests/run_async_field_application_mutations.py` mute des copies temporaires,
sans changer le checkout ni les oracles. La campagne couvre la publication au
join, le lancement, les résultats de boucle/match, les prêts stockés, le
descripteur initial et la branche sans écriture. Le journal final est
`validation/async-field-application-complete-mutations.log`.
Huit mutations sont détectées ; une survit. Les huit détections comprennent
des refus statiques manquants et des sorties natives erronées, notamment 18
au lieu de 16 quand l'ancien emprunt utilise le descripteur du champ courant.

La mutation supprimant le contrôle de destination au join survit au scénario
choisi : verify et compile refusent encore la lecture ultérieure avec
« champ emprunté : cible non disponible ». Le diagnostic isolé est conservé
dans `async-field-application-lifetime-mutation-diagnostic.log`. Cela démontre
une compensation dans ce scénario, pas l'équivalence générale de la mutation.
Le runner signale un échec lorsque cette mutation survit ; ce résultat n'est
pas masqué. La première mutation du rassemblement de résultats de boucle
survivait au test de if choisi ; le test de sortie de boucle exerce maintenant
ce chemin distinct.

Restent ouverts : modifications transmises par tâches enfants, fabriques et
auxiliaires synchrones manipulant ces handles, stores directs dans le corps
async, champs `&mut`, sources projetées ou inline, résultats agrégés/empruntés
des tâches modificatrices, reprises de boucle modifiant les champs et
corrélation complète des effets avec les branches Ok/Err. Ces refus sont des
limites d'implémentation, pas de nouvelles règles de langage.

Pas de nouvelle preuve ASan/TSan, de comparaison entre compilateurs C
indépendants, de mesure de performance ni de preuve formelle. Le lot ne couvre
pas toutes les combinaisons du langage et ne termine pas l'objectif global.
