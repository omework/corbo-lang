[English](CONSUMING_JOIN_MATCH_CYCLE.md)

# Cycle — Match consommant des résultats de join

## Règles et défaut initial

F2, U1, T1/T6, H1–H3, ST17/ST18, B1–B5, AS8–AS15 et MT7 restent
inchangées. AGENTS.md et l’index des brouillons ont été relus, ainsi que les
règles pertinentes. VALIDATION_GUIDELINES.md a été lue intégralement dans le
travail continu, puis consultée à nouveau dans ce lot. Aucun arbitrage nouveau
ni modification normative.

Le parser traitait tout `match (-> résultat)` à bras Ok/Err comme un résultat
de replace/try_push. Un Result de join était donc refusé à tort, même avec un
simple Int. Les preuves initiales sont conservées dans
validation/consuming-join-match-baseline.log et les deux fixtures
open-consuming-join-match.crust et open-async-inline-public.crust.

## Implémentation

Le match consommant nommé produit désormais la représentation générale du
Result. Le vérificateur et l’abaissement async choisissent ensuite les
opérations adaptées au type du sujet. Le résultat propriétaire est consommé,
son ancien nom devient inutilisable et les contraintes du payload sont
conservées dans le bras qui le reçoit.

Les résultats de replace/try_push conservent leurs deux provenances : Err
peut y contenir une allocation, alors que l’Err d’un join contient une erreur
runtime. Les motifs `_` sont vérifiés selon le contenu du bras. Ok(())
consomme la réservation de try_push avant l’exécution du bras, y compris
pour les vecteurs de références mutables. Le runtime C reste inchangé. Dans le C conservé du cas public, le bras Ok
retire la garde du Result avant de remettre son pointeur au receveur ;
vector_remove écrit dans le stockage local du Point. Le nettoyage détruit
le vector et le Point séparément, puis le pool peut être réutilisé. Le bras
Err ne lit que le statut déjà sauvegardé. Cette inspection complète les tests
de sortie et de réemploi sans constituer une preuve sur tous les chemins.

Le traitement générique a également révélé un manque dans le placement :
une fonction retournant soit le Point local d’un Result reçu, soit un Point
fraîchement construit était refusée. Le contrat reconnaît désormais le
paramètre comme local lorsque ses sources le prouvent, et la planification
conserve les couches Result pour trouver les seuls constructeurs frais à
placer chez l’appelant. Elle ne transforme pas une allocation A<Point> en
valeur locale et ne déplace pas un objet existant.

## Cas ciblés et résultats

Sept nouvelles méthodes dans tests/test_consuming_join_match.py :
**12 exécutions C réussies**, dont trois avec échec de lancement injecté,
et **7 programmes refusés aux deux entrées** verify_program et compile_source.

- Les deux programmes minimaux initiaux : Int et A<Vector<Point>> transmis
  par handle public puis relais Result.
- Payload A<Int> reçu par match expression, destruction puis réemploi du
  pool de capacité un ; ancien Result et motifs écartant le propriétaire
  refusés.
- Err nommé, Err(_) et variante entière `_` pour l’erreur runtime ; échec
  de lancement injecté et réemploi du pool ensuite.
- Référence partagée reçue dans Ok : mutation et drop de la cible refusés
  avant son dernier usage, mutation permise après le match.
- Point local retourné par un relais avec une construction alternative dans
  Err ; succès et échec de lancement exécutés, signature A<Point> refusée.
- Résultat Void avec Ok(()) en synchrone et en async.
- Résultat propriétaire attendu dans une tâche, yield dans Ok puis lecture
  et drop ; tentative de réimporter le Result consommé refusée.

Passage ciblé final O0/UBSan : **8 méthodes, 6,661 s, code 0**, journal
validation/consuming-join-match-targeted-eighth.log. Il comprend les sept
nouvelles méthodes et le test existant des wildcards des échanges de handles.
Les deux tests existants replace/try_push de références mutables ont aussi
réussi dans targeted-fourth (8 méthodes au total à ce stade, 7,107 s).

Trente-cinq tests d’échanges synchrones et async ont réussi avant les derniers
raccordements des motifs unitaires/wildcards : exchanges-third.log,
47,773 s. Ils sont inclus dans la régression finale ou couverts par les mêmes
modules rejoués. Les attentes de résultats et de destruction viennent des
règles et des oracles existants, pas de la sortie du compilateur.

Compilation native : Clang C11, pthread, Wall/Wextra/Werror, UBSan fatal.
Les refus statiques ne sont pas exécutés nativement.

## Défauts corrigés pendant le lot

Les premiers raccordements génériques ont perdu la position d’une expression
synthétique, puis tenté de copier un résultat mutable. Les positions sont
rattachées à l’expression d’origine et les résultats non Copy du match sont
consommés explicitement. Le diagnostic d’un replace sans -> a été conservé.

Un test d’usage après consommation atteignait d’abord la règle d’entrée de
scope. Il utilise désormais l’entrée explicite `r ->;` pour exercer le refus
de réutilisation du résultat consommé, sans contourner les règles de scope.

La consommation du résultat dans Err avait déjà invalidé sa charge avant
le traitement du wildcard. Ce traitement ne relit maintenant aucune charge
morte. L’absence de motif Ok explicite est distinguée de Ok(()) pour préserver
le wildcard valide de la variante unitaire de try_push.

Les journaux targeted-first à seventh et exchanges-first/second gardent les
échecs intermédiaires. Ils ne sont pas présentés comme des validations réussies.

## Régression et limites

Régression O2/UBSan : **223 méthodes couvertes avec succès**. Le premier
processus a terminé 216 méthodes avec succès, puis a rencontré ENOSPC
(disque plein) et s’est arrêté avec le code 120, sans résumé final complet.
Les sept méthodes restantes ou touchées ont été rejouées : **7 méthodes,
11,103 s, code 0**, dans consuming-join-match-regression-resume.log.
Le compilateur et le test ciblé (31 empreintes) sont identiques dans les deux
passages. Il ne s’agit pas d’un passage unique de 223 méthodes avec code 0.

La reprise est documentée dans consuming-join-match-regression-recovery.json
et resume-selection.txt. Une première génération de cette liste a échoué
sur le format des identifiants unittest ; aucun test n’a alors été exécuté
(code 5, journal resume-selection-error). Après correction de l’extraction,
la sélection contient exactement les identifiants sans succès final enregistré.

Seuls les caches Python régénérables des anciens répertoires temporaires
/private/tmp/crust* ont été supprimés : 7 053 fichiers __pycache__/*.pyc,
1 024 240 327 octets, inventaire consuming-join-match-cache-cleanup.json.
Les sources, snapshots, fixtures et journaux ont été conservés.
Sélection : validation/consuming-join-match-test-selection.txt ; journal :
validation/consuming-join-match-regression.log. Elle couvre les contrats publics,
Result imbriqués, retours locaux et catégories de stockage, échanges et prêts,
ainsi que les vecteurs async du lot précédent.

Cette sélection ne prouve pas la sûreté générale ni la complétude du langage.
Les autres intégrations de Vector<T>, les graphes async généraux, le placement
anticipé général et les gardes mutex restent ouverts. Aucun modèle indépendant
nouveau, campagne aléatoire ou campagne de mutations n’a été ajouté ; les
oracles et modèles présents dans les tests sélectionnés restent ceux existants.
Reset n’est pas réintroduit ; les tests historiques ciblés qui l’utilisent
conservent leur profil legacy explicite.

Reproduction : snapshot /tmp/crust-before-consuming-join-match ; patch et
empreintes validation/consuming-join-match.patch et consuming-join-match-changes.json.
C du cas public : validation/consuming-join-match.c, obtenu depuis la fixture
open-async-inline-public.crust précédemment refusée.
