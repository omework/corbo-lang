[English](VECTOR_PAYLOAD_GRAPHS_CYCLE.md)

# Cycle — Graphes des éléments de vecteurs locaux

## Portée et règles

Application de H1–H3, VE1–VE4, F2–F4, B1–B5, D1–D3 et des règles de
transfert/nettoyage par scope. Aucune règle normative n'est modifiée.
AGENTS.md, VALIDATION_GUIDELINES.md, l'index des décisions et les règles
concernées ont été consultés. La priorité reste l'implémentation des cas
retenus et leurs régressions directes ; le laboratoire adversarial indépendant
n'est pas exécuté ni réputé terminé par ce cycle.

Ce lot ouvre les vecteurs **locaux synchrones** de handles dont les objets
contiennent des références et/ou des allocations. Il ne clôt pas le chantier
des collections complexes : leurs paramètres/résultats de fonctions et leur
intégration async restent à raccorder. Les fonctions peuvent déjà construire
un vecteur local et retourner l'objet extrait, avec propagation de ses champs
empruntés dans le contrat.

## Implémentation

- Le vecteur conserve le graphe de chaque élément, indexé par les identités
  possibles de ses allocations. Les parcours de dépendances et de sources
  suivent ces graphes, y compris les descendants propriétaires.
- Remove et pop transmettent les champs empruntés, les parents de réemprunt,
  les champs propriétaires et les variantes possibles au nouvel accès.
  Les options, les sorties de boucle et les jonctions conservent ces données.
- Replace et try_push enregistrent les graphes des deux résultats possibles.
  L'extraction d'un résultat sélectionne le graphe de son bras. La mise à jour
  d'une case via un emprunt mutable enregistre aussi le contenu entrant.
- Les états de branches et le point fixe des boucles incluent les graphes.
  Les nouvelles identités créées lors d'une réanalyse ne sont pas prises à tort
  pour un changement sémantique imposant une réanalyse infinie.
- Les analyses symboliques des résultats et des contraintes conservent les
  valeurs complètes des éléments à côté de leurs identités de stockage.
  L'extraction restitue les métadonnées des champs ; les contrats de l'objet
  extrait peuvent ainsi être utilisés par un appelant puis par un relais.
- Les signatures de vecteurs complexes encore incomplètes conservent un refus
  explicite, y compris sous A<Vector<…>> et en résultat. C'est un écart
  d'implémentation temporaire, pas une nouvelle restriction du langage.

Le runtime de stockage et les adresses des objets ne changent pas. Le C utilise
les handles existants ; le nettoyage du vecteur appelle déjà celui des éléments.

## Scénarios et défauts rencontrés

Onze méthodes ciblées : **20 exécutions C** avec passage préalable par
verify_program et compile_source, et **28 programmes invalides** contrôlés aux
deux entrées (56 décisions de refus).

- Push/remove conserve une référence partagée, permet la lecture du contenu,
  puis le réemploi d'un pool de capacité 1. Le drop prématuré de la cible et
  l'utilisation de l'ancien handle déplacé sont refusés.
- Pop direct, option nommée, option issue d'un if et d'une boucle : contenu
  lu puis détruit ; la dépendance reste active tant que le résultat doit servir.
- Item possède Inner, qui emprunte Int : lecture via une fonction, nettoyage
  unique des deux objets et réemploi de leurs pools ; drop de la cible refusé
  avant l'extraction et avant l'utilisation de l'objet extrait.
- Le champ &mut Int interdit lecture, mutation et destruction concurrentes de
  la cible. Les six refus couvrent le vecteur et l'objet extrait.
- Replace avec indice valide/invalide restitue respectivement l'ancien objet
  ou l'entrant, et conserve les dépendances des deux objets encore possibles.
- Try_push réussi, consommation directe par drop de remove/pop, remplacement
  de case par &mut A<Item> : responsabilité et nettoyage conservés.
- Remove de la première case distingue deux objets du même pool empruntant
  deux cibles ; la première cible peut être détruite après son objet extrait.
- Réemploi sur trois itérations et transfert du vecteur depuis if/loop.
- Un constructeur utilisant un vecteur local rend l'objet extrait ; un relais
  supplémentaire conserve le contrat d'emprunt. Le drop prématuré chez
  l'appelant reste refusé.
- Le transfert refuse un pool d'élément ou une cible qui ne survit pas au
  receveur. Aucun déplacement implicite de ces dépendances n'est introduit.

Le premier essai a révélé une perte de type/champs du descendant propriétaire
dans l'analyse symbolique : le C local pouvait conserver le graphe, mais un
appel sur ce descendant était refusé. Les métadonnées sont maintenant conservées
par les analyses de résultats et de contraintes, sans contourner leurs contrôles.

Trois échecs du troisième essai provenaient des nouveaux exemples de tests :
réemprunt de pool avec une syntaxe non prise en charge (le paramètre déjà emprunté
se passe par son nom), transfert descendant manquant avant insertion dans le
bloc enfant, et substitution de texte manquant un saut de ligne. Les programmes
ont été corrigés conformément aux règles existantes ; les attentes de sûreté
n'ont pas été changées.

## Preuves d'exécution

- Cas enregistré initial : sortie 7 puis 9 et traces de destruction dans
  `validation/vector-payload-graphs-first-o0.log`. Le journal est terminé ;
  l'ancien identifiant de processus n'était plus disponible à la reprise.
- Premier ciblé O0 : six méthodes, 4,046 s, code 1, un échec de métadonnées.
- Deuxième ciblé O0 : six méthodes, 4,909 s, code 0.
- Troisième ciblé O0 : dix méthodes, 5,178 s, code 1, trois erreurs de fixtures.
- Quatrième ciblé O0 : dix méthodes, 6,732 s, code 0.
- Cinquième ciblé O0 : onze méthodes, 7,082 s, code 0.
- Ciblé final O0 : onze méthodes, 7,029 s, code 0,
  `validation/vector-payload-graphs-targeted-final-o0.log`.
- Régression O2 : 135 méthodes, 113,766 s, code 1, sept sous-cas en échec
  répartis dans cinq méthodes historiques. Sélection dans
  `validation/vector-payload-graphs-test-selection.txt`, journal
  `validation/vector-payload-graphs-regression-o2.log`.
- Reproduction sur le snapshot avant lot : quinze méthodes, 7,604 s, code 1,
  les sept mêmes échecs. `validation/vector-payload-graphs-nested-baseline-o2.log`
  indique explicitement le chemin du compilateur sauvegardé.
- Après mise à jour des seules annotations des fixtures : quinze méthodes,
  10,713 s, code 0, `validation/vector-payload-graphs-nested-final-o2.log`.

Les sept anciens sous-cas rendaient des allocations de pools avec une annotation
T local. Ils annoncent maintenant A<T>, conformément à la distinction normative
déjà intégrée. Les assertions de destruction, d'identité et de refus restent
inchangées. La régression de 135 méthodes et ce complément de quinze méthodes
sur le **même compilateur** ferment les échecs observés ; ce n'est pas un passage
monolithique de 135 méthodes entièrement vert.

Deux modèles existants sont rejoués sans modification de leurs prédictions :
les huit combinaisons des durées de vie pool extérieur/pool descendant/cible
(un programme admis et sept refusés), et les quatre combinaisons local/pool
de deux paramètres (quatre admis et quatre refusés). Ils ne modélisent pas à eux
seuls les opérations des nouveaux vecteurs.

Le harnais compile du C11 avec pthread, Wall/Wextra/Werror et UBSan fatal.
Le source initial est `validation/open-vector-handle-borrowed-fields.crust` ;
son C actuel est conservé dans `validation/vector-payload-graphs-remove.c`.
Les journaux initiaux en échec restent présents.

## Limites et suite

Le cas valide `validation/open-vector-payload-contract.crust` reste refusé
aux deux entrées : une fonction reçoit directement &mut Vector<A<Item>> et
retourne un objet empruntant extrait. Le journal associé conserve le diagnostic.
Il reste à formaliser ces métadonnées dans les contrats de conteneurs et de
leurs mutations, puis à les transmettre aux captures/résultats async.

Les échanges différés gardent une union conservative des éléments possibles du
vecteur ; ce lot ne promet pas une précision nouvelle pour tous les indices ou
toutes les corrélations entre variantes. Les enums complexes, les charges de
collections récursives, les lectures par toutes les formes de projections et
les compositions async générales ne sont pas validés ici. La régression des
parcours async précédents n'établit pas leur prise en charge pour ces graphes.

Reset reste absent du profil normal. Les mutations et la recherche adversariale
approfondie sont reportées au laboratoire demandé par l'utilisateur. Ce cycle
ne fournit ni preuve générale de sûreté ni clôture de l'objectif global.

## Traçabilité

Snapshot avant lot : `/tmp/crust-before-vector-payload-graphs`.
Patches exacts et empreintes avant/après :
`validation/vector-payload-graphs-changes.json`.
