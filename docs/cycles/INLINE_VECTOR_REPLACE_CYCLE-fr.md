[English](INLINE_VECTOR_REPLACE_CYCLE.md)

# Cycle en cours — Replace des structures en ligne

## Règles et périmètre

VE1–VE3, H1, U1, B1–B5, T4/T5/T6, ST15/ST17/ST18 restent inchangées.
AGENTS.md, VALIDATION_GUIDELINES.md et l’index des brouillons ont été relus.
La spécification complète a été lue dans le travail continu ; les règles de
vectors et les interactions mémoire pertinentes sont reprises pour ce lot.
Aucune nouvelle sémantique ni décision normative.

Ce checkpoint historique raccorde les opérations locales synchrones et les fonctions
qui effectuent le remplacement puis consomment le résultat. Il ne clôt pas
replace : le retour par contrat et l’intégration async restent ouverts.

## Baseline et réalisation

Snapshot initial : `/tmp/crust-before-inline-vector-replace`.
`validation/inline-vector-replace.crust` est le cas VE3 minimal, conservé avec
son refus aux deux entrées dans `-baseline.log`. Il s’exécute maintenant avec
la sortie attendue 7 puis 9.

Une valeur entrante T doit être transférée explicitement et ne doit plus être
empruntée. A<T> ne se substitue pas implicitement à T. L’indice est évalué avant
l’entrant, puis l’accès exclusif au vector est contrôlé. Le C réutilise le
porteur local de l’entrant : vector_replace échange ses octets avec ceux de la
case, ou ne les modifie pas si l’indice est invalide. Le résultat possède ce
porteur. Les cibles des champs A<T> gardent leur adresse ; seules leurs
responsabilités de nettoyage changent de porteur.

Le résultat est typé Result<T,T>. Son succès porte les champs de l’ancienne
case ; son erreur porte ceux de l’entrant. L’ancienne variable entrante est
invalidée sans détruire les champs transmis. Le layout de nettoyage du vector
est conservé pour les champs propriétaires. Une position constante connue est
mise à jour précisément ; les positions inconnues restent conservatrices.

Les types de résultats distinguent Result<T,T> et Result<A<T>,A<T>>. Le
reconnaisseur prépare également leur identification dans les wrappers typés,
mais cette reconnaissance ne prouve pas leur intégration complète aux contrats.
Le partage du code d’évaluation d’un entrant entre push et replace évite une
seconde implémentation de leurs contraintes de transfert.

## Défauts rencontrés et ciblé

Le premier ciblé exécutait six méthodes et signalait six échecs/sub-échecs :
les diagnostics sans flèche étaient génériques, et la branche de succès d’un
indice statiquement invalide n’était pas marquée sans charge. Cette branche
inaccessible tentait ensuite d’utiliser un graphe de champs absent. Les sources
de sa charge sont désormais vides et le diagnostic de transfert est explicite.
Deuxième ciblé : six méthodes, 3,924 s, code 0.

Un appel de fonction pour construire l’entrant a ensuite révélé deux réservations
mutables temporaires du même vector. Replace conserve sa réservation pendant
l’évaluation de l’indice et de l’entrant ; l’évaluation commune n’en ajoute pas
une seconde. Le troisième ciblé garde cet échec ; le quatrième passe.

`validation/inline-vector-replace-targeted-fourth.log` : **sept méthodes,
4,737 s, code 0**, O0/UBSan. **13 exécutions C réussies**, **huit variantes
invalides** contrôlées aux deux entrées verify_program/compile_source.

Cas admis : succès, indices négatif/hors limite, résultat annoté, transfert
nommé/frais, champs propriétaires et empruntés, lecture après drop du vector,
nettoyage unique des descendants, réemploi de deux slots, structures vides,
drop direct, fonction consommant le résultat et ordre d’évaluation observable.
Cas refusés : T/A<T>, flèches manquantes, ancien nom après transfert, entrant
encore emprunté, motif propriétaire ignoré et mutation d’une cible avant le
dernier usage de son emprunt. Reset reste retiré du profil courant.

## Régression

Régression sélectionnée terminée : **142 méthodes, 111,163 s, code 0**,
O2/UBSan, dans `validation/inline-vector-replace-regression.log`. Les 43 empreintes
compilateur/tests sont inchangées pendant le passage. La sélection comprend
pop, push/remove et champs des structures en ligne, leurs usages async existants,
ainsi que les échanges propriétaires typés synchrones/async.
Sélection et empreintes : `validation/inline-vector-replace-selection.json`
et `-start.json`. Diff : `validation/inline-vector-replace.patch` ; manifeste :
`-changes.json`. Cette réussite ne clôt pas les écarts de replace ci-dessous.
Le C de la fixture minimale est conservé dans `validation/inline-vector-replace.c`.
Le harnais utilise C11, pthread, Wall/Wextra/Werror, UBSan fatal et O0/O2.

## Suite du checkpoint

Les retours synchrones et paramètres Result<T,T> ont depuis été raccordés et
exercés dans [le cycle des contrats](INLINE_VECTOR_REPLACE_CONTRACTS_CYCLE.md).
La fixture -replace-return.crust ci-dessous décrit donc le refus initial,
conservé pour traçabilité. L'intégration async demeure ouverte.

## Écarts au moment du checkpoint et limites

`validation/inline-vector-replace-return.crust` reste refusé : les candidats de
l’ancienne case ne décrivent pas encore le porteur local du résultat retourné,
et le placement de ses chemins doit être raccordé. Le journal
`validation/inline-vector-replace-contract-baseline.log` conserve ce refus et
celui d’un consommateur, depuis corrigé par le suivi de l’identité de la case.
Le consommateur corrigé est désormais testé ; le retour ne l’est pas comme
fonctionnalité acquise. L’async reste à traiter dans ce lot.

Pas de preuve générale de sûreté. Les unions après indices inconnus et les
compositions de contrats ne sont pas déclarées complètes. La régression ciblée
ne remplace pas l’audit final de toutes les règles. Aucune campagne adversariale
étendue ni mutation n’est lancée ici ; aucun résultat du lab indépendant n’est
supposé. Le chantier global demeure actif.
