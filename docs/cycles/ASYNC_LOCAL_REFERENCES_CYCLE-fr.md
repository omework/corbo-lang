[English](ASYNC_LOCAL_REFERENCES_CYCLE.md)

# Cycle — liaisons locales d’emprunts conditionnels async

## Règles et réalisation

Application de B1/B2/B3/B4/B5, D1, AS8/AS9/AS11/AS12 et RT5/RT6.
AGENTS.md, VALIDATION_GUIDELINES.md et l’index des sept brouillons ont été
relus ; B4/B5, REFERENCE_VALUES.md et les clauses async restent normatifs.
Ce cycle ne modifie aucune règle de langage.

Le contre-exemple `validation/open-async-local-reference-if.crust` est corrigé.
Une référence reçue par `let mut selected = if ...` peut survivre à yield et
être retournée. Les deux sources sont conservées dans le contrat. Le programme
enregistré affiche 30 puis 20 ; son ancien diagnostic reste historique.

Le compilateur conserve désormais les expressions de provenance des liaisons,
avec leur contexte lexical, plutôt que de reconnaître uniquement les références
issues directement d’await ou de push_new. L’inférence suit les réemprunts
explicites, les branches, blocs et relais, et réunit les cibles possibles.
Un mode mutable n’est jamais obtenu à partir d’un mode partagé.

Le cadre async matérialise la sélection dans un champ pointeur typé. La
traduction des branches vérifie un mode et un type identiques, puis réunit
leurs emprunts. Elle conserve les parents de réemprunts nécessaires. À la
sortie d’un bras, les noms intermédiaires qui disparaissent peuvent être retirés
de cet ensemble seulement parce que leurs cibles sous-jacentes y restent.
Toute cible locale qui disparaîtrait est refusée avant nettoyage du bras.
Aucune allocation cible n’est déplacée ni prolongée implicitement.

B4 ne généralise pas `let alias = reference`. La nouvelle voie exclut donc
l’initialisation directe par nom ; les réemprunts utilisent `&*r` ou `&mut *r`.
Les valeurs finales des branches, les paramètres et les retours peuvent toujours
transmettre la référence par son nom, conformément aux règles déjà retenues.
Un test négatif maintient explicitement la restriction sur l’alias implicite.

## Scénarios et indépendance des attentes

Le module final `tests/test_async_local_references.py` compte onze méthodes,
23 exécutions natives normales et 34 refus attendus par passage complet.
Ces comptes comprennent les variantes de paramètres ; ils ne signifient pas
que toutes les interactions du langage sont couvertes.

- Deux branches, modes partagé/mutable, blocs imbriqués, réemprunts locaux,
  suspension et retour ; écriture uniquement dans la cible sélectionnée.
- Réemprunt enfant mutable puis réutilisation du parent après le dernier usage ;
  accès aux deux cibles et au parent refusés avant celui-ci.
- Réemprunt partagé d’une sélection mutable ; aucune conversion silencieuse
  ni perte de la réservation exclusive d’origine.
- Branche avec retour anticipé et branche fournissant le résultat local.
- Nouvelles cases Vector<Int/u8> issues directement de push_new ou d’await,
  réemprunt du résultat puis passage à une seconde tâche qui le retourne.
  La mutation de chaque vecteur reste refusée tant que le résultat sert.
- Type, mode, annotation, let sans droit d’écriture, branche sans résultat et
  cible locale invalide refusés. Le contrôle de portée est aussi testé dans
  une fonction Void : le refus ne dépend pas de l’inférence des retours.
- Réemprunt sortant d’un bloc après disparition de son nom parent : ses deux
  cibles restent protégées, puis redeviennent accessibles après usage.
- Cases d’un tableau fixe dans une boucle avec yield, continue et break ;
  résultat final [2, 1], accès concurrents aux cases refusés.
- Résultat reçu après join : drop et transfert de chaque source refusés avant
  son dernier usage ; après usage, nettoyage et réemploi du pool réussissent.
- Modèle indépendant : sélection de deux entiers par indices explicites 0/1
  et deux tirages de graine 2097. Une liste Python détermine les valeurs finales
  attendues, sans consulter le contrat, les prêts internes ou le C généré.

Les invariants de nettoyage du cycle précédent sont réexécutés, notamment la
destruction avant join d’une tâche enfant inactive propriétaire d’une capture.
Les réservations mémoire, structures et opérations runtime restent inchangées.

## Défauts trouvés pendant le cycle

Le premier passage voisin avait une erreur sur le réemprunt partagé d’un u8.
La nouvelle détection reconnaissait cette forme mais son évaluateur était prévu
pour &Int, &mut Int et &mut u8. L’aiguillage a été corrigé : &u8 conserve le
traitement existant. `async-local-references-neighbors-initial.log` conserve
l’échec ; les régressions finales incluent le même test, maintenant réussi.

L’examen de B4/REFERENCE_VALUES a aussi conduit à retirer l’acceptation trop
large de `let alias = reference` pendant le développement. Les scénarios
positifs utilisent des réemprunts explicites et un test négatif conserve la
restriction. Il ne s’agit pas d’une décision normative nouvelle.

## Preuves exécutées

Tous les helpers natifs utilisés ici ont été inspectés : Clang C11, pthread,
-Wall/-Wextra/-Werror, UBSan fatal. CRUST_TEST_OPT sélectionne O0 ou O2.

| Trace dans validation/ | Observation |
| --- | --- |
| async-local-references-initial.log | 8 méthodes, 7,763 s, OK, développement initial |
| async-local-references-neighbors-initial.log | 25 méthodes, une erreur &u8, corrigée ensuite |
| async-local-references-O2.log | 33 méthodes, 28,625 s, OK après correction &u8 |
| async-local-references-final-O2.log | 10 méthodes, 8,681 s, OK après maintien de la restriction B4 |
| async-local-references-final-O0.log | Mêmes 10 méthodes, 10,762 s, OK |
| async-local-references-drop-transfer.log | Onzième méthode, deux variantes et huit refus, 0,889 s, OK en O2 |
| async-local-references-drop-transfer-O0.log | Même complément, 0,753 s, OK en O0 |
| async-local-references-abi-regression.log | 10 méthodes voisines, 17,301 s, OK : références retournées, tableaux de références, contrôle et nettoyage |
| async-local-references-final-regression.log | 39 méthodes, 33,853 s, OK : retours conditionnels async, push_new et expressions empruntées synchrones |

Les dix premières méthodes et le complément constituent ensemble le module
final testé aux deux optimisations, lors de passages séparés. `py_compile`
a réussi. Le diff de ce cycle est conservé dans
`validation/async-local-references.patch` pour rendre le changement inspectable.

## Mutations

Quatre copies temporaires du compilateur, quatre fautes détectées :

| Faute | Détection |
| --- | --- |
| Garder un seul emprunt après sélection | Accès interdit à une alternative accepté |
| Garder une seule provenance dans le contrat | Mutation d’un vecteur encore emprunté acceptée après relais async |
| Supprimer les parents du réemprunt | Accès à la cible accepté alors que l’enfant sorti du bloc reste utilisé |
| Inverser les pointeurs sélectionnés | Valeurs finales incorrectes dans le test natif |

Les traces initiales et finales sont dans
`async-local-references-mutations.log` et
`async-local-references-final-mutations.log`. Les quatre détections finales
sont des assertions de comportement ou de refus ; aucune n’est créditée sur
un simple crash Python ou une erreur de compilation sans diagnostic analysé.
Aucun taux global de détection n’est extrapolé.

## Limites et suite

`validation/open-async-local-reference-match.crust` reproduit le manque suivant :
recevoir la référence produite par un match sur le résultat de l’attente d’un
handle, suspendre puis la retourner. Le succès doit afficher 30 puis 20 ; le
refus actuel de provenance n’est pas normatif. Le match correspondant est déjà
possible dans le compilateur synchrone ; sa prise en charge dans le cadre async
et son inférence de provenance restent à étendre.

Ce cycle n’ajoute pas les expressions d’emprunt à toutes les positions syntaxiques,
les références générales d’agrégats, ni les résultats de boucle empruntés.
Les autres obligations N/P des sept brouillons demeurent, notamment scheduler,
threads, Select, mutex et stockage implicite. L’objectif global n’est pas atteint.

Reset reste retiré du prototype. Les tests de ce cycle ne revendiquent pas de
nouvelle couverture de reset. ASan n’a pas été relancé après l’échec de démarrage
d’un C vide documenté au cycle antérieur. Aucune validation ASan/TSan, second
compilateur, preuve formelle ni garantie générale de sûreté n’est affirmée.

## Suivi

Le match emprunté signalé ci-dessus est corrigé et validé dans
[ASYNC_MATCH_REFERENCES_CYCLE.md](ASYNC_MATCH_REFERENCES_CYCLE.md). Ce cycle
révèle et corrige aussi la double projection mutable d’un Result nommé.
