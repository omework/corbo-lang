[English](READY_QUEUE_CYCLE.md)

# RT2–RT4 — File prête, tickets de réveil et workers réutilisés

## Règles et portée

Ce lot applique le brouillon 04 et RT2–RT4 : file de tâches prêtes, un seul
poll actif, regroupement des réveils et possibilité de réutiliser un thread.
RT8 reste distinct : `runtime::thread` crée toujours un thread natif.
Aucune règle normative n’est changée. Les deux workers du scheduler par défaut
sont un choix d’implémentation, pas une taille imposée par le langage.

## Implémentation

La file est FIFO et chaînée dans des entrées réservées, sans allocation heap
par soumission. Le compilateur génère une entrée persistante par emplacement
de pool d’état, séparément de la mémoire réutilisable de la frame. L’initialisation
du super pool prépare ces entrées et sa fermeture les détruit après l’arrêt
des workers. Les fabriques raccordent chaque frame à son entrée.

Une entrée reste marquée planifiée pendant son séjour dans la file, le délai
entre retrait et poll, le poll et sa finalisation. Les réveils pendant cet
intervalle rendent la tâche prête sans dupliquer l’entrée. Après le poll,
Yield ou une notification conservée remet l’entrée en fin de file ; Pending
sans notification attend. Les workers dorment sur une variable de condition
lorsque la file est vide.

Le réveil externe interne au runtime passe par un ticket (entrée, génération).
La fin de la tâche retire son pointeur sous le verrou de l’entrée avant la
publication finale de `worker_done`. Un producteur peut donc envoyer un ancien
ticket après libération de la frame sans la déréférencer. Une autre utilisation
de l’entrée reçoit une nouvelle génération ; la génération maximale est retirée
au lieu de boucler. L’entrée, elle, doit rester vivante jusqu’à l’arrêt des
producteurs de tickets. Ce n’est pas une permission d’utiliser un ticket après
destruction du contexte qui porte son entrée.

La revue des verrous vérifie l’ordre entrée puis file. Le retrait libère le
verrou de file avant d’acquérir celui de l’entrée, et aucun corps utilisateur
ne s’exécute sous ces verrous. La publication de fin est le dernier accès à
la frame ; après cette publication, le worker ne touche plus que l’entrée
persistante et la file. Il s’agit d’un argument de conception accompagné
des essais ci-dessous, pas d’une preuve formelle.

Le scheduler par défaut démarre ses deux workers au premier `spawn`, les
réutilise, puis les joint à la fermeture du contexte. `join` attend la
publication de fin sur la condition de la file. `spawn_blocking` garde une
voie séparée qui ne peut pas occuper ces deux workers ; les blocs natifs
contournent toujours le scheduler. Les shims C historiques de scheduler et
les tâches de harnais sans entrée générée conservent leur voie antérieure.

Si le deuxième worker ne démarre pas, le premier est arrêté et joint avant
de rendre l’échec. Une erreur d’initialisation de la condition de file est
également renvoyée. Les captures de la tâche sont détruites avant le résultat
`LaunchFailed`, et une soumission ultérieure peut réessayer l’initialisation.

## Vérification

`test_ready_queue.py` comporte six méthodes :

- Modèle FIFO indépendant avec `deque` Python, quatre scripts de tâches et
  quarante scénarios reproductibles (graine 4112026), soit 5 440 opérations.
  Il prédit les tâches pollées et les réponses aux réveils ; les quatre tâches
  terminent avec dix polls au total par scénario. Il n’utilise pas la file C.
- Vingt réemplois du même emplacement avec tickets obsolètes, doublons de
  soumission, file encore occupée, file fermée et génération maximale.
- Huit frames allouées puis libérées par le harnais, trois workers et un
  producteur qui continue à envoyer leurs tickets après libération. Chaque
  corps vérifie l’absence de poll simultané ; chaque résultat est pris une fois.
- Six vraies frames générées par le compilateur, avec pools locaux et nettoyage,
  exécutées en trois vagues sur deux workers réutilisés.
- Programme source utilisant `runtime::spawn` : deux créations de workers pour
  trois tâches ; variantes injectant le refus du deuxième worker et l’échec
  de la condition. Résultats, nombre de joins et trois destructions sont vérifiés.
- Migration forcée d’une vraie frame : un tableau local et sa référence
  survivent au premier yield sur un worker, puis la tâche reprend sur le thread
  principal et attend un enfant utilisant cette référence. Les trois polls
  vérifient l’identité de la frame et le changement effectif de thread.

Le passage initial du test de réemploi a échoué à compiler à cause d’une
assertion ambiguë (`!close(...) == 0`). Elle a été remplacée par le contrôle
explicite du statut `EBUSY`, sans changement de règle ou de runtime.

## Injections de panne adaptées

Les anciens tests qui utilisaient une création pthread pour représenter chaque
soumission async ne visaient plus le bon événement. Le test du bloc natif enfant
rendait 999 (échec d’un worker du parent) au lieu du 99 attendu (échec du natif).
Il cible désormais la fonction de lancement native, indépendamment du scheduler.

`tests/scheduler_faults.py` injecte les refus à la frontière de soumission
logique sync ou async. Les scénarios conservent leurs attentes de résultat,
d’exclusivité et de destruction ; leur nombre de threads n’est plus un oracle
du nombre de tâches. Le scénario exigeant une seule soumission continue à
contrôler ce nombre, même après un premier poll d’attente forcé non prêt.
Les pannes de création réelle de threads restent testées séparément.

## Preuves exécutées

- `ready-queue-integration-o2.log` : 19 méthodes réussies, 14,315 s, avant
  les derniers compléments de lancement par défaut et d’initialisation.
- `ready-queue-final-o0.log` : neuf méthodes réussies, 12,627 s, avec les
  réveils du cycle précédent et les cinq nouvelles méthodes.
- `ready-queue-final-mutations-o2.log` : baseline finale de cinq méthodes,
  7,581 s, puis six fautes détectées : génération ignorée, frame conservée
  dans l’entrée terminée, doublons de file, Yield non remis en file, ordre LIFO
  et génération recyclée après débordement. Cinq échouent par assertion,
  le doublon provoque un arrêt runtime sur un scénario normalement valide.
  Le premier classifieur avait marqué cet arrêt sans message comme inconclusif ;
  le journal initial est conservé et le classifieur distingue désormais cet
  arrêt exécuté d’un échec de compilation ou d’un dépassement de délai.
- `ready-queue-native-mutations-o2.log` : les six mutations de la frontière
  native sont détectées ; l’ancre de suppression du nettoyage couvre maintenant
  les quatre voies de lancement (dont les deux nouvelles voies partagées).
- `ready-queue-failure-injection-o2.log` : trois méthodes réussies, 5,319 s,
  après ciblage des erreurs du natif enfant et des soumissions async.
- `ready-queue-injection-final-o2.log` : deux méthodes réussies, 6,467 s,
  dont le nettoyage des captures après refus d’une soumission. Le second
  scénario conditionnel restant est réexécuté dans
  `ready-queue-nested-collection-final-o2.log` : une méthode, 3,686 s, OK.
- `ready-queue-final-preconditions-o2.log` : cinq méthodes réussies, 3,996 s,
  avec vérification du succès d’initialisation des files des harnais.
- `ready-queue-migration-o2.log` et `ready-queue-migration-o0.log` : la méthode
  supplémentaire de migration générée passe aux deux niveaux d’optimisation.
- `ready-queue-native-o2.log` : 308 méthodes, 300,313 s, seize assertions
  en échec réparties dans douze méthodes. Les erreurs visent l’ancien lien
  entre soumission et création pthread. Les deux méthodes hors du module async
  sont réexécutées dans `failure-injection`; les autres sont incluses dans la
  campagne async avec les nouvelles injections. Ce journal reste présenté
  avec ses échecs. Le lancement précède aussi le complément de gestion d’erreur
  de la condition de file, couvert par les passages ciblés finaux.
- `ready-queue-async-o2.log` : 275 méthodes, 514,230 s, 273 réussites,
  une assertion et une erreur de décomposition de sortie dans les deux
  injections conditionnelles chargées avant leur correction. Les deux méthodes
  corrigées passent dans les journaux ciblés ci-dessus. Les dix méthodes async
  qui avaient échoué dans la campagne native sont couvertes par cette passe
  et ces réexécutions ; les deux méthodes hors du module async passent dans
  `ready-queue-failure-injection-o2.log`.
- Compilation Python des modules modifiés et des harnais réussie.

Les journaux sont dans `validation/`. Harnais Clang C11/pthread, avertissements
fatals, UBSan fatal, O0/O2. Les suites se recouvrent ; les comptages ne doivent
pas être additionnés en programmes distincts. Les succès sont répartis entre
les campagnes et les réexécutions ciblées. Aucun passage unique entièrement
vert de toutes les suites du dépôt n’est revendiqué.

## Limites

La file choisit FIFO comme stratégie de progrès : une tâche remise en fin ne
dépasse pas les tâches déjà prêtes. Les modèles et essais ne prouvent pas
l’équité du système d’exploitation ou tous les ordonnancements concurrents.
Pas de nouveau résultat TSan/ASan, second compilateur ou mesure de performance.

Les attentes générées de handles et d’enfants utilisent encore Yield. Leurs
inscriptions de réveil et la propagation vers l’appelante restent à raccorder
pour qu’elles rendent Pending sans se repoller. Le remplacement public du
scheduler, Select et les gardes de mutex restent ouverts. Le stockage des
entrées est borné par les pools ; aucun ticket ne peut dépasser la durée de
vie du contexte qui le porte. Les règles de tickets présentées ici restent
une interface interne, pas une nouvelle syntaxe utilisateur.
