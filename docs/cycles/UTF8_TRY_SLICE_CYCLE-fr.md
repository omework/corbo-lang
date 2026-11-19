[English](UTF8_TRY_SLICE_CYCLE.md)

# Cycle — découpes UTF-8 faillibles (brouillon 07)

## Décision et périmètre

TX4 et E2 intègrent la décision validée : les crochets refusent une invalidité
statiquement établie, sinon arrêtent avec diagnostic après contrôle dynamique.
`try_slice` retourne une erreur récupérable et conserve l'emprunt de la source.
Le prototype nomme le type `Result<&str,SliceError>` ; OutOfBounds et
NotCharBoundary sont les variantes prescrites par le brouillon.

La première étape ci-dessous raccorde le chemin synchrone, ses contrats, résultats de fonctions,
provenances multiples et destruction explicite. Elle ne clôt pas le lot 07 :
la conservation de ce Result dans un état async et son transport par await/join
restaient à implémenter avant la deuxième étape décrite plus bas. Deux programmes exploratoires confirment un diagnostic
« résultat ... requis » ou « expression utf8_try_slice non prise en charge »
sur ces formes ; aucune acceptation async n'est revendiquée.

## Implémentation et invariants examinés

- Les quatre formes de plage sont analysées directement. Le receveur puis les
  bornes sont évalués une fois, de gauche à droite. Le receveur reste emprunté
  pendant leurs effets et leur résultat est figé avant l'opération.
- La validité de toute la plage précède le contrôle des frontières UTF-8 :
  une borne hors limites l'emporte sur une autre coupant un caractère.
- La vue réutilise les octets existants et leur direction de stockage. Le
  Result inline ne consomme pas de slot de pool.
- Le contrat transmet les dépendances du texte, sans transformer les indices
  en provenances. Deux origines conditionnelles restent réservées à l'appelant.
- La liaison relève d'U1. Sa destruction termine l'emprunt ; une mutation,
  destruction ou réinitialisation prématurée reste refusée.
- Les motifs courts du brouillon, Err(OutOfBounds) et Err(NotCharBoundary),
  sont pris en charge pour les découpes et char_at. Les formes qualifiées
  restent contrôlées par type ; CharAtError ne traite pas un SliceError.

## Preuves exécutées

`PYTHONPATH=tests:. python3 -m unittest test_utf8_try_slice -v`, avec deux
configurations de compilation C : clang C11, O0 puis O2, UBSan et
`-fno-sanitize-recover=all`. Huit méthodes passent dans chaque configuration,
journal `/tmp/crust-try-slice-optimizations.log`.

Neuf programmes/harness admis et dix-huit programmes refusés sont exercés par
ces huit méthodes, à chaque configuration. Une neuvième méthode complémentaire
passe ensuite à O0 et O2 (`/tmp/crust-try-slice-result-alias.log`) : un programme
admis et trois refus vérifient les alias de Result, le retour du Result depuis
une fonction et le remplacement de sa provenance. Détruire une liaison ne
termine pas l'emprunt encore porté par sa copie. Le test d'oracle explore les 144 couples
de bornes de -1 à 10 sur « été🌍 ». Les frontières attendues sont calculées en
Python en encodant les préfixes de caractères, indépendamment du parcours des
octets dans le runtime. Les sous-chaînes attendues sont décodées par Python.

Les scénarios combinent deux relais de fonctions, boucles, résultats
conditionnels, deux sources String, croissance après dernier usage, drop et
réemploi des slots. Un reset historique est testé uniquement avec l'option de
compatibilité, sans réintroduire reset dans l'API publique. Le reset effectué
par une fonction appelée dans une borne est également refusé.

Un harness C vérifie explicitement les adresses, longueurs et directions des
vues pour des octets rangés dans chaque sens, une vue vide au bout du texte,
les extrêmes Int32 et un texte vide avec pointeur NULL. Il complète les
programmes Crust et ne démontre pas toute la politique de placement des régions.

Trois mutations ciblées dans des copies temporaires sont détectées :

1. Omission du contrôle des frontières : des octets UTF-8 invalides arrivent
   dans la sortie, dont le décodage Python échoue.
2. OutOfBounds remplacé par NotCharBoundary : divergence avec l'oracle.
3. Offset ascendant utilisé en stockage descendant : le harness échoue avec
   le code 80 sur l'identité de la vue.

Journal `/tmp/crust-try-slice-mutations.log`, copies
`/var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-try-slice-mutations.gdua_qtx`.
Ces trois fautes ne donnent aucun taux global de détection des mutations.

## Régression et limites

La régression sélectionnée de 124 méthodes (UTF-8, String, arithmétique,
comparaisons, court-circuit, async associé et conversions entières) passe en
125,542 secondes, journal `/tmp/crust-try-slice-regression.log`.

Les deux modèles indépendants préexistants de `test_utf8_runtime` passent
également à O0 et O2 en 1,684 seconde : positions de décodage et aller-retour
Unicode (graine 1439), validation exhaustive des 65536 paires d'octets et
échantillons supplémentaires (graine 2671), y compris le stockage descendant.
Journal `/tmp/crust-try-slice-runtime-regression.log`. La compilation Python
des modules modifiés et du nouveau fichier de tests réussit.

Les premiers essais ont relevé deux problèmes dans les nouveaux tests :
`SliceError>=` était tokenisé comme l'opérateur >=, et l'expression régulière
attendue pour le refus d'un reset ne reconnaissait pas le diagnostic précis
« retenue par un argument ». Espacement et attente du diagnostic ont été
corrigés ; les valeurs et décisions d'acceptation attendues sont conservées.

Aucune preuve générale de sûreté ni couverture exhaustive des chemins n'est
revendiquée. Pas de nouvelle exécution ASan dans ce cycle. Le contrôle de
validité statique des crochets conserve la portée de propagation existante ;
il ne revendique pas une évaluation constante de toute expression possible.


## Deuxième étape — état async et transport du résultat emprunté

Le Result de découpe dispose d'un champ inline dans l'état et dans le résultat
d'attente. Il appartient aussi aux modes qui portent un emprunt. Son transport
ne se réduit donc pas à la copie de ses bits : les analyses de contrat,
capture, attente, extraction et dernier usage conservent ses provenances.
Le type C `CrustTextResult` est partagé avec le runtime des tâches.

Les règles AS8, AS10, AS11 et AS12 s'appliquent sans prolongation implicite de
l'état. Une vue vers une String transférée à la tâche peut servir dans son
corps, mais ne peut sortir avec le Result si cette String est détruite à la
terminaison. Les cibles fournies par emprunt restent réservées après l'attente
jusqu'au dernier usage du résultat ou de ses vues extraites.

La préparation des bornes partage maintenant le chemin utilisé par les
crochets. Les temporaires du receveur et des indices persistent dans l'état
si une borne suspend. Les origines du résultat sont celles du texte, pas
celles des valeurs seulement lues pour calculer ses bornes.

### Exécutions ciblées

Les huit premières méthodes async et les neuf méthodes synchrones passent
ensemble à O0 et O2 sous UBSan bloquant : 17 méthodes par configuration,
7,592 et 8,942 secondes, `/tmp/crust-try-slice-async-optimizations.log`.
Les huit méthodes async couvrent douze exécutions admises et dix-huit refus.

Trois méthodes supplémentaires passent séparément aux deux optimisations :

- `/tmp/crust-try-slice-async-capture-loop.log` : capture d'un Result emprunté
  créé chez l'appelant, drop de la liaison d'origine, résultat de boucle et
  refus de mutation pendant l'usage du résultat (deux admis, un refus).
- `/tmp/crust-try-slice-computed-await-usage.log` : tâche choisie par if puis
  attendue ; usage explicite par drop admis, liaison inutilisée et `_` refusés
  (un admis, deux refus).
- `/tmp/crust-try-slice-bound-provenance.log` : libération de la réservation
  d'une capture utilisée seulement comme borne après join, en conservant
  celle des octets effectivement retournés (un admis, un refus).

Les interactions comprennent des bornes contenant await, yield avant et après
la construction, relais de fonctions async, Result capturé par une autre
tâche, attente d'un handle depuis une tâche, sources String locales à l'état
ou empruntées, deux sources conditionnelles, réaffectation de Result, alias,
réemploi de slot après destruction, et reset historique refusé avant le dernier
usage. Les valeurs et erreurs attendues sont fixées indépendamment de
l'implémentation ; l'oracle synchrone de plages est rejoué avec le runtime modifié.

### Contre-exemple corrigé

Un await sur une tâche choisie par if passait par un abaissement distinct qui
omettait U1 : `let ignored = (if ... { let t = cut(); <- t } else { ... }).await;`
était accepté sans usage du Result. Le chemin applique désormais la même
vérification d'usage que l'await ordinaire. Le programme avec drop explicite
reste admis. Les huit régressions existantes ciblant les attentes et résultats
calculés passent en 19,439 secondes (`/tmp/crust-computed-await-usage-regression.log`).

### Mutations

Trois mutations des règles de durée de vie sont détectées : suppression de
la vérification de source au retour, perte du descripteur d'emprunt après join,
et perte des prêts du Result local avant sa copie et sa capture. Chacune rend
au moins un programme interdit accepté, et le test négatif échoue.
Journal `/tmp/crust-try-slice-async-mutations.log`, copies
`/var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-try-slice-async-mutations.own_fw4z`.
Une quatrième mutation supprime le nouveau contrôle U1 dans l'await calculé ;
elle est détectée (`/tmp/crust-computed-await-usage-mutation.log`).
Aucun taux de détection global n'est déduit de ces quatre mutants ciblés.

### Régression et limites

La régression sélectionnée de 147 méthodes inclut les tranches, UTF-8, String,
les captures et retours async associés, les conversions entières et les deux
modèles indépendants du runtime UTF-8. Journal
`/tmp/crust-try-slice-async-regression.log` : **147 méthodes réussies en
154,153 secondes**.
Cette exécution a chargé le compilateur avant la correction locale U1 ; les
huit régressions d'attente calculée ci-dessus valident ensuite cette correction.
La compilation Python des modules modifiés réussit.

Ces exécutions ne prouvent pas la sûreté générale de l'async. Aucun stress
multithread supplémentaire ni TSAN/ASan n'est exécuté dans cette étape. Les
changements de scheduler, runtime::thread, runtime::Error, Select et mutex du
brouillon 04 restent un lot distinct à terminer. Les contrats génériques de
résultats imbriqués et tous les usages/motifs propriétaires du brouillon 01
ne sont pas déclarés intégralement couverts par ce cycle.
