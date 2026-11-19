[English](UTF8_STRINGS.md)

# Corbo — str, char et String UTF-8

Décisions validées dans la discussion, consignées le 5 novembre 2026.

Extension normative de [LANGUAGE_RULES.md](LANGUAGE_RULES.md), en complément des
[structures et méthodes](STRUCTURES_METHODS.md) et des
[régions grandissantes](GROWING_REGIONS.md). La consignation initiale était
documentaire. Le support implémenté depuis et ses limites sont suivis dans la
[matrice](VERIFICATION_MATRIX.md) et les rapports de cycle. Les exemples
normatifs ne constituent pas à eux seuls des preuves d'exécution.

## 1. Texte, octets et valeurs Unicode

**TX1 — str et littéraux statiques.** Le nom retenu est `str` en minuscule.
`&str` est une vue immuable sur une séquence d'octets UTF-8 valide, représentable
par une adresse et une longueur en octets. Un littéral comme `"été"` est stocké
dans les données statiques du programme : ses octets sont immuables et vivent
pendant toute l'exécution. Il ne demande ni slot de pool ni drop. Il n'a pas
besoin de terminateur nul pour délimiter la vue ; le détail ABI reste à définir.

Les littéraux entre guillemets doubles acceptent les échappements JSON
`\"`, `\\`, `\/`, `\b`, `\f`, `\n`, `\r`, `\t` et `\uXXXX`.
`XXXX` contient exactement quatre chiffres hexadécimaux. Deux échappements
Unicode peuvent former une paire de substituts pour un caractère hors du plan
multilingue de base. Un substitut isolé, un échappement inconnu ou un caractère
de contrôle brut est refusé. Les caractères Unicode peuvent aussi s’écrire
directement, par exemple `"é"` et `"\u00e9"` donnent les mêmes octets UTF-8.

**TX2 — Octet et char distincts.** `u8` est un entier non signé de 8 bits.
`char` désigne une valeur scalaire Unicode, pas nécessairement un caractère
visuel complet. Une lettre et un accent combinant peuvent être deux `char`.
Lire un octet ne réalise jamais de conversion implicite en `char`. Un `char`
décodé est une valeur indépendante des octets qui ont servi à le produire.

**TX3 — Longueurs explicites.** `texte.byte_len()` fournit la longueur utilisée
en octets de `str` ou de `String`. `caractere.utf8_len()` fournit le nombre
d'octets de l'encodage UTF-8 de ce `char`, de 1 à 4. Il ne s'agit ni d'un compte
de caractères visuels, ni nécessairement de la taille de représentation du
type `char` en mémoire. Pour `"été"`, byte_len vaut 5 et les positions des char
sont 0, 2 et 3.

## 2. Indexation, découpes et conversions

**TX4 — Découpe et emprunt explicite.** Une expression de découpe désigne une
portion de `str` ; les crochets ne créent pas automatiquement une référence.
On écrit `&texte[debut..fin]` pour obtenir un `&str` sans copie, avec fin exclue.
Les formes `&texte[..fin]`, `&texte[debut..]` et `&texte[..]` sont autorisées ;
les bornes omises sont 0 et byte_len. Les conditions sont
`0 <= debut <= fin <= byte_len`, avec deux bornes sur des frontières UTF-8.
La vue ne peut survivre aux octets d'origine ; les règles d'emprunt existantes
s'appliquent. Une annotation de type n'introduit pas le `&` manquant.

`&texte[..2]` pour `"été"` a le type `&str`, pas `&[u8]` : le type du receveur
et son API déterminent la vue produite. Le stockage interne en octets ne permet
pas d'éluder les frontières UTF-8 d'une découpe textuelle.

Une invalidité statiquement établie est refusée. Sinon, le contrôle précède
la construction de la vue ; un échec arrête le programme avec un diagnostic.

`texte.try_slice(debut..fin)` applique les mêmes contrôles et rend un `Result`.
Une plage invalide donne `Err(OutOfBounds)` ; si la plage est valide mais une
borne coupe un caractère, elle donne `Err(NotCharBoundary)`. Le succès donne
`Ok(&str)` sans copie des octets. Les bornes omises utilisent 0 et byte_len.
Le résultat conserve les contraintes d'emprunt de la source ; U1 impose son
usage explicite, même en cas d'erreur connue. Décision du brouillon 07.

**TX5 — Index simple d'octet.** `texte[i]` retourne la valeur `u8` à la position
en octets ; `&texte[i]` fournit `&u8`, pas `&str`. L'accès exige
`0 <= i < byte_len`, mais pas une frontière de char : un octet de continuation
est lisible. Ces accès sont retenus sur `&str` et `String`. Ils ne décodent pas
le texte et restent soumis aux contrôles de bornes.

**TX6 — char_at.** `texte.char_at(index)` décode un char commençant à cet index
en octets et retourne `Result<char, CharAtError>` :

- `OutOfBounds` si l'index est négatif ou supérieur ou égal à byte_len ;
- `NotCharBoundary` si l'octet visé n'est pas le début d'un char.

La fin du texte ne contient pas de char, même si elle est une frontière valide
pour une découpe. Il n'y a ni arrondi vers une autre position ni allocation.
La méthode a été introduite pour `&str` ; les éventuels raccourcis supplémentaires
sur `String` ne doivent pas introduire une conversion ou une copie cachée.

**TX7 — Conversion d'un texte entier en char.**
`char::from_str(texte)` retourne `Result<char, CharFromStrError>`. Le texte doit
contenir exactement une valeur scalaire Unicode. Les erreurs sont `Empty` et
`MultipleChars`. `"é"` donne un char malgré ses deux octets ; `"été"` échoue.
Cette conversion n'ignore jamais silencieusement la suite du texte. Elle
n'alloue pas et ne conserve pas d'emprunt dans le résultat char.

**TX8 — Validation depuis les octets.** `str::from_utf8(&octets)` retourne
`Result<&str, Utf8Error>`. Le succès construit une vue sans copie, après
validation de l'encodage ; l'erreur ne remplace pas automatiquement les octets
invalides. Le détail de `Utf8Error` reste ouvert. La référence obtenue conserve
les contraintes de durée et de partage des octets sources.

## 3. String et stockage grandissant

**TX9 — String encapsule Vector<u8>.** `String` possède un stockage grandissant
fondé sur un `Vector<u8>` interne et expose une API orientée texte, avec un
invariant : le contenu accessible est toujours du UTF-8 valide. Mutualiser les
mécanismes avec le vecteur n'expose pas automatiquement toutes ses opérations.
Sa construction par défaut produit un texte vide.

Cette décision d'architecture n'approuve pas à elle seule l'ensemble de l'API
générique `Vector<T>`. Le premier cas sur sa construction vide est seulement
proposé au moment de cette consignation.

**TX10 — Pool, région et nettoyage.** `pool<String>` fournit les slots contenant
les informations fixes ; le stockage grandissant associé utilise les stratégies
de data stacks/régions déjà retenues. `textes.new()` construit un String vide.
L'annotation actuelle est `#(directive, stack_region_max_size=1M)` avant un scope ; les
anciens noms proposés ne sont plus à utiliser. Les règles d'héritage, capacité,
limites et stabilité restent celles de G1–G12.

La destruction de String nettoie son stockage associé et restitue son slot,
sans double nettoyage. Les sous-vues ou tâches dépendantes peuvent empêcher
cette destruction selon les règles existantes. Le protocole interne exact entre
pool de descripteurs et région reste à implémenter ; aucune réallocation cachée
sur un autre allocateur n'est autorisée par ces décisions.

**TX11 — push(char).** `texte.push(caractere)` ajoute l'encodage complet du char
à la fin du texte. Avant écriture, tout l'encodage doit tenir dans la capacité
disponible. Aucun ajout ne laisse une séquence UTF-8 incomplète et les éléments
existants ne sont pas déplacés. L'opération exige un accès mutable compatible
avec les emprunts. Un dépassement suit la politique de limites déjà retenue.

**TX12 — Vue depuis String.** `let vue: &str = &texte[..];` emprunte le contenu
d'un String sans copie ni transfert de sa responsabilité de nettoyage. Les
sous-vues utilisent les mêmes découpes que TX4. Muter le String est refusé si
la vue doit encore être utilisée après cette mutation. Les règles de dernière
utilisation et de frontière de scope sont héritées, pas réarbitrées ici.

**TX13 — push_str.** `texte.push_str(source: &str)` copie les octets du texte
source à la fin du contenu. La source reste disponible ; son stockage n'est
pas transféré. La capacité de l'ajout complet est vérifiée avant toute écriture.
Le résultat reste UTF-8 valide et les éléments déjà présents ne bougent pas.
Receveur et arguments suivent les restrictions d'emprunt déjà établies.

**TX14 — pop.** `texte.pop()` retire le dernier char complet et retourne
`Option<char>` : `Some(caractere)` ou `None` pour une chaîne vide. None est un
cas d'enum, pas une référence nulle. Les octets conservés ne sont pas déplacés.
La longueur diminue et l'espace retiré devient réutilisable dans la région ;
la région reste réservée au String jusqu'à son nettoyage. Le résultat est une
valeur indépendante.

## 4. Mutation d'octets et stabilité

**TX15 — replace_byte.** `texte.replace_byte(index, octet)` retourne
`Result<u8, ByteReplaceError>`. Le succès remplace l'octet et restitue sa valeur
précédente. Les erreurs sont `OutOfBounds` pour un index négatif ou au moins égal
à byte_len, et `InvalidUtf8` si le texte résultant aurait un encodage invalide.
Toutes les vérifications précèdent la modification ; un échec laisse le contenu
inchangé. L'index peut viser un octet de continuation. La longueur et les
adresses des autres octets restent inchangées.

**TX16 — replace_bytes.** `texte.replace_bytes(debut, source)` remplace un bloc
par les octets source, sans insertion ni suppression. Le bloc remplacé contient
exactement autant d'octets que la source. L'intervalle doit tenir dans la
longueur courante, avec des calculs de tailles valides ; le texte résultant doit
être UTF-8 valide. Le retour est `Result<(), ByteReplaceError>` avec les mêmes
cas `OutOfBounds` et `InvalidUtf8`. Le succès ne fournit pas de copie collective
des anciens octets ; un échec n'altère rien.

La source est consultée par emprunt (par exemple `&tableau_octets`). Le résultat
du bloc entier est validé avant modification : ne pas remplacer cette opération
par une suite de replace_byte qui exigerait des étapes intermédiaires valides.
Le nombre de char peut changer, pas la longueur en octets ni les adresses des
octets conservés. Remplacer C3 A9 (`é`) par 61 62 (`ab`) est ainsi autorisé.

**TX17 — Pas d'accès mutable brut.** La lecture `texte[i]` et l'emprunt partagé
`&texte[i]` sont permis. Obtenir un `&mut u8` sur les octets du String est refusé,
même avec un receveur mutable ; une fonction pourrait sinon contourner la
validation UTF-8. L'affectation directe `texte[i] = octet` est également refusée.
Les écritures passent par les méthodes contrôlées de l'API String. Le vecteur
interne n'est pas exposé mutablement de façon à contourner cet invariant.

**TX18 — UTF-8, sens du texte et décalages.** Le type garantit l'encodage, pas
le sens du texte ni la conservation de ses caractères lors d'un remplacement
d'octets. Les modifications au milieu qui nécessitent de décaler les octets
suivants construisent un nouveau String ; le stockage ancien reste stable
jusqu'à sa destruction. Le coût de nouvelle allocation et de copie doit rester
visible ; les deux stockages peuvent coexister pendant la construction.

La proposition replace_char limitée aux remplacements de même largeur n'a pas
été retenue. La formulation intermédiaire « toute modification au milieu exige
un nouveau String » a été précisée par l'autorisation des remplacements d'octets
de longueur constante avec validation du résultat.

## 5. Copie, affichage et parcours

**TX19 — Pas de copie structurelle de String.** String n'est pas Copy car il
possède son stockage grandissant. Une structure qui contient un String n'est
donc pas structurellement Copy. `copy(original)` et `pool.copy(original)` sont
refusés pour un String : dupliquer son descripteur ne duplique pas son stockage.

Dupliquer le texte exige un nouveau String avec un stockage indépendant. Les
opérations déjà retenues suffisent : construire une destination, puis
`destination.push_str(&original[..])`. Une future méthode de duplication pourra
regrouper ces opérations, avec coût et source d'allocation explicites ; son nom
et sa signature ne sont pas encore fixés.

**TX20 — Affichage selon le type.** Le builtin print accepte un `&str` pour
transmettre du texte UTF-8 et un `char` pour afficher une valeur Unicode, sans
conversion implicite entre ces deux types ni création d'un String temporaire.
Afficher un &str contenant un seul char n'exige pas de convertir ce texte en
char. Pour un String, l'emprunt est explicite : `print(&texte[..])` ; l'appel
`print(texte)` n'est pas transformé automatiquement en emprunt. Les autres formes
de print déjà existantes ne sont pas retirées par ce cas.

Le stockage de str est bien une séquence d'octets, mais son type porte la
garantie UTF-8. L'affichage peut transmettre ces octets sans construire une
collection de char. La représentation de l'API de sortie reste distincte du
stockage de String.

Les itérateurs génériques et les méthodes `chars()`/`char_indices()` ont été
reportés. Le parcours par boucle explicite avec char_at et utf8_len suffit au
prototype de conception. Sur du UTF-8 déjà valide, vérifier une frontière puis
décoder un char à une position en octets demande au plus quatre octets : cette
opération peut être O(1), et un parcours complet O(n) en octets avec O(1) de
mémoire auxiliaire. Ce sont des objectifs algorithmiques, pas des mesures ni
des performances d'une implémentation déjà exécutée.

## 6. Exemples de conception

### Extraction explicite et frontière invalide

```rust
fn main() -> Int {
    let texte: &str = "été";
    let premier: &str = &texte[..2];
    print(premier);

    match texte.char_at(1) {
        Ok(caractere) => { print(caractere); return 1; },
        Err(CharAtError::OutOfBounds) => { return 2; },
        Err(CharAtError::NotCharBoundary) => { return 0; }
    }
}
```

Le texte a cinq octets. La position 1 est lisible avec texte[1], mais ne commence
pas un char. Les types d'erreur utilisés ici désignent les enums de l'API retenue,
pas des déclarations supplémentaires faites par chaque programme.

### Remplacement groupé valide sans étape intermédiaire exposée

```rust
fn main() -> Int {
    #(directive, stack_region_max_size=1M)
    {
        let mut textes = pool<String>(1);
        let mut texte: String = textes.new();
        texte.push_str("été");
        let octets: [u8; 2] = [0x61, 0x62];

        match texte.replace_bytes(0, &octets) {
            Ok(()) => {},
            Err(erreur) => { return 1; }
        }

        print(&texte[..]); // abté
        print(texte.byte_len()); // 5
        drop(-> texte);
    }
    return 0;
}
```

### Duplication indépendante, pas de copie de descripteur

```rust
fn main() -> Int {
    #(directive, stack_region_max_size=1M)
    {
        let mut textes = pool<String>(2);
        let mut original: String = textes.new();
        original.push_str("é");

        let mut copie: String = textes.new();
        copie.push_str(&original[..]);
        copie.push('!');

        drop(-> original);
        print(&copie[..]); // é!
        drop(-> copie);
    }
    return 0;
}
```

## 7. Propositions reportées et statut

- `truncate_bytes` et son type d'erreur ont été proposés, sans validation
  explicite avant la réorientation vers une API classique de String ; ils ne
  sont pas ajoutés aux opérations retenues dans ce document.
- Les méthodes classiques supplémentaires relèvent d'une API orientée texte.
  Ne réarbitrer que les nouveaux choix d'allocation, décalage, indexation et
  invariant UTF-8 ; les règles générales déjà retenues s'appliquent automatiquement.
- Les itérateurs et les deux méthodes de parcours restent reportés.
- Détail de Utf8Error, signatures exactes des vues d'octets et ABI des types :
  points à préciser lors de l'intégration. La politique des découpes est validée
  par le brouillon 07 et consignée en TX4.
- Conversion consommante String/Vector et méthode dédiée de duplication :
  aucune API supplémentaire n'est déduite de la seule représentation interne.
- Le vecteur vide même lorsque T n'a pas de défaut, les autres règles de
  vecteur et les compléments à String sont consignés dans
  [FOUNDATIONS_AND_VECTORS.md](FOUNDATIONS_AND_VECTORS.md).

Statut historique à la rédaction : TX1–TX20 étaient **N : non implémentés,
non vérifiés par exécution dans cette passe**. Le statut courant se trouve
dans VERIFICATION_MATRIX.md ; le cycle UTF8_TRY_SLICE_CYCLE.md couvre
l’intégration synchrone de la découpe faillible du brouillon 07. Les preuves des tableaux fixes, des champs et des anciens pools ne
constituent pas des preuves de validité UTF-8 ou de leurs interactions avec
String. Voir la [matrice](VERIFICATION_MATRIX.md) et le
[rapport documentaire](cycles/UTF8_STRINGS_CYCLE.md).
