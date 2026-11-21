// HeatReady: progressive enhancement for the header menu (works without JS via <details>).
(function () {
  var menu = document.querySelector(".site-header .menu");
  if (!menu) return;
  var close = function () { menu.removeAttribute("open"); };
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && menu.open) { close(); menu.querySelector("summary").focus(); } });
  document.addEventListener("click", function (e) { if (menu.open && !menu.contains(e.target)) close(); });
  menu.addEventListener("click", function (e) { if (e.target.closest(".menu-panel a")) close(); });
  var mq = window.matchMedia("(min-width: 768px)");
  var onChange = function () { if (mq.matches) close(); };
  mq.addEventListener ? mq.addEventListener("change", onChange) : mq.addListener(onChange);
})();
