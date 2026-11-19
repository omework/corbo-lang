[English](ASYNC_OWNED_BORROWED_CAPTURES_CYCLE.md)

# Captures propriétaires de structures contenant des emprunts

## Portée

Ce lot applique les règles existantes T1/T6, B1/B2/B3/B4a, D1, ST6–ST15,
L1/L2/L6, AS2/AS5/AS8/AS9/AS13/AS14, RT6/RT7/RT8 et MT8. Les consignes
AGENTS.md et VALIDATION_GUIDELINES.md sont suivies. Aucune décision normative
n'est modifiée. Le résultat précédent est décrit dans
LOCAL_RESULT_ENVELOPES_CYCLE.md.

Une structure à champs Int, &Int et &mut Int peut être transférée entière à
une tâche. Celle-ci détruit le porteur reçu ; elle ne détruit pas les cibles
empruntées. Les captures conservent les sources et les capacités de ces champs
pendant la vie de la tâche, indépendamment du dernier usage du nom de la tâche.
Le transfert peut partir d'une valeur locale ou d'une allocation de pool.

Cette couverture inclut les appels directs, les fabriques et relais synchrones,
les appelants async, les threads natifs, les arguments préparés et les branches
perdantes de Select sans obligation de join non résolue. Elle ne généralise pas
tous les graphes mixtes ni tous les retours de la structure capturée.

## Contre-exemples et corrections

- `validation/open-owned-borrowed-structure-capture.crust` était refusé à la
  signature de capture. Le backend accepte maintenant ces porteurs en utilisant
  la disposition Cell et le nettoyage existants, sans déplacer leur mémoire.
- La tâche concrète conserve les cibles et capacités des champs de l'objet
  transféré. Les parents d'emprunts sont transportés avec elles.
- Lever seulement la restriction de signature révélait une perte de prêt à
  travers une fabrique. `open-owned-borrowed-capture-factory-invalid.crust`
  était accepté aux deux étapes alors que number était détruit avant join.
  Cette acceptation est conservée dans
  `owned-borrowed-capture-factory-lifetime-counterexample.log`. Le programme
  invalide n'a pas été exécuté. Le résumé distingue maintenant les cibles des
  champs d'un paramètre transféré des références vers le porteur lui-même.
- Un relais de tâche déjà construite perdait également les dépendances des
  champs de sa capture propriétaire : `owned-borrowed-captures-task-relay-probe.log`.
  Les paramètres symboliques de tâche et de handle conservent maintenant ces
  captures, avec leur mode. Le vérificateur concret et les contraintes de
  sources les reconstituent aux appels.
- Le pont C pour les appels synchrones depuis async ne décrivait que les champs
  propriétaires A<T>. Il fournit maintenant aussi les cibles symboliques des
  champs empruntés Int. Il ne les prend pas en charge comme valeurs possédées.
- Les prêts des champs passent du porteur déplacé aux arguments préparés puis
  à la tâche enfant. Ils sont libérés après destruction/attente effective du
  porteur. Les métadonnées de l'ancien accès ne doivent pas continuer à réserver
  la cible après cette attente.
- Les effets suspendus d'un porteur transféré ne sont pas des écritures dans
  un porteur externe emprunté. Le résumé de suspension distingue les deux,
  ce qui permet le nettoyage d'une branche perdante possédant le porteur.
- L'en-tête d'un thread natif transfère une valeur existante ; il n'impose pas
  implicitement A<T> à une structure locale. Le stockage concret reste déduit
  à l'appel, avec les vérifications de source.

## Tests et preuves exécutées

`tests/test_async_owned_borrowed_captures.py` contient 11 méthodes.
`validation/count_owned_borrowed_captures.py` compte les exécutions effectivement
atteintes sans modifier les oracles.

Le passage final O0 (`owned-borrowed-captures-complete-o0.log`) réussit en
10,653 s : 19 exécutions natives, 24 programmes invalides, chacun vérifié aux
deux étapes, soit 48 vérifications de refus. La base O2 finale passe ces onze
méthodes en 11,314 s.

Les cas admis vérifient les valeurs et les destructions uniques du porteur et
de sa cible. Les refus portent sur drop prématuré, accès incompatible avec un
champ mutable, source ou cible trop courte, usage d'une cible pendant un
argument préparé, et destruction de la cible avant une branche perdante.
Un résultat partagé détaché est utilisé après destruction du porteur ; sa
cible reste protégée après join.

Le modèle indépendant croise pool du porteur extérieur/intérieur et cible
extérieure/intérieure. La tâche quitte le bloc. Seul le couple extérieur /
extérieur est admis. Chaque disposition est testée par appel direct et par
fabrique : deux exécutions admises et six refus, inclus dans les comptes.

Le harnais natif emploie Clang C11, pthread, Wall/Wextra/Werror,
Wno-unused-function, UBSan fatal, à O0/O2. Les échecs du scheduler et de
pthread_create sont injectés séparément. Aucun résultat ASan/TSan ni preuve
générale de sûreté n'est revendiqué.

`owned-borrowed-captures-regression-o2.log` : 155 méthodes passent en
146,629 s avec CRUST_TEST_OPT=-O2 et CRUST_SANITIZE=undefined. Modules :
async_owned_struct_captures, async_borrowed_struct_pools,
async_borrowed_local_results, local_result_envelopes, async_local_captures,
async_structure_effects, select_source, suspended_cleanup, native_blocks,
storage_requirements. Le compilateur est inchangé depuis ce lancement ; le
dernier ajout de test sur la référence détachée a été exécuté séparément dans
les suites ciblées finales.

## Mutations et essais intermédiaires

`tests/run_owned_borrowed_capture_mutations.py` injecte huit fautes dans des
copies temporaires du compilateur. Le journal final
`owned-borrowed-captures-complete-mutations-o2.log` les détecte toutes :
perte de cible concrète, perte de capacité mutable, perte du champ dans une
fabrique, perte dans un paramètre de tâche, perte des prêts d'un enfant,
perte des cibles du pont C, fuite du porteur inactif et exigence de pool
erronée dans un thread natif. Ce sont des fautes ciblées, pas un taux de
détection global.

Les essais intermédiaires sont conservés sous validation/ :

- `owned-borrowed-structure-capture-baseline.log`, puis `...-direct.log`.
- La première sonde de fabrique utilisait une annotation Task<read> non reconnue ;
  la sonde corrigée emploie le type nominal read. Un premier refus dû au double
  drop a été minimisé avant d'identifier l'acceptation incorrecte ci-dessus.
- `owned-borrowed-capture-factory-contract.log` conserve une erreur interne
  intermédiaire : confusion entre le type ciblé et le mode d'un champ. Le
  journal `...-contract-fixed.log` montre la correction et le contrat publié.
- `owned-borrowed-captures-initial-o0.log` et `...-relays-o0.log` conservent les
  défauts de relais et de pont ; `...-bridge-o0.log` passe les quatre méthodes.
- `...-expanded-o0.log` conserve les refus natif et Select corrigés ;
  `...-contracts-o0.log` passe dix méthodes.
- `...-mutations-o2.log` détecte deux fautes puis s'arrête sur un point
  d'injection ambigu. L'ancre est rendue spécifique au champ propriétaire ;
  `...-mutations-final-o2.log` détecte les huit fautes avec dix méthodes.
- L'argument invalide préparé a ensuite été rendu explicitement transférant
  avec `n ->;`, pour vérifier le conflit de prêt plutôt qu'un refus de scope.
  Les suites finales gardent cette version.

Tous les processus finaux cités sont terminés. Les diffs depuis
`/tmp/crust-before-owned-borrowed-captures` sont conservés sous validation/.

## Écarts ouverts et prochain lot

Deux programmes valides restent refusés et sont conservés :

- `open-owned-borrowed-capture-result-owner.crust` : retourner la structure
  capturée entière. Le contrat de cible du résultat doit projeter ses champs
  depuis la capture propriétaire ; il ne doit pas demander un paramètre &Int
  supplémentaire.
- `open-owned-borrowed-mixed-task-relay.crust` : relayer une tâche dont le
  porteur possède à la fois un champ partagé et un champ mutable. Le résumé
  regroupe actuellement les capacités par paramètre de capture et devient
  trop exclusif pour la cible du champ partagé. Le cas direct sans ce relais
  de tâche est couvert et admis. Il faut conserver la distinction par champ.

Leurs journaux sont `owned-borrowed-captures-remaining-results.log` et
`owned-borrowed-captures-mixed-task-relay-probe.log`. Les graphes contenant
simultanément des champs A<T> et des références, les projections récursives
générales et les autres lots de l'objectif global restent également ouverts.
La sonde de lecture partagée dérivée d'un parent mutable est conservée comme
observation, sans lui attribuer une violation normative ni durcir une règle.
Le lot est validé dans son périmètre décrit ; l'implémentation globale des
règles n'est pas déclarée complète.


Suite : les deux premiers programmes ouverts sont maintenant admis et testés
dans [le cycle des contrats par champ](ASYNC_CAPTURE_FIELD_CONTRACTS_CYCLE.md).
Les constats ci-dessus décrivent l'état antérieur ; les graphes généraux restent
ouverts. Le nouveau cycle conserve un autre contre-exemple de fabrique.
