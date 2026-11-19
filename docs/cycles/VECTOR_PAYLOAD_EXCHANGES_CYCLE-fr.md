[English](VECTOR_PAYLOAD_EXCHANGES_CYCLE.md)

# Cycle — Graphes des charges dans les résultats de vecteurs

## Portée et règles

Suite de VECTOR_PAYLOAD_OPTIONS_CYCLE.md, selon H1–H3, VE2–VE4, B1–B5/B4c,
D1–D3, F2–F4 et U1. Aucun changement normatif. Les consignes AGENTS.md,
VALIDATION_GUIDELINES.md, l’index des sept brouillons et les règles concernées
ont été lus dans cette session. Les tests restent centrés sur les cas retenus
et les régressions directes ; la campagne adversariale indépendante reste séparée.

Les signatures synchrones Result<A<Item>,A<Item>> et Result<(),A<Item>>
transportent maintenant les graphes de champs empruntés/propriétaires dans les
retours et relais testés. Le pool d’origine et l’adresse de chaque objet restent
inchangés. Les variantes conservent chacune leurs propres dépendances.

## Implémentation

- FunctionResult porte `exchange_values`, description statique de la charge de
  chaque variante. Cette information est produite quand un graphe est nécessaire ;
  les échanges simples continuent d’utiliser leur contrat de provenance.
- L’analyse des résultats conserve les chemins internes `ok/…` et `err/…` dans
  les paramètres, les relais et les projections. Ces chemins ne sont pas une
  nouvelle syntaxe du langage.
- L’analyse de contraintes résout les champs et les descendants de chaque charge
  avec les sources réelles, puis restitue la bonne charge au match consommant.
- Le vérificateur résout les deux contrats avant de publier la mutation du vecteur.
  Il compose ensuite le contrat global à partir des graphes concrets de ces deux
  variantes, y compris les descendants hérités d’un paramètre transféré.
- Les paramètres symboliques et les résultats d’appels conservent des prototypes
  de charge distincts. Le contrôle du corps examine la charge effective de chaque
  variante, sans attribuer les variantes d’un objet à Ok(()) qui ne contient rien.
- L’identité des capacités stockées est conservée au déplacement d’une charge.
  Lorsqu’une mutation conditionnelle conserve la même charge comme alternative
  dans le vecteur, ce prêt n’est pas compté comme un second emprunt indépendant.
  Les accès dérivés des champs réutilisent cette identité ; les autres emprunts
  et les accès directs à la cible restent vérifiés.

Le runtime et le format C des résultats ne changent pas. Il s’agit d’un
raccordement des métadonnées statiques et de leurs contrôles.

## Cas ciblés

Sept méthodes : **14 exécutions C** après verify_program et compile_source,
et **18 programmes invalides** refusés aux deux entrées.

- Replace avec index valide/invalide : sortie 7/9, deux nettoyages Item au total.
- Retour puis relais ; flèche obligatoire à l’appel.
- Item possédant Inner qui emprunte Int, directement et via un relais : les
  deux résultats sont exécutés, avec deux destructions de chaque type.
- Drop de chacune des cibles prématuré refusé ; la cible d’un descendant est
  aussi protégée après le retour.
- Try_push dans une région 1 MiB disponible ou pleine ; Ok(())/Err(Item), relais,
  réemploi du pool d’Item après nettoyage. La limite est calculée selon la taille
  du pointeur de la plateforme. Le remplissage alloue 131072 handles sur ce host.
- Charge contenant &mut Int : lecture par la charge admise, lecture/écriture
  directe des cibles refusée avant consommation. Construire un deuxième emprunt
  mutable indépendant vers la même cible reste refusé.
- Transfert du résultat vers un parent, avec destruction du vecteur enfant ; un
  pool d’Item enfant trop court est refusé.
- Drop direct du résultat de l’opération, usage explicite requis, double
  consommation refusée.

## Défauts rencontrés

Le premier cas enregistré a été admis après raccordement du contrat direct.
Les essais suivants ont exposé trois pertes de métadonnées :

1. La charge d’un Result n’était pas reconstruite dans l’analyse de contraintes,
   ce qui rendait un appel au descendant Inner impossible.
2. Le contrat global perdait le pool d’un descendant hérité du paramètre entrant,
   alors que la charge issue du vecteur conservait le sien. La composition se
   fait maintenant après résolution séparée des deux variantes.
3. Le vérificateur attribuait une variante de l’objet à la branche Ok(()) vide,
   et comptait deux fois la capacité mutable déplacée lors d’un remplacement
   conditionnel. Les contrôles portent maintenant sur les charges réelles et
   l’identité du prêt conservé ; les contrôles internes restent actifs.

Les journaux d’échec et les attentes originales sont conservés. Le diagnostic
intermédiaire `vector-payload-exchanges-nested-diagnostic.log` identifie les deux
sources de descendants dont une manquait au contrat. Ce diagnostic instrumente
le contrôle sans supprimer son erreur ; il ne constitue pas un test natif.

## Exécutions et traçabilité

- Probe du cas enregistré : C exécuté, sortie 7, code 0,
  `validation/vector-payload-exchanges-first-o0.log`.
- Ciblés O0 initiaux : trois méthodes, 1,849 s puis 1,903 s, un échec à chaque
  essai ; troisième essai, trois méthodes, 2,847 s, code 0.
- Quatrième essai : six méthodes, 3,287 s, deux échecs.
- Cinquième, sixième, septième : six méthodes, respectivement 4,659 s, 4,657 s,
  4,633 s, un échec mutable ; huitième : six méthodes, 4,852 s, code 0.
- Ciblé final O0 : **sept méthodes, 6,890 s, code 0**,
  `validation/vector-payload-exchanges-targeted-ninth-o0.log`.
- Régression O2 : **159 méthodes, 158,585 s, code 0**, sélection
  `validation/vector-payload-exchanges-test-selection.txt`, journal
  `validation/vector-payload-exchanges-regression-o2.log`.

C11, pthread, Wall/Wextra/Werror et UBSan fatal. Le programme précédemment refusé
`validation/open-vector-payload-exchange-contract.crust` est maintenant exécuté
par les tests ; son ancien journal reste historique. Le C et le contrat courant
sont archivés dans `validation/vector-payload-exchanges.c` et
`validation/vector-payload-exchanges-contract.json`.

Snapshot : `/tmp/crust-before-vector-payload-exchanges`. Patches et empreintes
des trois modules et du test : `validation/vector-payload-exchanges-changes.json`.

## Limites et suite

Les unions de provenances restent conservatrices. Ce lot ne démontre pas toutes
les corrélations entre variantes, positions dynamiques et graphes récursifs.
Les références nominales générales, les retours de vecteurs entiers empruntants
et l’intégration async de ces charges restent à compléter. Le prochain cas minimal
est `validation/open-vector-payload-container-contract.crust` : la fabrique de
Vector<A<Item>> empruntant un Int injecté reste explicitement refusée aux deux
entrées, journal associé conservé.

Reset reste retiré du profil normal. Pas de nouveau modèle indépendant ni de
campagne de mutations. Les modèles précédents ont été rejoués : huit
combinaisons de durées de vie (une admission et sept refus), et quatre
combinaisons de stockage (quatre admissions et quatre refus), sans changement
de leurs prédictions. Ils ne modélisent pas les nouvelles capacités des échanges. Ni les tests ni
UBSan ne constituent une preuve générale de sûreté. L’objectif global reste actif.
