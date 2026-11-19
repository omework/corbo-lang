[English](SPAWN_BLOCKING_CYCLE.md)

# Cycle RT4/RT6 — Lancement bloquant et erreur de lancement publique

## Règles et portée

Application du brouillon 04 et de RT4–RT7, sans modification normative.
`runtime::spawn_blocking(-> tâche)` est maintenant reconnu par le parseur,
les contrats et les deux backends de lancement. L’AST conserve l’intention
bloquante jusqu’à la génération de `task_thread_start_blocking` ou
`task_async_start_blocking`.

L’interface C interne du scheduler expose un callback distinct
`launch_blocking`. Le scheduler pthread par défaut crée un thread indépendant ;
ce choix est permis par les règles et ne prétend pas implémenter une file de
workers réutilisables. Une implémentation interne qui ne fournit pas le callback
bloquant refuse ce lancement avec ENOTSUP ; elle ne le redirige pas silencieusement
vers le callback ordinaire. Les deux voies partagent les transitions d’état et
le nettoyage après échec. Le handle garde son obligation d’attente.

Le nom public `runtime::Error` remplace le nom expérimental `JoinError` dans les
signatures de résultats propriétaires déjà prises en charge, y compris les
résultats imbriqués. Les sources correspondantes de `test_async_runtime.py`
ont été migrées sans modifier leurs scénarios ni leurs assertions de sûreté.
`Err(runtime::Error::LaunchFailed)` est accepté dans les matchs de join/await.
Le C utilise désormais la constante nommée `CRUST_RUNTIME_LAUNCH_FAILED`.
Les erreurs métier restent dans le résultat intérieur.

La reconnaissance de cette variante est typée : un résultat UTF-8 ne peut pas
être traité comme une erreur de lancement, et un résultat de lancement ne peut
pas être traité comme un CharAtError, même si des codes internes sont réutilisés.
L’intégration de runtime::Error reste **partielle** : voir les limites ci-dessous.

## Invariants et contre-exemples

- Le choix bloquant ne change ni les captures ni leurs provenances. La tâche est
  transférée une fois et ne peut plus être lancée à nouveau.
- Un échec de lancement détruit les captures avant de rendre l’erreur à l’attente.
  Le slot d’une capture Int redevient disponible ; son adresse est réutilisée et
  sa destruction ne se répète pas à la sortie du parent.
- Le handle doit être attendu, même si la tâche n’a pas d’emprunt ou si son
  lancement échoue. Drop et sorties sans attente restent refusés.
- La réservation d’un &mut Int suit le handle à travers les contrats synchrones.
  Lecture, écriture, drop et reset historique sont refusés avant l’attente ;
  la mutation après join est admise.
- Le résultat propriétaire imbriqué distingue Ok(Ok), Ok(Err) et Err. Le résultat
  intérieur reste utilisable après le nettoyage du cadre de la tâche extérieure.
- Un worker par défaut bloqué sur une condition n’empêche pas un second worker
  ordinaire de signaler cette condition. L’oracle attend l’entrée effective dans
  la section bloquante avant de lancer le second worker, sans temporisation
  arbitraire. Ce scénario ne prouve pas l’équité générale du scheduler.

Le modèle indépendant de délégation couvre huit configurations : lancement
ordinaire/bloquant, appelant synchrone/async, scheduler qui accepte/refuse la
voie bloquante. Le résultat attendu est fixé par ce tableau, sans lire le choix
du compilateur. Les tests vérifient les valeurs, les adresses réutilisées et la
destruction unique. Un second oracle C distingue les compteurs des deux callbacks,
refuse un callback bloquant absent et observe quatre libérations uniques.

## Vérifications exécutées

Clang Homebrew 20.1.3 sur arm64 macOS ; C11, UBSan fatal
(`-fsanitize=undefined -fno-sanitize-recover=all`). Les oracles C imposent
`-Wall -Wextra -Werror -Wno-unused-function -pthread`.

| Exécution | Résultat | Trace |
| --- | --- | --- |
| Nouveau lot à O0 | 6 méthodes réussies, 11,740 s | validation/spawn-blocking-O0.log |
| Nouveau lot + handles obligatoires + capacités async + features async à O2 | 28 méthodes réussies, 31,516 s | validation/spawn-blocking-O2.log |
| Scénarios existants concernés, spawn ordinaire | 14 méthodes réussies, 43,697 s | validation/spawn-blocking-regression.log |
| Mêmes scénarios, appels Crust remplacés par spawn_blocking | 14 méthodes réussies, 43,890 s | validation/spawn-blocking-injected-regression.log |
| Diagnostic final de variante inconnue | Méthode concernée réussie | validation/spawn-blocking-diagnostic-final.log |
| Mutations | 5 détectées | validation/spawn-blocking-mutations-final.log |

Les six nouvelles méthodes exécutent 13 binaires par niveau d’optimisation et
vérifient 15 programmes refusés. Les 14 méthodes rejouées sont sélectionnées
explicitement par `tests/run_spawn_blocking_regression.py` : résultats propriétaires
et imbriqués avec le nom public de l’erreur, réservation mutable, réemploi entre
itérations, transferts conditionnels de handles, contrats UTF-8 et frontière du
scheduler. L’option `--blocking` remplace uniquement les appels de lancement des
programmes source, sans changer les résultats attendus.

Mutations réalisées dans des copies temporaires : perte du marqueur bloquant
au backend synchrone ; perte au backend async ; callback ordinaire appelé à la
place du callback bloquant ; nettoyage omis après échec ; confusion entre
runtime::Error et les erreurs UTF-8. Toutes sont détectées par des échecs
reproductibles. Aucun taux de détection global n’est déduit de ces cinq fautes.

Commandes de reproduction principales :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_spawn_blocking -v
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_spawn_blocking test_handle_obligations test_async_capacity test_async_type_features -v
python3 tests/run_spawn_blocking_regression.py
python3 tests/run_spawn_blocking_regression.py --blocking
python3 tests/run_spawn_blocking_mutations.py
```

## Limites et suite du travail

État historique du lot. Le cycle suivant [RUNTIME_ERROR_VALUES_CYCLE.md](RUNTIME_ERROR_VALUES_CYCLE.md)
résout le premier écart ci-dessous pour les contextes qui y sont testés.

- `runtime::Error` n’est pas encore une valeur autonome transmissible par une
  liaison `Err(error)` puis par un appel de fonction. Le programme conforme à la
  cible normative `validation/open-runtime-error-value.crust` demeure refusé ;
  son diagnostic est consigné dans `validation/open-runtime-error-value.log`.
  Ce refus est un écart d’implémentation, pas une règle retenue.
- Les signatures génériques `runtime::Handle<T>` et l’ensemble des formes de
  `Result<T,runtime::Error>` restent à intégrer. Les signatures propriétaires
  couvertes ici ne constituent pas une preuve pour tous les types de résultats.
- L’installation publique `runtime::set_scheduler` directement dans main, la
  conservation des réveils et la politique générale de reprise/migration restent
  ouvertes. Le callback testé ici est une frontière C interne, non une API de
  personnalisation du scheduler déjà offerte au langage.
- `runtime::thread`, Select et les mutex restent ouverts. Les constructeurs de
  mutex demeurent reportés conformément à points-ouverts.md.
- Le C arbitraire n’est pas vérifié. Les callbacks de l’oracle respectent leur
  contrat : un refus de lancement n’a pas exécuté la tâche. Ce lot ne prouve pas
  la sûreté d’un callback qui violerait ce contrat.

Les suites entières du dépôt n’ont pas été relancées dans ce cycle ; les lots
exécutés et leurs interactions sont énumérés ci-dessus. Le chantier des sept
brouillons reste ouvert.
