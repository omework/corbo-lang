[English](CELL_REFERENCE_BRIDGES_CYCLE.md)

# Emprunts stockés par les auxiliaires synchrones des tâches

## Périmètre et changement

Aucune règle normative modifiée. B1/B2/B4, ST8/ST10–ST13, AS12/AS13 et
L1/L2 exigent de conserver la cible, ses dépendances et son identité lorsqu'un
auxiliaire stocke un emprunt dans un objet. Le programme conservé dans
`validation/open-async-local-stored-reference.crust` était accepté par le
vérificateur, mais refusé à l'émission C : son auxiliaire recevait un pointeur
Int brut alors que le champ référence attendait le descripteur Cell de la cible.
Le journal `cell-reference-bridges-recorded-baseline.log` reproduit cet écart
avec le compilateur antérieur. Le journal `cell-reference-bridges-recorded-final.log`
montre désormais la valeur 7 et le nettoyage de la vue puis de la cible.

Le contrat de résultat comporte maintenant `stored_reference_parameters`.
Cette exigence concerne également les stores temporaires dans des objets locaux,
même si aucun champ extérieur n'est modifié au retour. Elle traverse les relais
synchrones, les méthodes et les fonctions qui ne retournent jamais. L'inférence
ne confond pas cette exigence de représentation avec un effet final sur les champs.

Les bridges concernés reçoivent le Cell existant. L'état async le retrouve
depuis une allocation locale, une capture transférée ou un champ référence d'un
porteur. Plusieurs provenances sont sélectionnées en comparant le pointeur déjà
évalué aux cibles suivies. Il n'y a ni copie de la cible, ni déplacement, ni
descripteur artificiel construit autour d'un pointeur brut. Les autres arguments
empruntés conservent leur ABI précédente. Les prêts préparés restent protégés
pendant l'évaluation des arguments suivants.

Deux contre-exemples supplémentaires ont exposé un C incorrect pour les
auxiliaires divergents : la propriété de non-retour manquait sur le bridge,
puis sur la fonction synchrone spécialisée déclarant un résultat Int. Les deux
déclarations utilisent désormais `_Noreturn`; une garde fatale termine le corps
si cette propriété était violée. Le test compile les corps divergents avec une
entrée C vide de substitution : il ne prétend pas exécuter leur boucle infinie.

## Vérification exécutée

Commandes ciblées finales :

```
CRUST_TEST_OPT=-O0 PYTHONPATH=tests python3 -m unittest test_cell_reference_bridges -v
CRUST_TEST_OPT=-O2 PYTHONPATH=tests python3 -m unittest test_cell_reference_bridges -v
```

Quatorze méthodes réussissent à O0 (14,271 s) et O2 (14,470 s), journaux
`validation/cell-reference-bridges-final-o{0,2}.log`. Le harnais compile le C11
avec Clang, pthread, avertissements fatals et UBSan fatal. Les cas comprennent
identité d'adresse avant/après suspension, cible mutable, réemprunts nommés,
choix conditionnels, argument non premier, références retournées, destruction
prématurée refusée, réemploi d'un pool de capacité un, thread natif et refus de
lancement injecté. Les références vers une cible non représentable restent
diagnostiquées comme une limite du backend, pas comme une règle normative.

Un modèle indépendant énumère seize scénarios : dernière utilisation avant ou
après les destructions, quatre ensembles de cibles détruites et deux branches.
Dix programmes sont exécutés avec la valeur attendue, six sont refusés par
`verify_program` et `compile_source`. Le modèle utilise les ensembles de cibles
possibles, sans consulter l'analyse du compilateur.

Le test de remplacement d'un champ extérieur exécute un bridge généré depuis
un appelant C synchrone déjà vérifié. Il prouve cette frontière C précise ; il
ne prouve pas la prise en charge du même remplacement dans une tâche complète.

Régressions du lot, sélections qui se recouvrent :

- 111 méthodes natives/bridges, 111,037 s, avant les correctifs finaux de
  divergence : `cell-reference-bridges-regression-o2.log`.
- 159 méthodes synchrones : un ancien test violait U1 en n'utilisant jamais
  `old`; les 158 autres réussissent. Même erreur reproduite sur le compilateur
  antérieur préchargé depuis sa copie isolée, journal
  `cell-reference-bridges-provenance-baseline-confirmed.log`. Le premier essai
  de reproduction n'isolait pas correctement les imports et ne sert pas de preuve.
- Le test ajoute la lecture explicite de `old`, attend sa sortie 99 puis 20,
  et conserve les assertions de destruction unique. Les 24 méthodes de
  provenances passent en 34,563 s : `cell-reference-bridges-provenance-final.log`.
- 76 méthodes de contrats/fonctions/features/résultats imbriqués, 46,143 s,
  avant le dernier correctif C : `cell-reference-bridges-final-contract-regression.log`.
- Après le dernier correctif, 45 méthodes de fonctions et expressions
  divergentes passent en 32,641 s : `cell-reference-bridges-divergence-regression.log`.
- Compilation Python des modules modifiés et des nouveaux tests réussie.

Les journaux intermédiaires conservent les erreurs de fixtures initiales
(adresse directement imprimée dans l'état et compilation réutilisant le même
objet Compiler), puis les deux défauts C de divergence. Les attentes de sûreté
n'ont pas été supprimées pour obtenir les passages finaux.

`python3 tests/run_cell_reference_bridge_mutations.py` détecte huit fautes
dans des copies temporaires : trois pertes d'exigences de contrat, sélection
de la mauvaise cible, suppression du paramètre Cell du bridge, ABI incorrecte
de l'argument, absence de non-retour sur le bridge et sur la fonction ordinaire.
Journal final : `cell-reference-bridges-final-mutations-eight.log`. Les stades
sont distingués : contrat, rejet d'un programme valide, compilation C ou valeur
erronée à l'exécution. Ce ne sont pas huit violations mémoire observées au runtime,
ni une mesure générale du taux de détection.

## Restant et limites

Mise à jour : les captures Int d'allocations sont désormais raccordées par
le lot [descripteurs capturés](CAPTURED_CELL_DESCRIPTORS_CYCLE.md). Le paragraphe
suivant conserve la frontière atteinte à la fin du présent cycle.

Les références Int capturées sous forme de pointeur brut et les éléments inline
n'ont pas encore le descripteur durable nécessaire au stockage dans ces champs.
La généralisation aux autres types et agrégats reste ouverte. Le refus async
des auxiliaires modifiant les dépendances de champs extérieurs reste actif : il
faut raccorder les effets aux états, aux handles et à l'appelant après attente.
Le cycle précédent d'inférence n'était pas une implémentation de cette propagation.

Pas de nouvelle preuve ASan/TSan, ni de comparaison avec un compilateur C
indépendant, ni de preuve formelle. Pas de passage de toute la suite globale.
Les patches du lot sont conservés sous `validation/cell-reference-bridges-*.patch`.
L'objectif d'implémentation de l'ensemble des règles reste ouvert.
