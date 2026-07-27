/* room.js - Room Management Live Calculation */

document.addEventListener("DOMContentLoaded", function() {
  const layoutInput = document.getElementById("row_layout");
  const calcPreview = document.getElementById("layout_calc_preview");

  if (layoutInput && calcPreview) {
    function updateCalc() {
      const val = layoutInput.value.trim();
      if (!val) {
        calcPreview.textContent = "Capacity = 0 | Rows = 0";
        return;
      }
      const parts = val.split(",").map(p => p.trim()).filter(p => p !== "" && !isNaN(p));
      const rows = parts.length;
      const capacity = parts.reduce((sum, num) => sum + parseInt(num, 10), 0);

      calcPreview.textContent = `Capacity = ${capacity} | Rows = ${rows}`;
    }

    layoutInput.addEventListener("input", updateCalc);
    updateCalc();
  }
});
