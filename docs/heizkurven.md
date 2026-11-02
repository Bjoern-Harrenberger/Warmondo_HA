# Die festen Kennlinien, in Zahlen

Vorlauf-Solltemperatur in °C bei der jeweiligen Außentemperatur. Die
Herstellerdokumentation benennt diese Kurven, beziffert sie aber nirgends;
die Werte hier sind von der Anzeige der Regelung abgelesen (Menü
*Heizkurve für Zone A*).

| Register&shy;wert | Kurve | 20 °C | 10 °C | 0 °C | −10 °C | −20 °C |
| ---: | :--- | ---: | ---: | ---: | ---: | ---: |
| 1 | Niedrige Temperatur 1 | 32 | 33 | 35 | 37 | 38 |
| 2 | Niedrige Temperatur 2 | 31 | 32 | 34 | 36 | 37 |
| 3 | Niedrige Temperatur 3 | 29 | 31 | 33 | 34 | 36 |
| 4 | Niedrige Temperatur 4 | 28 | 30 | 32 | 33 | 35 |
| 5 | Niedrige Temperatur 5 | 27 | 29 | 31 | 32 | 34 |
| 6 | Niedrige Temperatur 6 | 26 | 28 | 29 | 31 | 32 |
| 7 | Niedrige Temperatur 7 | 25 | 27 | 28 | 30 | 31 |
| 8 | Niedrige Temperatur 8 | 24 | 25 | 26 | 28 | 29 |
| 9 | Hohe Temperatur 1 | 50 | 51 | 53 | 54 | 55 |
| 10 | Hohe Temperatur 2 | 48 | 49 | 51 | 52 | 53 |
| 11 | Hohe Temperatur 3 | 47 | 48 | 50 | 51 | 52 |
| 12 | Hohe Temperatur 4 | 45 | 46 | 48 | 49 | 50 |
| 13 | Hohe Temperatur 5 | 43 | 44 | 46 | 47 | 48 |
| 14 | Hohe Temperatur 6 | 40 | 41 | 43 | 44 | 45 |
| 15 | Hohe Temperatur 7 | 38 | 39 | 41 | 42 | 43 |
| 16 | Hohe Temperatur 8 | 35 | 36 | 38 | 39 | 40 |

Registerwert 0 bedeutet *Deaktiviert*: dann gilt die von Hand
eingestellte Soll-Vorlauftemperatur. Die Werte 17 bis 20 stehen für die
frei definierbaren Kurven 9 bis 12 und sind hier nicht aufgeführt, weil
ihre Stützpunkte in den Benutzerparametern stehen.

## Hinweis zu „Hohe Temperatur 5“

Die Anzeige der Regelung beschriftet zwei Kurven gleich mit „Hohe
Temperatur 4“. Die Kurve mit 43/44/46/47/48 °C ist hier nach Reihenfolge
und gleichmäßigem Abstand der Reihe als *Hohe Temperatur 5* eingeordnet.

## Verwendung

Die Integration führt diese Tabellen in `multibeton_modbus/curve_tables.py`
und zeichnet die jeweils gewählte Kurve selbst als Bild-Entität
(*Heizkurve Zone A* usw.). `kurven_erzeugen.py` erzeugt daraus zusätzlich
die SVG-Grafiken in `docs/kurven/`.

## Die Kühlkurven

Ebenfalls von der Anzeige abgelesen (Menü *Zone A Cooling Curve*).
**Achtung, andere Achse als beim Heizen:** die Regelung zeigt hier 30 bis
−10 °C Umgebungstemperatur, nicht 20 bis −20.

| Register&shy;wert | Kurve | 30 °C | 20 °C | 10 °C | 0 °C | −10 °C |
| ---: | :--- | ---: | ---: | ---: | ---: | ---: |
| 1 | Niedrige Temperatur 1 | 5 | 11 | 16 | 16 | 16 |
| 2 | Niedrige Temperatur 2 | 6 | 12 | 17 | 17 | 17 |
| 3 | Niedrige Temperatur 3 | 7 | 13 | 18 | 18 | 18 |
| 4 | Niedrige Temperatur 4 | 8 | 14 | 19 | 19 | 19 |
| 5 | Niedrige Temperatur 5 | 9 | 15 | 20 | 20 | 20 |
| 6 | Niedrige Temperatur 6 | 10 | 16 | 21 | 21 | 21 |
| 7 | Niedrige Temperatur 7 | 11 | 17 | 22 | 22 | 22 |
| 8 | Niedrige Temperatur 8 | 12 | 18 | 23 | 23 | 23 |
| 9 | Hohe Temperatur 1 | 16 | 18 | 20 | 20 | 20 |
| 10 | Hohe Temperatur 2 | 17 | 19 | 21 | 21 | 21 |
| 11 | Hohe Temperatur 3 | 17 | 20 | 22 | 22 | 22 |
| 12 | Hohe Temperatur 4 | 18 | 21 | 23 | 23 | 23 |
| 13 | Hohe Temperatur 5 | 18 | 21 | 24 | 24 | 24 |
| 14 | Hohe Temperatur 6 | 19 | 22 | 24 | 24 | 24 |
| 15 | Hohe Temperatur 7 | 19 | 22 | 25 | 25 | 25 |
| 16 | Hohe Temperatur 8 | 20 | 23 | 25 | 25 | 25 |

Unterhalb von etwa 15 °C außen laufen alle Kurven waagerecht — die
Kühlung arbeitet dann mit festem Sollwert.

Daneben zeigt die Regelung die frei definierbaren Kurven: **2P-Kurve 9 und
10** als Zweipunktkurve (zum Beispiel 35 °C außen → 10 °C Vorlauf und
25 °C außen → 16 °C) sowie **SOF-Kurve 11 und 12** als Steigungskurve
(Steigung 1,0, Versatz 0). Deren Werte stehen in den Benutzerparametern
und sind deshalb hier nicht tabelliert.
