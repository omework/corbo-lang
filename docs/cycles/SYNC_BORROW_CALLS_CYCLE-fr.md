[English](SYNC_BORROW_CALLS_CYCLE.md)

# Cycle — emprunts des auxiliaires synchrones dans les états

## Portée normative et implémentation

Suite de [NATIVE_SYNC_CALLS_CYCLE.md](NATIVE_SYNC_CALLS_CYCLE.md), sans modification
des règles normatives. AGENTS.md, VALIDATION_GUIDELINES.md et l’index des sept
brouillons ont été relus ; LANGUAGE_RULES.md et ASYNC_MULTITHREAD_RULES.md lus
au cycle précédent restent applicables. B1–B5, D1/D3, L6, AS2/AS9/AS12/AS15,
MT1/MT6 et RT8 gouvernent ce lot.

Les appels synchrones depuis un bloc natif ou un état async acceptent maintenant
des paramètres et résultats &Int, &mut Int et &mut u8, en plus des scalaires
déjà raccordés. Les arguments peuvent venir des captures, de variables locales,
de cases de tableaux et d’autres résultats synchrones empruntés. Le mode et
le type restent explicites ; & sur une référence n’est pas aplati.

Le backend synchrone existant reçoit des paramètres symboliques de places,
avec leur provenance, puis génère une fonction C utilisant les pointeurs des
valeurs. Aucun Cell temporaire, copie de la cible ou nouvelle allocation ne
remplace l’emprunt. L’ABI synchrone existante utilise aussi des pointeurs C
non const pour les prêts en lecture : l’adaptation enlève le qualificatif C,
mais ne change pas le contrat Crust, qui interdit la mutation par &Int.

La vérification des appels utilise toujours FunctionContract. Le backend n’est
appelé qu’après verify ; un test intercepte sa méthode de génération et exige
que verify_program réussisse sans l’invoquer. Les résultats substituent les
reference_targets du contrat aux arguments réels, sans lire le corps à l’appel.
Un résultat conditionnel garde toutes ses cibles possibles. Les paramètres
qui ne participent pas au résultat ne sont pas arbitrairement réservés après
l’appel. Les parents des réemprunts retenus restent protégés.

## Préparation, suspension et durée de vie

Chaque argument est préparé de gauche à droite. Un prêt fourni à l’appel reste
actif pendant les arguments suivants, même si l’un se suspend. Les pointeurs
temporaires sont dans l’état stable. Un sous-appel qui retourne un scalaire
peut terminer le dernier usage d’un prêt nommé avant l’argument suivant.
L’analyse conserve les continuations extérieures et les retours au début des
boucles : une utilisation future interdit cette expiration.

Un return pendant un argument annule la préparation de l’appel. Les prêts
temporaires sont retirés avant le nettoyage des cibles propriétaires quittées ;
un pool de capacité un est ensuite réutilisable. Aucune invocation du callee
ni destruction supplémentaire ne doit apparaître sur ce chemin.

Le résultat emprunté peut être capturé directement par une tâche enfant.
Sa réservation dure pendant l’enfant et, si celui-ci le retourne, jusqu’au
dernier usage du résultat reçu. Les contrats de retour async composent aussi
les résultats des auxiliaires synchrones. Une cible locale ou reçue par
transfert ne devient pas durable parce que le retour passe par un auxiliaire.

## Écart supplémentaire corrigé

Les tests de drop ont révélé que le backend des états refusait les scalaires
locaux comme une instruction drop_value non supportée. Ce refus masquait
le contrôle d’emprunt recherché. Selon L6 déjà retenue, drop consomme désormais
les liaisons Int, Bool, u8 et char locales, sous contrôle d’accès exclusif.
Il n’émet pas de destructeur pour ces valeurs triviales. Une lecture, écriture
ou seconde consommation après drop est refusée. Le drop avant la dernière
utilisation d’un emprunt est refusé pour cette raison, plutôt que par absence
de support syntaxique. Les vues et les autres types ne sont pas réputés couverts
par ce raccordement des scalaires.

## Scénarios, oracles et défauts intermédiaires

`tests/test_sync_borrow_calls.py` contient seize méthodes : vingt-deux exécutions
Crust/C et soixante-cinq refus attendus par passage complet, avec une vérification
supplémentaire de séparation entre contrats et génération.

Les cas couvrent lecture et mutation de captures, variables locales et cases
Int/u8 ; alias dans les arguments ; lecture pendant un prêt mutable préparé ;
retours mutables et réemprunts partagés ; dernier usage au milieu des arguments ;
utilisation future dans le bloc, le parent ou l’itération suivante ; yield dans
un argument ; return pendant sa préparation ; références conditionnelles depuis
deux pools/cibles ; prêts transportés dans join ; échec de lancement ; passage
direct d’un résultat emprunté à une tâche enfant ; drop et réemploi du pool.

Les oracles sont explicitement les traces de valeurs, les destructions uniques,
les contraintes de dernière utilisation et les ensembles de cibles des fonctions
choose (deux cibles) et first (seulement la première). Ils ne consultent pas les
contrats pour décider des sorties attendues. La régression des retours synchrones
inclut le modèle existant de cibles générées ; aucun nouveau modèle général
de concurrence ou générateur aléatoire n’est revendiqué.

Les premières sondes ont relevé un refus incorrect du cas valide
pair(read(vue), &mut nombre). Le suivi de continuation entre les arguments le
corrige. Deux premiers tests employaient accidentellement le nom réservé set
pour une fonction ; les fixtures utilisent désormais write_value. Une sonde
initiale utilisait aussi .set(n), alors que le backend synchrone limite cette
méthode au littéral ; elle a été exprimée avec l’écriture *v = n déjà disponible.
Ces problèmes de fixtures sont distincts du défaut d’implémentation de drop.

Le premier journal de mutations n’est pas une preuve suffisante : le cas de
références alternatives avait encore des échecs non liés aux mutations, dus
au drop scalaire manquant. La campagne renforcée commence maintenant par exiger
une baseline complète verte. Les fautes injectées portent sur la réservation
des arguments, la perte d’une cible possible, l’oubli des usages futurs,
le mauvais pointeur rendu et la perte du prêt retourné par l’enfant. Elles
vivent dans des copies temporaires ; les tests et leurs attentes restent inchangés.

## Artefacts et limites

`validation/sync-borrows-example.crust` et le C correspondant conservent une
sonde réelle : relay rend le pointeur reçu, le natif le transmet via join,
la cible vaut 9, puis le pool est réutilisé pour 10. Les traces exigent une
destruction de chacune. Le C montre un paramètre et un résultat int *, puis
l’affectation directe de ce pointeur au résultat de l’état.

Les signatures propriétaires, les autres agrégats et les pools directement
créés dans les états restent à raccorder. &u8 en lecture utilise une autre
famille de types, encore refusée à cette frontière ; &mut u8 est couvert.
Les résultats empruntés généraux de champs ou conteneurs ne sont pas couverts
par la substitution des seuls paramètres scalaires directs. Les limites
Bool des signatures synchrones du cycle précédent restent ouvertes.

`sync-borrows-artifacts.log` conserve trois sondes : les deux premières
(transfert propriétaire et &u8) restent ouvertes ; la troisième, capture directe
du résultat synchrone par une tâche, a ensuite été raccordée et testée dans
test_returned_reference_is_captured_by_async_child. Le journal initial reste
historique. Les autres obligations des sept brouillons demeurent actives.

Pas de preuve formelle, TSan, de second compilateur ou de nouvelle validation
ASan. Les blocages ASan antérieurement consignés ne sont pas des succès.

## Résultats finaux exécutés

| Configuration | Résultat | Journal |
| --- | --- | --- |
| Régression native, Clang C11 pthread, O2, UBSan fatal | 109 méthodes, 117,219 s, OK | `validation/sync-borrows-final-regression-o2.log` |
| Lot emprunts, mêmes contrôles, O0 | 16 méthodes, 18,946 s, OK | `validation/sync-borrows-final-o0.log` |
| Mutations O2 | Baseline 16 méthodes verte, cinq fautes détectées | `validation/sync-borrows-validated-mutations.log` |
| Contrats synchrones O2, avant les dernières extensions drop/capture enfant | 130 méthodes, 64,240 s, OK | `validation/sync-borrows-contracts-o2.log` |

Les cinq mutations sont détectées par des assertions des tests inchangés.
La perte de réservation retournée par l’enfant accepte la mutation prématurée ;
pour le drop, elle reporte à tort le diagnostic sur l’usage après destruction.
Cette campagne finie ne donne pas un taux de détection général.

Suite : [&u8 partagé et provenance à travers les appels](SYNC_BYTE_BORROW_CALLS_CYCLE.md). La limite &u8 ci-dessus décrit le début de ce cycle et est levée pour les formes du cycle suivant.
