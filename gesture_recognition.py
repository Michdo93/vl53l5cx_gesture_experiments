import time
import numpy as np
import vl53l5cx

# ==========================================
# SETTINGS & THRESHOLD VALUES
# ==========================================
SENSOR_CEILING_HEIGHT_MM = 2000      # Ceiling height in mm (2.0 m)
MIN_DISTANCE_MM = 400                # Closest allowed position (40 cm below the ceiling)
MAX_DISTANCE_MM = 1500               # Farthest position for gesture (1.50 m below the ceiling)
HAND_DEFUELING_VALUE = 300           # E.g., raising a hand >300 mm upward movement

# Initialize the VL53L5CX sensor
print("Initializing VL53L5CX sensor (may take up to 5–10 seconds)...")
sensor = vl53l5cx.VL53L5CX()

# Set the resolution to 4x4 zones for fast response time (up to 60 Hz)
sensor.set_resolution(4 * 4)
sensor.set_ranging_frequency_hz(15)  # 15 queries per second
sensor.start_ranging()

print("Sensor is ready! Waiting for gestures...")

# Time window & state buffer for gestures
history = []
cooldown = 0

def calculate_center_of_mass(grid):
    """
    Calculates the X/Y position of the hand in the 4x4 grid based on valid distance values.
    Returns: (x, y, avg_distance)
    """
    mask = (grid >= MIN_DISTANCE_MM) & (grid <= MAX_DISTANCE_MM)
    if not np.any(mask):
        return None, None, None

    # Coordinates of the 4x4 grid
    x_indices, y_indices = np.meshgrid(np.arange(4), np.arange(4))
    
    # Weighting: Close to the sensor (short distance) -> Higher weight
    weights = MAX_DISTANCE_MM - grid[mask]
    
    x_pos = np.sum(x_indices[mask] * weights) / np.sum(weights)
    y_pos = np.sum(y_indices[mask] * weights) / np.sum(weights)
    avg_distance = np.mean(grid[mask])
    
    return x_pos, y_pos, avg_distance

# ==========================================
# MAIN LOOP
# ==========================================
try:
    while True:
        if sensor.data_ready():
            data = sensor.get_data()
            
            # Format the 16 measurement values into a 4x4 matrix
            grid = np.array(data.distance_mm[:16]).reshape((4, 4))
            
            x, y, dist = calculate_center_of_mass(grid)
            
            if cooldown > 0:
                cooldown -= 1
                time.sleep(0.05)
                continue

            if x is not None:
                history.append((time.time(), x, y, dist))
                
                # Limit the history log to the last 0.6 seconds
                history = [v for v in history if time.time() - v[0] <= 0.6]
                
                # We need at least 3 data points for a motion analysis
                if len(history) >= 3:
                    dx = history[-1][1] - history[0][1]   # Change in the X-axis
                    dy = history[-1][2] - history[0][2]   # Change in the Y-axis
                    ddist = history[-1][3] - history[0][3] # Change in distance

                    # 1. Swipe gestures (horizontal and vertical in space)
                    if dx > 1.2:
                        print("👉 GESTURE RECOGNIZED: Swipe RIGHT")
                        cooldown = 10  # 0.5-second delay to prevent multiple triggers
                        history.clear()
                    elif dx < -1.2:
                        print("👈 GESTURE RECOGNIZED: Swipe LEFT")
                        cooldown = 10
                        history.clear()
                    elif dy > 1.2:
                        print("⬇️ GESTURE RECOGNIZED: Swipe DOWN")
                        cooldown = 10
                        history.clear()
                    elif dy < -1.2:
                        print("⬆️ GESTURE RECOGNIZED: Swipe UP")
                        cooldown = 10
                        history.clear()

                    # 2. Hand heben / senken (Z-Achse: Annäherung zum Sensor)
                    elif ddist < -HAND_DEFUELING_VALUE:
                        print("🖐️ GESTURE RECOGNIZED: Hand RAISED (closer to ceiling)")
                        cooldown = 10
                        history.clear()
                    elif ddist > HAND_DEFUELING_VALUE:
                        print("👇 GESTURE RECOGNIZED: Hand LOWERED (further down)")
                        cooldown = 10
                        history.clear()
            else:
                # No Hands on the Field
                if len(history) > 0:
                    history.clear()

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nEnd Measurement...")
    sensor.stop_ranging()
