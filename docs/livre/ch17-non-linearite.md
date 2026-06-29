# Chapitre 17 — Le défi de la non-linéarité

> *Où l'on rencontre des composants qui changent de comportement selon leur propre état, où l'on découvre pourquoi cela menace toute notre méthode — et comment le simulateur s'en tire par une ruse élégante, quoique imparfaite.*

## 17.1 Linéaire, non-linéaire : de quoi parle-t-on ?

Tous nos composants, jusqu'ici, partageaient une propriété cachée mais cruciale : la **linéarité**. Une résistance de `100 Ω` laisse passer `1 A` sous `100 V`, et `2 A` sous `200 V` : doublez la cause, vous doublez l'effet. La relation entre tension et courant est une droite. C'est cette linéarité qui permet de tout écrire sous la forme `G·x = b` — une matrice n'exprime, par nature, que des relations linéaires.

Une **diode** ne joue pas le jeu. Sous une faible tension directe, elle bloque presque tout courant. Passé un seuil (environ `0,6 V`), elle devient soudain très conductrice. Sa courbe courant-tension n'est pas une droite : c'est un coude brutal. Doubler la tension ne double pas le courant — il peut le multiplier par mille. La diode est **non-linéaire**.

Le **transistor** est pire encore : son comportement bascule entre plusieurs **régimes** (bloqué, actif, saturé) selon les tensions à ses bornes. Dans chaque régime, il agit comme un composant différent.

## 17.2 Pourquoi cela casse la MNA

Le problème est fondamental. Pour tamponner un composant dans la matrice (chapitre 6), il faut connaître sa conductance. Mais pour une diode, *la conductance dépend de la tension à ses bornes* — qui est précisément ce que l'on cherche à calculer !

On tombe sur un cercle vicieux :

> Pour construire la matrice, j'ai besoin de savoir si la diode est passante. Pour savoir si elle est passante, j'ai besoin de connaître sa tension. Pour connaître sa tension, j'ai besoin de résoudre la matrice. Pour résoudre la matrice, j'ai besoin de la construire…

La méthode des chapitres précédents — *assembler, puis résoudre, une fois* — ne fonctionne plus. La cause (la matrice) dépend de l'effet (la solution).

## 17.3 La solution rigoureuse : itérer (Newton-Raphson)

Les simulateurs professionnels (comme SPICE) brisent ce cercle par l'**itération**. À chaque pas de temps, ils répètent une boucle :

1. **Deviner** un état pour chaque composant non-linéaire.
2. **Construire et résoudre** la matrice avec ces hypothèses.
3. **Vérifier** : la solution est-elle cohérente avec les hypothèses ?
4. Sinon, **affiner** la devinette et recommencer — jusqu'à ce que tout concorde.

Cette méthode (une variante de l'algorithme de **Newton-Raphson**) est précise et générale. Mais elle est coûteuse : chaque pas de temps peut exiger plusieurs résolutions, et la boucle peut parfois refuser de converger. Pour un simulateur **temps réel** comme le nôtre, qui doit produire un résultat à cadence fixe (chapitre 21), cette imprévisibilité est un luxe difficile à s'offrir.

## 17.4 La ruse de notre simulateur : le pas précédent comme oracle

Notre moteur fait un choix pragmatique, taillé pour la simplicité et la vitesse plutôt que pour la précision absolue. Au lieu d'itérer *dans* un pas, il **regarde le pas précédent** pour décider de l'état des composants.

L'idée tient en une phrase : *« la diode était-elle passante juste avant ? Alors je suppose qu'elle l'est encore maintenant. »* On utilise l'état d'il y a un instant — disponible dans `prev_state` (chapitre 14) — comme **oracle** pour figer le régime du composant. Une fois le régime décidé, le composant redevient **linéaire** pour ce pas : une simple conductance, que l'on sait tamponner. Le cercle vicieux est rompu, non pas en itérant, mais en **décalant la décision d'un pas dans le passé**.

On appelle cette approche la **linéarisation par morceaux** (*piecewise-linear*) : la courbe non-linéaire est approchée par des segments de droite, et c'est le pas précédent qui choisit sur quel segment on se trouve.

## 17.5 Le marché : simplicité contre exactitude

Ce choix a un prix, qu'il faut connaître honnêtement :

**Les avantages :**
- **Pas de boucle** : un seul assemblage et une seule résolution par pas, comme pour les composants linéaires. La cadence reste prévisible.
- **Simplicité** : chaque composant non-linéaire devient, après décision, un cas déjà connu (conductance, source de courant).
- **Robustesse** : pas de risque de non-convergence d'une itération.

**Le coût :**
- **Un pas de retard** : si une diode bascule au beau milieu d'un intervalle `dt`, le simulateur ne s'en aperçoit qu'au pas *suivant*. Aux transitions rapides, le modèle réagit avec un léger décalage.
- **Risque d'oscillation** : ce décalage peut, dans certains montages, faire « clignoter » un composant entre deux états d'un pas à l'autre. Nous verrons au chapitre 18 que la diode emploie une petite astuce (un décalage de tension) précisément pour calmer ce phénomène.

C'est le compromis assumé d'un simulateur **pédagogique et temps réel** : on accepte une physique approchée en échange d'un code simple et d'une exécution fluide. Garder ce marché en tête évite bien des surprises à la lecture des chapitres suivants.

## 17.6 À retenir

- Un composant est **non-linéaire** quand sa relation tension-courant n'est pas une droite (diode : coude au seuil ; transistor : régimes multiples).
- Cela brise la MNA : la **conductance dépend de la solution** que l'on cherche — un cercle vicieux « cause ↔ effet ».
- La solution **rigoureuse** est d'**itérer** dans chaque pas (Newton-Raphson, façon SPICE) : précise mais coûteuse et imprévisible.
- Notre simulateur **ruse** : il consulte le **pas précédent** (`prev_state`) pour figer le régime, ce qui rend le composant **linéaire** pour le pas courant. C'est la **linéarisation par morceaux**.
- Marché assumé : **simplicité et vitesse** contre **un pas de retard** et un possible risque d'oscillation aux transitions.

**Dans le prochain chapitre**, nous appliquerons cette ruse au composant non-linéaire le plus simple : la **diode**. Nous verrons son modèle à deux états, et la petite astuce de décalage de tension qui l'empêche d'osciller.
