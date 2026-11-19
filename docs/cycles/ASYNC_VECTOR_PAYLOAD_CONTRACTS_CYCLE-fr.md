[English](ASYNC_VECTOR_PAYLOAD_CONTRACTS_CYCLE.md)

# Cycle — Contrats de vecteurs complexes appelés depuis async

## Règles et portée

Suite de ASYNC_VECTOR_PAYLOAD_GRAPHS_CYCLE.md. H1–H3, VE1–VE4,
B1–B5/B4c, D1–D3, F2–F4, AS8–AS12 restent inchangées. Les consignes et
les guidelines ont été lues avant ce travail. La validation reste centrée sur
les fonctionnalités retenues et leurs régressions directes.

Un appel synchrone depuis un état async doit publier les dépendances des objets
qu’il insère dans un vecteur. Une extraction renvoyée doit conserver les prêts
et pools de sa charge même après destruction du conteneur. Le corps de l’appel
n’est pas reparcouru par l’analyse de l’appelant ; ses contrats inférés portent
ces informations. Le pont C vérifie et génère séparément le corps exécuté.

## Défauts et corrections

Le cas enregistré `open-async-vector-payload-sync-call.crust` appelait put,
puis extrayait un objet empruntant n. Une variante détruisant n avant extraction
était acceptée aux deux entrées. Les programmes invalides n’ont pas été exécutés.

- Le backend async publie désormais `vector_write_payloads` dans les prêts
  stockés du vecteur, au retour de l’appel. Les cibles antérieures restent
  conservées quand une insertion ajoute des alternatives.
- Les pools des descendants possédés sont inclus dans les sources retenues,
  et leur durée de vie est vérifiée par rapport au vecteur receveur.
- Les paramètres vecteurs empruntés fournissent leurs prêts aux résultats de
  l’appel. Les champs des descendants propriétaires sont parcourus récursivement
  pour restituer aussi leurs prêts au receveur de l’extraction.
- Le pont C construit un graphe symbolique des éléments possibles, pour un
  vecteur reçu par emprunt ou transfert. Il ne lit pas arbitrairement sa première
  case : le vecteur peut être vide. L’accès C réel est généré lors de l’extraction.
- Les cibles empruntées de ce graphe restent dans le scope extérieur ; elles ne
  sont pas transférées avec le conteneur. Une première version les enregistrait
  dans un scope différent de leur rattachement, détecté par verify_state et corrigé
  sans désactiver l’invariant.

La première version ne conservait que les champs directs d’un résultat. Le cas
Item possédant Inner empruntant n a montré la perte du prêt après extraction.
Le parcours récursif corrige ce cas ; le test de refus ne contient plus de second
usage direct de n susceptible de masquer la raison de rejet recherchée.

## Scénarios exécutés

Six méthodes ciblées : **8 exécutions C**, **11 programmes invalides**, chacun
vérifié par verify_program et compile_source, soit 22 contrôles de refus.

- Insertion directe et par relais ; cible protégée avant extraction et après
  destruction du vecteur tant que l’objet extrait vit.
- Extraction par fonction recevant le vecteur par &mut.
- Insertion d’un objet contenant &mut Int : lecture et écriture concurrentes
  de sa cible refusées.
- Fonction consommant le vecteur et retournant un élément : nettoyage du
  conteneur et conservation de l’emprunt de l’élément.
- Pop par fonction : Some et None ; vecteur détruit avant match, suspension,
  résultat 7 ou 0 et libération des prêts après consommation.
- Item → A<Inner> → &Int : insertion/extraction par fonctions, lecture via un
  helper, deux destructions Inner avec réemploi d’un pool de capacité 1.
  Destruction anticipée de n et pool Inner trop court refusés.

## Journaux et artefacts

Préfixe `validation/async-vector-payload-contracts-` :

- targeted-first-o0 : trois méthodes, 1,383 s, échec ; refus attendus manquants et
  extraction non raccordée.
- targeted-second-o0 : trois méthodes, 1,558 s, échec dans le pont d’extraction.
- targeted-third-o0 : trois méthodes, 2,099 s, succès.
- targeted-fourth-o0 : mêmes trois méthodes, 1,802 s, succès ; une erreur de
  script avait empêché l’ajout des nouveaux tests avant cette exécution.
- targeted-fifth-o0 : six méthodes, 3,150 s, échec ; graphe imbriqué perdu et
  invariant de scope du pont.
- targeted-sixth-o0 : **six méthodes, 3,856 s, code 0**.
- regression-o2 : **270 méthodes, 269,141 s, code 0** ; liste dans
  `validation/async-vector-payload-contracts-test-selection.txt`.

Harnais C11, pthread, Wall/Wextra/Werror, UBSan fatal, O0 puis O2. Les modèles
antérieurs de durée de vie, stockage et Select sont rejoués dans la régression ;
ils ne constituent pas un nouveau modèle indépendant de ces contrats.
Pas de nouvelle campagne de mutations, ASan ou TSan.

C et description du contrat put : fichiers `.c` et `-contract.json` associés.
Le contrat distingue l’effet sur v, la source p et la cible n.
Snapshot : `/tmp/crust-before-async-vector-payload-contracts`.
Patches exacts et empreintes des deux modules et du test : fichier `-changes.json`.

## Limites et suite

Les prêts locaux sont encore joints par chemin de champ `[]`, sans corrélation
complète entre indice, branche et cible. Le pont décrit un graphe fini ; les
compositions récursives générales restent à valider et raccorder.

Le retour async d’un vecteur entier est le prochain cas :
`validation/open-async-vector-payload-return.crust/.log`. Un vecteur reçu par
transfert, suspendu puis restitué via join est encore refusé à la signature aux
deux entrées. Sa règle est déjà retenue ; ce refus est un écart d’implémentation.

Reset reste retiré. Les résultats de ce cycle ne sont pas une preuve générale de
sûreté ni une validation exhaustive de toutes les règles. L’objectif reste actif.
