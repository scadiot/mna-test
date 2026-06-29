# Chapitre 10 — Les sources et leurs formes d'onde

> *Où l'on apprend qu'une source est faite de deux idées séparées — « quelle forme » et « comment se brancher » — et où le temps fait sa première vraie apparition dans le simulateur.*

## 10.1 Une source, deux questions indépendantes

Quand on parle d'une « source », deux questions distinctes se posent :

1. **Quelle est sa forme d'onde ?** Une valeur constante ? Une sinusoïde ? Une impulsion brève ? Un signal carré qui clignote ?
2. **Comment se branche-t-elle ?** Impose-t-elle une **tension** (chapitre 7) ou injecte-t-elle un **courant** (chapitre 11) ?

Le simulateur sépare proprement ces deux préoccupations. La **forme d'onde** est un petit objet autonome (dans [simulator/sources.py](../../simulator/sources.py)), et la **manière de se brancher** est un composant (`VoltageSource` ou `CurrentSource`) qui *contient* une forme d'onde. C'est un exemple de bonne conception logicielle : on peut combiner librement n'importe quelle forme avec n'importe quel mode de branchement, sans dupliquer de code.

Ce chapitre traite de la première question. Le chapitre 11 traitera de la seconde.

## 10.2 Le contrat : une fonction du temps

Toutes les formes d'onde partagent une unique méthode : `voltage(t)`, qui répond à la question *« quelle est ta valeur à l'instant t ? »*. C'est le **contrat** qui les rend interchangeables. Le composant source, à chaque pas de simulation, appelle simplement `self.source.voltage(t)` pour connaître la valeur à imposer (vous l'avez vu dans le stamping du chapitre 7).

> Une petite franchise de vocabulaire s'impose : la méthode s'appelle `voltage`, mais pour une **source de courant** elle renvoie en réalité une valeur de **courant** (en ampères). Le nom trahit l'origine du code, pas la grandeur. Voyez-la comme *« la valeur imposée à l'instant t »*, quelle que soit son unité.

C'est ici, dans cette dépendance en `t`, que le temps entre pour la première fois dans notre histoire. Jusqu'au chapitre 9, tout était statique. Désormais, le second membre `b` du système peut **changer à chaque pas**.

## 10.3 La source continue (DC)

La plus simple : une valeur constante, indépendante du temps ([sources.py](../../simulator/sources.py#L4-L11)).

```python
class DCSource:
    """Source de tension ou de courant continu (valeur constante)."""
    def __init__(self, amplitude):
        self.amplitude = amplitude
    def voltage(self, t):
        return self.amplitude
```

`voltage(t)` ignore `t` et renvoie toujours `amplitude`. C'est la pile idéale, la tension d'alimentation stable. Tous nos exemples des chapitres précédents (la source de 6 V du diviseur) étaient des sources DC.

## 10.4 La source sinusoïdale

Le pain quotidien de l'électronique analogique et du secteur : une oscillation douce ([sources.py](../../simulator/sources.py#L14-L23)).

```python
class SineSource:
    """Source sinusoïdale : A * sin(2π * f * t + φ)."""
    def __init__(self, amplitude, frequency, phase=0.0):
        ...
    def voltage(self, t):
        return self.amplitude * math.sin(2 * math.pi * self.frequency * t + self.phase)
```

Trois paramètres définissent une sinusoïde :

- l'**amplitude** `A` : la valeur crête (en volts ou ampères) ;
- la **fréquence** `f` : le nombre d'oscillations par seconde (en **hertz**, Hz). Le facteur `2π` convertit la fréquence en *pulsation* `ω = 2πf`, car la fonction `sin` raisonne en radians ;
- la **phase** `φ` : le décalage à l'origine (en radians), qui permet de décaler la courbe dans le temps.

Cette forme d'onde est essentielle pour étudier le comportement *dynamique* d'un circuit : c'est en envoyant un sinus qu'on révèle l'effet des condensateurs et des bobines (Partie IV), qui filtrent différemment selon la fréquence.

## 10.5 L'impulsion (pulse)

Une bouffée unique entre deux instants ([sources.py](../../simulator/sources.py#L26-L35)).

```python
class PulseSource:
    """Impulsion rectangulaire unique entre t_start et t_end."""
    def voltage(self, t):
        return self.amplitude if self.t_start <= t <= self.t_end else 0.0
```

La valeur est `amplitude` pendant la fenêtre `[t_start, t_end]`, et `0` partout ailleurs. Idéale pour observer la **réponse transitoire** d'un circuit : on le « pousse » brièvement et on regarde comment il revient à l'équilibre — typiquement la charge puis la décharge d'un condensateur.

## 10.6 Le signal carré (square)

Une alternance périodique entre une valeur haute et zéro ([sources.py](../../simulator/sources.py#L38-L50)).

```python
class SquareSource:
    """Signal créneau périodique avec rapport cyclique (duty_cycle)."""
    def voltage(self, t):
        period = 1.0 / self.frequency
        position = (t % period) / period      # position dans la période, entre 0 et 1
        return self.amplitude if position < self.duty_cycle else 0.0
```

Deux idées à saisir :

- La **période** est l'inverse de la fréquence (`T = 1/f`). L'opérateur modulo `t % period` calcule *où l'on en est* dans le cycle courant — c'est ce qui rend le signal périodique.
- Le **rapport cyclique** (`duty_cycle`, entre 0 et 1) fixe la proportion du cycle passée « en haut ». À `0.5`, le signal est haut la moitié du temps (créneau symétrique) ; à `0.1`, seulement 10 % du temps (impulsions brèves et répétées).

Le signal carré est la signature du numérique et de la commande : horloges, modulation de largeur d'impulsion (PWM) pour piloter un moteur ou faire varier une luminosité, etc.

## 10.7 Le temps, vu d'en haut

Ce qu'il faut retenir au-delà des quatre formules : à chaque pas de simulation, le moteur fait avancer un instant `t`, et **redemande à chaque source sa valeur courante**. Une source DC répond toujours pareil ; les trois autres répondent différemment selon `t`. C'est ainsi qu'un circuit « prend vie » dans le temps, alors même que chaque pas individuel reste une résolution statique de `G·x = b` (chapitre 8).

Cette idée — *un problème dynamique résolu comme une succession de problèmes statiques* — est le cœur de la simulation temporelle. Elle atteindra sa pleine puissance à la Partie IV, lorsque les composants eux-mêmes (condensateur, bobine) auront besoin de se souvenir du pas précédent.

## 10.8 À retenir

- Une source = une **forme d'onde** (que faire) + un **mode de branchement** (tension ou courant, chapitre 11). Les deux sont **découplés** dans le code.
- Toutes les formes d'onde partagent le contrat `voltage(t)` : *« ta valeur à l'instant t »* (même si, pour une source de courant, cette valeur est un courant).
- Quatre formes : **DC** (constante), **sinus** (`A·sin(2πft+φ)`), **impulsion** (fenêtre unique), **créneau** (périodique, avec rapport cyclique).
- Le temps entre par les sources : le vecteur `b` peut **changer à chaque pas**. Mais chaque pas reste une résolution statique — un problème dynamique = une succession de problèmes statiques.

**Dans le prochain chapitre**, nous répondrons à la seconde question : une fois la forme choisie, faut-il imposer une **tension** ou injecter un **courant** ? Nous comparerons `VoltageSource` et `CurrentSource`, deux composants jumeaux mais profondément duals.
