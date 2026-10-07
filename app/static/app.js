/**
 * Driver Shift Diary - Mobile-First Receipt Client
 */

const state = {
  currentDate: "",
  availableDates: [],
  trips: [],
  summary: null,
  currency: "₸", // Default to Tenge ₸ as in the test task mockup
};

// DOM Elements
const elements = {
  dateInput: document.getElementById("shiftDateInput"),
  prevDayBtn: document.getElementById("prevDayBtn"),
  nextDayBtn: document.getElementById("nextDayBtn"),
  todayBtn: document.getElementById("todayBtn"),
  availableDatesList: document.getElementById("availableDatesList"),

  // Receipt elements
  receiptCard: document.getElementById("receiptCard"),
  receiptPaperArea: document.getElementById("receiptPaperArea"),
  receiptDate: document.getElementById("receiptDate"),
  receiptTripsList: document.getElementById("receiptTripsList"),
  receiptTotalTrips: document.getElementById("receiptTotalTrips"),
  receiptTotalGross: document.getElementById("receiptTotalGross"),
  receiptTotalComm: document.getElementById("receiptTotalComm"),
  receiptCashCard: document.getElementById("receiptCashCard"),
  receiptNetIncome: document.getElementById("receiptNetIncome"),
  rawReceiptLink: document.getElementById("rawReceiptLink"),

  // Modal
  addTripModal: document.getElementById("addTripModal"),
  openAddModalBtnDesktop: document.getElementById("openAddModalBtnDesktop"),
  openAddModalBtnMobile: document.getElementById("openAddModalBtnMobile"),
  closeModalBtn: document.getElementById("closeModalBtn"),
  cancelModalBtn: document.getElementById("cancelModalBtn"),
  addTripForm: document.getElementById("addTripForm"),
  formAlert: document.getElementById("formAlert"),
  tripStart: document.getElementById("tripStart"),
  tripEnd: document.getElementById("tripEnd"),
  timeValidationMsg: document.getElementById("timeValidationMsg"),
  tripAmount: document.getElementById("tripAmount"),
  amountValidationMsg: document.getElementById("amountValidationMsg"),
  tripCommission: document.getElementById("tripCommission"),
  tripId: document.getElementById("tripId"),
  submitTripBtn: document.getElementById("submitTripBtn"),
  formCurrLabel: document.getElementById("formCurrLabel"),

  // Currency
  currKztBtn: document.getElementById("currKztBtn"),
  currRubBtn: document.getElementById("currRubBtn"),

  // Action buttons
  shareReceiptBtn: document.getElementById("shareReceiptBtn"),
  resetDataBtn: document.getElementById("resetDataBtn"),
  toastContainer: document.getElementById("toastContainer"),
};

// Format utilities
function formatAmount(val) {
  if (val === undefined || val === null) return "0";
  const num = Number(val);
  const formatted = new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: num % 1 !== 0 ? 2 : 0,
    maximumFractionDigits: 2,
  }).format(num);
  return formatted;
}

function formatDateDot(dateStr) {
  if (!dateStr) return "";
  const parts = dateStr.split("-");
  if (parts.length === 3) {
    return `${parts[2]}.${parts[1]}.${parts[0]}`;
  }
  return dateStr;
}

function formatTimeOnly(isoStr) {
  try {
    const d = new Date(isoStr);
    const h = String(d.getHours()).padStart(2, "0");
    const m = String(d.getMinutes()).padStart(2, "0");
    return `${h}:${m}`;
  } catch (e) {
    return isoStr.substring(11, 16);
  }
}

function toLocalIsoInput(date) {
  const pad = (n) => String(n).padStart(2, "0");
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  const icon = type === "success" ? "✅" : type === "warning" ? "⚠️" : "❌";
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;

  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Quick amount addition on mobile
window.addAmountPreset = (preset) => {
  const currentVal = parseFloat(elements.tripAmount.value) || 0;
  const newVal = currentVal > 0 ? currentVal + preset : preset;
  elements.tripAmount.value = newVal;
  elements.tripCommission.value = Math.round(newVal * 0.15);
  elements.amountValidationMsg.classList.add("hidden");
};

// Currency Switcher
window.setCurrency = (curr) => {
  state.currency = curr;
  elements.currKztBtn.classList.toggle("active", curr === "₸");
  elements.currRubBtn.classList.toggle("active", curr === "₽");
  elements.formCurrLabel.textContent = `(${curr})`;
  renderReceipt();
};

// API
async function fetchShiftData(date = "") {
  try {
    const url = date ? `/api/trips?date=${encodeURIComponent(date)}` : "/api/trips";
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Ошибка при получении данных смены");
    }
    const data = await res.json();

    state.currentDate = data.date;
    state.summary = data.summary;
    state.trips = data.trips;
    state.availableDates = data.available_dates || [];

    renderUI();
  } catch (err) {
    console.error(err);
    showToast(err.message, "error");
  }
}

function renderUI() {
  // Update inputs
  elements.dateInput.value = state.currentDate;
  if (elements.rawReceiptLink) {
    elements.rawReceiptLink.href = `/api/receipt?date=${state.currentDate}&currency=${encodeURIComponent(state.currency)}`;
  }

  // Update date pills
  elements.availableDatesList.innerHTML = "";
  state.availableDates.forEach((d) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `chip-btn ${d === state.currentDate ? "active" : ""}`;
    btn.textContent = formatDateDot(d);
    btn.onclick = () => {
      if (d !== state.currentDate) fetchShiftData(d);
    };
    elements.availableDatesList.appendChild(btn);
  });

  renderReceipt();
}

function renderReceipt() {
  const s = state.summary;
  const c = state.currency;

  elements.receiptDate.textContent = formatDateDot(state.currentDate);

  // Trips rows
  elements.receiptTripsList.innerHTML = "";
  if (!state.trips || state.trips.length === 0) {
    elements.receiptTripsList.innerHTML = `
      <div class="receipt-row" style="color:#94a3b8; font-style: italic; justify-content: center; padding: 12px 0;">
        — Нет поездок за эту дату —
      </div>
    `;
  } else {
    state.trips.forEach((t) => {
      const row = document.createElement("div");
      row.className = "receipt-row";
      const startTime = formatTimeOnly(t.start);
      const endTime = formatTimeOnly(t.end);
      const payLabel = t.payment === "card" ? "карта" : "нал.";

      row.innerHTML = `
        <span class="row-left">${startTime}–${endTime} ${payLabel}</span>
        <span class="row-right">${formatAmount(t.amount)} ${c}</span>
      `;
      elements.receiptTripsList.appendChild(row);
    });
  }

  // Summary rows
  if (s) {
    elements.receiptTotalTrips.textContent = s.total_trips;
    elements.receiptTotalGross.textContent = `${formatAmount(s.total_amount)} ${c}`;
    elements.receiptTotalComm.textContent = `-${formatAmount(s.total_commission)} ${c}`;
    elements.receiptCashCard.textContent = `${formatAmount(s.cash_amount)} / ${formatAmount(s.card_amount)}`;
    elements.receiptNetIncome.textContent = `${formatAmount(s.net_income)} ${c}`;
  }
}

// Generate Receipt Text for Sharing/Copying
function generateReceiptText() {
  const s = state.summary;
  const c = state.currency;
  const dateFormatted = formatDateDot(state.currentDate);

  let text = `       Дневник смен       \n        ${dateFormatted}        \n\n`;

  state.trips.forEach((t) => {
    const timePart = `${formatTimeOnly(t.start)}–${formatTimeOnly(t.end)} ${t.payment === "card" ? "карта" : "нал."}`;
    const amtPart = `${formatAmount(t.amount)} ${c}`;
    const spaces = " ".repeat(Math.max(1, 34 - timePart.length - amtPart.length));
    text += `${timePart}${spaces}${amtPart}\n`;
  });

  const divider = "-".repeat(34) + "\n";
  text += divider;

  const row = (label, val) => `${label}${" ".repeat(Math.max(1, 34 - label.length - val.length))}${val}\n`;

  text += row("Поездок", String(s.total_trips));
  text += row("Выручка", `${formatAmount(s.total_amount)} ${c}`);
  text += row("Комиссия", `-${formatAmount(s.total_commission)} ${c}`);
  text += row("Наличные / карта", `${formatAmount(s.cash_amount)} / ${formatAmount(s.card_amount)}`);
  text += divider;
  text += row("На руки", `${formatAmount(s.net_income)} ${c}`);

  return text;
}

// Share / Copy handler with native mobile Web Share API support
elements.shareReceiptBtn.addEventListener("click", async () => {
  const text = generateReceiptText();
  const dateFormatted = formatDateDot(state.currentDate);

  if (navigator.share) {
    try {
      await navigator.share({
        title: `Дневник смен — ${dateFormatted}`,
        text: text,
      });
      return;
    } catch (err) {
      if (err.name === "AbortError") return; // User closed share sheet
    }
  }

  // Fallback to clipboard
  navigator.clipboard.writeText(text).then(
    () => showToast("Чек скопирован в буфер обмена!"),
    () => showToast("Не удалось скопировать", "error")
  );
});

// Mobile Swipe Gesture on Receipt Card
let touchStartX = 0;
let touchStartY = 0;

elements.receiptPaperArea.addEventListener("touchstart", (e) => {
  touchStartX = e.changedTouches[0].screenX;
  touchStartY = e.changedTouches[0].screenY;
}, { passive: true });

elements.receiptPaperArea.addEventListener("touchend", (e) => {
  const touchEndX = e.changedTouches[0].screenX;
  const touchEndY = e.changedTouches[0].screenY;
  const deltaX = touchEndX - touchStartX;
  const deltaY = touchEndY - touchStartY;

  // Only trigger horizontal swipe if movement is predominantly horizontal
  if (Math.abs(deltaX) > 60 && Math.abs(deltaX) > Math.abs(deltaY) * 1.5) {
    if (deltaX < 0) {
      // Swiped left -> next day
      shiftDateByDays(1);
      showToast("Следующий день ▶", "success");
    } else {
      // Swiped right -> prev day
      shiftDateByDays(-1);
      showToast("◀ Предыдущий день", "success");
    }
  }
}, { passive: true });

// Date switching
function shiftDateByDays(days) {
  if (!state.currentDate) return;
  const parts = state.currentDate.split("-");
  const d = new Date(parts[0], parts[1] - 1, parts[2]);
  d.setDate(d.getDate() + days);
  const pad = (n) => String(n).padStart(2, "0");
  const newDate = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  fetchShiftData(newDate);
}

elements.prevDayBtn.addEventListener("click", () => shiftDateByDays(-1));
elements.nextDayBtn.addEventListener("click", () => shiftDateByDays(1));
elements.todayBtn.addEventListener("click", () => {
  const pad = (n) => String(n).padStart(2, "0");
  const now = new Date();
  fetchShiftData(`${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`);
});
elements.dateInput.addEventListener("change", (e) => {
  if (e.target.value) fetchShiftData(e.target.value);
});

// Modal Logic
function openModal() {
  elements.formAlert.classList.add("hidden");
  elements.timeValidationMsg.classList.add("hidden");
  elements.amountValidationMsg.classList.add("hidden");

  let baseDate = new Date();
  if (state.currentDate) {
    const [y, m, d] = state.currentDate.split("-").map(Number);
    baseDate.setFullYear(y, m - 1, d);
  }

  const start = new Date(baseDate.getTime());
  const end = new Date(baseDate.getTime() + 25 * 60 * 1000);

  elements.tripStart.value = toLocalIsoInput(start);
  elements.tripEnd.value = toLocalIsoInput(end);
  elements.tripAmount.value = "";
  elements.tripCommission.value = "";
  elements.tripId.value = "";

  elements.addTripModal.classList.remove("hidden");
  setTimeout(() => elements.tripAmount.focus(), 100);
}

function closeModal() {
  elements.addTripModal.classList.add("hidden");
}

if (elements.openAddModalBtnDesktop) {
  elements.openAddModalBtnDesktop.addEventListener("click", openModal);
}
if (elements.openAddModalBtnMobile) {
  elements.openAddModalBtnMobile.addEventListener("click", openModal);
}

elements.closeModalBtn.addEventListener("click", closeModal);
elements.cancelModalBtn.addEventListener("click", closeModal);
elements.addTripModal.addEventListener("click", (e) => {
  if (e.target === elements.addTripModal) closeModal();
});

// Auto commission calculation
elements.tripAmount.addEventListener("input", () => {
  const amt = parseFloat(elements.tripAmount.value);
  if (!isNaN(amt) && amt > 0) {
    elements.tripCommission.value = Math.round(amt * 0.15);
  }
});

// Form submit
elements.addTripForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const start = new Date(elements.tripStart.value);
  const end = new Date(elements.tripEnd.value);
  const amount = parseFloat(elements.tripAmount.value);

  // Validations
  let valid = true;
  if (!elements.tripStart.value || !elements.tripEnd.value || end <= start) {
    elements.timeValidationMsg.classList.remove("hidden");
    valid = false;
  } else {
    elements.timeValidationMsg.classList.add("hidden");
  }

  if (isNaN(amount) || amount <= 0) {
    elements.amountValidationMsg.classList.remove("hidden");
    valid = false;
  } else {
    elements.amountValidationMsg.classList.add("hidden");
  }

  if (!valid) return;

  const commission = elements.tripCommission.value
    ? parseFloat(elements.tripCommission.value)
    : Math.round(amount * 0.15);
  const payment = elements.addTripForm.querySelector('input[name="tripPayment"]:checked').value;
  const customId = elements.tripId.value.trim() || undefined;

  const payload = {
    start: start.toISOString(),
    end: end.toISOString(),
    amount: amount,
    commission: commission,
    payment: payment,
  };
  if (customId) payload.id = customId;

  try {
    elements.submitTripBtn.disabled = true;
    const res = await fetch("/api/trips", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      const errDetail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join(", ") : data.detail;
      elements.formAlert.className = "alert alert-danger";
      elements.formAlert.textContent = `❌ ${errDetail}`;
      elements.formAlert.classList.remove("hidden");
      return;
    }

    if (data.is_duplicate) {
      elements.formAlert.className = "alert alert-warning";
      elements.formAlert.textContent = `⚠️ Поездка #${data.trip.id} уже есть в базе. Дубль предотвращен!`;
      elements.formAlert.classList.remove("hidden");
      showToast(`Поездка #${data.trip.id} уже зарегистрирована`, "warning");
    } else {
      showToast(`Поездка #${data.trip.id} сохранена!`);
      closeModal();
      fetchShiftData(data.trip.start.substring(0, 10));
    }
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    elements.submitTripBtn.disabled = false;
  }
});

// Reset data
elements.resetDataBtn.addEventListener("click", async () => {
  if (!confirm("Сбросить данные к образцу из задания?")) return;
  await fetch("/api/reset", { method: "POST" });
  showToast("Данные сброшены к начальным");
  fetchShiftData("2026-10-01");
});

// Initial load
document.addEventListener("DOMContentLoaded", () => {
  fetchShiftData("2026-10-01");
});
