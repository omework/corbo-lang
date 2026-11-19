[English](INLINE_VECTOR_OWNED_CYCLE.md)

# Cycle — Champs propriétaires des structures en ligne dans Vector<T>

## Règles et périmètre

VE1–VE3, H1, ST1/ST15/ST17, B1–B5, T4/T5/T6 et AS2/AS8/AS11–AS13
restent inchangées. AGENTS.md, VALIDATION_GUIDELINES.md et l’index des brouillons
ont été relus. Les règles de structures et de vectors, ainsi que les règles
mémoire pertinentes, ont été lues dans le travail continu. Aucun arbitrage
nouveau ni modification normative.

Le lot raccorde push/remove et la destruction de structures en ligne contenant
des handles propriétaires. Les contrats synchrones, leur utilisation depuis
async, les captures et les résultats exercés sont inclus. Les autres opérations
et les compositions générales demeurent ouvertes.

## Baseline et changements

validation/inline-vector-owned.crust était refusé aux deux entrées pour une
restriction explicite des champs propriétaires. Le journal -baseline.log conserve
ce constat. Snapshot initial : /tmp/crust-before-inline-vector-owned.

Le runtime des vectors conserve désormais un pointeur vers le layout statique
des cases possédant des champs. Push copie le payload et transmet le nettoyage
des descendants à la case ; seul le stockage du porteur local consommé est
libéré. Les objets désignés par A<T> restent dans leurs pools, aux mêmes adresses.
Le nettoyage d’un vector non vide parcourt ses cases présentes, puis les champs
propriétaires selon le layout, avant de récupérer sa région. Les références
empruntées ne sont pas détruites. Remove transmet les champs au porteur extrait ;
les octets hors du préfixe initialisé ne sont pas nettoyés une seconde fois.

Le vérificateur conserve les sous-graphes propriétaires des cases et de leur
résultat extrait. La copie d’une structure contenant A<T> reste refusée.
L’inférence de contrats matérialise les chemins propriétaires des paramètres
transférés dans les cases. Le backend async conserve les sources des descendants
séparément du stockage local du porteur consommé.

## Défauts rencontrés et corrections

Premier ciblé : 12 méthodes, 2,929 s, deux échecs sur le retour par contrat.
Une restriction ne reconnaissait que les cases de vectors de handles ; la
reconnaissance s’applique aussi aux cases de valeurs. Un contrat d’insertion
avait ensuite omis les descendants d’un paramètre propriétaire non consulté
avant son transfert. Les projections des champs sont maintenant matérialisées.
Le journal -contract-first.log conserve l’étape intermédiaire (deux méthodes,
un échec synchrone). Le deuxième ciblé : 12 méthodes, 3,602 s, code 0.

Le ciblé élargi a révélé une acceptation invalide dans un corps async : une
fonction synchrone insérait un Item contenant A<Int> provenant d’un pool enfant
dans un vector parent. Les deux entrées acceptaient ce programme ;
-targeted-third.log conserve les deux sous-échecs, sur 17 méthodes en 5,025 s.
Les effets du contrat ignoraient tout stockage pour les cases inline, alors
que seuls les anciens slots des porteurs doivent être ignorés. Les pools des
champs propriétaires sont désormais conservés et vérifiés contre le scope du
receveur. Le test négatif n’a pas été affaibli. Le quatrième ciblé passe :
17 méthodes, 5,164 s, code 0.

## Ciblé final

**19 méthodes, 5,963 s, code 0**, O0/UBSan, dans -targeted-final.log.
Cela représente **16 exécutions C réussies** et **14 variantes invalides**
examinées aux deux entrées verify_program/compile_source.

Cas admis : transfert nommé/frais, remove, destruction du vector vide/non vide,
réemploi des slots de deux pools distincts, champs contenus imbriqués, descendant
possédé portant un emprunt, fonctions d’insertion/extraction et relais, passages
successifs entre deux vectors dans une boucle, cleanup de scope, corps async avec
yield, capture propriétaire, retour par join et destruction d’une tâche inactive.
Les traces assertent le nettoyage unique des enfants, avec réemploi effectif.

Cas refusés : ancien nom après transfert, copie du propriétaire, mutation de la
cible d’un emprunt descendant avant dernier usage, pool enfant trop court,
insertion via contrat qui tenterait de prolonger ce pool.

## Traduction C et régression

C conservé dans validation/inline-vector-owned.c. Le layout marque le champ
A<Int> par le code 2 et sizeof(Cell *). L’appel vector_push_owned_value précède
cell_release_storage du seul porteur ; le résultat de vector_remove reçoit le
layout normal et son cell_drop nettoie le descendant. L’inspection confirme les
opérations présentes ; les exécutions et traces vérifient les chemins testés.
Les champs packés utilisent memcpy dans les accès existants.

Régression principale O2/UBSan : **236 méthodes, 138,586 s, code 1** :
232 succès, trois échecs et une erreur dans test_async_recursive_owned.
Les quatre défauts sont reproduits avec le snapshot initial du compilateur :
-recursive-baseline.log, cinq méthodes, 0,821 s, même bilan. Les signatures
historiques utilisaient Node local pour des allocations A<Node>. Elles sont
corrigées en A<Node>, sans modifier les assertions. Rejeu du module :
**cinq méthodes, 3,361 s, code 0**, -recursive-corrected.log.

Le compilateur est inchangé depuis le passage principal ; seule cette fixture
a changé après sa fin. Les empreintes avant/après sont consignées dans
-first-integrity.log et -final-integrity.log. Les 236 méthodes sélectionnées
ont ainsi leurs résultats disponibles après correction de la fixture ;
il ne s’agit pas d’un unique passage global vert.
Complément régions/deux curseurs terminé : **35 méthodes, 26,861 s, code 0**,
-control.log ; 33 empreintes compilateur/tests inchangées (-control-integrity.log).
Sélection,
empreintes initiales, diff et manifeste : validation/inline-vector-owned-*.
Aucun changement compilateur/tests pendant l’exécution.

## Limites

Pas de preuve de sûreté générale. Les positions après certains appels et branches
restent conservatrices ; le suivi async peut garder des sources plus longtemps
que nécessaire. Pop, replace, try_push, tranches et push_new des structures en
ligne restent ouverts, de même que les graphes/types non représentés.
Reset est retiré par défaut ; les tests de ce lot utilisent drop et les scopes.
La régression sélectionnée ne remplace pas l’audit final de toutes les règles.
C11/pthread, Wall/Wextra/Werror, UBSan fatal via le harnais existant.
Pas de campagne de mutations ou recherche adversariale étendue ; aucun résultat
supposé du lab indépendant. Les journaux intermédiaires restent conservés.

Prochain écart reproduit : pop de Vector<Point>, attendu Option<Point>, reste
refusé aux deux entrées. Fixture validation/inline-vector-pop.crust et journal
-baseline.log. Ce cas et les autres opérations ouvertes ne sont pas couverts
par la réussite du présent lot.
