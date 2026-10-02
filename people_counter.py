import time
import numpy as np
import vl53l5cx

# ==========================================
# CONFIGURATION & THRESHOLDS
# ==========================================
MAX_PASSAGE_HEIGHT_MM = 1800  # Objects closer than 1.8m (person passing door)
DEBOUNCE_TIME_SEC = 0.8       # Minimum cooldown between registered counts

print("Initializing VL53L5CX for Bidirectional People Counter...")
sensor = vl53l5cx.VL53L5CX()
sensor.set_resolution(8 * 8)
sensor.set_ranging_frequency_hz(15)  # 15 Hz for fast traversal tracking
sensor.start_ranging()

# Counter state variables
people_in_count = 0
people_out_count = 0

# Sequence tracking for directional movement
current_sequence = []
last_event_time = 0

def check_side_triggers(grid):
    """
    Checks if a person is detected on the LEFT (Columns 0-3) or RIGHT (Columns 4-7) side.
    Returns: (left_active, right_active)
    """
    left_half = grid[:, 0:4]
    right_half = grid[:, 4:8]
    
    # Active if at least 2 pixels detect an object within doorway height
    left_active = np.sum(left_half < MAX_PASSAGE_HEIGHT_MM) >= 2
    right_active = np.sum(right_half < MAX_PASSAGE_HEIGHT_MM) >= 2
    
    return left_active, right_active

# ==========================================
# MAIN LOOP
# ==========================================
try:
    print("People Counter Active! Monitoring doorway...\n")
    
    while True:
        if sensor.data_ready():
            data = sensor.get_data()
            grid = np.array(data.distance_mm[:64]).reshape((8, 8))
            
            left, right = check_side_triggers(grid)
            now = time.time()
            
            # Record state transitions
            if left and not right:
                if not current_sequence or current_sequence[-1] != "LEFT":
                    current_sequence.append("LEFT")
            elif right and not left:
                if not current_sequence or current_sequence[-1] != "RIGHT":
                    current_sequence.append("RIGHT")
            elif left and right:
                if not current_sequence or current_sequence[-1] != "BOTH":
                    current_sequence.append("BOTH")
                    
            # Evaluate sequence when area becomes completely clear again
            if not left and not right and current_sequence:
                if now - last_event_time > DEBOUNCE_TIME_SEC:
                    # LEFT -> BOTH -> RIGHT or LEFT -> RIGHT (Entering)
                    if current_sequence[0] == "LEFT" and "RIGHT" in current_sequence:
                        people_in_count += 1
                        print(f"➡️ PERSON ENTERED | Total IN: {people_in_count} | Total OUT: {people_out_count}")
                        last_event_time = now
                        
                    # RIGHT -> BOTH -> LEFT or RIGHT -> LEFT (Exiting)
                    elif current_sequence[0] == "RIGHT" and "LEFT" in current_sequence:
                        people_out_count += 1
                        print(f"⬅️ PERSON EXITED  | Total IN: {people_in_count} | Total OUT: {people_out_count}")
                        last_event_time = now
                        
                # Reset sequence for next person
                current_sequence.clear()
                
            # Timeout reset if someone lingers in doorway without passing
            if current_sequence and (now - last_event_time > 3.0) and not (left or right):
                current_sequence.clear()

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nStopping People Counter...")
    print(f"Final Count -> Total IN: {people_in_count} | Total OUT: {people_out_count}")
    sensor.stop_ranging()
