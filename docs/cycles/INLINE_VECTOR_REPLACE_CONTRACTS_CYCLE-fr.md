[English](INLINE_VECTOR_REPLACE_CONTRACTS_CYCLE.md)

# Cycle — Contrats de replace des structures en ligne

## Périmètre et statut

Extension synchrone de INLINE_VECTOR_REPLACE_CYCLE.md. VE1–VE3, H1, U1,
B1–B5, T4/T5/T6, F2–F4 et ST17/ST18 restent inchangées. AGENTS.md,
VALIDATION_GUIDELINES.md et design-buffer/decisions.md relus ; les règles de
vectors et leurs dépendances sont reprises dans ce travail continu.
Aucune sémantique normative nouvelle. Le chantier global reste ouvert.

Snapshot initial : `/tmp/crust-before-inline-vector-replace-contracts`.
La fixture `validation/inline-vector-replace-return.crust`, refusée avant ce
lot, rend maintenant 7 puis 9 dans le C exécuté avec UBSan.

## Réalisation

Le contrat sépare l'identité du porteur local de la valeur des champs de chaque
bras. Replace réutilise le porteur de l'entrant ; Ok contient l'ancienne case,
Err l'entrant inchangé. Deux charges peuvent partager ce porteur sans partager
leur graphe de champs. Les analyses de résultat et de contraintes conservent
ces charges distinctes, y compris lors des jointures et des relais.

Le placement réserve le constructeur entrant dans le stockage de l'appelant
lorsqu'il fournit le résultat local. La taille réservée est celle de T, pas
celle du type syntaxique Result<T,T>. Un entrant transmis en paramètre conserve
son identité de stockage. La case du vector reçoit une identité distincte,
liée au stockage du vector ; ses champs gardent leurs cibles propres.
Les obligations de stockage local de l'entrant sont propagées dans le contrat.
La jonction d'un résultat conserve la distinction T / A<T>.
Les signatures de paramètres et de retour Result<T,T> portent également cette
distinction, y compris dans la vérification symbolique des corps.

## Validation ciblée

`-contract-targeted-fifth.log` : 12 méthodes, 9,053 s, code 0, O0/UBSan
(les sept méthodes locales existantes et les cinq premières méthodes de contrats).
`-contract-branches-second.log` : six méthodes de contrats, 4,534 s, code 0,
après ajout des retours conditionnels. Ce dernier module exécute 11 programmes
C admis et quatre variantes refusées aux deux entrées verify_program et
compile_source.

Cas admis : construction fraîche ou nommée, retour via un relais, Ok et Err,
retours conditionnels, entrant transmis par paramètre, champs A<Int> ou &Int,
lecture après drop du vector, nettoyage unique et réemploi de deux slots.
Cas refusés : réutilisation de l'entrant transféré, mutation des cibles avant
le dernier usage du résultat, déclaration A<T> pour un résultat local T.
Reset est retiré du profil courant.

Les premiers journaux conservent les défauts rencontrés : porteur local
confondu avec une allocation de case, fusion des charges utilisant une
représentation propre à une seule analyse, flèche d'un appel retourné non
reconnue, obligation locale absente du filtre d'analyse et identité de case
absente du contrat d'écriture. Ces défauts sont corrigés dans le ciblé.
Trois erreurs de fixtures ont aussi été corrigées : méthode du harnais
manquante, remplacement textuel ne correspondant pas aux espaces de la fixture,
et paramètre A<Int> écrit Int. Le premier test conditionnel utilisait Bool,
alors que le type du langage est bool ; la fixture utilise un Int comparé à 1.
Les sorties attendues et les règles n'ont pas été modifiées.

Le transfert du Result local lui-même vers une fonction a révélé un dernier
écart : le type de stockage des paramètres Result était encore implicitement
celui d'une allocation. Les signatures, entrées symboliques et obligations
portent maintenant le type de stockage déclaré. La fixture
`validation/inline-vector-replace-result-parameter.crust` et son refus initial
`-contract-result-parameter-baseline.log` sont conservés.

Ciblé final : `-contract-graph-targeted.log`, **huit méthodes, 7,461 s, code 0**,
O0/UBSan ; **17 programmes C admis** et **six variantes refusées** aux deux
entrées. Les compléments couvrent le Result transféré en paramètre, ses champs
propriétaires/empruntés et les deux bras, ainsi que le refus T/A<T> et l'absence
de flèche de retour.
Le C conservé dans `validation/inline-vector-replace-contract.c` montre que
l'appelant réserve sizeof(int) pour Point, que le callee construit l'entrant
dans local_output puis retourne ce porteur après vector_replace.

## Régression et limites

Premier passage O2/UBSan : **169 méthodes, 129,800 s, code 0**. Les 46 empreintes
suivies sont inchangées. Les deux méthodes ajoutées ensuite pour les paramètres
Result ne faisaient pas partie de ce premier passage.
Le passage final a été interrompu lors d'une reprise de session : le handle
64303 était introuvable, le journal ne contenait pas de bilan et le fichier
d'intégrité était absent. Ce passage incomplet, conservé sous le préfixe
`validation/inline-vector-replace-contract-final`, n'est pas compté comme réussi.

Le rejeu complet a terminé : **171 méthodes, 160,035 s, code 0**, O2/UBSan.
Les 46 empreintes sont inchangées pendant l'exécution. Sélection, journal,
empreintes initiales et résultat d'intégrité utilisent le préfixe
`validation/inline-vector-replace-contract-replay`.
La sélection couvre le ciblé, push/remove/pop et champs des structures en ligne,
leurs cas async existants, les échanges typés et les obligations de stockage.
Diff et manifeste du changement : `-contract.patch` et `-contract-changes.json`.
La sélection initiale utilise le préfixe `validation/inline-vector-replace-contract`.
Le harnais compile en C11 avec pthread, Wall/Wextra/Werror et UBSan fatal.

Le passage de ce remplacement dans un état async reste ouvert. La fixture
`validation/inline-vector-replace-async.crust` est refusée aux deux entrées
(`-async-baseline.log`) : le lowering attend encore un élément de type A<T>.
C'est le prochain raccordement identifié. Les cas de
contrats exécutés ici ne prouvent pas toutes les compositions de graphes et de
types. Les positions inconnues restent conservatrices. Pas de preuve générale
ni de campagne adversariale étendue ; l'état du lab indépendant n'est pas supposé.
