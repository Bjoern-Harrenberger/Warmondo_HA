# Warmondo für Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/github/v/release/Bjoern-Harrenberger/Warmondo_HA)](https://github.com/Bjoern-Harrenberger/Warmondo_HA/releases)

Bindet **Warmondo**-Wärmepumpen der **MULTIBETON GmbH** in Home Assistant ein.
Alle Werte der Anlage erscheinen in Home Assistant, die wichtigsten
Einstellungen lassen sich von dort aus ändern, Störungen werden gemeldet,
und Wärmemenge, Stromverbrauch und Arbeitszahl werden von selbst erfasst.

Unterstützt werden die Baureihen **WM-S, WM-M, WM-L und WM-XL**, als
Einzelgerät und als Kaskade mit bis zu acht Geräten.

*English summary at the end of this page.*

---

## Inhalt

- [Was Sie brauchen](#was-sie-brauchen)
- [Installation](#installation)
- [Einrichtung](#einrichtung)
- [Was Sie danach sehen](#was-sie-danach-sehen)
- [Einstellungen ändern](#einstellungen-ändern)
- [Störmeldung aufs Handy](#störmeldung-aufs-handy)
- [Energie-Dashboard](#energie-dashboard)
- [Häufige Fragen und Fehlersuche](#häufige-fragen-und-fehlersuche)
- [Hilfe und Kontakt](#hilfe-und-kontakt)

---

## Was Sie brauchen

- **Home Assistant** ab Version 2026.6.
- **Das Modbus-TCP-Gateway an der Regelung** der Wärmepumpe. Es verbindet
  die Regelung mit Ihrem Heimnetz. Ihr Installationsbetrieb richtet es bei
  der Inbetriebnahme ein.
- **Eine feste IP-Adresse für das Gateway.** Die Adresse finden Sie in der
  Weboberfläche des Gateways oder in der Geräteliste Ihres Routers. Damit
  sie sich nicht ändert, stellen Sie im Router „immer dieselbe IP-Adresse
  zuweisen“ ein.
- Für die Installation über HACS: [HACS](https://hacs.xyz) ist in Home
  Assistant installiert.

## Installation

### Über HACS (empfohlen)

[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Bjoern-Harrenberger&repository=Warmondo_HA&category=integration)

1. Auf den Knopf oben klicken – oder in HACS oben rechts über die drei
   Punkte → *Benutzerdefinierte Repositories* die Adresse
   `https://github.com/Bjoern-Harrenberger/Warmondo_HA` mit dem Typ
   *Integration* hinzufügen.
2. **Warmondo** in HACS auswählen und *Herunterladen* klicken.
3. Home Assistant neu starten: *Einstellungen → System → Neu starten*.

Updates bietet HACS danach von selbst an.

### Von Hand

Den Ordner `custom_components/multibeton` aus der
[aktuellen Version](https://github.com/Bjoern-Harrenberger/Warmondo_HA/releases)
nach `config/custom_components/multibeton` kopieren, zum Beispiel über das
Add-on *Samba share*, und Home Assistant neu starten.

## Einrichtung

[![Integration hinzufügen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=multibeton)

Auf den Knopf klicken – oder unter *Einstellungen → Geräte & Dienste →
Integration hinzufügen* nach **Warmondo** suchen. Im Dialog:

| Feld | Was eintragen |
| :--- | :--- |
| **Name** | Freilassen. Nur nötig, wenn Sie mehr als eine Wärmepumpe einbinden – dann z. B. „Warmondo Keller“. |
| **Baureihe** | Die Baureihe vom Typenschild, z. B. *WM-L*. Die Regelung meldet sie nicht, deshalb wird sie hier gewählt. |
| **IP-Adresse des Gateways** | Die feste IP-Adresse des Modbus-TCP-Gateways, z. B. `192.168.1.50`. |

Das genügt in aller Regel. Unter **Erweitert** stehen Port (502),
Modbus-Adresse der Regelung (1) und Übertragungsformat (`socket`) – diese
Werte nur ändern, wenn das Gateway ausdrücklich anders eingestellt ist.
Dort findet sich auch **Nur lesen**: Dann legt die Integration keine
Bedienelemente an, die Anlage lässt sich aus Home Assistant heraus nicht
verstellen – gedacht für Vorführanlagen oder reine Überwachung.

Beim Speichern liest die Integration die Regelung einmal aus. Klappt das,
ist die Anlage eingerichtet. Spätere Änderungen, etwa eine neue IP-Adresse,
gehen über *Geräte & Dienste → Warmondo → drei Punkte → Neu konfigurieren*;
dabei bleiben alle Geräte, Werte und Verläufe erhalten.

## Was Sie danach sehen

Die Integration legt **ein Gerät für die Anlage** an und **ein Gerät je
Wärmepumpe** der Kaskade: den *Master* und, falls vorhanden, *Slave 01#*,
*Slave 02#* und so weiter. Wie viele es sind, liest sie aus der Regelung –
auch eine Erweiterung um ein weiteres Gerät erkennt sie selbst.

**Am Anlagengerät**

- **Status** – Betriebszustand, Betriebsart, Abtauung, Frostschutz,
  Störung, Hauptschalter, Zonen und Warmwasser.
- **Temperaturen** – Außen-, Raum-, Vorlauf- und Speichertemperaturen.
- **Leistung und Effizienz** – Heiz-, Kühl- und Warmwasserleistung, die
  aufgenommene elektrische Leistung und die momentane Leistungszahl (COP),
  gesamt und je Betriebsart.
- **Bilanz** – *Wärmemenge* und *Strommenge* als fortlaufende Zähler sowie
  Wärmemenge, Strommenge und **Arbeitszahl über 24 Stunden, 7, 30 und 365
  Tage**. Die Arbeitszahl ist erzeugte Wärme geteilt durch verbrauchten
  Strom – die Kennzahl, an der sich die Effizienz über die Zeit ablesen
  lässt. Die Werte für 30 und 365 Tage füllen sich naturgemäß erst nach
  und nach.
- **Heiz- und Kühlkurven** – die gewählte Kurve je Zone als Diagramm,
  dazu der aktuelle Arbeitspunkt: bei welcher Außentemperatur die Kurve
  gerade welche Vorlauftemperatur fordert. Die Diagramme sind im Breitformat
  angelegt und wirken am besten auf voller Breite: im Dashboard eine
  *Bild-Entität*-Karte hinzufügen und unter *Layout* die volle Breite
  wählen. Auf dem Handy passt sich die Schrift von selbst an.
- **Betriebsstunden und Starts** – Verdichter gesamt und je Betriebsart,
  Zusatzheizstäbe, Abtauvorgänge.
- **Aktive Störungen** – im Wortlaut der Regelung.

**An jedem Wärmepumpengerät (Master, Slave)**

- Leistung, Verdichterdrehzahl, Vor- und Rücklauf, Volumenstrom.
- Kältekreis: Hoch- und Niederdruck, Gas- und Lamellentemperaturen,
  Überhitzung.
- Abtauung, Heizstäbe, Pumpen und Ventile, Störungen dieses Geräts.

Werte für Fachleute – etwa Ventilstellungen und Frequenzumrichterdaten –
sind zunächst ausgeblendet. Sie lassen sich in der Entitätenliste des
Geräts jederzeit einschalten.

**Wenn ein Wert „Nicht verfügbar“ zeigt**, ist der zugehörige Fühler an
Ihrer Anlage in aller Regel nicht verbaut (zum Beispiel Solar- oder
Pufferfühler). Die Regelung meldet das so, und die Integration zeigt dann
bewusst keinen Phantasiewert an.

## Einstellungen ändern

Über Home Assistant lassen sich die Einstellungen ändern, die auch an der
Regelung für Benutzer freigegeben sind: Hauptschalter, Zonen und
Warmwasser ein/aus, Betriebsart, Leistungsmodus, Raum-, Vorlauf- und
Warmwasser-Sollwerte, Heiz- und Kühlkurve je Zone, die freie Kurve 9,
Desinfektion und Urlaubsbetrieb. **Einstellungen für Inbetriebnahme,
Service und Werk sind nur lesbar** – sie bleiben Ihrem Fachbetrieb
vorbehalten.

**Bitte beachten Sie bei Automatisierungen:** Die Regelung speichert ihre
Sollwerte dauerhaft in einem Speicherbaustein, der nur eine begrenzte Zahl
von Schreibvorgängen verträgt. Automatisierungen sollten deshalb nur
schreiben, wenn sich der Wert tatsächlich ändert – nicht in kurzen
Abständen immer wieder. Beispiele, die das richtig machen, liegen in
[`docs/beispiel-automationen`](docs/beispiel-automationen).

## Störmeldung aufs Handy

Bei einer Störung erscheint in Home Assistant von selbst eine
**Benachrichtigung** mit dem Wortlaut der Regelung und dem Gerät, an dem
sie auftritt. Sie verschwindet, sobald die Störung behoben ist.

Für eine **Nachricht aufs Handy** liegt eine fertige Vorlage bei. Dazu muss
die Home-Assistant-App auf dem Handy installiert und angemeldet sein.

[![Vorlage importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FBjoern-Harrenberger%2FWarmondo_HA%2Fblob%2Fmaster%2Fblueprints%2Fautomation%2Fmultibeton%2Fwarmondo_stoermeldung.yaml)

1. Auf den Knopf klicken und die Vorlage importieren.
2. *Automatisierung aus Vorlage erstellen*, das Handy auswählen,
   speichern.

## Energie-Dashboard

Die Zähler **Wärmemenge** und **Strommenge** lassen sich direkt im
Energie-Dashboard von Home Assistant verwenden: *Einstellungen →
Dashboards → Energie*, unter *Einzelne Geräte* die *Strommenge* der
Wärmepumpe hinzufügen.

Die Zähler entstehen aus den Leistungswerten, die die Regelung alle 30
Sekunden meldet. Sie beginnen bei der Einrichtung bei null und zählen ab
dann weiter, auch über Neustarts hinweg.

## Häufige Fragen und Fehlersuche

**Bei der Einrichtung erscheint „Keine Verbindung zur Regelung“.**
1. Ist das Gateway eingeschaltet und die IP-Adresse richtig? Die
   Weboberfläche des Gateways muss sich im Browser unter dieser Adresse
   öffnen lassen.
2. Unter *Erweitert* das andere Übertragungsformat wählen (`rtu` statt
   `socket`) und erneut versuchen.
3. Port und Modbus-Adresse mit den Einstellungen des Gateways
   vergleichen (üblich: 502 und 1).

**Alle Werte stehen plötzlich auf „Nicht verfügbar“.** Die Verbindung zum
Gateway ist unterbrochen. Die Integration versucht es alle 30 Sekunden neu
und verbindet sich von selbst wieder, sobald das Gateway erreichbar ist.
Hilft das nicht, Gateway kurz stromlos machen.

**Ein einzelner Wert ist dauerhaft „Nicht verfügbar“.** Der Fühler ist an
Ihrer Anlage nicht verbaut – siehe oben.

**Die Arbeitszahl zeigt keinen Wert.** Sie erscheint erst, wenn im
Zeitraum mindestens 0,5 kWh Strom verbraucht wurden. Nach der Einrichtung
und bei geringer Last dauert das eine Weile.

**Es erscheint der Hinweis „Baureihe passt nicht zur Anlage“.** Die bei
der Einrichtung gewählte Baureihe passt nicht zur Nennspannung, die die
Anlage meldet. Bitte die Baureihe auf dem Typenschild prüfen und über
*Neu konfigurieren* korrigieren.

**Wie aktualisiere ich?** HACS zeigt neue Versionen von selbst an. Nach
dem Herunterladen Home Assistant neu starten.

## Hilfe und Kontakt

**Bei Fragen zur Wärmepumpe und zu dieser Integration:**

> **MULTIBETON GmbH**
> Heuserweg 23
> 53842 Troisdorf
>
> Telefon: [+49 2241 252000](tel:+492241252000)
> E-Mail: [waermepumpe@multibeton.de](mailto:waermepumpe@multibeton.de)

**Diagnosedaten mitschicken:** Bei technischen Fragen hilft uns eine
Diagnosedatei sehr. Sie enthält alle Werte, die die Integration aus der
Regelung liest, und keine Zugangsdaten; die IP-Adresse des Gateways ist
darin unkenntlich gemacht.
*Einstellungen → Geräte & Dienste → Warmondo → drei Punkte →
Diagnosedaten herunterladen* und die Datei an
[waermepumpe@multibeton.de](mailto:waermepumpe@multibeton.de) senden.

Fehler in der Integration können Sie auch direkt als
[Issue auf GitHub](https://github.com/Bjoern-Harrenberger/Warmondo_HA/issues)
melden.

---

## English summary

Home Assistant integration for **Warmondo** air-to-water heat pumps by
**MULTIBETON GmbH** (models WM-S, WM-M, WM-L, WM-XL; single units and
cascades of up to eight). It talks Modbus TCP to the gateway at the
controller and provides one device for the plant plus one per unit, live
values, user-level settings, fault notifications, heating/cooling curve
diagrams, and energy counters with performance factors over 24 hours, 7,
30 and 365 days.

Install through HACS as a custom repository (category *Integration*),
restart, then add **Warmondo** under *Settings → Devices & services*. The
gateway's IP address is usually all the setup needs. Only parameters the
controller releases at user level are writable; commissioning, service and
factory settings are read-only.

Support: MULTIBETON GmbH, +49 2241 252000,
[waermepumpe@multibeton.de](mailto:waermepumpe@multibeton.de).

## Lizenz

Copyright © 2026 MULTIBETON GmbH. Veröffentlicht unter der MIT-Lizenz –
siehe [`LICENSE`](LICENSE). „Warmondo“ und „MULTIBETON“ sind Namen der
MULTIBETON GmbH; die Lizenz erstreckt sich nicht auf sie.
