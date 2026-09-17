/* allocation.js - New Seating Arrangement Wizard, Section & Open Elective (OE) Allocation */

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
  const mode = document.querySelector('input[name="left_entry_mode"]:checked')?.value || "dataset";
  const college = document.getElementById("left_college")?.value || "GHRCE";
  const branch = document.getElementById("left_branch")?.value || "";
  const sem = document.getElementById("left_semester")?.value || "";
  const sec = document.getElementById("left_section")?.value || "";
  const oeSub = document.getElementById("left_oe_subject")?.value || "";
  const exDate = document.getElementById("exam_date")?.value || "";
  const count = document.getElementById("left_dataset_count")?.value || 15;
  const preview = document.getElementById("left_dataset_preview_text");

  if (!preview) return;

  if (mode === "oe") {
    if (!sem || !oeSub) {
      preview.textContent = "Select Semester & Open Elective (OE) Subject to load enrolled students.";
      return;
    }

    fetch(`/api/get_oe_students?semester=${encodeURIComponent(sem)}&open_elective=${encodeURIComponent(oeSub)}&exam_date=${encodeURIComponent(exDate)}&limit=${count}`)
      .then(res => res.json())
      .then(data => {
        if (data.students && data.students.length > 0) {
          const list = data.students.map(s => `${s.roll_no} (${s.branch}-${s.section})`).join(", ");
          let allocatedNotice = "";
          if (data.total_already_allocated > 0) {
            allocatedNotice = `<span style="color:#d97706; margin-left:0.5rem;"><i class="fa-solid fa-shield-halved"></i> (${data.total_already_allocated} students already allocated on ${exDate} automatically excluded)</span>`;
          }
          preview.innerHTML = `<strong>Selected ${data.students.length} Unallocated OE Students (out of ${data.total_active} taking '${oeSub}' in Sem ${sem}):</strong>${allocatedNotice}<br><code style="word-break:break-all;">${list}</code>`;
        } else if (data.total_active > 0) {
          preview.innerHTML = `<span style="color:#d97706;"><i class="fa-solid fa-triangle-exclamation"></i> All ${data.total_active} students taking '${oeSub}' in Sem ${sem} are already allocated to other rooms on ${exDate}.</span>`;
        } else {
          preview.textContent = `No active student records found for Open Elective '${oeSub}' in Sem ${sem}. Add OE choices in Student Management.`;
        }
      })
      .catch(() => {
        preview.textContent = "Error loading Open Elective student dataset preview.";
      });

  } else {
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
}

function loadRightDatasetPreview() {
  const mode = document.querySelector('input[name="right_entry_mode"]:checked')?.value || "dataset";
  const college = document.getElementById("right_college")?.value || "GHRCE";
  const branch = document.getElementById("right_branch")?.value || "";
  const sem = document.getElementById("right_semester")?.value || "";
  const sec = document.getElementById("right_section")?.value || "";
  const oeSub = document.getElementById("right_oe_subject")?.value || "";
  const exDate = document.getElementById("exam_date")?.value || "";
  const count = document.getElementById("right_dataset_count")?.value || 15;
  const preview = document.getElementById("right_dataset_preview_text");

  if (!preview) return;

  if (mode === "oe") {
    if (!sem || !oeSub) {
      preview.textContent = "Select Semester & Open Elective (OE) Subject to load enrolled students.";
      return;
    }

    fetch(`/api/get_oe_students?semester=${encodeURIComponent(sem)}&open_elective=${encodeURIComponent(oeSub)}&exam_date=${encodeURIComponent(exDate)}&limit=${count}`)
      .then(res => res.json())
      .then(data => {
        if (data.students && data.students.length > 0) {
          const list = data.students.map(s => `${s.roll_no} (${s.branch}-${s.section})`).join(", ");
          let allocatedNotice = "";
          if (data.total_already_allocated > 0) {
            allocatedNotice = `<span style="color:#d97706; margin-left:0.5rem;"><i class="fa-solid fa-shield-halved"></i> (${data.total_already_allocated} students already allocated on ${exDate} automatically excluded)</span>`;
          }
          preview.innerHTML = `<strong>Selected ${data.students.length} Unallocated OE Students (out of ${data.total_active} taking '${oeSub}' in Sem ${sem}):</strong>${allocatedNotice}<br><code style="word-break:break-all;">${list}</code>`;
        } else if (data.total_active > 0) {
          preview.innerHTML = `<span style="color:#d97706;"><i class="fa-solid fa-triangle-exclamation"></i> All ${data.total_active} students taking '${oeSub}' in Sem ${sem} are already allocated to other rooms on ${exDate}.</span>`;
        } else {
          preview.textContent = `No active student records found for Open Elective '${oeSub}' in Sem ${sem}. Add OE choices in Student Management.`;
        }
      })
      .catch(() => {
        preview.textContent = "Error loading Open Elective student dataset preview.";
      });

  } else {
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

  // Allocation Type Toggle (Section vs OE)
  const allocTypeSection = document.getElementById("alloc_type_section");
  const allocTypeOE = document.getElementById("alloc_type_oe");

  function updateAllocationTypeUI() {
    const isOE = allocTypeOE && allocTypeOE.checked;
    
    // Left Mode Elements
    const leftModeOE = document.getElementById("left_mode_oe");
    const leftModeDataset = document.getElementById("left_mode_dataset");
    const leftOEInputs = document.getElementById("left_oe_inputs");
    const leftSectionRow = document.getElementById("left_section_row");

    // Right Mode Elements
    const rightModeOE = document.getElementById("right_mode_oe");
    const rightModeDataset = document.getElementById("right_mode_dataset");
    const rightOEInputs = document.getElementById("right_oe_inputs");
    const rightSectionRow = document.getElementById("right_section_row");

    if (isOE) {
      if (leftModeOE) {
        leftModeOE.checked = true;
        leftModeOE.parentElement.style.display = "inline-flex";
      }
      if (rightModeOE) {
        rightModeOE.checked = true;
        rightModeOE.parentElement.style.display = "inline-flex";
      }
      if (leftOEInputs) leftOEInputs.style.display = "block";
      if (rightOEInputs) rightOEInputs.style.display = "block";
      if (leftSectionRow) leftSectionRow.style.display = "none";
      if (rightSectionRow) rightSectionRow.style.display = "none";
    } else {
      if (leftModeDataset) {
        leftModeDataset.checked = true;
      }
      if (rightModeDataset) {
        rightModeDataset.checked = true;
      }
      if (leftModeOE) leftModeOE.parentElement.style.display = "none";
      if (rightModeOE) rightModeOE.parentElement.style.display = "none";
      if (leftOEInputs) leftOEInputs.style.display = "none";
      if (rightOEInputs) rightOEInputs.style.display = "none";
      if (leftSectionRow) leftSectionRow.style.display = "grid";
      if (rightSectionRow) rightSectionRow.style.display = "grid";
    }
    updateLeftModeUI();
    updateRightModeUI();
  }

  if (allocTypeSection) allocTypeSection.addEventListener("change", updateAllocationTypeUI);
  if (allocTypeOE) allocTypeOE.addEventListener("change", updateAllocationTypeUI);

  // Left Mode Toggle
  function updateLeftModeUI() {
    const leftModeOE = document.getElementById("left_mode_oe");
    const leftModeDataset = document.getElementById("left_mode_dataset");
    const leftModeManual = document.getElementById("left_mode_manual");
    const leftDatasetInputs = document.getElementById("left_dataset_inputs");
    const leftManualInputs = document.getElementById("left_manual_inputs");

    if (leftDatasetInputs) leftDatasetInputs.style.display = "block";
    if (leftManualInputs) {
      leftManualInputs.style.display = (leftModeManual && leftModeManual.checked) ? "block" : "none";
    }
    loadLeftDatasetPreview();
  }

  const leftModes = document.querySelectorAll('input[name="left_entry_mode"]');
  leftModes.forEach(r => r.addEventListener("change", updateLeftModeUI));

  // Right Mode Toggle
  function updateRightModeUI() {
    const rightModeDataset = document.getElementById("right_mode_dataset");
    const rightModeManual = document.getElementById("right_mode_manual");
    const rightDatasetInputs = document.getElementById("right_dataset_inputs");
    const rightManualInputs = document.getElementById("right_manual_inputs");

    if (rightDatasetInputs) rightDatasetInputs.style.display = "block";
    if (rightManualInputs) {
      rightManualInputs.style.display = (rightModeManual && rightModeManual.checked) ? "block" : "none";
    }
    loadRightDatasetPreview();
  }

  const rightModes = document.querySelectorAll('input[name="right_entry_mode"]');
  rightModes.forEach(r => r.addEventListener("change", updateRightModeUI));

  // Exam Date change -> reload previews
  if (examDateInput) {
    examDateInput.addEventListener("change", function() {
      loadLeftDatasetPreview();
      loadRightDatasetPreview();

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

function toggleAllocationScopeUI() {
  const scopeMulti = document.getElementById("scope_multi");
  const seatingForm = document.getElementById("seatingForm");
  const singleGroup = document.getElementById("single_room_group");
  const multiGroup = document.getElementById("multi_room_group");
  const selectRoom = document.getElementById("select_room");

  if (scopeMulti && scopeMulti.checked) {
    if (seatingForm) seatingForm.action = "/auto_create_seating";
    if (singleGroup) singleGroup.style.display = "none";
    if (multiGroup) multiGroup.style.display = "block";
    if (selectRoom) selectRoom.required = false;
  } else {
    if (seatingForm) seatingForm.action = "/create_seating";
    if (singleGroup) singleGroup.style.display = "block";
    if (multiGroup) multiGroup.style.display = "none";
    if (selectRoom) selectRoom.required = true;
  }
}

  // Block change -> load rooms
  if (blockSelect) {
    blockSelect.addEventListener("change", function() {
      const block = this.value;
      if (roomSelect) roomSelect.innerHTML = '<option value="">-- Choose Room --</option>';
      const multiBox = document.getElementById("multi_room_checkboxes");
      if (multiBox) multiBox.innerHTML = '<span style="font-size: 0.82rem; color: var(--text-muted);">Loading rooms...</span>';
      if (roomInfoCard) roomInfoCard.style.display = "none";

      if (block) {
        fetch(`/api/get_rooms?block=${encodeURIComponent(block)}`)
          .then(res => res.json())
          .then(rooms => {
            if (multiBox) multiBox.innerHTML = '';
            rooms.forEach(r => {
              if (roomSelect) {
                const opt = document.createElement("option");
                opt.value = r.room_no;
                opt.textContent = `${r.room_no} (Cap: ${r.default_capacity})`;
                opt.dataset.capacity = r.default_capacity;
                opt.dataset.rows = r.default_rows;
                opt.dataset.layout = r.default_row_layout;
                opt.dataset.block = r.block;
                roomSelect.appendChild(opt);
              }
              if (multiBox) {
                const lbl = document.createElement("label");
                lbl.style.cssText = "display:inline-flex; align-items:center; gap:0.35rem; background:#fff; padding:0.4rem 0.75rem; border:1px solid #cbd5e1; border-radius:6px; cursor:pointer; font-size:0.85rem; font-weight:600;";
                lbl.innerHTML = `<input type="checkbox" name="selected_rooms" value="${r.room_no}" checked> Room ${r.room_no} (${r.default_capacity} seats)`;
                multiBox.appendChild(lbl);
              }
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

          const isSingle = benchModeSingle && benchModeSingle.checked;
          const targetCap = isSingle ? parseInt(selectedOpt.dataset.capacity) : Math.ceil(parseInt(selectedOpt.dataset.capacity) / 2);
          setLeftDatasetCount(targetCap);
          setRightDatasetCount(targetCap);
        }

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

  // Class / OE inputs change -> trigger preview update
  ["left_college", "left_branch", "left_semester", "left_section", "left_oe_subject"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", loadLeftDatasetPreview);
    if (el) el.addEventListener("change", loadLeftDatasetPreview);
  });

  ["right_college", "right_branch", "right_semester", "right_section", "right_oe_subject"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", loadRightDatasetPreview);
    if (el) el.addEventListener("change", loadRightDatasetPreview);
  });

  // Initial load
  updateAllocationTypeUI();
});
