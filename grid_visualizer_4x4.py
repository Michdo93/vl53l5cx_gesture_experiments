import os
import time
import numpy as np
import vl53l5cx

# Color formatting helpers for terminal output
COLOR_RESET = "\033[0m"
COLOR_CLOSE = "\033[1;31m"   # Red: Hand very close (< 800 mm)
COLOR_MID = "\033[1;33m"     # Yellow: Hand in gesture zone (800 - 1500 mm)
COLOR_FAR = "\033[0;34m"     # Blue: Floor or empty space (> 1500 mm)

print("Initializing VL53L5CX sensor for live visualization...")
sensor = vl53l5cx.VL53L5CX()

# Set to 4x4 grid resolution
sensor.set_resolution(4 * 4)
sensor.set_ranging_frequency_hz(15)
sensor.start_ranging()

def render_terminal_grid(grid):
    """
    Clears the screen and draws an ASCII representation of the 4x4 matrix.
    """
    # Clear screen (works on Linux / Raspberry Pi OS terminal)
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("=========================================")
    print("      VL53L5CX 4x4 GRID VISUALIZER       ")
    print("=========================================")
    print("Legend:")
    print(f" {COLOR_CLOSE}[ <800mm ]{COLOR_RESET} Close | {COLOR_MID}[ 800-1500mm ]{COLOR_RESET} Hand Zone | {COLOR_FAR}[ >1500mm ]{COLOR_RESET} Far/Floor\n")
    print("+---------+---------+---------+---------+")

    for row in range(4):
        row_str = "|"
        for col in range(4):
            distance = grid[row, col]
            
            # Select color based on distance
            if distance < 800:
                color = COLOR_CLOSE
            elif 800 <= distance <= 1500:
                color = COLOR_MID
            else:
                color = COLOR_FAR
                
            row_str += f" {color}{distance:4d}mm{COLOR_RESET} |"
        
        print(row_str)
        print("+---------+---------+---------+---------+")
    
    print("\nPress Ctrl+C to exit.")

try:
    while True:
        if sensor.data_ready():
            data = sensor.get_data()
            grid = np.array(data.distance_mm[:16]).reshape((4, 4))
            render_terminal_grid(grid)
            
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nExiting visualizer...")
    sensor.stop_ranging()
