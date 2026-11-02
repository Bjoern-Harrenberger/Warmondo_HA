/*
 * Warmondo dashboard - shipped with the integration, nothing to install.
 *
 * Two parts:
 *
 * - `warmondo-info-card`, a small card in the style of a Mushroom template
 *   card: coloured icon, a primary and a secondary line. Its text is not a
 *   template the user writes but one of the summaries below ("2 von 2
 *   Verdichtern laufen", "COP 5,1 - 21,9 kW Leistung aus 4,3 kW Strom"),
 *   computed here from the plant's entities.
 * - A dashboard strategy, offered under Settings -> Dashboards -> Add
 *   dashboard as "Warmondo". It lays the dashboard out from Home Assistant's
 *   own cards (tile, entities, heading, history graph, picture entity,
 *   markdown) plus the info card, and finds the integration's entities by
 *   translation key and device rather than by entity ID - so it fits every
 *   plant whatever its name, model, module count or read-only setting.
 *
 * Copyright MULTIBETON GmbH, MIT licensed.
 */

const PLATFORM = "multibeton";
const UNAVAILABLE = ["unavailable", "unknown"];

// ---------------------------------------------------------------------------
// helpers shared by card and strategy

function stateOf(hass, entityId) {
  return entityId ? hass.states[entityId] : undefined;
}

function isOn(hass, entityId) {
  return stateOf(hass, entityId)?.state === "on";
}

function has(hass, entityId) {
  const state = stateOf(hass, entityId);
  return !!state && !UNAVAILABLE.includes(state.state);
}

function num(hass, entityId) {
  const state = stateOf(hass, entityId);
  if (!state || UNAVAILABLE.includes(state.state)) return undefined;
  const value = Number(state.state);
  return Number.isFinite(value) ? value : undefined;
}

function fmt(hass, value, digits = 1) {
  if (value === undefined) return "–";
  return value.toLocaleString(hass.locale?.language || "de", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** The entity's state as Home Assistant would show it, unit included. */
function shown(hass, entityId) {
  const state = stateOf(hass, entityId);
  if (!state) return "–";
  return hass.formatEntityState ? hass.formatEntityState(state) : state.state;
}

const plural = (n, one, many) => (n === 1 ? one : many);

// ---------------------------------------------------------------------------
// the info card: one summary per "kind"

const KINDS = {
  plant: (hass, e) => ({
    icon: "mdi:heat-pump",
    color: "teal",
    primary: e.model || "Warmondo",
    secondary: `${shown(hass, e.state)} · ${shown(hass, e.mode)}`,
    entity: e.state,
  }),

  compressors: (hass, e) => {
    const n = num(hass, e.running) ?? 0;
    const g = num(hass, e.count) ?? 1;
    const run = Math.round(num(hass, e.run) ?? 0);
    const idle = Math.round(num(hass, e.idle) ?? 0);
    let primary;
    if (g === 1) primary = n > 0 ? "Verdichter läuft" : "Verdichter steht";
    else primary = `${n} von ${g} Verdichtern ${n === 1 ? "läuft" : "laufen"}`;
    const secondary =
      n > 0
        ? `seit ${run} Minuten · Stillstand davor ${idle} min`
        : `Stillstand seit ${idle} Minuten · davor ${run} min Lauf`;
    return { icon: "mdi:engine", color: n > 0 ? "green" : "grey", primary, secondary, entity: e.running };
  },

  faults: (hass, e) => {
    const text = stateOf(hass, e.faults)?.state;
    const ok = !text || text === "Keine Störung" || text === "none";
    return {
      icon: ok ? "mdi:check-circle-outline" : "mdi:alert-circle",
      color: ok ? "green" : "red",
      primary: "Aktive Störungen",
      secondary: ok ? "keine" : text,
      entity: e.faults,
    };
  },

  aux_plant: (hass, e) => {
    const state = stateOf(hass, e.active);
    const n = Number(state?.attributes?.modules_heating ?? 0);
    const g = Number(state?.attributes?.modules_total ?? 1);
    const w = num(hass, e.power) ?? 0;
    let primary;
    if (n === 0) primary = "Kein Heizstab in Betrieb";
    else if (g === 1) primary = "Heizstab läuft";
    else primary = `Heizstab läuft in ${n} von ${g} Geräten`;
    const secondary =
      w > 0
        ? `${fmt(hass, w, 0)} W von ${fmt(hass, num(hass, e.configured) ?? 0, 0)} W konfiguriert`
        : "derzeit keine Leistung";
    return { icon: "mdi:resistor", color: isOn(hass, e.active) ? "red" : "grey", primary, secondary, entity: e.active };
  },

  aux_short: (hass, e) => {
    const on = isOn(hass, e.active);
    return {
      icon: "mdi:resistor",
      color: on ? "red" : "grey",
      primary: "Zusatzheizung",
      secondary: on ? "in Betrieb" : "aus",
      entity: e.active,
    };
  },

  aux_module: (hass, e) => {
    const s1 = isOn(hass, e.rod1);
    const s2 = isOn(hass, e.rod2);
    let which = "aus";
    if (s1 && s2) which = "beide Stäbe";
    else if (s1) which = "Stab 1";
    else if (s2) which = "Stab 2";
    return {
      icon: "mdi:resistor",
      color: s1 || s2 ? "red" : "grey",
      primary: e.label ? `${e.label} — ${which}` : `Zusatzheizung ${which}`,
      secondary: s1 || s2 ? "läuft" : "Stab 1 und Stab 2 außer Betrieb",
      entity: e.rod1,
    };
  },

  cop_now: (hass, e) => {
    const c = num(hass, e.cop);
    let color = "grey";
    if (c !== undefined) color = c >= 4 ? "green" : c >= 3 ? "orange" : "red";
    return {
      icon: "mdi:gauge",
      color,
      primary: c === undefined ? "Verdichter steht" : `COP ${fmt(hass, c, 2)}`,
      secondary:
        c === undefined
          ? "wird erst ab 0,2 kW Aufnahme gebildet"
          : `${fmt(hass, num(hass, e.out), 2)} kW Leistung aus ${fmt(hass, num(hass, e.in), 2)} kW Strom`,
      entity: e.cop,
    };
  },

  cop_mode: (hass, e) => {
    const c = num(hass, e.cop);
    return {
      icon: e.icon,
      color: c === undefined ? "grey" : e.color,
      primary: c === undefined ? `${e.label} steht` : `${e.label} — COP ${fmt(hass, c, 2)}`,
      secondary:
        c === undefined
          ? "läuft gerade nicht"
          : `${fmt(hass, num(hass, e.out), 2)} kW aus ${fmt(hass, num(hass, e.in), 2)} kW Strom`,
      entity: e.cop,
    };
  },

  runtime: (hass, e) => {
    const h = num(hass, e.hours) ?? 0;
    const s = num(hass, e.starts) ?? 0;
    const total = num(hass, e.total) ?? 0;
    let secondary;
    if (s === 0 || h === 0) secondary = "noch nie gelaufen";
    else {
      secondary = `${Math.round((h * 60) / s)} Minuten je Lauf`;
      if (e.total && total > 0) secondary += ` · ${Math.round((100 * h) / total)} % der Laufzeit`;
    }
    return {
      icon: e.icon,
      color: e.color,
      primary: `${e.label} ${fmt(hass, h, 0)} h · ${s} ${plural(s, "Start", "Starts")}`,
      secondary,
      entity: e.hours,
    };
  },

  curve_demand: (hass, e) => ({
    icon: "mdi:chart-bell-curve-cumulative",
    color: "teal",
    primary: has(hass, e.flow) ? `Kurve fordert ${fmt(hass, num(hass, e.flow))} °C Vorlauf` : "Kurve fordert nichts",
    secondary: has(hass, e.ambient)
      ? `bei ${fmt(hass, num(hass, e.ambient))} °C Außentemperatur`
      : "Außentemperatur nicht verfügbar",
    entity: e.flow,
  }),

  locked: (hass, e) => ({
    icon: "mdi:lock-outline",
    color: "grey",
    primary: `${e.label} ${shown(hass, e.setpoint)}`,
    secondary: "von der Kennlinie geführt, nicht einstellbar",
    entity: e.setpoint,
  }),

  pumps: (hass, e) => {
    const running = e.list.filter(([id]) => isOn(hass, id)).map(([, label]) => label);
    const n = running.length;
    let primary = `${n} Pumpen laufen`;
    if (n === 0) primary = "Keine Pumpe läuft";
    else if (n === 1) primary = "Eine Pumpe läuft";
    return {
      icon: "mdi:pump",
      color: n ? "blue" : "grey",
      primary,
      secondary: n ? running.join(", ") : "Die Hydraulik der Anlage steht",
      entity: e.list[0]?.[0],
    };
  },

  valve: (hass, e) => {
    const state = stateOf(hass, e.valve)?.state;
    let secondary = "nicht lesbar";
    if (state === "on") secondary = e.on;
    else if (state === "off") secondary = e.off;
    return {
      icon: "mdi:valve",
      color: state === "on" && e.highlight ? "blue" : "grey",
      primary: e.label,
      secondary,
      entity: e.valve,
    };
  },

  signals: (hass, e) => {
    const active = e.list.filter(([id]) => isOn(hass, id)).map(([, label]) => label);
    const n = active.length;
    return {
      icon: "mdi:import",
      color: n ? "blue" : "grey",
      primary: n === 0 ? "Keine externe Anforderung" : `${n} ${plural(n, "Signal liegt", "Signale liegen")} an`,
      secondary: n ? active.join(", ") : "Die Anlage regelt nach ihren eigenen Sollwerten",
      entity: e.list[0]?.[0],
    };
  },

  sg_ready: (hass, e) => {
    const evu = isOn(hass, e.evu);
    const sg = isOn(hass, e.sg);
    if (evu && !sg) {
      return {
        icon: "mdi:lightning-bolt",
        color: "green",
        primary: "Kraftbetrieb erzwungen",
        secondary: "Warmwasser zuerst, danach Heizen oder Kühlen",
        entity: e.evu,
      };
    }
    if (sg) {
      return {
        icon: "mdi:speedometer-slow",
        color: "orange",
        primary: "Leistungsaufnahme begrenzt",
        secondary: "Die Anlage nimmt höchstens 4000 W auf",
        entity: e.sg,
      };
    }
    return {
      icon: "mdi:transmission-tower",
      color: "grey",
      primary: "Normalbetrieb",
      secondary: "Kein Netzsignal · die Anlage folgt dem Leistungsmodus",
      entity: e.sg,
    };
  },

  work_figure: (hass, e) => {
    const c = num(hass, e.figure);
    let color = "grey";
    if (c !== undefined) color = c >= 4 ? "green" : c >= 3 ? "orange" : "red";
    return {
      icon: e.icon || "mdi:chart-line",
      color,
      primary: "Arbeitszahl",
      secondary:
        c === undefined ? "sammelt noch Daten" : `${fmt(hass, c, 2)} Kilowattstunden Wärme je Kilowattstunde Strom`,
      entity: e.figure,
    };
  },

  module_cop: (hass, e) => {
    const c = num(hass, e.cop);
    return {
      icon: "mdi:gauge",
      color: c === undefined ? "grey" : "green",
      primary: c === undefined ? "Verdichterzahl" : `Verdichterzahl ${fmt(hass, c, 2)}`,
      secondary: c === undefined ? "Verdichter steht" : "Wärme je kW Verdichterleistung",
      entity: e.cop,
    };
  },
};

class WarmondoInfoCard extends HTMLElement {
  setConfig(config) {
    if (!config.kind || !KINDS[config.kind]) throw new Error(`Unbekannte Karte: ${config.kind}`);
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 1;
  }

  getGridOptions() {
    return { columns: 12, rows: 1, min_columns: 6 };
  }

  _render() {
    if (!this._hass || !this._config) return;
    const info = KINDS[this._config.kind](this._hass, this._config.e || {});
    const key = JSON.stringify(info);
    if (key === this._last) return;
    this._last = key;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.innerHTML = `
        <style>
          ha-card { height: 100%; box-sizing: border-box; padding: 10px; display: flex;
                    align-items: center; gap: 10px; cursor: pointer; }
          .icon { flex: none; width: 36px; height: 36px; border-radius: 18px;
                  display: flex; align-items: center; justify-content: center; }
          .icon ha-icon { --mdc-icon-size: 24px; }
          .text { min-width: 0; display: flex; flex-direction: column; }
          .primary { font-weight: 500; font-size: 14px; line-height: 20px;
                     color: var(--primary-text-color); white-space: nowrap;
                     overflow: hidden; text-overflow: ellipsis; }
          .secondary { font-size: 12px; line-height: 16px; color: var(--secondary-text-color);
                       white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        </style>
        <ha-card>
          <div class="icon"><ha-icon></ha-icon></div>
          <div class="text"><span class="primary"></span><span class="secondary"></span></div>
        </ha-card>`;
      this.shadowRoot.querySelector("ha-card").addEventListener("click", () => {
        if (!this._entity) return;
        this.dispatchEvent(
          new CustomEvent("hass-more-info", { detail: { entityId: this._entity }, bubbles: true, composed: true })
        );
      });
    }
    this._entity = info.entity;
    // The same palette the tile card draws from, so both kinds of card match.
    const color = info.color === "grey" ? "var(--disabled-color, #bdbdbd)" : `var(--${info.color}-color)`;
    const icon = this.shadowRoot.querySelector(".icon");
    icon.style.background = `color-mix(in srgb, ${color} 20%, transparent)`;
    icon.style.color = color;
    this.shadowRoot.querySelector("ha-icon").setAttribute("icon", info.icon);
    this.shadowRoot.querySelector(".primary").textContent = info.primary;
    this.shadowRoot.querySelector(".secondary").textContent = info.secondary || "";
  }
}

if (!customElements.get("warmondo-info-card")) {
  customElements.define("warmondo-info-card", WarmondoInfoCard);
}

// ---------------------------------------------------------------------------
// the dashboard strategy

/** Entities of one device, looked up by translation key. */
class DeviceEntities {
  constructor(hass, deviceId) {
    this.hass = hass;
    this.device = hass.devices[deviceId];
    this.byKey = {};
    for (const entry of Object.values(hass.entities)) {
      if (entry.platform !== PLATFORM || entry.device_id !== deviceId || entry.hidden || !entry.translation_key) {
        continue;
      }
      (this.byKey[entry.translation_key] ||= []).push(entry.entity_id);
    }
  }

  /** The entity for `key`, a control before a read-only mirror. */
  get(key) {
    const order = ["switch", "select", "number", "button", "image", "binary_sensor", "sensor"];
    return [...(this.byKey[key] || [])].sort(
      (a, b) => order.indexOf(a.split(".")[0]) - order.indexOf(b.split(".")[0])
    )[0];
  }

  /** The entity for `key` only if the controller reports a value for it. */
  fitted(key) {
    const id = this.get(key);
    return has(this.hass, id) ? id : undefined;
  }
}

const compact = (list) => list.filter(Boolean);
const FULL = { grid_options: { columns: 12 } };
const DIVIDER = { type: "divider" };

function heading(text, icon, subtitle = false) {
  const card = { type: "heading", heading: text };
  if (icon) card.icon = icon;
  if (subtitle) card.heading_style = "subtitle";
  return card;
}

function section(title, icon, cards) {
  const body = compact(cards);
  if (!body.some((card) => card.type !== "heading")) return undefined;
  return { type: "grid", cards: [heading(title, icon), ...body] };
}

/** A full-width tile, like a Mushroom entity card. */
function tile(entity, name, color, extra = {}) {
  if (!entity) return undefined;
  const card = { type: "tile", entity, name, ...FULL, ...extra };
  if (color) card.color = color;
  const domain = entity.split(".")[0];
  if (domain === "select") card.features = [{ type: "select-options" }];
  if (domain === "number") card.features = [{ type: "numeric-input", style: "buttons" }];
  if (domain === "switch") card.tap_action = { action: "toggle" };
  if (domain === "button") card.tap_action = { action: "toggle" };
  return card;
}

function info(kind, e) {
  return { type: "custom:warmondo-info-card", kind, e, ...FULL };
}

function entities(title, rows) {
  const list = rows.filter((r) => r && (r.type || r.entity));
  if (!list.some((r) => r.entity)) return undefined;
  const card = { type: "entities", entities: list, ...FULL };
  if (title) card.title = title;
  return card;
}

function row(entity, name, icon) {
  if (!entity) return undefined;
  return icon ? { entity, name, icon } : { entity, name };
}

function when(card, entity, state) {
  if (!card || !entity) return card;
  return { ...card, visibility: [{ condition: "state", entity, state }] };
}

function unless(card, entity, state) {
  if (!card || !entity) return card;
  return { ...card, visibility: [{ condition: "state", entity, state_not: state }] };
}

// -- views -------------------------------------------------------------------

function overview(dev, model) {
  const g = (k) => dev.get(k);
  const zone = (letter, actual) => {
    const heatCurve = g(`curve_select_heating_zone_${letter}`);
    const coolCurve = g(`curve_select_cooling_zone_${letter}`);
    const heatSet = g(`heating_setpoint_zone_${letter}`);
    const coolSet = g(`cooling_setpoint_zone_${letter}`);
    return [
      tile(g(`zone_${letter}_on`), `Zone ${letter.toUpperCase()}`, "green"),
      tile(actual, "Vorlauf (Ist)", "red"),
      tile(heatCurve, "Heizkurve"),
      info("curve_demand", {
        flow: g(`sensors_curve_flow_temp_zone_${letter}`),
        ambient: g("system_status_curve_ambient_temp"),
      }),
      when(tile(heatSet, "Heizen Soll"), heatCurve, "disabled"),
      unless(info("locked", { label: "Heizen Soll", setpoint: heatSet }), heatCurve, "disabled"),
      tile(coolCurve, "Kühlkurve"),
      when(tile(coolSet, "Kühlen Soll"), coolCurve, "disabled"),
      unless(info("locked", { label: "Kühlen Soll", setpoint: coolSet }), coolCurve, "disabled"),
      entities("Was die Kennlinie fordert", [
        row(g(`sensors_curve_flow_temp_zone_${letter}`), "Vorlauf-Soll"),
        row(g(`sensors_curve_flow_temp_zone_${letter}_corrected`), "nach Korrektur"),
      ]),
    ];
  };

  const missing = [
    ["sensors_system_flow_temp", "Gesamtvorlauf System"],
    ["sensors_solar_temp", "Solartemperatur"],
    ["sensors_buffer_bottom_temp", "Pufferspeicher unten"],
    ["sensors_buffer_top_temp", "Pufferspeicher oben"],
    ["sensors_return_temp_zone_a", "Rücklauf Zone A"],
    ["sensors_dhw_tank_temp", "Warmwasserspeicher"],
  ].filter(([key]) => g(key) && !dev.fitted(key));

  return {
    title: "Überblick",
    path: "ueberblick",
    icon: "mdi:view-dashboard",
    type: "sections",
    max_columns: 3,
    sections: compact([
      section("Anlage", "mdi:heat-pump", [
        info("plant", { model, state: g("system_status_operating_state"), mode: g("system_status_current_mode") }),
        tile(g("system_on"), "Hauptschalter", "green"),
        info("compressors", {
          running: g("running_compressors"),
          count: g("system_status_module_count"),
          run: g("system_status_compressor_runtime_continuous_min"),
          idle: g("system_status_compressor_idle_continuous_min"),
        }),
        tile(g("system_status_module_count"), "Anzahl Module", "teal"),
        tile(g("control_mode"), "Betriebsart"),
        tile(g("power_mode"), "Leistungsmodus"),
      ]),
      section("Status und Störungen", "mdi:alert-circle-outline", [
        tile(g("problem"), "Störung", "red"),
        info("aux_short", { active: g("aux_heating_active") }),
        tile(g("defrosting"), "Abtauung", "light-blue"),
        tile(g("frost_protection"), "Frostschutz", "cyan"),
        info("faults", { faults: g("active_faults") }),
        tile(g("reset_fault"), "Störung quittieren"),
      ]),
      section("Umgebung", "mdi:weather-partly-cloudy", [
        tile(dev.fitted("sensors_ambient_temp"), "Außentemperatur", "blue"),
        tile(dev.fitted("sensors_mean_ambient_temp"), "Außentemperatur im Mittel", "blue"),
        tile(dev.fitted("sensors_room_temp"), "Raumtemperatur", "amber"),
      ]),
      section("Leistung jetzt", "mdi:gauge", [
        info("cop_now", { cop: g("cop_current"), out: g("active_capacity"), in: g("active_power_input") }),
        // Unavailable while the compressor stands; the line above says so
        // already, and a tile would add a warning badge that reads as a fault.
        unless(tile(g("active_capacity"), "Leistung", "red"), g("active_capacity"), ["unavailable", "unknown"]),
        unless(
          tile(g("active_power_input"), "Leistungsaufnahme", "orange"),
          g("active_power_input"),
          ["unavailable", "unknown"]
        ),
        info("cop_mode", {
          label: "Heizen", icon: "mdi:radiator", color: "red",
          cop: g("cop_heating"), out: g("power_heating_capacity"), in: g("power_heating_power_input"),
        }),
        info("cop_mode", {
          label: "Kühlen", icon: "mdi:snowflake", color: "blue",
          cop: g("cop_cooling"), out: g("power_cooling_capacity"), in: g("power_cooling_power_input"),
        }),
        info("cop_mode", {
          label: "Warmwasser", icon: "mdi:water-thermometer", color: "purple",
          cop: g("cop_dhw"), out: g("power_dhw_capacity"), in: g("power_dhw_power_input"),
        }),
      ]),
      section("Betriebsstunden und Starts", "mdi:timer-outline", [
        info("runtime", {
          label: "Verdichter gesamt", icon: "mdi:timer-outline", color: "teal",
          hours: g("system_status_compressor_runtime_total_min"), starts: g("system_status_compressor_starts"),
        }),
        info("runtime", {
          label: "Heizen", icon: "mdi:radiator", color: "red",
          hours: g("system_status_compressor_runtime_heating_min"), starts: g("system_status_heating_starts"),
          total: g("system_status_compressor_runtime_total_min"),
        }),
        info("runtime", {
          label: "Kühlen", icon: "mdi:snowflake", color: "blue",
          hours: g("system_status_compressor_runtime_cooling_min"), starts: g("system_status_cooling_starts"),
          total: g("system_status_compressor_runtime_total_min"),
        }),
        info("runtime", {
          label: "Warmwasser", icon: "mdi:water-thermometer", color: "purple",
          hours: g("system_status_compressor_runtime_dhw_min"), starts: g("system_status_dhw_starts"),
          total: g("system_status_compressor_runtime_total_min"),
        }),
        tile(g("system_status_defrost_count"), "Abtauvorgänge", "light-blue"),
      ]),
      section("Zusätzliche Temperaturen", "mdi:thermometer-lines", [
        entities("Hydraulik", [
          row(dev.fitted("sensors_climate_flow_temp"), "Gesamtvorlauf (Klimabetrieb)"),
          row(dev.fitted("sensors_floor_heating_flow_temp"), "Vorlauf Fußbodenheizung"),
          row(dev.fitted("sensors_buffer_top_temp"), "Pufferspeicher oben"),
          row(dev.fitted("sensors_system_flow_temp"), "Gesamtvorlauf System"),
          DIVIDER,
          row(g("system_status_power_control_actual_temp"), "Regeltemperatur Leistungsregelung"),
          row(g("system_status_power_control_target_temp"), "Zieltemperatur Leistungsregelung"),
        ]),
        missing.length
          ? entities("Kein Fühler angeschlossen", missing.map(([key, name]) => row(g(key), name)))
          : undefined,
      ]),
      section(
        "Heizzone A",
        "mdi:radiator",
        zone("a", dev.fitted("sensors_buffer_top_temp") || dev.fitted("sensors_climate_flow_temp"))
      ),
      section("Heizzone B", "mdi:heating-coil", zone("b", dev.fitted("sensors_floor_heating_flow_temp"))),
      section("Warmwasser", "mdi:water-boiler", [
        tile(g("dhw_on"), "Warmwasser", "green"),
        tile(g("dhw_setpoint"), "Warmwasser Soll"),
        tile(dev.fitted("sensors_dhw_tank_temp"), "Speichertemperatur", "purple"),
        tile(g("forced_dhw"), "Warmwasser erzwingen", "orange"),
        tile(g("scheduled_disinfection"), "Geplante Desinfektion", "red"),
        entities("Desinfektion", [
          row(g("disinfection_setpoint"), "Temperatur"),
          row(g("disinfection_max_interval_min"), "Max. Intervall"),
          row(g("disinfection_hold_time_min"), "Haltezeit"),
        ]),
      ]),
    ]),
  };
}

function curves(dev) {
  const g = (k) => dev.get(k);
  const picture = (key, select) =>
    g(key)
      ? unless({ type: "picture-entity", entity: g(key), show_state: false, show_name: false, ...FULL }, select, "disabled")
      : undefined;
  const zone = (letter) => {
    const heatCurve = g(`curve_select_heating_zone_${letter}`);
    const coolCurve = g(`curve_select_cooling_zone_${letter}`);
    return section(`Zone ${letter.toUpperCase()}`, "mdi:chart-bell-curve-cumulative", [
      heading("Heizen", undefined, true),
      entities(undefined, [row(heatCurve, "Gewählte Kurve")]),
      picture(`heating_curve_zone_${letter}`, heatCurve),
      info("curve_demand", {
        flow: g(`sensors_curve_flow_temp_zone_${letter}`),
        ambient: g("system_status_curve_ambient_temp"),
      }),
      entities(undefined, [
        row(g(`heating_curve_heating_min_zone_${letter}`), "Untergrenze", "mdi:arrow-collapse-down"),
        row(g(`heating_curve_heating_max_zone_${letter}`), "Obergrenze", "mdi:arrow-collapse-up"),
      ]),
      heading("Kühlen", undefined, true),
      entities(undefined, [row(coolCurve, "Gewählte Kurve")]),
      picture(`cooling_curve_zone_${letter}`, coolCurve),
      unless(
        entities(undefined, [
          row(g(`heating_curve_cooling_min_zone_${letter}`), "Untergrenze", "mdi:arrow-collapse-down"),
          row(g(`heating_curve_cooling_max_zone_${letter}`), "Obergrenze", "mdi:arrow-collapse-up"),
        ]),
        coolCurve,
        "disabled"
      ),
    ]);
  };
  const curveA = g("curve_select_heating_zone_a");
  const curveB = g("curve_select_heating_zone_b");
  return {
    title: "Kennlinien",
    path: "kennlinien",
    icon: "mdi:chart-bell-curve-cumulative",
    type: "sections",
    max_columns: 3,
    sections: compact([
      zone("a"),
      zone("b"),
      section("Kurve 9 — frei einstellbar", "mdi:chart-line-variant", [
        curveA && {
          type: "markdown",
          content:
            "**Diese Werte gelten für Zone A und Zone B gemeinsam.** Die Regelung führt Kurve 9 nur einmal.\n\n" +
            `{% set a = states('${curveA}') == 'curve_9' %}{% set b = states('${curveB}') == 'curve_9' %}` +
            "{% if a and b %}Beide Zonen folgen ihr gerade.{% elif a %}Zone A folgt ihr gerade, Zone B nicht." +
            "{% elif b %}Zone B folgt ihr gerade, Zone A nicht.{% else %}Zurzeit folgt ihr keine Zone.{% endif %}",
          ...FULL,
        },
        entities("Heizen", [
          row(g("curve9_heating_ambient_1"), "Punkt 1 · bei Außentemperatur"),
          row(g("curve9_heating_outlet_1"), "Punkt 1 · Vorlauf"),
          DIVIDER,
          row(g("curve9_heating_ambient_2"), "Punkt 2 · bei Außentemperatur"),
          row(g("curve9_heating_outlet_2"), "Punkt 2 · Vorlauf"),
        ]),
        entities("Kühlen", [
          row(g("curve9_cooling_ambient_1"), "Punkt 1 · bei Außentemperatur"),
          row(g("curve9_cooling_outlet_1"), "Punkt 1 · Vorlauf"),
          DIVIDER,
          row(g("curve9_cooling_ambient_2"), "Punkt 2 · bei Außentemperatur"),
          row(g("curve9_cooling_outlet_2"), "Punkt 2 · Vorlauf"),
        ]),
      ]),
    ]),
  };
}

function auxHeating(dev, modules) {
  const g = (k) => dev.get(k);
  return {
    title: "Zusatzheizung",
    path: "zusatzheizung",
    icon: "mdi:resistor",
    type: "sections",
    max_columns: 3,
    sections: compact([
      section("Zusatzheizung der Anlage", "mdi:resistor", [
        info("aux_plant", {
          active: g("aux_heating_active"),
          power: g("power_aux_heater_power"),
          configured: g("power_aux_heater_power_configured"),
        }),
        entities("Leistung", [
          row(g("power_aux_heater_power"), "Jetzt"),
          row(g("power_aux_heater_power_configured"), "Konfiguriert (DIP-Schalter)"),
        ]),
        entities("Zwangsbetrieb", [
          row(g("forced_aux_heater"), "Zusatzheizstab"),
          row(g("forced_tank_heater"), "Speicher-Heizstab"),
          row(g("forced_external_source"), "Externe Wärmequelle"),
        ]),
        entities("Schaltzustand", [
          row(g("tank_heater"), "Speicher-Heizstab"),
          row(g("tank_heater_feedback"), "Rückmeldung Speicher-Heizstab"),
          row(g("external_heat_source"), "Externe Wärmequelle"),
        ]),
        entities("Betriebsstunden und Starts", [
          row(g("system_status_aux_heater_runtime_min"), "Laufzeit Zusatzheizstab"),
          row(g("system_status_aux_heater_starts"), "Starts Zusatzheizstab"),
          DIVIDER,
          row(g("system_status_tank_heater_runtime_min"), "Laufzeit Speicher-Heizstab"),
          row(g("system_status_tank_heater_starts"), "Starts Speicher-Heizstab"),
        ]),
        ...modules.map((m) =>
          info("aux_module", {
            label: m.label,
            rod1: m.dev.get("module_aux_heater_1"),
            rod2: m.dev.get("module_aux_heater_2"),
          })
        ),
      ]),
    ]),
  };
}

function hydraulics(dev) {
  const g = (k) => dev.get(k);
  const pumps = [
    [g("external_pump"), "Pumpe Zone A"],
    [g("mixing_pump"), "Pumpe Zone B"],
    [g("return_pump"), "Warmwasser-Zirkulation"],
    [g("solar_pump"), "Solarpumpe"],
  ].filter(([id]) => id);
  const signals = [
    [g("remote_switch"), "Fernbedienungsschalter"],
    [g("heating_switch"), "Schalter Heizen"],
    [g("cooling_switch"), "Schalter Kühlen"],
    [g("dhw_switch"), "Schalter Warmwasser"],
    [g("thermostat_h"), "Thermostat Heizen"],
    [g("thermostat_c"), "Thermostat Kühlen"],
    [g("solar_signal"), "Solarsignal"],
  ].filter(([id]) => id);
  const valve = (key, label, on, off, highlight) =>
    g(key) ? info("valve", { valve: g(key), label, on, off, highlight }) : undefined;
  return {
    title: "Hydraulik",
    path: "hydraulik",
    icon: "mdi:pipe-valve",
    type: "sections",
    max_columns: 3,
    sections: compact([
      section("Hydraulik der Anlage", "mdi:pipe-valve", [
        pumps.length ? info("pumps", { list: pumps }) : undefined,
        heading("Ventile", "mdi:valve", true),
        valve("three_way_valve_1", "Warmwasser-Umschaltung", "steht auf Heizen/Kühlen", "steht auf Warmwasser", true),
        valve("three_way_valve_2", "Heizen/Kühlen-Umschaltung", "Befehl Kühlen", "Befehl Heizen", false),
        valve("three_way_valve_3", "Zirkulationsventil", "geschlossen", "offen", true),
        valve("mixing_valve", "Mischventil Zone B", "wird verstellt", "steht", false),
        entities("Pumpen", pumps.map(([id, name]) => row(id, name))),
      ]),
      section("Schnittstelle nach außen", "mdi:import", [
        signals.length ? info("signals", { list: signals }) : undefined,
        entities("Raumthermostat", [
          row(g("thermostat_h"), "Thermostatsignal H · Heizen"),
          row(g("thermostat_c"), "Thermostatsignal C · Kühlen"),
        ]),
        entities("Externe Schalter", [
          row(g("remote_switch"), "Fernbedienungsschalter"),
          row(g("heating_switch"), "Schalter Heizen"),
          row(g("cooling_switch"), "Schalter Kühlen"),
          row(g("dhw_switch"), "Schalter Warmwasser"),
        ]),
        entities("Solarkreis", [row(g("solar_signal"), "Solarsignal")]),
        entities("Meldungen nach außen", [
          row(g("defrost_indication"), "Abtauanzeige"),
          row(g("fault_indication"), "Störungsanzeige"),
        ]),
      ]),
      section("SG-Ready", "mdi:transmission-tower", [
        g("smart_grid_sg") ? info("sg_ready", { sg: g("smart_grid_sg"), evu: g("smart_grid_evu") }) : undefined,
        entities("Die beiden Klemmen", [row(g("smart_grid_sg"), "SG-Signal"), row(g("smart_grid_evu"), "EVU-Signal")]),
        entities("Status und Befehl", [
          row(g("system_status_smart_grid_status"), "Smart-Grid-Status"),
          row(g("system_status_smart_grid_command"), "Smart-Grid-Befehl"),
        ]),
        g("smart_grid_sg") && {
          type: "markdown",
          title: "Was die Signale bedeuten",
          content:
            "| SG | EVU | Die Anlage tut dann |\n|---|---|---|\n" +
            "| 0 | 0 | Normalbetrieb nach Leistungsmodus |\n" +
            "| 1 | 0 oder 1 | Aufnahme wird auf 4000 W begrenzt |\n" +
            "| 0 | 1 | Kraftbetrieb erzwungen, Warmwasser zuerst |\n\n" +
            "Ein Signal muss **10 Minuten** anstehen, bevor die Anlage reagiert — zurück in den Normalbetrieb genügt eine Minute.",
          ...FULL,
        },
      ]),
    ]),
  };
}

function moduleView(modules) {
  return {
    title: "Module",
    path: "module",
    icon: "mdi:heat-pump-outline",
    type: "sections",
    max_columns: 2,
    sections: compact(
      modules.map((m) => {
        const g = (k) => m.dev.get(k);
        const fitted = (k) => m.dev.fitted(k);
        return section(m.label, "mdi:heat-pump-outline", [
          tile(g("module_inverter_actual_speed"), "Verdichter", "blue"),
          unless(tile(g("module_current_power"), "Wärmeleistung", "red"), g("module_current_power"), [
            "unavailable",
            "unknown",
          ]),
          info("module_cop", { cop: g("module_compressor_cop") }),
          tile(g("module_defrosting"), "Abtauung", "light-blue"),
          tile(g("module_problem"), "Störung", "red"),
          info("aux_module", { rod1: g("module_aux_heater_1"), rod2: g("module_aux_heater_2") }),
          tile(g("module_aux_heater_1"), "Heizstab 1"),
          tile(g("module_aux_heater_2"), "Heizstab 2"),
          tile(fitted("module_high_pressure"), "Hochdruck", "red"),
          tile(fitted("module_low_pressure"), "Niederdruck", "blue"),
          tile(fitted("module_actual_superheat"), "Überhitzung"),
          tile(fitted("module_fin_temp"), "Lamelle"),
          tile(fitted("module_phe_flow_temp"), "Vorlauf", "red"),
          tile(fitted("module_phe_return_temp"), "Rücklauf", "blue"),
          tile(fitted("module_pump_flow"), "Volumenstrom", "cyan"),
          tile(fitted("module_fan_1_speed"), "Ventilator"),
        ]);
      })
    ),
  };
}

function history(dev) {
  const g = (k) => dev.get(k);
  const balance = (title, icon, window) =>
    section(title, icon, [
      g(`work_figure_${window}`) ? info("work_figure", { figure: g(`work_figure_${window}`), icon }) : undefined,
      tile(g(`heat_energy_${window}`), "Wärmemenge", "red", { icon: "mdi:fire" }),
      tile(g(`electric_energy_${window}`), "Strommenge", "orange", { icon: "mdi:flash" }),
    ]);
  const graph = (title, icon, rows) => {
    const list = rows.filter(([id]) => id).map(([entity, name]) => ({ entity, name }));
    if (!list.length) return undefined;
    return section(title, icon, [{ type: "history-graph", hours_to_show: 24, entities: list, ...FULL }]);
  };
  return {
    title: "Verlauf",
    path: "verlauf",
    icon: "mdi:chart-line",
    type: "sections",
    max_columns: 2,
    sections: compact([
      balance("Bilanz 24 Stunden", "mdi:clock-outline", "24h"),
      balance("Bilanz 7 Tage", "mdi:calendar-week", "7d"),
      balance("Bilanz 30 Tage", "mdi:calendar-month", "30d"),
      balance("Bilanz 365 Tage", "mdi:calendar", "365d"),
      graph("Temperaturen, 24 Stunden", "mdi:thermometer", [
        [dev.fitted("sensors_ambient_temp"), "Außen"],
        [dev.fitted("sensors_floor_heating_flow_temp"), "Vorlauf FBH"],
        [dev.fitted("sensors_climate_flow_temp"), "Vorlauf Klima"],
        [g("sensors_curve_flow_temp_zone_a"), "Kurve fordert"],
        [dev.fitted("sensors_room_temp"), "Raum"],
      ]),
      graph("Leistung und Verdichter, 24 Stunden", "mdi:flash", [
        [g("active_power_input"), "Leistungsaufnahme"],
        [g("running_compressors"), "Verdichter in Betrieb"],
      ]),
      graph("COP und Wärmeleistung, 24 Stunden", "mdi:gauge", [
        [g("cop_current"), "COP"],
        [g("active_capacity"), "Leistung"],
      ]),
    ]),
  };
}

// -- plants ------------------------------------------------------------------

function findPlants(hass) {
  const ours = new Set(
    Object.values(hass.entities)
      .filter((entry) => entry.platform === PLATFORM && entry.device_id)
      .map((entry) => entry.device_id)
  );
  const name = (id) => hass.devices[id]?.name_by_user || hass.devices[id]?.name || id;
  return [...ours]
    .filter((id) => !hass.devices[id]?.via_device_id)
    .map((id) => ({
      id,
      name: name(id),
      modules: [...ours]
        .filter((m) => hass.devices[m]?.via_device_id === id)
        .sort((a, b) => name(a).localeCompare(name(b)))
        // "<plant> Master", "<plant> Slave 01#": the role is what tells
        // the units apart; the plant's name in front of it is noise here.
        .map((m) => ({ id: m, label: name(m).match(/(Master|Slave \d+#)$/)?.[1] || name(m) })),
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * With several plants, six tabs each would crowd the tab bar with look-alike
 * icons. Each plant gets one tab instead, named after it; its other pages
 * become subviews, reached from a row of buttons on top of its overview.
 */
function asOneTab(plant, plantViews) {
  const dashboard = window.location.pathname.split("/")[1] || "lovelace";
  const suffix = plant.id.slice(0, 6);
  for (const view of plantViews) view.path = `${view.path}-${suffix}`;
  const [main, ...rest] = plantViews;
  const mainPath = `/${dashboard}/${main.path}`;

  main.title = plant.name;
  delete main.icon; // a text tab: the plant's name is what tells them apart
  main.sections.unshift({
    type: "grid",
    column_span: 3,
    cards: rest.map((view) => ({
      type: "button",
      name: view.title,
      icon: view.icon,
      show_state: false,
      tap_action: { action: "navigate", navigation_path: `/${dashboard}/${view.path}` },
      // A spanning section has twelve grid columns per view column, so four
      // keeps each button wide enough for "Zusatzheizung" on any screen.
      grid_options: { columns: 4, rows: 2 },
    })),
  });

  for (const view of rest) {
    view.title = `${plant.name} – ${view.title}`;
    view.subview = true;
    view.back_path = mainPath;
  }
  return plantViews;
}

class WarmondoDashboardStrategy extends HTMLElement {
  static async generate(config, hass) {
    let plants = findPlants(hass);
    if (config.device_id) plants = plants.filter((p) => p.id === config.device_id);
    if (!plants.length) {
      return {
        views: [
          {
            title: "Warmondo",
            cards: [
              {
                type: "markdown",
                content:
                  "Keine Warmondo-Wärmepumpe gefunden. Bitte zuerst die Integration einrichten: " +
                  "Einstellungen → Geräte & Dienste → Integration hinzufügen → Warmondo.",
              },
            ],
          },
        ],
      };
    }
    const views = [];
    for (const plant of plants) {
      const dev = new DeviceEntities(hass, plant.id);
      const modules = plant.modules.map((m) => ({ ...m, dev: new DeviceEntities(hass, m.id) }));
      const plantViews = [
        overview(dev, hass.devices[plant.id]?.model),
        curves(dev),
        auxHeating(dev, modules),
        hydraulics(dev),
        moduleView(modules),
        history(dev),
      ];
      if (plants.length > 1) {
        views.push(...asOneTab(plant, plantViews));
      } else {
        views.push(...plantViews);
      }
    }
    return { views };
  }
}

if (!customElements.get("ll-strategy-dashboard-warmondo")) {
  customElements.define("ll-strategy-dashboard-warmondo", WarmondoDashboardStrategy);
}

window.customStrategies = window.customStrategies || [];
if (!window.customStrategies.some((s) => s.type === "warmondo")) {
  window.customStrategies.push({
    type: "warmondo",
    strategyType: "dashboard",
    name: "Warmondo",
    description:
      "Fertiges Dashboard für Warmondo-Wärmepumpen: Überblick, Kennlinien, Zusatzheizung, Hydraulik, Module und Verlauf.",
    documentationURL: "https://github.com/Bjoern-Harrenberger/Warmondo_HA#dashboard",
  });
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "warmondo-info-card")) {
  window.customCards.push({
    type: "warmondo-info-card",
    name: "Warmondo Info",
    description: "Zusammenfassung eines Anlagenwerts, wie im Warmondo-Dashboard.",
  });
}
