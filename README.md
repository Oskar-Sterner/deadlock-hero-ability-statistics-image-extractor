# DISCLAIMER

This is a wip project and I do not guarantee it will work. This is under constant development.

# Deadlock Ability & Item Tooltip Image Extractor

A Python tool with both CLI and web interfaces to automatically launch Deadlock and extract either **hero ability tooltips** or **item tooltips** using custom-trained **YOLOv8 segmentation models**.

## Features

- **Cross-Platform Support**: Works on **Windows** and **Linux**.
- **Dual Interface**: Use the modern web dashboard or the powerful command-line tool.
- **Automatic Game Integration**: Launches Deadlock and navigates to either hero selection or item shop.
- **Runtime Launch Controls**: Configure platform override, launch mode (`auto`/`direct`/`steam`), and custom game path.
- **Resolution-Aware Automation**: Auto-detects primary display resolution for click scaling, with optional manual overrides.
- **State-of-the-Art Detection**: Utilizes a custom-trained **YOLOv8 segmentation model** for highly accurate, real-time tooltip detection.
- **Shape-Preserving Crops**: Exports tooltip images as transparent PNGs so non-rectangular tooltip edges are preserved.
- **Train Your Own Model**: Includes a complete workflow for labeling your own data and training a custom detector.
- **Flexible Extraction**: Choose extraction mode: `ability` or `items`.
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

Then, open your browser to **`http://localhost:3000`**. From the dashboard, you can start/stop the process, select extraction mode (`ability` or `items`), and see live results.

Use **Settings** to configure:

- platform override (`auto`, `windows`, `linux`)
- launch mode (`auto`, `direct`, `steam`)
- game executable path
- steam app id (used for steam launch mode)
- optional display width/height override for coordinate scaling

### Command-Line Interface

```bash
# Extract ability tooltips (default)
uv run deadlock-extractor --mode ability

# Extract item tooltips
uv run deadlock-extractor --mode items

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
uv run deadlock-extractor --headless --mode ability
```

---

## How It Works

The extractor uses a modern computer vision pipeline for detection.

1.  **Launch & Navigate**: The tool launches Deadlock, waits for the main menu, and navigates to hero selection (`ability` mode) or item shop (`items` mode).
2.  **Tooltip Iteration**: It iterates either hero abilities or item cards to trigger tooltips.
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

Use task-scoped datasets:

- `yolo_dataset/abilities/{images,annotations_labelme,labels}`
- `yolo_dataset/items/{images,annotations_labelme,labels}`

1. Pick a task (`abilities` or `items`).
2. Add screenshots to `yolo_dataset/<task>/images`.
3. Save LabelMe JSON annotations to `yolo_dataset/<task>/annotations_labelme`.
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
   - Open `yolo_dataset/<task>/images`.
   - Set output directory to `yolo_dataset/<task>/annotations_labelme`.
   - Use the **Polygon** tool and trace the tooltip edge.
   - Use label name `tooltip`.
   - Save each annotation as JSON.

### 3\. Convert LabelMe JSON -> YOLO Segmentation Labels

Convert the annotations into YOLO segmentation `.txt` labels:

```bash
uv run convert-labelme-yolo-seg \
  --input yolo_dataset/<task>/annotations_labelme \
  --output yolo_dataset/<task>/labels \
  --class-map tooltip=0
```

The converter writes labels in YOLO segmentation format:

```text
class x1 y1 x2 y2 x3 y3 ...
```

Where all coordinates are normalized to `[0, 1]`.

### 4\. Train the Segmentation Model

Ensure task YAML files are present in the project root:

```yaml
path: ./yolo_dataset/abilities
train: images
val: images

names:
  0: tooltip
```

```yaml
path: ./yolo_dataset/items
train: images
val: images

names:
  0: tooltip
```

Run training with segmentation defaults:

```bash
# Abilities model
uv run train-tooltip-detector --task abilities

# Items model
uv run train-tooltip-detector --task items
```

Optional overrides:

```bash
uv run train-tooltip-detector \
  --task items \
  --model yolov8n-seg.pt \
  --epochs 100 \
  --imgsz 768 \
  --device 0 \
  --run-name train
```

Expected output weights path:

```text
runs/abilities/segment/train/weights/best.pt
runs/items/segment/train/weights/best.pt
```

Runtime model lookup is mode-specific:

- ability mode: `models/abilities/best.pt` then `runs/abilities/segment/train/weights/best.pt`
- items mode: `models/items/best.pt` then `runs/items/segment/train/weights/best.pt`

### 5\. Migration Note for Existing Labels

Existing bounding-box labels should be fully relabeled as polygons. Do not rely on auto-converted box polygons for production-quality results.

If you already have old ability data directly in `yolo_dataset/`, move it into `yolo_dataset/abilities/` before retraining.
