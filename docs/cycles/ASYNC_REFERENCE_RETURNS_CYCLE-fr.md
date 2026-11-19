[English](ASYNC_REFERENCE_RETURNS_CYCLE.md)

# Cycle — retours conditionnels d’emprunts async

## Portée et règles

Ce cycle applique B1/B2/B3/B5, D1, AS8–AS12 et RT5/RT6, sans changer la
sémantique normative. AGENTS.md, VALIDATION_GUIDELINES.md et l’index des sept
brouillons ont été relus ; les clauses U1, B5, AS11/12 et le brouillon 01 ont
été confrontés aux changements. L’objectif global des sept brouillons reste
ouvert. Les autres capacités non vérifiées de la matrice ne sont pas couvertes
par ce cycle.

Le contre-exemple `validation/open-async-reference-if-expression.crust` est
corrigé : `return if ...` peut rendre un &Int, &mut Int ou &mut u8 durable.
Le programme enregistré affiche maintenant 30 puis 20. Son ancien log de
refus est conservé comme trace historique.

L’expansion interne remplace le retour d’une expression if par des retours
terminaux dans ses branches, y compris else-if. L’inférence des provenances et
la génération du cadre utilisent cette même forme. Les instructions des bras,
les points de suspension et leurs scopes sont conservés. Aucune copie de cible,
allocation supplémentaire ni prolongation de sa durée de vie n’est introduite.
Chaque retour passe par les contrôles ordinaires de mode, type, durabilité et
accès, puis par le nettoyage terminal. Les contrats retiennent l’union des
cibles possibles, indépendamment du chemin réellement choisi.

Ce mécanisme concerne la position de retour. Il ne prétend pas résoudre tous
les contextes où une expression peut produire un emprunt.

## Scénarios et oracles

`tests/test_async_reference_returns.py` comporte dix méthodes : 23 exécutions
natives normales et 24 vérifications de refus par passage complet. Les nombres
comptent les variantes exécutées, pas des propriétés indépendantes.

- Les deux bras et modes partagé/mutable, avec yield dans les bras, sont
  exécutés ; l’écriture atteint seulement la cible choisie.
- Else-if, retour anticipé dans un bras et condition avec compteur : un seul
  calcul de la condition est observé.
- Cases d’un tableau fixe, nouvelles cases de Vector<Int/u8>, await dans un
  bras et résultat local issu d’await dans l’autre ; un relais supplémentaire
  conserve les provenances et le type d’élément.
- La mutation des deux sources de tableau ou vecteur reste refusée avant le
  dernier usage du résultat. Chez l’appelant synchrone, lecture, mutation et
  destruction de chaque cible sont refusées tant que le résultat doit servir.
- Les sources locales, propriétaire reçu par transfert, mauvais mode,
  entier à la place d’une référence et branche sans résultat sont refusés.
- Le nettoyage d’une capture propriétaire précède le retour de join. Son pool
  d’un seul slot peut être réutilisé dans le bras Ok, pendant que l’emprunt
  rendu reste utilisé. Une capture lue mais non retournée peut être détruite.
- Une tâche enfant inactive, créée avant le retour conditionnel et possédant
  l’allocation à nettoyer, est détruite avant ce même réemploi. Son corps ne
  s’exécute pas. La trace compte exactement une destruction de la capture.
- Un modèle indépendant choisit parmi trois entiers puis remplace seulement
  la valeur sélectionnée : indices 0/1/2 et deux tirages de graine 2041. Les
  trois valeurs finales du programme sont comparées à cette liste Python.

Les sorties attendues et traces sont définies depuis ces règles, sans consulter
les décisions internes du compilateur. Le modèle reste fini ; il ne constitue
pas une preuve générale des combinaisons de contrôle ou d’aliasing.

## Exécutions

| Trace dans validation/ | Résultat exécuté |
| --- | --- |
| async-reference-returns-initial.log | 8 méthodes, 9,448 s, OK, Clang O2 + UBSan fatal |
| async-reference-returns-cleanup-fixed.log | 1 méthode, 1,077 s, OK, nettoyage direct et capture non retournée |
| async-reference-returns-O0.log | 9 méthodes, 17,467 s, OK, Clang O0 + UBSan fatal |
| async-reference-returns-regression.log | 43 méthodes, 85,039 s, OK ; les 9 méthodes initiales, push_new, erreurs builtin et cinq scénarios async voisins |
| async-reference-returns-child-cleanup.log | Dixième méthode ajoutée après la mutation survivante, 1,461 s, OK, O2 + UBSan fatal |
| async-reference-returns-child-cleanup-O0.log | Cette même méthode, 1,962 s, OK, O0 + UBSan fatal |

Les neuf premières méthodes et le complément couvrent ensemble le module final
aux deux optimisations ; les durées ci-dessus proviennent de passages séparés.
L’inspection du helper `AsyncRuntimeTests.run_c_oracle` confirme qu’il utilise
aussi CRUST_TEST_OPT et UBSan fatal : les 43 méthodes de cette régression
native ont donc la configuration O2 + UBSan, contrairement au helper
synchrone historique utilisé dans le cycle précédent.
`py_compile` a aussi réussi sur les sources et scripts modifiés ; les liens
locaux des quatre documents modifiés ont été vérifiés.

## Préparation des tests et mutations

Le premier test de destruction d’une capture non retournée tentait un drop
parent → enfant sans transfert d’entrée. Ce programme était invalide. L’ajout
de `-> ignored;` respecte la règle existante ; les traces initiale et corrigée
sont conservées dans `async-reference-returns-cleanup*.log`. Aucune règle n’a
été assouplie pour le test.

Trois fautes sont injectées dans des copies temporaires du compilateur :

| Faute | Observation |
| --- | --- |
| Intervertir les bras lors de l’expansion | Valeur finale incorrecte dans les tests natifs, détectée |
| Ne garder qu’une provenance dans le contrat | Accès interdit à la seconde source accepté, détecté |
| Forcer le chemin de nettoyage à celui d’une tâche inactive | Capture de la tâche enfant non libérée, pool d’un slot épuisé, détecté après renforcement du scénario |

La troisième mutation a d’abord survécu : le scénario ne possédait qu’une
capture directe, pour laquelle le nettoyage d’une tâche inactive et celui de
la tâche terminée étaient équivalents. Le scénario ajouté crée une tâche enfant
inactive qui reçoit la capture. Le nettoyage terminal doit détruire cet enfant,
alors que le nettoyage initial n’en connaît pas l’existence. Le compilateur
normal passe ; le mutant échoue avec `pool capacity exceeded` sur les deux
bras. L’oracle n’a pas été modifié pour s’aligner sur le mutant.

Traces : `validation/async-reference-returns-mutations.log` (deux détectées,
une survie initiale) et `validation/async-reference-returns-cleanup-mutation.log`
(détection ciblée après ajout). Aucun taux global de détection n’est déduit.

## Limites et contre-exemple suivant

La liaison locale d’un résultat conditionnel reste refusée :
`validation/open-async-local-reference-if.crust` et son log. Ce programme fait
`let mut selected = if ...`, suspend puis retourne selected. Sa cible est
injectée et durable ; le refus n’est pas normatif. L’expansion de retours
terminaux ne traite pas ce contexte et l’analyse des alias locaux doit être
étendue. Les matchs produisant un emprunt dans les cadres async, les enums
et agrégats généraux, ainsi que les autres obligations N/P restent ouverts.

Reset n’est pas réintroduit. Le lot précédent couvre son interdiction publique
et deux contrôles dans le profil historique ; ce lot async ne revendique pas
une nouvelle validation de reset.

ASan n’a pas été relancé après le blocage de démarrage reproduit par un C vide
au cycle précédent. Les tests natifs nouveaux utilisent Clang C11, pthread,
-Wall/-Wextra/-Werror, UBSan fatal. Aucun succès ASan/TSan, second compilateur,
preuve formelle ni garantie générale de sûreté n’est revendiqué.

## Suivi

La liaison locale conditionnelle signalée ci-dessus est corrigée et testée dans
[ASYNC_LOCAL_REFERENCES_CYCLE.md](ASYNC_LOCAL_REFERENCES_CYCLE.md).
Le match produisant un emprunt dans le cadre async reste un écart distinct.
