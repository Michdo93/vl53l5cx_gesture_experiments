import os
import time
import numpy as np
import vl53l5cx

# Color formatting helpers for terminal output (ANSI escape codes)
COLOR_RESET = "\033[0m"
COLOR_CLOSE = "\033[1;31m"   # Red: Object / Hand very close (< 800 mm)
COLOR_MID = "\033[1;33m"     # Yellow: Object in active gesture range (800 - 1500 mm)
COLOR_FAR = "\033[0;34m"     # Blue: Floor or empty space (> 1500 mm)

print("Initializing VL53L5CX sensor for 8x8 live visualization...")
sensor = vl53l5cx.VL53L5CX()

# Set sensor to full 8x8 resolution (64 zones)
sensor.set_resolution(8 * 8)
sensor.set_ranging_frequency_hz(15)  # 15 Hz sampling rate
sensor.start_ranging()

def render_terminal_grid_8x8(grid):
    """
    Clears the screen and draws an ASCII representation of the 8x8 matrix.
    """
    # Clear screen for Linux terminal
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("=================================================================================")
    print("                         VL53L5CX 8x8 GRID VISUALIZER                            ")
    print("=================================================================================")
    print("Legend:")
    print(f" {COLOR_CLOSE}[ <800mm ]{COLOR_RESET} Close | {COLOR_MID}[ 800-1500mm ]{COLOR_RESET} Gesture Zone | {COLOR_FAR}[ >1500mm ]{COLOR_RESET} Floor/Empty\n")
    
    border_line = "+" + "--------+" * 8
    print(border_line)

    for row in range(8):
        row_str = "|"
        for col in range(8):
            distance = grid[row, col]
            
            # Select color based on measured distance
            if distance < 800:
                color = COLOR_CLOSE
            elif 800 <= distance <= 1500:
                color = COLOR_MID
            else:
                color = COLOR_FAR
                
            # Format each cell with a fixed 4-digit millimeter readout
            row_str += f" {color}{distance:4d}mm{COLOR_RESET} |"
        
        print(row_str)
        print(border_line)
    
    print("\nPress Ctrl+C to exit.")

# ==========================================
# MAIN LOOP
# ==========================================
try:
    while True:
        if sensor.data_ready():
            data = sensor.get_data()
            
            # Reshape raw 64 distance measurements into an 8x8 matrix
            grid = np.array(data.distance_mm[:64]).reshape((8, 8))
            render_terminal_grid_8x8(grid)
            
        time.sleep(0.02)

except KeyboardInterrupt:
    print("\nExiting 8x8 visualizer...")
    sensor.stop_ranging()
