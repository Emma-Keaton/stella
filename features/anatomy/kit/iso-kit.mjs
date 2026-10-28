// features/anatomy/kit/iso-kit.mjs
// Self-contained isometric SVG kit for Stella's anatomy skill.
// No template literals (for maximum Node.js compatibility).
// Framework-free: only Node stdlib.

var TAU = Math.PI * 2;

var dot3 = function(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; };
var add3 = function(a, b) { return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]; };
var sub3 = function(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; };
var mul3 = function(a, k) { return [a[0] * k, a[1] * k, a[2] * k]; };
var len3 = function(a) { return Math.hypot(a[0], a[1], a[2]); };
var unit3 = function(a) { var l = len3(a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
var cross3 = function(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; };
var lerp3 = function(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; };

function cameraOf(P) {
  var az = P.azimuth || 45;
  var el = P.elevation || 30;
  var sinA = Math.sin(az * Math.PI / 180);
  var cosA = Math.cos(az * Math.PI / 180);
  var sinE = Math.sin(el * Math.PI / 180);
  var cosE = Math.cos(el * Math.PI / 180);
  var k = P.scale || 1;
  return { sinA: sinA, cosA: cosA, sinE: sinE, cosE: cosE, k: k };
}

function iso(point, P) {
  var x = point[0];
  var y = point[1];
  var z = point[2];
  var c = cameraOf(P);
  var rx = x * c.cosA - y * c.sinA;
  var ry = x * c.sinA + y * c.cosA;
  var sx = rx * c.k;
  var sy = (-ry * c.sinE - z * c.cosE) * c.k;
  return [P.cx + sx, P.cy + sy];
}

function fitProjection(points, width, height, opts) {
  opts = opts || {};
  var pad = opts.pad || 30;
  var azimuth = opts.azimuth || 45;
  var elevation = opts.elevation || 30;
  var P = { azimuth: azimuth, elevation: elevation, cx: width / 2, cy: height / 2, scale: 1 };
  var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (var i = 0; i < points.length; i++) {
    var p = points[i];
    var sp = iso([p[0], p[1], p[2]], P);
    minX = Math.min(minX, sp[0]);
    maxX = Math.max(maxX, sp[0]);
    minY = Math.min(minY, sp[1]);
    maxY = Math.max(maxY, sp[1]);
  }
  var spanX = maxX - minX || 1;
  var spanY = maxY - minY || 1;
  var scale = Math.min((width - 2 * pad) / spanX, (height - 2 * pad) / spanY);
  P.scale = scale;
  var cx = width / 2 - (minX + maxX) / 2 * scale;
  var cy = height / 2 - (minY + maxY) / 2 * scale;
  P.cx = cx;
  P.cy = cy;
  return P;
}

function depthOf(p, P) {
  var c = cameraOf(P);
  var rx = p[0] * c.cosA - p[1] * c.sinA;
  var ry = p[0] * c.sinA + p[1] * c.cosA;
  return ry * c.sinE + p[2] * c.cosE;
}

function translateAlong(P, d) {
  var s0 = iso([0, 0, 0], P);
  var s1 = iso([d[0], d[1], d[2]], P);
  return "translate(" + (s1[0] - s0[0]) + ", " + (s1[1] - s0[1]) + ")";
}

function corners(plan, inset) {
  inset = inset || 0;
  var x = plan.x;
  var y = plan.y;
  var w = plan.w;
  var d = plan.d;
  var r = Math.min(plan.r, inset ? 0 : plan.r);
  return [
    [x + inset, y + inset],
    [x + w - inset, y + inset],
    [x + w - inset, y + d - inset],
    [x + inset, y + d - inset]
  ];
}

function boxCorners(plan, z0, z1) {
  var cs = corners(plan);
  var out = [];
  for (var i = 0; i < cs.length; i++) {
    var c = cs[i];
    out.push([c[0], c[1], z0]);
    out.push([c[0], c[1], z1]);
  }
  return out;
}

function insetPlan(plan, inset) {
  return {
    x: plan.x + inset,
    y: plan.y + inset,
    w: plan.w - 2 * inset,
    d: plan.d - 2 * inset,
    r: Math.max(0, plan.r - inset)
  };
}

function planOutline(plan, z, P, strokeW) {
  strokeW = strokeW || 1;
  var cs = corners(plan);
  var pts = [];
  for (var i = 0; i < cs.length; i++) {
    var sp = iso([cs[i][0], cs[i][1], z], P);
    pts.push(sp[0] + "," + sp[1]);
  }
  return "<polygon points=\"" + pts.join(" ") + "\" fill=\"none\" stroke-width=\"" + strokeW + "\"/>";
}

function toneMapValue(tone) {
  var m = { hi: "#e2e8f0", mid: "#94a3b8", lo: "#475569", faint: "#cbd5e1", none: "none" };
  return m[tone] || m.mid;
}

function slabOf(plan, z0, z1, P, strokeW, crease) {
  strokeW = strokeW || 1;
  crease = crease || "mid";
  var cs = corners(plan);
  var top = [];
  var bottom = [];
  for (var i = 0; i < cs.length; i++) {
    top.push(iso([cs[i][0], cs[i][1], z1], P));
    bottom.push(iso([cs[i][0], cs[i][1], z0], P));
  }
  var all = top.concat(bottom);
  var xs = all.map(function(p) { return p[0]; });
  var ys = all.map(function(p) { return p[1]; });
  var minX = Math.min.apply(null, xs);
  var maxX = Math.max.apply(null, xs);
  var minY = Math.min.apply(null, ys);
  var maxY = Math.max.apply(null, ys);
  var points = top.map(function(p) { return p[0] + "," + p[1]; }).join(" ");
  var fill = toneMapValue(crease);
  return "<polygon points=\"" + points + "\" fill=\"" + fill + "\" stroke-width=\"" + strokeW + "\" stroke=\"" + fill + "\"/>";
}

function cylinder(x, y, r, z0, z1, P, sides, crease, lit) {
  sides = sides || 24;
  crease = crease || "mid";
  var top = [];
  var bottom = [];
  for (var i = 0; i <= sides; i++) {
    var a = (i / sides) * TAU;
    top.push(iso([x + r * Math.cos(a), y + r * Math.sin(a), z1], P));
    bottom.push(iso([x + r * Math.cos(a), y + r * Math.sin(a), z0], P));
  }
  var sideTop = top.map(function(p) { return p[0] + "," + p[1]; }).join(" ");
  var sideBottom = bottom.map(function(p) { return p[0] + "," + p[1]; }).join(" ");
  var fillTop = lit ? "#fbbf24" : "#94a3b8";
  var strokeTop = lit ? "#fbbf24" : "#94a3b8";
  var fillBottom = lit ? "#f59e0b" : "#64748b";
  var strokeBottom = lit ? "#f59e0b" : "#64748b";
  var out = [];
  out.push("<polygon points=\"" + sideTop + "\" fill=\"" + fillTop + "\" stroke-width=\"1\" stroke=\"" + strokeTop + "\"/>");
  out.push("<polygon points=\"" + sideBottom + "\" fill=\"" + fillBottom + "\" stroke-width=\"1\" stroke=\"" + strokeBottom + "\"/>");
  return out.join("");
}

function ring(x, y, r, z, P, sides) {
  sides = sides || 24;
  var pts = [];
  for (var i = 0; i <= sides; i++) {
    var a = (i / sides) * TAU;
    pts.push(iso([x + r * Math.cos(a), y + r * Math.sin(a), z], P));
  }
  return "<polyline points=\"" + pts.map(function(p) { return p.join(","); }).join(" ") + "\" fill=\"none\" stroke-width=\"1\" stroke=\"#94a3b8\"/>";
}

function sideArc(x, y, r, z, P, sides) {
  sides = sides || 24;
  var pts = [];
  for (var i = 0; i <= sides / 2; i++) {
    var a = (i / (sides / 2)) * Math.PI;
    pts.push(iso([x + r * Math.cos(a), y, z], P));
  }
  return "<polyline points=\"" + pts.map(function(p) { return p.join(","); }).join(" ") + "\" fill=\"none\" stroke-width=\"1\" stroke=\"#64748b\"/>";
}

function knurl(x, y, r, z0, z1, sides, P, pitch) {
  sides = sides || 24;
  pitch = pitch || 0.3;
  var out = [];
  for (var i = 0; i < sides; i++) {
    var a = (i / sides) * TAU;
    var x1 = x + r * Math.cos(a);
    var y1 = y + r * Math.sin(a);
    var h = pitch * Math.sin(i * 4);
    var p0 = iso([x1, y1, z0 + h], P);
    var p1 = iso([x1, y1, z1 - h], P);
    out.push("<line x1=\"" + p0[0] + "\" y1=\"" + p0[1] + "\" x2=\"" + p1[0] + "\" y2=\"" + p1[1] + "\" stroke=\"#475569\" stroke-width=\"0.6\"/>");
  }
  return out.join("");
}

function haloOf(plan, z0, z1, P) {
  var cs = corners(plan);
  var pts = [];
  for (var i = 0; i < cs.length; i++) {
    pts.push(iso([cs[i][0], cs[i][1], z0], P));
  }
  for (var i = cs.length - 1; i >= 0; i--) {
    pts.push(iso([cs[i][0], cs[i][1], z1], P));
  }
  return pts.map(function(p) { return p.join(","); }).join(" ");
}

function topMatrix(x, y, z, P, anchor) {
  anchor = anchor || "middle";
  var sp = iso([x, y, z], P);
  return "translate(" + sp[0] + ", " + sp[1] + ")";
}

function faceTextSvg(transform, text, opts) {
  opts = opts || {};
  var size = opts.size || 2;
  var tone = opts.tone || "mid";
  var anchor = opts.anchor || "middle";
  var m = { hi: "#f8fafc", mid: "#e2e8f0", lo: "#475569", faint: "#94a3b8" };
  var fill = m[tone] || m.mid;
  return "<text transform=\"" + transform + "\" font-family=\"monospace\" font-size=\"" + size + "\" fill=\"" + fill + "\" text-anchor=\"" + anchor + "\" dominant-baseline=\"middle\">" + text + "</text>";
}

function solidSvg(paths, style) {
  style = style || {};
  var tone = style.tone || "mid";
  var crease = style.crease || "mid";
  var lit = style.lit ? "fill:#fbbf24;stroke:#f59e0b" : "";
  var m = { hi: "#f8fafc", mid: "#94a3b8", lo: "#475569", faint: "#cbd5e1", none: "none" };
  var fill = m[tone] || m.mid;
  var creaseFill = m[crease] || m.mid;
  return "<g " + lit + "><path d=\"" + paths + "\" fill=\"" + fill + "\" stroke=\"" + creaseFill + "\" stroke-width=\"0.8\"/></g>";
}

function lineSvg(d, style) {
  style = style || {};
  var tone = style.tone || "mid";
  var m = { hi: "#f8fafc", mid: "#94a3b8", lo: "#475569", faint: "#cbd5e1", none: "none" };
  return "<path d=\"" + d + "\" fill=\"none\" stroke=\"" + m[tone] || m.mid + "\" stroke-width=\"" + (style.strokeWidth || 1) + "\"/>";
}

function dotsSvg(points, opts) {
  opts = opts || {};
  var size = opts.size || 0.5;
  var tone = opts.tone || "mid";
  var m = { hi: "#f8fafc", mid: "#94a3b8", lo: "#475569", faint: "#94a3b8" };
  return points.map(function(p) {
    return "<circle cx=\"" + p[0] + "\" cy=\"" + p[1] + "\" r=\"" + size + "\" fill=\"" + m[tone] || m.mid + "\"/>";
  }).join("");
}

function figureSvg(opts) {
  opts = opts || {};
  var width = opts.width || 600;
  var height = opts.height || 380;
  var label = opts.label || "Fig 1";
  var body = opts.body || [];
  var pad = opts.pad || 30;
  var P = { azimuth: 45, elevation: 30, cx: width / 2, cy: height / 2, scale: 1 };
  var svg = "<svg width=\"" + width + "\" height=\"" + height + "\" viewBox=\"0 0 " + width + " " + height + "\" xmlns=\"http://www.w3.org/2000/svg\" class=\"iso-stage\">";
  svg += "<defs><filter id=\"blur\" x=\"-50%\" y=\"-50%\" width=\"200%\" height=\"200%\"><feGaussianBlur in=\"SourceGraphic\" stdDeviation=\"4\"/></filter></defs>";
  svg += "<rect width=\"" + width + "\" height=\"" + height + "\" fill=\"#0c0d14\"/>";
  svg += "<g class=\"figure\">" + body.join("") + "</g>";
  svg += "<text x=\"" + pad + "\" y=\"" + (pad + 18) + "\" font-family=\"monospace\" font-size=\"14\" fill=\"#e2e8f0\" font-weight=\"bold\">" + label + "</text>";
  svg += "</svg>";
  return svg;
}

function plateHtml(opts) {
  opts = opts || {};
  var fig = opts.fig || "Fig 1";
  var title = opts.title || "";
  var hint = opts.hint || "";
  var readout = opts.readout || "";
  var keys = opts.keys || [];
  var caption = opts.caption || "";
  var body = opts.body || "";
  var keyHtml = keys.map(function(k) {
    var bg = k.mark === "lit" ? "#fbbf24" : "#94a3b8";
    return '<div class="key"><span class="mark" style="background:' + bg + ';"></span> ' + k.label + "</div>";
  }).join("");
  return "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>" + title + "</title>" +
    "<style>" +
    "body{font-family:system-ui,sans-serif;background:#0c0d14;color:#e2e8f0;margin:0;padding:24px;}" +
    ".card{background:#161826;border:1px solid #334155;border-radius:8px;padding:20px;max-width:900px;margin:0 auto;}" +
    ".fig{font-size:10px;color:#94a3b8;margin-bottom:4px;}" +
    ".title{font-size:18px;font-weight:700;margin:0 0 8px 0;}" +
    ".hint{font-size:12px;color:#94a3b8;margin-bottom:12px;}" +
    ".readout{font-family:monospace;font-size:13px;color:#fbbf24;margin-bottom:16px;}" +
    ".keys{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;}" +
    ".key{display:flex;align-items:center;gap:6px;font-size:12px;color:#cbd5e1;}" +
    ".mark{width:10px;height:10px;border-radius:2px;}" +
    ".caption{font-size:13px;color:#94a3b8;line-height:1.5;}" +
    ".iso-stage{display:block;max-width:100%;height:auto;}" +
    "</style></head><body><div class=\"card\">" +
    "<div class=\"fig\">" + fig + "</div>" +
    "<div class=\"title\">" + title + "</div>" +
    "<div class=\"hint\">" + hint + "</div>" +
    "<div class=\"readout\">" + readout + "</div>" +
    "<div class=\"keys\">" + keyHtml + "</div>" +
    body +
    "<div class=\"caption\">" + caption + "</div>" +
    "</div></body></html>";
}

function pageHtml(opts) {
  opts = opts || {};
  var title = opts.title || "";
  var theme = opts.theme || "dark";
  var body = opts.body || "";
  var script = opts.script || "";
  var bg = theme === "light" ? "#f4f3ef" : "#0c0d14";
  var fg = theme === "light" ? "#0c0d14" : "#e2e8f0";
  return "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>" + title + "</title>" +
    "<style>body{font-family:system-ui,sans-serif;background:" + bg + ";color:" + fg + ";margin:0;padding:24px;}.iso-stage{display:block;max-width:100%;height:auto;}</style>" +
    "</head><body>" + body + "<script>" + script + "</script></body></html>";
}

function kitScript() {
  return "document.addEventListener('DOMContentLoaded', function() { var stage = document.querySelector('.iso-stage'); if (!stage) return; var observer = new IntersectionObserver(function(entries) { stage.classList.toggle('visible', entries[0].isIntersecting); }, { rootMargin: '120px 0px' }); observer.observe(stage); });";
}

function topTicks(x0, x1, count, spacing, y, z, bands, P) {
  var minor = [];
  var major = [];
  var step = (x1 - x0) / count;
  for (var i = 0; i <= count; i++) {
    var x = x0 + i * step;
    var sp = iso([x, y, z], P);
    var d = "M" + (sp[0] - 2) + "," + (sp[1] - 2) + "L" + (sp[0] + 2) + "," + (sp[1] + 2);
    (i % bands[0] === 0 ? major : minor).push(d);
  }
  return { minor: minor.join(""), major: major.join("") };
}

function radialTicks(x, y, r, count, start, z, bands, P) {
  var minor = [];
  var major = [];
  for (var i = 0; i <= count; i++) {
    var a = (i / count) * TAU;
    var x1 = x + r * Math.cos(a);
    var y1 = y + r * Math.sin(a);
    var sp = iso([x1, y1, z], P);
    var d = "M" + sp[0] + "," + sp[1] + "L" + (sp[0] + Math.cos(a) * 4) + "," + (sp[1] - Math.sin(a) * 4);
    (i % bands[0] === 0 ? major : minor).push(d);
  }
  return { minor: minor.join(""), major: major.join("") };
}

function lineOnTop(p0, p1, z, P) {
  var sp0 = iso([p0[0], p0[1], z], P);
  var sp1 = iso([p1[0], p1[1], z], P);
  return "M" + sp0[0] + "," + sp0[1] + "L" + sp1[0] + "," + sp1[1];
}

export {
  dot3, add3, sub3, mul3, len3, unit3, cross3, lerp3,
  cameraOf, iso, fitProjection, depthOf, translateAlong,
  corners, boxCorners, insetPlan, planOutline,
  slabOf, cylinder, ring, sideArc, knurl,
  haloOf, topMatrix, faceTextSvg,
  solidSvg, lineSvg, dotsSvg,
  figureSvg, plateHtml, pageHtml, kitScript,
  topTicks, radialTicks, lineOnTop
};
