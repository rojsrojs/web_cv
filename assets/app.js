// Theme toggle (remembered per browser) and tab switching with deep links (#experience etc.).
(() => {
  const root = document.documentElement;
  const systemDark = matchMedia("(prefers-color-scheme: dark)");
  const currentTheme = () => root.dataset.theme || (systemDark.matches ? "dark" : "light");

  const themeButton = document.getElementById("theme-toggle");
  const syncThemeLabel = () =>
    themeButton.setAttribute("aria-label", currentTheme() === "dark" ? "Switch to light mode" : "Switch to dark mode");
  themeButton.addEventListener("click", () => {
    root.dataset.theme = currentTheme() === "dark" ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch {}
    syncThemeLabel();
  });
  systemDark.addEventListener("change", syncThemeLabel);
  syncThemeLabel();

  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const panels = [...document.querySelectorAll('[role="tabpanel"]')];
  const panelFromHash = () => {
    const id = decodeURIComponent(location.hash.slice(1));
    return panels.some((p) => p.id === id) ? id : panels[0].id;
  };

  const show = (id) => {
    for (const tab of tabs) {
      const selected = tab.getAttribute("aria-controls") === id;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    }
    for (const panel of panels) panel.hidden = panel.id !== id;
  };

  for (const tab of tabs) {
    tab.addEventListener("click", (event) => {
      event.preventDefault();
      const id = tab.getAttribute("aria-controls");
      history.pushState(null, "", `#${id}`);
      show(id);
      // If the user has scrolled past the start of the section, bring it into view
      // (each layout sets scroll-margin-top for its own sticky elements).
      const panel = document.getElementById(id);
      const margin = parseFloat(getComputedStyle(panel).scrollMarginTop) || 0;
      if (panel.getBoundingClientRect().top < margin) panel.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    tab.addEventListener("keydown", (event) => {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
      if (!step) return;
      const next = tabs[(tabs.indexOf(tab) + step + tabs.length) % tabs.length];
      next.focus();
      next.click();
    });
  }

  addEventListener("popstate", () => show(panelFromHash()));
  show(panelFromHash());
})();
