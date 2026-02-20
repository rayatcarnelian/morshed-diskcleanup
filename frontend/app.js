const API_URL = "";

async function startScan() {
    const path = document.getElementById('scan-path').value;
    const minSize = document.getElementById('min-size').value || 100;
    const onlyTemp = document.getElementById('only-temp').checked;
    const fileList = document.getElementById('file-list');
    fileList.innerHTML = '<p class="placeholder">Scanning... Please wait.</p>';

    try {
        const response = await fetch(`${API_URL}/scan?path=${encodeURIComponent(path)}&min_size_mb=${minSize}&only_temp=${onlyTemp}`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }

        const data = await response.json();
        console.log(data);

        // Start polling for results
        fileList.innerHTML = '<p class="placeholder">Scan started. Searching for large files...</p>';
        pollResults();

    } catch (error) {
        fileList.innerHTML = `<p class="placeholder" style="color: var(--danger-color)">Scan Failed: ${error.message}</p>`;
    }
}

let pollInterval;

function pollResults() {
    if (pollInterval) clearInterval(pollInterval);
    const fileList = document.getElementById('file-list');

    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/status`);
            if (!response.ok) return;
            const statusData = await response.json();

            if (statusData.status === "scanning") {
                fileList.innerHTML = `<p class="placeholder">Scanning... Files processed: ${statusData.files_processed} | Large files found: ${statusData.total_found}</p>`;
            } else if (statusData.status === "completed") {
                clearInterval(pollInterval);
                fetchFiles();
            } else if (statusData.status.startsWith("error")) {
                clearInterval(pollInterval);
                fileList.innerHTML = `<p class="placeholder" style="color: var(--danger-color)">Scan Failed: ${statusData.status}</p>`;
            }
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 1000);
}

let allFiles = [];

async function fetchFiles() {
    const fileList = document.getElementById('file-list');

    try {
        const response = await fetch(`${API_URL}/files`);
        allFiles = await response.json();
        renderFiles();
    } catch (error) {
        console.error('Failed to fetch files:', error);
    }
}

function applyFilters() {
    renderFiles();
}

function renderFiles() {
    const fileList = document.getElementById('file-list');
    const deleteSafeBtn = document.getElementById('delete-safe-btn');
    const sortBy = document.getElementById('sort-by').value;
    const filterCategory = document.getElementById('filter-category').value;

    let filteredFiles = allFiles;

    // Apply Category Filter
    if (filterCategory !== 'All') {
        filteredFiles = filteredFiles.filter(f => f.category === filterCategory);
    }

    // Apply Sort
    filteredFiles.sort((a, b) => {
        if (sortBy === 'largest') {
            return b.filesize_mb - a.filesize_mb;
        } else {
            return a.filesize_mb - b.filesize_mb;
        }
    });

    if (filteredFiles.length === 0) {
        fileList.innerHTML = '<p class="placeholder">No large files found.</p>';
        return;
    }

    fileList.innerHTML = '';
    let hasSafeFiles = false;

    filteredFiles.forEach(file => {
        if (file.is_safe_to_delete) hasSafeFiles = true;

        const item = document.createElement('div');
        item.className = 'file-item';
        const safetyBadge = file.is_safe_to_delete
            ? '<span class="safe-badge">Temp file (Safe)</span>'
            : '<span class="unsafe-badge">Not temp file (Review carefully)</span>';

        const deleteWarning = file.is_safe_to_delete
            ? "Are you sure you want to delete this file? This action cannot be undone."
            : "WARNING: This is not a temporary file. It might be an important personal or system file. Are you absolutely sure you want to FORCE DELETE it?";

        const deleteLabel = file.is_safe_to_delete ? "Delete" : "Force Delete";

        item.innerHTML = `
                <div class="file-info">
                    <span class="filename">${file.filename} ${safetyBadge}</span>
                    <span class="filepath">${file.filepath}</span>
                    <span class="filesize">${file.filesize_mb} MB</span>
                    <span class="filepath">Category: ${file.category}</span>
                </div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <button class="action-btn" onclick="openFileLocation(${file.id})">Show in Folder</button>
                    <button class="delete-btn" style="${file.is_safe_to_delete ? '' : 'background-color: #d32f2f;'}" onclick="deleteFile(${file.id}, \`${deleteWarning}\`)">${deleteLabel}</button>
                </div>
            `;
        fileList.appendChild(item);
    });

    if (deleteSafeBtn) {
        deleteSafeBtn.style.display = hasSafeFiles ? 'block' : 'none';
    }
}

async function deleteFile(id, warningMsg) {
    if (!confirm(warningMsg)) return;

    try {
        const response = await fetch(`${API_URL}/delete/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            alert("File deleted successfully!");
            fetchFiles(); // Refresh list
        } else {
            alert("Failed to delete file.");
        }
    } catch (error) {
        console.error('Error deleting file:', error);
    }
}

async function deleteAllSafe() {
    if (!confirm("Are you sure you want to delete ALL safe files? This process cannot be undone!")) return;

    const deleteSafeBtn = document.getElementById('delete-safe-btn');
    deleteSafeBtn.innerText = "Deleting...";
    deleteSafeBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/delete-all-safe`, {
            method: 'DELETE'
        });

        if (response.ok) {
            const result = await response.json();
            alert(result.message);
            fetchFiles();
        } else {
            alert("Failed to delete all safe files.");
        }
    } catch (error) {
        console.error('Error deleting safe files:', error);
        alert("An error occurred during bulk deletion.");
    } finally {
        deleteSafeBtn.innerText = "Delete All Safe Files";
        deleteSafeBtn.disabled = false;
    }
}

async function openFileLocation(id) {
    try {
        const response = await fetch(`${API_URL}/open/${id}`, {
            method: 'POST'
        });

        if (response.ok) {
            console.log("Opened file location.");
        } else {
            alert("Failed to open file location. The file might no longer exist.");
        }
    } catch (error) {
        console.error('Error opening file location:', error);
    }
}
