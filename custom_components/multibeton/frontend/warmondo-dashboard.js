/*
 * Warmondo dashboard - a dashboard strategy shipped with the integration.
 *
 * Settings -> Dashboards -> Add dashboard offers "Warmondo". The strategy
 * builds the dashboard from Home Assistant's own cards (tile, heading,
 * history graph, picture entity) - nothing from HACS. It finds the
 * integration's entities by their translation key and device rather than by
 * entity ID, so it fits every plant whatever its name, model or module count,
 * and a read-only plant (setpoints shown as sensors) as well.
 *
 * Copyright MULTIBETON GmbH, MIT licensed.
 */

const PLATFORM = "multibeton";

const TEXT = {
  de: {
    overview: "Übersicht",
    plant: "Anlage",
    temperatures: "Temperaturen",
    power_now: "Leistung jetzt",
    balance: "Bilanz",
    operate: "Bedienen",
    zones: "Heizzonen und Warmwasser",
    history: "Verlauf",
    temps_24h: "Temperaturen, 24 Stunden",
    power_24h: "Leistung und Leistungsaufnahme, 24 Stunden",
    cop_24h: "Leistungszahl, 24 Stunden",
    curves: "Heizkurven",
    zone_a: "Zone A",
    zone_b: "Zone B",
    heating: "Heizen",
    cooling: "Kühlen",
    units: "Wärmepumpen",
    h24: "24 Stunden",
    d7: "7 Tage",
    d30: "30 Tage",
    d365: "365 Tage",
    work_figure: "Arbeitszahl",
    heat: "Wärmemenge",
    electricity: "Strommenge",
    none:
      "Keine Warmondo-Wärmepumpe gefunden. Bitte zuerst die Integration " +
      "einrichten: Einstellungen → Geräte & Dienste → Integration hinzufügen → Warmondo.",
  },
  en: {
    overview: "Overview",
    plant: "Plant",
    temperatures: "Temperatures",
    power_now: "Power now",
    balance: "Balance",
    operate: "Controls",
    zones: "Zones and hot water",
    history: "History",
    temps_24h: "Temperatures, 24 hours",
    power_24h: "Output and input power, 24 hours",
    cop_24h: "Coefficient of performance, 24 hours",
    curves: "Heating curves",
    zone_a: "Zone A",
    zone_b: "Zone B",
    heating: "Heating",
    cooling: "Cooling",
    units: "Heat pumps",
    h24: "24 hours",
    d7: "7 days",
    d30: "30 days",
    d365: "365 days",
    work_figure: "Performance factor",
    heat: "Heat energy",
    electricity: "Electrical energy",
    none:
      "No Warmondo heat pump found. Please set up the integration first: " +
      "Settings → Devices & services → Add integration → Warmondo.",
  },
};

/** Entities of one device, looked up by translation key. */
class DeviceEntities {
  constructor(hass, deviceId) {
    this.hass = hass;
    this.device = hass.devices[deviceId];
    this.byKey = {};
    for (const entry of Object.values(hass.entities)) {
      if (
        entry.platform !== PLATFORM ||
        entry.device_id !== deviceId ||
        entry.hidden ||
        !entry.translation_key
      ) {
        continue;
      }
      (this.byKey[entry.translation_key] ||= []).push(entry.entity_id);
    }
  }

  /**
   * The entity for `key`, preferring a control over a read-only mirror.
   * Returns undefined when the plant does not have it, or - with
   * `installedOnly` - when the controller reports the sensor as not fitted.
   */
  get(key, { installedOnly = false } = {}) {
    const candidates = this.byKey[key] || [];
    const order = ["switch", "select", "number", "button", "image", "binary_sensor", "sensor"];
    const sorted = [...candidates].sort(
      (a, b) => order.indexOf(a.split(".")[0]) - order.indexOf(b.split(".")[0])
    );
    const entityId = sorted[0];
    if (!entityId) return undefined;
    if (installedOnly) {
      const state = this.hass.states[entityId];
      if (!state || state.state === "unavailable") return undefined;
    }
    return entityId;
  }

  /** The entity's own name, without the device name in front of it. */
  name(entityId) {
    const state = this.hass.states[entityId];
    const friendly = state?.attributes?.friendly_name || entityId;
    const deviceName = this.device?.name_by_user || this.device?.name || "";
    return deviceName && friendly.startsWith(deviceName + " ")
      ? friendly.slice(deviceName.length + 1)
      : friendly;
  }
}

const compact = (list) => list.filter(Boolean);

function tile(dev, key, extra = {}) {
  const entity = dev.get(key, { installedOnly: extra.installedOnly });
  if (!entity) return undefined;
  const { installedOnly, ...options } = extra;
  const card = { type: "tile", entity, name: options.name || dev.name(entity) };
  const domain = entity.split(".")[0];
  if (domain === "select") card.features = [{ type: "select-options" }];
  if (domain === "number") card.features = [{ type: "numeric-input", style: "buttons" }];
  if (domain === "switch") card.features = [{ type: "toggle" }];
  delete options.name;
  return { ...card, ...options };
}

function heading(text, icon) {
  return { type: "heading", heading: text, icon };
}

function section(title, icon, cards, extra = {}) {
  const body = compact(cards);
  if (!body.length) return undefined;
  return { type: "grid", cards: [heading(title, icon), ...body], ...extra };
}

/** Show a card only while `entity` is in one of `states`. */
function onlyWhen(card, entity, states) {
  if (!card || !entity) return card;
  return { ...card, visibility: [{ condition: "state", entity, state: states }] };
}

/** Hide a card while `entity` is in one of `states`. */
function unlessIn(card, entity, states) {
  if (!card || !entity) return card;
  return { ...card, visibility: [{ condition: "state", entity, state_not: states }] };
}

const FULL = { column_span: 3 };
const FULL_CARD = { grid_options: { columns: "full" } };

function overviewView(t, dev) {
  const mode = dev.get("control_mode");
  const curveA = dev.get("curve_select_heating_zone_a");
  const curveB = dev.get("curve_select_heating_zone_b");
  const coolCurveA = dev.get("curve_select_cooling_zone_a");

  return {
    title: t.overview,
    path: "uebersicht",
    icon: "mdi:heat-pump",
    type: "sections",
    max_columns: 3,
    sections: compact([
      section(t.plant, "mdi:heat-pump", [
        tile(dev, "system_status_operating_state"),
        tile(dev, "system_on"),
        tile(dev, "problem"),
        tile(dev, "active_faults"),
        tile(dev, "running_compressors"),
        tile(dev, "defrosting"),
      ]),
      section(t.temperatures, "mdi:thermometer", [
        tile(dev, "sensors_ambient_temp", { installedOnly: true }),
        tile(dev, "sensors_room_temp", { installedOnly: true }),
        tile(dev, "sensors_floor_heating_flow_temp", { installedOnly: true }),
        tile(dev, "sensors_climate_flow_temp", { installedOnly: true }),
        tile(dev, "sensors_dhw_tank_temp", { installedOnly: true }),
        tile(dev, "sensors_buffer_top_temp", { installedOnly: true }),
        tile(dev, "sensors_buffer_bottom_temp", { installedOnly: true }),
        tile(dev, "sensors_solar_temp", { installedOnly: true }),
      ]),
      section(t.power_now, "mdi:lightning-bolt", [
        tile(dev, "active_capacity"),
        tile(dev, "active_power_input"),
        tile(dev, "cop_current"),
      ]),
      section(t.balance, "mdi:chart-bar", [
        tile(dev, "work_figure_24h", { name: `${t.work_figure} ${t.h24}` }),
        tile(dev, "work_figure_7d", { name: `${t.work_figure} ${t.d7}` }),
        tile(dev, "work_figure_30d", { name: `${t.work_figure} ${t.d30}` }),
        tile(dev, "work_figure_365d", { name: `${t.work_figure} ${t.d365}` }),
        tile(dev, "heat_energy_24h", { name: `${t.heat} ${t.h24}` }),
        tile(dev, "electric_energy_24h", { name: `${t.electricity} ${t.h24}` }),
      ]),
      section(t.operate, "mdi:tune-variant", [
        tile(dev, "control_mode"),
        tile(dev, "power_mode"),
        // A fixed flow setpoint only applies while no curve is selected.
        onlyWhen(tile(dev, "heating_setpoint_zone_a"), curveA, ["disabled"]),
        onlyWhen(tile(dev, "heating_setpoint_zone_b"), curveB, ["disabled"]),
        // Cooling values are of no interest while the plant only heats.
        unlessIn(
          onlyWhen(tile(dev, "cooling_setpoint_zone_a"), coolCurveA, ["disabled"]),
          mode,
          ["heat"]
        ),
        tile(dev, "dhw_setpoint"),
      ]),
      section(t.zones, "mdi:radiator", [
        tile(dev, "zone_a_on"),
        tile(dev, "zone_b_on"),
        tile(dev, "dhw_on"),
        tile(dev, "vacation_away"),
      ]),
    ]),
  };
}

function historyView(t, dev) {
  const graph = (title, keys) => {
    const entities = compact(keys.map((key) => dev.get(key, { installedOnly: true })));
    if (!entities.length) return undefined;
    return {
      type: "history-graph",
      title,
      hours_to_show: 24,
      entities: entities.map((entity) => ({ entity, name: dev.name(entity) })),
      ...FULL_CARD,
    };
  };
  return {
    title: t.history,
    path: "verlauf",
    icon: "mdi:chart-line",
    type: "sections",
    max_columns: 3,
    sections: compact([
      section(t.balance, "mdi:chart-bar", [
        tile(dev, "work_figure_24h", { name: `${t.work_figure} ${t.h24}` }),
        tile(dev, "work_figure_7d", { name: `${t.work_figure} ${t.d7}` }),
        tile(dev, "work_figure_30d", { name: `${t.work_figure} ${t.d30}` }),
        tile(dev, "work_figure_365d", { name: `${t.work_figure} ${t.d365}` }),
        tile(dev, "heat_energy_7d", { name: `${t.heat} ${t.d7}` }),
        tile(dev, "electric_energy_7d", { name: `${t.electricity} ${t.d7}` }),
        tile(dev, "heat_energy_365d", { name: `${t.heat} ${t.d365}` }),
        tile(dev, "electric_energy_365d", { name: `${t.electricity} ${t.d365}` }),
      ], FULL),
      section(t.temps_24h, "mdi:thermometer", [
        graph(t.temps_24h, [
          "sensors_ambient_temp",
          "sensors_room_temp",
          "sensors_floor_heating_flow_temp",
          "sensors_climate_flow_temp",
          "sensors_curve_flow_temp_zone_a",
        ]),
      ], FULL),
      section(t.power_24h, "mdi:lightning-bolt", [
        graph(t.power_24h, ["active_capacity", "active_power_input"]),
      ], FULL),
      section(t.cop_24h, "mdi:gauge", [graph(t.cop_24h, ["cop_current"])], FULL),
    ]),
  };
}

function curvesView(t, dev) {
  const zone = (title, suffix) =>
    section(title, "mdi:chart-bell-curve", [
      heading(t.heating, "mdi:radiator"),
      tile(dev, `curve_select_heating_zone_${suffix}`),
      dev.get(`heating_curve_zone_${suffix}`) && {
        type: "picture-entity",
        entity: dev.get(`heating_curve_zone_${suffix}`),
        show_name: false,
        show_state: false,
        ...FULL_CARD,
      },
      tile(dev, `sensors_curve_flow_temp_zone_${suffix}`),
      heading(t.cooling, "mdi:snowflake"),
      tile(dev, `curve_select_cooling_zone_${suffix}`),
      dev.get(`cooling_curve_zone_${suffix}`) && {
        type: "picture-entity",
        entity: dev.get(`cooling_curve_zone_${suffix}`),
        show_name: false,
        show_state: false,
        ...FULL_CARD,
      },
    ], FULL);
  return {
    title: t.curves,
    path: "kennlinien",
    icon: "mdi:chart-bell-curve",
    type: "sections",
    max_columns: 3,
    sections: compact([zone(t.zone_a, "a"), zone(t.zone_b, "b")]),
  };
}

function unitsView(t, hass, moduleIds) {
  const sections = moduleIds.map((id) => {
    const dev = new DeviceEntities(hass, id);
    const title = dev.device?.name_by_user || dev.device?.name || "";
    return section(title, "mdi:heat-pump-outline", [
      tile(dev, "module_current_power"),
      tile(dev, "module_inverter_actual_speed"),
      tile(dev, "module_compressor_cop"),
      tile(dev, "module_defrosting"),
      tile(dev, "module_problem"),
      tile(dev, "module_active_faults"),
      tile(dev, "module_phe_flow_temp", { installedOnly: true }),
      tile(dev, "module_phe_return_temp", { installedOnly: true }),
      tile(dev, "module_pump_flow", { installedOnly: true }),
      tile(dev, "module_high_pressure", { installedOnly: true }),
      tile(dev, "module_low_pressure", { installedOnly: true }),
      tile(dev, "module_aux_heater_1"),
      tile(dev, "module_aux_heater_2"),
    ]);
  });
  return {
    title: t.units,
    path: "waermepumpen",
    icon: "mdi:heat-pump-outline",
    type: "sections",
    max_columns: 3,
    sections: compact(sections),
  };
}

/** Devices of this integration: plants and the modules under them. */
function findPlants(hass) {
  const ours = new Set(
    Object.values(hass.entities)
      .filter((entry) => entry.platform === PLATFORM && entry.device_id)
      .map((entry) => entry.device_id)
  );
  const plants = [...ours].filter((id) => !hass.devices[id]?.via_device_id);
  return plants
    .map((id) => ({
      id,
      name: hass.devices[id]?.name_by_user || hass.devices[id]?.name || id,
      modules: [...ours]
        .filter((m) => hass.devices[m]?.via_device_id === id)
        .sort((a, b) =>
          (hass.devices[a]?.name || "").localeCompare(hass.devices[b]?.name || "")
        ),
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

class WarmondoDashboardStrategy extends HTMLElement {
  static async generate(config, hass) {
    const t = (hass.locale?.language || hass.language || "de").startsWith("de")
      ? TEXT.de
      : TEXT.en;
    let plants = findPlants(hass);
    if (config.device_id) plants = plants.filter((p) => p.id === config.device_id);
    if (!plants.length) {
      return {
        views: [
          {
            title: "Warmondo",
            cards: [{ type: "markdown", content: t.none }],
          },
        ],
      };
    }
    const views = [];
    for (const plant of plants) {
      const dev = new DeviceEntities(hass, plant.id);
      const plantViews = [
        overviewView(t, dev),
        historyView(t, dev),
        curvesView(t, dev),
        unitsView(t, hass, plant.modules),
      ];
      if (plants.length > 1) {
        // One set of views per plant; the plant's name tells them apart.
        for (const view of plantViews) {
          view.title = `${plant.name} – ${view.title}`;
          view.path = `${view.path}-${plant.id.slice(0, 6)}`;
        }
      }
      views.push(...plantViews);
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
      "Fertiges Dashboard für Warmondo-Wärmepumpen: Übersicht, Verlauf, Heizkurven und alle Geräte der Kaskade.",
    documentationURL: "https://github.com/Bjoern-Harrenberger/Warmondo_HA#dashboard",
  });
}
