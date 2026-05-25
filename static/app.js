(function () {
  'use strict';

  // --- Animate messages auto-dismiss ---
  document.querySelectorAll('.alert').forEach(function (el) {
    setTimeout(function () {
      el.style.transition = 'opacity 0.4s, transform 0.4s';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-10px)';
      setTimeout(function () { el.remove(); }, 400);
    }, 5000);
  });

  // --- Fade in cards on page load ---
  document.querySelectorAll('.card').forEach(function (el, i) {
    el.style.opacity = '0';
    el.style.transform = 'translateY(12px)';
    el.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
    setTimeout(function () {
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
    }, 60 * i);
  });

  // --- Date validation sur le formulaire facture ---
  var arrival = document.getElementById('id_date_arrivee');
  var departure = document.getElementById('id_date_depart');

  function getToday() {
    var d = new Date();
    return d.getFullYear() + '-' +
      String(d.getMonth() + 1).padStart(2, '0') + '-' +
      String(d.getDate()).padStart(2, '0');
  }

  function setMinDate(input) {
    if (input && !input.getAttribute('data-min-set')) {
      input.setAttribute('min', getToday());
      input.setAttribute('data-min-set', 'true');
    }
  }
  setMinDate(arrival);
  setMinDate(departure);

  function showError(input, msg) {
    var container = input.closest('.form-group');
    if (!container) return;
    var existing = container.querySelector('.field-error');
    if (!existing) {
      existing = document.createElement('small');
      existing.className = 'field-error';
      existing.style.cssText = 'color:#dc3545;font-size:12px;display:block;margin-top:4px;';
      container.appendChild(existing);
    }
    existing.textContent = msg;
  }

  function clearError(input) {
    var container = input.closest('.form-group');
    if (!container) return;
    var existing = container.querySelector('.field-error');
    if (existing) existing.remove();
  }

  function validateDates() {
    if (!arrival || !departure) return;
    var da = arrival.value;
    var dd = departure.value;

    clearError(arrival);
    clearError(departure);

    if (da && da < getToday()) {
      showError(arrival, 'La date d\'arrivée ne peut pas être dans le passé.');
      return;
    }
    if (dd && dd < getToday()) {
      showError(departure, 'La date de départ ne peut pas être dans le passé.');
      return;
    }
    if (da && dd && dd <= da) {
      showError(departure, 'Le départ doit être après l\'arrivée.');
    }
  }

  if (arrival) {
    arrival.addEventListener('change', validateDates);
    arrival.addEventListener('blur', validateDates);
  }
  if (departure) {
    departure.addEventListener('change', validateDates);
    departure.addEventListener('blur', validateDates);
  }

  // --- Smooth hover effet sur les lignes du tableau ---
  document.querySelectorAll('.table tbody tr').forEach(function (tr) {
    tr.addEventListener('mouseenter', function () {
      this.style.transition = 'background 0.15s';
    });
  });

  // --- Confirmation de suppression avec animation ---
  document.querySelectorAll('a.danger, .btn-danger').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      var href = this.getAttribute('href');
      if (href && href.includes('delete') && !confirm('Confirmer la suppression ?')) {
        e.preventDefault();
      }
    });
  });

})();
