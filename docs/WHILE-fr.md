[English](WHILE.md)

# While : tester avant chaque itération

`while` accepte les mêmes conditions que `if` : `true`, `false` ou une
comparaison de valeurs Int (`==`, `!=`, `<`, `<=`, `>`, `>=`). Les opérandes
sont évalués de gauche à droite, une fois par test.

```rust
let mut memory = pool<Int>(1);
let mut controls = pool<Int>(1);
let mut state = new(controls) Int(0);
while *state == 0 {
    let mut temporary = new(memory) Int(42);
    print(temporary);
    state.set(1);
}
```

La condition précède le corps à chaque passage. Le corps peut donc ne jamais
s'exécuter. `break` sort de la boucle la plus proche ; `continue` nettoie
l'itération puis reprend son test, sans exécuter le reste du corps.
`return` quitte la fonction avec le nettoyage déjà défini pour les retours.
Aucun de ces sauts ne traverse la frontière d'une fonction.

## Scope du test et du corps

Le test et le corps partagent un scope d'itération. Il n'y a pas de bloc
intermédiaire entre le corps et le parent de la boucle : les transferts
`-> data` à l'entrée du corps ciblent bien le parent direct.

Les temporaires alloués directement pendant l'évaluation du test appartiennent
à l'itération. Ils sont détruits à sa fermeture, y compris lorsque la condition
est fausse, lors de `continue`, `break` ou `return`. Ils restent présents pendant
le corps lorsque le test réussit. Il faut compter ces temporaires dans la
capacité simultanée du pool. Les blocs explicites dans la condition conservent
leurs propres règles de transfert et de nettoyage.

Les allocations du corps sont détruites avant celles du test, selon l'ordre
inverse de création/réception. Une allocation `<-` marquée suit les règles
ordinaires de transfert au parent. Les sources locales sont fermées après
leurs allocations. Les slots libérés peuvent servir au test ou au corps du
passage suivant ; cela ne réactive aucun ancien accès.

## Vérification des chemins

L'analyse de reprise de `loop` est réutilisée. Les lectures de la condition
participent aux usages de l'itération suivante : un emprunt nécessaire au
prochain test empêche une destruction incompatible avant la reprise.
Les chemins `break` ne reprennent pas ce test ; les emprunts encore utilisés
après la boucle restent toutefois protecteurs.

L'état après la boucle réunit les sorties `break` et les sorties par condition
fausse, après les effets et le nettoyage du test. Cela inclut le premier test,
quand le corps ne s'est jamais exécuté. Un accès doit être disponible sur tous
ces chemins pour être utilisé ensuite. Un appel dans la condition peut muter
ou réinitialiser une source : ses effets sont vérifiés même si le corps ne
s'exécute pas.

Les conditions ne sont pas évaluées statiquement pour prouver des corrélations
entre branches. Même `while true` conserve un chemin abstrait de condition
fausse : une fonction retournant une valeur doit fournir un retour après la
boucle si sa suite reste accessible à l'analyse. Pour exprimer une boucle sans
sortie par condition, utiliser `loop`.

## Traduction en C

Le backend utilise la même boucle C `for (;;)` que pour `loop`. Au début du
corps généré, il évalue les opérandes du test dans des variables temporaires,
puis émet le nettoyage de l'itération et un saut de sortie si le test échoue.
Le corps Corbo suit ce contrôle. `continue` saute à la fin du corps C après
nettoyage ; le passage suivant réévalue donc le test.

Le contrôle initial est une instruction interne du compilateur, sans scope
supplémentaire. Ses expressions sont indexées pour le suivi des emprunts,
les effets des fonctions et les retours ou sauts anticipés pendant le test.

## Exemple et validation

```sh
python3 prototype/crust.py run examples/while.crb
PYTHONPATH="$PWD/prototype" PYTHONPATH="$PWD/prototype" python3 -m unittest discover -s tests -p test_while.py -q
```

Les régressions couvrent zéro itération, les comparaisons, les effets et
allocations du test, les transferts, les emprunts cycliques, les fonctions,
les sauts pendant le test, les sources privées et les slots des pools Int/enum.
Les limites du prototype restent décrites dans [SAFETY.md](SAFETY.md).
