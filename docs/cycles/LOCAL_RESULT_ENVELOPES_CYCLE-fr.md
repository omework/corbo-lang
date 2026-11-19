[English](LOCAL_RESULT_ENVELOPES_CYCLE.md)

# Enveloppes Result de valeurs locales

## Périmètre et règles

Ce lot applique T1/T6, B1/B2/B4, D1, L1/L2/L6/L7, ST6–ST15,
AS9/AS12, RT6/RT7 et les exigences de stockage des contrats, sans nouvelle
décision normative. Il poursuit ASYNC_BORROWED_LOCAL_RESULTS_CYCLE.md.
Les flèches restent explicites ; aucune promotion de cible empruntée et aucun
reset public ne sont introduits. Les consignes AGENTS.md et
VALIDATION_GUIDELINES.md ont été suivies.

Le résultat `Result<T,runtime::Error>` conserve la racine locale T ;
`Result<A<T>,runtime::Error>` conserve une allocation de pool. La différence
fait partie des signatures, même quand aucune charge Ok n'est possible.
Les deux enveloppes ne deviennent pas interchangeables dans un if, une boucle,
une annotation ou une contrainte de type feature.

## Défauts reproduits et corrections

- `validation/open-sync-join-local-payload-type.crust` : retour synchrone de
  l'enveloppe d'une structure locale contenant un emprunt. Le parseur conserve
  maintenant le stockage de la charge séparément du mode interne join_owned.
  Les contrats de paramètres, résultats et méthodes propagent cette information.
- Les résultats futurs des handles possèdent une identité distincte de leurs
  captures. Leur restitution par un helper ne doit pas être analysée comme une
  nouvelle allocation. L'identité d'entrée et les assets symboliques du résultat
  sont maintenant conservés pendant la vérification modulaire.
- Les champs empruntés et réservations du résultat sont transportés par les
  appels vérifiés sur contrat, les enveloppes et leur extraction. Les cibles
  restent protégées après libération de l'état producteur.
- `validation/open-async-local-result-envelope.crust` : destination de la
  racine locale à travers une enveloppe async, puis un second join. Le placement
  et le pont synchrone distinguent maintenant la forme de l'enveloppe de celle
  de la charge. Les statuts d'échec de chaque lancement restent distincts.
- La résolution de méthodes de type features utilisait un catalogue sans les
  fonctions async ; le cas valide provoquait KeyError. Le catalogue initial et
  celui des fonctions spécialisées sont désormais transmis à l'analyse.
- `validation/open-local-result-absent-payload.crust` : le corps enfant ne
  termine pas normalement, mais son lancement peut échouer. L'analyse complète
  prouve l'absence de charge ; elle ne l'infère jamais d'une liste de sources
  vide. Le descripteur d'enveloppe ne reçoit alors aucune identité d'allocation
  fictive, ni dépendance empruntée de charge inexistante. Cette preuve passe par
  les contrats, blocs, if et boucles. Une branche capable de terminer conserve
  ses sources et ses emprunts. Le type de stockage reste vérifiable séparément.
- `validation/open-local-result-mixed-storage.crust` était accepté par les
  deux entrées alors que ses branches produisent respectivement Result<Point>
  et Result<A<Point>>. Le contrôle de stockage à la jonction refuse maintenant
  ce mélange, y compris avec deux charges prouvées absentes.

## Couverture et oracles

`tests/test_local_result_envelopes.py` contient 19 méthodes. Le comptage O0
final rapporte 29 exécutions natives et 36 programmes invalides, chacun refusé
par verify_program et compile_source (72 vérifications de refus).

Les cas admis vérifient les valeurs imprimées et, selon le scénario, les
destructions uniques, l'absence de destruction d'une charge non construite et
le réemploi du pool. Ils croisent relais synchrones, contrats opaques,
méthodes, captures partagées/mutables, branches, boucles, annotations, résultats
imbriqués, attente directe et échecs de lancement injectés. Les programmes
invalides comprennent destruction prématurée, cible trop courte, mauvais
stockage, transfert absent et réutilisation après destruction.

Le modèle indépendant fini croise deux sources (local/pool) et deux signatures
(T/A<T>) ; il attend l'acceptation exactement quand elles correspondent. Il ne
consulte pas les choix internes du compilateur pour définir cette attente.
Ce modèle ne prouve pas la totalité du système de types.

Les corps infinis du scénario sans charge ne sont jamais lancés par les tests :
le harnais injecte le refus au premier lancement. Les scénarios mixtes exécutent
un chemin terminant et un chemin d'échec de lancement. Les contrôles de types
sur des corps infinis sont uniquement des compilations.

Le harnais natif utilise Clang C11, pthread, Wall/Wextra/Werror,
Wno-unused-function, UBSan fatal et les niveaux O0/O2. La régression historique
reçoit aussi CRUST_SANITIZE=undefined lorsque son harnais exige cette option.
ASan/TSan ne sont pas établis par ce lot.

## Chronologie des preuves

Tous les journaux sont sous `validation/`, préfixés `local-result-envelopes-`.

- `baseline.log`, `initial.log`, `symbolic.log` : refus initiaux ; `identity.log`
  exécute ensuite le programme reproduit et affiche 7.
- `tests-o0.log`, `constraints-o0.log`, `expanded-o0.log` : raccordement des
  assets et premiers cas (5 puis 8 méthodes).
- `branches-o0.log` : deux échecs, dont une fixture utilisant Bool en contexte
  synchrone. La fixture utilise bool et les transferts requis ; le défaut
  d'annotation Result est corrigé dans `annotations-o0.log` (10 méthodes).
- `async-probe-initial.log`, `async-placement.log`, `async-tests-o0.log` :
  destination de l'enveloppe async corrigée (12 méthodes).
- `bridge-o0.log`, `bridge-contract-o0.log`, `full-o0.log` : exigences de
  stockage des résultats de handles propagées (14 méthodes).
- `feature-o0.log`, `feature-catalog-o0.log` : catalogue async corrigé.
- `final-counted-o0.log` : 16 méthodes, 19 exécutions, 23 invalides/46 refus.
  `final-mutations-o2.log` détecte les dix mutations de cette version.
- `regression-o2.log` : 163 méthodes, un échec de diagnostic attendu dans
  test_plain_join_contracts ; le refus reste correct. Le test reconnaît maintenant
  le diagnostic précis de charge Result incompatible. `final-regression-o2.log`
  passe ensuite 94 méthodes, avant la correction du cas sans charge.
- `absent-probe.log` conserve le refus interne initial. `absent-fixed-probe.log`
  montre 99 et une destruction de n après injection d'échec.
- `absence-tests-o0.log`, `absence-contracts-o0.log`, `absence-storage-o0.log`,
  `absence-relays-o0.log`, `absence-control-fixed-o0.log` conservent les défauts
  intermédiaires des relais et jonctions. `absence-branches-o0.log` passe les
  deux méthodes dédiées, après corrections.
- `completed-count-o0.log` : 18 méthodes, 26 exécutions, 31 invalides/62 refus.
  `absence-mutations-o2.log` détecte les 14 mutations de cette version.
  `absence-regression-o2.log` passe 106 méthodes en 133,658 s ; ce processus
  avait chargé le compilateur avant la correction du mélange local/pool.
- `mixed-storage-probe.log` conserve l'acceptation incorrecte aux deux étapes.
  `control-loans-probe.log` vérifie les trois formes bloc/if/boucle avec prêt.
- `storage-final-o0.log` : 19 méthodes en 17,094 s, 29 exécutions natives et
  36 invalides/72 refus, sur la version incluant le contrôle de jonction.

## Audit des mutations

`storage-mutations-o2.log` a une base de 19 méthodes réussies à O2, puis
13 mutations détectées et une survivante : suppression du contrôle anticipé
du stockage au retour. Le journal `redundant-guard-audit.log` démontre sur un
programme minimal que le contrôle de construction de Result refuse encore le
mauvais type aux deux étapes. C'est une redondance sur ce scénario, pas une
preuve d'équivalence générale du mutant.

Le runner final remplace cette injection redondante par la suppression du
contrôle de compatibilité à la jonction, exercée sur le contre-exemple qui
était effectivement accepté. Les tests et leurs attentes ne sont pas affaiblis.
La mutation de signature de type feature est détectée par le mauvais diagnostic
de phase : un contrôle ultérieur de stockage refuse encore le programme.
Elle ne démontre donc pas à elle seule une acceptation dangereuse.

`historical-mutations-o2.log` détecte sept mutations historiques, puis s'arrête
sur un point d'injection périmé : la condition d'export inclut maintenant task.
Le point est actualisé en conservant la même faute (oublier les Result exportés)
et le même test. Les journaux initiaux sont conservés.

Résultats terminaux sur la version finale :

- `final14-mutations-o2.log` : base de 19 méthodes réussie en 18,427 s à O2,
  puis 14 mutations détectées.
- `historical-mutations-final-o2.log` : base de 12 méthodes réussie en
  35,657 s, puis huit mutations historiques détectées.
- `final-regressions-o2.log` : 138 méthodes réussies en 149,861 s, modules
  plain_join_contracts, storage_requirements, type_features, async_type_features,
  builtin_features, async_result_storage, async_borrowed_local_results,
  async_failure_only_results, async_local_owned_result_graphs, owned_results et
  nested_plain_results. CRUST_TEST_OPT=-O2 et CRUST_SANITIZE=undefined.

Tous les processus cités dans ces résultats finaux sont terminés. Ce lot est
clos dans le périmètre décrit ; l'objectif global reste ouvert.

## Limites et suite

La portée concerne les familles représentées dans ces tests ; les captures
propriétaires de structures empruntantes, graphes mixtes généraux, signatures
et projections récursives async restent ouverts. Les décisions relatives aux
handles lancés capturés et aux perdantes de Select restent en attente d'arbitrage.
Le scheduler public et les autres lots ouverts ne sont pas déclarés achevés.
Les tests finis, UBSan et mutations ne constituent pas une preuve générale de
sûreté. Les diffs du lot sont conservés sous `validation/`.

Le prochain cas est reproduit dans
`validation/open-owned-borrowed-structure-capture.crust` : transférer une
structure locale View contenant &Int vers une tâche qui lit sa cible après
yield. `owned-borrowed-structure-capture-baseline.log` conserve le refus aux
deux étapes par la restriction actuelle de signature de capture. Ce programme
valide reste à raccorder ; le présent lot ne prétend pas le prendre en charge.
