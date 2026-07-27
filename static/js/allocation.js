/* allocation.js - New Seating Arrangement Wizard, Section Datasets & Duplicate Check */

function setLeftDatasetCount(count) {
  const input = document.getElementById("left_dataset_count");
  if (input) {
    input.value = count;
    loadLeftDatasetPreview();
  }
}

function setRightDatasetCount(count) {
  const input = document.getElementById("right_dataset_count");
  if (input) {
    input.value = count;
    loadRightDatasetPreview();
  }
}

function loadLeftDatasetPreview() {
  const college = document.getElementById("left_college")?.value || "GHRCE";
  const branch = document.getElementById("left_branch")?.value || "";
  const sem = document.getElementById("left_semester")?.value || "";
  const sec = document.getElementById("left_section")?.value || "";
  const exDate = document.getElementById("exam_date")?.value || "";
  const count = document.getElementById("left_dataset_count")?.value || 15;
  const preview = document.getElementById("left_dataset_preview_text");

  if (!preview) return;

  if (!branch || !sem || !sec) {
    preview.textContent = "Select Branch, Semester & Section to load active section roll numbers.";
    return;
  }

  fetch(`/api/get_section_students?college=${encodeURIComponent(college)}&branch=${encodeURIComponent(branch)}&semester=${encodeURIComponent(sem)}&section=${encodeURIComponent(sec)}&exam_date=${encodeURIComponent(exDate)}&limit=${count}`)
    .then(res => res.json())
    .then(data => {
      if (data.students && data.students.length > 0) {
        const list = data.students.map(s => s.roll_no).join(", ");
        let allocatedNotice = "";
        if (data.total_already_allocated > 0) {
          allocatedNotice = `<span style="color:#d97706; margin-left:0.5rem;"><i class="fa-solid fa-shield-halved"></i> (${data.total_already_allocated} students already allocated on ${exDate} automatically excluded)</span>`;
        }
        preview.innerHTML = `<strong>Selected ${data.students.length} Active Unallocated Students (out of ${data.total_active} in Master DB):</strong>${allocatedNotice}<br><code style="word-break:break-all;">${list}</code>`;
      } else if (data.total_active > 0) {
        preview.innerHTML = `<span style="color:#d97706;"><i class="fa-solid fa-triangle-exclamation"></i> All ${data.total_active} active students in ${branch} Sem ${sem} Sec ${sec} are already allocated to other rooms on ${exDate}.</span>`;
      } else {
        preview.textContent = `No active student records found in Master DB for ${branch} Sem ${sem} Sec ${sec}. Please add students in Student Management.`;
      }
    })
    .catch(() => {
      preview.textContent = "Error loading student dataset preview.";
    });
}

function loadRightDatasetPreview() {
  const college = document.getElementById("right_college")?.value || "GHRCE";
  const branch = document.getElementById("right_branch")?.value || "";
  const sem = document.getElementById("right_semester")?.value || "";
  const sec = document.getElementById("right_section")?.value || "";
  const exDate = document.getElementById("exam_date")?.value || "";
  const count = document.getElementById("right_dataset_count")?.value || 15;
  const preview = document.getElementById("right_dataset_preview_text");

  if (!preview) return;

  if (!branch || !sem || !sec) {
    preview.textContent = "Select Branch, Semester & Section to load active section roll numbers.";
    return;
  }

  fetch(`/api/get_section_students?college=${encodeURIComponent(college)}&branch=${encodeURIComponent(branch)}&semester=${encodeURIComponent(sem)}&section=${encodeURIComponent(sec)}&exam_date=${encodeURIComponent(exDate)}&limit=${count}`)
    .then(res => res.json())
    .then(data => {
      if (data.students && data.students.length > 0) {
        const list = data.students.map(s => s.roll_no).join(", ");
        let allocatedNotice = "";
        if (data.total_already_allocated > 0) {
          allocatedNotice = `<span style="color:#d97706; margin-left:0.5rem;"><i class="fa-solid fa-shield-halved"></i> (${data.total_already_allocated} students already allocated on ${exDate} automatically excluded)</span>`;
        }
        preview.innerHTML = `<strong>Selected ${data.students.length} Active Unallocated Students (out of ${data.total_active} in Master DB):</strong>${allocatedNotice}<br><code style="word-break:break-all;">${list}</code>`;
      } else if (data.total_active > 0) {
        preview.innerHTML = `<span style="color:#d97706;"><i class="fa-solid fa-triangle-exclamation"></i> All ${data.total_active} active students in ${branch} Sem ${sem} Sec ${sec} are already allocated to other rooms on ${exDate}.</span>`;
      } else {
        preview.textContent = `No active student records found in Master DB for ${branch} Sem ${sem} Sec ${sec}. Please add students in Student Management.`;
      }
    })
    .catch(() => {
      preview.textContent = "Error loading student dataset preview.";
    });
}

document.addEventListener("DOMContentLoaded", function() {
  const blockSelect = document.getElementById("select_block");
  const roomSelect = document.getElementById("select_room");
  const examDateInput = document.getElementById("exam_date");
  const roomInfoCard = document.getElementById("room_info_card");
  const roomCapSpan = document.getElementById("room_capacity");
  const roomRowsSpan = document.getElementById("room_rows");
  const roomLayoutSpan = document.getElementById("room_layout_disp");

  const duplicateModal = document.getElementById("duplicateModal");
  const btnDuplicateYes = document.getElementById("btnDuplicateYes");
  const btnDuplicateNo = document.getElementById("btnDuplicateNo");

  const benchModeDouble = document.getElementById("bench_mode_double");
  const benchModeSingle = document.getElementById("bench_mode_single");
  const rightGroupContainer = document.getElementById("right_group_container");

  // Left Modes
  const leftModeDataset = document.getElementById("left_mode_dataset");
  const leftModeAuto = document.getElementById("left_mode_auto");
  const leftModeManual = document.getElementById("left_mode_manual");
  const leftDatasetInputs = document.getElementById("left_dataset_inputs");
  const leftAutoInputs = document.getElementById("left_auto_inputs");
  const leftManualInputs = document.getElementById("left_manual_inputs");

  // Right Modes
  const rightModeDataset = document.getElementById("right_mode_dataset");
  const rightModeAuto = document.getElementById("right_mode_auto");
  const rightModeManual = document.getElementById("right_mode_manual");
  const rightDatasetInputs = document.getElementById("right_dataset_inputs");
  const rightAutoInputs = document.getElementById("right_auto_inputs");
  const rightManualInputs = document.getElementById("right_manual_inputs");

  // Exam Date change -> reload previews
  if (examDateInput) {
    examDateInput.addEventListener("change", function() {
      loadLeftDatasetPreview();
      loadRightDatasetPreview();

      // Check room duplicate if room selected
      if (roomSelect && roomSelect.value) {
        const roomNo = roomSelect.value;
        const exDate = examDateInput.value;
        fetch(`/api/check_duplicate?room_no=${encodeURIComponent(roomNo)}&exam_date=${encodeURIComponent(exDate)}`)
          .then(res => res.json())
          .then(data => {
            if (data.has_allocation && duplicateModal) {
              duplicateModal.classList.add("active");
            }
          });
      }
    });
  }

  // Block change -> load rooms
  if (blockSelect && roomSelect) {
    blockSelect.addEventListener("change", function() {
      const block = this.value;
      roomSelect.innerHTML = '<option value="">-- Choose Room --</option>';
      if (roomInfoCard) roomInfoCard.style.display = "none";

      if (block) {
        fetch(`/api/get_rooms?block=${encodeURIComponent(block)}`)
          .then(res => res.json())
          .then(rooms => {
            rooms.forEach(r => {
              const opt = document.createElement("option");
              opt.value = r.room_no;
              opt.textContent = `${r.room_no} (Cap: ${r.default_capacity})`;
              opt.dataset.capacity = r.default_capacity;
              opt.dataset.rows = r.default_rows;
              opt.dataset.layout = r.default_row_layout;
              opt.dataset.block = r.block;
              roomSelect.appendChild(opt);
            });
          })
          .catch(err => console.error("Error fetching rooms:", err));
      }
    });

    // Room change -> show details & check duplicate
    roomSelect.addEventListener("change", function() {
      const selectedOpt = this.options[this.selectedIndex];
      const roomNo = this.value;
      const exDate = examDateInput ? examDateInput.value : "";

      if (roomNo && selectedOpt) {
        if (roomInfoCard) {
          roomCapSpan.textContent = selectedOpt.dataset.capacity;
          roomRowsSpan.textContent = selectedOpt.dataset.rows;
          roomLayoutSpan.textContent = selectedOpt.dataset.layout;
          document.getElementById("selected_block_input").value = selectedOpt.dataset.block;
          roomInfoCard.style.display = "block";

          // Auto update dataset count inputs to half of capacity for double side
          const isSingle = benchModeSingle && benchModeSingle.checked;
          const targetCap = isSingle ? parseInt(selectedOpt.dataset.capacity) : Math.ceil(parseInt(selectedOpt.dataset.capacity) / 2);
          setLeftDatasetCount(targetCap);
          setRightDatasetCount(targetCap);
        }

        // Check if room has duplicate allocation for selected exam date
        fetch(`/api/check_duplicate?room_no=${encodeURIComponent(roomNo)}&exam_date=${encodeURIComponent(exDate)}`)
          .then(res => res.json())
          .then(data => {
            if (data.has_allocation && duplicateModal) {
              duplicateModal.classList.add("active");
            }
          });
      } else if (roomInfoCard) {
        roomInfoCard.style.display = "none";
      }
    });
  }

  // Duplicate modal actions
  if (duplicateModal) {
    if (btnDuplicateYes) {
      btnDuplicateYes.addEventListener("click", function() {
        duplicateModal.classList.remove("active");
      });
    }
    if (btnDuplicateNo) {
      btnDuplicateNo.addEventListener("click", function() {
        duplicateModal.classList.remove("active");
        if (roomSelect) roomSelect.value = "";
        if (roomInfoCard) roomInfoCard.style.display = "none";
      });
    }
  }

  // Bench mode toggle
  if (benchModeDouble && benchModeSingle && rightGroupContainer) {
    benchModeDouble.addEventListener("change", function() {
      if (this.checked) {
        rightGroupContainer.style.display = "block";
        if (roomSelect && roomSelect.selectedIndex > 0) {
          const cap = parseInt(roomSelect.options[roomSelect.selectedIndex].dataset.capacity);
          const halfCap = Math.ceil(cap / 2);
          setLeftDatasetCount(halfCap);
          setRightDatasetCount(halfCap);
        }
      }
    });
    benchModeSingle.addEventListener("change", function() {
      if (this.checked) {
        rightGroupContainer.style.display = "none";
        if (roomSelect && roomSelect.selectedIndex > 0) {
          const cap = parseInt(roomSelect.options[roomSelect.selectedIndex].dataset.capacity);
          setLeftDatasetCount(cap);
        }
      }
    });
  }

  // Left Mode Toggle
  function updateLeftModeUI() {
    if (leftModeDataset && leftModeDataset.checked) {
      leftDatasetInputs.style.display = "block";
      if (leftAutoInputs) leftAutoInputs.style.display = "none";
      if (leftManualInputs) leftManualInputs.style.display = "none";
      loadLeftDatasetPreview();
    } else if (leftModeAuto && leftModeAuto.checked) {
      leftDatasetInputs.style.display = "none";
      if (leftAutoInputs) leftAutoInputs.style.display = "flex";
      if (leftManualInputs) leftManualInputs.style.display = "none";
    } else if (leftModeManual && leftModeManual.checked) {
      leftDatasetInputs.style.display = "none";
      if (leftAutoInputs) leftAutoInputs.style.display = "none";
      if (leftManualInputs) leftManualInputs.style.display = "block";
    }
  }

  if (leftModeDataset) leftModeDataset.addEventListener("change", updateLeftModeUI);
  if (leftModeAuto) leftModeAuto.addEventListener("change", updateLeftModeUI);
  if (leftModeManual) leftModeManual.addEventListener("change", updateLeftModeUI);

  // Right Mode Toggle
  function updateRightModeUI() {
    if (rightModeDataset && rightModeDataset.checked) {
      rightDatasetInputs.style.display = "block";
      if (rightAutoInputs) rightAutoInputs.style.display = "none";
      if (rightManualInputs) rightManualInputs.style.display = "none";
      loadRightDatasetPreview();
    } else if (rightModeAuto && rightModeAuto.checked) {
      rightDatasetInputs.style.display = "none";
      if (rightAutoInputs) rightAutoInputs.style.display = "flex";
      if (rightManualInputs) rightManualInputs.style.display = "none";
    } else if (rightModeManual && rightModeManual.checked) {
      rightDatasetInputs.style.display = "none";
      if (rightAutoInputs) rightAutoInputs.style.display = "none";
      if (rightManualInputs) rightManualInputs.style.display = "block";
    }
  }

  if (rightModeDataset) rightModeDataset.addEventListener("change", updateRightModeUI);
  if (rightModeAuto) rightModeAuto.addEventListener("change", updateRightModeUI);
  if (rightModeManual) rightModeManual.addEventListener("change", updateRightModeUI);

  // Class inputs change -> trigger preview update
  ["left_college", "left_branch", "left_semester", "left_section"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", loadLeftDatasetPreview);
  });

  ["right_college", "right_branch", "right_semester", "right_section"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", loadRightDatasetPreview);
  });

  // Initial load
  updateLeftModeUI();
  updateRightModeUI();
});
