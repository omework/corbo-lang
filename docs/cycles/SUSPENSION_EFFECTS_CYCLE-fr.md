[English](SUSPENSION_EFFECTS_CYCLE.md)

# SL1 / AS9 / AS12 — Effets des champs aux suspensions

## Problème et portée

Une branche peut écrire `view.data = next`, suspendre, puis restaurer l'ancien
champ après son `yield`. Si elle perd un Select, la restauration n'est jamais
exécutée. Son contrat de terminaison ne décrit donc pas l'état extérieur laissé
après destruction de la perdante. Le programme de conception reste dans
[open-select-partial-field-effect.crust](../../validation/open-select-partial-field-effect.crb).
Il n'est pas actuellement compilable : le raccordement source de Select reste
ouvert. Ce lot prépare ce raccordement sans modifier les règles normatives.

AGENTS.md, VALIDATION_GUIDELINES.md, l'index et le brouillon 04 ont été consultés.
La distinction découle de SL1 et des règles existantes de provenance et de
destruction ; aucune annulation publique ni attente cachée n'est ajoutée.
Les anciennes mentions globales « non implémenté » de LANGUAGE_RULES.md et les
en-têtes des extensions async, régions et UTF-8 sont actualisés en statuts
partiels avec renvoi à la matrice. L'ancienne liste
de travaux est identifiée comme historique. Ces corrections de statut ne
changent pas la sémantique des règles.

## Implémentation

`AsyncStructureEffects` expose deux résultats distincts :

- `completion_result`, utilisé par les appels et attentes ordinaires ;
- `suspension_result`, décrivant l'union des cibles de champs aux suspensions
  atteignables. `may_suspend` distingue l'absence de suspension d'une suspension
  sans modification de champ. `suspension_complete` est indépendant de `complete`.

Les observations sont prises au `yield`, après les instructions précédentes.
Un store dont le membre droit se suspend n'est observé qu'après sa réalisation.
Les enfants attendus transmettent leurs états suspendus à travers leurs captures
sauvegardées, même s'ils ne terminent jamais. Les noms masqués et permutations
de paramètres ne changent pas ces captures. Une simple création inactive
n'exécute aucun effet. Un enfant terminé sans suspendre ne crée pas un point
de suspension fictif chez son parent.

Les états de branches et de reprises de boucles sont réunis. Les résumés des
auxiliaires synchrones sont utilisés sans corps de fonction. La projection
d'un enfant suspendu utilise un environnement séparé ; elle ne remplace pas
l'état de continuation normale. Les résultats empruntés et leurs capacités
restent dans le contrat de terminaison, séparés du résumé de champs suspendus.

Une cible non durable observée dans un champ, ou une composition de tâches
lancées dont les effets concurrents ne sont pas encore représentés, produit
un résumé de suspension inconnu avec raison. Ce résultat inconnu se propage
aux parents. Il n'est jamais remplacé par un résumé vide ; le contrat de
terminaison peut néanmoins rester disponible. Cela n'autorise pas encore
la destruction d'une branche possédant un handle lancé.

## Scénarios et preuves

`tests/test_suspension_effects.py` comprend quinze méthodes :

- Store/restauration avant ou après yield ; fonction sans suspension.
- Enfant inactif détruit, enfant immédiatement terminé, suspension du parent.
- Membre droit suspendu avant affectation du champ.
- Choix de tâches avec captures différentes ; alternatives de branche inchangée.
- Trois niveaux d'attente, permutation de paramètres, alias et nom masqué.
- Enfant qui suspend indéfiniment et branche voisine qui termine normalement.
- Boucles échangeant des références, champs mutables et résultat emprunté.
- Résumés inconnus locaux et propagés, sans perte du contrat de terminaison.
- Conteneurs de références dont les effets suspendus ne sont pas représentés :
  une garde empêche de présenter leurs mises à jour absentes comme un effet vide.
- Modèle indépendant de 64 séquences de trois actions : écrire a, écrire b,
  échanger deux cibles, suspendre. Deux étiquettes dans une liste décrivent
  l'état concret ; seules les pauses ajoutent une observation. Les attentes
  sont calculées sans valeurs ni graphe de contrôle du compilateur.
- Programme ordinaire exécuté après attente complète : drop de la cible
  temporaire accepté, lecture de la cible restaurée égale à 1. Le voisin
  détruisant cette dernière est refusé par check et compile.
- Sonde Select C avec frames et nettoyages réellement générés, huit réemplois :
  la branche gagnante rend 9 ; le champ de la perdante conserve la seconde
  cellule après destruction, avec valeur 2. Le harnais garde cette cellule
  vivante ; il ne provoque pas artificiellement un accès après libération.

La sonde C démontre l'écart entre suspension et terminaison. Elle ne démontre
pas encore le refus statique du programme Select source, qui reste à raccorder.

Exécutions Clang C11/pthread, Wall/Wextra/Werror, UBSan fatal, O0/O2 :

- `validation/suspension-effects-existing-initial.log` : 25 méthodes des
  contrats existants, 1,447 s, OK.
- `validation/suspension-effects-initial-o0.log` : 19 méthodes, 11,625 s, OK.
  Dix provenaient d'une classe importée collectée aussi par unittest. L'import
  a été remplacé par un import de module pour ne pas doubler cette collecte.
- `validation/suspension-effects-final-o0.log` : 11 méthodes, 1,136 s, OK.
- `validation/suspension-effects-complete-o0.log` et `complete-o2.log` :
  13 méthodes, 1,645 s et 1,610 s, OK.
- `validation/suspension-effects-final-14-o0.log` et `final-14-o2.log` :
  14 méthodes, 1,264 s et 1,129 s, OK.
- `validation/suspension-effects-propagation-o0.log` : extension du test des
  résumés inconnus aux parents, une méthode, 0,008 s, OK.
- `validation/suspension-effects-final-mutations-o2.log` : baseline finale
  de 14 méthodes, 1,134 s, OK ; sept mutations détectées. Sont ciblés l'oubli
  de yield, la perte d'un état antérieur, l'oubli des suspensions d'enfants,
  une continuation inventée, la confusion des contrats, l'inconnu rendu vide
  et l'acceptation d'une cible non durable. Les oracles restent inchangés
  dans les copies temporaires. La campagne précédente sur 11 méthodes est
  conservée dans `suspension-effects-mutations-o2.log` (sept détections aussi).
- `validation/suspension-effects-contract-regression-o2.log` : 94 méthodes,
  61,545 s, OK : résultats synchrones, contrats async, champs mutables,
  retours empruntés, fabriques et boucles.
- `validation/suspension-effects-final-15-o0.log` : 15 méthodes, 1,071 s, OK,
  après ajout de la garde sur les autres conteneurs de références.
- `validation/suspension-effects-final-15-mutations-o2.log` : baseline finale
  de 15 méthodes, 1,128 s, OK ; les huit mutations sont détectées. La nouvelle
  mutation retire la garde sur les conteneurs non suivis.
- `validation/suspension-effects-final-contracts-o2.log` : 52 méthodes,
  8,750 s, OK, après ajout de la garde sur les autres conteneurs.
- `validation/suspension-effects-legacy-mutations-o2.log` : les onze mutations
  antérieures des contrats async sont détectées. Trois ancres ont été déplacées
  vers le nouveau point commun d'application des résumés ; celle de LaunchFailed
  a été précisée pour distinguer ses deux occurrences. Les fautes injectées et
  les assertions attendues conservent leur sens ; aucun oracle n'est affaibli.
- `validation/suspension-effects-runtime-regression-o2.log` : 292 méthodes,
  524,837 s, OK : 275 de la suite async/runtime, dix de nettoyage suspendu,
  sept du mécanisme Select. Le test d'instrumentation corrigé au lot précédent
  passe aussi dans cette exécution complète.
- Compilation Python des modules et tests du lot réussie.
- Liens locaux des sept documents modifiés contrôlés : aucune cible manquante.

La sélection de 94 méthodes et la suite runtime ont chargé le code avant
l'ajout final de cette garde. Celle-ci affecte seulement la disponibilité du
nouveau résumé de suspension ; les contrats de terminaison et le backend ne
la consomment pas. La baseline finale et la sélection contrats/résultats sont
exécutées sur la version contenant cette garde.

Les comptages se recouvrent et ne représentent pas des programmes distincts.
Les tests de mutation qui échouent sont les détections attendues, pas des
échecs de la version normale.

## Limites et suite

Le résumé porte sur les champs représentés par l'analyse existante, en
particulier les structures injectées à champs Int, &Int et &mut Int. Il ne
généralise pas encore tous les agrégats, les tableaux modifiés aux suspensions,
les mutex ou les signatures récursives. Les alternatives sont conservatrices,
sans corrélation complète entre chaque champ et chaque chemin.

Pour composer un Select, le futur consommateur doit aussi considérer les
branches non pollées et les branches terminées : le résumé de suspension
seul ne représente pas ces états. L'inférence des effets concurrents de handles
lancés et des fabriques opaques reste ouverte, indépendamment de l'arbitrage
sur leur destruction. Les tests ordinaires d'attente restent basés sur les
contrats de terminaison et ne sont pas rendus inutilement conservateurs.

Pas de preuve formelle, pas de résultat nouveau ASan/TSan, ni de validation
par un deuxième compilateur C. L'objectif global reste incomplet.
