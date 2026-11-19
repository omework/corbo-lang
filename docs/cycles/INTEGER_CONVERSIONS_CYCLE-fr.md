[English](INTEGER_CONVERSIONS_CYCLE.md)

# Conversions entières — intégration du brouillon 07

## Règles et portée

F5 et I5 consignent la décision validée : `as` préserve toutes les valeurs du
type source ; une conversion susceptible d’échouer passe par `try_from`.
La première étape a implémenté `as` pour les types entiers actuellement
pris en charge, Int32 (`Int`) et `u8`, ainsi que l’initialisation explicitement
typée d’un littéral `u8`. La deuxième étape ci-dessous ajoute `u8::try_from`
et le contrôle d’usage des résultats faillibles inline pris en charge.

Le contrôle s’appuie sur les intervalles des types, sans exception pour une
constante. Le C synchrone évalue l’opérande une fois dans un temporaire du type
destination. Le chemin async applique le même contrôle et conserve la valeur
dans son état quand elle traverse une suspension. Les analyses de résultats,
de contraintes et d’effets traversent l’opérande pour conserver ses usages et
ses effets mémoire. Un cast ne déréférence pas implicitement une allocation.

## Preuves exécutées

`tests/test_integer_conversions.py` ajoute cinq méthodes. Quatre programmes
admis sont compilés et exécutés à O0 puis O2 avec C11, UBSan et
`-fno-sanitize-recover=all`. Les cinq méthodes passent aux deux niveaux :
`/tmp/crust-integer-casts.log`.

- Une liste Python indépendante donne les 256 valeurs attendues pour toutes
  les valeurs de u8 élargies à Int. Les deux extrêmes Int32 restent inchangés.
  Les conversions identitaires, la priorité sur la multiplication et
  l’initialisation des littéraux typés sont exercées.
- Deux appels produisent des effets observables dans l’ordre 1 puis 2, une
  seule fois chacun, avant la somme 510. Le pool est ensuite nettoyé.
- La lecture convertie peut survivre au drop de l’allocation d’origine et
  au réemploi de son slot. Convertir à partir d’un emprunt encore utilisé
  après drop ou reset est refusé. Convertir une variable déjà dropped est
  également refusé. Reset est exercé uniquement dans le profil historique.
- Une tâche capture un u8, crée un autre u8, suspend son exécution puis rend
  la somme élargie 297. La capture et le résultat passent par spawn/join.

Après renforcement des cas négatifs, quinze programmes refusés sont couverts :
onze formes de conversion/initialisation invalides, trois usages après
destruction et une conversion réductrice en async. Le test des onze formes
a été rejoué séparément : `/tmp/crust-integer-casts-refusals.log`.

## Mutations

Deux mutations temporaires sont détectées :

1. Retirer le contrôle d’inclusion des intervalles fait accepter trois
   conversions Int vers u8 interdites, y compris les constantes 0 et 42.
   Les programmes négatifs utilisent le résultat comme u8 avant de l’élargir
   pour l’afficher, afin qu’un refus indépendant de print ne masque pas le
   défaut. `/tmp/crust-integer-narrowing-mutation-final.log`.
2. Passer par int8_t dans le C généré corrompt la valeur 128, première
   divergence avec l’énumération indépendante des 256 valeurs.
   `/tmp/crust-integer-casts-mutations.log`.

Copies temporaires :
`/var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-cast-mutations.be40pzxx`.
Ces deux mutants ciblés ne donnent aucun taux de détection général.

## Régression et limites

Les régressions d’arithmétique, court-circuit, comparaisons, octets async,
arguments, tableaux fixes et mutabilité se terminent avec **129 tests réussis**
en 62,011 secondes. Journal `/tmp/crust-integer-casts-regression.log`.
La compilation Python des six modules modifiés réussit également.

Un premier scénario d’ordre utilisait `.set` avec une expression arithmétique,
forme non prise en charge par cette API existante. Il a été remplacé par deux
appels distincts écrivant des constantes ; l’ordre et l’unicité des effets
restent observables, sans étendre cette API dans le chantier des conversions.

Les preuves portent sur Int et u8. Elles ne couvrent pas d’autres largeurs
entières ni une nouvelle ABI. Le modèle des types d’entiers est simple et
partagé entre les chemins de compilation ; l’oracle des valeurs attendues
ne l’importe pas. Aucune preuve générale de sûreté n’est revendiquée.

## Deuxième étape — try_from, usage explicite et drop d’expression

`u8::try_from(value)` évalue une fois un Int ou un u8 et rend
`Result<u8,IntegerConversionError>`. La variante d’erreur du prototype est
`IntegerConversionError::OutOfRange`. Le contrôle précède le cast C ; aucune
allocation de pool n’est nécessaire pour le résultat. Les contrats transmettent
ce type et le backend async peut le capturer, le conserver pendant yield,
le retourner par await et le transporter dans le résultat de join.

U1/L6 intègrent la décision du brouillon 07. Une liaison de résultat faillible
inline doit être utilisée, même pour une variante établie statiquement. Le nom
`_` ne permet pas de contourner cette règle. Un usage conditionnel suffit.
La réaffectation seule ne compte pas comme usage de l’ancienne valeur.
`drop(-> expression)` abaisse l’évaluation dans une liaison interne puis
consomme ce résultat avant l’instruction suivante. La même forme s’applique
aux opérations propriétaires déjà prises en charge ; leur couverture complète
selon le brouillon 01 reste à achever.

Un contre-exemple a révélé une erreur de dispatch : un bras `Err(_)` écrit
avant `Ok` comparait le statut au seul code 5. Une erreur d’un autre code
pouvait atteindre le bras Ok et déclencher une extraction invalide. La lecture
du discriminant générique normalise désormais tout statut non nul comme Err,
en synchrone et async ; les motifs d’erreur précis gardent leur discriminant.

### Preuves ciblées

Les onze méthodes de `test_integer_conversions.py` passent à O0 et O2 sous
UBSan bloquant. Journal `/tmp/crust-try-from-final-tests.log`.

- Un oracle Python indépendant classe les 260 entrées de -2 à 257 et les deux
  extrêmes Int32. Deux fonctions relaient le Result ; Err(_) figure avant Ok.
  Les variantes nommées d’erreur sont également exercées.
- Les évaluations de deux expressions consommées par drop ont des effets
  observables une seule fois, avant les instructions suivantes. Un résultat
  nommé peut être consommé et son second drop est refusé.
- Le résultat ne garde aucun emprunt de l’entier copié : il reste utilisable
  après drop, réemploi ou reset historique du pool d’origine. La conversion
  depuis un emprunt devenu invalide est refusée.
- Les usages conditionnels et la transmission à une fonction sont admis.
  Treize formes négatives couvrent l’abandon, `_`, le nom `_unused`, la double
  consommation, l’absence de flèche, les types/aritès incorrects, l’écrasement
  d’un résultat inutilisé et deux familles UTF-8 existantes.
- Le chemin async suspend avant et après le retour du Result. Le join d’une
  autre tâche rend le Result entier, déballé par deux matchs successifs.
  Une liaison async inutilisée, une première valeur écrasée sans usage et un
  retour après drop sont refusés.
- Le drop d’un résultat de validation UTF-8 termine son emprunt ; le tableau
  d’octets peut ensuite être modifié.

Trois mutants temporaires sont détectés à O2 : suppression des bornes,
suppression du contrôle d’usage (six refus deviennent acceptés), et retour
du code d’erreur brut au lieu de la normalisation Err(_). Journaux
`/tmp/crust-try-from-mutations.log`, copies dans
`/var/folders/rs/ld5jvh_n6t92p1hhs2qrmt7w0000gn/T/crust-try-from-mutations.z0aouxqx`.

### Migration des tests existants

La première régression de 155 tests a terminé avec trois méthodes concernées
par la nouvelle règle d’usage (trois erreurs et deux échecs de sous-cas),
journal `/tmp/crust-fallible-results-regression.log`. Les programmes qui
écrasaient ou abandonnaient un Result ont reçu un match sans sortie ou un drop
explicite. Les essais de type incorrect consomment désormais le résultat
précédent afin que son abandon ne masque pas l’erreur de type visée.
Les valeurs, traces et invariants mémoire attendus n’ont pas été modifiés.
Les trois méthodes migrées passent, journaux
`/tmp/crust-fallible-migrated-tests.log` et `/tmp/crust-fallible-bytes-migrated.log`.

La seconde régression de 155 tests termine en 183,441 secondes avec une erreur :
le scénario nommé char_at écrasait encore son premier Result sans usage.
Un match explicite avant l'écrasement conserve l'objet du test ; cette méthode
rejouée passe en 2,214 secondes (`/tmp/crust-fallible-char-migrated.log`).
Le journal global conserve l'échec : `/tmp/crust-fallible-results-final-regression.log`.
Il ne constitue donc pas une exécution globale intégralement verte.

Un autre contre-exemple concernait la priorité unaire : `-byte as Int` était
interprété comme `-(byte as Int)`. L'opérateur unaire lie désormais son opérande
avant `as` ; la négation u8 est refusée, et `-(byte as Int)` est admis. Les deux
méthodes ciblées passent à O0 et O2 (`/tmp/crust-integer-cast-precedence.log`).

### Résultat propriétaire consommé par drop

L’exemple du brouillon 01 avec `drop(-> valeurs.replace(index, -> entrant))`
est également raccordé au résultat propriétaire existant de replace. Deux
exécutions, index valide puis invalide, vérifient que le slot rendu contient
respectivement l’ancien objet et l’entrant rejeté. L’allocation suivante dans
le pool de capacité deux réutilise exactement ce slot ; le vecteur conserve
respectivement 9 et 7. Les deux premières destructions sont comparées à la
trace attendue. Un troisième programme consomme directement `pool.new(7)`
puis réutilise le pool de capacité un.

Ces trois programmes passent à O0 et O2 sous UBSan bloquant, journal
`/tmp/crust-drop-expression-owned-tests.log`. Le test a aussi révélé un défaut
du C généré : le nom interne du receveur temporaire contenait un caractère
NUL dans l’étiquette de nettoyage. Le nom logique reste interne ; l’étiquette
C utilise désormais `drop-result`, et l’absence de NUL est vérifiée.

Ce raccordement ne couvre pas encore toutes les opérations propriétaires,
notamment le drop direct du résultat de pop, ni l’interdiction de tous les
motifs consommateurs `_` visés par le brouillon 01.

### Limites de cette étape

Le contrôle d’usage couvre les modes de résultats inline déclarés dans le
prototype ; les familles propriétaires, les motifs consommateurs et tous les
parcours de join restent à confronter entièrement au brouillon 01. Le suivi
des usages conditionnels n’est pas une preuve d’exécution effective. Les cas
généraux d’écrasement sous contrôle de flux doivent encore être audités.
La frontière publique des erreurs de runtime, Select et les mutex relèvent
toujours du lot async restant. Les découpes UTF-8 faillibles restent à ajouter.

La régression ultérieure du cycle UTF8_TRY_SLICE_CYCLE.md inclut les douze
méthodes de conversions, les scénarios UTF-8/async migrés et l'arithmétique :
124 méthodes passent (`/tmp/crust-try-slice-regression.log`). Ce périmètre est
explicite ; il ne remplace pas une exécution intégrale de tous les tests.
