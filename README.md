# DISCLAIMER

This is a wip project and I do not guarantee it will work. This is under constant development.

# Deadlock Hero Ability & Statistics Image Extractor

A Python tool with both CLI and web interfaces to automatically launch Deadlock and extract hero ability and statistics tooltips using a custom-trained **YOLOv8 segmentation model**.

## Features

- **Cross-Platform Support**: Works on **Windows** and **Linux**.
- **Dual Interface**: Use the modern web dashboard or the powerful command-line tool.
- **Automatic Game Integration**: Launches Deadlock and navigates to the hero selection screen.
- **Runtime Launch Controls**: Configure platform override, launch mode (`auto`/`direct`/`steam`), and custom game path.
- **Resolution-Aware Automation**: Auto-detects primary display resolution for click scaling, with optional manual overrides.
- **State-of-the-Art Detection**: Utilizes a custom-trained **YOLOv8 segmentation model** for highly accurate, real-time tooltip detection.
- **Shape-Preserving Crops**: Exports tooltip images as transparent PNGs so non-rectangular tooltip edges are preserved.
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

Use **Settings** to configure:

- platform override (`auto`, `windows`, `linux`)
- launch mode (`auto`, `direct`, `steam`)
- game executable path
- steam app id (used for steam launch mode)
- optional display width/height override for coordinate scaling

### Command-Line Interface

```bash
# Extract both abilities and statistics
uv run deadlock-extractor --abilities --stats

# Extract only abilities (default)
uv run deadlock-extractor --abilities

# Specify a custom game path
uv run deadlock-extractor --game-path "/path/to/your/deadlock/executable"

# Linux + Proton example (prefer steam launch mode)
uv run deadlock-extractor \
  --platform linux \
  --launch-mode steam \
  --game-path "/mnt/nvme2tb/SteamLibrary/steamapps/common/Deadlock/game/bin/win64/deadlock.exe"

# Optional manual display override for click scaling
uv run deadlock-extractor --display-width 2560 --display-height 1440

# Explicit headless/CLI mode (same behavior as default CLI)
uv run deadlock-extractor --headless --abilities
```

---

## How It Works

The extractor uses a modern computer vision pipeline for detection.

1.  **Launch & Navigate**: The tool launches Deadlock, waits for the main menu, and automatically navigates to the hero selection screen.
2.  **Hero Iteration**: It iterates through each hero, hovering the mouse over abilities and stats to trigger tooltips.
3.  **YOLOv8 Segmentation**: For each frame, it takes a screenshot and feeds it to the custom-trained YOLOv8 segmentation model (`yolov8n-seg.pt` for training). The runtime model returns the best tooltip mask/polygon and confidence.
4.  **Capture & Save**: The tooltip is cropped to the mask bounding region and saved as a transparent PNG in `extracted_images/`.

---

## Training Your Own Segmentation Model

The model is designed to be re-trained whenever tooltip visuals change. Use this workflow to create polygon labels and train segmentation weights.

### 1\. Installation for Training

Install development dependencies (includes `labelme` for polygon annotation):

```bash
uv pip install -e ".[dev]"
```

If your virtual environment is corrupted or from another OS, recreate it and reinstall:

```bash
uv venv -p python3.9
uv sync
uv pip install -e ".[dev]"
```

### 2\. Data Collection & Polygon Annotation (LabelMe)

1. Create `yolo_dataset/images` and add many in-game screenshots with tooltip variation.
2. Create `yolo_dataset/annotations_labelme` for LabelMe JSON annotations.
3. Launch LabelMe:

```bash
# Linux/macOS
uv run labelme
```

```powershell
# Windows (PowerShell)
.\.venv\Scripts\labelme.exe
```

4. In LabelMe:
   - Open `yolo_dataset/images`.
   - Set output directory to `yolo_dataset/annotations_labelme`.
   - Use the **Polygon** tool and trace the tooltip edge.
   - Use label name `tooltip`.
   - Save each annotation as JSON.

### 3\. Convert LabelMe JSON -> YOLO Segmentation Labels

Convert the annotations into YOLO segmentation `.txt` labels:

```bash
uv run convert-labelme-yolo-seg \
  --input yolo_dataset/annotations_labelme \
  --output yolo_dataset/labels \
  --class-map tooltip=0
```

The converter writes labels in YOLO segmentation format:

```text
class x1 y1 x2 y2 x3 y3 ...
```

Where all coordinates are normalized to `[0, 1]`.

### 4\. Train the Segmentation Model

Ensure `tooltip_dataset.yaml` is present in the project root:

```yaml
path: ./yolo_dataset
train: images
val: images

names:
  0: tooltip
```

Run training with segmentation defaults:

```bash
uv run train-tooltip-detector
```

Optional overrides:

```bash
uv run train-tooltip-detector --model yolov8n-seg.pt --epochs 100 --imgsz 768 --device 0
```

Expected output weights path:

```text
runs/segment/train/weights/best.pt
```

Runtime fallback is supported for older detect weights at `runs/detect/train/weights/best.pt`, but the segmentation path is preferred.

### 5\. Migration Note for Existing Labels

Existing bounding-box labels should be fully relabeled as polygons. Do not rely on auto-converted box polygons for production-quality results.
