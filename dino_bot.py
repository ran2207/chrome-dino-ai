import os
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# JSON file to store learning data between runs
DATA_FILE = "learning_data.json"

def load_data():
    """
    Loads thresholds and other data from JSON file if available.
    Otherwise returns a default structure.
    """
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    else:
        # Default data
        data = {
            "speed_thresholds": {
                # For speeds in [0, 6) -> jump threshold = 120
                "0-6": 120,
                # For speeds in [6, 9) -> jump threshold = 140
                "6-9": 140,
                # For speeds >= 9 -> jump threshold = 160
                "9+": 160
            },
            "jump_threshold_step": 2,
            "obstacles_passed": 0,
            "score_history": [],         # Track distances at crash
            "threshold_history": []      # Track threshold changes
        }
    return data

def save_data(data):
    """
    Saves data to JSON file.
    """
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_speed_category(speed):
    """
    Return a string key ('0-6', '6-9', '9+') based on current speed.
    This will help us select the right jump threshold from our data.
    """
    if speed < 6:
        return "0-6"
    elif speed < 9:
        return "6-9"
    else:
        return "9+"

def main():
    # Load data from file
    data = load_data()
    speed_thresholds = data["speed_thresholds"]
    jump_threshold_step = data["jump_threshold_step"]
    
    driver = webdriver.Chrome()
    driver.get("https://chromedino.com/")
    time.sleep(2)
    
    body = driver.find_element(By.TAG_NAME, 'body')
    
    # Start the game
    body.send_keys(Keys.SPACE)
    
    # Keep track of how many obstacles we pass without crashing this run
    obstacles_passed_this_run = 0
    
    while True:
        # Read game info from the DOM
        game_info = driver.execute_script("""
            let runner = Runner.instance_;
            let obstacles = runner.horizon.obstacles.map(o => ({
                xPos: o.xPos,
                yPos: o.yPos
            }));
            return {
                crashed: runner.crashed,
                speed: runner.currentSpeed,
                obstacles: obstacles,
                distanceRan: runner.distanceRan
            };
        """)

        crashed = game_info["crashed"]
        current_speed = game_info["speed"]
        obstacles_list = game_info["obstacles"]
        distance_ran = game_info["distanceRan"]
        
        # If crashed
        if crashed:
            print(f"--- Crashed at distance: {distance_ran:.2f} ---")
            data["score_history"].append(distance_ran)
            
            # We'll adjust the threshold based on the obstacle position
            if obstacles_list:
                obstacle_x = obstacles_list[0]["xPos"]
                # Find which speed range we were in
                speed_cat = get_speed_category(current_speed)
                current_threshold = speed_thresholds[speed_cat]
                
                if obstacle_x < current_threshold:
                    # Possibly jumped too late
                    speed_thresholds[speed_cat] += jump_threshold_step
                    print(f"Increasing threshold for speed '{speed_cat}' to {speed_thresholds[speed_cat]}")
                else:
                    # Possibly jumped too early
                    speed_thresholds[speed_cat] -= jump_threshold_step
                    print(f"Decreasing threshold for speed '{speed_cat}' to {speed_thresholds[speed_cat]}")
                    
                # Ensure threshold doesn't go below some minimum
                speed_thresholds[speed_cat] = max(20, speed_thresholds[speed_cat])
                
                # Keep history of threshold changes
                data["threshold_history"].append({
                    "speed_cat": speed_cat,
                    "new_threshold": speed_thresholds[speed_cat],
                    "distance_ran": distance_ran
                })
            
            # If we passed a lot of obstacles, we can reduce the step size a bit
            # so that future changes aren't so drastic
            total_passed = data.get("obstacles_passed", 0) + obstacles_passed_this_run
            data["obstacles_passed"] = total_passed
            
            # For example: every 50 obstacles, reduce the step by 1 (down to a limit of 1)
            if total_passed > 0 and total_passed % 50 == 0 and jump_threshold_step > 1:
                jump_threshold_step -= 1
                data["jump_threshold_step"] = jump_threshold_step
                print(f"Reduced jump_threshold_step to {jump_threshold_step} after passing {total_passed} obstacles.")
            
            # Save data to file
            save_data(data)
            
            # Restart the game
            body.send_keys(Keys.SPACE)
            time.sleep(1)
            
            # Reset for next run
            obstacles_passed_this_run = 0
            continue
        
        # If we haven't crashed, let's see if there's an obstacle
        if obstacles_list:
            # We only check the first obstacle
            first_obstacle = obstacles_list[0]
            obstacle_x = first_obstacle["xPos"]
            
            # Decide jump threshold based on current speed range
            speed_cat = get_speed_category(current_speed)
            current_threshold = speed_thresholds[speed_cat]
            
            # Jump if the obstacle is within that threshold
            if obstacle_x < current_threshold:
                body.send_keys(Keys.SPACE)
                obstacles_passed_this_run += 1  # We'll assume we jump over it successfully
            
        # Sleep briefly to let the game run
        time.sleep(0.02)

if __name__ == "__main__":
    main()
