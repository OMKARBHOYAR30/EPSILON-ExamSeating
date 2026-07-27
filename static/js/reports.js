/* reports.js - Direct PDF Printing & Preview */

function printPdfFrame(iframeId) {
  const iframe = document.getElementById(iframeId);
  if (iframe && iframe.contentWindow) {
    iframe.contentWindow.focus();
    iframe.contentWindow.print();
  } else {
    // Fallback if iframe fails
    window.print();
  }
}

document.addEventListener("DOMContentLoaded", function() {
  const printBlockBtn = document.getElementById("btnPrintBlockReport");
  if (printBlockBtn) {
    printBlockBtn.addEventListener("click", function() {
      printPdfFrame("blockPdfIframe");
    });
  }

  const printSummaryBtn = document.getElementById("btnPrintAllocationSummary");
  if (printSummaryBtn) {
    printSummaryBtn.addEventListener("click", function() {
      printPdfFrame("summaryPdfIframe");
    });
  }

  // Handle Room Selector on Block Report Page
  const blockReportRoomSelect = document.getElementById("block_report_room_select");
  if (blockReportRoomSelect) {
    blockReportRoomSelect.addEventListener("change", function() {
      const allocId = this.value;
      const iframe = document.getElementById("blockPdfIframe");
      if (allocId && iframe) {
        iframe.src = `/generated_reports/preview_block?id=${allocId}&t=${Date.now()}`;
      }
    });
  }
});
