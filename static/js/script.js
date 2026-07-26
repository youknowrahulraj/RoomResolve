/* ══════════════════════════════════════════════════════
   RoomResolve — Custom JavaScript
   ══════════════════════════════════════════════════════ */

// ── Auto-dismiss flash alerts after 4 seconds ─────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {

  const alerts = document.querySelectorAll('.alert.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 4000);
  });

  // ── Bootstrap tooltip initialisation ─────────────────────────────────────
  const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

  // ── Image preview on complaint form ──────────────────────────────────────
  const imageInput   = document.getElementById('imageInput');
  const previewBox   = document.getElementById('imagePreview');
  const previewImg   = document.getElementById('previewImg');

  if (imageInput) {
    imageInput.addEventListener('change', function () {
      const file = this.files[0];
      if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function (e) {
          previewImg.src = e.target.result;
          previewBox.classList.remove('d-none');
        };
        reader.readAsDataURL(file);
      } else {
        previewBox.classList.add('d-none');
        previewImg.src = '';
      }
    });
  }

});


// ── Admin dashboard: filter table rows by status ──────────────────────────────
function filterTable(status) {
  const rows = document.querySelectorAll('#complaintsTable tbody tr');

  // Update active tab styling
  document.querySelectorAll('#complaintTabs .nav-link').forEach(function (btn) {
    btn.classList.toggle('active', btn.textContent.trim() === status);
  });

  rows.forEach(function (row) {
    if (status === 'All') {
      row.style.display = '';
    } else {
      row.style.display = row.dataset.status === status ? '' : 'none';
    }
  });
}