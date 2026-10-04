/**
 * Attestatsiya.uz - Global Frontend Utilities
 */
document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 6000);
  });

  // Tooltips initialization
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
});

// Copy to clipboard helper
function copyToClipboard(text, successMsg = "Nusxalandi!") {
  navigator.clipboard.writeText(text).then(() => {
    alert(successMsg);
  }).catch(err => {
    console.error("Nusxa olishda xatolik:", err);
  });
}
