// Sindbad.Tech SharePoint Doc Indexer - Frontend JavaScript

const API_BASE = '/api';
let currentJobId = null;
let statusPollInterval = null;

// DOM Elements
const discoverBtn = document.getElementById('discoverBtn');
const refreshBtn = document.getElementById('refreshBtn');
const stopResetBtn = document.getElementById('stopResetBtn');
const statusBadge = document.getElementById('statusBadge');
const progressContainer = document.getElementById('progressContainer');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const searchResults = document.getElementById('searchResults');
const clearSearchBtn = document.getElementById('clearSearchBtn');
const sitesList = document.getElementById('sitesList');
const filesList = document.getElementById('filesList');
const clearFilesBtn = document.getElementById('clearFilesBtn');
const errorMessage = document.getElementById('errorMessage');
const siteSelectionContainer = document.getElementById('siteSelectionContainer');
const siteSelectionList = document.getElementById('siteSelectionList');
const selectAllBtn = document.getElementById('selectAllBtn');
const deselectAllBtn = document.getElementById('deselectAllBtn');
const selectedCount = document.getElementById('selectedCount');

// State
let discoveredSites = [];
let selectedSiteIds = new Set();
// Track which sites have SharePoint and/or Email selected
let siteOptions = new Map(); // siteId -> { sharepoint: boolean, email: boolean }

// Stat elements
const statSites = document.getElementById('statSites');
const statFiles = document.getElementById('statFiles');
const statFileTypes = document.getElementById('statFileTypes');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Load user info first
    await loadUserInfo();
    
    loadStats();
    loadFiles();
    loadSites();
    
    // Check for any stale job status and reset UI if needed
    await checkAndResetStaleJob();
    
    discoverBtn.addEventListener('click', handleDiscover);
    refreshBtn.addEventListener('click', handleRefresh);
    stopResetBtn.addEventListener('click', handleStopAndReset);
    clearFilesBtn.addEventListener('click', handleClearFiles);
    clearSearchBtn.addEventListener('click', handleClearSearch);
    selectAllBtn.addEventListener('click', handleSelectAll);
    deselectAllBtn.addEventListener('click', handleDeselectAll);
    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });
});

// Load user info and display in header
async function loadUserInfo() {
    try {
        const response = await fetch('/api/user');
        if (response.ok) {
            const user = await response.json();
            const userNameEl = document.getElementById('userName');
            if (userNameEl && user.name) {
                userNameEl.textContent = user.name;
            }
        } else if (response.status === 401) {
            // Not authenticated, redirect to login
            window.location.href = '/auth/login';
        }
    } catch (error) {
        console.error('Error loading user info:', error);
        // If error, might not be authenticated
        if (error.message.includes('401') || error.message.includes('Unauthorized')) {
            window.location.href = '/auth/login';
        }
    }
}

// Check for stale job and reset UI if needed
async function checkAndResetStaleJob() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        if (response.ok) {
            const status = await response.json();
            // If job is completed, failed, or cancelled, reset UI
            if (status && (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled')) {
                refreshBtn.disabled = false;
                discoverBtn.disabled = false;
                progressContainer.classList.add('hidden');
                statusBadge.textContent = '';
                statusBadge.className = 'status-badge';
                statusBadge.classList.remove('active', 'running', 'completed', 'failed', 'cancelled');
            } else if (status && status.status === 'running') {
                // If job is still running, start polling
                currentJobId = status.job_id;
                showProgress();
                refreshBtn.disabled = true;
                discoverBtn.disabled = true;
                startStatusPolling();
            }
        } else if (response.status === 404) {
            // No job found, ensure buttons are enabled
            refreshBtn.disabled = false;
            discoverBtn.disabled = false;
            progressContainer.classList.add('hidden');
        }
    } catch (error) {
        // If status check fails, ensure buttons are enabled
        console.log('No active job found, enabling buttons');
        refreshBtn.disabled = false;
        discoverBtn.disabled = false;
    }
}

// Discover sites
async function handleDiscover() {
    try {
        discoverBtn.disabled = true;
        discoverBtn.textContent = 'Discovering...';
        hideError();
        
        const response = await fetch(`${API_BASE}/sites/discover`);
        
        if (!response.ok) {
            throw new Error('Failed to discover sites');
        }
        
        const data = await response.json();
        discoveredSites = data.sites || [];
        
        // Initialize site options (all unchecked by default)
        initializeSiteOptions();
        // Show site selection UI
        displaySiteSelection();
        discoverBtn.disabled = false;
        discoverBtn.textContent = '🔍 Discover Sites';
        
    } catch (error) {
        showError(`Failed to discover sites: ${error.message}`);
        discoverBtn.disabled = false;
        discoverBtn.textContent = '🔍 Discover Sites';
    }
}

// Display site selection (alphabetically sorted)
function displaySiteSelection() {
    if (discoveredSites.length === 0) {
        siteSelectionList.innerHTML = '<div class="loading">No sites found.</div>';
        return;
    }
    
    // Sort sites alphabetically by name
    const sortedSites = [...discoveredSites].sort((a, b) => {
        const nameA = (a.name || '').toLowerCase();
        const nameB = (b.name || '').toLowerCase();
        return nameA.localeCompare(nameB);
    });
    
    siteSelectionList.innerHTML = sortedSites.map(site => {
        const siteId = site.id;
        // Initialize with both options unchecked if not already set
        if (!siteOptions.has(siteId)) {
            siteOptions.set(siteId, { sharepoint: false, email: false });
        }
        const options = siteOptions.get(siteId);
        return `
        <div class="site-selection-item">
            <div class="site-selection-item-info">
                <div class="site-selection-item-name">${escapeHtml(site.name)}</div>
                <div class="site-selection-item-url">${escapeHtml(site.url)}</div>
            </div>
            <div class="site-selection-options">
                <label class="site-option-label">
                    <input 
                        type="checkbox" 
                        id="sharepoint-${siteId}" 
                        ${options.sharepoint ? 'checked' : ''}
                        onchange="handleOptionToggle('${siteId}', 'sharepoint')"
                    >
                    <span>Search SharePoint</span>
                </label>
                <label class="site-option-label">
                    <input 
                        type="checkbox" 
                        id="email-${siteId}" 
                        ${options.email ? 'checked' : ''}
                        onchange="handleOptionToggle('${siteId}', 'email')"
                    >
                    <span>Search Email</span>
                </label>
            </div>
        </div>
    `;
    }).join('');
    
    siteSelectionContainer.classList.remove('hidden');
    refreshBtn.style.display = 'inline-flex';
    updateSelectedCount();
}

// Handle option toggle (must be global for inline handlers)
window.handleOptionToggle = function(siteId, optionType) {
    const checkbox = document.getElementById(`${optionType}-${siteId}`);
    if (!siteOptions.has(siteId)) {
        siteOptions.set(siteId, { sharepoint: false, email: false });
    }
    const options = siteOptions.get(siteId);
    options[optionType] = checkbox.checked;
    
    // Update selectedSiteIds based on whether at least one option is selected
    const hasAnyOption = options.sharepoint || options.email;
    if (hasAnyOption) {
        selectedSiteIds.add(siteId);
    } else {
        selectedSiteIds.delete(siteId);
    }
    updateSelectedCount();
};

// Initialize site options when sites are discovered
function initializeSiteOptions() {
    discoveredSites.forEach(site => {
        const siteId = site.id;
        if (!siteOptions.has(siteId)) {
            siteOptions.set(siteId, { sharepoint: false, email: false });
        }
    });
    // Clear selected sites since nothing is checked by default
    selectedSiteIds.clear();
    updateSelectedCount();
}

// Select all sites
function handleSelectAll() {
    discoveredSites.forEach(site => {
        const siteId = site.id;
        selectedSiteIds.add(siteId);
        if (!siteOptions.has(siteId)) {
            siteOptions.set(siteId, { sharepoint: true, email: true });
        } else {
            siteOptions.get(siteId).sharepoint = true;
            siteOptions.get(siteId).email = true;
        }
        const sharepointCheckbox = document.getElementById(`sharepoint-${siteId}`);
        const emailCheckbox = document.getElementById(`email-${siteId}`);
        if (sharepointCheckbox) sharepointCheckbox.checked = true;
        if (emailCheckbox) emailCheckbox.checked = true;
    });
    updateSelectedCount();
}

// Deselect all sites
function handleDeselectAll() {
    selectedSiteIds.clear();
    discoveredSites.forEach(site => {
        const siteId = site.id;
        if (!siteOptions.has(siteId)) {
            siteOptions.set(siteId, { sharepoint: false, email: false });
        } else {
            siteOptions.get(siteId).sharepoint = false;
            siteOptions.get(siteId).email = false;
        }
        const sharepointCheckbox = document.getElementById(`sharepoint-${siteId}`);
        const emailCheckbox = document.getElementById(`email-${siteId}`);
        if (sharepointCheckbox) sharepointCheckbox.checked = false;
        if (emailCheckbox) emailCheckbox.checked = false;
    });
    updateSelectedCount();
}

// Update selected count
function updateSelectedCount() {
    const count = selectedSiteIds.size;
    selectedCount.textContent = `${count} site${count !== 1 ? 's' : ''} selected`;
}

// Stop and reset everything - one button that does it all
async function handleStopAndReset() {
    if (!confirm('This will stop all indexing processes, clear all indexed data, and reset the server state. Continue?')) {
        return;
    }
    
    try {
        stopResetBtn.disabled = true;
        stopResetBtn.innerHTML = '<span class="btn-icon">⏳</span> Stopping...';
        hideError();
        
        // Stop any ongoing status polling immediately
        stopStatusPolling();
        
        // Try to cancel first if there's an active job
        if (currentJobId) {
            try {
                await fetch(`${API_BASE}/cancel`, { method: 'POST' });
            } catch (e) {
                // Ignore cancel errors - continue with reset
            }
        }
        
        // Call clear-all to reset everything
        const response = await fetch(`${API_BASE}/clear-all`, {
            method: 'POST',
        });
        
        if (!response.ok) {
            throw new Error('Failed to stop and reset');
        }
        
        const data = await response.json();
        
        // Force reset all UI elements
        filesList.innerHTML = '<div class="loading">No files displayed. Click "Index Selected Sites" to load files.</div>';
        sitesList.innerHTML = '<div class="loading">No sites displayed. Click "Index Selected Sites" to load sites.</div>';
        searchResults.innerHTML = '';
        searchResults.classList.add('hidden');
        searchInput.value = '';
        
        // Hide progress
        progressContainer.classList.add('hidden');
        refreshBtn.style.display = 'none';
        clearFilesBtn.style.display = 'none';
        siteSelectionContainer.classList.add('hidden');
        
        // Reset status badge
        statusBadge.textContent = '';
        statusBadge.className = 'status-badge';
        statusBadge.classList.remove('active', 'running', 'completed', 'failed', 'cancelled');
        
        // Force enable all buttons
        discoverBtn.disabled = false;
        refreshBtn.disabled = false;
        
        // Reset site selection
        selectedSiteIds.clear();
        siteOptions.clear();
        discoveredSites = [];
        siteSelectionList.innerHTML = '';
        currentJobId = null;
        
        // Reset statistics
        await loadStats();
        
        // Hide search results header
        const searchResultsHeader = document.getElementById('searchResultsHeader');
        if (searchResultsHeader) {
            searchResultsHeader.style.display = 'none';
        }
        
        showSuccess('All processes stopped and data cleared successfully.');
        
    } catch (error) {
        showError(`Failed to stop and reset: ${error.message}`);
    } finally {
        stopResetBtn.disabled = false;
        stopResetBtn.innerHTML = '<span class="btn-icon">⏹️</span> Stop & Reset All';
    }
}

// Refresh index
async function handleRefresh() {
    try {
        // Check if at least one site has at least one option selected
        const hasAnySelection = Array.from(selectedSiteIds).some(siteId => {
            const options = siteOptions.get(siteId) || { sharepoint: false, email: false };
            return options.sharepoint || options.email;
        });
        
        if (!hasAnySelection || selectedSiteIds.size === 0) {
            showError('Please select at least one site with at least one option (SharePoint or Email) to index');
            return;
        }
        
        refreshBtn.disabled = true;
        discoverBtn.disabled = true; // Disable discover during indexing
        hideError();
        
        // Build request with site options
        const sitesConfig = Array.from(selectedSiteIds).map(siteId => {
            const options = siteOptions.get(siteId) || { sharepoint: true, email: true };
            return {
                site_id: siteId,
                index_sharepoint: options.sharepoint,
                index_email: options.email
            };
        });
        
        const response = await fetch(`${API_BASE}/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ sites: sitesConfig }),
        });
        
        if (!response.ok) {
            throw new Error('Failed to start indexing');
        }
        
        const data = await response.json();
        currentJobId = data.job_id;
        
        showProgress();
        startStatusPolling();
        
        // Hide site selection after starting
        siteSelectionContainer.classList.add('hidden');
        
    } catch (error) {
        showError(`Failed to start indexing: ${error.message}`);
        refreshBtn.disabled = false;
    }
}

// Poll for status updates
function startStatusPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
    }
    
    statusPollInterval = setInterval(async () => {
        try {
            const url = currentJobId 
                ? `${API_BASE}/status?job_id=${currentJobId}`
                : `${API_BASE}/status`;
            
            const response = await fetch(url);
            
            if (!response.ok) {
                if (response.status === 404) {
                    // Job not found or completed - stop polling and reset UI
                    stopStatusPolling();
                    refreshBtn.disabled = false;
                    discoverBtn.disabled = false;
                    progressContainer.classList.add('hidden');
                    statusBadge.textContent = '';
                    statusBadge.className = 'status-badge';
                    statusBadge.classList.remove('active', 'running', 'completed', 'failed', 'cancelled');
                    currentJobId = null;
                    // Reload data if job was likely completed
                    await loadStats();
                    await loadFiles();
                    await loadSites();
                    return;
                }
                throw new Error('Failed to get status');
            }
            
            const status = await response.json();
            
            // If no status or status is null, stop polling and reset UI
            if (!status || !status.status) {
                stopStatusPolling();
                refreshBtn.disabled = false;
                discoverBtn.disabled = false;
                progressContainer.classList.add('hidden');
                statusBadge.textContent = '';
                statusBadge.className = 'status-badge';
                statusBadge.classList.remove('active', 'running', 'completed', 'failed', 'cancelled');
                return;
            }
            
            updateProgress(status);
            
            if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
                stopStatusPolling();
                // Force enable buttons immediately
                refreshBtn.disabled = false;
                discoverBtn.disabled = false;
                progressContainer.classList.add('hidden');
                
                // Clear current job ID to prevent stale state
                currentJobId = null;
                
                if (status.status === 'completed') {
                    // Reload stats, files, and sites
                    await loadStats();
                    await loadFiles();
                    await loadSites();
                } else if (status.status === 'cancelled') {
                    // Don't show error for cancelled - it's expected
                    hideError();
                } else {
                    showError(`Indexing failed: ${status.error_message || 'Unknown error'}`);
                }
            }
            
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 2000); // Poll every 2 seconds
}

function stopStatusPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
        statusPollInterval = null;
    }
}

// Update progress UI
function updateProgress(status) {
    const progress = (status.progress || 0) * 100;
    
    // Animate progress bar - ensure minimum width when running for visibility
    if (status.status === 'running' && progress < 3) {
        progressFill.style.width = '3%';
    } else {
        progressFill.style.width = `${progress}%`;
    }
    
    // Add moving animation class when running
    if (status.status === 'running') {
        progressFill.classList.add('progress-moving');
        progressContainer.classList.add('progress-active');
    } else {
        progressFill.classList.remove('progress-moving');
        progressContainer.classList.remove('progress-active');
    }
    
    let statusText = `Progress: ${Math.round(progress)}%`;
    if (status.current_site) {
        statusText += ` - Site: ${status.current_site}`;
    }
    if (status.current_folder) {
        statusText += ` - Folder: ${status.current_folder}`;
    }
    if (status.sites_processed && status.total_sites) {
        statusText += ` (${status.sites_processed}/${status.total_sites} sites)`;
    }
    if (status.files_processed) {
        statusText += ` - ${status.files_processed} files processed`;
    }
    if (status.folders_processed) {
        statusText += ` - ${status.folders_processed} folders processed`;
    }
    
    progressText.textContent = statusText;
    
    // Update status badge
    statusBadge.textContent = status.status.toUpperCase();
    statusBadge.className = `status-badge active ${status.status}`;
}

function showProgress() {
    progressContainer.classList.remove('hidden');
    statusBadge.className = 'status-badge active running';
    statusBadge.textContent = 'RUNNING';
}

function hideProgress() {
    progressContainer.classList.add('hidden');
    statusBadge.className = 'status-badge';
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/index/stats`);
        if (!response.ok) {
            throw new Error('Failed to load stats');
        }
        
        const stats = await response.json();
        
        statSites.textContent = formatNumber(stats.total_sites);
        statFiles.textContent = formatNumber(stats.total_files);
        
        // Display file types breakdown
        if (stats.file_types && Object.keys(stats.file_types).length > 0) {
            // Sort by count (descending) and take top 5
            const sortedTypes = Object.entries(stats.file_types)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);
            
            const typesText = sortedTypes
                .map(([type, count]) => `${type}: ${formatNumber(count)}`)
                .join(', ');
            
            statFileTypes.textContent = typesText;
        } else {
            statFileTypes.textContent = '-';
        }
        
    } catch (error) {
        console.error('Error loading stats:', error);
        statSites.textContent = '-';
        statFiles.textContent = '-';
        statFileTypes.textContent = '-';
    }
}

// Clear view (files and sites)
function handleClearFiles() {
    filesList.innerHTML = '<div class="loading">No files displayed. Click "Index Selected Sites" to load files.</div>';
    sitesList.innerHTML = '<div class="loading">No sites displayed. Click "Index Selected Sites" to load sites.</div>';
    clearFilesBtn.style.display = 'none';
}

// Clear search results (must be global for onclick handler)
window.handleClearSearch = function() {
    searchResults.innerHTML = '';
    searchResults.classList.add('hidden');
    searchInput.value = '';
    const searchResultsHeader = document.getElementById('searchResultsHeader');
    if (searchResultsHeader) {
        searchResultsHeader.style.display = 'none';
    }
};

// Load all files in table format
async function loadFiles() {
    try {
        filesList.innerHTML = '<div class="loading">Loading files...</div>';
        
        const response = await fetch(`${API_BASE}/files?limit=500`);
        if (!response.ok) {
            throw new Error('Failed to load files');
        }
        
        const data = await response.json();
        
        if (data.items.length === 0) {
            filesList.innerHTML = '<div class="loading">No files indexed yet. Click "Index Selected Sites" to start.</div>';
            return;
        }
        
        // Simple table with file data
        clearFilesBtn.style.display = 'inline-flex';
        filesList.innerHTML = `
            <table class="files-table" id="filesTable">
                <thead>
                    <tr>
                        <th class="sortable" data-sort="name">File Name</th>
                        <th class="sortable" data-sort="type">Type</th>
                        <th class="sortable" data-sort="source">Source</th>
                        <th class="sortable" data-sort="created">Date Created</th>
                        <th class="sortable" data-sort="modified">Date Modified</th>
                        <th class="sortable" data-sort="owner">Owner</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.items.map(file => {
                        const sourceLabel = file.source === 'email' ? '📧 Email' : '📁 SharePoint';
                        const sourceClass = file.source === 'email' ? 'source-email' : 'source-sharepoint';
                        return `
                        <tr>
                            <td data-sort="name">${escapeHtml(file.name)}<br><a href="${escapeHtml(file.url)}" target="_blank" class="file-link">Open</a></td>
                            <td data-sort="type">${escapeHtml(file.type || '-')}</td>
                            <td data-sort="source" data-sort-value="${file.source || 'sharepoint'}" class="${sourceClass}">${sourceLabel}</td>
                            <td data-sort="created" data-sort-value="${file.created_date || ''}">${file.created_date ? formatDate(file.created_date) : '-'}</td>
                            <td data-sort="modified" data-sort-value="${file.modified_date || ''}">${file.modified_date ? formatDate(file.modified_date) : '-'}</td>
                            <td data-sort="owner">${escapeHtml(file.owner || '-')}</td>
                        </tr>
                    `;
                    }).join('')}
                </tbody>
            </table>
        `;
        
        // Initialize table sorting
        initTableSorting('filesTable');
        
    } catch (error) {
        console.error('Error loading files:', error);
        filesList.innerHTML = '<div class="loading">Error loading files. Please try again.</div>';
    }
}

// Load sites
async function loadSites() {
    try {
        sitesList.innerHTML = '<div class="loading">Loading sites...</div>';
        
        const response = await fetch(`${API_BASE}/index?limit=100`);
        if (!response.ok) {
            throw new Error('Failed to load sites');
        }
        
        const data = await response.json();
        
        if (data.items.length === 0) {
            sitesList.innerHTML = '<div class="loading">No sites indexed yet. Click "Refresh Index" to start.</div>';
            return;
        }
        
        sitesList.innerHTML = data.items.map(site => `
            <div class="site-card">
                <h3>${escapeHtml(site.site_name)}</h3>
                <div class="site-url">${escapeHtml(site.site_url)}</div>
                <div class="site-stats">
                    <span>📄 ${formatNumber(site.total_files)} files</span>
                    <span>📁 ${formatNumber(site.total_folders)} folders</span>
                    <span>💾 ${formatBytes(site.total_size)}</span>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading sites:', error);
        sitesList.innerHTML = '<div class="loading">Error loading sites. Please try again.</div>';
    }
}

// Search files
async function handleSearch() {
    const query = searchInput.value.trim();
    
    if (!query) {
        showError('Please enter a search query');
        return;
    }
    
    try {
        hideError();
        searchResults.classList.remove('hidden');
        searchResults.innerHTML = '<div class="loading">Searching...</div>';
        
        // Properly encode query including Arabic/Unicode characters
        const encodedQuery = encodeURIComponent(query);
        const response = await fetch(`${API_BASE}/search?q=${encodedQuery}&limit=50`);
        if (!response.ok) {
            throw new Error('Search failed');
        }
        
        const data = await response.json();
        
        if (data.items.length === 0) {
            searchResults.innerHTML = '<div class="loading">No results found.</div>';
            return;
        }
        
        const searchResultsHeader = document.getElementById('searchResultsHeader');
        if (searchResultsHeader) {
            searchResultsHeader.style.display = 'block';
        }
        
        // Build search results HTML with header and clear button
        const resultsHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0;">Search Results (${data.total} found)</h3>
                <button id="clearSearchResultsBtn" class="btn btn-secondary btn-small" onclick="handleClearSearch()">
                    Clear Results
                </button>
            </div>
            <table class="files-table" id="searchTable">
                <thead>
                    <tr>
                        <th class="sortable" data-sort="name">File Name</th>
                        <th class="sortable" data-sort="type">Type</th>
                        <th class="sortable" data-sort="source">Source</th>
                        <th class="sortable" data-sort="created">Date Created</th>
                        <th class="sortable" data-sort="modified">Date Modified</th>
                        <th class="sortable" data-sort="owner">Owner</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.items.map(item => {
                        const sourceLabel = item.source === 'email' ? '📧 Email' : '📁 SharePoint';
                        const sourceClass = item.source === 'email' ? 'source-email' : 'source-sharepoint';
                        return `
                        <tr>
                            <td data-sort="name">${escapeHtml(item.name)}<br><a href="${escapeHtml(item.url)}" target="_blank" class="file-link">Open</a></td>
                            <td data-sort="type">${escapeHtml(item.type || '-')}</td>
                            <td data-sort="source" data-sort-value="${item.source || 'sharepoint'}" class="${sourceClass}">${sourceLabel}</td>
                            <td data-sort="created" data-sort-value="${item.created_date || ''}">${item.created_date ? formatDate(item.created_date) : '-'}</td>
                            <td data-sort="modified" data-sort-value="${item.modified_date || ''}">${item.modified_date ? formatDate(item.modified_date) : '-'}</td>
                            <td data-sort="owner">${escapeHtml(item.owner || '-')}</td>
                        </tr>
                    `;
                    }).join('')}
                </tbody>
            </table>
        `;
        
        searchResults.innerHTML = resultsHTML;
        
        // Initialize table sorting
        initTableSorting('searchTable');
        
    } catch (error) {
        showError(`Search failed: ${error.message}`);
        searchResults.innerHTML = '';
    }
}

// Utility functions
function formatNumber(num) {
    if (num === null || num === undefined) return '-';
    return new Intl.NumberFormat().format(num);
}

function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return '-';
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return '-';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
    errorMessage.style.background = '#dc3545';
    errorMessage.style.color = 'white';
}

function showSuccess(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
    errorMessage.style.background = '#28a745';
    errorMessage.style.color = 'white';
    // Auto-hide after 5 seconds
    setTimeout(() => {
        hideError();
    }, 5000);
}

function hideError() {
    errorMessage.classList.add('hidden');
}

// Table sorting functionality
function initTableSorting(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const headers = table.querySelectorAll('th.sortable');
    let currentSort = { column: null, direction: 'asc' };
    
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.getAttribute('data-sort');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            // Determine sort direction
            if (currentSort.column === column) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.column = column;
                currentSort.direction = 'asc';
            }
            
            // Remove sort classes from all headers
            headers.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            
            // Add sort class to current header
            header.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            
            // Sort rows
            rows.sort((a, b) => {
                const aCell = a.querySelector(`td[data-sort="${column}"]`);
                const bCell = b.querySelector(`td[data-sort="${column}"]`);
                
                if (!aCell || !bCell) return 0;
                
                let aValue = aCell.getAttribute('data-sort-value') || aCell.textContent.trim();
                let bValue = bCell.getAttribute('data-sort-value') || bCell.textContent.trim();
                
                // Handle dates
                if (column === 'created' || column === 'modified') {
                    aValue = aValue ? new Date(aValue).getTime() : 0;
                    bValue = bValue ? new Date(bValue).getTime() : 0;
                } else {
                    // String comparison
                    aValue = aValue.toLowerCase();
                    bValue = bValue.toLowerCase();
                }
                
                if (aValue < bValue) return currentSort.direction === 'asc' ? -1 : 1;
                if (aValue > bValue) return currentSort.direction === 'asc' ? 1 : -1;
                return 0;
            });
            
            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        });
    });
}

