[English](ASYNC_CAPTURE_FIELD_CONTRACTS_CYCLE.md)

# Contrats de capture par champ et restitution du porteur empruntant

## Périmètre et règles

Ce lot applique les règles existantes T1/T6, B1/B2/B3/B4a, D1, ST6–ST15,
AS2/AS8–AS14 et MT8, ainsi que la distinction de stockage T/A<T>.
Aucune règle normative n'est modifiée. Les références partagées et mutables
restent distinctes après passage par un contrat ; la restitution d'un porteur
ne promeut ni ses cibles ni son pool. AS12 exige de conserver les dépendances
du résultat, sans les attacher arbitrairement à tous les paramètres.

Le périmètre exécutable couvre les structures à champs Int/&Int/&mut Int
prises en charge, locales ou allouées en pool, leurs captures propriétaires,
les relais nominaux de tâches synchrones, la restitution entière, les enfants
async directs et les fabriques synchrones prises en charge. Les graphes mêlant
A<T> et références et les signatures générales ne sont pas déclarés terminés.

## Défauts corrigés

Les deux contre-exemples du cycle précédent sont maintenant admis :

- `validation/open-owned-borrowed-mixed-task-relay.crust` : le contrat regroupait
  les champs par numéro de capture ; la cible partagée devenait exclusive au
  contact du champ mutable. La lecture partagée passe, les accès concurrents
  incompatibles restent refusés.
- `validation/open-owned-borrowed-capture-result-owner.crust` : le résultat
  entier ne pouvait projeter les cibles des champs depuis le paramètre déplacé.
  Il les conserve maintenant après join, sans demander un paramètre emprunté
  supplémentaire ni conserver artificiellement l'état terminé.

Un troisième refus excessif est corrigé : après restitution directe d'un
seul champ partagé, la cible d'un autre champ restait réservée. Le test
`test_detached_result_releases_unrelated_field` libère cette autre cible puis
utilise la référence retournée. La variante qui détruit sa vraie cible est
refusée. La première sonde tentait un drop depuis un bras enfant sans transfert
entrant ; le test final reçoit la référence dans le parent et y effectue les
drops, afin d'isoler la propriété étudiée.

## Implémentation

`capture_paths.py` définit les sélecteurs de capture : numéro de paramètre,
complété d'un chemin de champ lorsqu'il faut le distinguer. Les contrats de
résultats, les sources symboliques et les dépendances concrètes utilisent la
même identité de champ. Le préfixe de capacité partagée/mutable reste séparé.

Le backend async prépare les prêts par champ avant de consommer le porteur.
Les résultats des enfants et des fabriques réattachent ces prêts au porteur
reçu. Les cibles d'un résultat entier sont projetées depuis les captures
correspondantes. Les chemins de résultats directs filtrent les autres champs.
Le code de transfert physique conserve le pointeur existant ; aucune copie
ni translation d'adresse n'est introduite par ce lot.

Les snapshots antérieurs des modules Python sont dans
`/tmp/crust-before-capture-field-contracts`. Les diffs sont conservés sous
`validation/capture-fields-*.patch`. Les points d'injection des huit mutations
historiques de captures propriétaires ont été adaptés au nouveau nommage,
sans changer la faute injectée ni les attentes des tests.

## Preuves exécutées

`tests/test_async_capture_field_contracts.py` contient treize méthodes.

- `validation/capture-fields-final-count-o0.log` : 13 méthodes, 20,833 s,
  24 exécutions natives et 37 programmes invalides, chacun vérifié par
  `verify_program` et `compile_source`, soit 74 vérifications de refus.
- `validation/capture-fields-final-suite-o2.log` : 13 méthodes, 21,121 s, réussite.
- Les deux suites emploient le harnais Clang C11/pthread, Wall/Wextra/Werror,
  Wno-unused-function et UBSan fatal ; l'optimisation varie entre O0 et O2.
- `validation/capture-fields-first-regression-o0.log` : 47 méthodes réussies
  avant le dernier complément de projection des résultats directs.

Les scénarios comprennent les relais successifs, le retour mutable, les
projections partagées indépendantes, les scopes parents, les boucles,
les retours conditionnels, les branches Select, les tâches inactives et les
échecs de lancement injectés. Le test d'adresse compare le pointeur avant
capture et après retour, pour un porteur local et un porteur de pool ; avec
un pool d'un slot, une nouvelle allocation réutilise ce slot après drop.
Les destructions du porteur et de la cible sont comptées séparément.

Deux petits modèles indépendants fixent les attentes :

1. Une table de six opérations : lecture/écriture/drop de la cible partagée
   ou mutable. Seule la lecture de la cible partagée est autorisée tant que
   la tâche reste vivante ; deux profondeurs de relais sont exercées.
2. Les quatre dispositions intérieur/extérieur du pool du porteur et de la
   cible. Seule la disposition où tous deux survivent au receveur extérieur
   est admise. Le modèle ne consulte pas les décisions du compilateur.

## Mutations et essais intermédiaires

`validation/capture-fields-final-mutations-o2.log` : base de douze méthodes
réussie, puis sept mutations détectées. Le test d'adresse a été ajouté ensuite
et les treize méthodes finales sont exécutées séparément aux deux optimisations.
Les fautes fusionnent les champs, effacent les cibles du résultat, regroupent
les prêts async, effacent ces prêts, perdent un chemin de résultat, retiennent
un champ non retourné ou perdent les prêts dans une fabrique.

Le premier passage (`capture-fields-mutations-o2.log`) détectait deux fautes
uniquement par un diagnostic différent : un second drop du même objet masquait
l'acceptation du premier. Les variantes finales suppriment ce second drop.
Le passage final détecte effectivement l'acceptation indue aux deux étapes
pour l'effacement des prêts async et celui des prêts de fabrique. Une détection
par refus d'un programme valide est distinguée d'une violation exécutée ;
aucun taux global de détection n'est revendiqué.

`validation/capture-fields-historical-mutations-fixed-o2.log` : les huit
mutations historiques sont détectées. La perte de capture concrète est encore
détectée par un changement de diagnostic dans ce test historique ; elle ne
constitue pas à elle seule une preuve d'acceptation indue ou d'exécution fautive.

Les erreurs intermédiaires sont conservées : import avant `__future__`, masquage
du helper de décodage par une variable locale, deux noms de receveurs dupliqués
dans les nouveaux tests, et erreur de guillemets dans l'adaptation du script de
mutations historique. Les journaux `initial-probe`, `existing-o0`,
`new-initial-o0` et `historical-mutations-o2` permettent de les examiner.

## Écarts ouverts

`validation/open-owned-borrowed-detached-factory.crust` reste refusé aux deux
étapes (`validation/capture-fields-open-detached-factory.log`). Le cas direct
détachant un champ fonctionne ; une fabrique synchrone qui crée la même tâche
provoque une inférence prématurée du résultat emprunté, avant que son contrat de
terminaison soit disponible. Ce programme valide reste à raccorder ; ce n'est
pas une nouvelle restriction normative.

Les graphes mixtes A<T>/références, les autres familles de projections et
signatures async, l'API publique du scheduler et le placement anticipé général
restent ouverts. Les deux arbitrages sur les handles déjà lancés restent
inchangés. Aucun résultat ASan/TSan nouveau ni preuve générale de sûreté n'est
revendiqué. La clôture de ce lot ne signifie pas la fin de l'objectif global.

## Régression finale

`validation/capture-fields-regression-o2.log` : 195 méthodes réussies en
199,572 s, avec CRUST_TEST_OPT=-O2 et CRUST_SANITIZE=undefined. Modules :
async_owned_borrowed_captures, async_borrowed_local_results,
local_result_envelopes, async_local_captures, async_structure_effects,
select_source, suspended_cleanup, native_blocks, storage_requirements,
public_borrowed_handles, concrete_handle_relays, async_detached_field_returns,
async_borrowed_struct_pools.

Le compilateur n'a pas changé pendant ni après cette régression. Les treize
méthodes du nouveau lot sont exécutées séparément sur le même compilateur.
Tous les processus finaux cités sont terminés. Le lot est clos dans son
périmètre décrit, avec l'écart de fabrique conservé et l'objectif global actif.


Suite : l'écart de fabrique détachant un champ partagé est corrigé dans le
[cycle des fabriques détachées](DETACHED_TASK_FACTORIES_CYCLE.md), qui corrige
aussi la perte d'un prêt de résultat enfant après await. Les constats ouverts
ci-dessus décrivent l'état antérieur à ce complément.
