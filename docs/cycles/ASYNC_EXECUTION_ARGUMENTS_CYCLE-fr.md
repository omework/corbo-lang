[English](ASYNC_EXECUTION_ARGUMENTS_CYCLE.md)

# Handles lancés transmis à une fonction depuis un état async

## Règles et périmètre

Ce lot applique les transferts explicites, les réservations jusqu'à attente,
les dépendances du résultat et RT5–RT7, MT5–MT6, SL2. Aucune nouvelle sémantique
n'est inventée. Le choix utilisateur SL2 reste : refuser une perdante de Select
qui possède un handle lancé encore à attendre, sans join caché.

Le passage explicite d'un handle à un relais synchrone depuis async est raccordé
pour les signatures représentées. Cela ne lance pas la tâche à nouveau et
n'attend pas sa terminaison. L'auxiliaire reçoit l'obligation d'attente et peut
la rendre avec le handle. Un auxiliaire qui appelle join reste interdit depuis
une fonction async ; il est utilisable dans un bloc de thread natif.

## Défauts trouvés et corrections

Le programme `validation/open-public-structure-async-relay.crust`, valide,
était refusé par le registre des signatures aux deux étapes. Le pont C et
le backend acceptent maintenant les paramètres execution, publics ou concrets,
en conservant captures, sources de stockage, prêts du résultat et effets différés.
Les arguments sont préparés de gauche à droite. Une suspension dans un argument
ultérieur conserve les réservations ; une sortie abandonnant le handle préparé
est refusée. Une sortie avant sa création reste admise.

`task_sync_adopt` transmet le pointeur et l'erreur à la représentation synchrone
sans soumission ni attente, invalide la source et conserve le protocole commun
de terminaison. Les workers natifs async sont déjà détachés ; leur fin est
observée par le même protocole worker_done.

L'analyse des effets traitait aussi un relais pur de handle comme un lancement.
Elle conserve désormais ses captures différées sans exécuter leurs effets.

Un contre-exemple de sûreté a ensuite été trouvé : dans
`validation/open-native-wait-argument-field-effects.crust`, insérer `drop(->b)`
avant `print(*v.data)` après l'appel de l'auxiliaire `wait` était accepté aux deux
étapes, malgré le champ désormais susceptible de référencer b. Le journal
`validation/async-execution-arguments-native-field-probe.log` conserve cette
acceptation ; le C invalide n'a pas été exécuté.

L'attente signalée par le contrat applique maintenant les effets du handle
au backend et à l'analyse des champs. Elle conserve aussi l'état initial,
possible en cas de LaunchFailed. Le test couvre les champs locaux au bloc
natif et les champs de porteurs injectés, visibles chez son appelant.
Omettre séparément chacune de ces deux corrections est ciblé par mutation.

## Validation exécutée

La suite ciblée finale passe 19 méthodes à O0 en 21,740 s : 26 exécutions
natives (dont l'oracle du pont C), 25 programmes invalides et 50 contrôles de
refus. Journal `validation/async-execution-arguments-complete-count-o0.log`.
Le baseline de mutations à O2 passe ces 19 méthodes en 22,020 s ; les six
mutations finales sont détectées par assertions, sans survivante ni délai
dépassé dans cette dernière campagne. Journal
`validation/async-execution-arguments-complete-mutations-o2.log`.
Ces six fautes choisies ne donnent pas un taux global de détection.

La régression élargie passe 214 méthodes à O2 en 255,973 s, avec
`CRUST_SANITIZE=undefined` pour les harness historiques. Elle comprend les
17 premières méthodes de ce lot, les arguments de tâches, les handles publics
de structures/références/allocations/vues, les effets de champs, le nettoyage
suspendu, Select, les blocs natifs, les relais concrets et le stockage des
résultats. Les deux dernières méthodes du lot sont couvertes par les baselines
finaux O0 et O2 ci-dessus. Journal
`validation/async-execution-arguments-regression-o2.log`.
Tous les processus cités sont terminés. Les campagnes finales sortent avec
le code 0 ; les essais intermédiaires en échec restent archivés.

Commandes finales reproductibles depuis le dépôt :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 validation/count_async_execution_arguments.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 tests/run_async_execution_argument_mutations.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 tests/run_sync_task_argument_mutations.py
CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_async_field_return_model test_async_field_reborrow_model test_async_struct_reference_field_model -v
CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined PYTHONPATH=.:tests python3 -m unittest test_async_execution_arguments test_sync_task_arguments test_public_structure_handles test_public_borrowed_handles test_public_owned_handles test_public_view_handles test_async_field_application test_sync_handle_field_effects test_suspended_cleanup test_select_contracts test_select_source test_native_blocks test_native_sync_calls test_concrete_handle_relays test_task_result_storage test_async_child_field_effects -v
```

La dernière commande inclut maintenant les deux méthodes ajoutées après le
lancement de la campagne archivée ; son nombre attendu est donc 216.

- Suite ciblée : transferts répétés, types publics/concrets, résultats scalaires,
  références partagées/mutables, tableaux, str, structures locales/en pool,
  réemploi de capacité un, erreurs de lancement et absence de resoumission.
- Refus : cibles/pools trop courts, drop anticipé, réemploi du handle consommé,
  transfert implicite, type incompatible, join caché, sorties return/break/continue
  et perdante Select abandonnant un handle préparé.
- Trois modèles finis existants passent : chemins de résultat/dernière utilisation,
  disjonction de champs/réemprunts, dépendance tâche → porteur → cible.
  Ils couvrent 53 exécutions natives admises et 19 refus au vérificateur,
  en trois méthodes, 36,986 s, à O2. Ils ne constituent pas un modèle complet
  du scheduler ni du nouveau pont C.
- La campagne historique des arguments de tâches passe son baseline de 18
  méthodes en 17,775 s ; les sept fautes sont détectées, dont une par plantage
  du compilateur. Journal `async-execution-arguments-historical-mutations-o2.log`.

Les exécutions natives utilisent clang C11, pthread, les avertissements traités
comme erreurs, UBSan fatal et O0/O2 selon le journal. Aucun résultat ASan ou
TSan nouveau n'est revendiqué.

## Essais intermédiaires conservés

Les premiers essais ont corrigé des erreurs de fixture : noms de liaisons
réutilisés, transfert vers un bloc enfant absent, expression après return,
et captures de bloc natif non explicites. Les journaux restent disponibles.
La sixième suite a refusé le cas valide de champs après attente : le backend
avait été corrigé mais pas encore le résumé de champs. La septième passe
17 méthodes en 10,029 s.

Les deux premières campagnes de mutations ont rencontré des ancres non uniques
ou mal orthographiées. La seconde a aussi observé des délais dépassés sur les
mutations perdant le pointeur ou l'erreur : classées inconclusives, sans masquer
ces sorties. Un oracle C direct du transfert entre représentations contrôle
désormais ces invariants sans scheduler ni attente. Sa première fixture ne
générait pas le runtime async nécessaire ; elle a été corrigée en demandant
un lancement depuis async. Aucun résultat de cette fixture incorrecte n'est
compté comme preuve sur le runtime.

## Limites et suite

Les auxiliaires attendant un handle et modifiant aussi des champs, ou renvoyant
un résultat emprunté/propriétaire dépendant de cette attente, ne sont pas
généralisés par l'analyse des effets différés. Elle conserve un diagnostic
d'incomplétude lorsque l'ordre ou les provenances ne sont pas raccordés.
Les cas testés utilisent un résultat scalaire et n'ajoutent pas d'écritures
propres dans l'auxiliaire attendant.

Le remplacement des dépendances d'un champ descendant, les signatures générales
et l'API publique de remplacement du scheduler restent ouverts. La capture d'un
handle lancé par une tâche inactive reste un arbitrage séparé de SL2.
Une suite réussie n'établit pas la sûreté générale du langage ou des exécutions
concurrentes. Ce rapport ne clôt pas l'objectif global.

Les quatre différences du compilateur/runtime sont archivées sous
`validation/async-execution-arguments-*.py.patch`, depuis le snapshot préalable
`/tmp/crust-before-async-execution-arguments`.
