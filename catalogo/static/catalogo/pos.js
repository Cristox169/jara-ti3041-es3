(() => {
  const productCards = [...document.querySelectorAll('[data-pos-product]')];
  const filterButtons = [...document.querySelectorAll('[data-pos-filter]')];
  const searchInput = document.getElementById('pos-search');
  const visibleCount = document.getElementById('pos-visible-count');
  const emptyResults = document.getElementById('pos-empty-results');
  const cartItems = document.getElementById('cart-items');
  const cartCount = document.getElementById('cart-count');
  const cartSubtotal = document.getElementById('cart-subtotal');
  const cartUnits = document.getElementById('cart-units');
  const cartTotal = document.getElementById('cart-total');
  const checkoutButton = document.getElementById('checkout-button');
  const toast = document.getElementById('pos-toast');
  const checkoutDialog = document.getElementById('checkout-dialog');
  const receiptItems = document.getElementById('receipt-items');
  const receiptTotal = document.getElementById('receipt-total');
  const receiptNumber = document.getElementById('receipt-number');
  const receiptDate = document.getElementById('receipt-date');
  const printStatus = document.getElementById('print-status');
  const receiptActions = document.getElementById('receipt-actions');
  const cart = new Map();
  let selectedCategory = 'todos';
  let toastTimer;
  let printTimer;

  const formatCurrency = (value) => new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    maximumFractionDigits: 0,
  }).format(value);

  const normalize = (value) => value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

  const escapeHtml = (value) => value.replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;',
  })[character]);

  const getTotals = () => [...cart.values()].reduce((summary, item) => ({
    units: summary.units + item.quantity,
    total: summary.total + (item.price * item.quantity),
  }), { units: 0, total: 0 });

  const showToast = (productName) => {
    toast.querySelector('strong').textContent = `${productName} agregado`;
    toast.classList.add('is-visible');
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), 1700);
  };

  const renderCart = () => {
    const { units, total } = getTotals();

    if (cart.size === 0) {
      cartItems.innerHTML = `
        <div class="pos-cart-empty" id="cart-empty">
          <span aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M3 4h2l2.3 10.2a2 2 0 0 0 2 1.6h7.9a2 2 0 0 0 1.9-1.4L21 8H7"></path><path d="M9 10h8"></path></svg>
          </span>
          <h3>Tu carro está vacío</h3>
          <p>Selecciona un producto del panel para comenzar la venta.</p>
        </div>`;
    } else {
      cartItems.innerHTML = [...cart.values()].map((item) => `
        <article class="cart-line" data-cart-id="${item.id}">
          <div class="cart-line-top">
            <span class="cart-line-number">${String(item.id).padStart(2, '0')}</span>
            <div>
              <h3>${escapeHtml(item.name)}</h3>
              <p>${formatCurrency(item.price)} c/u · Stock ${item.stock}</p>
            </div>
            <strong>${formatCurrency(item.price * item.quantity)}</strong>
          </div>
          <div class="cart-line-actions">
            <div class="cart-quantity" aria-label="Cantidad de ${escapeHtml(item.name)}">
              <button type="button" data-cart-action="decrease" aria-label="Restar una unidad">−</button>
              <span aria-label="${item.quantity} unidades">${item.quantity}</span>
              <button type="button" data-cart-action="increase" aria-label="Sumar una unidad" ${item.quantity >= item.stock ? 'disabled' : ''}>+</button>
            </div>
            <button class="cart-remove" type="button" data-cart-action="remove">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5"></path></svg>
              Eliminar
            </button>
          </div>
        </article>`).join('');
    }

    cartCount.textContent = `${cart.size} ${cart.size === 1 ? 'producto' : 'productos'}`;
    cartSubtotal.textContent = formatCurrency(total);
    cartUnits.textContent = `${units} ${units === 1 ? 'unidad' : 'unidades'}`;
    cartTotal.textContent = formatCurrency(total);
    checkoutButton.disabled = cart.size === 0;
  };

  const filterProducts = () => {
    const term = normalize(searchInput.value.trim());
    let count = 0;

    productCards.forEach((card) => {
      const matchesCategory = selectedCategory === 'todos' || card.dataset.category === selectedCategory;
      const matchesSearch = normalize(card.dataset.name).includes(term);
      const isVisible = matchesCategory && matchesSearch;
      card.hidden = !isVisible;
      if (isVisible) count += 1;
    });

    visibleCount.textContent = count;
    emptyResults.hidden = count !== 0;
  };

  productCards.forEach((card) => {
    card.addEventListener('click', () => {
      if (card.disabled) return;

      const id = Number(card.dataset.id);
      const existing = cart.get(id);
      const stock = Number(card.dataset.stock);
      if (existing && existing.quantity >= stock) return;

      cart.set(id, existing ? { ...existing, quantity: existing.quantity + 1 } : {
        id,
        name: card.dataset.name,
        price: Number(card.dataset.price),
        stock,
        quantity: 1,
      });
      renderCart();
      showToast(card.dataset.name);
    });
  });

  filterButtons.forEach((button) => {
    button.addEventListener('click', () => {
      selectedCategory = button.dataset.posFilter;
      filterButtons.forEach((item) => {
        const isActive = item === button;
        item.classList.toggle('active', isActive);
        item.setAttribute('aria-pressed', String(isActive));
      });
      filterProducts();
    });
  });

  searchInput.addEventListener('input', filterProducts);

  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      searchInput.focus();
    }
  });

  cartItems.addEventListener('click', (event) => {
    const actionButton = event.target.closest('[data-cart-action]');
    const line = event.target.closest('[data-cart-id]');
    if (!actionButton || !line) return;

    const id = Number(line.dataset.cartId);
    const item = cart.get(id);
    if (!item) return;

    if (actionButton.dataset.cartAction === 'increase' && item.quantity < item.stock) {
      item.quantity += 1;
    }
    if (actionButton.dataset.cartAction === 'decrease' && item.quantity > 1) {
      item.quantity -= 1;
    }
    if (actionButton.dataset.cartAction === 'remove') {
      cart.delete(id);
    }
    renderCart();
  });

  const closeReceipt = () => {
    window.clearTimeout(printTimer);
    checkoutDialog.close();
  };

  checkoutButton.addEventListener('click', async () => {
    if (cart.size === 0) return;

    const { total } = getTotals();
    checkoutButton.disabled = true;
    checkoutButton.querySelector('span').textContent = 'Registrando…';
    let venta;
    try {
      const response = await fetch(checkoutButton.dataset.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.querySelector('#pos-security [name=csrfmiddlewaretoken]').value,
        },
        body: JSON.stringify({
          items: [...cart.values()].map(({ id, quantity }) => ({ id, quantity })),
        }),
      });
      venta = await response.json();
      if (!response.ok || !venta.ok) throw new Error(venta.error || 'No fue posible registrar la venta.');
    } catch (error) {
      window.alert(error.message);
      checkoutButton.disabled = false;
      checkoutButton.querySelector('span').textContent = 'Finalizar compra';
      return;
    }
    receiptItems.innerHTML = [...cart.values()].map((item) => `
      <div class="receipt-line">
        <span><strong>${item.quantity} × ${escapeHtml(item.name)}</strong><small>${formatCurrency(item.price)} c/u</small></span>
        <strong>${formatCurrency(item.price * item.quantity)}</strong>
      </div>`).join('');
    receiptTotal.textContent = formatCurrency(total);
    receiptNumber.textContent = venta.numero;
    receiptDate.textContent = venta.fecha;
    printStatus.textContent = 'Imprimiendo comprobante…';
    receiptActions.hidden = true;
    checkoutDialog.classList.add('is-printing');
    checkoutDialog.classList.remove('is-complete');
    checkoutDialog.showModal();

    window.clearTimeout(printTimer);
    printTimer = window.setTimeout(() => {
      checkoutDialog.classList.remove('is-printing');
      checkoutDialog.classList.add('is-complete');
      printStatus.textContent = 'Comprobante listo';
      receiptActions.hidden = false;
      checkoutButton.querySelector('span').textContent = 'Finalizar compra';
    }, 1900);
  });

  document.getElementById('receipt-close').addEventListener('click', closeReceipt);
  document.getElementById('receipt-continue').addEventListener('click', closeReceipt);
  document.getElementById('new-sale').addEventListener('click', () => {
    cart.clear();
    renderCart();
    closeReceipt();
  });
  checkoutDialog.addEventListener('click', (event) => {
    if (event.target === checkoutDialog) closeReceipt();
  });

  renderCart();
})();
