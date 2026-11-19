[English](REFERENCE_VALUES.md)

# Créer un emprunt et utiliser une référence existante

Extension ultérieure : les [retours &mut Int](MUTABLE_BORROW_RETURNS.md) sont
maintenant disponibles. Les restrictions et mesures ci-dessous décrivent le
périmètre du cycle historique, dont les sources brutes et empreintes sont conservées.

Décision de l'utilisateur du 2 novembre 2026 : conserver une lecture claire de
`&`, dans les appels et les retours. Ce cycle corrige le raccourci qui traitait
`&reference` comme un réemprunt vers la cible sans niveau supplémentaire.
Références : B4/B5 et I1/V2/V3/P9 dans [LANGUAGE_RULES.md](LANGUAGE_RULES.md),
[guidelines](VALIDATION_GUIDELINES.md), [matrice](VERIFICATION_MATRIX.md).

## Écritures retenues

```rust
fn inspect(data: &Int) -> Int {
    return *data;
}

fn borrow(data: &Int) -> &Int {
    return data;
}

fn relay(data: &Int) -> &Int {
    let mut view = borrow(data);
    return view;
}

let mut memory = Pool<Int>::new(1);
let mut data = new(memory) Int(42);
let mut view = &data;
let mut a = inspect(&data);           // Crée un emprunt depuis l'allocation.
let mut b = inspect(view);            // Fournit l'emprunt existant.
let mut c = inspect(borrow(view));    // Le sous-appel fournit déjà un emprunt.
print(a);
print(b);
print(c);
```

`inspect(&view)` et `return &data` lorsque `data` est déjà un paramètre &Int
ajoutent un niveau de référence. Le prototype n'implémente pas les références
imbriquées : ces expressions sont refusées, sans aplatissement ni conversion
en pointeur vers la cible. `return data` transmet l'emprunt reçu. Un retour
qui crée un emprunt depuis une allocation locale reste refusé pour sa durée
de vie, même si le pool survit.

La signature conserve le type et le mode de passage. Une allocation exige
encore `&`, `&mut` ou `->` selon l'intention ; `inspect(data)` est refusé si
`data` désigne l'allocation. Un emprunt reçu ne devient pas un accès possédant,
ni un Int copiable. Les retours alloués conservent leur `<-` explicite.
Les affectations générales `let mut alias = view` entre références ne sont pas
ajoutées par cette clarification des appels/retours.

Un accès mutable existant se passe aussi par son nom. Les accès incompatibles
restent suspendus pendant son utilisation par le sous-appel ; un résultat &Int
prolonge les restrictions en lecture jusqu'à son dernier usage. Un paramètre
mutable peut ainsi fournir l'accès en lecture annoncé par `-> &Int`, sans créer
un deuxième accès mutable. L'escalade d'un emprunt partagé vers &mut est refusée.

Les pools suivent la même règle :

```rust
fn make(memory: &mut Pool<Int>) -> <- Int {
    let mut data = new(memory) Int(42);
    return <- data;
}

fn forward(memory: &mut Pool<Int>) -> <- Int {
    let mut data = make(memory); // memory est déjà un emprunt de pool.
    return <- data;
}
```

L'appel depuis un pool local reste `forward(&mut pool)`. Une capacité en lecture
ne devient pas mutable par transmission du nom. Les champs &Int sont cohérents :
`field: &data` depuis une allocation, `field: view` depuis une référence nommée.
Le pattern `match &value` reste la syntaxe spécifique de lecture du match actuel ;
ce cycle ne redéfinit pas sa grammaire en expressions générales.

## Vérifications conservées

Les cibles et leurs sources ne sont pas déplacées. Les frontières enfant →
parent restent contrôlées sans promotion implicite. Toutes les alternatives
d'un retour conditionnel sont suivies, ainsi que leurs parents mutables.
Une référence passée par nom protège aussi sa cible lorsqu'un argument suivant
est évalué. Une référence retournée reste liée à l'historique des resets de sa
cible ; elle n'est pas traitée comme une nouvelle allocation.

Avant le dernier usage, drop, reset, déplacement et mutation incompatibles sont
refusés. Après ce dernier usage, drop/reset et réutilisation du slot restent
possibles sans réactiver un ancien accès. Le format du pointeur et le runtime C
ne changent pas ; il n'y a ni nouvelle allocation ni destruction pour la seule
réception d'une référence.

Le vérificateur des appels accepte les noms des références déjà existantes et
les résultats &Int de sous-appels, tout en refusant le nom d'une allocation non
explicitement empruntée. Les paramètres de sources portent désormais le fait
qu'ils sont déjà empruntés, séparément de leur capacité mutable. L'inférence des
effets vérifie également la distinction source locale/paramètre. L'inférence
des résultats et des contraintes refuse les opérateurs & sur des références.
Le traitement contextuel `returning_reference` a été supprimé du compilateur.
Le parcours de vérification reste modulaire ; le backend C reste spécialisé.

## Validation et état des preuves

Le précédent cycle avait 632 méthodes réussies en standard et sous UBSan.
Quinze méthodes nouvelles portent sur les formes d'appel/retour, les références
imbriquées, la préservation des modes, les pools, les champs et les usages futurs.
Leur périmètre comprend **8 programmes admis exécutables** et **23 cas refusés**
par le vérificateur puis la compilation, plus un contrôle d'inférence seule
sur une fonction retournant &référence. Ces comptes décrivent les fixtures
nouvelles ; ils ne comptent pas tous les programmes internes aux suites globales.

Les fixtures des tests précédents et leurs générateurs ont été migrés vers la
syntaxe décidée. Les graphes d'entrée, ensembles de cibles attendus, graines,
valeurs et traces de destruction attendues n'ont pas été changés. Le contrôle
[de migration](../validation/reference-values-fixture-migration.json) conserve les
noms des méthodes et les secondes expressions des comparaisons d'assertions
pour 23 fichiers Python sauvegardés avant migration. Cela ne constitue pas une
preuve automatique de conservation de chaque oracle. Un ancien diagnostic
`emprunter directement` a été actualisé en `emprunt imbriqué`, en gardant son
programme interdit.

Les modèles bornés précédents sont réutilisés : routes de pools (40 graines),
frontières des champs &Int (32 scénarios), retours de porteurs (24 graines) et
cibles des retours directs (24 graines). Leurs rendus de programmes utilisent
les noms des paramètres empruntés sans changer les prédictions de leurs oracles.
Les modèles du nettoyage et l'oracle C du runtime font aussi partie des suites.

Cinq mutations spécifiques sont détectées dans des copies temporaires :
aplatir une référence dans l'inférence de résultat, autoriser l'emprunt implicite
d'un nom d'allocation, rejeter un argument nommé valide, rejeter un retour nommé
valide et oublier qu'un paramètre de pool est déjà emprunté. Les quatorze
mutations précédentes des champs, porteurs et retours directs sont également
détectées. Les quatre campagnes conservent les empreintes Python du projet.
Il ne s'agit pas d'un taux global de détection.

Les campagnes C des retours directs, porteurs et contrats de pools ont chacune
12 exécutions : trois programmes en O0, O2, Os et O2+UBSan. Les **36 exécutions**
satisfont leurs observations définies (valeurs, adresses, destructions, resets
et diagnostics d'épuisement), sans diagnostic UBSan. Une seule famille de
compilateur C est disponible. L'exemple CLI des retours directs est aussi
exécuté avec `return data` et relais par nom ; cette exécution CLI n'est pas
instrumentée par `CRUST_SANITIZE`.

Rapports : [mutations nouvelles](../validation/reference-values-mutations.json),
[mutations retours directs](../validation/reference-values-direct-mutations.json),
[mutations porteurs](../validation/reference-values-holder-mutations.json),
[mutations champs](../validation/reference-values-field-mutations.json),
[C retours directs](../validation/reference-values-direct-c.json),
[C porteurs](../validation/reference-values-holder-c.json),
[C pools](../validation/reference-values-pool-c.json).
Les deux suites globales sont terminées : **647 tests réussis en mode
standard (420.021 s)** et **647 sous UBSan (420.331 s)**.
Aucun test n'est sauté et aucun échec n'est laissé non résolu dans ces exécutions.
Le [bilan brut](../validation/reference-values-suites.json) conserve commandes,
sorties, durées, configurations et empreintes Python.

Les rapports bruts des cycles antérieurs conservent leurs anciennes sources et
empreintes. Les exemples documentaires ont été migrés vers la syntaxe actuelle ;
les mesures historiques ne sont pas présentées comme des exécutions du code
modifié. Pendant la migration, un audit rapide compilait les cas admis puis
sautait leur exécution C ; ses sauts et compteurs de modèles incomplets ne sont
pas des résultats de validation. Les suites finales exécutent les tests entiers.

## Limites

Aucun support de &&Int, de référence à une variable scalaire locale, de retour
&mut, de références de références, de graphe transitif ou d'affectation générale
d'alias n'est ajouté. Le sous-ensemble est synchrone, sans récursion ni FFI.
Les erreurs de durée de vie restent refusées plutôt que compensées par une
promotion, un changement de source ou un déplacement d'octets implicite.
Les modèles et parcours restent bornés ; inférence, vérificateur et backend
font partie de la base de confiance. Les niveaux d'optimisation C ne remplacent
pas une famille indépendante de compilateurs. ASan n'est pas relancé, compte
tenu de l'échec antérieur de cet hôte même sur un programme C vide ; voir
[SAFETY.md](SAFETY.md). Aucune preuve générale de sûreté n'est revendiquée.
