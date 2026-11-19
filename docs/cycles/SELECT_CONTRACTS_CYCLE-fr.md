[English](SELECT_CONTRACTS_CYCLE.md)

# SL1 — Parsing et composition des contrats de Select

## Portée réelle

Ce lot poursuit les [contrats de suspension](SUSPENSION_EFFECTS_CYCLE.md).
La syntaxe `runtime::select(-> tache1, -> tache2, ...)` est maintenant parsée.
L'analyse des effets async compose les contrats des branches, sans exécuter
leurs corps à la création et sans reparcourir les corps des helpers synchrones.

Le vérificateur des captures, l'attente unique, les transferts de stockage et
le backend source de Select restent à raccorder. Un programme source complet
contenant Select n'est donc **pas encore compilable** : il reçoit le diagnostic
`prototype async : expression task_select non prise en charge`. Le test de
cette frontière constate un écart d'implémentation, pas une interdiction normative.

AGENTS.md, VALIDATION_GUIDELINES.md et l'index de design-buffer ont été suivis ;
SL1 et le brouillon 04 définissent le comportement visé. Aucune nouvelle règle
normative ni politique de destruction des handles lancés n'est décidée ici.

## Composition

- Chaque argument doit porter `->`. Les arguments sont évalués dans l'ordre ;
  leurs effets synchrones sont exécutés symboliquement à la construction,
  tandis que les tâches transférées restent inactives.
- Les branches doivent avoir le même résultat, mode compris. Le descripteur
  symbolique d'une sélection conserve ce type et les alternatives de capture.
- Pour une gagnante possible, le contrat applique ses effets de terminaison.
  Les perdantes précédentes ont nécessairement été pollées : leurs états
  suspendus sont considérés. Les branches suivantes peuvent être non pollées,
  ou suspendues depuis un tour antérieur si la gagnante pouvait suspendre.
- Une branche qui ne suspend jamais empêche de poller les suivantes : soit elle
  rend Ready, soit elle ne rend pas la main. Les corps suivants ne sont alors
  pas nécessaires pour décrire les effets de cette attente.
- L'appelante peut suspendre si toutes les branches le peuvent. Son résumé de
  suspension combine les préfixes des branches, sans leur ajouter des effets
  de terminaison ni une restauration future.
- Le résultat emprunté provient uniquement des gagnantes possibles. Les effets
  persistants des perdantes sont conservés indépendamment de ce résultat.
- Une composition requérant un résumé inconnu reste inconnue, avec diagnostic.
  Une sélection créée puis détruite sans attente n'exige pas de connaître les
  effets de corps qui ne sont jamais exécutés.

La composition décrit les états de champs ; elle ne remplace pas la vérification
que deux branches ne capturent pas simultanément la même cible de façon exclusive.
La rétention des captures jusqu'au drop de Select reste à raccorder au backend.

## Contre-exemple corrigé pendant l'intégration

Le descripteur de sélection n'était pas reconnu comme valeur transférable par
l'analyse des expressions conditionnelles et des moves. Les champs calculés
par une sélection choisie dans un if ne pouvaient donc pas rejoindre l'appelante.
Les sélections sont maintenant admises dans ces transferts symboliques ; leur
type inclut le résultat et leur ensemble d'alternatives conserve les captures.
Le test couvre aussi `break <- selection` puis un renommage explicite.

Programme conservé :
[select-contracts-conditional-selection.crust](../../validation/select-contracts-conditional-selection.crb).
La reproduction avant correction utilise une copie temporaire de `results.py`
et les mêmes oracles finaux :
`validation/select-contracts-transfer-counterexample.log`. Le refus de l'analyse
est confirmé. Le programme complet reste soumis à la limitation du backend
Select indiquée plus haut ; seule cette erreur de contrat est levée par ce lot.

## Validation exécutée

`tests/test_select_contracts.py` contient seize méthodes : parsing admis/refusé,
effets avant restauration, branches non pollées, perdante non terminante,
suspensions de l'appelante, construction sans exécution, arguments synchrones,
types incompatibles, résumés inconnus, retours empruntés, captures sauvegardées,
sélections imbriquées, transferts conditionnels et par boucle.

Un modèle indépendant exécute 25 couples de petits programmes, avec deux
champs extérieurs distincts. Ses positions d'instructions, écritures, pauses
et choix du premier Ready sont calculés sans contrats ni objets du compilateur.
La cible réellement laissée dans chaque champ doit appartenir à l'union
annoncée. Ce contrôle vérifie une inclusion : il ne démontre pas que l'union
est minimale. Les cas déterminés par une première branche immédiatement prête
ont en plus des assertions exactes sur les cibles et le résultat emprunté.

Une sonde C utilise deux états et destructeurs générés : la perdante modifie
un premier champ, la gagnante un second. Le résultat est 9 ; les deux écritures
restent observables après drop de Select. Huit réemplois sont exécutés.
Le Select de cette sonde est construit dans le harnais C, pas encore depuis
la syntaxe source du langage.

Journaux sous `validation/` ; les exécutions C emploient Clang C11/pthread,
Wall/Wextra/Werror et UBSan fatal :

- `select-contracts-initial.log` : onze méthodes d'analyse, 0,037 s, OK.
- `select-contracts-final-15-o0.log` : quinze méthodes, 0,486 s, OK.
- `select-contracts-final-16-o0.log` : seize méthodes, 0,636 s, OK.
- `select-contracts-final-mutations-o2.log` : baseline finale de seize méthodes,
  0,650 s, OK ; huit mutations détectées. Elles retirent le marqueur explicite,
  substituent la terminaison d'une perdante à sa suspension, oublient l'état
  non pollé, perdent l'origine du résultat ou les captures, omettent la
  suspension parente, acceptent des résultats incompatibles ou exigent à tort
  le contrat d'une branche jamais pollée.
- `select-contracts-regression-o2.log` : 74 méthodes, 9,524 s, OK, avec les
  suspensions, les contrats existants, les résultats synchrones et Select C.
- `select-contracts-final-regression-o2.log` : 83 méthodes, 7,413 s, OK,
  après correction des transferts conditionnels : seize nouvelles méthodes,
  quinze de suspension, 25 des contrats async et 27 des résultats synchrones.
- `select-contracts-prefix-mutations-o2.log` et
  `select-contracts-completion-mutations-o2.log` : les huit mutations de
  suspension et onze de terminaison précédentes sont détectées. Leur ancre
  d'enfant non terminant vise explicitement l'attente ordinaire après l'ajout
  du parcours Select ; aucune assertion n'est affaiblie.
- Compilation Python des fichiers du lot réussie.

Les premiers passages à treize et quatorze méthodes sont conservés également.
Ces comptages se recouvrent ; ils ne désignent pas des programmes distincts.
Les mutations ont lieu sur des copies temporaires, sans modifier les oracles.

## Limites et travail suivant

Les résumés actuels disent qu'une branche *peut* suspendre, sans distinguer
tous les chemins qui suspendent nécessairement avant leur premier retour.
Par conséquent, l'union peut retenir une gagnante impossible dans une exécution
concrète, et protéger trop de cibles. Le test restauration/gagnante immédiate
rend cette limite explicite. L'ordre des branches toujours immédiatement prêtes
est déjà exploité, sans imposer une nouvelle règle au programmeur.

Les champs injectés reconnus et les retours scalaires/empruntés sont composés.
Les retours agrégés, les autres conteneurs de références, les effets concurrents
de handles et les gardes de mutex restent à compléter. Les signatures récursives
inconnues ne deviennent pas des contrats vides.

La prochaine intégration doit relier ces descripteurs au suivi des captures et
de l'attente unique, au nettoyage par scope et suspension, à la réception des
résultats et au dimensionnement des pools d'états retenus. L'arbitrage sur une
perdante qui possède un handle lancé reste ouvert. Ce lot ne termine ni SL1,
ni l'objectif global. Pas de preuve formelle, ni nouveau résultat ASan/TSan.
