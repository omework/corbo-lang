[English](BUSINESS_RESULT_ENVELOPES_CYCLE.md)

# Cycle RT5/RT6 — Enveloppes des résultats métier

## Règles et portée

Application de AS2/AS4/AS12, RT5/RT6, U1 et des règles existantes de conversion
V3 et de chaînes UTF-8. Aucune règle normative n’est modifiée. Les consignes
AGENTS.md, VALIDATION_GUIDELINES.md, l’index design-buffer et les clauses
pertinentes ont été relus. La lecture normative complète et les interactions
du système sont poursuivies depuis les cycles précédents, sans inférer la
sémantique du seul compilateur.

L’écart `validation/open-async-business-result-envelope.crust` est corrigé :
une fonction async peut maintenant recevoir et retourner l’enveloppe du join
d’une tâche retournant `Result<u8,IntegerConversionError>`. Son ancien log
reste historique ; le programme est exécuté dans le nouveau module.

Le même raccordement couvre les six familles déjà existantes sans emprunt :
`Result<u8,IntegerConversionError>`, `Result<char,CharAtError>`,
`Result<char,CharFromStrError>`, `Option<char>`, `Result<u8,ByteReplaceError>`
et `Result<(),ByteReplaceError>`. Le join ajoute `runtime::Error` et chaque
attente suivante peut ajouter une nouvelle enveloppe, sans confondre l’erreur
métier avec l’échec de lancement.

## Implémentation et défauts corrigés

Les enveloppes utilisent les représentations C déjà définies pour ces valeurs.
Le registre de types fait correspondre signature explicite et type inféré du
join. Le premier niveau garde son champ de charge dédié ; les suivants
utilisent la représentation structurelle du cycle précédent. Les annotations,
contrats synchrones, captures, retours async, réaffectations, copies, branches,
boucles et drop gardent le type complet. Les résultats contenant une vue,
notamment `Result<&str,SliceError>`, sont exclus du registre sans emprunt ; leur
suivi de provenance existant reste nécessaire.

Deux défauts supplémentaires ont été reproduits puis corrigés :

- Un `Ok(inner)` extrait d’un join async pouvait lier un résultat métier faillible
  sans aucun usage. U1 est maintenant appliquée à cette extraction, comme aux
  autres liaisons faillibles. Le voisin avec `drop(->inner)` reste accepté.
- La création d’une tâche depuis du code synchrone ne contrôlait pas le type
  complet de certaines captures de résultats et de `runtime::Error`. Une
  représentation C commune ne suffit pas à prouver leur compatibilité. Le
  contrôle exige maintenant le mode Crust exact. Cela refuse notamment de
  capturer un résultat de slice emprunté dans un paramètre déclaré comme
  résultat de conversion entière sans emprunt.

Ce deuxième défaut a été découvert en corrigeant le test lui-même : sa première
version utilisait `try_slice(0,1)` et obtenait une erreur de syntaxe. Le vrai
appel est `try_slice(0..1)`. Avec cette syntaxe, le programme incompatible était
accepté, comme le montre `validation/business-envelope-borrow-boundary.log`.
Le test final exécute d’abord un voisin valide affichant la slice, puis exige
le diagnostic de type approprié pour la capture incompatible. L’ancien refus
syntaxique n’est pas compté comme preuve de contrôle de provenance.

## Modèle, programmes et interactions

Une table indépendante du compilateur fixe les résultats de six opérations :
conversion 255/256, lecture au début/au milieu d’un caractère multioctet,
conversion d’un texte à un/deux caractères, pop d’une chaîne pleine/vide,
remplacement d’octet et remplacement de plage à un indice valide/hors limites.
Elle ne lit aucune décision interne ni aucun champ du C généré.

Le générateur combine ces deux issues avec une ou trois enveloppes et une
observation synchrone ou après copie/capture/suspension dans une autre tâche :
48 configurations natives. Six autres configurations refusent le lancement à
chacun des trois niveaux, avec les deux modes d’observation. L’erreur doit se
trouver exactement au niveau refusé ; le calcul métier ne s’exécute pas lorsque
son lancement échoue. Les valeurs calculées depuis une String sont utilisées
après le drop de cette source.

Les voisins supplémentaires couvrent contrats, retour direct d’attente,
if/loop, annotation, réaffectation, usage après drop et résultats inutilisés.
Huit charges incompatibles et deux mauvaises valeurs `runtime::Error` doivent
être refusées à la capture. Le module final compte **7 méthodes, 58 exécutions
natives et 16 refus attendus** par niveau d’optimisation. Les régressions et
mutations sont comptées séparément.

## Mutations et correction de la couverture

Les mutants sont exécutés dans des copies temporaires :

1. Omission du contrôle de type lors d’une création sync de tâche.
2. Omission de l’usage obligatoire du résultat métier extrait.
3. Effacement du statut métier à l’extraction dans une tâche async.
4. Effacement du statut métier au retour du join synchrone direct.

La première campagne détecte les trois premiers mais le quatrième survit
(`validation/business-envelope-mutations.log`). Les chaînes à trois niveaux
n’exerçaient pas ce chemin : le premier join était effectué en async.
La matrice est donc élargie à une seule enveloppe, sans modification de
l’implémentation ou des attentes. Les quatre mutants sont alors détectés
par des assertions de comportement ou d’acceptation
(`validation/business-envelope-mutations-final.log`). La corruption du statut
métier produit notamment `0` au lieu du diagnostic attendu `90`.

Cette campagne ne donne pas un taux de détection global et ne constitue pas
une preuve de sûreté.

## Preuves d’exécution

Clang Homebrew 20.1.3, arm64 macOS, C11 et pthread. Les nouveaux programmes
natifs utilisent UBSan fatal (`-fsanitize=undefined -fno-sanitize-recover=all`)
à O0/O2. Les oracles C de runtime ajoutent les avertissements stricts.
Les anciens helpers contraintes/effets utilisent leur optimisation propre ;
CRUST_SANITIZE active UBSan, mais CRUST_TEST_OPT ne prouve pas qu’ils utilisent O2.

| Vérification terminée | Résultat | Trace |
| --- | --- | --- |
| Nouveau module élargi O0 | 7 méthodes réussies, 50,186 s | validation/business-envelope-O0-expanded.log |
| Nouveau module élargi O2 | 7 méthodes réussies, 31,240 s | validation/business-envelope-O2-expanded.log |
| Module avant élargissement, résultats imbriqués, contrats simples, runtime::Error, contraintes et effets | 86 méthodes réussies, 112,195 s | validation/business-envelope-O2-regression.log |
| Capture incompatible de slice et dix autres types | 2 méthodes réussies | validation/business-envelope-capture-types.log |
| Première régression des opérations UTF-8, avant renforcement du contrôle de capture sync | 15 méthodes réussies, 33,318 s | validation/business-envelope-typed-regression.log |
| Régression UTF-8 finale après toutes les corrections | 15 méthodes réussies, 37,170 s | validation/business-envelope-typed-regression-final.log |
| ABI des tâches, Bool/tableaux, emprunts et attentes calculées | 15 méthodes réussies, 23,517 s | validation/business-envelope-abi-regression.log |
| Campagne finale de mutation | 4 détectées | validation/business-envelope-mutations-final.log |

Le premier log `business-envelope-initial.log` conserve l’acceptation fautive
d’un résultat extrait inutilisé. Le log `business-envelope-O0.log` précède
la correction du test de slice et ne valide pas cette frontière. Les deux
exécutions élargies finales incorporent toutes les corrections et les tests
sur les bons diagnostics. La compilation Python des modules modifiés et des
scripts a réussi.

## Limites et suite

Ce cycle ne rend pas génériques tous les Result<T,E> : les autres charges de
vecteurs, les conteneurs, les propriétaires et les emprunts généraux restent à
compléter. Un écart suivant est matérialisé dans
`validation/open-async-vector-value-result.crust` et son log :
`Result<(),u8>` existe et son relais synchrone s’exécute, mais sa capture/son
retour async étaient encore refusés à la clôture de ce cycle. Ce défaut est
corrigé dans [ASYNC_VECTOR_RESULTS_CYCLE.md](ASYNC_VECTOR_RESULTS_CYCLE.md). Le contrôle synchrone affiche `1` sous
UBSan. Ce programme async est un cas valide restant à implémenter, pas un
exemple de programme invalide.

Les obligations restantes des sept brouillons sont conservées : API
runtime::Handle<T>, scheduler public, réveils/équité, runtime::thread, Select,
gardes et autres écarts de stockage déjà consignés. La frontière C, les traits
à plusieurs méthodes et les constructeurs de mutex restent reportés selon
les décisions de design. Il n’y a ici ni preuve formelle, ni campagne ASan/TSan,
ni exécution de toute la suite monolithique du projet.

Commandes :

```sh
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_business_result_envelopes -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 PYTHONPATH=.:tests python3 -m unittest test_business_result_envelopes test_nested_plain_results test_plain_join_contracts test_runtime_error_values test_constraints test_effects -v
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_business_envelope_regression.py
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_plain_join_regression.py
CRUST_SANITIZE=undefined CRUST_TEST_OPT=-O2 python3 tests/run_business_envelope_mutations.py
```
