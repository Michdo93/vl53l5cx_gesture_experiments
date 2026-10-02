import time
import numpy as np
import vl53l5cx

# ==========================================
# CONFIGURATION & THRESHOLDS
# ==========================================
SENSOR_HEIGHT_MM = 2000     # Sensor height mounted at ceiling (2.0 meters)
MIN_DISTANCE_MM = 600       # Nearest allowed object distance (60 cm below ceiling)
MAX_DISTANCE_MM = 1500      # Max distance range for gestures (1.50 m below ceiling)
MAX_ACTIVE_ZONES = 6        # More than 6 active zones = body/head -> Ignore!
HAND_SWIPE_THRESHOLD = 1.5  # Required distance moved in grid units for a swipe

# Initialize the VL53L5CX sensor
print("Initializing VL53L5CX sensor (may take 5-10 seconds)...")
sensor = vl53l5cx.VL53L5CX()

# Set 4x4 resolution for fast response time (up to 60Hz)
sensor.set_resolution(4 * 4)
sensor.set_ranging_frequency_hz(15)  # 15 samples per second
sensor.start_ranging()

print("Sensor ready! Waiting for gestures...")

# History tracking and cooldown counters
history = []
cooldown = 0

def analyze_grid(grid):
    """
    Filters distances and calculates the hand centroid (X, Y) inside the 4x4 grid.
    Returns: (x_pos, y_pos, avg_distance, active_zones_count)
    """
    # Create mask for valid hand distance range
    hand_mask = (grid >= MIN_DISTANCE_MM) & (grid <= MAX_DISTANCE_MM)
    active_zones = np.sum(hand_mask)
    
    # FILTER 1: Too many active zones means a person is walking/standing underneath
    if active_zones > MAX_ACTIVE_ZONES or active_zones == 0:
        return None, None, None, active_zones

    # Generate 4x4 coordinate matrices
    x_indices, y_indices = np.meshgrid(np.arange(4), np.arange(4))
    
    # Calculate weights (closer objects get higher weight)
    weights = MAX_DISTANCE_MM - grid[hand_mask]
    
    x_pos = np.sum(x_indices[hand_mask] * weights) / np.sum(weights)
    y_pos = np.sum(y_indices[hand_mask] * weights) / np.sum(weights)
    avg_distance = np.mean(grid[hand_mask])
    
    return x_pos, y_pos, avg_distance, active_zones

# ==========================================
# MAIN LOOP
# ==========================================
try:
    while True:
        if sensor.data_ready():
            data = sensor.get_data()
            grid = np.array(data.distance_mm[:16]).reshape((4, 4))
            
            x_pos, y_pos, avg_dist, active_zones = analyze_grid(grid)
            
            if cooldown > 0:
                cooldown -= 1
                time.sleep(0.05)
                continue

            # Ignore if a body or head is detected
            if active_zones > MAX_ACTIVE_ZONES:
                history.clear()
                continue

            if x_pos is not None:
                history.append((time.time(), x_pos, y_pos, avg_dist))
                
                # Keep history within a 0.35-second sliding window
                history = [h for h in history if time.time() - h[0] <= 0.35]
                
                if len(history) >= 3:
                    delta_x = history[-1][1] - history[0][1]
                    delta_y = history[-1][2] - history[0][2]
                    
                    # Check horizontal swipes
                    if delta_x > HAND_SWIPE_THRESHOLD:
                        print("👉 GESTURE DETECTED: Swipe RIGHT")
                        cooldown = 12  # Lock out for ~0.6s to prevent duplicate triggers
                        history.clear()
                    elif delta_x < -HAND_SWIPE_THRESHOLD:
                        print("👈 GESTURE DETECTED: Swipe LEFT")
                        cooldown = 12
                        history.clear()
                        
                    # Check vertical swipes
                    elif delta_y > HAND_SWIPE_THRESHOLD:
                        print("⬇️ GESTURE DETECTED: Swipe DOWN (Forward)")
                        cooldown = 12
                        history.clear()
                    elif delta_y < -HAND_SWIPE_THRESHOLD:
                        print("⬆️ GESTURE DETECTED: Swipe UP (Backward)")
                        cooldown = 12
                        history.clear()
            else:
                history.clear()

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nStopping sensor measurement...")
    sensor.stop_ranging()
