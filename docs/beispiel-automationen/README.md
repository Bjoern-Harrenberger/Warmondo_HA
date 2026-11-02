# Beispiel: Automationen

`warmondo-automationen.yaml` enthält fünf Automationen für den Kunden,
der mehr will als zusehen: Warmwasser in ein Zeitfenster legen, den
PV-Überschuss verheizen, vor einem Kälteeinbruch vorheizen, nachts
absenken, bei Abwesenheit in den Urlaubsbetrieb gehen.

Sie sind Beispiele, kein Lieferumfang. Nichts davon muss
nachinstalliert werden — alle verwendeten Dienste gehören zu Home
Assistant. Nur für die Wetterprognose braucht es eine
Wetter-Integration; `met.no` ist eingebaut, den DWD gibt es über HACS.

## Warum das in Home Assistant passiert und nicht in der Regelung

Die Regelung kennt keine von außen erreichbare Zeitsteuerung. Was sie
hat, ist ein Satz Sollwerte, der jederzeit beschreibbar ist. Zeitplan,
Wetterprognose und Logik liegen deshalb in Home Assistant, die Anlage
führt nur aus. Die Integration stellt die dafür nötigen Hebel schon
bereit: Betriebsart, Leistungsmodus, Vorlauf- und Raum-Sollwerte je
Zone, Warmwasser-Sollwert, Kurvenauswahl, die Zonen- und
Warmwasserschalter sowie den Urlaubsbetrieb.

## Drei Fallen

**Die Entity-IDs stimmen nicht.** Sie tragen den Gerätenamen als
Präfix. Heißt das Gerät "Warmondo WM-XL", wird aus
`switch.warmondo_warmwasser` ein `switch.warmondo_wm_xl_warmwasser`.
Einmal in den Entwicklerwerkzeugen nachsehen und ersetzen.

**Sollwerte landen im EEPROM der Regelung.** Das Bauteil verträgt eine
endliche Zahl von Schreibvorgängen. Jede Automation hier prüft deshalb
vorher, ob der Zielwert nicht ohnehin schon anliegt, und die
wetter- und leistungsgeführten arbeiten zusätzlich mit Hysterese und
Haltezeit. Wer diese Bedingungen herausnimmt, baut sich eine Automation,
die im Minutentakt schreibt — und die Steuerung hält das nicht aus.

**Im Kurvenbetrieb zieht der Vorlauf-Sollwert nicht.** Läuft die Zone
auf einer Heizkurve, kommt die Vorlauftemperatur aus der Kurve. Der
richtige Hebel ist dann der Raum-Sollwert oder ein Kurvenwechsel. Die
Vorheiz-Automation schreibt deshalb den Raum-Sollwert. Welcher Hebel an
einer konkreten Anlage wirkt, gehört vor dem Scharfschalten einmal von
Hand ausprobiert: Wert ändern und zusehen, ob sich die
Kennlinien-Vorlauftemperatur mitbewegt.

## Ob es etwas gebracht hat

Das beantworten die Arbeitszahlen über 24 Stunden, 7, 30 und 365 Tage
der Integration (Sensoren „Arbeitszahl …“). Eine Automation, die die Arbeitszahl
senkt, ist eine schlechte Automation — unabhängig davon, wie plausibel
sie klingt.
