[English](SYNC_HANDLE_BRIDGES_CYCLE.md)

# Fabriques synchrones de handles dans les états async

## Règles et implémentation

Ce lot applique AS8/AS10/AS12, RT4–RT8, B1–B5, D1/D3, U1 et les obligations
de stockage des pools. Aucune règle normative n’est ajoutée ou modifiée.
Un corps async peut appeler un auxiliaire synchrone retournant un
runtime::Handle<T>, recevoir ce handle puis l’attendre, ou écrire directement
`launch(...).await`. Le contrôle de l’appel utilise le contrat de l’auxiliaire.
Le backend génère une seule fonction C de pont par auxiliaire utilisé.

Le contrat public distingue les captures vivantes pendant l’exécution et les
cibles du résultat qui restent nécessaires après l’attente. Les arguments
préparés restent protégés pendant les arguments suivants, y compris en cas de
suspension. L’analyse des résultats async reconnaît aussi les projections du
résultat du handle dans les contrats synchrones ; elle ne rattache pas le
résultat à chaque argument du helper. Les sources des captures transférées et
celles des allocations retournées sont suivies séparément.

Le runtime reçoit le CrustExecution synchrone et le consomme dans un
CrustAsyncExecution. Un thread joinable réussi est détaché ; une tâche du
scheduler en pool n’a pas de thread individuel à détacher ; un lancement
échoué conserve son erreur sans tenter de détachement. L’adoption ne fait pas
de join. L’attente utilise les notifications de l’état, puis extrait le résultat
avant de rendre le slot. Le thread ne touche plus cet état après sa publication
de terminaison, comme pour les lancements async directs existants. Le handle
source est invalidé et son marqueur de consommation activé.

Les entrées symboliques empruntées du pont sont rattachées au stockage externe
qui les fournit. Les rattacher à la portée locale du pont faisait refuser à
tort le transfert du handle retourné. Les allocations possédées reçues restent
rattachées à la portée locale avec leurs obligations de nettoyage ; ce
changement ne promeut aucune donnée locale du programme.

## Contre-exemples

`validation/open-public-view-handle-async-helper.crust` compile et s’exécute
maintenant, avec la sortie été. L’ancien refus de signature est conservé dans
`validation/sync-view-bridges-next-handle-probe.log`. Le premier essai de pont
révélait le mauvais rattachement symbolique des emprunts : journal
`validation/sync-handle-bridges-initial-probe.log`. Après correction, le programme
est exécuté dans `validation/sync-handle-bridges-second-probe.log`.

Un deuxième cas retournait la première vue de deux arguments. La destruction
de l’autre capture après join restait refusée par l’analyse précoce. La
projection précise du contrat corrige cet écart : journaux precision-probe
et precision-second du préfixe `validation/sync-handle-bridges-`.

L’attente directe d’une fabrique était encore refusée alors que la réception
nommée fonctionnait : `validation/open-sync-handle-direct-await.crust`, journaux
direct-await-probe et direct-await-second. Les deux formes sont désormais
couvertes. L’abandon de cette attente était refusé avec un diagnostic de
fonction async inconnue ; il reçoit maintenant le diagnostic U1 du résultat
faillible sans usage explicite. Ce cas n’était pas un programme invalide accepté.

Les premiers tests &Int/&mut Int ont révélé que leur analyse de provenance ne
consultait pas le contrat d’une fabrique synchrone lors d’un await. Ce chemin
est raccordé. Les premiers tests de join direct attendaient un diagnostic plus
spécifique que le diagnostic existant de match ; leur attente textuelle est
élargie en conservant le refus. Aucun test d’acceptation n’est changé en refus.
Les journaux intermédiaires, y compris les deux premières passes finales avec
diagnostic U1 incorrect, restent conservés.

## Exécutions

`tests/test_sync_handle_bridges.py` : seize méthodes passent ensemble avec
Clang C11, pthread, avertissements fatals et UBSan fatal :

- O0 : 20,822 s, `validation/sync-handle-bridges-complete-o0.log`.
- O2 : 21,022 s, `validation/sync-handle-bridges-complete-o2.log`.

Le périmètre exercé comprend :

- Deux relais synchrones, spawn, spawn_blocking et thread natif, puis attente
  du handle dans un corps async ; annotations publiques et attente directe.
- Résultats Int, &str, &Int, &mut Int, tranches partagées/mutables Int/u8,
  Result<&str,SliceError>, allocations Int/String/Vector<Int/u8>.
- Captures locales protégées jusqu’à l’attente ; cibles du résultat protégées
  après l’attente et jusqu’au dernier usage ; captures sans lien libérées.
- Drop, sortie anticipée, double attente et résultat de handle abandonné
  refusés. Join depuis async reste refusé. L’ordre des arguments est observé,
  avec capture mutable préparée avant un argument suspendu.
- Pools locaux de capacité un réemployés après attente/destruction, captures
  propriétaires nettoyées sur un refus de lancement injecté, résultats alloués
  avec chemin de secours et refus de fuite hors d’un pool local.
- Chaîne de six fabriques imbriquées, sept niveaux async, deux workers par
  défaut, douze passages successifs. Elle termine sans bloquer les workers
  sur l’attente d’un enfant et réemploie les frames.
- Contrat C d’adoption : quatre combinaisons lancement réussi/échoué et
  exécution en pool/joinable ; conservation du pointeur et de l’erreur,
  consommation du handle source, détachement uniquement quand requis.

Un modèle indépendant énumère 32 combinaisons de captures détruites avant/après
attente et deux choix de résultat. Six scénarios valides sont exécutés ; 26
invalides sont refusés par verify_program et compile_source. Le modèle calcule
les ensembles nécessaires sans consulter les décisions du compilateur.
Un contrôle supplémentaire refuse une allocation dans le pool encore emprunté
par le handle : `validation/sync-handle-bridges-pool-reservation-probe.log`.

Régressions exécutées :

- 73 méthodes O2, 74,645 s : ponts sync, contrats publics de handles et
  notifications d’attente, `validation/sync-handle-bridges-regression-o2.log`.
- 24 méthodes O2, 28,303 s : spawn_blocking et threads natifs,
  `validation/sync-handle-bridges-native-regression-o2.log`.
- 19 méthodes O2, 16,408 s : try_slice async et obligations d’attente,
  `validation/sync-handle-bridges-await-usage-regression-o2.log`.

Le premier passage précède l’ajout de l’attente directe ; le deuxième précède
le dernier diagnostic U1 ; le troisième et les seize tests ciblés finaux
couvrent le dernier état du compilateur. Ce ne sont pas des passages de toute
la suite du dépôt. La compilation Python des trois modules modifiés et des
deux fichiers de tests/campagne réussit.

## Mutations et limites de preuve

`tests/run_sync_handle_bridge_mutations.py` détecte six fautes : perte des
emprunts des captures, perte des emprunts du résultat, oubli de la projection
précise du résultat, absence de détachement du thread joinable, effacement de
l’erreur de lancement, absence de consommation du handle source. Journal :
`validation/sync-handle-bridges-mutations-o2.log`. Cette campagne précède les
compléments d’attente directe ; ses chemins cibles restent inchangés.
Les assertions qui échouent dans ce journal sont celles des copies mutées.

Aucune preuve formelle, résultat nouveau ASan/TSan ou second compilateur C.
Les tests de progression n’établissent pas l’équité pour tout programme ni
l’absence universelle de course. Les mutations sont un échantillon ciblé.

## Écarts restants

Mise à jour : les projections Int décrites ci-dessous sont raccordées dans
[SYNC_HANDLE_FIELDS_CYCLE.md](SYNC_HANDLE_FIELDS_CYCLE.md). Le diagnostic suivant
est conservé comme constat historique ; le nouveau rapport précise les limites.

Les projections de champs dans le résultat d’une fabrique ne sont pas encore
raccordées à ce pont. Programme minimal :
`validation/open-sync-handle-field-result.crust`, refus reproduit dans
`validation/sync-handle-bridges-field-result-probe.log`. C’est une limite de
l’implémentation, pas une nouvelle interdiction du langage. Les signatures
et captures générales restent incomplètes ; ce lot ne couvre pas toutes les
charges acceptées par la syntaxe publique de Handle.

La capture d’un handle déjà lancé dans une instance inactive reste l’arbitrage
AS14/RT6/RT7 documenté séparément. Une fabrique appelée pendant l’exécution du
corps ne change pas ce point : son handle est créé à cet instant et doit être
attendu avant toute sortie. Les autres sujets globaux, dont Select, scheduler
personnalisable, mutex reportés et placement statique général, restent ouverts.
Reset demeure hors du prototype par défaut.

Snapshot : `/tmp/crust-before-sync-handle-bridges`. Différences conservées dans
`validation/sync-handle-bridges-*.py.patch`. L’objectif global reste actif.
