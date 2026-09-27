let currentFiles = new Map(); // key: path, value: { rawFile, path }
function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

function loadFiles(fileList, source) {
  if (!fileList || fileList.length === 0) return;

  const fileStatus = document.getElementById("fileStatusText");
  const dirStatus = document.getElementById("dirStatusText");

  for (const file of fileList) {
    const path = file.webkitRelativePath || file.name;
    currentFiles.set(path, {
      rawFile: file,
      path: path
    });
  }

  if (source === "file" && fileStatus) {
    fileStatus.textContent = `✓ Staged ${fileList.length} file(s)`;
    fileStatus.style.color = "#16a34a";
  } else if (source === "dir" && dirStatus) {
    dirStatus.textContent = `✓ Staged folder (${fileList.length} files)`;
    dirStatus.style.color = "#16a34a";
  }

  updateSummaryBadge();
  renderStagedTable();
}

window.deleteFile = function(path) {
  if (currentFiles.has(path)) {
    currentFiles.delete(path);
  }
  updateSummaryBadge();
  renderStagedTable();
};

function updateSummaryBadge() {
  const summaryBadge = document.getElementById("totalSummaryBadge");
  if (summaryBadge) {
    summaryBadge.textContent = `${currentFiles.size} file(s) staged`;
  }
}

async function setBaseline() {
  if (currentFiles.size === 0) {
    alert("Please upload files or a folder first!");
    return;
  }

  const formData = new FormData();
  for (const [path, item] of currentFiles.entries()) {
    formData.append("files", item.rawFile);
  }

  try {
    const res = await fetch("/api/save-baseline", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (data.error) {
      alert(data.error);
      return;
    }

    alert(data.message || "Baseline established by Python backend!");
    renderResultsTable(data.files);
  } catch (err) {
    alert("Could not connect to Python backend. Make sure app.py is running!");
    console.error(err);
  }
}

async function checkIntegrity() {
  if (currentFiles.size === 0) {
    alert("Please select files or a folder to verify against baseline.");
    return;
  }

  const formData = new FormData();
  for (const [path, item] of currentFiles.entries()) {
    formData.append("files", item.rawFile);
  }

  try {
    const res = await fetch("/api/check-integrity", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (data.error) {
      alert(data.error);
      return;
    }

    renderResultsTable(data.files);
  } catch (err) {
    alert("Could not connect to Python backend. Make sure app.py is running!");
    console.error(err);
  }
}
function renderStagedTable() {
  const tbody = document.getElementById("fileTable");
  if (!tbody) return;

  tbody.innerHTML = "";

  if (currentFiles.size === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-msg">No files selected. Choose files or a folder above.</td></tr>`;
    return;
  }

  currentFiles.forEach((item, path) => {
    const tr = document.createElement("tr");
    const safePath = path.replace(/'/g, "\\'");

    tr.innerHTML = `
      <td><span class="status status-ready">Staged</span></td>
      <td><strong>${item.rawFile.name}</strong><br><small style="color:#64748b;">${path}</small></td>
      <td>Pending Python Scan</td>
      <td>${formatSize(item.rawFile.size)}</td>
      <td class="hash-text">Awaiting Python...</td>
      <td><span class="threat-badge threat-pending">Unchecked</span></td>
      <td style="text-align: center;">
        <button class="btn-delete" onclick="deleteFile('${safePath}')" title="Delete file">✕ Delete</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderResultsTable(files) {
  const tbody = document.getElementById("fileTable");
  if (!tbody) return;

  tbody.innerHTML = "";

  files.forEach(info => {
    const tr = document.createElement("tr");

    let statusClass = "status-ready";
    if (info.status === "Intact") statusClass = "status-intact";
    if (info.status === "Modified") statusClass = "status-modified";
    if (info.status === "New") statusClass = "status-new";
    if (info.status === "Deleted") statusClass = "status-deleted";

    // Style threat badge
    const threatClass = info.is_threat ? "threat-danger" : "threat-safe";
    const threatDisplay = info.threat || "Clean";

    const safePath = info.name.replace(/'/g, "\\'");

    tr.innerHTML = `
      <td><span class="status ${statusClass}">${info.status}</span></td>
      <td><strong>${info.name}</strong></td>
      <td>${info.type}</td>
      <td>${info.size}</td>
      <td class="hash-text">${info.hash.length > 20 ? info.hash.substring(0, 18) + "..." : info.hash}</td>
      <td><span class="threat-badge ${threatClass}">${threatDisplay}</span></td>
      <td style="text-align: center;">
        <button class="btn-delete" onclick="deleteFile('${safePath}')" title="Delete file">✕ Delete</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}
async function resetAll() {
  try {
    await fetch("/api/reset", { method: "POST" });
  } catch (err) {
    console.warn("Backend reset ping failed:", err);
  }

  currentFiles.clear();

  const fileInput = document.getElementById("fileInput");
  const dirInput = document.getElementById("dirInput");
  const fileStatus = document.getElementById("fileStatusText");
  const dirStatus = document.getElementById("dirStatusText");

  if (fileInput) fileInput.value = "";
  if (dirInput) dirInput.value = "";
  if (fileStatus) {
    fileStatus.textContent = "No files chosen";
    fileStatus.style.color = "#2563eb";
  }
  if (dirStatus) {
    dirStatus.textContent = "No folder chosen";
    dirStatus.style.color = "#2563eb";
  }

  updateSummaryBadge();
  renderStagedTable();
}

// DOM Event Listeners
document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("fileInput");
  const dirInput = document.getElementById("dirInput");
  const setBaselineBtn = document.getElementById("setBaselineBtn");
  const checkIntegrityBtn = document.getElementById("checkIntegrityBtn");
  const resetBtn = document.getElementById("resetBtn");

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      loadFiles(e.target.files, "file");
      e.target.value = "";
    });
  }

  if (dirInput) {
    dirInput.addEventListener("change", (e) => {
      loadFiles(e.target.files, "dir");
      e.target.value = "";
    });
  }

  if (setBaselineBtn) setBaselineBtn.addEventListener("click", setBaseline);
  if (checkIntegrityBtn) checkIntegrityBtn.addEventListener("click", checkIntegrity);
  if (resetBtn) resetBtn.addEventListener("click", resetAll);
});