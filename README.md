# ⚠️ THIS IS STILL WORK IN PROGRESS! ⚠️

## CURRENTLY ONLY DOES HERO ABILITY TOOLTIPS NOT STATISTICS IMAGES YET

I do not guarantee that this will work. But it should :)

# Deadlock Hero Ability Tooltip & Statistics Image Extractor

A Python tool with both CLI and web interfaces to automatically launch Deadlock and extract hero ability tooltip images for analysis and documentation purposes. Features real-time progress tracking, intelligent tooltip detection, and organized asset management.

## Features

- **Dual Interface**: Command-line tool and modern web dashboard
- **Automatic Game Integration**: Launches Deadlock and navigates to hero selection
- **Smart Image Extraction**: Intelligent tooltip detection and image capture
- **Real-time Updates**: WebSocket-powered live progress tracking
- **Hero Data Integration**: Fetches latest hero data from deadlock-api.com with fallback support
- **Organized Output**: Structured file organization with hero ID-based naming
- **Process Monitoring**: Robust game process detection and management
- **Hotkey Controls**: Ctrl+Shift+Q emergency stop functionality

## Prerequisites

- Python 3.9+
- Deadlock game installed on Windows
- 1920x1080 screen resolution recommended
- uv package manager

## Installation

```bash
git clone https://github.com/Oskar-Sterner/deadlock-hero-ability-statistics-image-extractor
cd deadlock-hero-ability-statistics-image-extractor
uv sync
```

## Usage

### Web Interface (Recommended)

Launch the web dashboard for an interactive experience:

```bash
uv run deadlock-extractor-web
```

Then open your browser to `http://localhost:3000` for:

- Real-time extraction monitoring
- Live log updates
- Image preview as they're extracted
- Settings management
- Start/stop controls

### Command Line Interface

For direct command-line usage:

```bash
uv run deadlock-extractor
```

### Development Mode

```bash
uv sync --dev
uv run python src/deadlock_hero_ability_statistics_image_extractor/main.py
```

## Configuration

### Web Interface

Navigate to the Settings page in the web interface and update the game executable path.

### Manual Configuration

Update the game path in your settings or directly in the code:

```python
game_path = r"YOUR_STEAM_PATH\steamapps\common\Deadlock\game\bin\win64\deadlock.exe"
```

## Output Structure

```
extracted_images/
├── abilities/
│   ├── hero6_ability_1.png    # Abrams Ability 1
│   ├── hero6_ability_2.png    # Abrams Ability 2
│   ├── hero6_ability_3.png    # Abrams Ability 3
│   ├── hero6_ability_4.png    # Abrams Ability 4
│   └── ...                    # All heroes (32+ total)
└── stats/
    └── (future implementation)
```

## How It Works

1. **Game Launch**: Automatically launches Deadlock and monitors process
2. **Menu Navigation**: Waits for main menu and navigates to hero selection
3. **Hero Processing**: Systematically processes each hero from API data
4. **Tooltip Capture**: Hovers over abilities and captures tooltip images
5. **Smart Cropping**: Uses intelligent boundary detection for clean extracts
6. **Real-time Updates**: Reports progress via web interface or console
7. **Organized Storage**: Saves with consistent hero ID-based naming

## Project Structure

```
📦deadlock-hero-ability tooltip-statistics-image-extractor
 ┣ 📂extracted_images
 ┃ ┣ 📂abilities
 ┃ ┗ 📂stats
 ┣ 📂src
 ┃ ┗ 📂deadlock_hero_ability_statistics_image_extractor
 ┃ ┃ ┣ 📂static
 ┃ ┃ ┃ ┣ 📜app.js
 ┃ ┃ ┃ ┗ 📜style.css
 ┃ ┃ ┣ 📂templates
 ┃ ┃ ┃ ┣ 📜index.html
 ┃ ┃ ┃ ┗ 📜settings.html
 ┃ ┃ ┣ 📜main.py
 ┃ ┃ ┣ 📜web_app.py
 ┃ ┃ ┗ 📜__init__.py
 ┣ 📜pyproject.toml
 ┣ 📜README.md
 ┗ 📜uv.lock
```

## API Integration

The tool integrates with deadlock-api.com to fetch the latest hero data:

- Automatically retrieves current hero roster
- Falls back to embedded data if API is unavailable
- Supports dynamic hero additions/changes
- Maintains consistent hero ID mapping

## Development

### Install development dependencies

```bash
uv sync --dev
```

### Code formatting

```bash
uv run black src/
uv run ruff check src/
```

### Building

```bash
uv build
```

## Dependencies

### Core Requirements

- **psutil**: Process monitoring and management
- **pillow**: Image processing and manipulation
- **numpy**: Numerical operations for image analysis
- **pynput**: Keyboard hotkey detection
- **requests**: API integration for hero data

### Web Interface

- **fastapi**: Modern web framework
- **uvicorn**: ASGI server
- **jinja2**: Template rendering
- **python-multipart**: Form handling

## Controls

- **Ctrl+Shift+Q**: Emergency stop during extraction
- **Web Interface**: Start/stop buttons with real-time control
- **Process Monitoring**: Automatic game state detection

## Troubleshooting

### Common Issues

- Ensure Deadlock is not running before starting extraction
- Verify screen resolution is 1920x1080 for accurate coordinates
- Check game path in settings if launch fails
- Use web interface for better error visibility

### Performance Notes

- Extraction typically takes around 4 minutes for all hero ability tooltips

## License

MIT License
