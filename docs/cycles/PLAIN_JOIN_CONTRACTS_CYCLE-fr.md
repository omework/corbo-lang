[English](PLAIN_JOIN_CONTRACTS_CYCLE.md)

# Cycle RT5/RT6 — Contrats de résultats sans emprunt

## Règles appliquées et portée

Ce lot applique RT5/RT6, AS2/AS8, V3/V4 et U1, sans changement normatif.
Les types `Result<Int,runtime::Error>`, `Result<Bool,runtime::Error>`,
`Result<u8,runtime::Error>`, `Result<char,runtime::Error>`,
`Result<(),runtime::Error>` et `Result<runtime::Error,runtime::Error>` sont
reconnus dans les paramètres, retours et annotations synchrones. Ils peuvent
être copiés, réaffectés, rendus par if/loop, traités ou consommés explicitement.

Ces mêmes valeurs peuvent être capturées par une tâche et conservées pendant
une suspension. Le résultat simple d’un handle.await peut être annoté ; ses
copies, son passage à une tâche enfant, sa réaffectation et sa destruction sont
vérifiés. Cette prise en charge ne comprend pas encore le retour d’un Result
entier depuis une fonction async : voir l’écart reproduit plus bas.

Le type complet du résultat est conservé dans les analyses d’effets, de
provenances et de contraintes. Les types contenant un emprunt ou une allocation
ne sont pas convertis en ces modes sans dépendance. Les signatures propriétaires
existantes et leur suivi de sources restent séparés.

La représentation C utilise `CrustJoinResult`, maintenant déclaré dans les
types communs. Une signature peut ainsi être vérifiée sans instance active de
runtime. Le statut et la charge utile sont copiés ensemble, sans nouvelle
allocation. Cette représentation n’est pas une promesse d’optimisation de taille.

## Contre-exemples et corrections

- Le programme `validation/open-runtime-result-contract.crust` était refusé à
  la déclaration de wait. Il est maintenant compilé et exécuté : sortie 7.
  L’ancien diagnostic est conservé dans le fichier .log associé.
- Le parseur traitait `Result<...>=...` comme un token de comparaison. Une
  fermeture de type découpe maintenant ce token en `>` puis `=` et conserve
  les deux tokens pour les retours arrière du parseur. `2>=1` demeure une
  comparaison. Les versions avec et sans espace produisent le même résultat.
- Un résultat faillible issu d’une boucle async pouvait être ignoré. U1 est
  maintenant vérifiée sur cette voie, y compris pour les familles de résultats
  déjà connues.
- Les valeurs locales sans entrée de destruction pouvaient conserver leur
  marque de drop au-delà du bloc. Le nettoyage retire désormais cette marque
  pour les liaisons du bloc quitté, sans réactiver une liaison extérieure.
  Une copie de Result détruite dans un bloc puis un Int portant le même nom
  sont exercés après suspension.
- Les analyses auxiliaires décrivaient certains joins par le type de leur
  charge utile, voire par un type inconnu. Elles utilisent maintenant le même
  type Result complet pour les six cas et extraient le bon type dans Ok/Err.

Deux anciens tests (`test_constraints` et `test_effects`) ont également été
migrés vers U1 : lecture de `old`/`a` avant reset. Les assertions sur les sources
concernées, les destructions uniques et les conflits d’emprunt sont conservées.
Le profil historique de reset reste explicite ; aucune API publique reset
n’est réintroduite.

## Vérifications et oracles

Les 11 méthodes de `test_plain_join_contracts.py` couvrent 32 exécutions natives
et 38 programmes refusés. Les 24 configurations centrales suivent une table
indépendante : six charges utiles × succès/refus de lancement × relais
synchrone/capture async. Les sorties attendues sont fixées par cette table,
sans déduire les valeurs du C généré. Les cas complètent cette table par les
branches, boucles, annotations, copies, drop, réutilisation de nom et une
comparaison `>=`.

Le refus de lancement est injecté dans le seul callback bloquant. Le parent
et le consommateur peuvent toujours démarrer. L’erreur doit traverser les mêmes
contrats que le succès. Une capture copiée reste utilisable après drop de la
liaison source ; une liaison détruite n’est plus lisible. La vérification
n’accepte ni un résultat d’un autre type ni son utilisation comme entier ou
référence vers un entier.

Les six voisins avec charges empruntées/propriétaires sont refusés : les appels
au contrat simple sont rejetés pour type incompatible ; les annotations sur
ces joins sont rejetées par leur restriction de liaison existante. Ces tests
ne prouvent donc pas la prise en charge générale des signatures empruntées.

Clang Homebrew 20.1.3, arm64 macOS, C11, UBSan fatal pour les programmes natifs
indiqués. Les oracles de tâches activent pthread et les avertissements stricts.
Les anciens helpers d’effets/contraintes utilisent leur optimisation par défaut,
même quand CRUST_TEST_OPT vaut O2 ; CRUST_SANITIZE=undefined active leur UBSan.

| Exécution | Résultat | Trace |
| --- | --- | --- |
| Nouveau lot final à O0 | 11 méthodes réussies, 12,959 s | validation/plain-join-contracts-O0-current.log |
| Nouveau lot O2, runtime::Error, contraintes et effets | 67 méthodes réussies, 30,243 s | validation/plain-join-contracts-validated.log |
| Frontière entre résultats simples, empruntés et propriétaires | 1 méthode, 6 refus attendus | validation/plain-join-contracts-borrow-boundary-final.log |
| Lots capacités et features async avec les 9 premières méthodes du lot | 23 méthodes réussies, 28,777 s | validation/plain-join-contracts-O2.log |
| runtime::Error, spawn_blocking et obligations de handles | 24 méthodes réussies, 25,069 s | validation/plain-join-contracts-regression.log |
| Anciens résultats typés, attentes calculées et ABI | 15 méthodes réussies, 28,690 s | validation/plain-join-contracts-typed-regression.log |
| Contrats async, résultats propriétaires et scheduler après harmonisation des analyses | 14 méthodes réussies, 40,153 s | validation/plain-join-contracts-runtime-final.log |
| Mutations ciblées | 4 détectées | validation/plain-join-contracts-mutations-final.log |
| Mutations du cycle runtime::Error rejouées | 4 détectées | validation/plain-join-error-mutations.log |

Les dix premières méthodes sont incluses dans le groupe final de 67 ; la
onzième, qui ne produit que six refus, a été exécutée séparément puis dans le
lot O0 complet. Les logs initiaux conservent les échecs : erreur de tokenisation,
absence de vérification U1 sur la boucle et tests historiques non migrés.
Les ajustements d’expressions régulières de diagnostics n’ont pas remplacé un
refus attendu par une acceptation.

Les quatre mutations sont appliquées dans des copies temporaires : supprimer
la vérification du type de charge utile à un appel synchrone ; la supprimer
à une capture async ; remplacer le statut d’erreur reçu par un succès ; omettre
l’usage obligatoire du résultat de boucle. Elles sont toutes détectées. Aucun
taux global de détection ni preuve de sûreté n’en est déduit.

## Limites et prochain lot

Écart relevé à la clôture de ce cycle, corrigé depuis dans
[NESTED_PLAIN_RESULTS_CYCLE.md](NESTED_PLAIN_RESULTS_CYCLE.md) :
le retour `async fn wait() -> Result<Int,runtime::Error>` était refusé. Le
programme minimal `validation/open-async-plain-result-return.crust` et son
.log montrent cet écart : son join devrait produire un résultat imbriqué et
préserver la distinction entre erreur métier et erreur de lancement.

Restent aussi les signatures générales avec emprunts, conteneurs et
imbrications plus larges, runtime::Handle<T>, les constructeurs généraux de
Result et les autres chantiers ouverts du runtime. Le lot ne valide pas
l’équité, les réveils, Select, les threads natifs explicites ni les mutex.
Les constructeurs de mutex et la frontière C restent reportés selon les
consignes normatives. Il n’y a ici ni preuve formelle ni campagne ASan/TSan.

La validation a ciblé les interactions affectées et les suites listées,
pas l’ensemble monolithique du dépôt. L’objectif des sept brouillons demeure
actif et incomplet.

Commandes principales :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_plain_join_contracts -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_plain_join_contracts test_runtime_error_values test_constraints test_effects -v
python3 tests/run_plain_join_regression.py
python3 tests/run_spawn_blocking_regression.py
python3 tests/run_plain_join_mutations.py
python3 tests/run_runtime_error_mutations.py
```
