[English](ASYNC_MATCH_REFERENCES_CYCLE.md)

# Cycle — emprunts produits par match dans un cadre async

## Règles et changement

Application de B1/B2/B3/B5, D1, F2, AS8/AS11/AS12 et RT5/RT6, sans modifier
les règles normatives. AGENTS.md, VALIDATION_GUIDELINES.md, l’index des sept
brouillons, le brouillon 04 et les clauses AS11/AS12 ont été relus. La matrice
conserve les autres obligations ouvertes ; ce cycle ne conclut pas le chantier.

`validation/open-async-local-reference-match.crust` est désormais accepté et
exécuté : la référence produite par un match peut être liée, conservée pendant
une suspension puis retournée. Sa sortie est 30 puis 20. L’ancien log de refus
reste une trace historique.

L’inférence suit les appels derrière spawn/spawn_blocking, les tâches nommées,
les handles et leurs résultats stockés. La projection Ok transmet les provenances
du résultat de la tâche ; Err transmet celles de son expression de secours.
Les alternatives sont réunies dans le contrat, avec contrôle du mode et du type.
Le C utilise la même représentation de pointeur que les emprunts existants.

Le traitement des matchs transmet désormais le mode « résultat emprunté » aux
branches des résultats de handles, conversions, vecteurs et erreurs builtin.
Le sujet reste évalué une seule fois, avant le bras choisi. Les retours directs
et les branches à retour anticipé passent par les contrôles de portée existants.

## Contre-exemple de sûreté découvert et corrigé

Le programme `validation/async-match-overlapping-result-borrows.crust` faisait
deux matchs sur le même Result<&mut Int>. Le premier fournissait un emprunt
encore utilisé après la création du second. Les branches de secours visaient
des cibles distinctes, afin de ne pas masquer la duplication du chemin Ok.

Le vérificateur acceptait ce programme invalide. Le log initial enregistre cette
acceptation ; le programme n’a pas été exécuté comme un exemple sûr. La cible
était suivie, mais la capacité mutable portée par le Result nommé n’était pas
réservée pendant l’usage de l’emprunt extrait.

L’emprunt dérivé conserve maintenant aussi son porteur Result. Une seconde
projection incompatible est refusée jusqu’au dernier usage du premier emprunt.
Le contrôle corrigé produit :

```text
REJECTED: ligne 5: accès à 'outcome' incompatible avec un emprunt actif
```

La trace est dans `validation/async-match-overlapping-result-borrows-fixed.log`.
Le programme voisin qui termine le premier usage avant le second match est
exécuté et admis. Deux projections partagées restent admises et exécutées.
Cette correction applique l’exclusivité existante ; elle n’ajoute pas une règle
normative de consommation permanente du Result.

## Autres défauts corrigés

- Un match sur la constante runtime::Error::LaunchFailed produisait une
  comparaison de la constante avec elle-même, refusée par Clang avec -Werror.
  Le sujet est maintenant placé dans un temporaire typé avant le contrôle.
  La trace initiale est `async-match-references-other-families.log`.
- Le contrôle du retour emprunté exige désormais une référence effective.
  Retourner le conteneur Result entier à la place de son contenu est refusé
  avec un diagnostic, sans accéder à un champ interne inexistant.

## Scénarios, modèle et limites des attentes

Le module final `tests/test_async_match_references.py` comporte treize méthodes,
36 exécutions natives normales et 32 refus attendus par passage complet.
Ces nombres comptent les variantes exécutées, pas des garanties indépendantes.

- Modes partagé/mutable, ordre des bras inversé, yield dans les bras et après
  la réception, retours directs ou locaux.
- Tâche nommée avant lancement, résultat de handle stocké, ou spawn directement
  dans le sujet attendu ; branche Err avec retour anticipé.
- Refus de lancement injecté par EAGAIN : le corps de la tâche ne s’exécute pas,
  le marqueur de secours apparaît et la référence de secours est utilisée.
- Nouvelles cases Vector<Int/u8>, normal et lancement refusé, puis relais async ;
  croissance de chaque source refusée tant que la référence retournée sert.
- Mutation, lecture ou drop prématurés des deux sources refusés après retour ;
  accès, drop et réemploi des slots admis après le dernier usage.
- Résultats de conversion et pop de vecteur, erreurs builtin simples et match
  imbriqué d’erreur qui choisissent des emprunts externes. Un vecteur utilisé
  seulement pour calculer le choix peut être détruit avant utilisation du
  résultat emprunté : il n’est pas ajouté arbitrairement à sa provenance.
- Refus des modes incompatibles, cibles locales, bras sans valeur, match
  incomplet et conteneur Result pris pour une référence.
- Double projection mutable du même Result refusée ; variante séquentielle
  et projections partagées exécutées.

Un modèle indépendant choisit parmi trois entiers selon deux décisions :
réussite du lancement et appartenance d’un entier à [0,255]. Les quatre
combinaisons déterminent une case de liste Python, dont seule la valeur est
remplacée. Les trois valeurs finales du programme sont comparées à cette liste.
Chaque source possible est aussi testée contre une mutation avant usage.
Le modèle n’utilise ni contrats, ni provenance interne, ni C émis. Il reste fini.

## Exécutions

| Trace dans validation/ | Résultat exécuté |
| --- | --- |
| async-match-references-initial.log | 8 méthodes, 10,988 s, OK, O2 + UBSan |
| async-match-references-expanded.log | 9 méthodes, 11,086 s, OK, contrôle du conteneur Result ajouté |
| async-match-references-other-families.log | Une erreur de compilation C sur la constante runtime::Error, corrigée ensuite |
| async-match-references-O2-regression.log | 59 méthodes, 80,483 s, OK avant découverte du porteur manquant ; ce passage ne couvrait pas le contre-exemple découvert ensuite |
| async-match-references-carrier.log | Contre-exemple refusé et deux voisins valides exécutés, 1,235 s, OK |
| async-match-references-final-O0.log | Module final : 13 méthodes, 22,933 s, OK |
| async-match-references-final-O2-regression.log | 62 méthodes, 86,489 s, OK : module final, liaisons locales async, retours conditionnels async, erreurs builtin et expressions empruntées synchrones |

Les helpers de ces passages utilisent O0/O2 selon CRUST_TEST_OPT et UBSan
fatal. Le passage final ne saute aucune méthode. `py_compile` et la vérification
des liens locaux des documents modifiés ont réussi. Le diff est conservé dans
`validation/async-match-references.patch`. Les échecs de développement et
l’acceptation initiale du programme invalide restent disponibles pour audit.

## Mutations

Quatre fautes injectées dans des copies temporaires, quatre détections :

| Faute | Observation |
| --- | --- |
| Oublier le porteur Result de l’emprunt extrait | Double projection mutable invalide acceptée |
| Effacer les parents de la charge Ok | Accès incompatible à la cible accepté dans le cadre |
| Oublier la provenance du secours dans le contrat | Accès prématuré à la seconde source accepté chez l’appelant |
| Inverser le test du statut de join | Mauvais marqueur/valeur ou pointeur nul signalé par UBSan |

`validation/async-match-references-final-mutations.log` conserve les résultats.
La campagne initiale de trois fautes reste dans `async-match-references-mutations.log`.
Les détections reposent sur les assertions de refus/sortie et les exécutions
natives, pas sur un taux de couverture supposé de tous les défauts.

## Limites et suite

Le retour d’un emprunt produit par une boucle reste refusé :
`validation/open-async-reference-loop-result.crust` et son log. S5a/B5 autorisent
ce programme : les deux cibles sont injectées et durables ; les breaks utilisent
un réemprunt explicite. Sa sortie attendue est 30 puis 20. Ce refus est un manque
d’implémentation, pas une règle normative.

Suivi : ce manque est traité dans [ASYNC_LOOP_REFERENCES_CYCLE.md](ASYNC_LOOP_REFERENCES_CYCLE.md).
Le diagnostic ci-dessus décrit l’état antérieur à ce complément.

Les enums et agrégats généraux, toutes les formes calculées de handles et les
autres positions syntaxiques ne sont pas couverts par ces scénarios. Les autres
écarts des sept brouillons restent ouverts, notamment scheduler, threads,
Select, mutex et stockage implicite. Reset reste retiré ; aucune couverture
supplémentaire de reset n’est revendiquée dans ce lot.

Les tests natifs utilisent Clang C11, pthread, -Wall/-Wextra/-Werror et UBSan
fatal. ASan n’a pas été relancé après le blocage d’un exécutable C vide documenté
précédemment. Aucune preuve ASan/TSan, second compilateur, vérification formelle
ou sûreté générale du langage n’est affirmée.
