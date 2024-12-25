import os
import time
import random
import pickle

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import JavascriptException

DATA_FILE = "learning_data.pkl"
ACTIONS = ["NONE", "JUMP", "DUCK"]  # 0->NONE, 1->JUMP, 2->DUCK

def load_data():
    """
    Load Q-table and RL parameters from a pickle file if available.
    Otherwise, return a default structure.
    """
    if not os.path.exists(DATA_FILE):
        return {
            "q_table": {},
            "alpha": 0.1,           # learning rate
            "gamma": 0.9,           # discount factor
            "epsilon": 1.0,         # starting exploration rate
            "epsilon_decay": 0.99,  # decay factor per episode
            "epsilon_min": 0.05,    # minimum epsilon
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
    """Return a string key for speed range: '0-6', '6-9', or '9+'."""
    if speed < 6:
        return "0-6"
    elif speed < 9:
        return "6-9"
    else:
        return "9+"

def discretize_position(xPos):
    """Bin xPos in size-20 intervals."""
    return int(xPos // 20)

def discretize_y(yPos):
    """
    Bin yPos to differentiate cacti vs. pterodactyl heights.
    We'll use 4 bins: [0-39], [40-69], [70-99], [100+].
    """
    if yPos < 40:
        return 0
    elif yPos < 70:
        return 1
    elif yPos < 100:
        return 2
    else:
        return 3

def get_obstacle_type_id(obs_type_str):
    """
    Convert obstacle string to an ID:
      'CACTUS_SMALL' -> 0
      'CACTUS_LARGE' -> 1
      'PTERODACTYL'  -> 2
      unknown/none   -> 3
    """
    mapping = {
        "CACTUS_SMALL": 0,
        "CACTUS_LARGE": 1,
        "PTERODACTYL": 2
    }
    return mapping.get(obs_type_str, 3)

def get_state(game_info):
    """
    Return a tuple describing the game state:
      (speed_cat,
       f_type, f_x_bin, f_y_bin,
       s_type, s_x_bin, s_y_bin)

    If fewer obstacles exist, fill missing with (3, 0, 0).
    """
    speed = game_info["speed"]
    obstacles = game_info["obstacles"]
    speed_cat = get_speed_category(speed)

    NO_OBS_TYPE = 3
    NO_OBS_X_BIN = 0
    NO_OBS_Y_BIN = 0

    if len(obstacles) > 0:
        f_type = get_obstacle_type_id(obstacles[0]["type"])
        f_x_bin = discretize_position(obstacles[0]["xPos"])
        f_y_bin = discretize_y(obstacles[0]["yPos"])
    else:
        f_type = NO_OBS_TYPE
        f_x_bin = NO_OBS_X_BIN
        f_y_bin = NO_OBS_Y_BIN

    if len(obstacles) > 1:
        s_type = get_obstacle_type_id(obstacles[1]["type"])
        s_x_bin = discretize_position(obstacles[1]["xPos"])
        s_y_bin = discretize_y(obstacles[1]["yPos"])
    else:
        s_type = NO_OBS_TYPE
        s_x_bin = NO_OBS_X_BIN
        s_y_bin = NO_OBS_Y_BIN

    return (speed_cat, f_type, f_x_bin, f_y_bin, s_type, s_x_bin, s_y_bin)

def get_q_values(q_table, state):
    """
    Return [Q_NONE, Q_JUMP, Q_DUCK] for the given state,
    initializing if not present.
    """
    if state not in q_table:
        q_table[state] = [0.0, 0.0, 0.0]
    return q_table[state]

def choose_action(q_values, epsilon):
    """
    Epsilon-greedy among [NONE, JUMP, DUCK].
    """
    if random.random() < epsilon:
        return random.randint(0, len(ACTIONS) - 1)
    else:
        # Exploit best Q
        return q_values.index(max(q_values))

def wait_for_runner(driver, timeout=10):
    """
    Wait up to 'timeout' seconds for `Runner.instance_` to exist.
    Returns True if found, False otherwise.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            runner_exists = driver.execute_script("return !!(window.Runner && Runner.instance_)")
            if runner_exists:
                return True
        except JavascriptException:
            pass
        time.sleep(0.5)
    return False

def safe_reset_page(driver, attempts=3, wait_seconds=10):
    """
    Try reloading the T-Rex page multiple times until Runner is found.
    Return True if found, False otherwise.
    """
    for i in range(attempts):
        # Reload the page
        driver.get("https://elgoog.im/t-rex/")
        if wait_for_runner(driver, timeout=wait_seconds):
            return True
        print(f"Retry {i+1}/{attempts}: Runner not found, trying again...")
        time.sleep(2)
    return False

def run_episode(driver, data, max_steps=10000):
    """
    Play one Dino run. Return (episode_reward, obstacles_passed).
    """
    q_table = data["q_table"]
    alpha = data["alpha"]
    gamma = data["gamma"]
    epsilon = data["epsilon"]

    # Press SPACE to start
    body = driver.find_element(By.TAG_NAME, 'body')
    body.send_keys(Keys.SPACE)
    time.sleep(0.5)

    # Attempt to speed up the game
    try:
        driver.execute_script("""
            Runner.instance_.currentSpeed = 15;
            Runner.instance_.config.ACCELERATION = 0.001;
        """)
    except JavascriptException:
        pass  # If it fails, continue with default speed

    old_state = None
    old_action = None
    episode_reward = 0.0
    obstacles_passed = 0
    consecutive_passes = 0

    in_action = False
    action_end_time = 0

    for step in range(max_steps):
        # Grab game info
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

            # Final Q-update
            if old_state is not None and old_action is not None:
                old_q_values = get_q_values(q_table, old_state)
                old_q = old_q_values[old_action]
                # next state's Q = 0 (episode ends)
                new_q = old_q + alpha * (reward - old_q)
                old_q_values[old_action] = new_q
            break

        # Small reward for staying alive
        reward = 0.01

        # Check if we passed an obstacle
        if old_state is not None:
            old_first_type = old_state[1]  # first obstacle type in old state
            new_first_type = current_state[1]
            if old_first_type != 3 and (new_first_type != old_first_type or new_first_type == 3):
                reward += 1.0
                obstacles_passed += 1
                consecutive_passes += 1
                # small bonus every 3 consecutive passes
                if consecutive_passes % 3 == 0:
                    reward += 0.5

        episode_reward += reward

        # Q-update from old state
        if old_state is not None and old_action is not None:
            old_q_values = get_q_values(q_table, old_state)
            old_q = old_q_values[old_action]

            current_q_values = get_q_values(q_table, current_state)
            future_best_q = max(current_q_values)

            new_q = old_q + alpha * (reward + gamma * future_best_q - old_q)
            old_q_values[old_action] = new_q

        # Decide action
        current_q_values = get_q_values(q_table, current_state)
        action_index = choose_action(current_q_values, epsilon)
        action_str = ACTIONS[action_index]

        # Execute action
        if not in_action:
            if action_str == "JUMP":
                body.send_keys(Keys.SPACE)
                in_action = True
                action_end_time = time.time() + 0.12
            elif action_str == "DUCK":
                body.send_keys(Keys.ARROW_DOWN)
                in_action = True
                action_end_time = time.time() + 0.15
        else:
            # If we're holding a key, see if it's time to release
            if time.time() >= action_end_time:
                body.send_keys(Keys.SHIFT)  # Release
                in_action = False

        # Store old state/action
        old_state = current_state
        old_action = action_index

        # A small sleep so we don't outrun the game
        time.sleep(0.01)

    return episode_reward, obstacles_passed

def main():
    data = load_data()
    max_episodes = 50  # how many episodes to run

    # Headless Chrome
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://elgoog.im/t-rex/")

    # Ensure the runner loads at the start
    if not wait_for_runner(driver, timeout=15):
        print("Runner instance not found at start. Exiting.")
        driver.quit()
        return

    for ep in range(max_episodes):
        data["episodes"] += 1

        ep_reward, obs_passed = run_episode(driver, data, max_steps=10000)
        data["total_obstacles_passed"] += obs_passed

        # Decay epsilon
        if data["epsilon"] > data["epsilon_min"]:
            data["epsilon"] = max(data["epsilon_min"], data["epsilon"] * data["epsilon_decay"])

        print(
            f"Episode {data['episodes']} finished. "
            f"Reward = {ep_reward:.2f}, Obstacles = {obs_passed}, "
            f"Epsilon = {data['epsilon']:.3f}"
        )

        # Try reloading for the next episode
        if not safe_reset_page(driver, attempts=3, wait_seconds=15):
            print("Runner instance not found after multiple reload attempts. Exiting.")
            break

        # Save the updated Q-table
        save_data(data)

        time.sleep(0.5)

    driver.quit()
    print("All episodes completed.")

if __name__ == "__main__":
    main()
