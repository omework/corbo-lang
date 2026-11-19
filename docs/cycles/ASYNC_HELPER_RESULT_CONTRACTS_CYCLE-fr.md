[English](ASYNC_HELPER_RESULT_CONTRACTS_CYCLE.md)

# Résultats empruntés à travers les contrats sync et async

Cycle du 7 novembre 2026. Application des règles existantes B4c/B4e,
ST8/ST12/ST14, B1/B2/B4a, AS12/AS13 et MT3. Aucune règle normative changée.

## Corrections

Le contre-exemple `validation/open-async-helper-result-sync-contract.crust`
est désormais admis et affiche 21, 8, 21. Le résumé d'un helper synchrone
est disponible à la demande pendant l'inférence des résultats async, avant
l'assemblage des contrats complets d'effets et contraintes. Ce résumé est
mémorisé par l'analyseur habituel. Une dépendance cyclique ne reçoit pas un
résumé fictif ; elle reste refusée. Les corps et les appels sont toujours
vérifiés par les passes existantes.

La projection se conserve aussi lorsqu'une fonction fabrique et retourne
le handle. La capture réserve encore l'argument complet avant l'attente ;
le résultat de join ne réserve ensuite que ses chemins et capacités.

Une autre fonction peut recevoir le handle, le joindre et rendre la référence.
La vérification symbolique construit désormais les dépendances des champs de
ses captures, avec des clés distinctes par capture. La classification d'un
résultat projeté découle également de ses origines et chemins, même si le
marqueur de représentation scalaire n'a pas traversé un relais. Les signatures
ne deviennent pas un moyen d'effacer les cibles ou l'ascendance des emprunts.

Le C du cas initial est conservé dans
`validation/async-helper-result-contract-fixed.c`. Les diffs d'implémentation
sont `validation/async-helper-contracts-{async_lowering,crust,results}.py.patch`.

## Validation exécutée

- `async-helper-contracts-final-o0.log` : neuf méthodes, 23,797 s, OK.
- `async-helper-contracts-complete-o2.log` : 24 méthodes, 33,762 s, OK,
  avant le dernier test conditionnel et les corrections du paramètre handle.
- `async-helper-contracts-full-mutations-o2.log` : baseline finale de huit
  méthodes réussies, neuf exécutions C (dont un échec de lancement injecté),
  quinze programmes invalides contrôlés par check et compilation (30 contrôles).
- Modèle indépendant : 24 combinaisons, 18 exécutions et six refus. Le même
  oracle de chemins et derniers usages est exercé via helper → enfant async
  → join → résultat synchrone ; seul le générateur de programme change.
- `async-helper-contracts-final-regression-o2.log` : 67 méthodes, 52,559 s,
  66 réussites et une erreur historique U1, détaillée ci-dessous.
- `async-helper-contracts-fields.log` : 56 méthodes historiques sur les champs
  partagés/mutables, 42,193 s, OK.

Les nouveaux harnais utilisent Clang C11 pthread, UBSan fatal, O0/O2 selon
le journal. Les méthodes historiques de test_crust ignorent CRUST_TEST_OPT et
n'ajoutent pas d'option d'optimisation explicite, même dans la sélection dont
le nom contient o2. Aucun résultat ASan/TSan ou second compilateur ajouté.

Les six mutations finales sont détectées : contrat de helper indisponible,
chemin effacé, projection perdue dans une fabrique, alternative omise,
dépendances de capture symbolique omises, classification projetée omise.
L'alternative omise fait accepter un accès interdit ; les autres fautes sont
détectées notamment par le refus de programmes valides. Ce n'est pas une
mesure universelle de détection ni une preuve de sûreté. La survivante du
cycle précédent n'est pas reclassée par ces résultats.

## Échecs conservés

`async-helper-contracts-initial-o0.log` : deux erreurs, projection de fabrique
manquante et fixture qui lisait une cible avant le dernier usage de son porteur.
La fixture détruit maintenant le porteur avant de relire la cible et de vérifier
le réemploi du pool. Le passage ciblé suivant réussit.

Les journaux handle-parameter, handle-parameter-recheck et handle-parameter-final
conservent les étapes refusées : cibles symboliques absentes, puis contrat et
classification projetée incomplets. Le journal handle-parameter-resolved-o2
confirme la correction ; le test est inclus dans les passages finaux.
La première campagne de mutations conserve une ancre ambiguë ; l'ancre du
contrat de référence a été précisée avant la campagne complète.

La fixture historique `test_same_input_preserves_pending_export_and_reception_order`
recevait `other` sans jamais l'utiliser. L'échec U1 a été reproduit dans une
copie du compilateur restaurée aux snapshots d'avant ce lot :
`async-helper-contracts-results-baseline.log`. `print(other)` a été ajouté,
avec la sortie attendue correspondante ; l'ordre de destruction attendu
reste exactement `data` puis `other`. Le contrôle corrigé réussit dans
`async-helper-contracts-results-fixture-recheck.log`. Le journal initial de
67 méthodes n'est pas présenté comme entièrement vert.

## Limites

Les projections prises en charge restent celles des champs Int et des
réemprunts &mut Int, avec leurs modes déjà disponibles. Le retour détaché d'un
champ partagé, les graphes plus généraux, les mises à jour de champs dans
les états et les autres lots de l'objectif restent ouverts. La récursion des
contrats de résultats empruntés n'est pas ajoutée. Les modèles sont finis et
les tests n'explorent pas tous les ordonnancements.

La régression native élargie est terminée : 278 méthodes, 224,718 s, OK,
dans `validation/async-helper-contracts-native-o2.log`. Elle a commencé avant le
dernier complément sur les paramètres handles ; les passages finaux ciblés
et les régressions de contrats/champs couvrent ce complément.
La baseline finale des six mutations compte huit méthodes, 9,202 s, OK.
La fixture historique corrigée a été réexécutée seule en 0,314 s, OK.
