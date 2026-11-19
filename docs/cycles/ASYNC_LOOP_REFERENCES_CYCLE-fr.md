[English](ASYNC_LOOP_REFERENCES_CYCLE.md)

# Cycle — résultats empruntés de boucles async

## Périmètre et règles

Application de S4/S5/S5a, B1–B5, D1, AS8/AS10/AS11/AS12 et RT5/RT6,
sans modification normative. AGENTS.md, VALIDATION_GUIDELINES.md et l’index
des brouillons ont été relus, ainsi que les clauses de contrôle de flux,
d’emprunts et de résultats async. Les autres obligations ouvertes de la matrice
restent ouvertes. Le dernier échange sur le réglage High n’avait pas fait
progresser le compilateur ; ce cycle reprend les modifications présentes.

Le test initial précédemment lancé était terminé : son journal contient
8 méthodes réussies en 7,819 s. Aucun lancement de remplacement n’a été fait
sur la seule base d’une absence de message. L’inventaire des processus par ps
est interdit dans cet environnement ; le journal terminal établissait la fin.

Le programme `validation/open-async-reference-loop-result.crust` est désormais
compilé et exécuté : sortie 30 puis 20. L’ancien refus reste conservé.
Les breaks de la boucle courante fournissent des pointeurs de même type/mode.
Les sorties des boucles imbriquées appartiennent à leur propre boucle.
Le contrat réunit les cibles possibles ; la liaison du résultat réserve leurs
accès et les parents des réemprunts jusqu’au dernier usage.
Les cibles locales qui disparaissent à la sortie restent refusées.

Le C conserve un pointeur de résultat dans le cadre async, sans déplacer
l’allocation cible. Les nettoyages existants sont exécutés sur les scopes
quittés par break/continue ; le runtime n’a pas été modifié dans ce lot.

## Contre-exemple corrigé

`validation/async-loop-early-return-provenance.crust` contient :

```rust
return loop {
    yield;
    if flag == 1 { return a; }
    break &mut *b;
};
```

Le contrat ne conservait que la provenance du break, donc b. Il oubliait le
retour anticipé vers a dans l’expression du return externe. Chez l’appelant,
`a = 3;` avant l’usage du résultat mutable était accepté à tort. L’acceptation
est enregistrée dans `async-loop-early-return-provenance-initial.log` ; ce
programme invalide n’a pas été exécuté comme un exemple sûr.

L’analyse visite désormais aussi les retours imbriqués dans l’opérande d’un
return. Le journal `async-loop-early-return-provenance-fixed.log` contient :

```text
REJECTED: ligne 4: accès à 'a' incompatible avec un emprunt actif
```

Les lectures, mutations et drops des deux cibles sont refusés avant utilisation
du résultat. Les deux chemins valides sont exécutés, puis leurs slots réutilisés.

## Scénarios exécutés et modèle

`tests/test_async_loop_references.py` comporte dix méthodes : 18 exécutions
natives normales et 28 refus attendus par passage complet. Ces nombres
comptent les variantes, pas des propriétés indépendantes.

- Références partagées et mutables, deux sorties, plusieurs continue et yield.
- Boucles imbriquées, réemprunts locaux qui sortent vers une cible durable.
- Retour direct de boucle et retour anticipé depuis la boucle.
- Protection des deux sources chez l’appelant et dans le cadre async.
- Élément de tableau choisi par indice calculé, avec suspension avant écriture.
- Cases Vector<Int/u8> obtenues par await et match de handle : lancement réussi
  et échec EAGAIN injecté, puis emprunt sorti de boucle et retourné par relais.
- Refus des modes/types divergents, break sans valeur et cibles locales.
- Nettoyage d’un enfant inactif possédant une allocation sur les deux sorties,
  après des continue ; destruction exactement une fois et réemploi du pool
  de capacité un après join. L’enfant inactif ne doit pas exécuter son print.

Le modèle indépendant du test de tableau choisit l’une des trois cases d’une
liste Python, remplace cette case par 99, puis compare les trois valeurs finales
au programme natif. Il n’utilise ni contrats ni C généré. Les indices 0, 1 et 2
sont tous exécutés ; la modification de la source avant usage est aussi refusée.
Ce modèle fini ne prouve pas la correction générale des analyses de boucles.

## Validation exécutée

| Journal dans validation/ | Résultat |
| --- | --- |
| async-loop-references-initial.log | 8 méthodes, 7,819 s, OK, avant ajout du contre-exemple |
| async-loop-references-early-return-fix.log | 9 méthodes, 8,136 s, OK après correction du contrat |
| async-loop-references-cleanup.log | Nettoyage et réemploi : 1 méthode, 0,969 s, OK |
| async-loop-references-O0.log | Module final : 10 méthodes, 8,501 s, OK |
| async-loop-references-O2-regression.log | 80 méthodes, 92,284 s, OK ; module final, matchs et liaisons empruntées async, retours async, expressions empruntées synchrones et tests de boucles du runtime |

Les helpers natifs utilisent Clang C11, pthread, UBSan fatal et
-Wall/-Wextra/-Werror. Les variantes O0/O2 sont explicites via CRUST_TEST_OPT.
La régression O2 ne comporte aucun saut de méthode. `py_compile` a réussi.
Le diff du compilateur est conservé dans `validation/async-loop-references.patch`.
Le C de la fixture initiale est dans `validation/async-loop-reference-result.c` :
le cadre contient les pointeurs injectés et le pointeur du résultat ; chaque
break affecte ce dernier avant de sortir, et le yield suivant conserve ce
pointeur dans le cadre. Cette inspection complète les exécutions, sans en
déduire une preuve générale sur le C généré.

Commandes du module et de la campagne de fautes :

```sh
CRUST_TEST_OPT=-O0 PYTHONPATH=.:tests python3 -m unittest test_async_loop_references -v
python3 tests/run_async_loop_reference_mutations.py
```

La régression utilise CRUST_TEST_OPT=-O2, CRUST_SANITIZE=undefined et
PYTHONPATH=.:tests. Elle charge les cinq modules test_async_loop_references,
test_async_match_references, test_async_local_references,
test_async_reference_returns et test_reference_expressions, puis toutes les
méthodes d’AsyncRuntimeTests dont le nom contient loop, continue ou break.
Le journal conserve les noms exacts des 80 méthodes exécutées.

## Mutations

Quatre fautes dans des copies temporaires, quatre détections, journal
`validation/async-loop-references-mutations.log` :

| Faute | Observation |
| --- | --- |
| Oublier les retours imbriqués | Accès incompatible à la cible du retour anticipé accepté |
| Conserver seulement la première provenance de break | Accès incompatible à la seconde cible accepté |
| Effacer les réservations du résultat de boucle | Accès incompatible dans le cadre accepté |
| Omettre le nettoyage des scopes | Slot de l’enfant non rendu ; pool de capacité un épuisé |

Ces détections reposent sur les refus et comportements attendus, pas sur une
comparaison textuelle du C. Elles ne mesurent pas un taux global de détection.

## Limites et suite

Un autre programme valide reste refusé :
`validation/open-async-loop-break-in-initializer.crust` contient un break
dans un if utilisé pour initialiser une variable de la boucle. Le diagnostic
initial est `branche de if async : résultat Int ou retour requis`. La forme
de contrôle est encore non implémentée ; la variante
`validation/async-loop-nested-expression-provenance.crust` ajoute aussi un
accès incompatible pour chercher une perte de provenance, actuellement masquée
par ce refus syntaxique/structurel. Il faudra exécuter le voisin valide et
vérifier ce refus de sûreté après prise en charge du contrôle imbriqué.

Suivi : le cycle [ASYNC_EXPRESSION_LOOP_EXITS_CYCLE.md](ASYNC_EXPRESSION_LOOP_EXITS_CYCLE.md)
prend en charge cette initialisation et vérifie sa variante invalide. La limite
ci-dessus décrit donc l’état à la fin du présent cycle.

Les formes générales d’agrégats, handles, Select, scheduler, threads natifs,
mutex et stockage implicite restent suivies dans la matrice. Reset reste retiré.
ASan n’a pas été relancé après le blocage documenté d’un programme C vide.
Aucune preuve ASan/TSan, second compilateur, vérification formelle ou sûreté
générale n’est revendiquée. L’objectif des sept brouillons reste actif.
