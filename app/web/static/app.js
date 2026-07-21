"use strict";

const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
if (tg) { try { tg.ready(); tg.expand(); } catch (e) {} }

/* ─── Telegram tabiiy "orqaga" tugmasi ───
   Detal sahifada Telegram (telefonning) o'z BackButton'ini ko'rsatamiz;
   asosiy bo'limlarga qaytilganda yashiramiz. Oddiy brauzerda (tg yo'q)
   sahifadagi zaxira "← Orqaga" havolasi ishlaydi. */
let _backHandler = null;
function showBack(handler) {
  if (!tg || !tg.BackButton) return;
  hideBack();
  _backHandler = handler;
  try { tg.BackButton.onClick(handler); tg.BackButton.show(); } catch (e) {}
}
function hideBack() {
  if (!tg || !tg.BackButton) return;
  try {
    if (_backHandler) tg.BackButton.offClick(_backHandler);
    tg.BackButton.hide();
  } catch (e) {}
  _backHandler = null;
}

/* ─── Holat ─── */
let CONFIG = { prepay_percent: 10, delivery_fee: 19000, free_threshold: 300000, contact_phone: "", card: "", card_name: "" };
let STATS = { products: 0, orders_total: 0, orders_last_hour: 0, orders_today: 0, shops: 0 };
let ALL = [];
let CART = load("pm_cart", []);
let FAV = new Set(load("pm_fav", []));
let ME = { is_owner: false, is_admin: false, is_seller: false, shop: null };  // panel rollari (/api/me)
const view = document.getElementById("view");
let returnView = renderHome;   // detaldan "orqaga" qaytiladigan ekran

/* ─── Yordamchilar ─── */
function money(n) { return (Number(n) || 0).toLocaleString("ru-RU").replace(/,/g, " "); }
function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function load(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch (e) { return d; } }
function save(k, v) { localStorage.setItem(k, JSON.stringify(v)); }
function saveCart() { save("pm_cart", CART); updateBadges(); }
function saveFav() { save("pm_fav", [...FAV]); }
function cartCount() { return CART.reduce((s, i) => s + i.qty, 0); }
function cartTotal() { return CART.reduce((s, i) => s + i.price * i.qty, 0); }
function haptic(t) { try { tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred(t || "light"); } catch (e) {} }

function updateBadges() {
  const n = cartCount();
  for (const id of ["cart-badge", "nav-cart-badge"]) {
    const b = document.getElementById(id); if (!b) continue;
    b.textContent = n; b.hidden = n === 0;
  }
}

let toastTimer = null;
function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg; el.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.hidden = true, 1800);
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

/* ─── Timerlar (bosh sahifa) ─── */
let homeTimers = [];
function clearHomeTimers() { homeTimers.forEach(clearInterval); homeTimers = []; }

/* ─── Navigatsiya ─── */
function setNav(name) {
  clearHomeTimers();
  hideBack();
  document.querySelectorAll(".nav-item").forEach(b => b.classList.toggle("active", b.dataset.nav === name));
  window.scrollTo(0, 0);
}
document.querySelectorAll(".nav-item").forEach(b => b.addEventListener("click", () => go(b.dataset.nav)));
document.getElementById("cart-btn").addEventListener("click", () => go("cart"));
document.getElementById("fav-btn").addEventListener("click", () => go("favorites"));
function go(nav) {
  if (nav === "home") renderHome();
  else if (nav === "catalog") renderCatalog("all");
  else if (nav === "cart") renderCart();
  else if (nav === "favorites") renderFavorites();
  else if (nav === "profile") renderProfile();
}

/* ─── Filtrlar ─── */
function byId(a, b) { return (b.id || 0) - (a.id || 0); }
function filterProducts(key) {
  let list = ALL.slice();
  switch (key) {
    case "sale": return list.filter(p => p.discount > 0).sort((a, b) => b.discount - a.discount);
    case "new": return list.filter(p => p.new).sort(byId);
    case "cheap": return list.filter(p => p.price <= 100000).sort((a, b) => a.price - b.price);
    case "top": return list.filter(p => p.reviews > 0).sort((a, b) => b.rating - a.rating);
    case "free": return list.filter(p => p.free_delivery);
    case "gift": return list.filter(p => p.price >= CONFIG.free_threshold);
    default: return list;
  }
}
function trending() {
  return ALL.slice().sort((a, b) => (b.discount - a.discount) || (b.rating - a.rating)).slice(0, 10);
}

/* ─── Kartochka HTML ─── */
function stars(p) {
  if (!p.reviews) return "";
  return `<div class="rating"><span class="star">★</span>${p.rating.toFixed(1)} <span style="color:var(--ink-3)">(${p.reviews})</span></div>`;
}
function badge(p) {
  if (p.discount > 0) return `<span class="pbadge disc">-${p.discount}%</span>`;
  if (p.new) return `<span class="pbadge new">Yangi</span>`;
  return "";
}
function productCardHTML(p) {
  const img = p.photo ? `<img src="${esc(p.photo)}" loading="lazy" alt="">` : '<div class="noimg">📦</div>';
  const old = p.old_price && p.old_price > p.price ? `<span class="old">${money(p.old_price)}</span>` : "";
  const free = p.free_delivery ? '<div class="free">🚚 Bepul yetkazish</div>' : "";
  const favOn = FAV.has(p.id) ? " on" : "";
  return `<div class="pcard" data-id="${p.id}">
    <div class="pcard-img" data-open="${p.id}">
      ${img}${badge(p)}
      <button class="fav${favOn}" data-fav="${p.id}" aria-label="Sevimli">${FAV.has(p.id) ? "❤️" : "🤍"}</button>
    </div>
    <div class="pcard-b">
      ${stars(p)}
      <div class="pcard-n" data-open="${p.id}">${esc(p.name)}</div>
      <div class="price-row"><span class="price">${money(p.price)} so'm</span>${old}</div>
      ${free}
      <button class="addbtn" data-add="${p.id}">🛒 Savatga</button>
    </div>
  </div>`;
}
function trendCardHTML(p) {
  const img = p.photo ? `<img src="${esc(p.photo)}" loading="lazy" alt="">` : "";
  return `<div class="tcard" data-open="${p.id}">
    <div class="tcard-img">${img}</div>
    <div class="tcard-b"><div class="tcard-n">${esc(p.name)}</div><div class="tcard-p">${money(p.price)} so'm</div></div>
  </div>`;
}

/* Kartochkalardagi hodisalarni ulash (bir joyda — delegatsiya) */
function wireCards(root) {
  root.querySelectorAll("[data-open]").forEach(el => el.addEventListener("click", () => openDetail(+el.dataset.open)));
  root.querySelectorAll("[data-add]").forEach(el => el.addEventListener("click", e => {
    e.stopPropagation();
    const p = ALL.find(x => x.id === +el.dataset.add); if (p) { addToCart(p); haptic(); toast("Savatga qo'shildi ✓"); }
  }));
  root.querySelectorAll("[data-fav]").forEach(el => el.addEventListener("click", e => {
    e.stopPropagation(); toggleFav(+el.dataset.fav, el);
  }));
}

/* ─── Bosh sahifa ─── */
function maxDiscount() { return ALL.reduce((m, p) => Math.max(m, p.discount || 0), 0); }
function heroSlides() {
  const thr = money(CONFIG.free_threshold);
  const slides = [
    { tag: "🔥 Bugungi takliflar", title: "24 soatda yetkazamiz", sub: "Buyurtmangiz to'lov tasdiqlangach 24 soat ichida qo'lingizda", art: "📦", timer: true, target: "all" },
    { tag: "🎁 Har xaridga sovg'a", title: "Kafolatlangan sovg'a", sub: `${thr} so'mdan yuqori xaridga sovg'a qo'shamiz`, art: "🎁", target: "gift" },
    { tag: "🚚 Bepul yetkazish", title: "Yetkazish bepul", sub: `${thr} so'mdan yuqori xaridlarga yetkazib berish bepul`, art: "🚛", target: "free" },
  ];
  const md = maxDiscount();
  if (md > 0) slides.unshift({ tag: "🔥 Aksiya", title: "Chegirmali mahsulotlar", sub: "Eng foydali narxlarni ko'rib chiqing", disc: md, art: "🧊", timer: true, target: "sale" });
  return slides;
}
let HERO = heroSlides();
let heroIdx = 0;

function heroHTML(i) {
  const s = HERO[i];
  const disc = s.disc ? `<div class="hero-disc">−${s.disc}% gacha</div>` : "";
  const timer = s.timer ? `<div class="hero-timer" id="hero-timer"></div>` : "";
  return `<div class="hero-tag">${esc(s.tag)}</div>
    <div class="hero-title">${esc(s.title)}</div>
    <div class="hero-sub">${esc(s.sub)}</div>
    ${timer}
    <button class="hero-cta" data-hero="${s.target}">Ko'rish →</button>
    ${disc}
    <div class="hero-art">${s.art}</div>`;
}
function timerHTML() {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
  let sec = Math.max(0, Math.floor((end - now) / 1000));
  const h = String(Math.floor(sec / 3600)).padStart(2, "0");
  const m = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  const box = (v, l) => `<div class="tbox"><b>${v}</b><span>${l}</span></div>`;
  return box(h, "soat") + '<span class="tcolon">:</span>' + box(m, "daq") + '<span class="tcolon">:</span>' + box(s, "son");
}

function trustHTML() {
  const item = (bg, ico, t, s) => `<div class="trust-item"><div class="trust-ico" style="background:${bg}">${ico}</div><div><div class="trust-t">${t}</div><div class="trust-s">${s}</div></div></div>`;
  const prod = STATS.products ? `${STATS.products}+` : "100+";
  return item("rgba(37,99,235,.1)", "📦", prod, "mahsulot")
    + item("rgba(22,163,74,.1)", "🚚", "24 soat", "yetkazamiz")
    + item("rgba(245,166,35,.12)", "🛡", "100%", "xavfsiz to'lov");
}

const CATS = [
  { key: "sale", lbl: "Aksiya", ico: "🔥", bg: "rgba(239,68,68,.12)" },
  { key: "new", lbl: "Yangi", ico: "🆕", bg: "rgba(37,99,235,.12)" },
  { key: "gift", lbl: "Sovg'a", ico: "🎁", bg: "rgba(236,72,153,.12)" },
  { key: "free", lbl: "Yetkazish", ico: "🚚", bg: "rgba(22,163,74,.12)" },
  { key: "top", lbl: "Top", ico: "⭐", bg: "rgba(245,166,35,.14)" },
  { key: "all", lbl: "Barchasi", ico: "🗂", bg: "rgba(124,108,207,.14)" },
];
const QCHIPS = [
  { key: "sale", lbl: "🔥 Aksiya" }, { key: "free", lbl: "🚚 Bepul yetkazish" },
  { key: "cheap", lbl: "💰 100 minggacha" }, { key: "top", lbl: "⭐ Eng ko'p sotilgan" },
  { key: "new", lbl: "🆕 Yangi" },
];

async function renderHome() {
  setNav("home");
  returnView = renderHome;
  if (!ALL.length) { await loadData(); }
  HERO = heroSlides(); heroIdx = 0;
  const trend = trending();
  const forYou = ALL.slice(0, 10);
  view.innerHTML = `
    <div class="hero" id="hero">${heroHTML(0)}</div>
    <div class="dots" id="dots"></div>
    <div class="quickchips">${QCHIPS.map(c => `<button class="qchip" data-cat="${c.key}">${esc(c.lbl)}</button>`).join("")}</div>
    <div class="trust">${trustHTML()}</div>
    <div class="cats">${CATS.map(c => `<button class="cat" data-cat="${c.key}"><span class="cat-ico" style="background:${c.bg}">${c.ico}</span><span class="cat-lbl">${esc(c.lbl)}</span></button>`).join("")}</div>
    <div class="section-head"><h2>Bugun trendda 🔥</h2></div>
    <div class="hscroll" id="trend">${trend.map(trendCardHTML).join("")}</div>
    <div class="section-head"><h2>Siz uchun tanladik ✨</h2><a data-cat="all">Barchasini ko'rish →</a></div>
    <div class="grid" id="foryou">${forYou.map(productCardHTML).join("")}</div>
    ${socialHTML()}
    <div class="spacer80"></div>`;

  // Hodisalar
  wireCards(view);
  view.querySelectorAll("[data-cat]").forEach(el => el.addEventListener("click", () => renderCatalog(el.dataset.cat)));
  bindHero();

  // Dots + karusel
  renderDots();
  const rot = setInterval(() => { heroIdx = (heroIdx + 1) % HERO.length; refreshHero(); }, 5000);
  const tick = setInterval(() => { const t = document.getElementById("hero-timer"); if (t) t.innerHTML = timerHTML(); }, 1000);
  homeTimers.push(rot, tick);
  const t0 = document.getElementById("hero-timer"); if (t0) t0.innerHTML = timerHTML();
}
function refreshHero() {
  const h = document.getElementById("hero"); if (!h) return;
  h.innerHTML = heroHTML(heroIdx); bindHero(); renderDots();
  const t = document.getElementById("hero-timer"); if (t) t.innerHTML = timerHTML();
}
function bindHero() {
  const b = document.querySelector("[data-hero]");
  if (b) b.addEventListener("click", () => renderCatalog(b.dataset.hero));
}
function renderDots() {
  const d = document.getElementById("dots"); if (!d) return;
  d.innerHTML = HERO.map((_, i) => `<i class="${i === heroIdx ? "on" : ""}"></i>`).join("");
}
function socialHTML() {
  const parts = [];
  if (STATS.orders_last_hour > 0)
    parts.push(`<div class="social-item"><div class="social-ico">🔥</div><div><div class="social-t">${STATS.orders_last_hour} ta buyurtma</div><div class="social-s">oxirgi 1 soatda</div></div></div>`);
  if (STATS.orders_today > 0)
    parts.push(`<div class="social-item"><div class="social-ico">✅</div><div><div class="social-t">${STATS.orders_today} ta buyurtma</div><div class="social-s">bugun berildi</div></div></div>`);
  if (!parts.length)
    parts.push(`<div class="social-item"><div class="social-ico">🛡</div><div><div class="social-t">Ishonchli do'kon</div><div class="social-s">${STATS.shops || ""} tekshirilgan sotuvchi</div></div></div>`);
  return `<div class="social">${parts.join("")}</div>`;
}

/* ─── Katalog / filtr ─── */
let searchTimer = null;
document.getElementById("search").addEventListener("input", e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => runSearch(e.target.value.trim()), 300);
});
async function runSearch(q) {
  if (!q) { renderHome(); return; }
  setNav("catalog");
  view.innerHTML = '<div class="loading">Qidirilmoqda…</div>';
  let items = [];
  try { items = await api("/api/products?q=" + encodeURIComponent(q)); } catch (e) {}
  ALL = mergeAll(items);
  showGrid(items, `"${q}" bo'yicha natija`, "all");
}

function renderCatalog(key) {
  setNav(key === "all" ? "catalog" : "catalog");
  const items = filterProducts(key || "all");
  const title = ({ sale: "🔥 Aksiya", new: "🆕 Yangi", cheap: "💰 Arzon", top: "⭐ Eng ko'p sotilgan", free: "🚚 Bepul yetkazish", gift: "🎁 Sovg'a mavjud" })[key] || "Barcha mahsulotlar";
  showGrid(items, title, key || "all");
}

function showGrid(items, title, activeKey) {
  returnView = () => showGrid(items, title, activeKey);
  const chips = [{ key: "all", lbl: "Barchasi" }].concat(QCHIPS);
  view.innerHTML = `
    <div class="quickchips" style="margin-top:2px">${chips.map(c => `<button class="qchip${c.key === activeKey ? " on" : ""}" data-cat="${c.key}">${esc(c.lbl)}</button>`).join("")}</div>
    <div class="section-head"><h2>${esc(title)}</h2><a style="color:var(--ink-2)">${items.length} ta</a></div>
    ${items.length ? `<div class="grid">${items.map(productCardHTML).join("")}</div>` : '<div class="empty"><div class="em-ico">🔍</div><div class="em-t">Mahsulot topilmadi</div>Boshqa filtr yoki so\'z bilan urinib ko\'ring.</div>'}
    <div class="spacer80"></div>`;
  wireCards(view);
  view.querySelectorAll("[data-cat]").forEach(el => el.addEventListener("click", () => renderCatalog(el.dataset.cat)));
}

/* ─── Sevimli ─── */
async function toggleFav(id, btn) {
  const now = !FAV.has(id);
  if (now) FAV.add(id); else FAV.delete(id);
  saveFav();
  if (btn) { btn.textContent = now ? "❤️" : "🤍"; btn.classList.toggle("on", now); }
  haptic();
  toast(now ? "Sevimlilarga qo'shildi ❤️" : "Sevimlilardan olindi");
  if (tg && tg.initData) {
    try { await api("/api/favorite", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ initData: tg.initData, product_id: id }) }); } catch (e) {}
  }
}
function renderFavorites() {
  setNav("favorites");
  returnView = renderFavorites;
  const items = ALL.filter(p => FAV.has(p.id));
  view.innerHTML = `
    <div class="section-head" style="margin-top:6px"><h2>❤️ Sevimlilar</h2><a style="color:var(--ink-2)">${items.length} ta</a></div>
    ${items.length ? `<div class="grid">${items.map(productCardHTML).join("")}</div>` : '<div class="empty"><div class="em-ico">🤍</div><div class="em-t">Sevimlilar bo\'sh</div>Yoqqan mahsulotlarni yurakcha bilan saqlang.</div>'}
    <div class="spacer80"></div>`;
  wireCards(view);
}

/* ─── Mahsulot detali ─── */
let detailViews = 0;
async function openDetail(id) {
  clearHomeTimers();
  window.scrollTo(0, 0);
  view.innerHTML = '<div class="loading">Yuklanmoqda…</div>';
  let p;
  try { p = await api("/api/product/" + id); } catch (e) {
    view.innerHTML = '<div class="empty"><div class="em-ico">⚠️</div><div class="em-t">Mahsulot topilmadi</div></div>'; return;
  }
  const imgs = (p.photos && p.photos.length) ? p.photos.map(u => `<img src="${esc(u)}" alt="">`).join("") : '<div class="noimg">📦</div>';
  const old = p.old_price && p.old_price > p.price ? `<span class="detail-old">${money(p.old_price)}</span>` : "";
  const rate = p.reviews ? `<span><span style="color:var(--amber)">★</span> ${p.rating.toFixed(1)} (${p.reviews} sharh)</span>` : "";
  const favOn = FAV.has(p.id);
  view.innerHTML = `
    ${tg && tg.BackButton ? "" : '<button class="back-link" id="back">← Orqaga</button>'}
    <div class="detail-imgs">${imgs}</div>
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px">
      <div class="detail-name">${esc(p.name)}</div>
      <button class="fav${favOn ? " on" : ""}" style="position:static;flex:0 0 auto" data-fav="${p.id}">${favOn ? "❤️" : "🤍"}</button>
    </div>
    <div class="detail-meta">${rate}${p.shop_name ? `<span>🏪 ${esc(p.shop_name)}</span>` : ""}${p.city ? `<span>📍 ${esc(p.city)}</span>` : ""}</div>
    <div><span class="detail-price">${money(p.price)} so'm</span>${old}${p.discount ? ` <span class="pbadge disc" style="position:static;display:inline-block">-${p.discount}%</span>` : ""}</div>
    <div class="card-box">
      <div class="row"><span>🚚 Yetkazib berish</span><b>${p.free_delivery ? "Bepul" : money(CONFIG.delivery_fee) + " so'm"}</b></div>
      <div class="row"><span>💳 Oldindan to'lov</span><b>${CONFIG.prepay_percent}%</b></div>
      <div class="row"><span>🛡 Kafolat</span><b>${p.warranty ? esc(p.warranty) : "Mavjud"}</b></div>
    </div>
    ${p.description ? `<div class="detail-desc">${esc(p.description)}</div>` : ""}
    <button class="btn btn-primary" id="add" style="margin-top:16px" ${p.available ? "" : "disabled"}>${p.available ? "🛒 Savatga qo'shish" : "Hozircha tugagan"}</button>
    <div class="spacer80"></div>`;
  if (tg && tg.BackButton) {
    showBack(goBack);               // Telegram/telefon tabiiy "orqaga" tugmasi
  } else {
    document.getElementById("back").addEventListener("click", goBack);
  }
  view.querySelector("[data-fav]").addEventListener("click", e => toggleFav(p.id, e.currentTarget));
  if (p.available) document.getElementById("add").addEventListener("click", () => { addToCart(p); haptic(); toast("Savatga qo'shildi ✓"); });

  detailViews++;
  if (detailViews >= 3) maybePromptA2HS();
}
function goBack() { (returnView || renderHome)(); }

function addToCart(p) {
  const ex = CART.find(i => i.id === p.id);
  if (ex) ex.qty++;
  else CART.push({ id: p.id, name: p.name, price: p.price, photo: (p.photos && p.photos[0]) || p.photo || null, qty: 1 });
  saveCart();
}

/* ─── Savat ─── */
function renderCart() {
  setNav("cart");
  if (!CART.length) {
    view.innerHTML = '<div class="empty"><div class="em-ico">🛒</div><div class="em-t">Savat bo\'sh</div>Katalogdan mahsulot tanlang.<br><br><button class="btn btn-primary" style="max-width:220px;margin:0 auto" id="toshop">Xaridni boshlash</button></div>';
    const b = document.getElementById("toshop"); b && b.addEventListener("click", renderHome); return;
  }
  const items = CART.map((i, idx) => `
    <div class="citem">
      ${i.photo ? `<img src="${esc(i.photo)}" alt="">` : '<img alt="">'}
      <div class="citem-b">
        <div class="citem-n">${esc(i.name)}</div>
        <div class="citem-p">${money(i.price)} so'm</div>
        <div class="qty"><button data-act="dec" data-i="${idx}">−</button><span>${i.qty}</span><button data-act="inc" data-i="${idx}">+</button></div>
      </div>
      <button class="citem-x" data-act="del" data-i="${idx}">✕</button>
    </div>`).join("");
  const total = cartTotal();
  const fee = total >= CONFIG.free_threshold ? 0 : CONFIG.delivery_fee;
  const prepay = Math.round(total * CONFIG.prepay_percent / 100);
  view.innerHTML = `
    <div class="section-head" style="margin-top:6px"><h2>🛒 Savat</h2><a style="color:var(--ink-2)">${cartCount()} ta</a></div>
    ${items}
    <div class="summary">
      <div class="row"><span>Mahsulotlar</span><span>${money(total)} so'm</span></div>
      <div class="row"><span>Yetkazib berish</span><span>${fee ? money(fee) + " so'm" : "Bepul"}</span></div>
      <div class="row total"><span>Jami</span><span>${money(total + fee)} so'm</span></div>
      <div class="row"><span>Oldindan to'lov (${CONFIG.prepay_percent}%)</span><span>${money(prepay)} so'm</span></div>
    </div>
    <button class="btn btn-primary" id="checkout">Buyurtma berish</button>
    <div class="spacer80"></div>`;
  view.querySelectorAll("[data-act]").forEach(b => b.addEventListener("click", () => {
    const idx = +b.dataset.i, act = b.dataset.act;
    if (act === "inc") CART[idx].qty++;
    else if (act === "dec") { CART[idx].qty--; if (CART[idx].qty < 1) CART.splice(idx, 1); }
    else CART.splice(idx, 1);
    saveCart(); renderCart();
  }));
  document.getElementById("checkout").addEventListener("click", renderCheckout);
}

/* ─── Checkout ─── */
let receiptFile = null;
function renderCheckout() {
  clearHomeTimers(); window.scrollTo(0, 0); receiptFile = null;
  const total = cartTotal();
  const fee = total >= CONFIG.free_threshold ? 0 : CONFIG.delivery_fee;
  const prepay = Math.round(total * CONFIG.prepay_percent / 100);
  const multi = CART.length > 1;
  view.innerHTML = `
    <button class="back-link" id="back">← Savat</button>
    <div class="section-head" style="margin-top:0"><h2>Buyurtmani rasmiylashtirish</h2></div>
    ${multi ? '<div class="card-box" style="margin-top:0">ℹ️ Har bir mahsulot alohida buyurtma sifatida rasmiylashtiriladi.</div>' : ""}
    <div class="field"><label>Manzil (shahar, ko'cha, uy)</label><textarea id="f-address" placeholder="Toshkent, Chilonzor 12-kvartal, 5-uy"></textarea></div>
    <div class="field"><label>Telefon raqamingiz</label><input id="f-phone" type="tel" inputmode="tel" placeholder="+998 90 123 45 67"></div>
    <div class="summary">
      <div class="row total"><span>Jami</span><span>${money(total + fee)} so'm</span></div>
      <div class="row"><span>Oldindan to'lov (${CONFIG.prepay_percent}%)</span><span>${money(prepay)} so'm</span></div>
    </div>
    <div class="card-copy"><span>Karta: <code id="cardno">${esc(CONFIG.card || "—")}</code>${CONFIG.card_name ? " <span style='color:var(--ink-2);font-size:12px'>(" + esc(CONFIG.card_name) + ")</span>" : ""}</span><button class="btn-ghost" style="width:auto;padding:7px 14px;font-size:13px;border-radius:10px" id="copycard">Nusxa</button></div>
    <div class="field"><label>To'lov chekini yuklang (rasm yoki PDF)</label>
      <label class="file-box" id="filebox" for="f-receipt">📎 Chek faylini tanlang</label>
      <input id="f-receipt" type="file" accept="image/*,application/pdf" hidden></div>
    <button class="btn btn-primary" id="submit">Buyurtmani tasdiqlash</button>
    <div class="spacer80"></div>`;
  document.getElementById("back").addEventListener("click", renderCart);
  document.getElementById("copycard").addEventListener("click", () => { if (CONFIG.card) { navigator.clipboard && navigator.clipboard.writeText(CONFIG.card); toast("Karta nusxalandi"); } });
  const fi = document.getElementById("f-receipt");
  fi.addEventListener("change", () => {
    receiptFile = fi.files[0] || null;
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
  let lastId = null;
  try {
    for (const item of CART) {
      const fd = new FormData();
      fd.append("initData", tg.initData);
      fd.append("payload", JSON.stringify({ product_id: item.id, quantity: item.qty, address, phone, delivery: "taxi" }));
      fd.append("receipt", receiptFile, receiptFile.name);
      const r = await api("/api/order", { method: "POST", body: fd });
      lastId = r.order_id;
    }
  } catch (e) {
    btn.disabled = false; btn.textContent = "Buyurtmani tasdiqlash";
    return toast("Xatolik. Qayta urinib ko'ring.");
  }
  CART = []; saveCart(); haptic("medium"); showSuccess(lastId);
}

function showSuccess(orderId) {
  window.scrollTo(0, 0);
  view.innerHTML = `<div class="empty">
    <div class="em-ico">🎉</div>
    <div class="em-t">Buyurtma qabul qilindi</div>
    <div>Raqam: <b>#${esc(orderId)}</b></div>
    <div style="margin-top:10px">Chek tekshirilgach operator siz bilan bog'lanadi.</div>
    ${CONFIG.contact_phone ? `<div style="margin-top:6px">📞 ${esc(CONFIG.contact_phone)}</div>` : ""}
    <button class="btn btn-primary" style="margin-top:24px;max-width:240px;margin-left:auto;margin-right:auto" id="back-shop">Xaridni davom ettirish</button>
  </div>`;
  document.getElementById("back-shop").addEventListener("click", renderHome);
}

/* ─── Profil ─── */
function renderProfile() {
  setNav("profile");
  const u = (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) || {};
  const name = [u.first_name, u.last_name].filter(Boolean).join(" ") || "Foydalanuvchi";
  const initials = (name[0] || "P").toUpperCase();
  view.innerHTML = `
    <div class="card-box" style="margin-top:6px;display:flex;align-items:center;gap:14px">
      <div style="width:54px;height:54px;border-radius:16px;background:var(--brand);color:#fff;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800">${esc(initials)}</div>
      <div><div style="font-size:17px;font-weight:800">${esc(name)}</div>${u.username ? `<div style="color:var(--ink-2);font-size:13px">@${esc(u.username)}</div>` : ""}</div>
    </div>
    <div class="card-box">
      <div class="row"><span>❤️ Sevimlilar</span><b>${FAV.size} ta</b></div>
      <div class="row"><span>🛒 Savatda</span><b>${cartCount()} ta</b></div>
      <div class="row"><span>💳 Oldindan to'lov</span><b>${CONFIG.prepay_percent}%</b></div>
      <div class="row"><span>🚚 Bepul yetkazish</span><b>${money(CONFIG.free_threshold)}+</b></div>
      ${CONFIG.contact_phone ? `<div class="row"><span>📞 Aloqa</span><b>${esc(CONFIG.contact_phone)}</b></div>` : ""}
    </div>
    ${ME.is_seller ? '<button class="btn btn-ghost" id="p-seller" style="margin-top:4px">🏪 Sotuvchi paneli</button>' : ""}
    ${ME.is_admin ? '<button class="btn btn-ghost" id="p-admin" style="margin-top:4px">🛠 Admin panel</button>' : ""}
    <button class="btn btn-primary" id="a2hs-open" style="margin-top:4px">📲 Ilovani ekranga o'rnatish</button>
    <div class="spacer80"></div>`;
  const a = document.getElementById("a2hs-open"); a && a.addEventListener("click", () => showA2HS(true));
  const ps = document.getElementById("p-seller");
  if (ps) ps.addEventListener("click", () => { if (typeof renderSellerPanel === "function") renderSellerPanel(); });
  const pa = document.getElementById("p-admin");
  if (pa) pa.addEventListener("click", () => { if (typeof renderAdminPanel === "function") renderAdminPanel(); });
}

/* ─── Ekranga o'rnatish ─── */
function maybePromptA2HS() {
  if (!tg || localStorage.getItem("a2hs_done")) return;
  if (typeof tg.checkHomeScreenStatus === "function") {
    try {
      tg.checkHomeScreenStatus(status => {
        if (status === "added" || status === "unsupported") { localStorage.setItem("a2hs_done", "1"); return; }
        showA2HS(false);
      });
    } catch (e) {}
  }
}
function showA2HS(force) {
  if (!tg) { if (force) toast("Ilovani Telegram orqali oching"); return; }
  if (typeof tg.addToHomeScreen !== "function") { if (force) toast("Telegram ilovangizni yangilang"); return; }
  document.getElementById("a2hs").hidden = false;
}
document.getElementById("a2hs-add").addEventListener("click", () => {
  try { tg && tg.addToHomeScreen && tg.addToHomeScreen(); } catch (e) {}
  localStorage.setItem("a2hs_done", "1"); document.getElementById("a2hs").hidden = true;
});
document.getElementById("a2hs-later").addEventListener("click", () => {
  localStorage.setItem("a2hs_done", "1"); document.getElementById("a2hs").hidden = true;
});
if (tg && tg.onEvent) tg.onEvent("homeScreenAdded", () => localStorage.setItem("a2hs_done", "1"));

/* ─── Ma'lumot yuklash ─── */
function mergeAll(items) {
  // qidiruv natijasidagi yangi mahsulotlarni ALL bilan birlashtiradi (kartochka topilishi uchun)
  const map = new Map(ALL.map(p => [p.id, p]));
  items.forEach(p => map.set(p.id, p));
  return [...map.values()];
}
async function loadData() {
  const [cfg, stats, products] = await Promise.allSettled([api("/api/config"), api("/api/stats"), api("/api/products")]);
  if (cfg.status === "fulfilled") CONFIG = Object.assign(CONFIG, cfg.value);
  if (stats.status === "fulfilled") STATS = Object.assign(STATS, stats.value);
  if (products.status === "fulfilled") ALL = products.value;
  // sevimlilarni serverdan (agar Telegram ichida) — real bot favoritlari
  if (tg && tg.initData) {
    try {
      const f = await api("/api/favorites", { headers: { "X-Telegram-Init-Data": tg.initData } });
      if (f && Array.isArray(f.ids)) { FAV = new Set([...FAV, ...f.ids.map(Number)]); saveFav(); }
    } catch (e) {}
    // rollar (admin/seller panel tugmalari uchun)
    try {
      const me = await api("/api/me", { headers: { "X-Telegram-Init-Data": tg.initData } });
      if (me) ME = Object.assign(ME, me);
    } catch (e) {}
  }
}

/* ─── Boshlash ─── */
(async function init() {
  updateBadges();
  try {
    if (tg && tg.themeParams && tg.colorScheme === "dark") document.documentElement.style.setProperty("--brand", tg.themeParams.button_color || "#2563eb");
  } catch (e) {}
  await loadData();
  renderHome();
})();
