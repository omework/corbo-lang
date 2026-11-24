[English](OFFLINE_REFERENCE.md)

# Référence HTML hors ligne

`corboc doc` ouvre la référence installée dans le navigateur et la sert sur
`127.0.0.1`. Le système choisit un port disponible ; `--port PORT` permet de le
fixer et `--port 0` conserve le choix automatique. `--no-open` affiche seulement
l’URL. `Ctrl+C` arrête le serveur. Aucun manuel en ligne de commande n’est installé.

La référence contient les déclarations et membres de toute la STD, les sources
internes et leurs conditions de cible, ainsi que l’ABI C du runtime. Un catalogue
séparé décrit les types et API fournis par corboc : primitifs, références, tableaux,
tranches, tuples, appelables, allocations, collections natives, Result/Option,
handles, primitives et annotations. Les contrats compilateur/runtime sont
identifiés séparément des déclarations ordinaires.

Chaque type dispose d’une page avec signatures, méthodes et liens vers les
sources. Les champs privés restent privés. Le parcours du langage inclut les
exemples complets ; les guides historiques ne deviennent pas des garanties d’API.

Appuyez sur `/` ou `Ctrl/Cmd+K` pour rechercher. Plusieurs mots affinent les
résultats ; les flèches et Entrée ouvrent un résultat, Échap efface la recherche.
Les types des signatures et les paquets du menu sont cliquables.

Toutes les ressources sont locales, sans CDN ni police distante. Python sert à
la génération lors de l’installation, pas à l’exécution. Les fichiers sont placés
dans `PREFIX/share/corbo/docs/`, à côté de la STD épinglée. Le manifeste indique
la révision Corbo et l’empreinte du catalogue d’API du compilateur.

Le générateur est `corboc/scripts/stdlib_html.py` ; le catalogue est
`corboc/docs/BUILTIN_REFERENCE.json`. Le serveur est écrit en Corbo avec File/TCP ;
le code natif ouvre seulement le navigateur. Reconstruisez l’installation pour
actualiser la référence. Les commentaires source restent la référence pour les
API définies dans la STD ; on n’ajoute pas de faux corps de méthode pour les documenter.
