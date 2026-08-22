import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const API = "/tsc_prompt";
const EMPTY_FAV = "-";
const EMPTY_MARKERS = new Set([EMPTY_FAV, "（暂无收藏）", "(暂无收藏)", ""]);

async function getJson(path) {
  const res = await api.fetchApi(path);
  return await res.json();
}

async function postJson(path, body) {
  const res = await api.fetchApi(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  return await res.json();
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "className") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v !== undefined && v !== null) node.setAttribute(k, v);
  }
  for (const child of [].concat(children)) {
    if (child == null) continue;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

function injectStyles() {
  if (document.getElementById("tsc-prompt-panel-css")) return;
  const css = document.createElement("style");
  css.id = "tsc-prompt-panel-css";
  css.textContent = `
#tsc-prompt-fab {
  position: fixed; right: 18px; bottom: 88px; z-index: 9998;
  width: 48px; height: 48px; border-radius: 50%;
  background: #2d89ef; color: #fff; border: none; cursor: pointer;
  box-shadow: 0 4px 14px rgba(0,0,0,.28); font-size: 20px; font-weight: 700;
}
#tsc-prompt-fab:hover { background: #1b6fd4; }
#tsc-prompt-panel {
  position: fixed; right: 18px; bottom: 148px; z-index: 9999;
  width: 420px; max-height: min(86vh, 920px);
  background: #f7f7f7; color: #222; border: 1px solid #cfcfcf;
  border-radius: 10px; box-shadow: 0 10px 34px rgba(0,0,0,.28);
  display: none; flex-direction: column; overflow: hidden;
  font-family: "Microsoft YaHei", "Segoe UI", sans-serif; font-size: 13px;
}
#tsc-prompt-panel.open { display: flex; }
#tsc-prompt-panel .tsc-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; background: #fff; border-bottom: 1px solid #e2e2e2;
}
#tsc-prompt-panel .tsc-head h3 { margin: 0; font-size: 15px; }
#tsc-prompt-panel .tsc-body {
  padding: 10px 12px 12px; overflow: auto; display: flex; flex-direction: column; gap: 8px;
}
#tsc-prompt-panel .tsc-tip { color: #666; font-size: 12px; line-height: 1.45; }
#tsc-prompt-panel label { font-weight: 600; display: block; margin-bottom: 3px; }
#tsc-prompt-panel .tsc-row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
#tsc-prompt-panel .tsc-row > * { flex: 0 0 auto; }
#tsc-prompt-panel .tsc-row select, #tsc-prompt-panel .tsc-row input[type=text] { flex: 1 1 auto; }
#tsc-prompt-panel .tsc-gen-row { flex-wrap: nowrap; }
#tsc-prompt-panel .tsc-gen-row .primary { flex: 2 1 0; width: auto; }
#tsc-prompt-panel .tsc-gen-row .tsc-translate { flex: 1 1 0; width: auto; }
#tsc-prompt-panel select, #tsc-prompt-panel input[type=text], #tsc-prompt-panel textarea {
  width: 100%; box-sizing: border-box; border: 1px solid #bbb; border-radius: 4px;
  padding: 6px 8px; background: #fff; color: #111; font: inherit;
}
#tsc-prompt-panel textarea { min-height: 88px; resize: vertical; }
#tsc-prompt-panel textarea.tsc-result { min-height: 180px; font-family: Consolas, monospace; font-size: 12px; }
#tsc-prompt-panel button {
  border: 1px solid #b5b5b5; background: #fff; border-radius: 4px;
  padding: 5px 10px; cursor: pointer; font: inherit;
}
#tsc-prompt-panel button.primary { background: #2d89ef; color: #fff; border-color: #2d89ef; }
#tsc-prompt-panel button:disabled { opacity: .55; cursor: wait; }
#tsc-prompt-panel .tsc-status { color: #666; font-size: 12px; min-height: 16px; }
#tsc-prompt-panel .tsc-status.err { color: #c0392b; }
#tsc-prompt-panel .tsc-status.ok { color: #1e8449; }
#tsc-prompt-panel .tsc-imgname { color: #888; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
#tsc-prompt-panel .tsc-thumb {
  display: none; max-width: 100%; max-height: 120px; border: 1px solid #ccc;
  border-radius: 4px; object-fit: contain; background: #fff;
}
#tsc-prompt-panel .tsc-section {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 8px;
}
#tsc-usage-modal {
  position: fixed; inset: 0; z-index: 10000; background: rgba(0,0,0,.45);
  display: none; align-items: center; justify-content: center;
}
#tsc-usage-modal.open { display: flex; }
#tsc-usage-modal .box {
  width: min(720px, 92vw); height: min(580px, 86vh); background: #fff; color: #222;
  border-radius: 8px; display: flex; flex-direction: column; overflow: hidden;
}
#tsc-usage-modal .box pre {
  margin: 0; padding: 12px 14px; overflow: auto; flex: 1; white-space: pre-wrap;
  font-family: "Microsoft YaHei", sans-serif; font-size: 13px;
}
  `;
  document.head.appendChild(css);
}

function hideWidget(widget) {
  if (!widget) return;
  widget.hidden = true;
  widget.computeSize = () => [0, -4];
}

function getWidget(node, name) {
  return node.widgets?.find((w) => w.name === name);
}

function setComboValues(widget, values, preferred) {
  if (!widget) return;
  const list = values?.length ? values : [EMPTY_FAV];
  if (widget.options) widget.options.values = list;
  if (Array.isArray(widget.values)) widget.values = list;
  if (preferred && list.includes(preferred)) widget.value = preferred;
  else if (!list.includes(widget.value)) widget.value = list[0];
}

function comboNames(widget) {
  const raw = widget?.options?.values || widget?.values || [];
  return Array.isArray(raw) ? raw : [];
}

/** 删除后选同一位置的下一条；删的是末条则回退到上一条。 */
function pickNextFavorite(remaining, deletedName, beforeList) {
  const left = (remaining || []).filter((n) => n && !EMPTY_MARKERS.has(n));
  if (!left.length) return EMPTY_FAV;
  const before = (beforeList || []).filter((n) => n && !EMPTY_MARKERS.has(n));
  const idx = before.indexOf(deletedName);
  if (idx >= 0 && idx < left.length) return left[idx];
  if (idx > 0) return left[Math.min(idx - 1, left.length - 1)];
  return left[0];
}

function applyFavoriteItemToNode(node, item) {
  if (!item) return;
  setWidgetValue(node, "result_prompt", item.prompt || "");
  if (item.theme) setWidgetValue(node, "theme", item.theme);
  if (item.style) {
    const sw = getWidget(node, "style");
    const opts = sw?.options?.values || [];
    if (opts.includes(item.style)) setWidgetValue(node, "style", item.style);
  }
}

function setWidgetValue(node, name, value) {
  const w = getWidget(node, name);
  if (!w) return;
  w.value = value;
  node.setDirtyCanvas?.(true, true);
}

function widgetVal(node, name, fallback = "") {
  const w = getWidget(node, name);
  return w?.value != null ? String(w.value) : fallback;
}

function isIdeogram4Panel(node) {
  const t = node?.comfyClass || node?.type || "";
  return t === "TSCPromptWriterPanelIdeogram4";
}

function panelOutputFormat(node) {
  return isIdeogram4Panel(node) ? "ideogram4" : "";
}

/** 仅在节点内生成：调 API，不排队整图工作流 */
async function generateInNode(node) {
  if (node.__tscBusy) return;
  node.__tscBusy = true;
  const resultW = getWidget(node, "result_prompt");
  const prev = resultW?.value;
  if (resultW) {
    resultW.value = isIdeogram4Panel(node)
      ? "正在按所选风格生成，并转为 Ideogram4 JSON，请稍候…"
      : "正在加载模型并生成提示词，请稍候…";
  }
  node.setDirtyCanvas?.(true, true);
  try {
    const data = await postJson(`${API}/generate`, {
      model: widgetVal(node, "model"),
      style: widgetVal(node, "style"),
      theme: widgetVal(node, "theme"),
      aspect_ratio: widgetVal(node, "aspect_ratio"),
      output_format: panelOutputFormat(node),
    });
    if (!data.ok) {
      if (resultW) resultW.value = prev || "";
      app.ui?.dialog?.show?.(data.status || "生成失败");
      return;
    }
    if (resultW) resultW.value = data.prompt || "";
    const names = data.favorites?.length ? [EMPTY_FAV, ...data.favorites] : [EMPTY_FAV];
    setComboValues(getWidget(node, "favorite"), names, names[1] || EMPTY_FAV);
    node.setDirtyCanvas?.(true, true);
  } catch (e) {
    if (resultW) resultW.value = prev || "";
    app.ui?.dialog?.show?.("生成失败：" + (e.message || e));
  } finally {
    node.__tscBusy = false;
  }
}

function clearTheme(node) {
  setWidgetValue(node, "theme", "");
  node.setDirtyCanvas?.(true, true);
}

function clearResultPrompt(node) {
  setWidgetValue(node, "result_prompt", "");
  node.setDirtyCanvas?.(true, true);
}

async function copyResultPrompt(node) {
  const text = widgetVal(node, "result_prompt").trim();
  if (!text || EMPTY_MARKERS.has(text)) {
    app.ui?.dialog?.show?.("结果栏为空，没有可复制的内容");
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
}

async function translateInNode(node) {
  if (node.__tscBusy) return;
  const resultW = getWidget(node, "result_prompt");
  const prev = String(resultW?.value || "").trim();
  if (!prev || EMPTY_MARKERS.has(prev) || prev.startsWith("正在")) {
    app.ui?.dialog?.show?.("请先生成提示词，再点翻译");
    return;
  }
  node.__tscBusy = true;
  if (resultW) resultW.value = prev + "\n\n正在翻译为中文…";
  node.setDirtyCanvas?.(true, true);
  try {
    const data = await postJson(`${API}/translate`, {
      model: widgetVal(node, "model"),
      text: prev,
    });
    if (!data.ok) {
      if (resultW) resultW.value = prev;
      app.ui?.dialog?.show?.(data.status || "翻译失败");
      return;
    }
    if (resultW) resultW.value = data.prompt || prev;
    node.setDirtyCanvas?.(true, true);
  } catch (e) {
    if (resultW) resultW.value = prev;
    app.ui?.dialog?.show?.("翻译失败：" + (e.message || e));
  } finally {
    node.__tscBusy = false;
  }
}

function addNodeActionPanel(node) {
  const BTN_H = 22;
  const ROWS = 3;
  const panelH = BTN_H * ROWS;

  const panel = document.createElement("div");
  panel.style.cssText =
    `display:flex;flex-direction:column;width:100%;height:${panelH}px;` +
    "box-sizing:border-box;padding:0;margin:0;gap:0;border:1px solid #555;";

  const mkRow = () => {
    const row = document.createElement("div");
    row.style.cssText =
      `display:flex;width:100%;height:${BTN_H}px;box-sizing:border-box;padding:0;margin:0;gap:0;`;
    return row;
  };

  const mkBtn = (label, onClick, { flex = "1 1 0", primary = false } = {}) => {
    const b = document.createElement("button");
    b.textContent = label;
    b.style.cssText =
      `flex:${flex};height:${BTN_H}px;line-height:${BTN_H - 2}px;cursor:pointer;` +
      "padding:0 6px;margin:0;border:none;border-right:1px solid #555;border-bottom:1px solid #555;" +
      `background:${primary ? "#2a5a8a" : "#333"};color:#eee;` +
      "font:12px/20px sans-serif;box-sizing:border-box;border-radius:0;";
    b.addEventListener("mouseenter", () => {
      b.style.background = primary ? "#3470a8" : "#3a3a3a";
    });
    b.addEventListener("mouseleave", () => {
      b.style.background = primary ? "#2a5a8a" : "#333";
    });
    b.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      onClick();
    });
    return b;
  };

  const row1 = mkRow();
  const bClearTheme = mkBtn("清空主题", () => clearTheme(node));
  const bCopy = mkBtn("复制结果", () => copyResultPrompt(node));
  const bClearResult = mkBtn("清空结果", () => clearResultPrompt(node));
  bClearResult.style.borderRight = "none";
  row1.append(bClearTheme, bCopy, bClearResult);

  const row2 = mkRow();
  const bGen = mkBtn("▶ 生成提示词", () => generateInNode(node), {
    flex: "2 1 0",
    primary: true,
  });
  const bTr = mkBtn("翻译", () => translateInNode(node), { flex: "1 1 0" });
  bTr.style.borderRight = "none";
  row2.append(bGen, bTr);

  const row3 = mkRow();
  const bLoad = mkBtn("加载收藏", () => loadFavoriteInNode(node));
  const bDel = mkBtn("删除收藏", () => deleteFavoriteInNode(node));
  bDel.style.borderRight = "none";
  // 最后一行去掉底边，避免双边框
  for (const el of [bLoad, bDel]) el.style.borderBottom = "none";
  row3.append(bLoad, bDel);

  // 中间行也保留底边作为分隔；最上行按钮带底边
  panel.append(row1, row2, row3);

  const w = node.addDOMWidget("tsc_actions", "tsc_actions", panel, {
    serialize: false,
    getMinHeight: () => panelH,
  });
  if (w) {
    w.serialize = false;
    w.computeSize = (width) => [width, panelH];
    if (w.options) w.options.getMinHeight = () => panelH;
  }
  return w;
}

async function loadFavoriteInNode(node) {
  const name = widgetVal(node, "favorite");
  if (!name || EMPTY_MARKERS.has(name)) {
    app.ui?.dialog?.show?.("请先在收藏列表中选择一条历史");
    return;
  }
  try {
    const list = await getJson(`${API}/favorites`);
    const item = (list.items || []).find((x) => x.name === name);
    if (!item) {
      app.ui?.dialog?.show?.("未找到收藏：" + name);
      return;
    }
    applyFavoriteItemToNode(node, item);
  } catch (e) {
    app.ui?.dialog?.show?.("加载收藏失败：" + (e.message || e));
  }
}

async function deleteFavoriteInNode(node) {
  const name = widgetVal(node, "favorite");
  if (!name || EMPTY_MARKERS.has(name)) {
    app.ui?.dialog?.show?.("请先选择要删除的收藏");
    return;
  }
  try {
    const before = comboNames(getWidget(node, "favorite"));
    const data = await postJson(`${API}/favorites/delete`, { name });
    if (!data.ok) {
      app.ui?.dialog?.show?.(data.status || "删除失败");
      return;
    }
    const remaining = data.names || [];
    const names = remaining.length ? [EMPTY_FAV, ...remaining] : [EMPTY_FAV];
    const next = pickNextFavorite(remaining, name, before);
    setComboValues(getWidget(node, "favorite"), names, next);
    const nextItem = (data.items || []).find((x) => x.name === next);
    if (nextItem) applyFavoriteItemToNode(node, nextItem);
    else setWidgetValue(node, "result_prompt", "");
    node.setDirtyCanvas?.(true, true);
  } catch (e) {
    app.ui?.dialog?.show?.("删除失败：" + (e.message || e));
  }
}

class TscPromptPanel {
  constructor() {
    this.data = null;
    this.imageFile = null;
    this.busy = false;
    this._skipModelAutoLoad = false;
    this.build();
    this.reload();
  }

  build() {
    injectStyles();
    this.fab = el("button", {
      id: "tsc-prompt-fab",
      title: "提示词生成器",
      text: "词",
      onClick: () => this.toggle(),
    });
    this.root = el("div", { id: "tsc-prompt-panel" });

    const closeBtn = el("button", { text: "关闭", onClick: () => this.hide() });
    this.root.appendChild(
      el("div", { className: "tsc-head" }, [
        el("h3", { text: "提示词生成器" }),
        closeBtn,
      ])
    );

    this.body = el("div", { className: "tsc-body" });
    this.root.appendChild(this.body);

    this.tip = el("div", {
      className: "tsc-tip",
      text: "选定风格后填写主题，点生成。每次生成会自动写入收藏历史。",
    });
    this.body.appendChild(this.tip);

    const modelSec = el("div", { className: "tsc-section" });
    modelSec.appendChild(el("label", { text: "Llama 模型" }));
    this.modelSelect = el("select");
    this.modelSelect.addEventListener("change", () => this.onModelChange());
    modelSec.appendChild(this.modelSelect);
    const modelBtns = el("div", { className: "tsc-row" });
    this.btnLoad = el("button", { text: "加载", onClick: () => this.llama("ensure") });
    this.btnUnload = el("button", { text: "卸载", onClick: () => this.llama("卸载") });
    this.btnRestart = el("button", { text: "切换并重启", onClick: () => this.llama("ensure") });
    this.btnStatus = el("button", { text: "状态", onClick: () => this.llama("status") });
    modelBtns.append(this.btnLoad, this.btnUnload, this.btnRestart, this.btnStatus);
    modelSec.appendChild(modelBtns);
    this.body.appendChild(modelSec);

    this.body.appendChild(el("label", { text: "风格：" }));
    const styleRow = el("div", { className: "tsc-row" });
    this.styleSelect = el("select");
    this.btnRefresh = el("button", { text: "刷新", onClick: () => this.reload() });
    this.btnUsage = el("button", { text: "使用说明", onClick: () => this.showUsage() });
    styleRow.append(this.styleSelect, this.btnRefresh, this.btnUsage);
    this.body.appendChild(styleRow);

    this.body.appendChild(el("label", { text: "主题 / 画面描述：" }));
    this.theme = el("textarea", { placeholder: "填写主题或画面描述…" });
    this.body.appendChild(this.theme);

    const imgRow = el("div", { className: "tsc-row" });
    imgRow.appendChild(el("span", { text: "参考图：" }));
    this.fileInput = el("input", { type: "file", accept: "image/*", style: "display:none" });
    this.fileInput.addEventListener("change", () => this.onPickImage());
    this.btnPick = el("button", { text: "选图片", onClick: () => this.fileInput.click() });
    this.btnClearImg = el("button", { text: "移除", onClick: () => this.clearImage() });
    this.imgName = el("span", { className: "tsc-imgname", text: "未选择（墨线转译 / 图生视频可只选图）" });
    imgRow.append(this.btnPick, this.btnClearImg, this.imgName, this.fileInput);
    this.body.appendChild(imgRow);
    this.thumb = el("img", { className: "tsc-thumb", alt: "preview" });
    this.body.appendChild(this.thumb);

    this.status = el("div", { className: "tsc-status" });
    this.body.appendChild(this.status);

    const genRow = el("div", { className: "tsc-row tsc-gen-row" });
    this.btnGen = el("button", { className: "primary", text: "生成提示词", onClick: () => this.generate() });
    this.btnTranslate = el("button", { className: "tsc-translate", text: "翻译", onClick: () => this.translate() });
    genRow.append(this.btnGen, this.btnTranslate);
    this.body.appendChild(genRow);

    const actRow = el("div", { className: "tsc-row" });
    this.btnCopy = el("button", { text: "复制结果", onClick: () => this.copyResult() });
    this.btnClear = el("button", { text: "清空", onClick: () => this.clearTheme() });
    actRow.append(this.btnCopy, this.btnClear);
    this.body.appendChild(actRow);

    const aspectRow = el("div", { className: "tsc-row" });
    aspectRow.appendChild(el("span", { text: "画幅：" }));
    this.aspectSelect = el("select");
    aspectRow.appendChild(this.aspectSelect);
    this.body.appendChild(aspectRow);

    this.body.appendChild(el("label", { text: "生成结果：" }));
    this.result = el("textarea", { className: "tsc-result", placeholder: "生成结果…" });
    this.body.appendChild(this.result);

    const favSec = el("div", { className: "tsc-section" });
    favSec.appendChild(el("label", { text: "收藏历史（生成后自动写入）" }));
    const favRow2 = el("div", { className: "tsc-row" });
    this.favSelect = el("select");
    this.btnLoadFav = el("button", { text: "加载", onClick: () => this.loadFav() });
    this.btnDelFav = el("button", { text: "删除", onClick: () => this.deleteFav() });
    this.btnRefreshFav = el("button", { text: "刷新列表", onClick: () => this.reloadFavs() });
    favRow2.append(this.favSelect, this.btnLoadFav, this.btnDelFav, this.btnRefreshFav);
    favSec.appendChild(favRow2);
    this.body.appendChild(favSec);

    this.usageModal = el("div", { id: "tsc-usage-modal" });
    this.usagePre = el("pre");
    const usageClose = el("button", {
      text: "关闭",
      style: "margin:8px 14px 12px",
      onClick: () => this.usageModal.classList.remove("open"),
    });
    this.usageModal.appendChild(
      el("div", { className: "box" }, [
        el("div", { className: "tsc-head" }, [el("h3", { text: "使用说明" }), usageClose]),
        this.usagePre,
      ])
    );
    this.usageModal.addEventListener("click", (e) => {
      if (e.target === this.usageModal) this.usageModal.classList.remove("open");
    });

    document.body.append(this.fab, this.root, this.usageModal);
  }

  toggle() {
    this.root.classList.toggle("open");
    if (this.root.classList.contains("open") && !this.data) this.reload();
  }

  hide() {
    this.root.classList.remove("open");
  }

  setStatus(text, kind = "") {
    this.status.textContent = text || "";
    this.status.className = "tsc-status" + (kind ? " " + kind : "");
  }

  fillSelect(select, items, selected) {
    select.innerHTML = "";
    const list = items?.length ? items : [EMPTY_FAV];
    for (const item of list) {
      const opt = el("option", { value: item, text: item === EMPTY_FAV ? "（暂无 / 未选择）" : item });
      if (item === selected) opt.selected = true;
      select.appendChild(opt);
    }
  }

  async reloadFavs() {
    try {
      const list = await getJson(`${API}/favorites`);
      const names = list.names?.length ? [EMPTY_FAV, ...list.names] : [EMPTY_FAV];
      this.fillSelect(this.favSelect, names, names[1] || EMPTY_FAV);
    } catch (e) {
      this.setStatus("刷新收藏失败：" + (e.message || e), "err");
    }
  }

  async reload() {
    try {
      const data = await getJson(`${API}/bootstrap`);
      if (!data.ok) throw new Error(data.error || "bootstrap failed");
      this.data = data;
      this._skipModelAutoLoad = true;
      this.fillSelect(this.modelSelect, data.models, data.default_model);
      this._skipModelAutoLoad = false;
      this.fillSelect(this.styleSelect, data.styles, data.default_style);
      this.fillSelect(this.aspectSelect, data.aspect_ratios, "9:16 (Portrait Widescreen)");
      const favs = data.favorites?.length ? [EMPTY_FAV, ...data.favorites] : [EMPTY_FAV];
      this.fillSelect(this.favSelect, favs, favs[1] || EMPTY_FAV);
      const llamaOk = data.llama?.llama || data.llama?.ready;
      this.setStatus(
        `已加载 ${data.styles?.length || 0} 种风格 · Llama ${llamaOk ? "运行中" : "未运行"} · 收藏 ${data.favorites?.length || 0} 条`,
        llamaOk ? "ok" : ""
      );
    } catch (e) {
      this.setStatus("加载失败：" + (e.message || e), "err");
    }
  }

  styleId() {
    const label = this.styleSelect.value || "";
    if (this.data?.style_ids?.[label]) return this.data.style_ids[label];
    const m = label.match(/（([^）]+)）$/);
    return m ? m[1] : label;
  }

  async showUsage() {
    const sid = this.styleId();
    try {
      const data = await getJson(`${API}/usage?style_id=${encodeURIComponent(sid)}`);
      this.usagePre.textContent = data.text?.trim() || `风格「${sid}」暂无使用说明。`;
      this.usageModal.classList.add("open");
    } catch (e) {
      this.setStatus("读取使用说明失败：" + (e.message || e), "err");
    }
  }

  onPickImage() {
    const file = this.fileInput.files?.[0];
    if (!file) return;
    this.imageFile = file;
    this.imgName.textContent = file.name;
    this.imgName.style.color = "#333";
    const url = URL.createObjectURL(file);
    this.thumb.src = url;
    this.thumb.style.display = "block";
    this.setStatus("已选参考图。墨线风格将先读图再转译；图生视频可直接生成。");
  }

  clearImage() {
    this.imageFile = null;
    this.fileInput.value = "";
    this.imgName.textContent = "未选择（墨线转译 / 图生视频可只选图）";
    this.imgName.style.color = "#888";
    this.thumb.removeAttribute("src");
    this.thumb.style.display = "none";
  }

  clearTheme() {
    this.theme.value = "";
    this.setStatus("已清空主题");
  }

  async copyResult() {
    const text = (this.result.value || "").trim();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      this.setStatus("已复制（纯提示词正文）", "ok");
    } catch {
      this.result.select();
      document.execCommand("copy");
      this.setStatus("已复制", "ok");
    }
  }

  setBusy(v) {
    this.busy = v;
    for (const b of [
      this.btnGen, this.btnTranslate, this.btnLoad, this.btnUnload, this.btnRestart, this.btnStatus,
      this.btnLoadFav, this.btnDelFav, this.btnRefresh, this.btnRefreshFav,
    ]) {
      if (b) b.disabled = !!v;
    }
  }

  async onModelChange() {
    if (this.busy || this._skipModelAutoLoad || !this.modelSelect.value) return;
    await this.llama("ensure");
  }

  async llama(action) {
    if (this.busy) return;
    this.setBusy(true);
    this.setStatus("处理中…");
    try {
      const data = await postJson(`${API}/llama`, {
        model: this.modelSelect.value,
        action,
      });
      this.setStatus(data.status || (data.ok ? "完成" : "失败"), data.ok ? "ok" : "err");
    } catch (e) {
      this.setStatus("失败：" + (e.message || e), "err");
    } finally {
      this.setBusy(false);
    }
  }

  async generate() {
    if (this.busy) return;
    const style = this.styleSelect.value;
    const theme = this.theme.value.trim();
    if (!style) {
      this.setStatus("请先选择一种风格。", "err");
      return;
    }
    if (!theme && !((this.styleId() === "ltx-video" || this.styleId() === "ink-editorial") && this.imageFile)) {
      this.setStatus("请填写主题 / 画面描述，或为墨线风格 / 图生视频选一张参考图。", "err");
      return;
    }
    this.setBusy(true);
    this.setStatus("生成中…");
    this.result.value = `正在按风格「${this.styleId()}」生成，请稍候…`;
    try {
      let data;
      if (this.imageFile) {
        const fd = new FormData();
        fd.append("style", style);
        fd.append("theme", theme);
        fd.append("aspect_ratio", this.aspectSelect.value);
        fd.append("model", this.modelSelect.value);
        fd.append("image", this.imageFile, this.imageFile.name);
        const res = await api.fetchApi(`${API}/generate`, { method: "POST", body: fd });
        data = await res.json();
      } else {
        data = await postJson(`${API}/generate`, {
          style,
          theme,
          aspect_ratio: this.aspectSelect.value,
          model: this.modelSelect.value,
        });
      }
      if (!data.ok) {
        this.result.value = data.status || "生成失败";
        this.setStatus(data.status || "失败", "err");
      } else {
        this.result.value = data.prompt || "";
        this.setStatus(data.status || "完成", "ok");
        const favs = data.favorites?.length ? [EMPTY_FAV, ...data.favorites] : [EMPTY_FAV];
        this.fillSelect(this.favSelect, favs, favs[1] || EMPTY_FAV);
      }
    } catch (e) {
      this.result.value = "";
      this.setStatus("调用失败：" + (e.message || e), "err");
    } finally {
      this.setBusy(false);
    }
  }

  async translate() {
    if (this.busy) return;
    const prev = (this.result.value || "").trim();
    if (!prev || prev.startsWith("正在")) {
      this.setStatus("请先生成提示词，再点翻译。", "err");
      return;
    }
    this.setBusy(true);
    this.setStatus("翻译中…");
    this.result.value = prev + "\n\n正在翻译为中文…";
    try {
      const data = await postJson(`${API}/translate`, {
        model: this.modelSelect.value,
        text: prev,
      });
      if (!data.ok) {
        this.result.value = prev;
        this.setStatus(data.status || "翻译失败", "err");
      } else {
        this.result.value = data.prompt || prev;
        this.setStatus(data.status || "已翻译", "ok");
      }
    } catch (e) {
      this.result.value = prev;
      this.setStatus("翻译失败：" + (e.message || e), "err");
    } finally {
      this.setBusy(false);
    }
  }

  async loadFav() {
    const name = this.favSelect.value;
    if (!name || name === EMPTY_FAV || name.startsWith("（")) {
      this.setStatus("请先选择一条收藏", "err");
      return;
    }
    const list = await getJson(`${API}/favorites`);
    const item = (list.items || []).find((x) => x.name === name);
    if (!item) {
      this.setStatus("未找到收藏：" + name, "err");
      return;
    }
    this.result.value = item.prompt || "";
    if (item.theme) this.theme.value = item.theme;
    if (item.style) {
      const opts = [...this.styleSelect.options].map((o) => o.value);
      if (opts.includes(item.style)) this.styleSelect.value = item.style;
      else {
        const hit = opts.find((o) => o.includes(item.style) || item.style.includes(o));
        if (hit) this.styleSelect.value = hit;
      }
    }
    this.setStatus("已加载收藏：" + name, "ok");
  }

  async deleteFav() {
    const name = this.favSelect.value;
    if (!name || name === EMPTY_FAV || name.startsWith("（")) {
      this.setStatus("请先选择要删除的收藏", "err");
      return;
    }
    const before = [...this.favSelect.options].map((o) => o.value);
    const data = await postJson(`${API}/favorites/delete`, { name });
    if (!data.ok) {
      this.setStatus(data.status || "删除失败", "err");
      return;
    }
    const remaining = data.names || [];
    const favs = remaining.length ? [EMPTY_FAV, ...remaining] : [EMPTY_FAV];
    const next = pickNextFavorite(remaining, name, before);
    this.fillSelect(this.favSelect, favs, next);
    const nextItem = (data.items || []).find((x) => x.name === next);
    if (nextItem) {
      this.result.value = nextItem.prompt || "";
      if (nextItem.theme) this.theme.value = nextItem.theme;
    } else {
      this.result.value = "";
    }
    this.setStatus(
      next === EMPTY_FAV ? (data.status || "已删空") : `已删除，已切到下一条：${next}`,
      data.ok ? "ok" : "err",
    );
  }
}

function setupPanelNode(node) {
  if (node.__tscButtonsReady) return;
  node.__tscButtonsReady = true;
  node.setSize?.([420, 540]);

  // 旧工作流里可能还残留 action 控件，一律隐藏
  hideWidget(getWidget(node, "action"));

  const rp = getWidget(node, "result_prompt");
  if (rp && EMPTY_MARKERS.has(String(rp.value || "").trim())) {
    rp.value = "";
  }

  addNodeActionPanel(node);

  // 换模型 / 换风格：清空结果栏，避免工作流沿用旧提示词
  const hookClearOnChange = (widgetName) => {
    const w = getWidget(node, widgetName);
    if (!w || w.__tscClearHooked) return;
    w.__tscClearHooked = true;
    let last = String(w.value ?? "");
    const prev = w.callback;
    w.callback = function (value) {
      prev?.apply(this, arguments);
      const next = String(value ?? "");
      if (next === last) return;
      last = next;
      clearResultPrompt(node);
      if (widgetName === "model") {
        postJson(`${API}/llama`, { model: next, action: "ensure" }).catch(() => {});
      }
    };
  };
  hookClearOnChange("model");
  hookClearOnChange("style");

  getJson(`${API}/favorites`)
    .then((list) => {
      const names = list.names?.length ? [EMPTY_FAV, ...list.names] : [EMPTY_FAV];
      setComboValues(getWidget(node, "favorite"), names, names[1] || EMPTY_FAV);
      node.setDirtyCanvas?.(true, true);
    })
    .catch(() => {
      setComboValues(getWidget(node, "favorite"), [EMPTY_FAV], EMPTY_FAV);
    });
}

app.registerExtension({
  name: "comfy-tsc.PromptPanel",
  async setup() {
    window.__tscPromptPanel = new TscPromptPanel();
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== "TSCPromptWriterPanel" && nodeData?.name !== "TSCPromptWriterPanelIdeogram4") return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = onNodeCreated?.apply(this, arguments);
      setupPanelNode(this);
      return r;
    };

    const onExecuted = nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted = function (message) {
      onExecuted?.apply(this, arguments);
      const names = message?.favorites?.[0];
      if (Array.isArray(names)) {
        setComboValues(getWidget(this, "favorite"), names, names[1] || names[0]);
      }
      const rp = message?.result_prompt?.[0];
      if (typeof rp === "string") {
        const rw = getWidget(this, "result_prompt");
        if (rw) rw.value = rp;
      }
      this.setDirtyCanvas?.(true, true);
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (info) {
      const r = onConfigure?.apply(this, arguments);
      if (Array.isArray(this.widgets)) {
        this.widgets = this.widgets.filter((w) => {
          if (!w?.name) return true;
          if (w.name === "action") {
            hideWidget(w);
            return true;
          }
          if (
            w.name === "清空主题/结果" ||
            w.name === "tsc_clear_row" ||
            w.name === "tsc_fav_row" ||
            w.name === "tsc_actions" ||
            w.name === "参考图" ||
            w.name === "加载收藏（仅本节点）" ||
            w.name === "删除收藏（仅本节点）" ||
            w.name === "▶ 生成提示词（仅本节点）"
          ) {
            return false;
          }
          if (w.type === "button") return false;
          return true;
        });
      }
      const favW = getWidget(this, "favorite");
      if (favW && EMPTY_MARKERS.has(String(favW.value || "").trim())) {
        favW.value = EMPTY_FAV;
      }
      const rp = getWidget(this, "result_prompt");
      if (rp && EMPTY_MARKERS.has(String(rp.value || "").trim())) {
        rp.value = "";
      }
      this.__tscButtonsReady = false;
      if (Array.isArray(this.widgets)) {
        this.widgets = this.widgets.filter((w) => {
          if (!w?.name) return true;
          if (
            w.name === "tsc_clear_row" ||
            w.name === "tsc_fav_row" ||
            w.name === "tsc_actions" ||
            w.name === "▶ 生成提示词（仅本节点）"
          ) {
            return false;
          }
          return true;
        });
      }
      setupPanelNode(this);
      return r;
    };
  },
});
