/* Guage Kit report. Untrusted text is only ever set with textContent; no network, no eval, no storage. */
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("guage-data").textContent);
  var M = JSON.parse(document.getElementById("guage-manifest").textContent);
  var SVGNS = "http://www.w3.org/2000/svg";
  var main = document.getElementById("main");
  var tip = h("div", { class: "tip", role: "tooltip" });
  document.body.appendChild(tip);

  // ── helpers ──────────────────────────────────────────────────────────────
  function h(tag, attrs) {
    var el = document.createElement(tag);
    setAttrs(el, attrs);
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function s(tag, attrs) {
    var el = document.createElementNS(SVGNS, tag);
    setAttrs(el, attrs);
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function setAttrs(el, attrs) {
    if (!attrs) return;
    Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === "text") el.textContent = String(v);
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : String(v));
    });
  }
  function add(el, child) {
    if (child === null || child === undefined || child === false) return;
    if (Array.isArray(child)) { child.forEach(function (c) { add(el, c); }); return; }
    el.appendChild(typeof child === "object" ? child : document.createTextNode(String(child)));
  }
  function fmt(v, d) {
    if (v === null || v === undefined || (typeof v === "number" && !isFinite(v))) return "–";
    if (typeof v !== "number") return String(v);
    if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString();
    return v.toFixed(d === undefined ? 3 : d);
  }
  function pct(v) { return v === null || v === undefined ? "–" : Math.round(v * 100) + "%"; }
  function text(v) {
    if (v === null || v === undefined) return "";
    if (typeof v === "string") return v;
    try { return JSON.stringify(v, null, 2); } catch (e) { return String(v); }
  }
  function showTip(evt, lines) {
    tip.textContent = "";
    lines.forEach(function (l, i) { add(tip, i ? h("div", { class: "muted" }, l) : h("div", null, h("b", null, l))); });
    tip.style.display = "block";
    var x = Math.min(evt.clientX + 12, window.innerWidth - 330);
    tip.style.left = x + "px";
    tip.style.top = (evt.clientY + 14) + "px";
  }
  function hideTip() { tip.style.display = "none"; }
  function hover(el, lines) {
    el.addEventListener("mousemove", function (e) { showTip(e, lines); });
    el.addEventListener("mouseleave", hideTip);
    el.setAttribute("tabindex", "0");
    el.addEventListener("focus", function () { var r = el.getBoundingClientRect(); showTip({ clientX: r.right, clientY: r.top }, lines); });
    el.addEventListener("blur", hideTip);
  }
  function good(summary, value) {
    if (summary.threshold === null || summary.threshold === undefined || value === null) return null;
    return summary.higher_is_better ? value >= summary.threshold : value <= summary.threshold;
  }
  var SEQ = ["--seq-100", "--seq-200", "--seq-300", "--seq-400", "--seq-500", "--seq-600", "--seq-700"];
  function seqVar(t) { return "var(" + SEQ[Math.max(0, Math.min(SEQ.length - 1, Math.round(t * (SEQ.length - 1))))] + ")"; }
  var summaries = D.summaries || {};
  var metricNames = Object.keys(summaries);

  // ── header, tabs, footer ─────────────────────────────────────────────────
  document.getElementById("title").textContent = D.run.name || "Evaluation";
  document.title = D.title;
  var views = [["overview", "Overview"], ["metrics", "Metrics"]];
  if (Object.keys(D.slices || {}).length) views.push(["slices", "Slices"]);
  views.push(["samples", "Samples"]);
  if (D.comparison) views.push(["compare", "Comparison"]);
  views.push(["about", "About"]);
  var tabs = document.getElementById("tabs");
  var current = location.hash.replace("#", "") || "overview";
  if (!views.some(function (v) { return v[0] === current; })) current = "overview";
  views.forEach(function (v) {
    tabs.appendChild(h("button", { role: "tab", id: "tab-" + v[0], "aria-selected": v[0] === current ? "true" : "false", onclick: function () { go(v[0]); } }, v[1]));
  });
  tabs.addEventListener("keydown", function (e) {
    var i = views.findIndex(function (v) { return v[0] === current; });
    if (e.key === "ArrowRight") go(views[(i + 1) % views.length][0]);
    if (e.key === "ArrowLeft") go(views[(i - 1 + views.length) % views.length][0]);
  });
  function go(name) {
    current = name;
    history.replaceState(null, "", "#" + name);
    Array.prototype.forEach.call(tabs.children, function (b) { b.setAttribute("aria-selected", b.id === "tab-" + name ? "true" : "false"); });
    render();
  }
  var themes = ["auto", "light", "dark"], ti = 0;
  document.getElementById("theme").addEventListener("click", function () {
    ti = (ti + 1) % themes.length;
    if (themes[ti] === "auto") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = themes[ti];
    document.getElementById("theme").textContent = "◐ " + themes[ti].charAt(0).toUpperCase() + themes[ti].slice(1);
  });
  var foot = document.getElementById("foot");
  add(foot, "Generated by Guage Kit " + M.guage_kit + (M.ananke_plexus ? " on Ananke Plexus " + M.ananke_plexus : "") + " · run " + D.run.run_id + " · profile " + M.profile + " · offline file, no network access");

  function render() {
    main.textContent = "";
    hideTip();
    ({ overview: overview, metrics: metricsView, slices: slicesView, samples: samplesView, compare: compareView, about: about })[current]();
  }

  // ── charts ───────────────────────────────────────────────────────────────
  function miniHist(sm, w, hgt) {
    var counts = sm.histogram || [];
    var svg = s("svg", { viewBox: "0 0 " + w + " " + hgt, class: "chart", role: "img", "aria-label": "Distribution of " + sm.metric });
    if (!counts.length) return svg;
    var max = Math.max.apply(null, counts) || 1;
    var bw = w / counts.length;
    var r = sm.histogram_range || [0, 1];
    counts.forEach(function (c, i) {
      var bh = Math.max(c ? 2 : 0, (c / max) * (hgt - 6));
      var lo = r[0] + (r[1] - r[0]) * i / counts.length, hi = r[0] + (r[1] - r[0]) * (i + 1) / counts.length;
      var rect = s("rect", { x: i * bw + 1, y: hgt - bh, width: Math.max(1, bw - 2), height: bh, rx: 2, fill: "var(--seq-400)" });
      var hit = s("rect", { x: i * bw, y: 0, width: bw, height: hgt, fill: "transparent" });
      hover(hit, [c + " samples", fmt(lo) + " – " + fmt(hi)]);
      svg.appendChild(rect);
      svg.appendChild(hit);
    });
    return svg;
  }

  function ciBar(sm) {
    var lo = sm.value_range_lo, w = 220, hgt = 18;
    var a = 0, b = 1;
    if (sm.max !== null && (sm.max > 1 || (sm.min !== null && sm.min < 0))) { a = Math.min(sm.min, sm.ci_low || sm.min); b = Math.max(sm.max, sm.ci_high || sm.max); }
    if (b <= a) b = a + 1;
    function x(v) { return 6 + (v - a) / (b - a) * (w - 12); }
    var svg = s("svg", { viewBox: "0 0 " + w + " " + hgt, class: "chart", role: "img", "aria-label": "Value with 95% confidence interval" });
    svg.appendChild(s("line", { x1: 6, x2: w - 6, y1: 9, y2: 9, class: "grid-line" }));
    if (sm.ci_low !== null && sm.ci_high !== null) svg.appendChild(s("line", { x1: x(sm.ci_low), x2: x(sm.ci_high), y1: 9, y2: 9, stroke: "var(--seq-400)", "stroke-width": 4, "stroke-linecap": "round" }));
    if (sm.threshold !== null && sm.threshold !== undefined) svg.appendChild(s("line", { x1: x(sm.threshold), x2: x(sm.threshold), y1: 2, y2: 16, stroke: "var(--text-secondary)", "stroke-width": 1.5, "stroke-dasharray": "2 2" }));
    if (sm.value !== null) svg.appendChild(s("circle", { cx: x(sm.value), cy: 9, r: 5, fill: "var(--seq-600)", stroke: "var(--surface-1)", "stroke-width": 2 }));
    void lo;
    return svg;
  }

  function bigHist(sm) {
    var counts = sm.histogram || [], W = 560, H = 200, P = { l: 36, r: 10, t: 10, b: 28 };
    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, class: "chart", role: "img", "aria-label": "Histogram of " + sm.metric });
    svg.style.maxWidth = W + "px";
    if (!counts.length) { svg.appendChild(s("text", { x: 10, y: 20, text: "No per-sample values (corpus metric)" })); return svg; }
    var max = Math.max.apply(null, counts) || 1, r = sm.histogram_range || [0, 1];
    var iw = W - P.l - P.r, ih = H - P.t - P.b, bw = iw / counts.length;
    [0, 0.5, 1].forEach(function (f) {
      var y = P.t + ih - f * ih;
      svg.appendChild(s("line", { x1: P.l, x2: W - P.r, y1: y, y2: y, class: "grid-line" }));
      svg.appendChild(s("text", { x: P.l - 6, y: y + 4, "text-anchor": "end", text: Math.round(f * max) }));
    });
    counts.forEach(function (c, i) {
      var bh = (c / max) * ih, x = P.l + i * bw;
      var lo = r[0] + (r[1] - r[0]) * i / counts.length, hi = r[0] + (r[1] - r[0]) * (i + 1) / counts.length;
      if (c) svg.appendChild(s("rect", { x: x + 1, y: P.t + ih - bh, width: bw - 2, height: bh, rx: 4, fill: "var(--seq-400)" }));
      var hit = s("rect", { x: x, y: P.t, width: bw, height: ih, fill: "transparent" });
      hover(hit, [c + " samples", fmt(lo) + " – " + fmt(hi)]);
      svg.appendChild(hit);
    });
    [0, 0.5, 1].forEach(function (f) {
      svg.appendChild(s("text", { x: P.l + f * iw, y: H - 8, "text-anchor": f === 0 ? "start" : f === 1 ? "end" : "middle", text: fmt(r[0] + f * (r[1] - r[0]), 2) }));
    });
    if (sm.threshold !== null && sm.threshold !== undefined && sm.threshold >= r[0] && sm.threshold <= r[1]) {
      var tx = P.l + (sm.threshold - r[0]) / (r[1] - r[0]) * iw;
      svg.appendChild(s("line", { x1: tx, x2: tx, y1: P.t, y2: P.t + ih, stroke: "var(--text-secondary)", "stroke-dasharray": "3 3" }));
      svg.appendChild(s("text", { x: tx + 4, y: P.t + 10, text: "threshold " + fmt(sm.threshold, 2) }));
    }
    return svg;
  }

  function confusion(labels, matrix) {
    var max = 0;
    matrix.forEach(function (row) { row.forEach(function (v) { max = Math.max(max, v); }); });
    var t = h("table", { class: "heat" });
    var head = h("tr", null, h("th", { text: "gold \\ predicted" }));
    labels.forEach(function (l) { head.appendChild(h("th", { class: "num", text: l })); });
    t.appendChild(head);
    matrix.forEach(function (row, i) {
      var tr = h("tr", null, h("th", { text: labels[i] }));
      row.forEach(function (v, j) {
        var td = h("td", { class: "cell" }, String(v));
        var f = max ? v / max : 0;
        td.style.background = v ? seqVar(f) : "transparent";
        td.style.color = f > 0.55 ? "#fff" : "var(--text-primary)";
        hover(td, [v + " samples", "gold " + labels[i] + " → predicted " + labels[j]]);
        tr.appendChild(td);
      });
      t.appendChild(tr);
    });
    return t;
  }

  function reliability(bins) {
    var W = 320, H = 260, P = { l: 40, r: 10, t: 10, b: 34 }, iw = W - P.l - P.r, ih = H - P.t - P.b;
    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, class: "chart", role: "img", "aria-label": "Reliability diagram" });
    svg.style.maxWidth = W + "px";
    function X(v) { return P.l + v * iw; } function Y(v) { return P.t + ih - v * ih; }
    [0, 0.5, 1].forEach(function (f) {
      svg.appendChild(s("line", { x1: P.l, x2: W - P.r, y1: Y(f), y2: Y(f), class: "grid-line" }));
      svg.appendChild(s("text", { x: P.l - 6, y: Y(f) + 4, "text-anchor": "end", text: f }));
      svg.appendChild(s("text", { x: X(f), y: H - 16, "text-anchor": "middle", text: f }));
    });
    svg.appendChild(s("text", { x: P.l + iw / 2, y: H - 2, "text-anchor": "middle", text: "confidence" }));
    svg.appendChild(s("line", { x1: X(0), y1: Y(0), x2: X(1), y2: Y(1), stroke: "var(--text-muted)", "stroke-dasharray": "4 4" }));
    var pts = bins.map(function (b) { return X(b.confidence) + "," + Y(b.accuracy); }).join(" ");
    svg.appendChild(s("polyline", { points: pts, fill: "none", stroke: "var(--series-1)", "stroke-width": 2 }));
    bins.forEach(function (b) {
      var c = s("circle", { cx: X(b.confidence), cy: Y(b.accuracy), r: 5, fill: "var(--series-1)", stroke: "var(--surface-1)", "stroke-width": 2 });
      hover(c, ["bin " + fmt(b.lo, 1) + "–" + fmt(b.hi, 1), "accuracy " + fmt(b.accuracy) + " · confidence " + fmt(b.confidence), b.count + " samples"]);
      svg.appendChild(c);
    });
    return svg;
  }

  // ── overview ─────────────────────────────────────────────────────────────
  function overview() {
    var r = D.run;
    if (D.gate) {
      var g = D.gate;
      var labels = { PASS: "Passed", WARN: "Warning", REVIEW: "Needs review", BLOCK: "Blocked" };
      var icons = { PASS: "✓", WARN: "!", REVIEW: "?", BLOCK: "✕" };
      var failed = g.checks.filter(function (c) { return !c.ok; });
      main.appendChild(h("div", { class: "verdict" },
        h("span", { class: "badge" }, h("span", { class: "dot s-" + g.verdict }), icons[g.verdict] + " " + g.verdict + " · " + labels[g.verdict]),
        h("span", { class: "muted" }, g.checks.length + " gate checks, " + failed.length + " failed" + (g.evidence.length ? " · " + g.evidence.slice(0, 2).join("; ") : ""))));
    }
    var meta = h("div", { class: "meta" });
    [["Samples", r.dataset.samples], ["Dataset", (r.dataset.name || "") + " " + String(r.dataset.fingerprint || "").slice(0, 19)], ["Target", r.target && r.target.name], ["Judge", r.judge && r.judge.judge], ["Created", r.created_at], ["Took", fmt(r.duration_s, 1) + " s"]].forEach(function (m) {
      if (m[1]) meta.appendChild(h("span", null, m[0] + ": ", h("b", null, String(m[1]))));
    });
    main.appendChild(meta);
    (r.notes || []).forEach(function (n) { main.appendChild(h("div", { class: "note" }, n)); });
    if (!metricNames.length) { main.appendChild(h("div", { class: "empty" }, "No metrics were computed.")); return; }
    var grid = h("div", { class: "grid kpis" });
    metricNames.forEach(function (name) {
      var sm = summaries[name];
      var ok = good(sm, sm.value);
      var tile = h("div", { class: "card kpi clickable" },
        h("div", { class: "name" }, h("span", null, name, " ", h("span", { class: "muted", text: sm.higher_is_better ? "↑" : "↓", title: sm.higher_is_better ? "higher is better" : "lower is better" })), h("span", { class: "fam", text: sm.family })),
        h("div", { class: "value" + (ok === true ? " pass" : ok === false ? " fail" : "") }, fmt(sm.value), ok === null ? null : h("span", { class: "small", text: ok ? "  ✓ meets " + fmt(sm.threshold, 2) : "  ✕ misses " + fmt(sm.threshold, 2) })),
        h("div", { class: "sub" }, sm.ci_low !== null && sm.ci_low !== undefined ? "95% CI " + fmt(sm.ci_low) + " – " + fmt(sm.ci_high) : "", " · n=" + sm.n + (sm.skipped ? " · " + sm.skipped + " skipped" : "") + (sm.errors ? " · " + sm.errors + " errors" : "")),
        ciBar(sm),
        sm.histogram && sm.histogram.length ? miniHist(sm, 220, 40) : null);
      tile.addEventListener("click", function () { detailOf = name; go("metrics"); });
      grid.appendChild(tile);
    });
    main.appendChild(grid);
    if (D.gate && D.gate.checks.length) {
      main.appendChild(h("h3", null, "Gate checks (decided by Ananke Plexus policy)"));
      var t = h("table", null, h("tr", null, h("th", { text: "" }), h("th", { text: "metric" }), h("th", { text: "result" }), h("th", { text: "on fail" })));
      D.gate.checks.forEach(function (c) {
        t.appendChild(h("tr", null, h("td", { class: c.ok ? "pass" : "fail", text: c.ok ? "✓" : "✕" }), h("td", { text: c.metric }), h("td", { text: c.message }), h("td", { text: c.rule.on_fail })));
      });
      main.appendChild(h("div", { class: "card" }, t));
    }
  }

  // ── metrics ──────────────────────────────────────────────────────────────
  var detailOf = null, sortKey = null, sortDir = 1;
  function metricsView() {
    var cols = [["metric", "metric"], ["family", "family"], ["value", "value"], ["ci_low", "95% CI"], ["n", "n"], ["skipped", "skipped"], ["threshold", "threshold"], ["pass_rate", "pass rate"]];
    var rows = metricNames.map(function (n) { return summaries[n]; });
    if (sortKey) rows.sort(function (a, b) { var x = a[sortKey], y = b[sortKey]; return (x === y ? 0 : x === null ? 1 : y === null ? -1 : x > y ? 1 : -1) * sortDir; });
    var t = h("table");
    var hr = h("tr");
    cols.forEach(function (c) {
      hr.appendChild(h("th", { class: ["value", "ci_low", "n", "skipped", "threshold", "pass_rate"].indexOf(c[0]) >= 0 ? "num" : "", "aria-sort": sortKey === c[0] ? (sortDir > 0 ? "ascending" : "descending") : null, onclick: function () { sortDir = sortKey === c[0] ? -sortDir : 1; sortKey = c[0]; render(); } }, c[1]));
    });
    t.appendChild(hr);
    rows.forEach(function (sm) {
      var tr = h("tr", { class: "clickable", onclick: function () { detailOf = sm.metric; render(); } },
        h("td", null, h("b", { text: sm.metric }), h("div", { class: "muted small", text: sm.description })),
        h("td", { text: sm.family }),
        h("td", { class: "num", text: fmt(sm.value) }),
        h("td", { class: "num", text: sm.ci_low === null || sm.ci_low === undefined ? "–" : fmt(sm.ci_low) + " – " + fmt(sm.ci_high) }),
        h("td", { class: "num", text: sm.n }),
        h("td", { class: "num", text: sm.skipped }),
        h("td", { class: "num", text: fmt(sm.threshold, 2) }),
        h("td", { class: "num", text: pct(sm.pass_rate) }));
      t.appendChild(tr);
    });
    var wrap = h("div", { class: "grid two" }, h("div", { class: "card" }, t));
    var name = detailOf || metricNames[0];
    if (name && summaries[name]) wrap.appendChild(metricDetail(summaries[name]));
    main.appendChild(wrap);
  }
  function metricDetail(sm) {
    var card = h("div", { class: "card" }, h("h2", { text: sm.metric }), h("div", { class: "muted", text: sm.description }));
    add(card, h("div", { class: "meta" }, "value ", h("b", { text: fmt(sm.value) }), " · median ", h("b", { text: fmt(sm.median) }), " · std ", h("b", { text: fmt(sm.std) }), " · min ", h("b", { text: fmt(sm.min) }), " · max ", h("b", { text: fmt(sm.max) })));
    add(card, bigHist(sm));
    var d = sm.details || {};
    if (d.confusion_matrix) { add(card, h("h3", null, "Confusion matrix")); add(card, confusion(d.labels, d.confusion_matrix)); }
    if (d.reliability) { add(card, h("h3", null, "Reliability diagram")); add(card, reliability(d.reliability)); add(card, h("div", { class: "legend" }, h("span", null, h("span", { class: "swatch" }), "dashed: perfect calibration"))); }
    if (d.per_label) {
      add(card, h("h3", null, "Per label"));
      var t = h("table", null, h("tr", null, ["label", "precision", "recall", "f1", "support"].map(function (x) { return h("th", { text: x, class: x === "label" ? "" : "num" }); })));
      Object.keys(d.per_label).forEach(function (k) { var p = d.per_label[k]; t.appendChild(h("tr", null, h("td", { text: k }), h("td", { class: "num", text: fmt(p.precision) }), h("td", { class: "num", text: fmt(p.recall) }), h("td", { class: "num", text: fmt(p.f1) }), h("td", { class: "num", text: p.support }))); });
      add(card, t);
    }
    var rest = Object.keys(d).filter(function (k) { return ["confusion_matrix", "labels", "reliability", "per_label", "judge"].indexOf(k) < 0; });
    if (rest.length) {
      add(card, h("h3", null, "Details"));
      var o = {}; rest.forEach(function (k) { o[k] = d[k]; });
      add(card, h("pre", { class: "text", text: text(o) }));
    }
    // worst samples for this metric
    var rows = D.samples.filter(function (x) { return x.scores[sm.metric] && x.scores[sm.metric].value !== null; });
    rows.sort(function (a, b) { return (a.scores[sm.metric].value - b.scores[sm.metric].value) * (sm.higher_is_better ? 1 : -1); });
    if (rows.length) {
      add(card, h("h3", null, "Weakest samples"));
      var tb = h("table");
      rows.slice(0, 8).forEach(function (x) {
        tb.appendChild(h("tr", { class: "clickable", onclick: function () { focusSample = x.id; go("samples"); } }, h("td", { text: x.id }), h("td", { class: "num", text: fmt(x.scores[sm.metric].value) }), h("td", { class: "muted small", text: (x.scores[sm.metric].reason || "") })));
      });
      add(card, tb);
    }
    return card;
  }

  // ── slices ───────────────────────────────────────────────────────────────
  function slicesView() {
    var groups = Object.keys(D.slices);
    var cols = metricNames.filter(function (m) { return groups.some(function (g) { return D.slices[g][m] && D.slices[g][m].value !== null; }); });
    main.appendChild(h("div", { class: "legend" }, h("span", null, "Each column is shaded from its weakest slice (light) to its strongest (dark); lower-is-better metrics are flipped. Values are printed in every cell."), h("span", null, [0, 0.33, 0.66, 1].map(function (f) { var sw = h("span", { class: "swatch" }); sw.style.background = seqVar(f); return sw; }))));
    var t = h("table", { class: "heat" });
    var hr = h("tr", null, h("th", { text: "slice" }), h("th", { class: "num", text: "n" }));
    cols.forEach(function (m) { hr.appendChild(h("th", { class: "num", text: m })); });
    t.appendChild(hr);
    var overallRow = h("tr", null, h("td", null, h("b", { text: "all samples" })), h("td", { class: "num", text: D.run.dataset.samples }));
    cols.forEach(function (m) { overallRow.appendChild(h("td", { class: "num", text: fmt(summaries[m].value) })); });
    t.appendChild(overallRow);
    var ranges = {};
    cols.forEach(function (m) {
      var vs = groups.map(function (g) { return D.slices[g][m] ? D.slices[g][m].value : null; }).filter(function (v) { return v !== null; });
      ranges[m] = [Math.min.apply(null, vs), Math.max.apply(null, vs)];
    });
    groups.forEach(function (g) {
      var first = D.slices[g][cols[0]] || {};
      var tr = h("tr", null, h("td", { text: g }), h("td", { class: "num", text: first.n || "" }));
      cols.forEach(function (m) {
        var sm = D.slices[g][m], v = sm ? sm.value : null;
        var td = h("td", { class: "cell", text: fmt(v) });
        if (v !== null) {
          var r = ranges[m], f = r[1] > r[0] ? (v - r[0]) / (r[1] - r[0]) : 0.5;
          if (!summaries[m].higher_is_better) f = 1 - f;
          td.style.background = seqVar(f);
          td.style.color = f > 0.55 ? "#fff" : "var(--text-primary)";
          hover(td, [g + " · " + m, "value " + fmt(v) + (sm.ci_low !== null ? "  (95% CI " + fmt(sm.ci_low) + "–" + fmt(sm.ci_high) + ")" : ""), "overall " + fmt(summaries[m].value) + " · n=" + sm.n]);
        }
        tr.appendChild(td);
      });
      t.appendChild(tr);
    });
    main.appendChild(h("div", { class: "card", style: null }, t));
  }

  // ── samples ──────────────────────────────────────────────────────────────
  var focusSample = null, q = "", tagFilter = "", failingOnly = false, sortMetric = "", page = 0;
  function samplesView() {
    if (D.profile === "public") main.appendChild(h("div", { class: "note" }, "Public profile: sample text was removed; scores remain."));
    var tags = {};
    D.samples.forEach(function (x) { x.tags.forEach(function (t) { tags[t] = 1; }); });
    var search = h("input", { type: "search", placeholder: "Search id, input, output…", value: q, "aria-label": "Search samples" });
    search.addEventListener("input", function () { q = search.value; page = 0; list(); });
    var tagSel = h("select", { "aria-label": "Filter by tag" }, h("option", { value: "", text: "all tags" }), Object.keys(tags).sort().map(function (t) { return h("option", { value: t, text: t, selected: t === tagFilter }); }));
    tagSel.addEventListener("change", function () { tagFilter = tagSel.value; page = 0; list(); });
    var sortSel = h("select", { "aria-label": "Sort by metric" }, h("option", { value: "", text: "dataset order" }), metricNames.map(function (m) { return h("option", { value: m, text: "weakest " + m, selected: m === sortMetric }); }));
    sortSel.addEventListener("change", function () { sortMetric = sortSel.value; page = 0; list(); });
    var fail = h("input", { type: "checkbox", checked: failingOnly });
    fail.addEventListener("change", function () { failingOnly = fail.checked; page = 0; list(); });
    main.appendChild(h("div", { class: "toolbar" }, search, tagSel, sortSel, h("label", { class: "check" }, fail, "failing a threshold only")));
    var holder = h("div");
    main.appendChild(holder);
    function list() {
      holder.textContent = "";
      var needle = q.toLowerCase();
      var rows = D.samples.filter(function (x) {
        if (focusSample) return x.id === focusSample;
        if (tagFilter && x.tags.indexOf(tagFilter) < 0) return false;
        if (failingOnly && !Object.keys(x.scores).some(function (k) { return x.scores[k].passed === false; }) && !x.target_error) return false;
        if (needle) { var hay = (x.id + " " + text(x.input) + " " + text(x.output) + " " + text(x.expected)).toLowerCase(); if (hay.indexOf(needle) < 0) return false; }
        return true;
      });
      if (sortMetric) {
        var hib = summaries[sortMetric].higher_is_better;
        rows = rows.slice().sort(function (a, b) {
          var x = a.scores[sortMetric], y = b.scores[sortMetric];
          var xv = x && x.value !== null ? x.value : Infinity, yv = y && y.value !== null ? y.value : Infinity;
          return hib ? xv - yv : yv - xv;
        });
      }
      if (focusSample) holder.appendChild(h("button", { class: "ghost", onclick: function () { focusSample = null; list(); } }, "← all samples"));
      holder.appendChild(h("div", { class: "muted small", text: rows.length + " of " + D.samples.length + " samples" }));
      var per = 50, pages = Math.max(1, Math.ceil(rows.length / per));
      page = Math.min(page, pages - 1);
      rows.slice(page * per, page * per + per).forEach(function (x) { holder.appendChild(sampleCard(x, !!focusSample)); });
      if (!rows.length) holder.appendChild(h("div", { class: "empty" }, "No sample matches."));
      if (pages > 1) holder.appendChild(h("div", { class: "pager" },
        h("button", { class: "ghost", disabled: page === 0, onclick: function () { page--; list(); } }, "← previous"),
        h("span", { class: "muted", text: "page " + (page + 1) + " of " + pages }),
        h("button", { class: "ghost", disabled: page >= pages - 1, onclick: function () { page++; list(); } }, "next →")));
    }
    list();
  }
  function sampleCard(x, open) {
    var chips = h("span", { class: "chips" });
    Object.keys(x.scores).slice(0, 6).forEach(function (k) {
      var sc = x.scores[k];
      if (sc.value === null) return;
      chips.appendChild(h("span", { class: "chip" + (sc.passed === false ? " bad" : sc.passed === true ? " good" : ""), text: k + " " + fmt(sc.value, 2) }));
    });
    if (x.target_error) chips.appendChild(h("span", { class: "chip bad", text: "target error" }));
    var det = h("details", { class: "sample", open: open }, h("summary", null, h("span", { class: "sid", text: x.id }), h("span", { class: "preview", text: text(x.input).slice(0, 160) }), chips));
    det.addEventListener("toggle", function () {
      if (!det.open || det.dataset.built) return;
      det.dataset.built = "1";
      var body = h("div", { class: "body" });
      if (x.target_error) body.appendChild(field("Target error", x.target_error));
      if (x.input !== undefined) body.appendChild(field("Input", x.input));
      if (x.output !== undefined) body.appendChild(field("Output", x.output));
      if (x.expected !== undefined && x.expected !== null) body.appendChild(field("Expected", x.expected));
      if (x.repeats && x.repeats.length) body.appendChild(field("Repeated outputs", x.repeats.map(text).join("\n───\n")));
      if (x.tags.length) body.appendChild(h("div", { class: "chips" }, x.tags.map(function (t) { return h("span", { class: "chip", text: t }); })));
      var t = h("table", null, h("tr", null, h("th", { text: "metric" }), h("th", { class: "num", text: "value" }), h("th", { text: "explanation" })));
      Object.keys(x.scores).forEach(function (k) {
        var sc = x.scores[k];
        var why = sc.error ? "error: " + sc.error : sc.skipped ? "skipped: " + (sc.reason || "") : (sc.reason || "");
        var tdWhy = h("td", { class: "small" }, why);
        var d = sc.details || {};
        if (d.claims && d.claims.length) {
          var ct = h("table", { class: "claims" });
          d.claims.forEach(function (c) { ct.appendChild(h("tr", null, h("td", { class: c.supported ? "pass" : "fail", text: c.supported ? "✓" : "✕" }), h("td", { text: c.claim }), h("td", { class: "num muted", text: fmt(c.support, 2) }))); });
          add(tdWhy, ct);
        } else if (Object.keys(d).length) {
          add(tdWhy, h("pre", { class: "text small", text: text(d) }));
        }
        t.appendChild(h("tr", null, h("td", { text: k }), h("td", { class: "num " + (sc.passed === false ? "fail" : sc.passed === true ? "pass" : ""), text: fmt(sc.value) }), tdWhy));
      });
      body.appendChild(t);
      det.appendChild(body);
    });
    if (open) det.dispatchEvent(new Event("toggle"));
    return det;
  }
  function field(label, value) {
    return h("div", { class: "field" }, h("div", { class: "label", text: label }), h("div", { class: "text", text: text(value) }));
  }

  // ── comparison ───────────────────────────────────────────────────────────
  function compareView() {
    var C = D.comparison;
    main.appendChild(h("div", { class: "meta" },
      h("span", null, "Baseline: ", h("b", { text: (C.run_a.name || "") + " · " + C.run_a.run_id })),
      h("span", null, "Candidate: ", h("b", { text: (C.run_b.name || "") + " · " + C.run_b.run_id })),
      h("span", null, "Shared samples: ", h("b", { text: C.common_samples })),
      h("span", null, C.same_data ? "same inputs and references" : "⚠ different datasets: only shared ids are compared")));
    var names = Object.keys(C.metrics);
    // one axis: only metrics on a 0–1 scale share the plot; others (latency, tokens, cost) are in the table
    var rows = names.map(function (n) { return C.metrics[n]; }).filter(function (d) {
      return d.delta !== null && [d.a, d.b].every(function (v) { return v !== null && v >= -1 && v <= 1; });
    });
    var offScale = names.filter(function (n) { return rows.indexOf(C.metrics[n]) < 0 && C.metrics[n].delta !== null; });
    // forest plot
    var W = 760, rowH = 28, P = { l: 170, r: 150, t: 24, b: 30 }, H = P.t + P.b + rows.length * rowH;
    var ext = 0.05;
    rows.forEach(function (d) { [d.delta, d.ci_low, d.ci_high].forEach(function (v) { if (v !== null) ext = Math.max(ext, Math.abs(v)); }); });
    ext *= 1.1;
    var iw = W - P.l - P.r;
    function X(v) { return P.l + (v + ext) / (2 * ext) * iw; }
    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, class: "chart", role: "img", "aria-label": "Change per metric with 95% confidence interval" });
    svg.style.maxWidth = W + "px";
    [-ext, -ext / 2, 0, ext / 2, ext].forEach(function (v) {
      svg.appendChild(s("line", { x1: X(v), x2: X(v), y1: P.t - 6, y2: H - P.b, class: v === 0 ? "axis" : "grid-line", "stroke-width": v === 0 ? 1.5 : 1 }));
      svg.appendChild(s("text", { x: X(v), y: H - 10, "text-anchor": "middle", text: (v > 0 ? "+" : "") + fmt(v, 2) }));
    });
    svg.appendChild(s("text", { x: P.l, y: 12, text: "← candidate lower" }));
    svg.appendChild(s("text", { x: W - P.r, y: 12, "text-anchor": "end", text: "candidate higher →" }));
    rows.forEach(function (d, i) {
      var y = P.t + i * rowH + rowH / 2;
      var color = d.direction === "improved" ? "var(--div-pos)" : d.direction === "regressed" ? "var(--div-neg)" : "var(--text-muted)";
      svg.appendChild(s("text", { x: P.l - 10, y: y + 4, "text-anchor": "end", text: d.metric + (d.higher_is_better ? " ↑" : " ↓") }));
      if (d.ci_low !== null && d.ci_high !== null) svg.appendChild(s("line", { x1: X(d.ci_low), x2: X(d.ci_high), y1: y, y2: y, stroke: color, "stroke-width": 2, "stroke-linecap": "round" }));
      var dot = s("circle", { cx: X(d.delta), cy: y, r: 5.5, fill: color, stroke: "var(--surface-1)", "stroke-width": 2 });
      hover(dot, [d.metric + ": " + d.direction, "Δ " + fmt(d.delta) + (d.ci_low !== null ? "  [" + fmt(d.ci_low) + ", " + fmt(d.ci_high) + "]" : ""), "before " + fmt(d.a) + " → after " + fmt(d.b), d.p_adjusted !== null ? "p (Holm) " + fmt(d.p_adjusted, 4) + " · wins/losses " + d.wins + "/" + d.losses : "corpus metric: no per-sample test"]);
      svg.appendChild(dot);
      var label = { improved: "▲ improved", regressed: "▼ regressed", unchanged: "= unchanged", inconclusive: "· inconclusive", changed: "~ changed (untested)" }[d.direction];
      svg.appendChild(s("text", { x: W - P.r + 10, y: y + 4, text: label }));
    });
    main.appendChild(h("div", { class: "card" }, h("h2", null, "What moved"), h("div", { class: "legend" },
      h("span", null, h("span", { class: "swatch", style: null }), "dot: mean change (candidate − baseline); line: 95% paired-bootstrap interval"),
      h("span", null, "▲ blue improved · ▼ red regressed (significant after Holm correction) · gray: not significant")), svg,
      offScale.length ? h("div", { class: "muted small", text: "On other scales, in the table below: " + offScale.join(", ") }) : null));
    var t = h("table", null, h("tr", null, ["metric", "before", "after", "Δ", "95% CI", "p (Holm)", "effect", "wins / losses / ties", ""].map(function (c, i) { return h("th", { class: i && i < 8 ? "num" : "", text: c }); })));
    names.forEach(function (n) {
      var d = C.metrics[n];
      t.appendChild(h("tr", null, h("td", { text: n }), h("td", { class: "num", text: fmt(d.a) }), h("td", { class: "num", text: fmt(d.b) }), h("td", { class: "num", text: fmt(d.delta) }),
        h("td", { class: "num", text: d.ci_low !== null ? fmt(d.ci_low) + " – " + fmt(d.ci_high) : "–" }), h("td", { class: "num", text: fmt(d.p_adjusted, 4) }), h("td", { class: "num", text: fmt(d.effect_size, 2) }),
        h("td", { class: "num", text: d.level === "sample" ? d.wins + " / " + d.losses + " / " + d.ties : "–" }),
        h("td", { class: d.direction === "improved" ? "pass" : d.direction === "regressed" ? "fail" : "muted", text: d.direction })));
    });
    main.appendChild(h("div", { class: "card", style: null }, t));
    if (C.pairwise) {
      var p = C.pairwise;
      main.appendChild(h("div", { class: "card" }, h("h2", null, "Head to head (" + p.criterion + ", judged by " + p.judge + ")"),
        h("div", { class: "meta" }, "candidate win rate ", h("b", { text: pct(p.win_rate) }), " (95% CI " + pct(p.ci_low) + "–" + pct(p.ci_high) + ") · candidate wins " + p.b_wins + " · baseline wins " + p.a_wins + " · ties " + p.ties + " · order-swap consistency " + pct(p.position_consistency))));
    }
    [["regressions", "Biggest regressions"], ["improvements", "Biggest improvements"]].forEach(function (pair) {
      var list = C[pair[0]] || [];
      if (!list.length) return;
      var card = h("div", { class: "card" }, h("h2", { text: pair[1] }));
      list.forEach(function (r) {
        var det = h("details", { class: "sample" }, h("summary", null, h("span", { class: "sid", text: r.sample_id }), h("span", { class: "preview", text: text(r.input).slice(0, 140) }), h("span", { class: "chip " + (pair[0] === "regressions" ? "bad" : "good"), text: r.metric + " " + fmt(r.a, 2) + " → " + fmt(r.b, 2) })));
        var body = h("div", { class: "body grid two" });
        if (r.output_a !== undefined) { body.appendChild(field("Baseline output", r.output_a)); body.appendChild(field("Candidate output", r.output_b)); }
        det.appendChild(body);
        card.appendChild(det);
      });
      main.appendChild(card);
    });
  }

  // ── about ────────────────────────────────────────────────────────────────
  function about() {
    var r = D.run;
    main.appendChild(h("div", { class: "grid two" },
      h("div", { class: "card" }, h("h2", null, "Manifest"), h("pre", { class: "text", text: text(M) })),
      h("div", { class: "card" }, h("h2", null, "Environment"), h("pre", { class: "text", text: text(r.environment) }), h("h2", null, "Dataset"), h("pre", { class: "text", text: text(r.dataset) }), h("h2", null, "Judge"), h("pre", { class: "text", text: text(r.judge) })),
      h("div", { class: "card" }, h("h2", null, "Configuration"), h("pre", { class: "text", text: text(r.config) }))));
    if (D.limitations.length) D.limitations.forEach(function (l) { main.appendChild(h("div", { class: "note" }, l)); });
  }

  render();
})();
