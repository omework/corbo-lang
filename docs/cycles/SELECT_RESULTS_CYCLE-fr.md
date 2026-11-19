[English](SELECT_RESULTS_CYCLE.md)

# Select — résultats typés et effets de champs

## Portée et implémentation

Ce lot complète [Select source](SELECT_SOURCE_CYCLE.md), sans changer les
règles normatives SL1, AS4/AS12/AS16, B1/B2/B4/B5, D1/D3 et U1.
AGENTS.md et VALIDATION_GUIDELINES.md sont suivis.

Le programme `validation/open-select-owned-result-field.crust` était refusé
par les deux entrées du compilateur : les effets de champs des enfants
n'étaient pas raccordés à leurs résultats propriétaires. Le journal
`validation/select-results-before.log` conserve ce refus. Après correction,
le programme affiche 9, 2, 17 : résultat gagnant, champ laissé par la perdante,
puis allocation dans le slot récupéré. Les deux allocations x sont détruites
exactement une fois.

L'analyse conserve maintenant le contrat typé du résultat propriétaire ou
emprunté avec les modifications de champs. La composition commune aux attentes
directes, handles et Select réunit les sources des allocations et les cibles
des vues. Un échec de lancement conserve les champs initiaux et ne fournit
aucune cible de résultat réussi. Les scalaires, tableaux simples et enveloppes
d'erreurs sans référence utilisent leurs modes typés. Le registre de ces modes
reste dynamique pour les enveloppes enregistrées après import.

Le backend accepte ces effets seulement si le résumé est complet. Les formes
inconnues ne deviennent pas des effets vides. Un diagnostic de résumé incomplet
inclut désormais sa cause, notamment le transfert depuis un pool local.

## Cas exécutés et oracles

Les douze méthodes de `tests/test_select_results.py` couvrent :

- Résultats alloués Int, String, Vector<Int> et Vector<u8>, retour au parent,
  deux sources possibles, destruction unique et réemploi des pools.
- Gagnante modifiant un champ avant de terminer ; perdante modifiant un champ
  avant yield. Ces deux situations ont des oracles distincts.
- Vues &str, &u8, &[Int], &mut [Int], &mut [u8], et Result<&str,SliceError>,
  encore liées à leurs sources après drop de Select.
- Résultats de conversion entière et tableaux fixes avec effets de champs.
- Relais direct du résultat emprunté ; résultat propriétaire de handle avec
  deux positions d'échec de lancement injectées.
- Refus d'une destruction ou mutation prématurée, d'un retour depuis un pool
  local et de résultats propriétaires/faillibles laissés sans usage explicite.

Un modèle indépendant énumère neuf couples de nombres de yield (0 à 2).
Deux compteurs déterminent le gagnant sans consulter le compilateur. Les
exécutions comparent ce gagnant, les destructions des branches effectivement
pollées et le réemploi de deux pools de capacité 1. Les assertions de contrats
contrôlent séparément la présence des sources possibles.

Le passage final ciblé O0 compte 27 exécutions natives, dont deux refus de
lancement injectés, et 20 programmes refusés par chacune des deux entrées
verify_program et compile_source (40 contrôles de refus).

Configuration native : Clang C11, pthread, Wall/Wextra/Werror,
Wno-unused-function, UBSan fatal, O0 ou O2 selon le journal. Les modèles sont
finis ; aucune preuve générale, couverture exhaustive ni mesure de performance
n'est revendiquée. ASan et TSan ne sont pas validés par ce lot.

## Chronologie des vérifications

Tous les journaux sont dans `validation/` avec le préfixe `select-results-`.

| Journal | Résultat et version exercée |
| --- | --- |
| baseline-initial-o0.log | 80 méthodes, 22,757 s, OK ; avant les derniers ajustements du registre et des diagnostics |
| initial-o0.log | 31 méthodes, deux échecs de diagnostic ; 24 méthodes importées accidentellement incluses, import corrigé ensuite |
| owned-boundary-initial.log | Même refus attendu, diagnostic trop général ; cause du résumé ajoutée ensuite |
| targeted-o0.log | 7 méthodes, 7,410 s, OK |
| expanded-initial-o0.log | 9 méthodes, un échec de fixture : syntaxe de tranche mutable non retenue |
| collections-initial-o0.log | 10 méthodes, même fixture en échec ; collections propriétaires passent |
| expanded-o0.log | 10 méthodes, 10,072 s, OK ; fixture utilisant split_at_mut validé |
| views-o0.log | 11 méthodes, 22,481 s, OK |
| final-o0.log | 12 méthodes, 16,230 s, OK ; assertions U1 incluses |
| final-o2.log | 12 méthodes, 15,905 s, OK ; assertions U1 incluses |
| regression-o2.log | 122 méthodes, 120,627 s, OK ; code final, dix méthodes nouvelles à ce moment |
| runtime-regression-o2.log | 275 méthodes, 510,653 s, OK ; processus terminé avec code 0 |

Les extensions des tests après le lancement des deux régressions n'ont pas
modifié le compilateur. Les passages finaux ciblés couvrent ces extensions.

## Mutations

`tests/run_select_result_mutations.py` modifie des copies temporaires : effacer
les sources propriétaires, conserver seulement la première source, perdre les
cibles des vues, oublier les écritures d'une terminaison propriétaire, refuser
à nouveau les parents à résultat propriétaire. Les deux gardes visées par la
dernière mutation sont comptées explicitement.

`select-results-mutations-initial-o2.log` : baseline dix méthodes, quatre
mutations détectées et une survivante. L'oubli des écritures de terminaison
propriétaire survivait parce que le test ne regardait qu'une perdante suspendue,
dont le résumé de préfixe gardait l'écriture. Un test de gagnante immédiatement
terminée et une assertion de son contrat ont été ajoutés, sans modifier l'oracle.

`select-results-mutations-final-o2.log` : baseline douze méthodes, 24,222 s, OK,
cinq mutations détectées. Cette campagne précède seulement les deux assertions
supplémentaires U1, qui passent dans les tests finaux. Les mutations précédentes
restent détectées : onze de terminaison (`completion-mutations-o2.log`), huit
de contrats Select (`contract-mutations-o2.log`) et huit de suspension
(`prefix-mutations-o2.log`). Deux ancres suivent désormais l'union commune
des cibles ; les fautes injectées et les oracles ne changent pas.

## Limites et travail restant

Les agrégats empruntés généraux, les effets suspendus des tableaux de références,
porteurs A<T>, vecteurs de références et enums ne sont pas généralisés ici.
Les unions restent conservatrices, sans corrélation générale entre gagnant et
effets. Les résumés récursifs inconnus restent inconnus. Une attente de tâche
propriétaire dont seul LaunchFailed peut continuer demandait encore un examen
spécifique : absence de succès ne doit pas devenir origine inventée. Ce cas
est depuis traité dans le [cycle suivant](ASYNC_FAILURE_ONLY_RESULTS_CYCLE.md),
avec preuve d'absence distincte d'un résumé inconnu.

Le test d'échec de lancement porte sur un handle ordinaire attendu. Il ne
résout pas l'arbitrage d'une perdante Select possédant un handle lancé, ni celui
d'une instance inactive capturant un tel handle. L'API publique du scheduler
et les autres familles de types restent ouvertes. Ce lot ne clôt pas l'objectif
global d'implémentation.
