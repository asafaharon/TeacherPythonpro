/* modules.js – רשימת מודולים עם חיפוש וסינון לפי רמות */
document.addEventListener('DOMContentLoaded', async () => {
  const listEl = document.getElementById('modules-list');
  const searchEl = document.getElementById('search');
  const filterButtons = document.querySelectorAll('#filters button');

  let modules = [];
  let currentFilter = "all";

  try {
    const url = '/static/content/index.json?ts=' + Date.now();
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status} (${res.statusText})`);

    const data = await res.json();
    modules = Array.isArray(data) ? data : data.modules;
    if (!Array.isArray(modules)) throw new Error('פורמט index.json לא תקין');

    renderModules(modules);

    // חיפוש
    searchEl.addEventListener('input', () => {
      applyFilters();
    });

    // סינון לפי רמות
    filterButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        filterButtons.forEach(b => b.classList.remove('tp-btn--active'));
        btn.classList.add('tp-btn--active');
        currentFilter = btn.dataset.level;
        applyFilters();
      });
    });

  } catch (e) {
    console.error('[modules] load error', e);
    listEl.innerHTML = `<p class="tp-error">❌ ${e.message}</p>`;
  }

  function applyFilters() {
    const term = searchEl.value.trim();
    let filtered = modules;

    // חיפוש
    if (term) {
      filtered = filtered.filter(m =>
        m.title.includes(term) ||
        String(m.id).includes(term) ||
        (m.level && m.level.includes(term))
      );
    }

    // סינון לפי רמה
    if (currentFilter !== "all") {
      filtered = filtered.filter(m => m.level === currentFilter);
    }

    renderModules(filtered);
  }

  function renderModules(list) {
    if (!list.length) {
      listEl.innerHTML = `<p class="tp-muted">לא נמצאו מודולים</p>`;
      return;
    }

    // קיבוץ לפי רמה
    const levels = ["מתחילים", "בינוני", "מתקדם"];
    let html = "";

    levels.forEach(level => {
      const items = list.filter(m => m.level === level);
      if (!items.length) return;

      html += `<h3 class="tp-section-title">${level}</h3><ul class="tp-list">`;
      html += items.map(m => `
        <li class="tp-list-item">
          <a href="/module/${m.id}" class="tp-card-link">
            <span class="tp-badge">#${m.id}</span>
            <span class="tp-module-title">${m.title}</span>
            <span class="tp-level-badge ${getLevelClass(m.level)}">${m.level}</span>
          </a>
        </li>
      `).join('');
      html += `</ul>`;
    });

    listEl.innerHTML = html;
  }

  function getLevelClass(level) {
    switch (level) {
      case "מתחילים": return "tp-level-beginner";
      case "בינוני": return "tp-level-intermediate";
      case "מתקדם": return "tp-level-advanced";
      default: return "";
    }
  }
});
