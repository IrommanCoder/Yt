// Main JavaScript for YouTube Downloader

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const urlInput = document.getElementById('url');
    const searchInput = document.getElementById('search-input');
    const qualitySelect = document.querySelectorAll('input[name="quality"]');
    const formatSelect = document.querySelectorAll('input[name="format_type"]');
    const playlistCheckbox = document.getElementById('playlist-download');
    const getInfoBtn = document.getElementById('get-info-btn');
    const downloadBtn = document.getElementById('download-btn');
    const searchBtn = document.getElementById('search-btn');
    const videoInfoContainer = document.getElementById('video-info-container');
    const searchResultsContainer = document.getElementById('search-results');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const statusMessage = document.getElementById('status-message');
    const downloadResult = document.getElementById('download-result');
    
    let currentVideoInfo = null;
    
    // Helper Functions
    function showStatus(message, type = 'info') {
        statusMessage.textContent = message;
        statusMessage.className = `status-message ${type}`;
        statusMessage.style.display = 'block';
        
        if (type === 'success' || type === 'error') {
            setTimeout(() => {
                statusMessage.style.display = 'none';
            }, 5000);
        }
    }
    
    function hideStatus() {
        statusMessage.style.display = 'none';
    }
    
    function setLoading(element, loading = true) {
        if (loading) {
            element.disabled = true;
            if (!element.querySelector('.spinner')) {
                const originalText = element.textContent;
                element.dataset.originalText = originalText;
                element.innerHTML = '<span class="spinner"></span> Loading...';
            }
        } else {
            element.disabled = false;
            if (element.dataset.originalText) {
                element.textContent = element.dataset.originalText;
            }
        }
    }
    
    function updateProgress(percent, text = '') {
        progressFill.style.width = `${percent}%`;
        progressFill.textContent = `${Math.round(percent)}%`;
        if (text) {
            progressText.textContent = text;
        }
        progressContainer.style.display = 'block';
    }
    
    function resetProgress() {
        progressFill.style.width = '0%';
        progressFill.textContent = '';
        progressText.textContent = '';
        progressContainer.style.display = 'none';
    }
    
    function getSelectedQuality() {
        for (const radio of qualitySelect) {
            if (radio.checked) return radio.value;
        }
        return '720p';
    }
    
    function getSelectedFormat() {
        for (const radio of formatSelect) {
            if (radio.checked) return radio.value;
        }
        return 'video';
    }
    
    function formatDuration(seconds) {
        if (!seconds || seconds <= 0) return 'Unknown';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        
        if (h > 0) {
            return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }
        return `${m}:${s.toString().padStart(2, '0')}`;
    }
    
    function formatViews(count) {
        if (!count || count <= 0) return '0';
        if (count >= 1e9) return `${(count / 1e9).toFixed(2)}B`;
        if (count >= 1e6) return `${(count / 1e6).toFixed(2)}M`;
        if (count >= 1e3) return `${(count / 1e3).toFixed(2)}K`;
        return count.toString();
    }
    
    // Get Video Info
    async function getVideoInfo(url) {
        if (!url) {
            showStatus('Please enter a YouTube URL', 'error');
            return;
        }
        
        hideStatus();
        setLoading(getInfoBtn, true);
        videoInfoContainer.innerHTML = '';
        downloadResult.classList.add('hidden');
        resetProgress();
        
        try {
            const formData = new FormData();
            formData.append('url', url);
            
            const response = await fetch('/api/info', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to get video info');
            }
            
            currentVideoInfo = await response.json();
            displayVideoInfo(currentVideoInfo);
            
        } catch (error) {
            showStatus(`Error: ${error.message}`, 'error');
            console.error('Get info error:', error);
        } finally {
            setLoading(getInfoBtn, false);
        }
    }
    
    function displayVideoInfo(info) {
        if (info.is_playlist) {
            videoInfoContainer.innerHTML = `
                <div class="video-info-display">
                    <div class="video-details" style="flex: 1;">
                        <h3>${escapeHtml(info.title)}</h3>
                        <div class="video-meta">
                            <p><strong>Type:</strong> Playlist</p>
                            <p><strong>Videos:</strong> ${info.playlist_count}</p>
                            <p><strong>Uploader:</strong> ${escapeHtml(info.uploader)}</p>
                        </div>
                        ${info.description ? `
                            <div class="video-description">${escapeHtml(info.description)}</div>
                        ` : ''}
                    </div>
                </div>
                <div style="margin-top: 20px;">
                    <button id="start-playlist-download" class="btn btn-success">
                        Download Playlist (${info.playlist_count} videos)
                    </button>
                </div>
            `;
            
            document.getElementById('start-playlist-download').addEventListener('click', () => {
                startDownload(info.id, true);
            });
        } else {
            videoInfoContainer.innerHTML = `
                <div class="video-info-display">
                    <div class="video-thumbnail">
                        <img src="${escapeHtml(info.thumbnail)}" alt="${escapeHtml(info.title)}">
                    </div>
                    <div class="video-details">
                        <h3>${escapeHtml(info.title)}</h3>
                        <div class="video-meta">
                            <p><strong>Duration:</strong> ${formatDuration(info.duration)}</p>
                            <p><strong>Views:</strong> ${formatViews(info.view_count)}</p>
                            <p><strong>Uploader:</strong> ${escapeHtml(info.uploader)}</p>
                        </div>
                        ${info.description ? `
                            <div class="video-description">${escapeHtml(info.description)}</div>
                        ` : ''}
                    </div>
                </div>
            `;
        }
        
        downloadBtn.disabled = false;
    }
    
    // Start Download
    async function startDownload(url, isPlaylist = false) {
        if (!url) {
            showStatus('No video selected', 'error');
            return;
        }
        
        hideStatus();
        setLoading(downloadBtn, true);
        downloadResult.classList.add('hidden');
        resetProgress();
        
        const quality = getSelectedQuality();
        const formatType = getSelectedFormat();
        
        try {
            const formData = new FormData();
            formData.append('url', url);
            formData.append('quality', quality);
            formData.append('format_type', formatType);
            
            const response = await fetch('/api/download', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Download failed');
            }
            
            const result = await response.json();
            
            if (result.success) {
                if (result.is_playlist) {
                    showStatus(result.message, 'success');
                    downloadResult.innerHTML = `
                        <p style="margin-bottom: 15px;">${escapeHtml(result.message)}</p>
                        <a href="/history" class="btn btn-secondary">View History</a>
                    `;
                } else {
                    showStatus(result.message, 'success');
                    downloadResult.innerHTML = `
                        <p style="margin-bottom: 15px;"><strong>Download Ready:</strong> ${escapeHtml(result.title)}</p>
                        <a href="${result.download_url}" class="btn btn-success" download>
                            Download File
                        </a>
                        <a href="/stream/${result.filename}" class="btn btn-secondary" target="_blank" style="margin-left: 10px;">
                            Stream/Play
                        </a>
                    `;
                }
                downloadResult.classList.remove('hidden');
            }
            
        } catch (error) {
            showStatus(`Download failed: ${error.message}`, 'error');
            console.error('Download error:', error);
        } finally {
            setLoading(downloadBtn, false);
        }
    }
    
    // Search YouTube
    async function searchYouTube(query) {
        if (!query || query.trim().length === 0) {
            showStatus('Please enter a search query', 'error');
            return;
        }
        
        hideStatus();
        setLoading(searchBtn, true);
        searchResultsContainer.innerHTML = '';
        
        try {
            const formData = new FormData();
            formData.append('query', query.trim());
            
            const response = await fetch('/api/search', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Search failed');
            }
            
            const results = await response.json();
            displaySearchResults(results);
            
        } catch (error) {
            showStatus(`Search error: ${error.message}`, 'error');
            console.error('Search error:', error);
        } finally {
            setLoading(searchBtn, false);
        }
    }
    
    function displaySearchResults(results) {
        if (!results || results.length === 0) {
            searchResultsContainer.innerHTML = '<p>No results found.</p>';
            return;
        }
        
        const html = results.map(result => `
            <div class="search-result-card">
                <img src="${escapeHtml(result.thumbnail)}" alt="${escapeHtml(result.title)}" 
                     onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIwIiBoZWlnaHQ9IjE4MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMzMzIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiM2NjYiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0Ij5ObyBUaHVtYm5haWw8L3RleHQ+PC9zdmc+'">
                <div class="search-result-info">
                    <h3>${escapeHtml(result.title)}</h3>
                    <div class="search-result-meta">
                        <span>${formatDuration(result.duration)}</span> • 
                        <span>${formatViews(result.view_count)} views</span> • 
                        <span>${escapeHtml(result.uploader)}</span>
                    </div>
                    <div class="search-result-actions">
                        <button class="btn btn-sm" onclick="selectAndDownload('${escapeHtml(result.url)}')">
                            Download
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="fillUrl('${escapeHtml(result.url)}')">
                            Select
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
        searchResultsContainer.innerHTML = html;
    }
    
    // Global functions for inline event handlers
    window.selectAndDownload = function(url) {
        urlInput.value = url;
        getVideoInfo(url);
        // Scroll to download section
        document.getElementById('download-section').scrollIntoView({ behavior: 'smooth' });
    };
    
    window.fillUrl = function(url) {
        urlInput.value = url;
        urlInput.focus();
    };
    
    // Escape HTML to prevent XSS
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Event Listeners
    if (getInfoBtn) {
        getInfoBtn.addEventListener('click', () => {
            getVideoInfo(urlInput.value);
        });
    }
    
    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            if (currentVideoInfo) {
                const url = currentVideoInfo.is_playlist 
                    ? `https://www.youtube.com/playlist?list=${currentVideoInfo.id}`
                    : `https://www.youtube.com/watch?v=${currentVideoInfo.id}`;
                startDownload(url, currentVideoInfo.is_playlist);
            } else if (urlInput.value) {
                startDownload(urlInput.value, false);
            } else {
                showStatus('Please enter a URL or get video info first', 'error');
            }
        });
    }
    
    if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', () => {
            searchYouTube(searchInput.value);
        });
        
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchYouTube(searchInput.value);
            }
        });
    }
    
    if (urlInput) {
        urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                getVideoInfo(urlInput.value);
            }
        });
        
        // Auto-detect YouTube URL from clipboard on focus (optional)
        urlInput.addEventListener('focus', async () => {
            try {
                const clipboardText = await navigator.clipboard.readText();
                if (clipboardText.includes('youtube.com') || clipboardText.includes('youtu.be')) {
                    urlInput.value = clipboardText;
                }
            } catch (err) {
                // Clipboard access not permitted, ignore
            }
        });
    }
    
    // Format toggle behavior
    formatSelect.forEach(radio => {
        radio.addEventListener('change', () => {
            if (radio.value === 'audio') {
                // Show audio-specific options if needed
                console.log('Audio mode selected');
            }
        });
    });
    
    // Initialize
    downloadBtn.disabled = true;
    console.log('YouTube Downloader initialized');
});
