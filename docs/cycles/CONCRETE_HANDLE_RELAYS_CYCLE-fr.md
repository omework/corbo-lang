[English](CONCRETE_HANDLE_RELAYS_CYCLE.md)

# Relais de handles concrets vers leur contrat public

## Règles et correctifs

AS12/AS13, RT5/RT7, B1–B5, ST11–ST14 et D1/D3 restent inchangées.
Un transfert de `Execution<leaf>` vers `runtime::Handle<T>` ne doit perdre
ni les cibles du résultat, ni les capacités mutables dont elles dérivent.
Le reset est testé exclusivement dans le profil historique autorisé par PR1.

Le programme `validation/open-concrete-borrowed-handle-relay.crust` échouait
avec « capture empruntée introuvable ». La conversion publique renumérotait
les captures du descripteur consommé. Le contrôle du résultat utilisait ensuite
la signature concrète d'entrée avec ces nouveaux numéros. Il conserve désormais
une copie du descripteur d'entrée, sans dupliquer la responsabilité de nettoyage.
Le programme est exécuté et affiche 9.

La conversion des résultats partagés conserve aussi la capacité exclusive
d'origine. Un groupe public optionnel vide ne crée plus une fausse cible locale.
Les essais couvrent Int, u8 inline, les champs Int inline, les champs &mut Int
réempruntés et les champs &Int détachables.

Le modèle de contraintes distingue les sources nécessaires à l'exécution de
celles nécessaires au résultat emprunté. Les paramètres concrets ont un symbole
de source du résultat ; les conversions publiques conservent aussi les autres
captures. Les sources traversent les fabriques, les auxiliaires de join et les
relais. Une projection de champ partagé n'ajoute pas de dépendance envers son
porteur. Les projections de tableaux respectent les indices constants et
réunissent toutes les cases possibles pour un indice dynamique.

Le contrôle historique interdisait également tout reset dans un appel recevant
une tâche, même après son attente et le dernier usage de son résultat. Les
contraintes ordonnées remplacent ce refus global. Elles vérifient toutes les
captures au join, y compris les allocations transférées. L'application opaque
du contrat exclut des prêts encore actifs les tâches consommées par cet appel,
mais conserve ceux des autres tâches vivantes. Les resets avant attente ou avant
dernier usage restent refusés. Aucune API reset n'est réintroduite par défaut.

Une tâche lancée reste susceptible d'accéder à ses captures même sur un chemin
divergent sans join ultérieur. Le modèle garde donc les exécutions en cours
séparément des derniers usages ordinaires : création au spawn ou à la réception
d'un handle, réunion par chemin, consommation au join ou au transfert à un
appel dont les exigences sont contrôlées. Un reset rencontre ces captures
immédiatement. Cela couvre aussi un spawn temporaire dont un argument suivant
réinitialise une source.

## Preuves exécutées et chronologie

Le harnais exécute du C11 avec Clang, pthread, avertissements fatals et UBSan
fatal, à O0/O2. Compilation limitée à 30 s et exécution à 10 s.

`tests/test_concrete_handle_relays.py` contient seize méthodes. Les quatorze premières passent
à O0 en 13,201 s et O2 en 13,417 s dans
`validation/concrete-handle-relay-pending-final-o0.log` et
`validation/concrete-handle-relay-pending-final-o2.log`.
Les deux compléments portent sur la convergence de boucle avec attente/reset
et la distinction entre chemin divergent et chemin continuant. Le passage de
seize méthodes (`concrete-handle-relay-state-final-o*.log`) réussit quinze
méthodes ; la fixture restante utilisait `Bool` au lieu du `bool` synchrone puis
omettait le transfert descendant explicite de h dans son bras. Une fois ces
écritures corrigées, la méthode passe isolément à O0 (0,541 s) et O2 (0,744 s),
dans `concrete-handle-relay-divergent-branch-final-o*.log`. Les deux échecs de
fixture restent consignés ; ils ne sont pas présentés comme un passage groupé vert.
Les cas admis qui divergent volontairement sont vérifiés et traduits en C,
mais ne sont pas exécutés. Les cas terminants sont exécutés sous UBSan.

Le modèle de durée de vie examine 32 scénarios : attente faite ou non, huit
ensembles de destructions et deux branches. Avant join, trois captures doivent
survivre ; après join, seules les deux cibles possibles du résultat doivent
survivre. Six scénarios sont exécutés et 26 refusés aux deux entrées. L'oracle
n'utilise ni les contrats ni le C pour calculer les permissions attendues.

Les autres essais vérifient les sources des contrats indépendamment de
l'exécution, puis exercent un appelant sans corps de fonctions. Ils comprennent
le reset après dernier usage, une capture non retournée, une allocation capturée
par transfert, une autre tâche toujours active, un refus de lancement injecté,
les slots de pool réutilisés, et les cibles de secours possibles du résultat.
Les six variantes de sources de tableaux croisent indice constant/dynamique
et création directe/fabrique concrète.

Les premiers passages ciblés ont révélé une fixture avec allocation inutilisée
(supprimée uniquement dans les cas inline), des groupes publics vides pris pour
des cibles locales, des sources absentes des contraintes, et les deux refus
globaux de reset décrits ci-dessus. Tous les journaux intermédiaires sont
conservés. Les assertions de sûreté n'ont pas été retirées.

La régression initiale de 44 méthodes passe en 66,732 s, puis une sélection de
88 méthodes passe en 101,968 s. Ces passages précèdent plusieurs correctifs.
La campagne élargie (`concrete-handle-relay-regression-final-o2.log`) termine
avec 122 méthodes et une erreur due au refus opaque historique du reset après
join. Après correction, les 122 méthodes passent en 185,547 s dans
`concrete-handle-relay-regression-complete-o2.log`. Ces passages précèdent le
suivi explicite des exécutions en cours ; sa régression est suivie séparément
dans `concrete-handle-relay-pending-regression-o2.log` : 122 méthodes réussies
en 125,725 s. Ce dernier passage précède l'ajout des exécutions en cours dans
le critère de convergence des boucles, couvert par le complément boucle ciblé.
Le complément tableaux passe onze méthodes préexistantes en 53,805 s dans
`concrete-handle-relay-array-regression-o2.log`, après la projection des coordonnées
et avant le suivi des exécutions en cours.

## Mutations

Six fautes ont été détectées dans des copies temporaires par
`tests/run_concrete_handle_relay_mutations.py` : absence de copie du descripteur
d'entrée ; groupe public vide transformé en cible locale ; source du résultat
concret effacée ; captures propriétaires ignorées au join ; rétention injustifiée
du porteur d'un champ partagé ; perte des captures non retournées lors de la
conversion publique. Journal `validation/concrete-handle-relay-mutations-o2.log`.
Cette campagne précède les derniers compléments d'application opaque du reset
et de coordonnées de tableaux ; elle ne couvre pas ces nouveaux chemins.
La campagne finale ajoute deux fautes ciblant les exécutions en cours : sept
mutations détectées et une survivante, consignées dans
`validation/concrete-handle-relay-mutations-complete-o2.log`. Le script termine
avec le statut 1 pour signaler cette survivante. L'effacement du contrôle des
captures propriétaires au join est désormais masqué par la protection immédiate
au reset. Une première campagne du suivi actif ciblait la mauvaise méthode
pour tester la libération au join ; le scénario de join direct suivi de reset
détecte cette seconde faute. Tous les journaux restent disponibles. Aucun taux
général de détection n'est déduit de ces injections.

## Limites

Ces tests n'établissent ni preuve générale de sûreté, ni exhaustivité des
ordonnancements, ni absence d'erreurs sur toutes les signatures. Aucun nouveau
passage ASan/TSan ni compilateur C indépendant n'est revendiqué.
Les signatures async générales, agrégats propriétaires, Select, remplacement
public du scheduler et placement statique général restent ouverts. L'arbitrage
sur un handle lancé capturé par une tâche inactive n'est pas modifié.
Prochain contre-exemple : `validation/open-async-sync-field-replacement.crust`.
Un auxiliaire synchrone remplace le champ &Int d'une structure capturée puis
la tâche le lit après suspension. Les deux entrées refusent ce programme avec
« remplacement des dépendances de champs par un appel depuis un état non raccordé ».
Le diagnostic est conservé dans `validation/async-sync-field-replacement-probe.log`.
L'objectif global reste actif.

Snapshot : `/tmp/crust-before-concrete-handle-relay`. Patches conservés dans
`validation/concrete-handle-relay-*.py.patch`.
