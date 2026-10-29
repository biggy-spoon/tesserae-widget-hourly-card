// weather_hourly_card: Apple-weather style card. Place + big temperature on
// the left, condition + H/L on the right, a row of hourly icon/temp columns
// underneath and an "As of" stamp (the panel only refreshes periodically).

const PH = {
  sun: "ph-sun", moon: "ph-moon", cloud: "ph-cloud", partly: "ph-cloud-sun",
  "partly-night": "ph-cloud-moon", drizzle: "ph-drop", rain: "ph-cloud-rain",
  "rain-heavy": "ph-cloud-rain", showers: "ph-cloud-rain", snow: "ph-snowflake",
  storm: "ph-cloud-lightning", fog: "ph-cloud-fog",
};

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

const deg = (v) => (v == null ? "-" : Math.round(Number(v)) + "°");

function hourLabel(h) {
  const ap = h >= 12 ? "PM" : "AM";
  return `${h % 12 === 0 ? 12 : h % 12} ${ap}`;
}

function asOf(h, m) {
  if (h == null) return "";
  const ap = h >= 12 ? "PM" : "AM";
  return `As of ${h % 12 === 0 ? 12 : h % 12}:${String(m ?? 0).padStart(2, "0")} ${ap}`;
}

export default function render(shadow, ctx) {
  const data = ctx?.data ?? {};
  const SHEET = '<link rel="stylesheet" href="/static/style/spectra-widgets.css">';
  if (data.error) {
    shadow.innerHTML = `${SHEET}
      <div class="w"><div class="w-title"><i class="ph-bold ph-warning-circle"></i><h3>Hourly forecast</h3></div>
      <div class="w-body"><p class="u-muted">${esc(data.error)}</p></div></div>`;
    return;
  }

  const slots = Array.isArray(data.slots) ? data.slots : [];
  const cols = slots.map((s) => `
    <div class="hc-col">
      <span class="hc-h">${esc(hourLabel(s.hour))}</span>
      <i class="ph-bold ${PH[s.icon] || "ph-cloud"}"></i>
      <span class="hc-t">${esc(deg(s.temp))}</span>
    </div>`).join("");

  shadow.innerHTML = `${SHEET}
    <style>
      .hc { font-family: inherit; display: flex; flex-direction: column; justify-content: space-between; height: 100%;
            box-sizing: border-box; padding: var(--space-3); gap: var(--space-2); container-type: size; }
      .hc-top { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-3); }
      .hc-left { min-width: 0; }
      .hc-place { font-size: clamp(1em, 7cqh, 2em); font-weight: var(--fw-bold); white-space: nowrap;
                  overflow: hidden; text-overflow: ellipsis; }
      .hc-now { font-size: clamp(2.4em, 26cqh, 7em); line-height: 1; font-weight: 300; }
      .hc-nowrow { display: flex; align-items: baseline; gap: 0.35em; }
      .hc-feels { font-size: clamp(0.9em, 7cqh, 1.8em); color: var(--text-secondary); white-space: nowrap; }
      .hc-cond-row { display: flex; align-items: center; justify-content: flex-end; gap: 0.5em; }
      .hc-precip { display: inline-flex; align-items: center; gap: 0.2em; font-size: clamp(0.9em, 7cqh, 1.8em);
                   color: var(--text-secondary); white-space: nowrap; }
      .hc-right { text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 0.15em; }
      .hc-right .ph-bold { font-size: clamp(1.6em, 12cqh, 3em); }
      .hc-cond { font-size: clamp(1em, 8cqh, 2em); font-weight: var(--fw-bold); }
      .hc-hl { font-size: clamp(0.9em, 7cqh, 1.8em); color: var(--text-secondary); }
      .hc-row { display: flex; justify-content: space-between; align-items: stretch; gap: var(--space-2); }
      .hc-col { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: 0.25em; }
      .hc-h { font-size: clamp(0.8em, 6cqh, 1.5em); color: var(--text-secondary); white-space: nowrap; }
      .hc-col .ph-bold { font-size: clamp(1.4em, 12cqh, 3em); }
      .hc-t { font-size: clamp(1em, 8cqh, 2em); font-weight: var(--fw-bold); }
      .hc-asof { text-align: right; font-size: clamp(0.7em, 4.5cqh, 1.1em); color: var(--text-muted); }
    </style>
    <div class="w" data-widget="weather_hourly_card"><div class="hc">
      <div class="hc-top">
        <div class="hc-left">
          <div class="hc-place">${esc(data.label || "")}</div>
          <div class="hc-nowrow">
            <div class="hc-now">${esc(deg(data.now))}</div>${
              data.feels != null ? `<div class="hc-feels">Feels ${esc(deg(data.feels))}</div>` : ""}
          </div>
        </div>
        <div class="hc-right">
          <i class="ph-bold ${PH[data.icon] || "ph-cloud"}"></i>
          <div class="hc-cond-row">${
            data.precip != null
              ? `<span class="hc-precip"><i class="ph-bold ph-drop"></i>${esc(data.precip)}%</span>` : ""}
            <div class="hc-cond">${esc(data.cond || "")}</div>
          </div>
          <div class="hc-hl">H:${esc(deg(data.hi))} L:${esc(deg(data.lo))}</div>
        </div>
      </div>
      <div class="hc-row">${cols}</div>
      <div class="hc-asof">${esc(asOf(data.asof_hour, data.asof_minute))}</div>
    </div></div>`;
}
