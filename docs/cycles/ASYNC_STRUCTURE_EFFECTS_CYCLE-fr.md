[English](ASYNC_STRUCTURE_EFFECTS_CYCLE.md)

# Contrats différés de remplacement des champs références

## Périmètre de cette étape

Mise à jour : les résultats empruntés des enfants attendus sont désormais
analysés conjointement avec les effets, dans
[le cycle des contrats de terminaison](ASYNC_COMPLETION_RESULTS_CYCLE.md).
Les limites ci-dessous décrivent l'état à la fin du présent cycle.

Aucune règle normative modifiée. ST10, ST8/ST12/ST13, B4 et AS2/AS12/AS13
imposent de suivre les nouvelles cibles d'un porteur emprunté, y compris après
l'attente d'une tâche. Cette étape implémente **l'inférence des effets**, pas
encore leur application par le backend async et chez l'appelant. Le refus des
appels async modifiant ces dépendances demeure en place. L'objectif global
n'est pas terminé.

Le compilateur produit `async_structure_effects` avant l'abaissement des états.
Chaque entrée distingue un contrat calculé, éventuellement vide, d'un contrat
non résolu (`structure_fields=None`, avec diagnostic). Un cas inconnu ne peut
pas servir de preuve d'absence de mutation. Le résumé indique aussi si le corps
possède un chemin de terminaison normale ; il n'affirme pas que ce chemin sera
pris à l'exécution.

Le module `async_structure_effects.py` réutilise le calcul symbolique des champs
du vérificateur synchrone. Ses auxiliaires synchrones sont représentés par
leurs contrats et des corps vides. Le remplacement instancie les origines à
partir des valeurs d'entrée sauvegardées. L'application commune du contrat a
été extraite dans `ResultContext.apply_structure_updates`, sans changement de
sémantique synchrone.

La création d'un enfant conserve ses arguments ; elle n'applique pas ses
écritures. L'attente applique le contrat de terminaison de l'enfant. La
destruction d'une tâche inactive n'applique rien. Une attente d'exécution lancée
réunit l'état après exécution avec l'état initial possible en cas de refus de
lancement. Un enfant divergent ne fabrique pas de continuation ; le refus de
son lancement peut en revanche rendre la main. Les branches, retours,
réemprunts de porteurs, renommages et boucles utilisent les jonctions existantes.
Les captures différées ont leur propre champ symbolique, distinct des identités
de stockage des structures.

Les contrats non résolus comprennent les effets récursifs, les agrégats hors
layout Int/&Int/&mut Int, les origines de résultats empruntés d'enfants et le
passage d'un handle porteur d'effets à un auxiliaire synchrone. Ce dernier cas
est explicitement détecté : le contrat actuel de l'auxiliaire ne peut pas faire
disparaître les écritures encore différées.

## Contre-exemples et frontières

Le programme conservé dans `validation/open-async-sync-field-replacement.crust`
avait une écriture implicite `view.data = next`. La vérification du corps
synchrone exige le réemprunt explicite `view.data = &*next`. L'original est
conservé sous le suffixe `-original.crust`, et les diagnostics précédents restent
historiques. La version corrigée possède le contrat attendu : le champ `.data`
du premier paramètre cible le deuxième paramètre.

Dans une copie temporaire seulement, retirer le refus async permet à
`verify_program` d'accepter le cas corrigé, mais `compile_source` refuse encore
le stockage de l'emprunt. Le bridge transmet un pointeur vers l'Int, tandis que
le champ référence stocke un `Cell *`. Journal :
`validation/async-structure-effects-next-boundary.log`. Ce n'est ni une
exécution du programme ni une validation du retrait du contrôle. La copie
temporaire a été supprimée, et le contrôle demeure dans les sources actives.

Un complément a révélé une erreur dans la nouvelle analyse : après un choix
entre deux fonctions async, le type public `runtime::Handle<Int>` n'est pas
une clé de la table des fonctions. L'ancienne lecture par ce nom produit un
KeyError, reproduit dans une copie temporaire dans
`validation/async-structure-effects-choice-counterexample.log`. Les signatures
sont désormais réunies depuis les captures différées des fonctions concrètes.
Le choix conserve les deux cibles nouvelles et l'ancienne cible possible à
l'échec de lancement. Aucun refus utilisateur ne remplace ce correctif.

Les étapes nécessaires restent : représentation durable de la cible à travers
le bridge, suivi des champs dans l'état suspendu, effets attachés aux tâches et
handles, puis application chez l'appelant après attente et suivi des prêts,
transferts et destructions. Les tableaux de résultats et les contrats publics
doivent conserver ces mêmes effets avant de lever le refus.

## Validation exécutée

`tests/test_async_structure_effects.py` couvre dix-sept méthodes : seize de
contrats et un voisin synchrone exécuté. Les programmes comportant les nouvelles
écritures async ne sont pas présentés comme exécutables. Les déclarations
d'auxiliaires synchrones sont vérifiées normalement avant l'analyse ciblée.

- Le modèle indépendant énumère 125 scénarios : une action initiale et deux
  branches parmi aucune écriture, cible a, cible b, enfant attendu et enfant
  détruit inactif. Un état concret « ancien/a/b » calcule les cibles attendues,
  sans employer les contrats ni le générateur C.
- Les autres tests couvrent deux champs échangés, origines détachées, champs
  mutables, alias masqués, trois niveaux d'attente, permutations des paramètres,
  choix de tâches par if/loop, sorties précoces, boucles et divergence.
  Un complément vérifie la convergence d'une boucle d'enfants attendus qui
  échangent deux champs ; un modèle concret de période deux fournit les cibles
  possibles indépendamment de l'analyse symbolique.
- Les cas non résolus doivent produire un statut incomplet explicite. Le test
  du programme complet vérifie que le contrat est calculé et que les deux
  entrées conservent le refus du backend.

Première passe : erreur de fixture due au réemprunt implicite, sans test exécuté.
Deuxième passe : onze méthodes réussies et une assertion d'origine erronée ;
ST13 exige ici `detached_field_parameter`, et non une réservation du porteur.
Les cibles et chemins attendus n'ont pas été changés. Les passes suivantes
réussissent douze, puis quatorze, puis quinze méthodes. Journaux
`validation/async-structure-effects-{initial,recheck,contracts,expanded,final,complete}.log`.
Le passage final groupé de seize méthodes est conservé dans
`validation/async-structure-effects-loop-final.log`.
Le complément synchrone exécute le remplacement, détruit l'ancienne cible et
affiche deux fois 9 ; détruire la nouvelle cible avant sa lecture est refusé
aux deux entrées. Les dix-sept méthodes passent ensuite ensemble à O0 (0,543 s)
et O2 (0,749 s), dans `validation/async-structure-effects-final-o{0,2}.log`.
Chaque passage comporte une exécution C de ce voisin sous UBSan fatal ; les
tests du nouveau contrat restent des analyses statiques, indépendantes du
niveau d'optimisation C.
Après le complément de choix entre fonctions distinctes, les dix-sept méthodes
passent à nouveau à O0 (0,597 s) et O2 (0,453 s), dans
`validation/async-structure-effects-choice-final-o{0,2}.log`.

La régression champs/handles réussit 85 méthodes à O2 en 79,808 s, avec Clang,
C11, pthread et UBSan fatal dans le harnais natif. Elle précède les derniers
compléments de statut incomplet, couverts par la passe ciblée finale et la
régression native élargie suivie séparément.
La première sélection synchrone termine 56 méthodes réussies et une erreur de
chargement : le nom `test_structure_field_updates` n'existe pas. Ce journal
n'est pas présenté comme vert ; la sélection corrigée est enregistrée à part.
Elle réussit 56 méthodes en 26,157 s dans
`validation/async-structure-effects-sync-final.log`, avec UBSan fatal. Le harnais
historique synchrone n'ajoute pas d'option d'optimisation explicite ; ce passage
n'est pas étiqueté O2.
La sélection native élargie réussit 312 méthodes à O2 en 233,060 s dans
`validation/async-structure-effects-native-o2.log`. Elle couvre l'intégration de
l'inférence dans le compilateur et précède le dernier correctif du choix de
fonctions concrètes, couvert par les passages ciblés suivants. Les sélections
se recouvrent ; leurs nombres ne sont pas additionnés en couverture unique.
Les dix-sept méthodes des contrats publics de handles passent après ce correctif
à O2 en 16,072 s : `validation/async-structure-effects-public-regression-o2.log`.
La dernière campagne de sept mutations passe aussi après ce correctif :
`validation/async-structure-effects-mutations-complete.log`.

## Mutations

`tests/run_async_structure_effect_mutations.py` modifie des copies temporaires.
La campagne initiale détecte six fautes ; la campagne finale en détecte sept :
écritures de l'enfant oubliées, échec de lancement oublié, continuation après
divergence inventée, inconnu transformé en contrat vide, captures perdues lors
d'un choix, effets synchrones ignorés, perte d'effets à la frontière d'un
auxiliaire de handle. Les assertions de contrats détectent ces fautes ; ce ne
sont pas sept violations mémoire démontrées à l'exécution. Journaux
`validation/async-structure-effects-mutations*.log`.

## Limites

Le calcul réutilise les jonctions du vérificateur : il ne constitue pas un
second vérificateur indépendant. Seul le petit oracle de 125 scénarios calcule
les attentes indépendamment. Il n'y a ni preuve formelle, ni nouvelle preuve
ASan/TSan, ni second compilateur C. Une inférence complète ne remplace pas la
vérification des emprunts, des types, des obligations d'attente ou du backend.

Snapshot : `/tmp/crust-before-async-structure-effects`. Les différences et les
nouveaux modules sont conservés dans `validation/async-structure-effects-*.patch`.
