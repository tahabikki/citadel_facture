(function () {
  'use strict';

  document.querySelectorAll('.hc-alert').forEach(function (el) {
    setTimeout(function () {
      el.style.opacity = '0';
      el.style.transform = 'translateY(-6px)';
      el.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
      setTimeout(function () { el.remove(); }, 280);
    }, 5000);
  });

  var arrival = document.getElementById('id_date_arrivee');
  var departure = document.getElementById('id_date_depart');

  function getToday() {
    var d = new Date();
    return d.getFullYear() + '-' +
      String(d.getMonth() + 1).padStart(2, '0') + '-' +
      String(d.getDate()).padStart(2, '0');
  }

  [arrival, departure].forEach(function (input) {
    if (input) input.removeAttribute('min');
  });

  function showError(input, msg) {
    var container = input.closest('.hc-field');
    if (!container) return;
    var existing = container.querySelector('.hc-field-error');
    if (!existing) {
      existing = document.createElement('small');
      existing.className = 'hc-field-error';
      existing.style.cssText = 'color:#867050;font-size:12px;display:block;margin-top:5px;font-weight:700;';
      container.appendChild(existing);
    }
    existing.textContent = msg;
  }

  function clearError(input) {
    var container = input.closest('.hc-field');
    if (!container) return;
    var existing = container.querySelector('.hc-field-error');
    if (existing) existing.remove();
  }

  function validateDates() {
    if (!arrival || !departure) return;
    clearError(arrival);
    clearError(departure);
    if (arrival.value && departure.value && departure.value <= arrival.value) showError(departure, "Le depart doit etre apres l'arrivee.");
  }

  if (arrival) arrival.addEventListener('change', validateDates);
  if (departure) departure.addEventListener('change', validateDates);

  var factureForm = arrival && arrival.closest('form');
  if (factureForm) {
    factureForm.addEventListener('submit', function (event) {
      if (arrival.value && arrival.value < getToday()) {
        var confirmed = window.confirm(
          "La date d'arrivee choisie est anterieure a aujourd'hui. Voulez-vous continuer ?"
        );
        if (!confirmed) event.preventDefault();
      }
    });
  }

  // Mobile sidebar toggle
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebar-overlay');
  var menuToggle = document.getElementById('menu-toggle');
  var sidebarClose = document.getElementById('sidebar-close');

  function openSidebar() {
    sidebar.classList.add('is-open');
    if (overlay) overlay.classList.add('is-visible');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('is-open');
    if (overlay) overlay.classList.remove('is-visible');
    document.body.style.overflow = '';
  }

  if (menuToggle) menuToggle.addEventListener('click', openSidebar);
  if (sidebarClose) sidebarClose.addEventListener('click', closeSidebar);
  if (overlay) overlay.addEventListener('click', closeSidebar);

  // Close sidebar on window resize (if goes desktop)
  window.addEventListener('resize', function () {
    if (window.innerWidth > 920 && sidebar) {
      sidebar.classList.remove('is-open');
      if (overlay) overlay.classList.remove('is-visible');
      document.body.style.overflow = '';
    }
  });
})();
