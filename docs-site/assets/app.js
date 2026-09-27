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

  // Respect a previously stored preference; default to Persian.
  var stored = null;
  try { stored = localStorage.getItem(STORAGE_KEY); } catch (e) { /* ignore */ }
  apply(stored === "en" ? "en" : "fa");

  if (btn) {
    btn.addEventListener("click", function () {
      apply(body.classList.contains("lang-en") ? "fa" : "en");
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
