import os
import time
import random
import pickle

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

DATA_FILE = "learning_data.pkl"  # We'll store everything in this pickle file

ACTIONS = ["NONE", "JUMP", "DUCK"]  # We'll map 0->NONE, 1->JUMP, 2->DUCK

def load_data():
    """
    Load Q-table and RL parameters from a pickle file if available.
    If not available, return a default structure.
    """
    if not os.path.exists(DATA_FILE):
        return {
            "q_table": {},
            # RL Hyperparameters
            "alpha": 0.1,          # learning rate
            "gamma": 0.9,          # discount factor
            "epsilon": 1.0,        # starting exploration rate
            "epsilon_decay": 0.99, # decay factor per episode
            "epsilon_min": 0.05,   # minimum epsilon
            # Stats
            "episodes": 0,
            "total_obstacles_passed": 0
        }
    with open(DATA_FILE, "rb") as f:
        data = pickle.load(f)
    return data

def save_data(data):
    """
    Save the Q-table and parameters to a pickle file.
    """
    with open(DATA_FILE, "wb") as f:
        pickle.dump(data, f)

def get_speed_category(speed):
    """
    Return a string key ('0-6', '6-9', '9+') based on current speed.
    """
    if speed < 6:
        return "0-6"
    elif speed < 9:
        return "6-9"
    else:
        return "9+"

def discretize_position(xPos):
    """
    Convert the xPos (which can be any float) into discrete bins of size 20.
    """
    bin_size = 20
    return int(xPos // bin_size)

def discretize_y(yPos):
    """
    Convert yPos into multiple bins for distinguishing
    cacti vs. pterodactyl heights. Let's do 4 bins:
      0-40, 40-70, 70-100, 100+
    """
    if yPos < 40:
        return 0
    elif yPos < 70:
        return 1
    elif yPos < 100:
        return 2
    else:
        return 3

def get_obstacle_type_id(obstacle_type):
    """
    Map obstacle type strings to discrete IDs:
      CACTUS_SMALL -> 0
      CACTUS_LARGE -> 1
      PTERODACTYL  -> 2
      none/unknown -> 3
    """
    mapping = {
        "CACTUS_SMALL": 0,
        "CACTUS_LARGE": 1,
        "PTERODACTYL": 2
    }
    return mapping.get(obstacle_type, 3)

def get_state(game_info):
    """
    Construct a state that includes:
      ( speed_cat,
        firstObstacle_type, firstObstacle_xBin, firstObstacle_yBin,
        secondObstacle_type, secondObstacle_xBin, secondObstacle_yBin )
    If there's only one or zero obstacles, the missing obstacle is coded as type=3, xBin=0, yBin=0.
    """
    speed = game_info["speed"]
    obstacles = game_info["obstacles"]
    
    speed_cat = get_speed_category(speed)
    
    # Default "no obstacle" values
    NO_OBS_TYPE = 3  # "none"
    NO_OBS_X_BIN = 0
    NO_OBS_Y_BIN = 0
    
    # First obstacle
    if len(obstacles) > 0:
        f_type_id = get_obstacle_type_id(obstacles[0]["type"])
        f_x_bin = discretize_position(obstacles[0]["xPos"])
        f_y_bin = discretize_y(obstacles[0]["yPos"])
    else:
        f_type_id = NO_OBS_TYPE
        f_x_bin = NO_OBS_X_BIN
        f_y_bin = NO_OBS_Y_BIN
    
    # Second obstacle
    if len(obstacles) > 1:
        s_type_id = get_obstacle_type_id(obstacles[1]["type"])
        s_x_bin = discretize_position(obstacles[1]["xPos"])
        s_y_bin = discretize_y(obstacles[1]["yPos"])
    else:
        s_type_id = NO_OBS_TYPE
        s_x_bin = NO_OBS_X_BIN
        s_y_bin = NO_OBS_Y_BIN
    
    # Return the entire state as a tuple
    return (
        speed_cat,
        f_type_id, f_x_bin, f_y_bin,
        s_type_id, s_x_bin, s_y_bin
    )

def get_q_values(q_table, state):
    """
    Return the list [Q_NONE, Q_JUMP, Q_DUCK] for the given state.
    If not present, init with [0,0,0].
    """
    if state not in q_table:
        q_table[state] = [0.0, 0.0, 0.0]
    return q_table[state]

def choose_action(q_values, epsilon):
    """
    Epsilon-greedy selection over q_values = [Q_NONE, Q_JUMP, Q_DUCK].
    """
    if random.random() < epsilon:
        # Explore
        return random.randint(0, len(ACTIONS) - 1)
    else:
        # Exploit (pick action with highest Q-value)
        max_q = max(q_values)
        return q_values.index(max_q)

def run_episode(driver, data, max_steps=10000):
    """
    Runs a single "episode" (one game run) until we crash or reach max_steps.
    Returns the total reward for this episode and the number of obstacles passed.
    """
    q_table = data["q_table"]
    alpha = data["alpha"]
    gamma = data["gamma"]
    epsilon = data["epsilon"]
    
    # Start the game
    body = driver.find_element(By.TAG_NAME, 'body')
    body.send_keys(Keys.SPACE)
    time.sleep(1)
    
    old_state = None
    old_action = None
    
    episode_reward = 0.0
    obstacles_passed_this_run = 0
    consecutive_passes = 0  # track consecutive obstacle passes for bonus
    
    in_action = False
    action_end_time = 0
    
    for step in range(max_steps):
        # Grab game state from the page
        game_info = driver.execute_script("""
            let runner = Runner.instance_;
            let obstacles = runner.horizon.obstacles.map(o => ({
                xPos: o.xPos,
                yPos: o.yPos,
                type: o.typeConfig.type
            }));
            return {
                crashed: runner.crashed,
                speed: runner.currentSpeed,
                obstacles: obstacles,
                distanceRan: runner.distanceRan
            };
        """)
        
        crashed = game_info["crashed"]
        current_state = get_state(game_info)
        
        if crashed:
            # Big penalty for crash
            reward = -10.0
            episode_reward += reward
            
            # Final Q-update for the step leading to crash
            if old_state is not None and old_action is not None:
                old_q_values = get_q_values(q_table, old_state)
                old_q = old_q_values[old_action]
                # next state's Q = 0 (episode ended)
                new_q = old_q + alpha * (reward - old_q)
                old_q_values[old_action] = new_q
            
            break  # end this episode
        
        # If not crashed, we do a partial reward for staying alive
        reward = 0.01
        
        # Check if we passed an obstacle since last check
        if old_state is not None:
            old_first_type = old_state[1]  # first obs type in old state
            new_first_type = current_state[1]
            
            # If we had a real obstacle (not 3) and it changed or disappeared, we likely passed it
            if old_first_type != 3 and (new_first_type != old_first_type or new_first_type == 3):
                reward += 1.0
                obstacles_passed_this_run += 1
                consecutive_passes += 1
                # small bonus for every 3 consecutive passes
                if consecutive_passes % 3 == 0:
                    reward += 0.5
        
        episode_reward += reward
        
        # Q-update from the previous step
        if old_state is not None and old_action is not None:
            old_q_values = get_q_values(q_table, old_state)
            old_q = old_q_values[old_action]
            
            current_q_values = get_q_values(q_table, current_state)
            future_best_q = max(current_q_values)
            
            new_q = old_q + alpha * (reward + gamma * future_best_q - old_q)
            old_q_values[old_action] = new_q
        
        # Choose action in the current state
        current_q_values = get_q_values(q_table, current_state)
        action_index = choose_action(current_q_values, epsilon)
        action_str = ACTIONS[action_index]
        
        # Execute the chosen action
        if not in_action:
            if action_str == "JUMP":
                body.send_keys(Keys.SPACE)
                in_action = True
                action_end_time = time.time() + 0.12  # hold jump ~ 0.12s
            elif action_str == "DUCK":
                body.send_keys(Keys.ARROW_DOWN)
                in_action = True
                action_end_time = time.time() + 0.15  # hold duck ~ 0.15s
            # NONE => do nothing
        else:
            # If we're in the middle of an action, check if it's time to release
            if time.time() >= action_end_time:
                body.send_keys(Keys.SHIFT)  # trick to "release" the key
                in_action = False
        
        # Save state/action for next iteration
        old_state = current_state
        old_action = action_index
        
        time.sleep(0.02)
    
    return episode_reward, obstacles_passed_this_run

def main():
    # Load or init data
    data = load_data()
    
    max_episodes = 50  # how many episodes (game runs) to do
    driver = webdriver.Chrome()
    driver.get("https://chromedino.com/")
    time.sleep(2)
    
    for ep in range(max_episodes):
        data["episodes"] += 1
        
        ep_reward, obs_passed = run_episode(driver, data, max_steps=10000)
        data["total_obstacles_passed"] += obs_passed
        
        # Decay epsilon
        if data["epsilon"] > data["epsilon_min"]:
            data["epsilon"] = max(
                data["epsilon_min"],
                data["epsilon"] * data["epsilon_decay"]
            )
        
        print(f"Episode {data['episodes']} finished. "
              f"Reward = {ep_reward:.2f}, "
              f"Obstacles = {obs_passed}, "
              f"Epsilon = {data['epsilon']:.3f}")
        
        # Save data (Q-table, hyperparams, stats)
        save_data(data)
        
        # Wait a bit before next episode
        time.sleep(2)
    
    driver.quit()
    print("All episodes completed.")

if __name__ == "__main__":
    main()
