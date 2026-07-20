"use strict";

const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

// ─── Telegram init + tema ───
function applyTheme() {
  if (!tg) return;
  const t = tg.themeParams || {};
  const r = document.documentElement.style;
  const set = (v, k) => { if (t[k]) r.setProperty(v, t[k]); };
  set("--bg", "bg_color");
  set("--text", "text_color");
  set("--hint", "hint_color");
  set("--link", "link_color");
  set("--btn", "button_color");
  set("--btn-text", "button_text_color");
  set("--sec-bg", "secondary_bg_color");
  set("--card", "section_bg_color");
}
if (tg) {
  try { tg.ready(); tg.expand(); } catch (e) {}
  applyTheme();
  tg.onEvent && tg.onEvent("themeChanged", applyTheme);
}

// ─── Holat ───
let CONFIG = { prepay_percent: 10, delivery_fee: 19000, free_threshold: 300000, contact_phone: "" };
let ALL = [];            // grid uchun oxirgi yuklangan ro'yxat
let CART = loadCart();
const view = document.getElementById("view");

// ─── Yordamchilar ───
function money(n) { return (Number(n) || 0).toLocaleString("ru-RU").replace(/,/g, " "); }
function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function loadCart() { try { return JSON.parse(localStorage.getItem("pm_cart") || "[]"); } catch (e) { return []; } }
function saveCart() { localStorage.setItem("pm_cart", JSON.stringify(CART)); updateCartBadge(); }
function cartCount() { return CART.reduce((s, i) => s + i.qty, 0); }
function cartTotal() { return CART.reduce((s, i) => s + i.price * i.qty, 0); }
function haptic() { try { tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred("light"); } catch (e) {} }

function updateCartBadge() {
  const b = document.getElementById("cart-badge");
  const n = cartCount();
  b.textContent = n;
  b.hidden = n === 0;
}

let toastTimer = null;
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg; el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 1800);
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

// ─── Navigatsiya ───
function setNav(name) {
  document.querySelectorAll(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.nav === name));
}
document.querySelectorAll(".nav-item").forEach(b => {
  b.addEventListener("click", () => {
    const n = b.dataset.nav;
    if (n === "catalog") renderCatalog();
    else if (n === "cart") renderCart();
    else if (n === "orders") renderOrders();
    else if (n === "profile") renderProfile();
  });
});
document.getElementById("cart-btn").addEventListener("click", renderCart);

// ─── Katalog (grid) ───
let searchTimer = null;
const searchEl = document.getElementById("search");
searchEl.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadProducts(searchEl.value.trim()), 300);
});

let activeChip = "";
async function loadProducts(q) {
  view.innerHTML = '<div class="loading">Yuklanmoqda…</div>';
  try {
    ALL = await api("/api/products" + (q ? "?q=" + encodeURIComponent(q) : ""));
  } catch (e) {
    view.innerHTML = '<div class="empty"><div class="em-ico">⚠️</div>Ma\'lumot yuklanmadi. Qayta urinib ko\'ring.</div>';
    return;
  }
  buildChips();
  renderGrid();
}

function buildChips() {
  const shops = [];
  ALL.forEach(p => { if (p.shop_name && !shops.includes(p.shop_name)) shops.push(p.shop_name); });
  const box = document.getElementById("chips");
  if (shops.length < 2) { box.innerHTML = ""; return; }
  const chip = (label, val) => `<div class="chip${activeChip === val ? " active" : ""}" data-val="${esc(val)}">${esc(label)}</div>`;
  box.innerHTML = chip("Hammasi", "") + shops.map(s => chip(s, s)).join("");
  box.querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => {
    activeChip = c.dataset.val; buildChips(); renderGrid();
  }));
}

function renderGrid() {
  setNav("catalog");
  const items = activeChip ? ALL.filter(p => p.shop_name === activeChip) : ALL;
  if (!items.length) {
    view.innerHTML = '<div class="empty"><div class="em-ico">🔍</div>Mahsulot topilmadi.</div>';
    return;
  }
  view.innerHTML = '<div class="grid">' + items.map(cardHTML).join("") + "</div>";
  view.querySelectorAll(".pcard").forEach(c => c.addEventListener("click", () => openDetail(+c.dataset.id)));
}

function discPct(p) {
  if (p.old_price && p.old_price > p.price) return Math.round((1 - p.price / p.old_price) * 100);
  return 0;
}

function cardHTML(p) {
  const d = discPct(p);
  const img = p.photo
    ? `<img src="${esc(p.photo)}" loading="lazy" alt="">`
    : '<div class="noimg">📦</div>';
  const free = p.price >= CONFIG.free_threshold ? '<div class="pcard-free">Bepul yetkazish</div>' : "";
  const old = p.old_price && p.old_price > p.price ? `<div class="pcard-old">${money(p.old_price)}</div>` : "";
  const badge = d ? `<span class="badge-disc">-${d}%</span>` : "";
  return `<div class="pcard" data-id="${p.id}">
    <div class="pcard-img">${img}${badge}</div>
    <div class="pcard-body">
      <div class="pcard-name">${esc(p.name)}</div>
      <div class="pcard-price">${money(p.price)}</div>
      ${old}${free}
    </div>
  </div>`;
}

// ─── Mahsulot detali ───
let detailViews = 0;
async function openDetail(id) {
  view.scrollTo && window.scrollTo(0, 0);
  view.innerHTML = '<div class="loading">Yuklanmoqda…</div>';
  let p;
  try { p = await api("/api/product/" + id); } catch (e) {
    view.innerHTML = '<div class="empty"><div class="em-ico">⚠️</div>Mahsulot topilmadi.</div>'; return;
  }
  const imgs = (p.photos && p.photos.length)
    ? p.photos.map(u => `<img src="${esc(u)}" alt="">`).join("")
    : '<div class="noimg" style="aspect-ratio:1/1;background:var(--sec-bg);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:40px;flex:0 0 82%">📦</div>';
  const d = discPct(p);
  const old = p.old_price && p.old_price > p.price ? `<span class="detail-old">${money(p.old_price)}</span>` : "";
  const warranty = p.warranty ? `<div class="row"><span>🛡 Kafolat</span><span>${esc(p.warranty)}</span></div>` : `<div class="row"><span>🛡 Kafolat</span><span>Mavjud</span></div>`;
  const free = p.price >= CONFIG.free_threshold;
  view.innerHTML = `
    <button class="back-link" id="back">← Orqaga</button>
    <div class="detail-imgs">${imgs}</div>
    <div class="detail-name">${esc(p.name)}</div>
    ${p.shop_name ? `<div class="detail-shop">🏪 ${esc(p.shop_name)}${p.city ? " · " + esc(p.city) : ""}</div>` : ""}
    <div><span class="detail-price">${money(p.price)}</span>${old}${d ? ` <span class="badge-disc" style="position:static">-${d}%</span>` : ""}</div>
    <div class="info-block">
      <div class="row"><span>🚚 Yetkazib berish</span><span>${free ? "Bepul" : money(CONFIG.delivery_fee)}</span></div>
      <div class="row"><span>💳 Oldindan to'lov</span><span>${CONFIG.prepay_percent}%</span></div>
      ${warranty}
    </div>
    ${p.description ? `<div class="detail-desc">${esc(p.description)}</div>` : ""}
    <button class="btn btn-primary sticky-cta" id="add" ${p.available ? "" : "disabled"}>${p.available ? "🛒 Savatga qo'shish" : "Hozircha tugagan"}</button>
    <div style="height:80px"></div>
  `;
  document.getElementById("back").addEventListener("click", renderCatalog);
  if (p.available) document.getElementById("add").addEventListener("click", () => {
    addToCart(p); haptic(); toast("Savatga qo'shildi");
  });

  // 3-mahsulotdan keyin ekranga o'rnatish taklifi
  detailViews++;
  if (detailViews >= 3) maybePromptA2HS();
}

function addToCart(p) {
  const existing = CART.find(i => i.id === p.id);
  if (existing) existing.qty++;
  else CART.push({ id: p.id, name: p.name, price: p.price, photo: (p.photos && p.photos[0]) || p.photo || null, qty: 1, color: "" });
  saveCart();
}

// ─── Savat ───
function renderCatalog() {
  setNav("catalog");
  if (ALL.length) { buildChips(); renderGrid(); }
  else loadProducts("");
}

function renderCart() {
  setNav("cart");
  window.scrollTo(0, 0);
  if (!CART.length) {
    view.innerHTML = '<div class="empty"><div class="em-ico">🛒</div>Savat bo\'sh.<br>Katalogdan mahsulot tanlang.</div>';
    return;
  }
  const items = CART.map((i, idx) => `
    <div class="citem">
      ${i.photo ? `<img src="${esc(i.photo)}" alt="">` : '<img alt="">'}
      <div class="citem-body">
        <div class="citem-name">${esc(i.name)}</div>
        <div class="citem-price">${money(i.price)}</div>
        <div class="qty">
          <button data-act="dec" data-i="${idx}">−</button>
          <span>${i.qty}</span>
          <button data-act="inc" data-i="${idx}">+</button>
        </div>
      </div>
      <button class="citem-del" data-act="del" data-i="${idx}">✕</button>
    </div>`).join("");
  const total = cartTotal();
  const fee = total >= CONFIG.free_threshold ? 0 : CONFIG.delivery_fee;
  const prepay = Math.round(total * CONFIG.prepay_percent / 100);
  view.innerHTML = items + `
    <div class="summary">
      <div class="row"><span>Mahsulotlar</span><span>${money(total)}</span></div>
      <div class="row"><span>Yetkazib berish</span><span>${fee ? money(fee) : "Bepul"}</span></div>
      <div class="row total"><span>Jami</span><span>${money(total + fee)}</span></div>
      <div class="row" style="color:var(--hint);font-size:12px"><span>Oldindan to'lov (${CONFIG.prepay_percent}%)</span><span>${money(prepay)}</span></div>
    </div>
    <button class="btn btn-primary" id="checkout">Buyurtma berish</button>
    <div style="height:80px"></div>`;
  view.querySelectorAll("[data-act]").forEach(b => b.addEventListener("click", () => {
    const idx = +b.dataset.i, act = b.dataset.act;
    if (act === "inc") CART[idx].qty++;
    else if (act === "dec") { CART[idx].qty--; if (CART[idx].qty < 1) CART.splice(idx, 1); }
    else if (act === "del") CART.splice(idx, 1);
    saveCart(); renderCart();
  }));
  document.getElementById("checkout").addEventListener("click", renderCheckout);
}

// ─── Checkout (to'liq ilovada) ───
let receiptFile = null;
function renderCheckout() {
  window.scrollTo(0, 0);
  receiptFile = null;
  const total = cartTotal();
  const fee = total >= CONFIG.free_threshold ? 0 : CONFIG.delivery_fee;
  const prepay = Math.round(total * CONFIG.prepay_percent / 100);
  const multi = CART.length > 1;
  view.innerHTML = `
    <button class="back-link" id="back">← Savat</button>
    <h3 style="margin:4px 0 12px;font-size:17px">Buyurtmani rasmiylashtirish</h3>
    ${multi ? '<div class="info-block" style="margin-top:0">ℹ️ Har bir mahsulot alohida buyurtma sifatida rasmiylashtiriladi.</div>' : ""}
    <div class="field">
      <label>Manzil (shahar, ko'cha, uy)</label>
      <textarea id="f-address" placeholder="Toshkent, Chilonzor 12-kvartal, 5-uy"></textarea>
    </div>
    <div class="field">
      <label>Telefon raqamingiz</label>
      <input id="f-phone" type="tel" inputmode="tel" placeholder="+998 90 123 45 67">
    </div>
    <div class="summary">
      <div class="row"><span>Jami</span><span>${money(total + fee)}</span></div>
      <div class="row total"><span>Oldindan to'lov (${CONFIG.prepay_percent}%)</span><span>${money(prepay)}</span></div>
    </div>
    <div class="card-copy">
      <span>Karta: <code id="cardno">${esc(CONFIG.card || "—")}</code>${CONFIG.card_name ? " <span style='color:var(--hint);font-size:12px'>(" + esc(CONFIG.card_name) + ")</span>" : ""}</span>
      <button class="btn-ghost" style="width:auto;padding:6px 12px;font-size:13px" id="copycard">Nusxa</button>
    </div>
    <div class="field">
      <label>To'lov chekini yuklang (rasm yoki PDF)</label>
      <label class="file-box" id="filebox" for="f-receipt">📎 Chek faylini tanlang</label>
      <input id="f-receipt" type="file" accept="image/*,application/pdf" hidden>
    </div>
    <button class="btn btn-primary" id="submit">Buyurtmani tasdiqlash</button>
    <div style="height:80px"></div>
  `;
  document.getElementById("back").addEventListener("click", renderCart);
  document.getElementById("copycard").addEventListener("click", () => {
    const t = CONFIG.card || "";
    if (t) { navigator.clipboard && navigator.clipboard.writeText(t); toast("Karta nusxalandi"); }
  });
  const fileInput = document.getElementById("f-receipt");
  fileInput.addEventListener("change", () => {
    receiptFile = fileInput.files[0] || null;
    const box = document.getElementById("filebox");
    if (receiptFile) { box.textContent = "✅ " + receiptFile.name; box.classList.add("has"); }
    else { box.textContent = "📎 Chek faylini tanlang"; box.classList.remove("has"); }
  });
  document.getElementById("submit").addEventListener("click", submitOrder);
}

async function submitOrder() {
  const address = document.getElementById("f-address").value.trim();
  const phone = document.getElementById("f-phone").value.trim();
  if (!address) return toast("Manzilni kiriting");
  if (!phone) return toast("Telefon raqamini kiriting");
  if (!receiptFile) return toast("To'lov chekini yuklang");
  if (!tg || !tg.initData) return toast("Ilovani Telegram orqali oching");

  const btn = document.getElementById("submit");
  btn.disabled = true; btn.textContent = "Yuborilmoqda…";

  // Har bir savat elementi alohida buyurtma (bot bilan bir xil model).
  let lastId = null;
  try {
    for (const item of CART) {
      const fd = new FormData();
      fd.append("initData", tg.initData);
      fd.append("payload", JSON.stringify({
        product_id: item.id, quantity: item.qty, color: item.color || "",
        address, phone, delivery: "taxi"
      }));
      fd.append("receipt", receiptFile, receiptFile.name);
      const r = await api("/api/order", { method: "POST", body: fd });
      lastId = r.order_id;
    }
  } catch (e) {
    btn.disabled = false; btn.textContent = "Buyurtmani tasdiqlash";
    return toast("Xatolik. Qayta urinib ko'ring.");
  }

  CART = []; saveCart();
  haptic();
  showSuccess(lastId);
}

function showSuccess(orderId) {
  window.scrollTo(0, 0);
  view.innerHTML = `
    <div class="empty">
      <div class="em-ico">✅</div>
      <div style="font-size:18px;font-weight:600;color:var(--text);margin-bottom:8px">Buyurtma qabul qilindi</div>
      <div>Raqam: <b>#${esc(orderId)}</b></div>
      <div style="margin-top:10px">Chek tekshirilgach operator siz bilan bog'lanadi.</div>
      ${CONFIG.contact_phone ? `<div style="margin-top:6px">📞 ${esc(CONFIG.contact_phone)}</div>` : ""}
      <button class="btn btn-primary" style="margin-top:24px" id="back-shop">Xaridni davom ettirish</button>
    </div>`;
  document.getElementById("back-shop").addEventListener("click", renderCatalog);
}

// ─── Buyurtmalarim / Profil (sodda) ───
function renderOrders() {
  setNav("orders");
  view.innerHTML = `<div class="empty"><div class="em-ico">📦</div>Buyurtmalaringizni bot ichidagi «📦 Buyurtmalarim» bo'limidan kuzatishingiz mumkin.<br><br><button class="btn btn-ghost" style="max-width:220px;margin:0 auto" id="toshop">Katalogga qaytish</button></div>`;
  const b = document.getElementById("toshop"); b && b.addEventListener("click", renderCatalog);
}
function renderProfile() {
  setNav("profile");
  const u = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || {};
  const name = [u.first_name, u.last_name].filter(Boolean).join(" ") || "Foydalanuvchi";
  view.innerHTML = `
    <div class="info-block" style="margin-top:0">
      <div style="font-size:16px;font-weight:600;margin-bottom:4px">${esc(name)}</div>
      ${u.username ? `<div style="color:var(--hint);font-size:13px">@${esc(u.username)}</div>` : ""}
    </div>
    <div class="info-block">
      <div class="row"><span>💳 Oldindan to'lov</span><span>${CONFIG.prepay_percent}%</span></div>
      <div class="row"><span>🚛 Bepul yetkazish</span><span>${money(CONFIG.free_threshold)}+</span></div>
      ${CONFIG.contact_phone ? `<div class="row"><span>📞 Aloqa</span><span>${esc(CONFIG.contact_phone)}</span></div>` : ""}
    </div>
    <button class="btn btn-ghost" id="a2hs-open">📲 Ilovani ekranga o'rnatish</button>`;
  const a = document.getElementById("a2hs-open");
  a && a.addEventListener("click", () => showA2HS(true));
}

// ─── Ekranga o'rnatish (Add to Home Screen, Bot API 8.0+) ───
function maybePromptA2HS() {
  if (!tg) return;
  if (localStorage.getItem("a2hs_done")) return;
  if (typeof tg.checkHomeScreenStatus === "function") {
    try {
      tg.checkHomeScreenStatus(status => {
        if (status === "added" || status === "unsupported") {
          localStorage.setItem("a2hs_done", "1"); return;
        }
        showA2HS(false);
      });
    } catch (e) { /* eski klient */ }
  }
}

function showA2HS(force) {
  if (!tg) { if (force) toast("Ilovani Telegram orqali oching"); return; }
  if (typeof tg.addToHomeScreen !== "function") { if (force) toast("Telegram ilovangizni yangilang"); return; }
  document.getElementById("a2hs").hidden = false;
}
document.getElementById("a2hs-add").addEventListener("click", () => {
  try { tg && tg.addToHomeScreen && tg.addToHomeScreen(); } catch (e) {}
  localStorage.setItem("a2hs_done", "1");
  document.getElementById("a2hs").hidden = true;
});
document.getElementById("a2hs-later").addEventListener("click", () => {
  localStorage.setItem("a2hs_done", "1");
  document.getElementById("a2hs").hidden = true;
});
if (tg && tg.onEvent) tg.onEvent("homeScreenAdded", () => localStorage.setItem("a2hs_done", "1"));

// ─── Boshlash ───
(async function init() {
  updateCartBadge();
  try { CONFIG = Object.assign(CONFIG, await api("/api/config")); } catch (e) {}
  try { const c = await api("/api/config"); if (c) CONFIG = Object.assign(CONFIG, c); } catch (e) {}
  await loadProducts("");
})();
