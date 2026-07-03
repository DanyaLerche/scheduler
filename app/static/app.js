const roomTypeOptions = [
  ["any", "Любая"],
  ["lecture", "Лекция"],
  ["practice", "Практика"],
  ["lab", "Лаборатория"],
];

const schemas = {
  timeslots: {
    title: "Слоты",
    fields: [
      { key: "id", label: "ID", type: "text" },
      { key: "day", label: "День", type: "text" },
      { key: "start", label: "Начало", type: "text" },
      { key: "end", label: "Конец", type: "text" },
      { key: "order", label: "Порядок", type: "number" },
    ],
  },
  rooms: {
    title: "Аудитории",
    fields: [
      { key: "id", label: "ID", type: "text" },
      { key: "name", label: "Название", type: "text" },
      { key: "capacity", label: "Мест", type: "number" },
      { key: "room_type", label: "Тип", type: "select", options: roomTypeOptions },
    ],
  },
  teachers: {
    title: "Преподаватели",
    fields: [
      { key: "id", label: "ID", type: "text" },
      { key: "name", label: "ФИО", type: "text" },
      { key: "unavailable", label: "Недоступные слоты", type: "list" },
    ],
  },
  groups: {
    title: "Группы",
    fields: [
      { key: "id", label: "ID", type: "text" },
      { key: "name", label: "Название", type: "text" },
      { key: "size", label: "Студентов", type: "number" },
      { key: "unavailable", label: "Недоступные слоты", type: "list" },
    ],
  },
  lessons: {
    title: "Занятия",
    fields: [
      { key: "id", label: "ID", type: "text" },
      { key: "subject", label: "Предмет", type: "text" },
      { key: "teacher_id", label: "Преподаватель", type: "text" },
      { key: "group_ids", label: "Группы", type: "list" },
      { key: "sessions", label: "Пар", type: "number" },
      { key: "room_type", label: "Тип ауд.", type: "select", options: roomTypeOptions },
      { key: "priority", label: "Приоритет", type: "number" },
    ],
  },
};

let dataset = null;
let result = null;
let activeSection = "lessons";

const elements = {};

document.addEventListener("DOMContentLoaded", async () => {
  bindElements();
  bindEvents();
  renderTabs();
  await loadSample();
});

function bindElements() {
  elements.status = document.querySelector("#status");
  elements.tabs = document.querySelector("#tabs");
  elements.editor = document.querySelector("#editor");
  elements.addRow = document.querySelector("#add-row");
  elements.loadSample = document.querySelector("#load-sample");
  elements.generate = document.querySelector("#generate");
  elements.exportJson = document.querySelector("#export-json");
  elements.importJson = document.querySelector("#import-json");
  elements.jsonFile = document.querySelector("#json-file");
  elements.metrics = document.querySelector("#metrics");
  elements.comparisonBody = document.querySelector("#comparison-body");
  elements.schedule = document.querySelector("#schedule");
  elements.scheduleCount = document.querySelector("#schedule-count");
  elements.conflicts = document.querySelector("#conflicts");
  elements.conflictCount = document.querySelector("#conflict-count");
  elements.unscheduled = document.querySelector("#unscheduled");
  elements.unscheduledCount = document.querySelector("#unscheduled-count");
}

function bindEvents() {
  elements.loadSample.addEventListener("click", loadSample);
  elements.generate.addEventListener("click", generateSchedule);
  elements.addRow.addEventListener("click", addRow);
  elements.exportJson.addEventListener("click", exportJson);
  elements.importJson.addEventListener("click", () => elements.jsonFile.click());
  elements.jsonFile.addEventListener("change", importJson);

  elements.tabs.addEventListener("click", (event) => {
    const button = event.target.closest("[data-section]");
    if (!button) return;
    activeSection = button.dataset.section;
    renderTabs();
    renderEditor();
  });

  elements.editor.addEventListener("input", updateCell);
  elements.editor.addEventListener("change", updateCell);
  elements.editor.addEventListener("click", (event) => {
    const button = event.target.closest("[data-delete-index]");
    if (!button) return;
    const index = Number(button.dataset.deleteIndex);
    dataset[activeSection].splice(index, 1);
    result = null;
    renderEditor();
    renderResults();
  });
}

async function loadSample() {
  setStatus("Загрузка примера...");
  try {
    const response = await fetch("/api/sample");
    assertResponse(response);
    dataset = await response.json();
    result = null;
    renderAll();
    await generateSchedule();
  } catch (error) {
    setStatus(error.message, true);
  }
}

async function generateSchedule() {
  if (!dataset) return;
  setStatus("Формирование расписания...");
  try {
    const response = await fetch("/api/schedule", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset,
        options: { include_comparison: true, seed: 42 },
      }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(formatApiError(payload) || `Ошибка API: ${response.status}`);
    }
    result = await response.json();
    renderResults();
    setStatus("Расписание сформировано.");
  } catch (error) {
    result = null;
    renderResults();
    setStatus(error.message, true);
  }
}

function renderAll() {
  renderTabs();
  renderEditor();
  renderResults();
  renderIcons();
}

function renderTabs() {
  elements.tabs.innerHTML = Object.entries(schemas)
    .map(([key, schema]) => {
      const active = key === activeSection ? " active" : "";
      return `<button class="tab-button${active}" type="button" data-section="${key}">${escapeHtml(schema.title)}</button>`;
    })
    .join("");
}

function renderEditor() {
  if (!dataset) {
    elements.editor.innerHTML = "";
    return;
  }
  const schema = schemas[activeSection];
  const rows = dataset[activeSection] || [];

  const header = schema.fields.map((field) => `<th>${escapeHtml(field.label)}</th>`).join("");
  const body = rows
    .map((row, index) => {
      const cells = schema.fields
        .map((field) => `<td>${fieldControl(field, row[field.key], index)}</td>`)
        .join("");
      return `
        <tr>
          ${cells}
          <td>
            <button class="row-action" type="button" title="Удалить строку" data-delete-index="${index}">
              <i data-lucide="trash-2"></i>
            </button>
          </td>
        </tr>`;
    })
    .join("");

  elements.editor.innerHTML = `
    <div class="table-shell">
      <table class="editor-table">
        <thead>
          <tr>${header}<th></th></tr>
        </thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
  renderIcons();
}

function fieldControl(field, rawValue, index) {
  const value = field.type === "list" ? formatList(rawValue) : rawValue ?? "";
  const common = `data-index="${index}" data-field="${field.key}" data-type="${field.type}"`;

  if (field.type === "select") {
    const options = field.options
      .map(([optionValue, label]) => {
        const selected = optionValue === value ? " selected" : "";
        return `<option value="${escapeHtml(optionValue)}"${selected}>${escapeHtml(label)}</option>`;
      })
      .join("");
    return `<select class="field-select" ${common}>${options}</select>`;
  }

  const inputType = field.type === "number" ? "number" : "text";
  return `<input class="field-input" type="${inputType}" value="${escapeHtml(value)}" ${common} />`;
}

function updateCell(event) {
  const input = event.target.closest("[data-field]");
  if (!input || !dataset) return;
  const index = Number(input.dataset.index);
  const field = input.dataset.field;
  const type = input.dataset.type;
  const value = parseFieldValue(type, input.value);

  dataset[activeSection][index][field] = value;
  result = null;
  renderResults();
}

function addRow() {
  if (!dataset) return;
  dataset[activeSection].push(defaultRow(activeSection));
  result = null;
  renderEditor();
  renderResults();
}

function defaultRow(section) {
  const suffix = Math.random().toString(36).slice(2, 7);
  const nextOrder = (dataset?.timeslots?.length || 0) + 1;

  const defaults = {
    timeslots: { id: `slot-${suffix}`, day: "Понедельник", start: "09:00", end: "10:30", order: nextOrder },
    rooms: { id: `room-${suffix}`, name: "Новая аудитория", capacity: 30, room_type: "practice" },
    teachers: { id: `teacher-${suffix}`, name: "Новый преподаватель", unavailable: [] },
    groups: { id: `group-${suffix}`, name: "Новая группа", size: 25, unavailable: [] },
    lessons: {
      id: `lesson-${suffix}`,
      subject: "Новое занятие",
      teacher_id: dataset?.teachers?.[0]?.id || "",
      group_ids: dataset?.groups?.[0]?.id ? [dataset.groups[0].id] : [],
      sessions: 1,
      room_type: "practice",
      priority: 3,
    },
  };

  return defaults[section];
}

function renderResults() {
  if (!result) {
    elements.metrics.innerHTML = "";
    elements.comparisonBody.innerHTML = "";
    elements.schedule.innerHTML = `<div class="empty-state">Нет рассчитанного расписания.</div>`;
    elements.scheduleCount.textContent = "";
    elements.conflicts.innerHTML = `<div class="empty-state">Нет данных.</div>`;
    elements.conflictCount.textContent = "";
    elements.unscheduled.innerHTML = `<div class="empty-state">Нет данных.</div>`;
    elements.unscheduledCount.textContent = "";
    return;
  }

  const greedy = result.greedy;
  renderMetrics(greedy.stats);
  renderComparison(result.comparisons || []);
  renderSchedule(greedy.entries || []);
  renderConflicts(greedy.conflicts || []);
  renderUnscheduled(greedy.unscheduled || []);
}

function renderMetrics(stats) {
  elements.metrics.innerHTML = [
    metricCard("Размещено", stats.scheduled_count, "green"),
    metricCard("Не размещено", stats.unscheduled_count, stats.unscheduled_count ? "amber" : "green"),
    metricCard("Конфликты", stats.conflict_count, stats.conflict_count ? "red" : "green"),
    metricCard("Заполнение", `${stats.utilization_percent}%`, ""),
  ].join("");
}

function metricCard(label, value, tone) {
  return `
    <div class="metric ${tone}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>`;
}

function renderComparison(rows) {
  elements.comparisonBody.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.title)}</td>
          <td>${escapeHtml(row.scheduled_count)}</td>
          <td>${escapeHtml(row.unscheduled_count)}</td>
          <td>${escapeHtml(row.conflict_count)}</td>
          <td>${escapeHtml(row.utilization_percent)}%</td>
          <td>${escapeHtml(row.elapsed_ms)} мс</td>
        </tr>`
    )
    .join("");
}

function renderSchedule(entries) {
  if (!dataset) return;
  elements.scheduleCount.textContent = `${entries.length} занятий`;

  if (!entries.length) {
    elements.schedule.innerHTML = `<div class="empty-state">Расписание пустое.</div>`;
    return;
  }

  const rooms = dataset.rooms || [];
  const slotsByDay = groupSlotsByDay(dataset.timeslots || []);
  const entryMap = new Map();
  for (const entry of entries) {
    const key = `${entry.timeslot_id}|${entry.room_id}`;
    const list = entryMap.get(key) || [];
    list.push(entry);
    entryMap.set(key, list);
  }

  elements.schedule.innerHTML = Object.entries(slotsByDay)
    .map(([day, slots]) => dayBlock(day, slots, rooms, entryMap))
    .join("");
}

function dayBlock(day, slots, rooms, entryMap) {
  const roomHeaders = rooms.map((room) => `<th>${escapeHtml(room.name)}</th>`).join("");
  const rows = slots
    .map((slot) => {
      const cells = rooms
        .map((room) => {
          const entries = entryMap.get(`${slot.id}|${room.id}`) || [];
          const content = entries.length
            ? entries.map(lessonPill).join("")
            : `<span class="empty-cell">Свободно</span>`;
          return `<td>${content}</td>`;
        })
        .join("");
      return `
        <tr>
          <td><span class="slot-time">${escapeHtml(slot.start)}-${escapeHtml(slot.end)}</span></td>
          ${cells}
        </tr>`;
    })
    .join("");

  const dayCount = slots.reduce((count, slot) => {
    return count + rooms.reduce((sum, room) => sum + (entryMap.get(`${slot.id}|${room.id}`)?.length || 0), 0);
  }, 0);

  return `
    <div class="day-block">
      <div class="day-title">
        <h3>${escapeHtml(day)}</h3>
        <span class="section-count">${dayCount} занятий</span>
      </div>
      <div class="table-shell">
        <table class="day-table">
          <thead>
            <tr><th>Время</th>${roomHeaders}</tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

function lessonPill(entry) {
  return `
    <div class="lesson-pill">
      <strong>${escapeHtml(entry.subject)}</strong>
      <span>${escapeHtml(entry.groups.join(", "))}</span>
      <span>${escapeHtml(entry.teacher)} · ${escapeHtml(entry.room)}</span>
    </div>`;
}

function renderConflicts(conflicts) {
  elements.conflictCount.textContent = `${conflicts.length}`;
  if (!conflicts.length) {
    elements.conflicts.innerHTML = `<div class="empty-state">Конфликтов нет.</div>`;
    return;
  }
  elements.conflicts.innerHTML = conflicts
    .map(
      (conflict) => `
        <div class="event-item conflict">
          <strong>${escapeHtml(conflict.type)}</strong>
          <span>${escapeHtml(conflict.message)}</span>
        </div>`
    )
    .join("");
}

function renderUnscheduled(items) {
  elements.unscheduledCount.textContent = `${items.length}`;
  if (!items.length) {
    elements.unscheduled.innerHTML = `<div class="empty-state">Все занятия размещены.</div>`;
    return;
  }
  elements.unscheduled.innerHTML = items
    .map(
      (item) => `
        <div class="event-item pending">
          <strong>${escapeHtml(item.subject)} · пара ${escapeHtml(item.session_index)}</strong>
          <span>${escapeHtml(item.reason)}</span>
        </div>`
    )
    .join("");
}

function groupSlotsByDay(slots) {
  return slots
    .slice()
    .sort((a, b) => (a.order || 0) - (b.order || 0))
    .reduce((acc, slot) => {
      if (!acc[slot.day]) acc[slot.day] = [];
      acc[slot.day].push(slot);
      return acc;
    }, {});
}

function exportJson() {
  if (!dataset) return;
  const blob = new Blob([JSON.stringify(dataset, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "schedule-data.json";
  link.click();
  URL.revokeObjectURL(url);
}

async function importJson(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    dataset = JSON.parse(await file.text());
    result = null;
    renderAll();
    setStatus("Данные импортированы.");
  } catch (error) {
    setStatus(`Не удалось импортировать JSON: ${error.message}`, true);
  } finally {
    event.target.value = "";
  }
}

function parseFieldValue(type, value) {
  if (type === "number") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  if (type === "list") return parseList(value);
  return value;
}

function parseList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatList(value) {
  if (Array.isArray(value)) return value.join(", ");
  return value || "";
}

function setStatus(message, isError = false) {
  elements.status.textContent = message;
  elements.status.classList.toggle("error", isError);
}

function assertResponse(response) {
  if (!response.ok) {
    throw new Error(`Ошибка API: ${response.status}`);
  }
}

function formatApiError(payload) {
  if (!payload?.detail) return "";
  if (!Array.isArray(payload.detail)) return String(payload.detail);
  return payload.detail
    .map((item) => {
      const path = Array.isArray(item.loc) ? item.loc.join(".") : "";
      return `${path}: ${item.msg}`;
    })
    .join("; ");
}

function renderIcons() {
  if (window.lucide?.createIcons) {
    window.lucide.createIcons();
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return replacements[char];
  });
}
