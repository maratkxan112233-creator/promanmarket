"use strict";
/* ─── ADMIN va SELLER panellari ───
   app.js dan keyin yuklanadi; uning global yordamchilaridan foydalanadi:
   tg, api, view, esc, money, toast, haptic, showBack, clearHomeTimers,
   renderProfile. Rollar /api/me orqali aniqlanadi (app.js dagi ME). */

const OSTAT = {
  pending: "⏳ Kutilmoqda", paid: "💳 To'lov qilindi",
  processing: "🔄 Tayyorlanmoqda", shipped: "🚚 Yo'lda",
  delivered: "✅ Yetkazildi", cancelled: "❌ Bekor qilindi",
};

/* ─── Yordamchilar ─── */
function _pAuthOk() {
  if (!tg || !tg.initData) { toast("Ilovani Telegram orqali oching"); return false; }
  return true;
}
function _aget(path) { return api(path, { headers: { "X-Telegram-Init-Data": tg.initData } }); }
function _jpost(path, data) {
  return api(path, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(Object.assign({ initData: tg.initData }, data || {})),
  });
}
function _val(id) { const e = document.getElementById(id); return e ? e.value.trim() : ""; }
function _showable(url) { return !!url && (url.indexOf("http") === 0 || url[0] === "/"); }
function _thumb(url) {
  return _showable(url) ? `<img src="${esc(url)}" alt="">` : '<div class="pthumb-ph">📦</div>';
}

/* Panel ekranini chizadi + "orqaga" tugmasini backFn ga ulaydi. */
function _panel(inner, backFn) {
  clearHomeTimers();
  window.scrollTo(0, 0);
  view.innerHTML = inner;
  const b = document.getElementById("pback");
  if (b) b.addEventListener("click", backFn);
  document.querySelectorAll(".nav-item").forEach(x => x.classList.remove("active"));
  if (tg && tg.BackButton) showBack(backFn);
}

function _head(title) {
  return `<button class="back-link" id="pback">← Orqaga</button>
    <div class="section-head" style="margin-top:0"><h2>${esc(title)}</h2></div>`;
}

/* ══════════════════ ADMIN — Mahsulotlar ══════════════════ */
async function renderAdminPanel() {
  if (!_pAuthOk()) return renderProfile();
  _panel(_head("🛠 Admin — Mahsulotlar") +
    '<button class="btn btn-primary" id="p-add" style="margin-bottom:12px">➕ Yangi mahsulot</button>' +
    '<div id="p-list"><div class="loading">Yuklanmoqda…</div></div><div class="spacer80"></div>',
    renderProfile);
  document.getElementById("p-add").addEventListener("click", () => renderProductForm({ mode: "admin", product: null }));
  let items = [];
  try { items = await _aget("/api/admin/products"); } catch (e) { }
  _fillProductList(items, "admin");
}

/* ══════════════════ SELLER — asosiy menyu ══════════════════ */
async function renderSellerPanel() {
  if (!_pAuthOk()) return renderProfile();
  const shopName = (ME.shop && ME.shop.shop_name) || "Do'koningiz";
  _panel(_head("🏪 " + shopName) +
    `<div class="panel-tabs">
       <button class="panel-tab" data-t="products"><span>📦</span>Mahsulotlar</button>
       <button class="panel-tab" data-t="orders"><span>🧾</span>Buyurtmalar</button>
       <button class="panel-tab" data-t="shop"><span>🏪</span>Do'kon</button>
       <button class="panel-tab" data-t="stats"><span>📊</span>Statistika</button>
     </div><div class="spacer80"></div>`,
    renderProfile);
  view.querySelectorAll(".panel-tab").forEach(b => b.addEventListener("click", () => {
    const t = b.dataset.t;
    if (t === "products") renderSellerProducts();
    else if (t === "orders") renderSellerOrders();
    else if (t === "shop") renderSellerShop();
    else if (t === "stats") renderSellerStats();
  }));
}

/* ─── SELLER — mahsulotlar ─── */
async function renderSellerProducts() {
  _panel(_head("📦 Mahsulotlarim") +
    '<button class="btn btn-primary" id="p-add" style="margin-bottom:12px">➕ Yangi mahsulot</button>' +
    '<div id="p-list"><div class="loading">Yuklanmoqda…</div></div><div class="spacer80"></div>',
    renderSellerPanel);
  document.getElementById("p-add").addEventListener("click", () => renderProductForm({ mode: "seller", product: null }));
  let items = [];
  try { items = await _aget("/api/seller/products"); } catch (e) { }
  _fillProductList(items, "seller");
}

/* Mahsulotlar ro'yxatini chizadi (admin/seller uchun bir xil). */
function _fillProductList(items, mode) {
  const box = document.getElementById("p-list");
  if (!box) return;
  if (!items.length) {
    box.innerHTML = '<div class="empty"><div class="em-ico">📦</div><div class="em-t">Mahsulot yo\'q</div>Yangi mahsulot qo\'shing.</div>';
    return;
  }
  box.innerHTML = items.map(p => {
    const photos = p.photos || [];
    const stock = p.stock === null || p.stock === undefined ? "∞" : p.stock;
    const av = p.available ? '<span class="pill ok">Sotuvda</span>' : '<span class="pill off">Tugagan</span>';
    return `<div class="prow">
      <div class="pthumb">${_thumb(photos[0])}</div>
      <div class="prow-b">
        <div class="prow-n">${esc(p.name)}</div>
        <div class="prow-m">${money(p.price)} so'm · zaxira: ${esc(String(stock))} ${av}</div>
        ${mode === "admin" ? `<div class="prow-shop">🏪 ${esc(p.shop_name || "")}</div>` : ""}
      </div>
      <div class="prow-actions">
        <button class="iconbtn" data-edit="${p.id}">✏️</button>
        <button class="iconbtn" data-del="${p.id}">🗑</button>
      </div>
    </div>`;
  }).join("");
  const map = new Map(items.map(p => [p.id, p]));
  box.querySelectorAll("[data-edit]").forEach(b => b.addEventListener("click", () =>
    renderProductForm({ mode, product: map.get(+b.dataset.edit) })));
  box.querySelectorAll("[data-del]").forEach(b => b.addEventListener("click", () =>
    _deleteProduct(+b.dataset.del, mode)));
}

async function _deleteProduct(id, mode) {
  if (!confirm("Mahsulot o'chirilsinmi?")) return;
  const url = mode === "admin"
    ? `/api/admin/product/${id}/delete` : `/api/seller/product/${id}/delete`;
  try {
    const r = await _jpost(url, {});
    if (r && r.ok) { haptic(); toast("O'chirildi"); }
    else return toast("O'chirib bo'lmadi");
  } catch (e) { return toast("Xatolik"); }
  mode === "admin" ? renderAdminPanel() : renderSellerProducts();
}

/* ─── Mahsulot formasi (qo'shish/tahrirlash) ─── */
let _keepPhotos = [];
let _adminSellers = [];
async function renderProductForm(opts) {
  const p = opts.product;
  const isNew = !p;
  _keepPhotos = p ? (p.photos || []).slice() : [];
  const back = opts.mode === "admin" ? renderAdminPanel : renderSellerProducts;

  // Admin yangi mahsulot qo'shsa — do'kon tanlash ro'yxati kerak
  let sellerSelect = "";
  if (opts.mode === "admin") {
    if (isNew) {
      try { _adminSellers = await _aget("/api/admin/sellers"); } catch (e) { _adminSellers = []; }
      sellerSelect = `<div class="field"><label>Do'kon</label>
        <select id="pf-seller" class="pf-select">${_adminSellers.map(s =>
          `<option value="${s.id}">${esc(s.shop_name)}${s.city ? " — " + esc(s.city) : ""}</option>`).join("")}</select></div>`;
    } else {
      sellerSelect = `<div class="field"><label>Do'kon</label>
        <input value="${esc(p.shop_name || "")}" disabled></div>`;
    }
  }

  _panel(_head(isNew ? "➕ Yangi mahsulot" : "✏️ Tahrirlash") +
    sellerSelect +
    `<div class="field"><label>Nomi *</label><input id="pf-name" value="${p ? esc(p.name) : ""}" placeholder="Mahsulot nomi"></div>
     <div class="field"><label>Narxi (so'm) *</label><input id="pf-price" type="number" inputmode="numeric" value="${p ? esc(String(p.price)) : ""}" placeholder="199000"></div>
     <div class="field"><label>Eski narx (chegirma uchun, ixtiyoriy)</label><input id="pf-old" type="number" inputmode="numeric" value="${p && p.old_price ? esc(String(p.old_price)) : ""}" placeholder="0"></div>
     <div class="field"><label>Zaxira (bo'sh = cheksiz)</label><input id="pf-stock" type="number" inputmode="numeric" value="${p && p.stock !== null && p.stock !== undefined ? esc(String(p.stock)) : ""}" placeholder="∞"></div>
     <div class="field"><label>Ranglar (vergul bilan)</label><input id="pf-colors" value="${p && p.colors ? esc(p.colors.join(", ")) : ""}" placeholder="Qora, Oq, Ko'k"></div>
     <div class="field"><label>Tavsif</label><textarea id="pf-desc" placeholder="Mahsulot haqida">${p ? esc(p.description || "") : ""}</textarea></div>
     <div class="field"><label>Rasmlar</label>
       <div id="pf-chips" class="photo-chips"></div>
       <label class="file-box" for="pf-images" style="margin-top:8px">📷 Rasm(lar) tanlash</label>
       <input id="pf-images" type="file" accept="image/*" multiple hidden>
       <div id="pf-imgcount" style="font-size:12px;color:var(--ink-2);margin-top:6px"></div>
     </div>
     <button class="btn btn-primary" id="pf-save">${isNew ? "Qo'shish" : "Saqlash"}</button>
     <div class="spacer80"></div>`,
    back);

  _renderChips();
  const fi = document.getElementById("pf-images");
  fi.addEventListener("change", () => {
    const n = fi.files ? fi.files.length : 0;
    document.getElementById("pf-imgcount").textContent = n ? `${n} ta yangi rasm tanlandi` : "";
  });
  document.getElementById("pf-save").addEventListener("click", () => _saveProduct(opts));
}

function _renderChips() {
  const box = document.getElementById("pf-chips");
  if (!box) return;
  box.innerHTML = _keepPhotos.map((u, i) =>
    _showable(u)
      ? `<div class="pchip"><img src="${esc(u)}" alt=""><button data-rm="${i}">✕</button></div>`
      : `<div class="pchip"><div class="pchip-ph">📦</div><button data-rm="${i}">✕</button></div>`
  ).join("");
  box.querySelectorAll("[data-rm]").forEach(b => b.addEventListener("click", () => {
    _keepPhotos.splice(+b.dataset.rm, 1); _renderChips();
  }));
}

async function _saveProduct(opts) {
  const name = _val("pf-name");
  const price = _val("pf-price");
  if (!name) return toast("Nomini kiriting");
  if (!price || +price <= 0) return toast("Narxini kiriting");
  const stockRaw = _val("pf-stock");
  const payload = {
    name,
    price: +price,
    old_price: _val("pf-old") ? +_val("pf-old") : 0,
    stock: stockRaw === "" ? null : +stockRaw,
    colors: _val("pf-colors"),
    description: _val("pf-desc"),
    keep_photos: _keepPhotos,
  };
  if (opts.mode === "admin" && !opts.product) {
    const sid = _val("pf-seller");
    if (!sid) return toast("Do'kon tanlang");
    payload.seller_id = +sid;
  }
  const base = opts.mode === "admin" ? "/api/admin" : "/api/seller";
  const url = opts.product ? `${base}/product/${opts.product.id}` : `${base}/product`;
  const fd = new FormData();
  fd.append("initData", tg.initData);
  fd.append("payload", JSON.stringify(payload));
  const fi = document.getElementById("pf-images");
  if (fi && fi.files) for (const f of fi.files) fd.append("image", f, f.name);
  const btn = document.getElementById("pf-save");
  btn.disabled = true; btn.textContent = "Saqlanmoqda…";
  try {
    const r = await api(url, { method: "POST", body: fd });
    if (!r || !r.ok) throw new Error("fail");
  } catch (e) {
    btn.disabled = false; btn.textContent = opts.product ? "Saqlash" : "Qo'shish";
    return toast("Saqlab bo'lmadi. Qayta urinib ko'ring.");
  }
  haptic("medium"); toast("Saqlandi ✓");
  opts.mode === "admin" ? renderAdminPanel() : renderSellerProducts();
}

/* ─── SELLER — buyurtmalar ─── */
async function renderSellerOrders() {
  _panel(_head("🧾 Buyurtmalar") +
    '<div id="p-orders"><div class="loading">Yuklanmoqda…</div></div><div class="spacer80"></div>',
    renderSellerPanel);
  let items = [];
  try { items = await _aget("/api/seller/orders"); } catch (e) { }
  const box = document.getElementById("p-orders");
  if (!box) return;
  if (!items.length) {
    box.innerHTML = '<div class="empty"><div class="em-ico">🧾</div><div class="em-t">Buyurtma yo\'q</div></div>';
    return;
  }
  box.innerHTML = items.map(o => {
    const acts = [
      ["processing", "🔄 Tayyorlash"], ["shipped", "🚚 Kurierga berdim"],
      ["delivered", "✅ Yetkazildi"], ["cancelled", "❌ Bekor"],
    ].filter(([s]) => s !== o.status)
      .map(([s, l]) => `<button class="ostat-b" data-oid="${o.id}" data-st="${s}">${l}</button>`).join("");
    return `<div class="card-box" style="margin:0 0 12px">
      <div class="orow"><b>#${o.id}</b><span class="pill ${o.status === 'cancelled' ? 'off' : 'ok'}">${esc(OSTAT[o.status] || o.status)}</span></div>
      <div class="prow-n" style="margin-top:4px">${esc(o.product_name)} × ${o.quantity}</div>
      <div class="prow-m">${money(o.total)} so'm${o.color ? " · " + esc(o.color) : ""}</div>
      <div class="prow-m">👤 ${esc(o.buyer_name || "—")} · 📞 ${esc(o.phone || "—")}</div>
      ${o.address ? `<div class="prow-m">📍 ${esc(o.address)}</div>` : ""}
      <div class="status-row">${acts}</div>
    </div>`;
  }).join("");
  box.querySelectorAll(".ostat-b").forEach(b => b.addEventListener("click", () =>
    _setOrderStatus(+b.dataset.oid, b.dataset.st)));
}

async function _setOrderStatus(oid, status) {
  try {
    const r = await _jpost(`/api/seller/order/${oid}/status`, { status });
    if (!r || !r.ok) return toast("O'zgartirib bo'lmadi");
  } catch (e) { return toast("Xatolik"); }
  haptic(); toast("Holat yangilandi ✓"); renderSellerOrders();
}

/* ─── SELLER — do'kon ma'lumotlari ─── */
async function renderSellerShop() {
  _panel(_head("🏪 Do'kon ma'lumotlari") +
    '<div id="p-shop"><div class="loading">Yuklanmoqda…</div></div><div class="spacer80"></div>',
    renderSellerPanel);
  let s = {};
  try { s = await _aget("/api/seller/shop"); } catch (e) { }
  const box = document.getElementById("p-shop");
  if (!box) return;
  const ro = s.is_owner === false;   // yordamchi bo'lsa — tahrirlay olmaydi
  box.innerHTML = `
    <div class="field"><label>Do'kon nomi</label><input id="sf-name" value="${esc(s.shop_name || "")}" ${ro ? "disabled" : ""}></div>
    <div class="field"><label>Telefon</label><input id="sf-phone" value="${esc(s.phone || "")}" ${ro ? "disabled" : ""}></div>
    <div class="field"><label>Karta raqami</label><input id="sf-card" value="${esc(s.card_number || "")}" ${ro ? "disabled" : ""}></div>
    <div class="field"><label>Shahar</label><input id="sf-city" value="${esc(s.city || "")}" ${ro ? "disabled" : ""}></div>
    ${ro ? '<div class="card-box">Faqat do\'kon egasi tahrirlay oladi.</div>'
         : '<button class="btn btn-primary" id="sf-save">Saqlash</button>'}`;
  const btn = document.getElementById("sf-save");
  if (btn) btn.addEventListener("click", async () => {
    const name = _val("sf-name");
    if (!name) return toast("Do'kon nomini kiriting");
    btn.disabled = true; btn.textContent = "Saqlanmoqda…";
    try {
      const r = await _jpost("/api/seller/shop", {
        shop_name: name, phone: _val("sf-phone"),
        card_number: _val("sf-card"), city: _val("sf-city"),
      });
      if (!r || !r.ok) throw new Error();
    } catch (e) {
      btn.disabled = false; btn.textContent = "Saqlash";
      return toast("Saqlab bo'lmadi");
    }
    haptic("medium"); toast("Saqlandi ✓");
    if (ME.shop) ME.shop.shop_name = name;
  });
}

/* ─── SELLER — statistika ─── */
async function renderSellerStats() {
  _panel(_head("📊 Statistika") +
    '<div id="p-stats"><div class="loading">Yuklanmoqda…</div></div><div class="spacer80"></div>',
    renderSellerPanel);
  let s = {};
  try { s = await _aget("/api/seller/stats"); } catch (e) { }
  const box = document.getElementById("p-stats");
  if (!box) return;
  const bs = s.by_status || {};
  const card = (ico, val, lbl) => `<div class="statcard"><div class="stat-ico">${ico}</div><div class="stat-v">${esc(String(val))}</div><div class="stat-l">${esc(lbl)}</div></div>`;
  box.innerHTML = `
    <div class="statgrid">
      ${card("📦", s.products || 0, "Mahsulot")}
      ${card("✅", s.active_products || 0, "Sotuvda")}
      ${card("🧾", s.orders_total || 0, "Buyurtma")}
      ${card("💰", money(s.revenue || 0), "Daromad, so'm")}
    </div>
    <div class="card-box">
      <div class="row"><span>⏳ Kutilmoqda</span><b>${bs.pending || 0}</b></div>
      <div class="row"><span>💳 To'lov qilindi</span><b>${bs.paid || 0}</b></div>
      <div class="row"><span>🔄 Tayyorlanmoqda</span><b>${bs.processing || 0}</b></div>
      <div class="row"><span>🚚 Yo'lda</span><b>${bs.shipped || 0}</b></div>
      <div class="row"><span>✅ Yetkazildi</span><b>${bs.delivered || 0}</b></div>
      <div class="row"><span>❌ Bekor qilindi</span><b>${bs.cancelled || 0}</b></div>
    </div>`;
}
