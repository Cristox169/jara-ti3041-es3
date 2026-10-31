(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector('#theme-toggle');

  const updateThemeLabel = () => {
    if (!themeButton) return;
    const darkMode = root.dataset.theme === 'dark';
    themeButton.setAttribute(
      'aria-label',
      darkMode ? 'Activar tema claro' : 'Activar tema oscuro',
    );
    themeButton.setAttribute(
      'title',
      darkMode ? 'Activar tema claro' : 'Activar tema oscuro',
    );
  };

  updateThemeLabel();
  themeButton?.addEventListener('click', () => {
    const nextTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = nextTheme;
    localStorage.setItem('crissteel-theme', nextTheme);
    updateThemeLabel();
  });

  const filterButtons = document.querySelectorAll('[data-filter]');
  const productCards = document.querySelectorAll('[data-product-card]');
  const visibleCount = document.querySelector('#visible-count');
  const emptyFilter = document.querySelector('#empty-filter');

  filterButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const selectedFilter = button.dataset.filter;
      let count = 0;

      filterButtons.forEach((item) => {
        const active = item === button;
        item.classList.toggle('active', active);
        item.setAttribute('aria-pressed', String(active));
      });

      productCards.forEach((card) => {
        const visible =
          selectedFilter === 'todos' || card.dataset.category === selectedFilter;
        card.hidden = !visible;
        if (visible) count += 1;
      });

      if (visibleCount) visibleCount.textContent = String(count);
      if (emptyFilter) emptyFilter.hidden = count !== 0;
    });
  });
})();
