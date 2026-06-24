const STORAGE = {
  account: "ssoSignalDesk.account",
  trades: "ssoSignalDesk.trades",
  theme: "ssoSignalDesk.theme",
  imported: "ssoSignalDesk.importedData",
};

const VIEW_META = {
  dashboard: ["SPY/SSO Signal Desk", "Operational close-to-next-day tracking for the SPY SMA200 / SSO strategy."],
  daily: ["Daily Data", "Search, sort, import, and export the complete model ledger."],
  account: ["Real Account", "Keep actual brokerage shares, cash, and fills separate from model values."],
  trades: ["Trade Log", "A browser-local record of deliberate real-account transactions."],
  calendar: ["Calendar Cycles", "Full 1, 2, 3, 5, and 10-year comparisons reset to $1,000."],
  spreads: ["Spread Cycles", "Informational SPY/SMA200 range context for each SSO buy-to-sell cycle."],
  rules: ["Rules", "The complete SPY SMA200 / SSO operating logic in plain language."],
  settings: ["Settings", "Data replacement, update status, local controls, and notification setup."],
};

const state = {
  data: null,
  daily: [],
  filteredDaily: [],
  dailyPage: 1,
  pageSize: 50,
  dailySort: { key: "date", direction: "desc" },
  calendarYears: 1,
  account: loadLocal(STORAGE.account, {}),
  trades: loadLocal(STORAGE.trades, []),
};

const $ = (id) => document.getElementById(id);
const money = (value) => Number.isFinite(Number(value)) ? Number(value).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }) : "—";
const pct = (value, digits = 2) => Number.isFinite(Number(value)) ? `${Number(value) >= 0 ? "+" : ""}${(Number(value) * 100).toFixed(digits)}%` : "—";
const number = (value, digits = 2) => Number.isFinite(Number(value)) ? Number(value).toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }) : "—";
const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));

function loadLocal(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}

function saveLocal(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function setText(id, value) {
  const element = $(id);
  if (element) element.textContent = value;
}

function tone(element, value) {
  element.classList.remove("positive", "negative");
  if (Number(value) > 0) element.classList.add("positive");
  if (Number(value) < 0) element.classList.add("negative");
}

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
}

function showView(name) {
  const target = VIEW_META[name] ? name : "dashboard";
  document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${target}`));
  document.querySelectorAll(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.view === target));
  setText("viewTitle", VIEW_META[target][0]);
  setText("viewSubtitle", VIEW_META[target][1]);
  document.querySelector(".sidebar").classList.remove("open");
  history.replaceState(null, "", `#${target}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function freshness(marketDate) {
  if (!marketDate) return { stale: true, label: "No data" };
  const today = new Date();
  const latest = new Date(`${marketDate}T20:00:00`);
  const days = Math.floor((today - latest) / 86400000);
  return { stale: days > 4, label: days > 4 ? `Stale · ${marketDate}` : `Current · ${marketDate}` };
}

function renderSummary() {
  const summary = state.data.summary;
  const freshnessState = freshness(state.data.last_updated);
  const badge = $("freshnessBadge");
  badge.textContent = freshnessState.label;
  badge.className = `badge ${freshnessState.stale ? "stale" : "fresh"}`;
  $("sidebarFreshDot").className = `status-dot ${freshnessState.stale ? "stale" : "fresh"}`;
  setText("sidebarFreshText", freshnessState.stale ? "Data needs attention" : "Data current");

  const positionPanel = $("positionPanel");
  positionPanel.classList.remove("sso", "cash");
  positionPanel.classList.add(String(summary.position).toLowerCase());
  setText("currentPosition", summary.position);
  setText("currentAction", summary.current_action);
  setText("latestReason", summary.reason);
  setText("latestDate", summary.date);
  setText("strategyValue", money(summary.strategy_value));
  setText("benchmarkValue", money(summary.spy_benchmark_value));
  setText("leadLag", money(summary.lead_lag_dollars));
  setText("leadLagPct", pct(summary.lead_lag_pct));
  tone($("leadLag"), summary.lead_lag_dollars);
  tone($("leadLagPct"), summary.lead_lag_pct);

  setText("spyClose", money(summary.spy_close));
  setText("ssoClose", money(summary.sso_close));
  setText("sma200", money(summary.sma200));
  setText("buyThreshold", money(summary.buy_threshold));
  setText("sellThreshold", money(summary.sell_threshold));
  setText("spread", pct(summary.spread));
  setText("currentDrawdown", pct(summary.strategy_drawdown));
  setText("maxDrawdown", pct(summary.max_strategy_drawdown));
  tone($("spread"), summary.spread);
  tone($("currentDrawdown"), summary.strategy_drawdown);
  tone($("maxDrawdown"), summary.max_strategy_drawdown);

  setText("cycleNumber", summary.spread_cycle_number ? `#${summary.spread_cycle_number}` : "None");
  setText("cycleFloor", pct(summary.cycle_high_floor));
  setText("cycleMax", pct(summary.cycle_max_spread));
  setText("cycleMaxDate", summary.cycle_max_date || "—");
  setText("inHighRange", summary.in_cycle_high_range == null ? "Not in SSO cycle" : summary.in_cycle_high_range ? "Yes" : "No");
  setText("statusCloseDate", state.data.last_updated);
  setText("generatedAt", new Date(state.data.generated_at_utc).toLocaleString());
  setText("dataSource", state.data.data_source);
  setText("rowCount", state.daily.length.toLocaleString());
  setText("settingsSource", state.data.data_source);
  setText("settingsDate", state.data.last_updated);
  setText("settingsGenerated", new Date(state.data.generated_at_utc).toLocaleString());
}

function dailySignalClass(signal) {
  if (signal === "Buy SSO") return "signal-buy";
  if (signal === "Sell to Cash") return "signal-sell";
  return "";
}

function applyDailyFilter() {
  const query = $("dailySearch").value.trim().toLowerCase();
  state.filteredDaily = state.daily.filter((row) => {
    const haystack = [row.date, row.signal, row.position, row.reason].join(" ").toLowerCase();
    return haystack.includes(query);
  });
  const { key, direction } = state.dailySort;
  state.filteredDaily.sort((a, b) => {
    const av = a[key] ?? "";
    const bv = b[key] ?? "";
    const compared = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
    return direction === "asc" ? compared : -compared;
  });
  const pages = Math.max(1, Math.ceil(state.filteredDaily.length / state.pageSize));
  state.dailyPage = Math.min(state.dailyPage, pages);
  renderDailyTable();
}

function renderDailyTable() {
  const start = (state.dailyPage - 1) * state.pageSize;
  const rows = state.filteredDaily.slice(start, start + state.pageSize);
  $("dailyBody").innerHTML = rows.map((row) => `
    <tr class="${row.signal === "Buy SSO" ? "trade-buy" : row.signal === "Sell to Cash" ? "trade-sell" : ""}">
      <td>${escapeHtml(row.date)}</td><td>${money(row.spy_close)}</td><td>${money(row.sso_close)}</td>
      <td>${money(row.sma200)}</td><td class="${Number(row.spread) >= 0 ? "positive" : "negative"}">${pct(row.spread)}</td>
      <td>${money(row.buy_threshold)} / ${money(row.sell_threshold)}</td>
      <td class="${dailySignalClass(row.signal)}">${escapeHtml(row.signal)}</td><td>${escapeHtml(row.position)}</td>
      <td class="${Number(row.strategy_return) >= 0 ? "positive" : "negative"}">${pct(row.strategy_return)}</td>
      <td>${money(row.strategy_value)}</td><td>${money(row.spy_benchmark_value)}</td>
      <td class="negative">${pct(row.strategy_drawdown)}</td><td class="negative">${pct(row.spy_drawdown)}</td>
    </tr>`).join("");
  $("dailyEmpty").classList.toggle("hidden", rows.length > 0);
  const pages = Math.max(1, Math.ceil(state.filteredDaily.length / state.pageSize));
  setText("dailyPage", `Page ${state.dailyPage} of ${pages} · ${state.filteredDaily.length.toLocaleString()} rows`);
  $("dailyPrev").disabled = state.dailyPage <= 1;
  $("dailyNext").disabled = state.dailyPage >= pages;
}

function renderCalendar() {
  const rows = state.data.calendar_cycles.filter((row) => Number(row.cycle_years) === state.calendarYears);
  $("calendarBody").innerHTML = rows.slice().reverse().map((row) => `
    <tr><td>${row.start_year}–${row.end_year}</td><td>${row.start_date} → ${row.end_date}</td>
    <td>${money(row.strategy_final)}</td><td>${money(row.spy_final)}</td>
    <td class="${row.strategy_return >= 0 ? "positive" : "negative"}">${pct(row.strategy_return)}</td>
    <td class="${row.spy_return >= 0 ? "positive" : "negative"}">${pct(row.spy_return)}</td>
    <td class="negative">${pct(row.strategy_max_drawdown)}</td><td class="negative">${pct(row.spy_max_drawdown)}</td>
    <td>${row.strategy_beat_spy ? "Yes" : "No"}</td><td>${row.strategy_positive ? "Yes" : "No"}</td></tr>`).join("");
}

function renderSpreads() {
  const cycles = state.data.spread_cycles;
  setText("spreadCycleCount", `${cycles.length} buy-to-sell cycles`);
  $("spreadBody").innerHTML = cycles.slice().reverse().map((row) => `
    <tr class="${row.status === "open" ? "current-cycle" : ""}">
      <td>#${row.cycle}</td><td>${row.status === "open" ? '<span class="badge info">Open</span>' : "Closed"}</td>
      <td>${row.buy_date}</td><td>${row.sell_date || "Open"}</td><td>${row.duration_trading_days}</td>
      <td>${pct(row.min_spread)}</td><td>${pct(row.high_range_floor)}</td><td>${pct(row.max_spread)}</td>
      <td>${row.max_spread_date}</td><td>${row.high_range_days}</td>
    </tr>`).join("");
}

function renderAccount() {
  const form = $("accountForm");
  for (const [key, value] of Object.entries(state.account)) {
    if (form.elements[key]) form.elements[key].value = value;
  }
  const shares = Number(state.account.shares || 0);
  const cash = Number(state.account.cash || 0);
  const ssoPrice = Number(state.data?.summary?.sso_close || 0);
  const ssoValue = shares * ssoPrice;
  const total = ssoValue + cash;
  const allocation = total > 0 ? ssoValue / total : 0;
  const target = state.data?.summary?.position === "SSO" ? 1 : 0;
  setText("actualSsoValue", money(ssoValue));
  setText("actualTotalValue", money(total));
  setText("modelTarget", target ? "100% SSO" : "100% Cash");
  setText("actualAllocation", total > 0 ? `${(allocation * 100).toFixed(2)}% SSO / ${((1 - allocation) * 100).toFixed(2)}% Cash` : "—");
  if (!total) {
    setText("reconciliation", "Add account values to begin.");
  } else {
    const gap = Math.abs(allocation - target);
    setText("reconciliation", gap <= 0.005 ? "Matched to the model target." : `Not matched: allocation differs by ${(gap * 100).toFixed(2)} percentage points.`);
    $("reconciliation").className = gap <= 0.005 ? "positive" : "negative";
  }
}

function renderTrades() {
  const rows = state.trades.slice().sort((a, b) => b.date.localeCompare(a.date));
  setText("tradeCount", `${rows.length} record${rows.length === 1 ? "" : "s"}`);
  $("tradeBody").innerHTML = rows.map((trade) => `
    <tr><td>${escapeHtml(trade.date)}</td><td>${escapeHtml(trade.action)}</td><td>${escapeHtml(trade.symbol)}</td>
    <td>${number(trade.shares, 4)}</td><td>${money(trade.fillPrice)}</td><td>${money(Number(trade.shares) * Number(trade.fillPrice))}</td>
    <td>${escapeHtml(trade.reason)}</td><td>${escapeHtml(trade.notes)}</td><td>${money(trade.accountValue)}</td>
    <td><button class="button edit-trade" data-id="${trade.id}">Edit</button></td></tr>`).join("");
  $("tradeEmpty").classList.toggle("hidden", rows.length > 0);
}

function csvEscape(value) {
  const text = value == null ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function exportRecords(filename, records) {
  if (!records.length) return;
  const headers = Object.keys(records[0]);
  const csv = [headers.join(","), ...records.map((row) => headers.map((key) => csvEscape(row[key])).join(","))].join("\n");
  download(filename, csv, "text/csv;charset=utf-8");
}

function download(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function parseCsv(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (char === '"' && quoted && text[i + 1] === '"') { field += '"'; i += 1; }
    else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) { row.push(field); field = ""; }
    else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[i + 1] === "\n") i += 1;
      row.push(field); field = "";
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
    } else field += char;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  if (rows.length < 2) throw new Error("The CSV has no data rows.");
  const headers = rows[0].map((value) => value.trim());
  const required = ["date", "spy_close", "sso_close", "sma200", "signal", "position"];
  const missing = required.filter((key) => !headers.includes(key));
  if (missing.length) throw new Error(`Missing required columns: ${missing.join(", ")}`);
  const numeric = new Set(["spy_close", "sso_close", "sma200", "spread", "buy_threshold", "sell_threshold", "strategy_return", "strategy_value", "spy_benchmark_value", "strategy_drawdown", "spy_drawdown"]);
  return rows.slice(1).map((values) => Object.fromEntries(headers.map((header, index) => [header, numeric.has(header) ? Number(values[index]) : values[index]])));
}

function validateData(data) {
  if (!data || !data.summary || !Array.isArray(data.daily) || !Array.isArray(data.calendar_cycles) || !Array.isArray(data.spread_cycles)) {
    throw new Error("JSON must contain summary, daily, calendar_cycles, and spread_cycles.");
  }
  return data;
}

function applyData(data, persist = false) {
  state.data = validateData(data);
  state.daily = state.data.daily;
  state.filteredDaily = state.daily.slice();
  state.dailyPage = 1;
  if (persist) saveLocal(STORAGE.imported, state.data);
  renderSummary();
  applyDailyFilter();
  renderCalendar();
  renderSpreads();
  renderAccount();
  $("loadingState").classList.add("hidden");
  $("errorState").classList.add("hidden");
  refreshIcons();
}

function handleTradeSubmit(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const record = Object.fromEntries(form.entries());
  record.id = record.id || crypto.randomUUID();
  ["shares", "fillPrice", "accountValue"].forEach((key) => record[key] = Number(record[key] || 0));
  const index = state.trades.findIndex((item) => item.id === record.id);
  if (index >= 0) state.trades[index] = record;
  else state.trades.push(record);
  saveLocal(STORAGE.trades, state.trades);
  resetTradeForm();
  renderTrades();
}

function startTradeEdit(id) {
  const record = state.trades.find((trade) => trade.id === id);
  if (!record) return;
  const form = $("tradeForm");
  Object.entries(record).forEach(([key, value]) => { if (form.elements[key]) form.elements[key].value = value; });
  setText("tradeFormTitle", "Edit trade record");
  setText("tradeSubmitText", "Save explicit edit");
  $("cancelTradeEdit").classList.remove("hidden");
  form.scrollIntoView({ behavior: "smooth" });
}

function resetTradeForm() {
  $("tradeForm").reset();
  $("tradeForm").elements.symbol.value = "SSO";
  $("tradeForm").elements.id.value = "";
  setText("tradeFormTitle", "Add trade record");
  setText("tradeSubmitText", "Add record");
  $("cancelTradeEdit").classList.add("hidden");
}

function bindEvents() {
  document.querySelector(".brand").addEventListener("click", (event) => {
    event.preventDefault();
    showView("dashboard");
  });
  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
  document.querySelectorAll("[data-open-view]").forEach((button) => button.addEventListener("click", () => showView(button.dataset.openView)));
  $("mobileMenu").addEventListener("click", () => document.querySelector(".sidebar").classList.toggle("open"));
  $("themeToggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem(STORAGE.theme, next);
  });
  $("dailySearch").addEventListener("input", () => { state.dailyPage = 1; applyDailyFilter(); });
  document.querySelectorAll("#dailyTable th[data-sort]").forEach((header) => header.addEventListener("click", () => {
    const key = header.dataset.sort;
    state.dailySort.direction = state.dailySort.key === key && state.dailySort.direction === "desc" ? "asc" : "desc";
    state.dailySort.key = key;
    applyDailyFilter();
  }));
  $("dailyPrev").addEventListener("click", () => { state.dailyPage -= 1; renderDailyTable(); });
  $("dailyNext").addEventListener("click", () => { state.dailyPage += 1; renderDailyTable(); });
  $("exportDaily").addEventListener("click", () => exportRecords("spy_sso_daily_data.csv", state.daily));
  $("dailyImport").addEventListener("change", async (event) => {
    try {
      const rows = parseCsv(await event.target.files[0].text());
      state.daily = rows;
      state.dailyPage = 1;
      $("importError").classList.add("hidden");
      applyDailyFilter();
    } catch (error) {
      $("importError").textContent = `Import error: ${error.message}`;
      $("importError").classList.remove("hidden");
    }
  });
  $("accountForm").addEventListener("submit", (event) => {
    event.preventDefault();
    state.account = Object.fromEntries(new FormData(event.currentTarget).entries());
    saveLocal(STORAGE.account, state.account);
    renderAccount();
  });
  $("tradeForm").addEventListener("submit", handleTradeSubmit);
  $("cancelTradeEdit").addEventListener("click", resetTradeForm);
  $("tradeBody").addEventListener("click", (event) => {
    const button = event.target.closest(".edit-trade");
    if (button) startTradeEdit(button.dataset.id);
  });
  $("exportTrades").addEventListener("click", () => exportRecords("sso_real_trade_log.csv", state.trades));
  document.querySelectorAll("#cycleFilter button").forEach((button) => button.addEventListener("click", () => {
    state.calendarYears = Number(button.dataset.years);
    document.querySelectorAll("#cycleFilter button").forEach((item) => item.classList.toggle("active", item === button));
    renderCalendar();
  }));
  $("exportCalendar").addEventListener("click", () => exportRecords(`spy_sso_${state.calendarYears}y_calendar_cycles.csv`, state.data.calendar_cycles.filter((row) => Number(row.cycle_years) === state.calendarYears)));
  $("exportSpreads").addEventListener("click", () => exportRecords("spy_sso_spread_cycles.csv", state.data.spread_cycles));
  $("exportJson").addEventListener("click", () => download("spy_sso_signals.json", JSON.stringify(state.data, null, 2), "application/json"));
  $("jsonImport").addEventListener("change", async (event) => {
    try { applyData(JSON.parse(await event.target.files[0].text()), true); }
    catch (error) { alert(`Import error: ${error.message}`); }
  });
  $("resetAccount").addEventListener("click", () => {
    if (!confirm("Reset browser-local real-account inputs?")) return;
    localStorage.removeItem(STORAGE.account); state.account = {}; $("accountForm").reset(); renderAccount();
  });
  $("resetTrades").addEventListener("click", () => {
    if (!confirm("Delete all browser-local trade records? This cannot be undone.")) return;
    localStorage.removeItem(STORAGE.trades); state.trades = []; renderTrades();
  });
  $("resetAll").addEventListener("click", () => {
    if (!confirm("Reset imported data, account inputs, trades, and theme in this browser?")) return;
    Object.values(STORAGE).forEach((key) => localStorage.removeItem(key));
    location.reload();
  });
}

async function init() {
  const theme = localStorage.getItem(STORAGE.theme);
  if (theme) document.documentElement.dataset.theme = theme;
  bindEvents();
  renderTrades();
  showView(location.hash.slice(1) || "dashboard");
  refreshIcons();
  try {
    const imported = loadLocal(STORAGE.imported, null);
    if (imported) applyData(imported);
    else {
      const response = await fetch("data/signals.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      applyData(await response.json());
    }
  } catch (error) {
    $("loadingState").classList.add("hidden");
    $("errorState").classList.remove("hidden");
    setText("errorMessage", `The dashboard could not read data/signals.json (${error.message}).`);
    refreshIcons();
  }
}

init();
