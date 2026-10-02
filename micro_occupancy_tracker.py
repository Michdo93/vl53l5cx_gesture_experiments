import time
import numpy as np
import vl53l5cx

# ==========================================
# CONFIGURATION
# ==========================================
PRESENCE_THRESHOLD_MM = 150  # Distance drop of >=150mm from baseline indicates presence
CALIBRATION_SAMPLES = 20     # Number of frames to build background baseline

print("Initializing VL53L5CX for Micro-Occupancy Tracking...")
sensor = vl53l5cx.VL53L5CX()
sensor.set_resolution(8 * 8)
sensor.set_ranging_frequency_hz(10)
sensor.start_ranging()

def calibrate_background(sensor, num_samples):
    """
    Measures static room geometry (floor/furniture) to create a baseline distance map.
    """
    print(f"Calibrating room background... Please leave the sensor area ({num_samples} frames).")
    samples = []
    
    while len(samples) < num_samples:
        if sensor.data_ready():
            data = sensor.get_data()
            grid = np.array(data.distance_mm[:64]).reshape((8, 8))
            samples.append(grid)
            time.sleep(0.05)
            
    # Calculate median distance per zone for robust baseline
    baseline = np.median(np.array(samples), axis=0)
    print("Calibration complete! Background baseline established.\n")
    return baseline

def evaluate_zones(current_grid, baseline):
    """
    Splits the 8x8 matrix into 4 sub-quadrants and checks for human presence in each.
    Returns: dict with occupancy status per quadrant
    """
    # Calculate difference from empty room baseline
    diff = baseline - current_grid
    
    # Identify pixels where an object is closer than the baseline
    occupied_mask = diff >= PRESENCE_THRESHOLD_MM
    
    # Divide 8x8 matrix into 4 Quadrants (Top-Left, Top-Right, Bottom-Left, Bottom-Right)
    quadrants = {
        "Zone 1 (Top-Left)":     occupied_mask[0:4, 0:4],
        "Zone 2 (Top-Right)":    occupied_mask[0:4, 4:8],
        "Zone 3 (Bottom-Left)":  occupied_mask[4:8, 0:4],
        "Zone 4 (Bottom-Right)": occupied_mask[4:8, 4:8]
    }
    
    status = {}
    for zone_name, mask in quadrants.items():
        # Zone is considered occupied if at least 2 pixels detect an object
        status[zone_name] = np.sum(mask) >= 2
        
    return status

# ==========================================
# MAIN LOOP
# ==========================================
try:
    baseline_grid = calibrate_background(sensor, CALIBRATION_SAMPLES)
    last_status = {}

    while True:
        if sensor.data_ready():
            data = sensor.get_data()
            current_grid = np.array(data.distance_mm[:64]).reshape((8, 8))
            
            zone_status = evaluate_zones(current_grid, baseline_grid)
            
            # Print update only if occupancy state changes
            if zone_status != last_status:
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] OCCUPANCY UPDATE:")
                for zone, is_occupied in zone_status.items():
                    state_str = "🟢 OCCUPIED" if is_occupied else "⚪ EMPTY"
                    print(f"  {zone}: {state_str}")
                print("-" * 40)
                last_status = zone_status
                
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping Occupancy Tracker...")
    sensor.stop_ranging()
