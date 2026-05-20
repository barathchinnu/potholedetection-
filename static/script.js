// Initialize Map
const map = L.map('map').setView([11.2748, 77.5828], 14); // Default to Perundurai

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap'
}).addTo(map);

// Custom Marker Icon
const potholeIcon = L.divIcon({
    className: 'custom-div-icon',
    html: `<div style="background-color: var(--accent); width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 15px rgba(255, 71, 87, 0.8); animation: pulse 2s infinite;"></div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10]
});

// State
let documentedDetections = new Set();
let markers = [];
let mapCentered = false;

// 🟢 Browser Geolocation Tracking (Live Device GPS -> Backend)
if (navigator.geolocation) {
    navigator.geolocation.watchPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            
            // Send high-accuracy GPS to backend in background
            fetch('/api/update_location', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({lat, lon})
            }).catch(err => console.error("Could not update GPS:", err));
            
            // Auto-center map on your location once immediately on load
            if (!mapCentered) {
                map.setView([lat, lon], 16);
                mapCentered = true;
                
                // Add a small generic marker to show user location roughly? Optional.
                L.marker([lat, lon], {
                    title: "Live Position"
                }).addTo(map).bindPopup("<b>Your live location tracking is active.</b>");
            }
        },
        (error) => {
            console.warn("Geolocation tracking error:", error);
        },
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
    );
} else {
    console.warn("Geolocation API not supported by this browser.");
}

// Polling function
async function fetchDetections() {
    try {
        const response = await fetch('/api/detections');
        const data = await response.json();
        
        updateDashboard(data);
    } catch (error) {
        console.error("Error fetching detections:", error);
    }
}

function updateDashboard(detections) {
    const logList = document.getElementById('log-list');
    const countBadge = document.getElementById('detection-count');
    
    if (detections.length === 0) return;

    // Update count
    countBadge.textContent = detections.length;

    // Check for new detections
    let isNew = false;
    
    // Sort array by ID descending to show newest first
    detections.forEach(det => {
        if (!documentedDetections.has(det.id)) {
            documentedDetections.add(det.id);
            isNew = true;
            
            // Remove empty state if it's the first
            const emptyState = logList.querySelector('.empty-state');
            if(emptyState) {
                emptyState.remove();
            }

            // Create Sidebar Item
            const item = document.createElement('div');
            item.className = 'log-item new-detection';
            item.innerHTML = `
                <div class="log-item-header">
                    <span><i class="fa-solid fa-triangle-exclamation" style="color: var(--accent); margin-right: 6px;"></i> Hole #${det.id}</span>
                    <span class="log-time">${det.time}</span>
                </div>
                <div class="log-coords">
                    ${det.lat.toFixed(5)}, ${det.lon.toFixed(5)}
                </div>
            `;
            
            // Add click listener to fly to marker
            item.addEventListener('click', () => {
                map.flyTo([det.lat, det.lon], 18, {
                    animate: true,
                    duration: 1.5
                });
            });

            // Prepend new item
            logList.insertBefore(item, logList.firstChild);

            // Add Marker to Map
            const marker = L.marker([det.lat, det.lon], {icon: potholeIcon}).addTo(map);
            
            const popupContent = `
                <div class="custom-popup">
                    <h4><i class="fa-solid fa-road-circle-exclamation"></i> Pothole #${det.id}</h4>
                    <p>Lat: ${det.lat.toFixed(5)}</p>
                    <p>Lon: ${det.lon.toFixed(5)}</p>
                    <p>Detected at: ${det.time}</p>
                </div>
            `;
            marker.bindPopup(popupContent);
            markers.push(marker);

            // Center map on newest detection
            map.flyTo([det.lat, det.lon], 16);
            
            // Remove highlight after a few seconds
            setTimeout(() => {
                item.classList.remove('new-detection');
            }, 3000);
        }
    });
}

// Global CSS animation for pulses
const style = document.createElement('style');
style.innerHTML = `
@keyframes pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 71, 87, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(255, 71, 87, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 71, 87, 0); }
}
`;
document.head.appendChild(style);

// Start polling every 2 seconds
setInterval(fetchDetections, 2000);
fetchDetections(); // Initial fetch
