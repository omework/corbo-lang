[English](TASK_WAKES_CYCLE.md)

# RT2 — Réveils conservés et attente d’événement

## Périmètre normatif

Ce lot applique la partie de RT2 et du brouillon 04 concernant un seul poll
actif, la conservation d’un réveil reçu pendant ce poll et le regroupement
des réveils. Aucune règle de langage n’est modifiée. Le protocole est interne
au C du runtime ; ce n’est pas encore une API de réveil accessible en Crust.

L’ancien runtime ne distinguait que `YIELD` et `RETURN`. Toute suspension
rendait donc immédiatement possible une nouvelle invocation du corps. Cela
ne représentait pas l’attente d’un événement requise pour le scheduler et
Select. Le nouveau résultat interne `TASK_STEP_PENDING` suspend le corps
jusqu’à un réveil ; `TASK_STEP_YIELD` le rend immédiatement prêt de nouveau.

## Implémentation et invariants

- Une tâche initialisée possède une permission de poll. Les réveils rendent
  cette permission présente, sans accumuler un compteur de polls futurs.
- La prise du poll consomme la permission sous un verrou atomique court.
  Le corps s’exécute hors du verrou, afin de pouvoir se réveiller lui-même.
- Un réveil pendant le corps conserve la permission. La publication de
  Pending ne l’efface pas. Une tâche terminée ou consommée ignore le réveil.
- Les lancements synchrones et détachés consomment aussi leur permission
  initiale avant le premier poll. Sinon, Pending serait repollé sans événement.
- La consommation de l’état terminé est synchronisée avec sa publication.
  Extraction et libération ont lieu hors du verrou, dans cet ordre.
- Le stockage reste stable pendant les polls. Un autre thread peut reprendre
  l’état après la fin du poll précédent ; aucun corps simultané n’est autorisé.

Le code se trouve dans `async_runtime.py`. La différence avec le snapshot
précédent est conservée dans `validation/task-wakes-runtime.patch`.

## Oracles et contre-exemples

`tests/test_task_wakes.py` contient quatre méthodes :

1. Un modèle indépendant décrit une permission d’exécution et quatre phases
   logiques, sans utiliser les verrous, pointeurs ou décisions du compilateur.
   Il énumère les 2 401 séquences de quatre opérations parmi sept opérations
   (réveil, poll Pending/Yield/Return, réveil pendant Pending, prise du résultat,
   destruction inactive), soit 9 604 transitions. Le C est comparé aux phases,
   nombres d’invocations, résultats des opérations et nombres de libérations.
2. Vingt essais gardent un poll ouvert pendant que quatre autres threads
   tentent chacun cent réveils et polls. Une reprise sur le thread principal
   conserve l’adresse et termine la tâche. Le premier thread reste vivant
   pour empêcher la réutilisation de son identifiant dans le contrôle de migration.
3. Les lancements avec join et avec attente détachée restent suspendus sans
   notification, puis produisent leur résultat et un seul nettoyage après réveil.
4. Deux cents essais font courir la publication de Pending et le réveil.
   La reprise suivante doit terminer, puis la destruction n’a lieu qu’une fois.

Le premier essai ciblé contenait une erreur d’oracle : `task_async_finish`
renvoie un statut nul en cas de réussite, pas un booléen vrai. Cette assertion
a été corrigée ; ni le statut runtime ni la règle n’ont été changés.
Le journal initial est conservé. Une importation de classe de tests avait
également inclus toute la suite async dans ce premier lancement ; l’importation
est corrigée et ce lancement est rapporté séparément des passages ciblés.

La régression générale a aussi trouvé une attente historique contraire à V4 :
`test_async_mutable_result_extends_exclusivity_until_its_last_use` exigeait un
refus pour `let view = lend(&mut n).await; view.set(...)`. V4 autorise l’écriture
de la cible via `&mut` même si la liaison ne peut être réaffectée. L’échec est
reproduit avec le snapshot runtime précédent
(`task-wakes-mutable-result-baseline.log`). Le test exige maintenant l’admission
et l’exécution donnant 4 ; ses contrôles d’exclusivité et de fuite locale restent
inchangés. `task-wakes-mutable-result-final.log` passe : une méthode, 2,460 s.

## Preuves exécutées

- `validation/task-wakes-complete-o0.log` : quatre méthodes réussies,
  4,664 s, dont le modèle et les courses.
- `validation/task-wakes-complete-mutations-o2.log` : baseline de quatre
  méthodes réussies, 4,649 s ; les six fautes injectées sont détectées par
  des assertions exécutées dans les binaires. Les fautes rendent Pending
  spontanément prêt, effacent un réveil pendant le poll, ignorent les réveils,
  omettent le contrôle de disponibilité, conservent la permission initiale du
  worker ou autorisent un poll pendant un autre poll.
- `validation/task-wakes-native-mutations-o2.log` : les six mutations
  préexistantes de la frontière native sont détectées. La mutation de routage
  du thread natif vers le scheduler échoue par assertion dans sa variante
  synchrone et dépasse aussi le délai dans sa variante détachée ; le délai
  seul n’est pas présenté comme une preuve de détection.
- `validation/task-wakes-native-o2.log` : 302 méthodes réussies en 312,219 s.
  Ce lancement inclut les trois premières méthodes de réveils ; la quatrième
  (course réveil/publication) a été ajoutée ensuite et passe dans les deux
  baselines ciblées finales ci-dessus.
- `validation/task-wakes-initial-o2.log` : 278 méthodes, 489,570 s,
  276 réussites et deux échecs d’attentes de tests. Ce processus avait chargé
  les anciennes assertions avant leur correction : statut nul de
  `task_async_finish` et liaison immutable de référence mutable. Leurs passages
  corrigés sont respectivement dans les baselines ciblées finales et dans
  `task-wakes-mutable-result-final.log`. Le runtime n’a pas changé pendant
  cette campagne. Le journal initial reste présenté avec ses deux échecs.
- Compilation Python des modules runtime et tests modifiés réussie.

Les harnais utilisent Clang C11/pthread, avertissements fatals, UBSan fatal
et O0/O2. Les comptages sont des méthodes ou des transitions selon leur libellé,
pas des nombres interchangeables de programmes source Crust.

Les suites native et async se recouvrent : leurs comptages ne sont pas à
additionner en nombre de programmes distincts. La couverture finale est
répartie entre la régression et les réexécutions ciblées ; aucun passage
unique entièrement vert de tout le dépôt n’est revendiqué.

## Limites et travail restant

Le runtime lancé continue à appeler `sched_yield` et à vérifier la disponibilité
dans une boucle. Il n’exécute plus le corps Pending sans permission, mais ce
lot ne fournit pas encore une file de tâches ni une attente système économe.
Il n’établit pas l’équité générale du scheduler ni son remplacement public.
Les attentes émises actuellement par le compilateur continuent à utiliser
Yield ; le raccordement événementiel des attentes et des réveils de parents,
Select et les mutex restent à réaliser.

Le pointeur passé au réveil doit rester vivant jusqu’au retour de cet appel.
Les tests conservent explicitement les états jusqu’au retour de tous les
threads. Une API publique de réveil devra assurer la durée de vie des inscriptions,
leur retrait et la protection contre le réemploi d’un slot ; ce lot ne fournit
pas cette gestion. Aucun réveil sur un pointeur déjà libéré n’est autorisé.

Les courses exécutées sont finies ; les essais ne prouvent ni tous les
ordonnancements ni l’absence générale de data races. Aucun nouveau résultat
ASan/TSan, second compilateur, benchmark ou preuve formelle n’est revendiqué.
RT2 reste partiellement implémentée et l’objectif global reste ouvert.
