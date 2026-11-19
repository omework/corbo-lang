[English](LOOPS.md)

# Loop, break et continue : un scope par itération

`loop { ... }` répète son bloc. Chaque passage est une nouvelle activation de
scope : ses allocations et sources locales sont nettoyées avant le passage
suivant. `break;` quitte la boucle la plus proche de la fonction courante.
`continue;` ferme les mêmes scopes, puis commence son itération suivante.

```rust
let mut memory = Pool<Int>::new(1);
loop {
    let mut temporary = new(memory) Int(42);
    print(temporary);
    break;
}
memory.reset();
```

`break` détruit `temporary` avant la sortie. `memory` appartient au parent et
reste disponible. Depuis un bloc imbriqué, les scopes quittés sont fermés du
plus profond jusqu'à celui de l'itération, avec destruction avant récupération
du stockage et fermeture des sources locales après leurs allocations.

## Plusieurs itérations

La lecture explicite `*data` copie le contenu Int d'une allocation ou d'un
emprunt vers cette allocation. Elle respecte les restrictions d'accès et ne
transfère pas le stockage. Elle est limitée à Int ; elle ne donne pas accès à
des pointeurs arbitraires ni à l'arithmétique de pointeurs.

```rust
let mut memory = Pool<Int>::new(1);
let mut controls = Pool<Int>::new(1);
let mut state = new(controls) Int(0);
loop {
    let mut temporary = new(memory) Int(42);
    if *state == 1 {
        break;
    }
    state.set(1);
}
```

Cet exemple effectue deux itérations dans le même slot de `memory`.
`state.set(1)` reste la syntaxe provisoire de mutation du contenu.
L'itération terminée ne laisse aucun accès local utilisable à son allocation.

Les indicateurs de nettoyage sont déclarés dans leur fonction C, mais activés
au point où l'allocation vivante est suivie. Cette activation se répète dans
le corps généré : un indicateur mis à zéro lors de la première destruction
ne peut pas empêcher celle de l'itération suivante. Les fonctions n'utilisent
que les indicateurs déclarés dans leur contexte C ou reçus par paramètre.

## Vérification de la reprise

Le compilateur analyse d'abord une itération depuis l'état d'entrée, puis réunit
cet état avec les chemins qui reviennent au début. Il réanalyse le corps si
des accès ou états de vie changent, jusqu'à stabilisation. Le C provisoire,
les indicateurs locaux et les retours enregistrés lors d'une passe abandonnée
ne sont pas conservés dans le programme final.

Ainsi, consommer une allocation du parent puis recommencer une itération qui
la demande est refusé :

```rust
let mut data = new(memory) Int(42);
loop {
    -> data;
    drop(-> data); // L'itération suivante ne peut plus importer data.
}
```

Les accès utilisés de nouveau dans le corps sont pris en compte à travers la
reprise, notamment les emprunts mutables. Lire un emprunt puis accéder à son
allocation par un accès incompatible avant l'itération suivante reste interdit.

Un reset du parent reste possible quand les anciens accès ne servent plus :
les itérations suivantes peuvent réinitialiser à nouveau une source déjà vide,
puis allouer leurs propres temporaires. Les indicateurs gardent ces opérations
correctes après la première destruction et après réutilisation d'une adresse.

## Sorties et transferts

Les chemins faisant `break` ne reviennent pas au début. Leurs états sont réunis
pour déterminer les accès disponibles après la boucle. Les chemins faisant
`return` quittent la fonction et sont exclus de cette suite. Un emprunt utilisé
après la boucle reste protégé sur les chemins qui font `break`.

Les transferts explicites existants restent nécessaires. Une allocation importée
par `-> data` meurt à la fin de l'itération si aucun `<- data` ne la rend à son
parent. Un retour au parent marqué avant `break` est appliqué en fermant les
scopes correspondants. Le résultat doit conserver un ordre de réception
compatible avec les chemins analysés ; les ordres contradictoires sont refusés.

Une fonction appelée depuis la boucle ne peut pas utiliser `break` pour quitter
la boucle de son appelant. Des boucles imbriquées ont chacune leur propre sortie.
Un `break` survenant pendant l'évaluation d'un argument nettoie aussi les
allocations déjà préparées dans l'itération et empêche l'appel non encore lancé.

## Reprise explicite avec continue

```rust
loop {
    let mut temporary = new(memory) Int(42);
    if *state == 0 {
        state.set(1);
        continue; // Détruit temporary avant de recommencer.
    }
    print(temporary);
    break;
}
```

Chaque chemin `continue` participe à l'analyse de reprise, comme la fin normale
du corps. Les emprunts nécessaires au prochain passage restent actifs, y compris
quand toutes les branches terminent par `continue`, `break` ou `return`.
Un transfert `<-` marqué est appliqué avant la reprise ; ses contraintes d'ordre
de réception restent identiques. Les pools peuvent réutiliser les slots libérés.

`continue` vise la boucle la plus proche dans la fonction courante. Il peut
survenir dans un bloc, une branche d'expression `if` ou pendant l'évaluation
d'un argument : les allocations déjà préparées sont alors nettoyées et l'appel
n'est pas lancé. Les instructions suivantes sur ce chemin ne sont pas émises.

## Traduction en C et divergence

Le backend émet une boucle `for (;;)`. Chaque `break` est traduit en nettoyage
des scopes concernés, puis en saut vers une étiquette propre à la boucle :

```c
for (;;) {
    Cell *temporary = cell_new(memory, 42, "temporary");
    cell_drop(temporary);
    goto loop_end;
}
loop_end: ;
```

Un `continue` émet aussi le nettoyage, puis un saut vers une étiquette placée
à la fin du corps C, avant la reprise du `for`. Il évite tout code restant
dans l'itération.
La sortie normale d'une itération émet son nettoyage avant le retour au début.
Une boucle sans chemin `break` ne poursuit pas les instructions qui la suivent.
Elle peut retourner depuis la fonction ou diverger. Un appel qui ne peut jamais
retourner ne reçoit pas de résultat fictif ; la suite correspondante n'est pas
émise. Les programmes de test ne sont pas exécutés sur des chemins infinis.

## Boucle avec receveur

```rust
fn main() {
    let mut memory = Pool<Int>::new(2);
    let result = loop {
        let temporary = new(memory) Int(10);
        let kept = new(memory) Int(20);
        print(temporary);
        break <- kept;
    };
    print(result);
}
```

Le C matérialise la valeur du `break` dans une variable déclarée avant le
`for`. Les allocations locales encore rattachées aux scopes quittés sont
nettoyées avant le saut. Le receveur reprend ensuite la responsabilité du
résultat alloué, à la même adresse. L'analyse rejoint seulement les sorties
`break`, retient toutes les provenances ou cibles d'emprunt et vérifie leur
durabilité à chaque sortie. Le résultat d'un `break` sans receveur est sans
effet pour un transfert explicite et déclenche un avertissement.

Une boucle utilisée à droite de `=` peut utiliser l'ancien receveur pendant
l'évaluation. `continue` ferme l'itération puis reprend. `return` quitte la
fonction avec son nettoyage habituel. Seul un `break` fournissant un résultat
atteint le remplacement.

## Remplacer un receveur déclaré avant la boucle

```rust
fn main() {
    let mut memory = Pool<Int>::new(2);
    let mut result = new(memory) Int(10);
    while *result == 10 {
        let replacement = new(memory) Int(20);
        result = <- replacement;
        continue;
    }
    print(result);
}
```

Le remplacement détruit l'ancienne allocation pendant l'itération. À
l'issue de cette itération, le C conserve l'adresse de la nouvelle allocation
dans un pointeur déclaré avant la boucle. Un `continue` ou la fin normale du
corps remet à jour ce pointeur avant le test suivant. Les `break` et le test
faux d'un `while` déterminent l'accès après la boucle. Une sortie `return`
nettoie la fonction ou transfère son résultat selon les règles habituelles.

Le compilateur réanalyse les reprises à partir des provenances et cibles
possibles. Un accès emprunté à l'ancienne allocation ne peut pas être utilisé
pour accéder à son remplacement. Après le dernier usage d'un emprunt
stocké, le porteur peut rester alloué jusqu'à son nettoyage. Ses accès
sont invalidés si la reprise remplace la cible. Un transfert marqué
susceptible de réactiver un accès, une dépendance que le receveur
emporterait vers sa propre génération ou des ordres de destruction
incompatibles font toujours refuser la reprise.

## Périmètre et validation

[WHILE.md](WHILE.md) décrit la boucle à condition, qui ne produit pas de valeur.
`for` et les labels utilisateur restent hors périmètre. L'analyse reste
conservative si la sûreté dépend de corrélations entre des conditions ou
d'ordres de réception contradictoires. Le nombre de passes est borné.

[tests/test_loops.py](../tests/test_loops.py) et
[tests/test_continue.py](../tests/test_continue.py) couvrent les sorties et
reprises ordinaires. [tests/test_loop_results.py](../tests/test_loop_results.py)
exerce les résultats de boucle, les emprunts, les fonctions, les réaffectations,
les provenances, le curseur et le reset.
