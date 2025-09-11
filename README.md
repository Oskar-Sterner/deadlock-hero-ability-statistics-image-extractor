# DISCLAIMER

This is a wip project and I do not guarantee it will work. This is under constant development.

# Deadlock Hero Ability & Statistics Image Extractor

A Python tool with both CLI and web interfaces to automatically launch Deadlock and extract hero ability and statistics tooltips using a state-of-the-art **YOLOv8 object detection model**.

## Features

- **Cross-Platform Support**: Works on **Windows** and **Linux**.
- **Dual Interface**: Use the modern web dashboard or the powerful command-line tool.
- **Automatic Game Integration**: Launches Deadlock and navigates to the hero selection screen.
- **State-of-the-Art Detection**: Utilizes a custom-trained **YOLOv8 model** for highly accurate, real-time tooltip detection.
- **Train Your Own Model**: Includes a complete workflow for labeling your own data and training a custom detector.
- **Flexible Extraction**: Choose to extract hero abilities, statistics, or both.
- **Real-time Updates**: The web dashboard provides live log updates and image previews.
- **Organized Output**: Saves all images in a structured directory with clear naming.
- **Emergency Stop**: Press **Ctrl+Shift+Q** at any time to safely halt the extraction process.

---

## Installation

This project requires **Python 3.9**. Due to dependencies, it is **not compatible with newer versions** like Python 3.10+.

```bash
# Clone the repository
git clone https://github.com/Oskar-Sterner/deadlock-hero-ability-statistics-image-extractor
cd deadlock-hero-ability-statistics-image-extractor

# Create a Python 3.9 virtual environment
# (Ensure python3.9 is available in your PATH)
uv venv -p python3.9

# Install dependencies
uv sync
```

---

## Usage

### Web Interface (Recommended)

The web interface offers the best user experience with full control and real-time feedback.

**Launch the server:**

```bash
uv run deadlock-extractor-web
```

Then, open your browser to **`http://localhost:3000`**. From the dashboard, you can start/stop the process, select what to extract, and see live results.

### Command-Line Interface

```bash
# Extract both abilities and statistics
uv run deadlock-extractor --abilities --stats

# Extract only abilities (default)
uv run deadlock-extractor --abilities

# Specify a custom game path
uv run deadlock-extractor --game-path "/path/to/your/deadlock/executable"
```

---

## How It Works

The extractor uses a modern computer vision pipeline for detection.

1.  **Launch & Navigate**: The tool launches Deadlock, waits for the main menu, and automatically navigates to the hero selection screen.
2.  **Hero Iteration**: It iterates through each hero, hovering the mouse over abilities and stats to trigger tooltips.
3.  **YOLOv8 Detection**: For each frame, it takes a screenshot and feeds it to the custom-trained YOLOv8 model (`yolov8n.pt`). The model instantly returns the precise bounding box of any tooltip it finds.
4.  **Capture & Save**: The detected region is cropped from the screenshot and saved to the `extracted_images/` directory.

---

## Training Your Own Model

The power of this tool is its custom-trained model. You can improve it or adapt it to game updates by following this workflow.

### 1\. Installation for Training

You will need the `labelImg` tool for annotating images. Install it into your environment:

```bash
# Install development dependencies, including labelImg
uv pip install -e ".[dev]"
```

If you encounter errors with the uv run train-tooltip-detector. Run this:

```bash
# Install development dependencies, including labelImg
uv pip install -e ."
```

and try again. If that fails you could run this:

```bash
# Install development dependencies, including labelImg
uv run python src/deadlock_hero_ability_statistics_image_extractor/train_yolo.py
```

### 2\. Data Collection & Annotation

- Create a `yolo_dataset/images` folder.
- Add dozens of in-game screenshots to this folder. Capture a wide variety of tooltips in different positions.
- Launch the annotation tool:
  ```powershell
  # On Windows
  .\.venv\Scripts\labelImg.exe
  ```
- In `labelImg`:
  1.  Open your `yolo_dataset/images` directory.
  2.  Set the save directory to a new `yolo_dataset/labels` folder.
  3.  **Crucially, set the format to `YOLO`**.
  4.  Draw a box around every tooltip and label it `tooltip`.
  5.  Save your work. This creates a `.txt` file for each labeled image.

### 3\. Training

- Create a `tooltip_dataset.yaml` file in the project root:

  ```yaml
  path: ./yolo_dataset
  train: images
  val: images

  names:
    0: tooltip
  ```

- Run the training script. This will take time and uses your CPU by default.
  ```bash
  uv run train-tooltip-detector
  ```
- Your new model will be saved in the `runs/detect/train/weights/best.pt` directory. Update the path in `tooltip_detector.py` if a new folder (e.g., `train`) is created.
