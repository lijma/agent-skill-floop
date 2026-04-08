"""floop preview — index page generator for the local preview server.

Generates a Figma-style navigation shell (index.html) in .floop/build/
that lists all HTML artefacts in a sidebar, grouped by category, and
renders the selected file in a full-height iframe.
"""

from __future__ import annotations

import csv
import html as html_mod
import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CATEGORY_ORDER = ["Design System", "Components", "Prototypes"]

_CATEGORY_ICONS = {
    "Design System": "◈",
    "Components": "⬡",
    "Prototypes": "▣",
}

# Keywords used to classify filenames into categories
_DESIGN_SYSTEM_KEYWORDS = (
    "token", "color", "colour", "typography", "design-system",
    "spacing", "palette", "theme",
)
_COMPONENT_KEYWORDS = (
    "component", "widget", "button", "card", "form", "input",
    "modal", "dialog", "badge", "chip",
)

# Canonical directory name → category (takes priority over keyword scan)
_DIR_CATEGORY: dict[str, str] = {
    "tokens": "Design System",
    "components": "Components",
    "journey": "Prototypes",
}

_INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>floop preview</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
body { display: flex; height: 100vh; background: #f4f4f5; }

/* ── Sidebar ─────────────────────────────────────────────────── */
.sidebar {
  width: 224px;
  flex-shrink: 0;
  background: #18181b;
  color: #e4e4e7;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid #09090b;
}
.sidebar-header {
  padding: 14px 16px;
  border-bottom: 1px solid #27272a;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.logo { font-size: 15px; font-weight: 700; color: #fff; letter-spacing: -0.4px; }
.badge {
  font-size: 10px; background: #3f3f46; color: #a1a1aa;
  padding: 2px 6px; border-radius: 4px; font-weight: 500; letter-spacing: 0.2px;
}
.sidebar-nav { flex: 1; overflow-y: auto; padding: 8px 0; }
.sidebar-nav::-webkit-scrollbar { width: 4px; }
.sidebar-nav::-webkit-scrollbar-track { background: transparent; }
.sidebar-nav::-webkit-scrollbar-thumb { background: #3f3f46; border-radius: 2px; }
.nav-section { margin-bottom: 4px; }
.nav-section-title {
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.8px; color: #52525b; padding: 10px 16px 4px;
}
.nav-item {
  display: flex; align-items: center; gap: 8px; padding: 7px 16px;
  cursor: pointer; color: #a1a1aa; font-size: 13px;
  transition: background 0.1s, color 0.1s;
  border-left: 2px solid transparent; user-select: none;
}
.nav-item:hover { background: #27272a; color: #e4e4e7; }
.nav-item.active { background: #27272a; color: #fff; border-left-color: #6366f1; }
.nav-item .icon { font-size: 12px; flex-shrink: 0; opacity: 0.7; }
.nav-item .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.domain-count {
  font-size: 10px; background: #3f3f46; color: #71717a;
  padding: 1px 5px; border-radius: 10px; flex-shrink: 0;
}
.nav-folder-header {
  display: flex; align-items: center; gap: 8px; padding: 7px 16px;
  cursor: pointer; color: #a1a1aa; font-size: 13px;
  transition: background 0.1s, color 0.1s;
  border-left: 2px solid transparent; user-select: none;
}
.nav-folder-header:hover { background: #27272a; color: #e4e4e7; }
.nav-folder-header.active { background: #27272a; color: #fff; border-left-color: #6366f1; }
.folder-toggle {
  margin-left: auto; font-size: 11px; opacity: 0.5;
  transition: transform 0.2s; flex-shrink: 0; line-height: 1;
}
.nav-folder.collapsed .folder-toggle { transform: rotate(-90deg); }
.nav-folder-children { overflow: hidden; }
.nav-folder.collapsed .nav-folder-children { display: none; }
.nav-child { padding-left: 28px; }
.sidebar-footer {
  padding: 10px 16px; border-top: 1px solid #27272a;
  font-size: 11px; color: #3f3f46; flex-shrink: 0;
}
.version-select {
  background: #3f3f46; border: 1px solid #52525b; color: #a1a1aa;
  font-size: 10px; border-radius: 4px; padding: 2px 5px;
  cursor: pointer; outline: none; max-width: 90px;
}
.version-select:focus { border-color: #6366f1; color: #e4e4e7; }
.readonly-banner {
  display: none; background: #78350f; color: #fef3c7;
  font-size: 11px; padding: 3px 12px; text-align: center;
  flex-shrink: 0; letter-spacing: 0.2px;
}

/* ── Main ────────────────────────────────────────────────────── */
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
.toolbar {
  height: 44px; background: #fff; border-bottom: 1px solid #e4e4e7;
  display: flex; align-items: center; padding: 0 12px; position: relative; flex-shrink: 0;
}
.breadcrumb {
  font-size: 13px; color: #71717a; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0;
}
.breadcrumb b { color: #18181b; font-weight: 600; }
.toolbar-controls {
  display: none; align-items: center; gap: 4px;
  position: absolute; left: 50%; transform: translateX(-50%);
}
/* ── Device selector (flat buttons) ─────────────────────────── */
.dv-btns { display: flex; gap: 2px; }
.dv-btn {
  display: flex; align-items: center; gap: 4px;
  background: none; border: 1px solid #e4e4e7; border-radius: 6px;
  padding: 3px 8px; cursor: pointer; font-size: 12px; color: #52525b;
  transition: background 0.1s, border-color 0.1s, color 0.1s; white-space: nowrap;
  line-height: 1.5;
}
.dv-btn:hover { background: #f4f4f5; border-color: #d4d4d8; color: #18181b; }
.dv-btn.active { background: #18181b; color: #fff; border-color: #18181b; }
.dv-btn.active svg { stroke: #fff; }
.toolbar-sep { color: #d4d4d8; font-size: 13px; padding: 0 2px; user-select: none; }
.page-select {
  font-size: 12px; background: #fff; border: 1px solid #e4e4e7;
  border-radius: 6px; color: #18181b; padding: 4px 6px; cursor: pointer;
  max-width: 180px; outline: none;
}
.page-select:focus { border-color: #6366f1; }
.fullscreen-btn {
  display: flex; align-items: center; justify-content: center;
  background: none; border: 1px solid #e4e4e7; border-radius: 6px;
  color: #71717a; width: 30px; height: 28px; cursor: pointer;
  transition: background 0.1s, color 0.1s;
}
.fullscreen-btn:hover { background: #f4f4f5; color: #18181b; }
/* hide sidebar when fullscreen */
body.is-fullscreen .sidebar { display: none; }

/* ── Frame area ──────────────────────────────────────────────── */
.frame-wrap {
  flex: 1; overflow: auto; position: relative;
  display: flex; align-items: flex-start; justify-content: center;
  transition: background 0.3s;
}
.frame-wrap.mode-full { background: #fff; align-items: stretch; }
.frame-wrap.mode-full > #preview-frame {
  border: none; background: #fff; width: 100%; display: block;
}
.frame-wrap.mode-phone { background: #18181b; padding: 40px 24px 56px; }
.frame-wrap.mode-tablet { background: #18181b; padding: 32px 24px 48px; }
.frame-wrap.mode-web {
  background: linear-gradient(160deg, #1e293b 0%, #0f172a 100%);
  padding: 32px 40px 56px;
}
/* Shared screen viewport (phone, tablet, web) */
.screen-viewport { overflow: hidden; background: #fff; position: relative; }
.screen-viewport iframe { border: none; display: block; background: #fff; width: 100%; height: 100%; }

/* ── Phone shell ─────────────────────────────────────────────── */
.device-phone {
  width: 436px; background: #1c1c1e; border-radius: 54px;
  padding: 48px 23px 44px;
  box-shadow: inset 0 0 0 2px #3a3a3c, 0 0 0 1px #000, 0 32px 96px rgba(0,0,0,0.7);
  position: relative; flex-shrink: 0;
}
.device-phone::before { /* volume buttons left */
  content: ''; position: absolute; left: -4px; top: 156px;
  width: 4px; height: 34px; background: #3a3a3c; border-radius: 2px 0 0 2px;
  box-shadow: 0 52px 0 #3a3a3c, 0 100px 0 #3a3a3c;
}
.device-phone::after { /* power button right */
  content: ''; position: absolute; right: -4px; top: 204px;
  width: 4px; height: 70px; background: #3a3a3c; border-radius: 0 2px 2px 0;
}
.device-phone .notch {
  position: absolute; top: 16px; left: 50%; transform: translateX(-50%);
  width: 128px; height: 36px; background: #000; border-radius: 0 0 24px 24px; z-index: 10;
}
.device-phone .screen-viewport { width: 390px; height: 844px; border-radius: 40px; }
.device-phone .home-bar {
  position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
  width: 140px; height: 5px; background: rgba(255,255,255,0.3); border-radius: 3px;
}

/* ── Tablet shell ────────────────────────────────────────────── */
.device-tablet {
  width: min(808px, calc(100% - 48px)); background: #1c1c1e; border-radius: 28px;
  padding: 39px 20px 56px;
  box-shadow: inset 0 0 0 2px #3a3a3c, 0 0 0 1px #000, 0 24px 72px rgba(0,0,0,0.6);
  position: relative; flex-shrink: 0;
}
.device-tablet::before { /* top/lock button */
  content: ''; position: absolute; top: -4px; right: 130px;
  height: 4px; width: 52px; background: #3a3a3c; border-radius: 2px 2px 0 0;
}
.device-tablet::after { /* volume right */
  content: ''; position: absolute; right: -4px; top: 80px;
  width: 4px; height: 48px; background: #3a3a3c; border-radius: 0 2px 2px 0;
  box-shadow: 0 64px 0 #3a3a3c;
}
.device-tablet .camera {
  position: absolute; top: 15px; left: 50%; transform: translateX(-50%);
  width: 10px; height: 10px; background: #3a3a3c; border-radius: 50%;
}
.device-tablet .screen-viewport { width: 100%; aspect-ratio: 768 / 600; height: auto; border-radius: 4px; }
.device-tablet .home-circle {
  position: absolute; bottom: 17px; left: 50%; transform: translateX(-50%);
  width: 36px; height: 36px; border: 2px solid #3a3a3c; border-radius: 50%;
}

/* ── Web / Desktop shell ─────────────────────────────────────── */
.device-web {
  width: 100%; max-width: 1440px; flex-shrink: 0;
  display: flex; flex-direction: column; align-items: center;
}
.device-web .win-frame {
  width: 100%; background: #1c1c1e; border-radius: 10px 10px 0 0;
  box-shadow: 0 0 0 2px #3a3a3c, 0 24px 60px rgba(0,0,0,0.5);
  overflow: hidden;
}
.device-web .win-chrome {
  height: 36px; background: #27272a; display: flex; align-items: center;
  padding: 0 14px; gap: 7px; border-bottom: 1px solid #3f3f46; flex-shrink: 0;
}
.device-web .win-dot { width: 12px; height: 12px; border-radius: 50%; }
.device-web .win-urlbar {
  flex: 1; height: 22px; background: #3f3f46; border-radius: 5px;
  margin: 0 16px; max-width: 460px;
}
.device-web .screen-viewport { width: 100%; height: calc(100vh - 215px); min-height: 480px; }
.device-web .win-stand {
  width: 180px; height: 28px; background: #27272a;
  clip-path: polygon(8% 0%, 92% 0%, 100% 100%, 0% 100%);
}
.device-web .win-base { width: 300px; height: 14px; background: #27272a; border-radius: 0 0 8px 8px; }

/* ── Welcome ─────────────────────────────────────────────────── */
.welcome {
  display: flex; align-items: center; justify-content: center;
  height: 100%; flex-direction: column; gap: 16px; padding: 32px;
}
.welcome-icon { font-size: 52px; opacity: 0.25; line-height: 1; }
.welcome h2 { font-size: 20px; color: #18181b; font-weight: 600; }
.welcome p {
  font-size: 14px; color: #71717a; max-width: 360px;
  text-align: center; line-height: 1.7;
}
.welcome code {
  background: #e4e4e7; padding: 2px 7px; border-radius: 4px;
  font-size: 13px; font-family: ui-monospace, 'SF Mono', Menlo, monospace;
  color: #18181b;
}
</style>
</head>
<body>
<div class="sidebar">
  <div class="sidebar-header">
    <div class="logo">floop</div>
    <select id="version-select" class="version-select" aria-label="Version">
<!-- VERSION_OPTIONS -->
    </select>
  </div>
  <div class="sidebar-nav" id="sidebar-nav">
<!-- VERSION_NAV -->
<!-- SITEMAP_NAV -->
<!-- SIDEBAR_NAV -->
  </div>
  <div class="sidebar-footer">floop &middot; local preview</div>
</div>
<div class="main">
  <div class="readonly-banner" id="readonly-banner">Viewing archived version — read only</div>
  <div class="toolbar">
    <span class="breadcrumb" id="breadcrumb">Select a page</span>
    <div class="toolbar-controls" id="toolbar-controls">
      <div class="dv-btns">
        <button class="dv-btn active" data-size="web">
          <svg width="13" height="13" viewBox="0 0 15 15" fill="none"><rect x="1" y="2" width="13" height="9" rx="1" stroke="currentColor" stroke-width="1.3"/><path d="M5 13h5M7.5 11v2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
          Web
        </button>
        <button class="dv-btn" data-size="phone">
          <svg width="10" height="13" viewBox="0 0 15 15" fill="none"><rect x="4.5" y="1" width="6" height="13" rx="1.5" stroke="currentColor" stroke-width="1.3"/><circle cx="7.5" cy="12" r="0.9" fill="currentColor"/></svg>
          Phone
        </button>
        <button class="dv-btn" data-size="tablet">
          <svg width="11" height="13" viewBox="0 0 15 15" fill="none"><rect x="2" y="1" width="11" height="13" rx="1.5" stroke="currentColor" stroke-width="1.3"/><circle cx="7.5" cy="12" r="0.9" fill="currentColor"/></svg>
          Tablet
        </button>
      </div>
      <span class="toolbar-sep">/</span>
      <select id="page-select" class="page-select" aria-label="Page"></select>
      <button id="fullscreen-btn" class="fullscreen-btn" title="Fullscreen"><svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 5V2h3M9 2h3v3M12 9v3H9M5 12H2V9" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
    </div>
  </div>
  <div class="frame-wrap mode-full" id="frame-wrap">
<!-- FRAME_AREA -->
  </div>
</div>
<script>
// DOMAINS_DATA
// VERSIONS_DATA
// CHANGEHISTORY_DATA
var _first = null;
// FIRST_ITEM
var _currentDevice = 'web';
var _currentDomain = null;
// ACTIVE_VERSION
var _fsEnterSvg = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 5V2h3M9 2h3v3M12 9v3H9M5 12H2V9" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>';
var _fsExitSvg = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 2v3H2M9 2v3h3M9 12v-3h3M5 12v-3H2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>';

function _versionUrl(relUrl) {
  if (_activeVersion === 'trunk') return relUrl;
  return '/versions/' + _activeVersion + '/' + relUrl;
}

document.getElementById('version-select').addEventListener('change', function() {
  _activeVersion = this.value;
  var readonly = _activeVersion !== 'trunk';
  document.getElementById('readonly-banner').style.display = readonly ? 'block' : 'none';
  if (_currentDomain) {
    var domainEl = document.getElementById('domain-' + _currentDomain);
    loadDomain(_currentDomain, domainEl);
  }
});

document.getElementById('toolbar-controls').addEventListener('click', function(e) {
  var btn = e.target.closest('.dv-btn');
  if (!btn) return;
  _currentDevice = btn.dataset.size;
  document.querySelectorAll('.dv-btn').forEach(function(b) { b.classList.remove('active'); });
  btn.classList.add('active');
  applyDeviceSize(_currentDevice);
});

function _mkEl(tag, cls) {
  var el = document.createElement(tag);
  if (cls) el.className = cls;
  return el;
}

function _mkFrame(src) {
  var f = document.createElement('iframe');
  f.id = 'preview-frame';
  f.src = src;
  f.style.border = 'none';
  f.style.display = 'block';
  f.style.background = '#fff';
  return f;
}

function _renderDevice(wrap, size, src) {
  wrap.className = 'frame-wrap';
  wrap.innerHTML = '';
  if (size === 'full' || !size) {
    wrap.classList.add('mode-full');
    if (src) wrap.appendChild(_mkFrame(src));
    return;
  }
  var screen = _mkEl('div', 'screen-viewport');
  screen.id = 'screen-viewport';
  if (src) screen.appendChild(_mkFrame(src));
  if (size === 'phone') {
    wrap.classList.add('mode-phone');
    var sh = _mkEl('div', 'device-phone');
    sh.appendChild(_mkEl('div', 'notch'));
    sh.appendChild(screen);
    sh.appendChild(_mkEl('div', 'home-bar'));
    wrap.appendChild(sh);
  } else if (size === 'tablet') {
    wrap.classList.add('mode-tablet');
    var sh = _mkEl('div', 'device-tablet');
    sh.appendChild(_mkEl('div', 'camera'));
    sh.appendChild(screen);
    sh.appendChild(_mkEl('div', 'home-circle'));
    wrap.appendChild(sh);
  } else {
    wrap.classList.add('mode-web');
    var web = _mkEl('div', 'device-web');
    var wf = _mkEl('div', 'win-frame');
    var wc = _mkEl('div', 'win-chrome');
    var d1 = _mkEl('div', 'win-dot'); d1.style.background = '#ff5f57';
    var d2 = _mkEl('div', 'win-dot'); d2.style.background = '#febc2e';
    var d3 = _mkEl('div', 'win-dot'); d3.style.background = '#28c840';
    wc.appendChild(d1); wc.appendChild(d2); wc.appendChild(d3);
    wc.appendChild(_mkEl('div', 'win-urlbar'));
    wf.appendChild(wc);
    wf.appendChild(screen);
    web.appendChild(wf);
    web.appendChild(_mkEl('div', 'win-stand'));
    web.appendChild(_mkEl('div', 'win-base'));
    wrap.appendChild(web);
  }
}

function applyDeviceSize(size) {
  var wrap = document.getElementById('frame-wrap');
  var existingFrame = document.getElementById('preview-frame');
  _renderDevice(wrap, size, existingFrame ? existingFrame.src : null);
}

document.getElementById('page-select').addEventListener('change', function() {
  var url = this.value;
  var name = this.options[this.selectedIndex] ? this.options[this.selectedIndex].textContent : url;
  if (url) loadPageInFrame(_versionUrl(url), name, true);
});

document.getElementById('fullscreen-btn').addEventListener('click', function() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(function() {});
  } else {
    document.exitFullscreen().catch(function() {});
  }
});

document.addEventListener('fullscreenchange', function() {
  var btn = document.getElementById('fullscreen-btn');
  if (!btn) return;
  if (document.fullscreenElement) {
    btn.innerHTML = _fsExitSvg;
    btn.title = 'Exit fullscreen';
    document.body.classList.add('is-fullscreen');
  } else {
    btn.innerHTML = _fsEnterSvg;
    btn.title = 'Fullscreen';
    document.body.classList.remove('is-fullscreen');
  }
});

document.getElementById('sidebar-nav').addEventListener('click', function(e) {
  if (e.target.closest('.folder-toggle')) {
    var h = e.target.closest('.nav-folder-header');
    if (h) document.getElementById(h.dataset.folder).classList.toggle('collapsed');
    return;
  }
  var fh = e.target.closest('.nav-folder-header');
  if (fh) {
    if (fh.dataset.domain) { loadDomain(fh.dataset.domain, fh); return; }
    if (fh.dataset.type === 'ds') { loadDsPage(fh.dataset.url, fh.dataset.name, fh); return; }
    if (fh.dataset.url) { loadPageInFrame(fh.dataset.url, fh.dataset.name, false); setActive(fh); }
    return;
  }
  var item = e.target.closest('.nav-item');
  if (!item) return;
  if (item.dataset.type === 'version-history') { loadVersionHistory(item); return; }
  if (item.dataset.domain) { loadDomain(item.dataset.domain, item); return; }
  if (item.dataset.type === 'ds') { loadDsPage(item.dataset.url, item.dataset.name, item); return; }
  if (item.dataset.url) { loadPageInFrame(item.dataset.url, item.dataset.name, false); setActive(item); }
});

function loadDomain(domainId, el) {
  var pages = _domains[domainId] || [];
  _currentDomain = domainId;
  setActive(el);
  var sel = document.getElementById('page-select');
  sel.innerHTML = '';
  pages.forEach(function(p) {
    var opt = document.createElement('option');
    opt.value = p.url;
    opt.textContent = p.name;
    sel.appendChild(opt);
  });
  var domainName = el && el.querySelector('.name') ? el.querySelector('.name').textContent : domainId;
  document.getElementById('breadcrumb').innerHTML = '<b>' + domainName + '</b>';
  document.getElementById('toolbar-controls').style.display = 'flex';
  if (pages.length > 0) loadPageInFrame(_versionUrl(pages[0].url), pages[0].name, false);
}

function loadVersionHistory(el) {
  _currentDomain = null;
  document.getElementById('breadcrumb').innerHTML = '<b>Version History</b>';
  document.getElementById('toolbar-controls').style.display = 'none';
  var html = '<!DOCTYPE html><html><head><meta charset="utf-8">'
    + '<style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;padding:32px;color:#18181b;max-width:720px}'
    + 'h2{font-size:20px;font-weight:700;margin-bottom:24px;color:#09090b}'
    + '.ver{border:1px solid #e4e4e7;border-radius:8px;padding:16px 20px;margin-bottom:12px}'
    + '.ver-name{font-size:15px;font-weight:600;color:#18181b}'
    + '.ver-date{font-size:12px;color:#71717a;margin-left:8px}'
    + '.ver-msg{font-size:13px;color:#52525b;margin-top:6px}'
    + '.ver-changes{margin-top:10px;padding-left:16px}'
    + '.ver-changes li{font-size:13px;color:#3f3f46;margin-bottom:4px}'
    + '.empty{color:#a1a1aa;font-size:14px}'
    + '</style></head><body><h2>Version History</h2>';
  var versions = (_changeHistory && _changeHistory.versions) ? _changeHistory.versions : [];
  if (!versions.length) {
    html += '<p class="empty">No version history yet. Ask Agent to update _changehistory.json, or run floop version create.</p>';
  } else {
    versions.forEach(function(v) {
      html += '<div class="ver">';
      html += '<span class="ver-name">' + v.version + '</span>';
      if (v.date) html += '<span class="ver-date">' + v.date + '</span>';
      if (v.message) html += '<div class="ver-msg">' + v.message + '</div>';
      if (v.changes && v.changes.length) {
        html += '<ul class="ver-changes">';
        v.changes.forEach(function(c) { html += '<li>' + c + '</li>'; });
        html += '</ul>';
      }
      html += '</div>';
    });
  }
  html += '</body></html>';
  var src = 'data:text/html;charset=utf-8,' + encodeURIComponent(html);
  _renderDevice(document.getElementById('frame-wrap'), 'full', src);
  setActive(el);
}

function loadDsPage(url, name, el) {
  if (!url) return;
  document.getElementById('breadcrumb').innerHTML = '<b>' + name + '</b>';
  document.getElementById('toolbar-controls').style.display = 'none';
  _renderDevice(document.getElementById('frame-wrap'), 'full', url);
  setActive(el);
}

function loadPageInFrame(url, name, syncSelect) {
  document.getElementById('breadcrumb').innerHTML = '<b>' + name + '</b>';
  _renderDevice(document.getElementById('frame-wrap'), _currentDevice, url);
  if (syncSelect) {
    var sel = document.getElementById('page-select');
    for (var i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === url) { sel.selectedIndex = i; break; }
    }
  }
}

function setActive(el) {
  document.querySelectorAll('.nav-item, .nav-folder-header').forEach(function(n) {
    n.classList.remove('active');
  });
  if (el) el.classList.add('active');
}

document.addEventListener('DOMContentLoaded', function() {
  if (_activeVersion !== 'trunk') {
    document.getElementById('readonly-banner').style.display = 'block';
  }
  if (!_first) return;
  if (_first.type === 'version-history') {
    var el = document.getElementById(_first.id);
    loadVersionHistory(el);
  } else if (_first.type === 'ds') {
    var el = document.getElementById(_first.id);
    loadDsPage(_first.url, _first.name, el);
  } else if (_first.domain) {
    var domainEl = document.getElementById('domain-' + _first.domain);
    loadDomain(_first.domain, domainEl);
  } else {
    var el = document.getElementById(_first.id);
    loadPageInFrame(_first.url, _first.name, false);
    if (el) setActive(el);
  }
});
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_preview_index(build_dir: Path, active_version: str = "trunk") -> Path:
    """Generate an index.html navigation shell in *build_dir*.

    If .floop/journey-map.csv is present, builds a Sitemap section at the top
    of the sidebar showing sitemap domains (with device toolbar + page dropdown
    on click).  Design System and Components categories are always shown;
    Prototypes is omitted when journey domains are loaded from the CSV.

    *active_version* sets the initially selected version in the dropdown.

    Returns the path to the generated index.html.
    """
    domains = _load_journey_domains(build_dir)

    categories = _categorize_files(build_dir)
    if domains:
        categories.pop("Prototypes", None)

    sitemap_nav_html, first_from_domains = _build_sitemap_nav_html(domains)
    nav_html, first_from_cats = _build_nav_html(categories, build_dir)

    # Versions + changehistory
    floop_dir = build_dir.parent
    versions = _load_versions(floop_dir)
    changehistory = _load_changehistory(build_dir)

    version_options_html = _build_version_options_html(versions, active_version)
    version_nav_html, first_from_versions = _build_version_nav_html(changehistory)

    # First item: version history > domains > categories
    if first_from_versions is not None:
        first_item = first_from_versions
    elif first_from_domains is not None:
        first_item = first_from_domains
    else:
        first_item = first_from_cats

    first_script = f"_first = {json.dumps(first_item)};" if first_item else ""
    domains_script = f"var _domains = {json.dumps(domains, ensure_ascii=False)};"
    versions_script = f"var _versions = {json.dumps(versions, ensure_ascii=False)};"
    changehistory_script = (
        f"var _changeHistory = {json.dumps(changehistory, ensure_ascii=False)};"
    )
    active_version_script = f"var _activeVersion = {json.dumps(active_version)};"

    frame_area = (
        ""
        if first_item
        else (
            '<div class="welcome">'
            '<div class="welcome-icon">◈</div>'
            "<h2>Nothing here yet</h2>"
            "<p>Run <code>floop token view</code> to generate a design token preview,"
            " then refresh this page.</p>"
            "</div>"
        )
    )

    content = (
        _INDEX_TEMPLATE
        .replace("<!-- VERSION_OPTIONS -->", version_options_html)
        .replace("<!-- VERSION_NAV -->", version_nav_html)
        .replace("<!-- SITEMAP_NAV -->", sitemap_nav_html)
        .replace("<!-- SIDEBAR_NAV -->", nav_html)
        .replace("<!-- FRAME_AREA -->", frame_area)
        .replace("// FIRST_ITEM", first_script)
        .replace("// DOMAINS_DATA", domains_script)
        .replace("// VERSIONS_DATA", versions_script)
        .replace("// CHANGEHISTORY_DATA", changehistory_script)
        .replace("// ACTIVE_VERSION", active_version_script)
    )

    out = build_dir / "index.html"
    out.write_text(content, encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _load_journey_domains(
    build_dir: Path,
) -> dict[str, list[dict[str, str]]]:
    """Read journey-map.csv and return ``{domain: [{page_id, url, name}, ...]}``.

    ``build_dir`` is ``.floop/build``; the CSV is expected at
    ``.floop/journey-map.csv`` (i.e. ``build_dir.parent / "journey-map.csv"``).
    HTML file paths in the CSV are relative to ``.floop/`` (e.g.
    ``build/journey/auth/login.html``); they are converted to URLs relative to
    ``build_dir`` by stripping the leading ``build/`` prefix.

    Returns an empty dict if the CSV is absent or contains no rows.
    """
    csv_path = build_dir.parent / "journey-map.csv"
    if not csv_path.exists():
        return {}

    domains: dict[str, list[dict[str, str]]] = {}
    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            domain = (row.get("domain") or "").strip() or "default"
            html_file = (row.get("html_file") or "").strip()
            if not html_file:
                continue
            try:
                url = Path(html_file).relative_to("build").as_posix()
            except ValueError:
                url = html_file
            raw_title = (row.get("title") or "").strip()
            name = raw_title if raw_title else _display_name(Path(html_file).stem)
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(
                {"page_id": row.get("page_id", ""), "url": url, "name": name}
            )
    return domains


def _load_versions(floop_dir: Path) -> list[dict]:
    """Return version metadata list from .floop/versions/*/meta.json, sorted newest first."""
    versions_dir = floop_dir / "versions"
    if not versions_dir.exists():
        return []
    results = []
    for meta_path in sorted(versions_dir.glob("*/meta.json")):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            results.append(data)
        except (json.JSONDecodeError, KeyError):
            continue
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results


def _load_changehistory(build_dir: Path) -> dict:
    """Read .floop/build/_changehistory.json; return empty dict if absent/invalid."""
    path = build_dir / "_changehistory.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _build_version_options_html(versions: list[dict], active_version: str) -> str:
    """Build <option> tags for the version select dropdown."""
    selected_trunk = ' selected' if active_version == "trunk" else ""
    parts = [f'      <option value="trunk"{selected_trunk}>trunk</option>']
    for v in versions:
        name = v.get("version", "")
        if not name:
            continue
        selected = ' selected' if active_version == name else ""
        label = html_mod.escape(name)
        parts.append(f'      <option value="{label}"{selected}>{label}</option>')
    return "\n".join(parts)


def _build_version_nav_html(
    changehistory: dict,
) -> tuple[str, dict[str, Any] | None]:
    """Build the Versions sidebar section from changehistory data.

    Returns (html_str, first_item_dict | None).  first_item_dict has
    type='version-history' so DOMContentLoaded loads the history page first.
    """
    if not changehistory:
        return "", None

    item_id = "nav-version-history"
    parts = ['<div class="nav-section">']
    parts.append('<div class="nav-section-title">Versions</div>')
    parts.append(
        f'<div class="nav-item" id="{item_id}" data-type="version-history">'
        f'<span class="icon">⏱</span>'
        f'<span class="name">Version History</span>'
        f'</div>'
    )
    parts.append("</div>")

    first_item: dict[str, Any] = {
        "id": item_id,
        "type": "version-history",
        "url": "",
        "name": "Version History",
    }
    return "".join(parts), first_item


def _build_sitemap_nav_html(
    domains: dict[str, list[dict[str, str]]],
) -> tuple[str, dict[str, Any] | None]:
    """Build the Sitemap sidebar section from *domains*.

    Each domain becomes a ``nav-item`` with a ``data-domain`` attribute and a
    page-count badge.  Returns ``(html_str, first_item_dict | None)`` where
    *first_item_dict* has keys ``domain``, ``url``, ``name``, ``id``.
    """
    if not domains:
        return "", None

    parts: list[str] = ['<div class="nav-section">']
    parts.append('<div class="nav-section-title">Sitemap</div>')

    first_item: dict[str, Any] | None = None
    for domain_id, pages in domains.items():
        domain_name = _display_name(domain_id)
        item_id = f"domain-{domain_id}"
        if first_item is None and pages:
            first_item = {
                "domain": domain_id,
                "url": pages[0]["url"],
                "name": domain_name,
                "id": item_id,
            }
        parts.append(
            f'<div class="nav-item" id="{html_mod.escape(item_id)}"'
            f' data-domain="{html_mod.escape(domain_id)}">'
            f'<span class="icon">&#8853;</span>'
            f'<span class="name">{html_mod.escape(domain_name)}</span>'
            f'<span class="domain-count">{len(pages)}</span>'
            f"</div>"
        )

    parts.append("</div>")
    return "".join(parts), first_item


def _categorize_files(build_dir: Path) -> dict[str, list]:
    """Categorise *.html files in *build_dir* (recursively) into labelled sections.

    Root index.html (the preview shell) is excluded.
    Subdirectories with an index.html become a folder group: a tuple of
    ``(index_path, [child_paths])``, placed before any root-level files in
    their category.  Subdirectories without an index.html are listed flat.
    Returns only non-empty buckets, preserving *_CATEGORY_ORDER*.
    """
    root_index = build_dir / "index.html"
    all_html = sorted(f for f in build_dir.rglob("*.html") if f != root_index)

    # Separate root-level files from subdirectory files (one level deep)
    root_files: list[Path] = []
    by_subdir: dict[Path, list[Path]] = {}
    for f in all_html:
        if f.parent == build_dir:
            root_files.append(f)
        else:
            immediate = build_dir / f.relative_to(build_dir).parts[0]
            by_subdir.setdefault(immediate, []).append(f)

    # Classify helper — canonical dir name takes priority over keyword scan
    def _cat(dir_name: str, stem: str = "") -> str:
        if dir_name in _DIR_CATEGORY:
            return _DIR_CATEGORY[dir_name]
        tokens = stem.lower() + " " + dir_name.lower()
        if any(kw in tokens for kw in _DESIGN_SYSTEM_KEYWORDS):
            return "Design System"
        if any(kw in tokens for kw in _COMPONENT_KEYWORDS):
            return "Components"
        return "Prototypes"

    # Folder groups (subdirs) — placed first within their category
    folder_buckets: dict[str, list] = {c: [] for c in _CATEGORY_ORDER}
    for subdir_path in sorted(by_subdir):
        files = by_subdir[subdir_path]
        index_file = next((f for f in files if f.name == "index.html"), None)
        others = sorted(f for f in files if f.name != "index.html")
        cat = _cat(subdir_path.name.lower())
        if index_file:
            folder_buckets[cat].append((index_file, others))
        else:
            folder_buckets[cat].extend(others)

    # Root-level files — appended after folder groups
    file_buckets: dict[str, list] = {c: [] for c in _CATEGORY_ORDER}
    for f in root_files:
        file_buckets[_cat("", f.stem)].append(f)

    merged: dict[str, list] = {}
    for cat in _CATEGORY_ORDER:
        combined = folder_buckets[cat] + file_buckets[cat]
        if combined:
            merged[cat] = combined
    return merged


def _display_name(stem: str) -> str:
    """Convert a file stem to a human-readable display name.

    >>> _display_name("design-tokens")
    'Design Tokens'
    >>> _display_name("home_page")
    'Home Page'
    """
    return stem.replace("-", " ").replace("_", " ").title()


def _build_nav_html(
    categories: dict[str, list],
    build_dir: Path,
) -> tuple[str, dict[str, Any] | None]:
    """Build sidebar nav HTML from *categories*.

    Each category value is a list of either:
    - ``Path`` — a regular nav item
    - ``(index_path, [child_paths])`` — a collapsible folder group

    Returns ``(html_string, first_item_dict | None)`` where *first_item_dict*
    has keys ``id``, ``url``, ``name`` and is used for auto-loading the first
    page on DOMContentLoaded.
    """
    parts: list[str] = []
    first_item: dict[str, Any] | None = None
    item_idx = 0
    folder_idx = 0

    for section_name, entries in categories.items():
        icon = _CATEGORY_ICONS.get(section_name, "▣")
        type_attr = ' data-type="ds"' if section_name in ("Design System", "Components") else ""
        parts.append('<div class="nav-section">')
        parts.append(
            f'<div class="nav-section-title">'
            f'{html_mod.escape(section_name)}'
            f'</div>'
        )
        for entry in entries:
            if isinstance(entry, tuple):
                # Folder group: (index_path, [child_paths])
                index_file, children = entry
                folder_dom_id = f"folder-{folder_idx}"
                folder_idx += 1
                item_id = f"nav-{item_idx}"
                folder_name = _display_name(index_file.parent.name)
                rel_url = index_file.relative_to(build_dir).as_posix()

                if first_item is None:
                    first_item = {"id": item_id, "url": rel_url, "name": folder_name}
                    if type_attr:
                        first_item["type"] = "ds"

                parts.append(f'<div class="nav-folder" id="{folder_dom_id}">')
                parts.append(
                    f'<div class="nav-folder-header" id="{item_id}"'
                    f' data-url="{html_mod.escape(rel_url)}"'
                    f' data-name="{html_mod.escape(folder_name)}"'
                    f' data-folder="{folder_dom_id}"{type_attr}>'
                    f'<span class="icon">{icon}</span>'
                    f'<span class="name">{html_mod.escape(folder_name)}</span>'
                    f'<span class="folder-toggle">&#9660;</span>'
                    f'</div>'
                )
                item_idx += 1

                if children:
                    parts.append(
                        f'<div class="nav-folder-children" id="{folder_dom_id}-children">'
                    )
                    for child in children:
                        child_id = f"nav-{item_idx}"
                        child_name = _display_name(child.stem)
                        child_url = child.relative_to(build_dir).as_posix()
                        parts.append(
                            f'<div class="nav-item nav-child" id="{child_id}"'
                            f' data-url="{html_mod.escape(child_url)}"'
                            f' data-name="{html_mod.escape(child_name)}"{type_attr}>'
                            f'<span class="icon">·</span>'
                            f'<span class="name">{html_mod.escape(child_name)}</span>'
                            f'</div>'
                        )
                        item_idx += 1
                    parts.append('</div>')  # nav-folder-children

                parts.append('</div>')  # nav-folder

            else:
                # Regular file
                f = entry
                item_id = f"nav-{item_idx}"
                name = _display_name(f.stem)
                rel_url = f.relative_to(build_dir).as_posix()
                parts.append(
                    f'<div class="nav-item" id="{item_id}"'
                    f' data-url="{html_mod.escape(rel_url)}"'
                    f' data-name="{html_mod.escape(name)}"{type_attr}>'
                    f'<span class="icon">{icon}</span>'
                    f'<span class="name">{html_mod.escape(name)}</span>'
                    f'</div>'
                )
                if first_item is None:
                    first_item = {"id": item_id, "url": rel_url, "name": name}
                    if type_attr:
                        first_item["type"] = "ds"
                item_idx += 1

        parts.append("</div>")

    return "".join(parts), first_item
