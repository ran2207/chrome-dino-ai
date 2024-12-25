# Chrome Dino Game AI Bot

An AI-powered bot that learns to play the Chrome Dinosaur Game using reinforcement learning (Q-learning). This bot uses Selenium for browser automation and supports both visible and headless modes for faster training.

---

## Overview

This project includes multiple implementations of a bot to play the Chrome Dino Game:

1. **Basic adaptive threshold learning**: Dynamically adjusts jump thresholds based on game speed and crash data.
2. **Q-learning-based bot**: Learns obstacle patterns and improves decision-making over episodes.
3. **Headless training**: Runs in headless mode for faster, automated training.

---

## Features

- **Reinforcement Learning**: Uses Q-learning to master the game over multiple episodes.
- **Game Speed Customization**: Speeds up training by increasing the game’s speed and reducing acceleration.
- **Persistence**: Saves learning data between runs for continuous improvement.
- **Cross-Platform**: Works on Windows, macOS, and Linux.
- **Headless Mode**: Supports headless Chrome for faster training without UI.

---

## File Descriptions

### **`dino_bot.py`**

- A basic implementation that adjusts jump thresholds based on game speed and crash data.
- Saves learning progress in a JSON file (`learning_data.json`).

### **`dino_bot_ml.py`**

- Implements Q-learning for smarter obstacle handling.
- Uses a pickle file (`learning_data.pkl`) for saving and loading learning data.
- Runs in visible mode with full Q-learning logic.

### **`dino_bot_ml_headless.py`**

- Enhanced version of `dino_bot_ml.py` that supports:
  - Headless Chrome for faster training.
  - Automatic retries if the game fails to load.
  - Game speed customization for faster progress.

### **`learning_data.pkl`**

- A binary file used to store the Q-table and learning parameters for the Q-learning bots.

### **`requirements.txt`**

- Contains the list of dependencies required to run the scripts.

### **`README.md`**

- Documentation explaining the project, file structure, setup instructions, and usage guidelines.

---

## Requirements

### Prerequisites

1. **Python 3.8+**
2. **Google Chrome** (latest version)
3. **ChromeDriver**
   - Download from [ChromeDriver Downloads](https://chromedriver.chromium.org/downloads).
   - Ensure the version matches your Chrome browser.
   - Add ChromeDriver to your `PATH`.

### Install Dependencies

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/dino-ml-bot.git
   cd dino-ml-bot
   ```

## How to Run

### **Basic Bot**

1. Run `dino_bot.py`:

   ```bash
   python3 dino_bot.py
   ```

2. The bot will:
   - Start the Chrome Dino game at `https://chromedino.com/`.
   - Adjust jump thresholds based on game speed and crash data.

### **Q-Learning Bot (Visible Mode)**

1. Run `dino_bot_ml.py`:

   ```bash
   python3 dino_bot_ml.py
   ```

2. The bot will:
   - Open the game on `https://chromedino.com/` or similar.
   - Use Q-learning to master obstacle patterns.

### **Q-Learning Bot (Headless Mode)**

1. Run `dino_bot_ml_headless.py`:

   ```bash
   python3 dino_bot_ml_headless.py
   ```

2. The bot will:
   - Use a headless browser for faster training.
   - Load the game at `https://elgoog.im/t-rex/`.
   - Save learning progress in `learning_data.pkl`.

---

## Supported Platforms

This bot works on:

- **Windows**
- **macOS**
- **Linux**

### Platform-Specific Notes

#### Windows

- Install ChromeDriver and ensure it's in your `PATH`.
- Run scripts via Command Prompt or PowerShell.

#### macOS

- Use Homebrew to install ChromeDriver:
  ```bash
  brew install chromedriver
  ```
- Add ChromeDriver to your `PATH`:
  ```bash
  export PATH=$PATH:/usr/local/bin
  ```

#### Linux

- Install ChromeDriver via your package manager or manually download it.
- Ensure ChromeDriver is executable and in your `PATH`:
  ```bash
  sudo chmod +x /path/to/chromedriver
  export PATH=$PATH:/path/to/chromedriver
  ```

---

## Troubleshooting

### Common Issues

#### `Runner is not defined`

- Ensure you're using the correct T-Rex URL: [https://elgoog.im/t-rex/](https://elgoog.im/t-rex/).
- Check your internet connection and retry.

#### `selenium.common.exceptions.WebDriverException`

- Ensure ChromeDriver is in your `PATH` and matches your Chrome version.

#### Slow Training

- Use `dino_bot_ml_headless.py` for headless mode.
- Adjust sleep durations or increase `currentSpeed` in the script.

---

## Contributions

Contributions are welcome! Feel free to fork this repository, submit a pull request, or open an issue.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

### Next Steps

Save this content as `README.md` in your project directory, and you’re ready to commit and push to GitHub. Let me know if you need any further refinements!
