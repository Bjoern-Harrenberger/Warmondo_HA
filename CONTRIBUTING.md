# Mitwirken

Fehlermeldungen und Verbesserungsvorschläge sind willkommen – am besten als
[Issue](../../issues/new/choose). Bitte bei Fehlern die Diagnosedatei
anhängen (*Einstellungen → Geräte & Dienste → Warmondo → drei Punkte →
Diagnosedaten herunterladen*); sie enthält keine Zugangsdaten.

Für Fragen zur Wärmepumpe selbst ist der MULTIBETON-Service der richtige
Ansprechpartner: +49 2241 252000, waermepumpe@multibeton.de.

## Code

- Zweig von `master` abzweigen, Änderung als Pull Request einreichen.
- `scripts/lint` (Ruff) und `pytest` müssen ohne Befund durchlaufen; die CI
  prüft beides sowie Home Assistants eigene Validierung (`hassfest`) und
  die HACS-Prüfung.
- Registeradressen, Skalierungen und Grenzwerte kommen aus den
  Registertabellen des Herstellers, nicht aus Vermutungen.
- **Schreibbar wird nur, was die Typenparametertabelle der Stufe
  „Benutzer“ zuordnet.** Inbetriebnahme-, Service- und Werksparameter
  bleiben lesend, auch wenn das Register einen Schreibzugriff annähme. Ein
  Test in `tests/` prüft das.

`scripts/setup` und `scripts/develop` starten eine lokale
Home-Assistant-Entwicklungsinstanz. Der Aufbau des Repositorys folgt der
Vorlage [`ludeeus/integration_blueprint`](https://github.com/ludeeus/integration_blueprint).

## Lizenz

Beiträge stehen unter derselben MIT-Lizenz wie das Projekt.
