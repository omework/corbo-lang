[English](STRICT_STRUCTURE_RETURNS_CYCLE.md)

# Cycle — Retours nominaux T et allocations A<T>

## Règles et périmètre

V1, T6, H1 et le brouillon 05 distinguent la valeur locale `T` de l'allocation
`A<T>`. Ce cycle applique cette distinction aux retours propriétaires de types
nominaux (structures/enums connus du compilateur). Il ne modifie aucune règle
normative. Les anciennes conventions des primitives, dont `-> <- Int`, ne sont
pas redéfinies ici.

Le cas consigné dans
`validation/open-plain-structure-return-from-handle-result.crust` renvoyait
une charge `A<Point>` issue d'un résultat de `Vector.replace` sous une signature
`Point`. Il est maintenant refusé par `verify_program` et `compile_source`.
Le diagnostic exécuté est conservé dans
`validation/strict-structure-returns-recorded.log`. Avec la signature
`A<Point>`, le même programme conserve les sorties `7, 9, 10, 11` et réutilise
ses slots. Le C est conservé dans
`validation/strict-structure-returns-exchange-point.c`.

## Implémentation

- L'analyse des exigences de stockage traite chaque retour nominal propriétaire,
  y compris les définitions non appelées et le retour final sans point-virgule. Une signature nue demande le stockage
  local ; `A<T>` demande un pool.
- Ces exigences sont propagées dans les contrats et relais existants. Les appels
  continuent de vérifier les contrats sans reparcourir le corps du callee.
- La vérification des retours avant émission C rejette aussi une provenance de
  pool sous une signature nominale locale.
- Une exigence de pool inférée sur un paramètre nominal renseigne le type de sa
  source symbolique. Sans cela, un helper de copie correctement déclaré
  `A<Point>` était refusé pendant la vérification de son corps.

La représentation C et le runtime ne changent pas. Aucune conversion du stockage,
aucune copie supplémentaire et aucune promotion implicite ne sont introduites.

## Tests ciblés et migrations

`tests/test_strict_structure_returns.py` ajoute six méthodes : neuf programmes
natifs admis et quatorze programmes invalides contrôlés aux deux entrées. Fabriques
locales/de pool, relais, emprunt avant/après transfert, branches, définition
inutilisée, retour async et join sont exercés. Les sorties et le réemploi après
destruction sont explicitement attendus.

Les tests historiques qui renvoyaient une allocation sous un type nominal nu
sont migrés vers `A<T>` pour conserver leur scénario. Les couples local/pool
utilisent des signatures distinctes. Les cas de copie interne à une tâche qui
renvoie un Int conservent les deux stockages sans helper à retour nominal
ambigu. Les assertions de résultat/destruction restent en place ; une assertion
de diagnostic peut être adaptée au contrôle désormais plus précoce. Les
fixtures historiques restent conservées ; les transformations des programmes
sont visibles dans les tests et les diffs archivés.

## Exécutions

- Premier passage O0 : 35 méthodes, 25,387 s, code 1 ; quatre échecs de scénarios
  historiques dont le helper promettait Point mais produisait une copie de pool.
  Log : `validation/strict-structure-returns-initial-o0.log`.
- Ciblé O0 après migration : 16 méthodes, 5,844 s, code 1 ; cinq échecs dus au type
  manquant de la source symbolique de la copie de pool. Log :
  `validation/strict-structure-returns-targeted-o0.log`.
- Ciblé O0 après correction : 16 méthodes, 7,983 s, code 0. Log :
  `validation/strict-structure-returns-targeted-second-o0.log`.
- Première régression O2 : 227 méthodes, 165,714 s, code 1 ; 225 réussissent.
  Un test attendait le label de copie du helper remplacé par une copie interne
  (`q` au lieu de `async copy`) ; le nombre attendu de destructions reste deux.
  Un autre utilisait encore le même retour nominal Point pour les deux stockages.
  Il possède maintenant deux helpers à signatures explicites, avec les mêmes
  sorties et la même coexistence de l'original et de la copie pendant l'évaluation.
  Log : `validation/strict-structure-returns-regression-o2.log`.
- Le retour final `<- valeur` avait encore besoin de propager la même exigence
  que le return explicite. Le cas valide initialement refusé est conservé dans
  `validation/strict-structure-returns-implicit-before.crust/.log` ; un test de
  relais et son pendant invalide sont ajoutés.
- Troisième passage ciblé : 41 méthodes, 20,631 s, code 1 (trois échecs et
  une erreur). Les 22 méthodes Foundation supplémentaires migrent des retours
  historiques de pools vers A<T>. Les quatre échecs sont reproduits, inchangés,
  dans la copie du compilateur et des tests prise avant ce lot : quatre méthodes,
  1,759 s, code 1. Logs `strict-structure-returns-targeted-third-o0.log` et
  `strict-structure-returns-foundation-baseline.log` sous validation/.
- Quatrième passage ciblé : 41 méthodes, 26,806 s, code 1 ; la correction de
  masquage et les trois scénarios historiques passent, hormis le nom attendu de
  la destruction du nouveau champ (`champ=8`, et non `item=8`). Cette assertion
  conserve le compte exact de un ; le label est corrigé.
  Log : `validation/strict-structure-returns-targeted-fourth-o0.log`.
- Ciblé final : 21 méthodes, 18,702 s, code 0. O0/UBSan pour les tests ciblés
  et de contrats, configuration native O2/UBSan historique pour les quatre
  méthodes Foundation. Log : `validation/strict-structure-returns-targeted-final-o0.log`.
- Complément après migration des signatures historiques Holder/Root/View dans
  les suites de restitution et réemprunts : 14 méthodes, 11,973 s, code 0,
  O2/UBSan. Log : `validation/strict-structure-returns-migrated-reborrows-o2.log`.
- Régression O2 étendue : 276 méthodes, 233,082 s, code 1 ; 270 réussissent,
  cinq échecs et une erreur proviennent des anciennes signatures dans les deux
  suites de restitution/réemprunts chargées avant leur migration. Le complément
  de 14 méthodes ci-dessus réexécute intégralement ces deux suites et clôt ces
  six échecs sur le même compilateur, sans changement de code entre les runs.
  Il ne s'agit pas d'une passe monolithique verte. Logs :
  `validation/strict-structure-returns-regression-final-o2.log` et
  `validation/strict-structure-returns-migrated-reborrows-o2.log`.
- La correspondance des six identifiants en échec avec les succès du complément,
  les 276 identifiants distincts couverts et les empreintes finales ont été
  contrôlés. Synthèse : `validation/strict-structure-returns-validation-summary.json`.
  Aucun échec non résolu ne reste dans cette sélection ; ce constat ne porte
  pas sur l'ensemble du dépôt.

Le harness passe par les deux entrées Crust puis compile le C avec pthread,
Wall/Wextra/Werror et UBSan fatal. Le niveau O0/O2 est transmis par
`CRUST_TEST_OPT`. Les tests Foundation sélectionnés utilisent leur
configuration native historique et le profil legacy-reset explicite.

## Écarts historiques directement rencontrés

Trois assertions étaient devenues obsolètes avec des extensions déjà consignées :

- La restitution après remplacement d'un champ propriétaire est autorisée
  ([cycle antérieur](RETURNED_OWNED_REPLACEMENT_CYCLE.md)). L'ancien refus est
  remplacé par une exécution qui contrôle l'identité de la racine, le résultat 8,
  la destruction de l'ancien et du nouveau champ et le réemploi des deux pools.
- Une référence partagée copiée depuis un champ conserve la cible, sans retenir
  le porteur ([cycle antérieur](ASYNC_DETACHED_FIELD_RETURNS_CYCLE.md)). Détruire
  l'ancien porteur ou reset son pool est donc accepté et exécuté ; détruire la
  cible ou reset son pool reste refusé. Le cas reset reste legacy uniquement.

Le quatrième échec est un défaut préexistant de contrat : une référence mutable
créée avant le masquage de la variable propriétaire mettait à jour le symbole
masquant au lieu de l'objet d'origine. L'analyse des résultats et celle des
contraintes retrouvent désormais le porteur masqué par son identité. Les deux
branches du test existant conservent leurs valeurs 1/3 et les deux cibles
potentielles restent protégées contre drop. L'invariant de couverture du contrat
n'est pas supprimé ni affaibli.

## Limites

Les modèles finis local/pool déjà présents sont conservés. Aucune nouvelle
campagne générative, mutation ou recherche adversariale approfondie n'est lancée.
Le retrait de reset du profil normal reste inchangé. Ce lot ne clôt ni les
charges de collections à dépendances imbriquées, ni les enveloppes async
non Int, ni le placement anticipé général ou l'intégration publique des mutex.
Les résultats ne constituent pas une preuve générale de sûreté ni une clôture
de l'objectif global.

## Artefacts et suite

La copie initiale est `/tmp/crust-before-strict-structure-returns` (modules Python
racine et tests). Les vingt diffs exacts sont archivés sous
`validation/strict-structure-returns-*.patch` ; le manifeste
`validation/strict-structure-returns-changes.json` contient les empreintes
avant/après. La sélection finale des tests est enregistrée dans
`validation/strict-structure-returns-final-test-selection.txt`.

Prochain écart concret : `validation/open-typed-async-vector-option.crust/.log`.
La signature async `Option<A<Point>>` est refusée explicitement aux deux entrées.
Le comportement synchrone correspondant est raccordé ; son intégration async
reste à réaliser, sans modifier les exigences de stockage validées ici.

Rejouer la sélection étendue sur l'état courant :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 - <<'PYTEST'
import unittest
from pathlib import Path
names = Path('validation/strict-structure-returns-final-test-selection.txt').read_text().splitlines()
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
raise SystemExit(not result.wasSuccessful())
PYTEST
```
