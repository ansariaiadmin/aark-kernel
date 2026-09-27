/* ==========================================================================
   AARK Kernel — landing page behaviour
   Language toggle (RTL/LTR) + mobile navigation. No dependencies.
   ========================================================================== */
(function () {
  "use strict";

  var STORAGE_KEY = "aark-lang";
  var body = document.body;
  var html = document.documentElement;
  var btn = document.getElementById("langBtn");

  /* ---------- language ---------- */
  function currentLang() {
    return html.getAttribute("lang") === "en" ? "en" : "fa";
  }

  function apply(lang) {
    var isEn = lang === "en";
    body.classList.toggle("lang-en", isEn);
    body.classList.toggle("lang-fa", !isEn);
    html.setAttribute("lang", isEn ? "en" : "fa");
    html.setAttribute("dir", isEn ? "ltr" : "rtl");
    if (btn) {
      btn.textContent = isEn ? "فارسی" : "EN";
      btn.setAttribute("aria-label", isEn ? "Switch to Persian" : "Switch to English");
    }
    try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* private mode */ }
  }

  // The initial language is already decided by the inline script in the
  // document head — a stored preference, otherwise the browser language.
  // Here we only read it back so the toggle button starts in the right state.
  apply(currentLang());

  if (btn) {
    btn.addEventListener("click", function () {
      apply(currentLang() === "en" ? "fa" : "en");
    });
  }

  /* ---------- mobile navigation ---------- */
  var toggle = document.getElementById("navToggle");
  var links = document.getElementById("navLinks");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    // Close the menu after following a link.
    links.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        links.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ---------- close FAQ siblings for a tidier read (optional) ---------- */
  var items = document.querySelectorAll("details");
  items.forEach(function (d) {
    d.addEventListener("toggle", function () {
      if (d.open) {
        items.forEach(function (o) { if (o !== d) o.open = false; });
      }
    });
  });
})();
