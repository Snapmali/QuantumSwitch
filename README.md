<div align="center">

# Quantum Switch

### _ねこみみは量子力学_

[简体中文](README_CN.md) | English

</div>

Quantum Switch is a local web-based tool for Hatsune Miku: Project DIVA Mega Mix+ that allows quick song switching through your browser.

## Features
- Switch to any song via web interface
- Support Arcade/Console/Mixed chart style switching
- Song search, alias search, and Mod filtering
- Favorites functionality for quick access to frequently used songs
- Responsive design, supports mobile and tablet

## Special Thanks

- Thanks to hiki8man for testing, and open-sourcing the memory addresses and r/w logic, which greatly helped in implementing this project
- Uses the vanilla song `mod_pv_db` from hiki8man's [Select Song with PVID](https://gamebanana.com/tools/21051) project
- sasnchis' [DivaSongViewer](https://gamebanana.com/tools/18296) project; the core song switching logic and `mod_pv_db` parsing logic in this project heavily references the DivaSongViewer open-source project
- vixen256's [DIVA Mod Archive](https://github.com/vixen256/divamodarchive). The parsing logic for pv_db and nc_db references this project.
- Project DIVA Mega Mix+ community, GameBanana's [mod_pv_db structure guide](https://gamebanana.com/tuts/15681#H1_13)
- Various AI tools. Can't get anything done without them.

---

## System Requirements

| Item | Requirement |
|------|-------------|
| OS | Windows 10/11 (64-bit) |
| Game | Hatsune Miku: Project DIVA MegaMix+ (Steam version) |
| Browser | Chrome, Edge, Firefox, or any modern browser |

---

## Using Pre-built Version

If you have downloaded the pre-built version (includes `QuantumSwitch.exe`), follow these steps to deploy:

### 1. Deployment

1. Extract the `QuantumSwitch` folder to any location
2. Navigate to the `config` folder, copy `.env.template` to `.env`
3. Edit the `.env` configuration file

### 2. Configuration

Supported configuration options in `.env`:

```env
# Mods directory path (auto-detected if not set)
GAME_MODS_DIRECTORY='C:\Path\To\mods'

# Server bind address (default 127.0.0.1, optional 0.0.0.0)
HOST=127.0.0.1

# Server port (default 8000)
PORT=8000

# Debug mode (default false)
DEBUG=false

# Game process name (usually no need to modify)
GAME_PROCESS_NAME=DivaMegaMix.exe
```

### 3. Usage

**Step 1: Launch the Game**

Start Project DIVA MegaMix+ first, and enter the main menu or song selection screen.

**Step 2: Launch Quantum Switch**

Double-click `QuantumSwitch.exe` to run.

**Step 3: Open Web Interface**

Visit http://localhost:8000 in your browser

---

## Building from Source

### 1. Environment Requirements

| Item | Requirement |
|------|-------------|
| Python | 3.11 or higher |
| Node.js | 18 or higher (only needed for development/building) |

### 2. Get the Code

```bash
git clone https://github.com/Snapmali/QuantumSwitch.git
cd QuantumSwitch
```

### 3. Install Backend Dependencies

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure Mods Directory

Edit the configuration file:

```bash
notepad .env
```

Modify the following settings:

> **Note**: If `GAME_MODS_DIRECTORY` is not configured, the program will attempt to auto-detect the path from Steam registry.

```env
# Your game mods folder path
GAME_MODS_DIRECTORY='C:\Program Files (x86)\Steam\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus\mods'

# Server host and port
HOST=0.0.0.0
PORT=8000
```

### 5. Install Frontend Dependencies (Development Mode Only)

```bash
cd ..\frontend
npm install
```

### 6. Start Methods

#### Development Mode (Separate Frontend/Backend)

Suitable for development and debugging; frontend and backend run separately.

**Terminal 1 - Start Backend:**
```bash
cd backend
.venv\Scripts\activate
python start.py
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run dev
```

Visit http://localhost:5173 to use the tool.

#### Production Mode (Single Service)

Suitable for daily use; only the backend needs to run, frontend pages are served directly by the backend.

**Step 1: Build Frontend**
```bash
cd frontend
npm run build
```

**Step 2: Start Service**
```bash
cd ..\backend
.venv\Scripts\activate
python start.py
```

Visit http://localhost:8000 to use the tool.

### 7. Building Executable

#### Prerequisites

Ensure you have installed:
- Python 3.11+ and pip
- Node.js 18+

#### Build Steps

The project root provides an automatic build script `build.bat`:

```bash
build.bat
```

Build process overview:
1. **Frontend Build**: Automatically installs dependencies (if needed) and runs `npm run build`
2. **Environment Setup**: Automatically creates virtual environment and installs dependencies
3. **PyInstaller Packaging**: Uses `build.spec` configuration to package the backend
4. **Resource Copying**: Copies frontend build artifacts, configuration templates, data files, etc.

After building, the output directory is `backend/dist/QuantumSwitch/`, containing:

```
QuantumSwitch/
├── QuantumSwitch.exe      # Main executable
├── config/
│   └── .env.template      # Configuration template
├── data/                  # Data files (aliases, favorites, etc.)
│   ├── vanilla/           # Vanilla game data directory
│   ├── aliases.json
│   └── favorites.json
├── frontend/dist/         # Frontend build resources
├── logs/                  # Log directory
└── icon.ico               # Application icon
```

Copy the `QuantumSwitch` folder to the target computer for deployment. See the [Using Pre-built Version](#using-pre-built-version) section above for details.

#### Manual Build (Alternative)

To build manually:

```bash
# 1. Build frontend
cd frontend
npm install
npm run build
cd ..

# 2. Prepare backend environment
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller

# 3. Package
python -m PyInstaller build.spec

# 4. Copy resources to dist/QuantumSwitch/
# (See resource copying steps in build.bat)
```

---

## Troubleshooting

### Issue: Song list is empty or incomplete

**Solution:**
1. Click the "Reload song list" button next to the song search box to reload the song list
2. Check if `GAME_MODS_DIRECTORY` path in `.env` is correct
3. Ensure the path uses backslashes `\` or double backslashes `\\`
4. Ensure the path points to the mods folder in the game directory
5. Restart the backend service to reload

### Issue: Web page shows the game "Not running"

**Solution:**
1. Ensure the game is running
2. Click the "Refresh status" button
3. Ensure you are using the Steam version of Project DIVA Mega Mix+
4. Check if the process name in Task Manager is `DivaMegaMix.exe`

### Issue: NewClassics is installed but not displayed in game status, or chart style switching fails

**Solution:**
1. Click the "Reattach to the game process" button
2. Restart the backend service to reload

### Issue: No response after switching song

**Solution:**
1. Ensure the game is in a state where it can accept commands
2. If in the menu selection screen, manually enter the rhythm game menu
3. Check the backend console for error logs

### Issue: Frontend build fails

**Solution:**
1. Ensure Node.js version >= 18
2. Delete the `node_modules` folder and rerun `npm install`
3. Check for port conflicts (5173 or 8000)

---

## Notes

- Only supports the Steam version of Hatsune Miku: Project DIVA Mega Mix+
- Ensure the game is running before attempting to switch songs
- Game major updates may require waiting for tool memory address updates
- In some cases, may need to run as administrator
- Most of the code for this project comes from vibe coding (including this README), please use with caution

---

## Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** - Web framework
- **Pydantic** - Data validation and serialization
- **pywin32** - Windows API memory operations
- **loguru** - Logging

### Frontend
- **TypeScript**
- **Vue 3**
- **Element Plus** - Vue 3 component library
- **Pinia** - State management
- **Vite** - Build tool

---

## Project Structure

```
QuantumSwitch/
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── api/                      # API routes
│   │   │   ├── __init__.py
│   │   │   ├── songs.py              # Song list, search, pagination
│   │   │   └── game.py               # Game status, song switching
│   │   ├── core/                     # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── process_manager.py    # Game process find/attach
│   │   │   ├── memory_operator.py    # Memory read/write
│   │   │   ├── song_selector.py      # Song switching logic
│   │   │   ├── pvdb_parser.py        # Mod database parser
│   │   │   ├── alias_manager.py      # Song alias management
│   │   │   ├── favorites_manager.py  # Favorites management
│   │   │   ├── game_status_processor.py  # Game status processing
│   │   │   ├── bootstrap.py          # Startup initialization
│   │   │   └── container.py          # DI container
│   │   ├── models/                   # Data models
│   │   │   ├── __init__.py
│   │   │   ├── song.py               # Song, difficulty models
│   │   │   ├── schemas.py            # API request/response models
│   │   │   ├── chart.py              # Chart model
│   │   │   ├── difficulty_type.py    # Difficulty type definitions
│   │   │   ├── game_state.py         # Game state model
│   │   │   ├── mod_info.py           # Mod info model
│   │   │   └── process_module.py     # Process module model
│   │   ├── utils/                    # Utilities
│   │   │   ├── __init__.py
│   │   │   ├── game_dir_processor.py # Game directory processing
│   │   │   └── logger.py             # Logging config
│   │   ├── config.py                 # App configuration
│   │   └── main.py                   # FastAPI entry
│   ├── data/                         # Data directory
│   │   ├── vanilla/                  # Vanilla game data
│   │   ├── aliases.json
│   │   └── favorites.json
│   ├── .env                          # Config (manual creation required)
│   ├── .env.template                 # Config template
│   ├── requirements.txt              # Python deps
│   ├── build.spec                    # PyInstaller config
│   ├── build_entry.py                # Package entry
│   └── start.py                      # Dev entry
│
├── frontend/                         # Vue 3 frontend
│   ├── src/
│   │   ├── api/
│   │   │   └── index.ts              # Axios client
│   │   ├── components/               # Vue components
│   │   │   ├── SongList.vue          # Song list
│   │   │   ├── SongDetail.vue        # Song detail
│   │   │   ├── GameStatus.vue        # Game status
│   │   │   ├── AliasManager.vue      # Alias manager
│   │   │   ├── LanguageSwitch.vue    # Language switch
│   │   │   ├── SearchAliasDropdown.vue   # Alias search
│   │   │   ├── SearchModDropdown.vue     # Mod search
│   │   │   └── WarningDialog.vue     # Warning dialog
│   │   ├── locales/                  # i18n files
│   │   │   ├── index.ts
│   │   │   ├── zh-CN.ts              # Simplified Chinese
│   │   │   └── en-US.ts              # English
│   │   ├── router/
│   │   │   └── index.ts              # Vue Router
│   │   ├── stores/                   # Pinia stores
│   │   │   ├── songs.ts              # Song state
│   │   │   ├── game.ts               # Game state
│   │   │   └── locale.ts             # Locale state
│   │   ├── types/
│   │   │   └── index.ts              # TypeScript types
│   │   ├── views/
│   │   │   └── HomeView.vue          # Main page
│   │   ├── App.vue                   # Root component
│   │   └── main.ts                   # Entry
│   ├── public/
│   ├── package.json                  # Node.js deps
│   ├── vite.config.ts                # Vite config
│   └── tsconfig.json                 # TypeScript config
│
├── build.bat                         # Windows build script
├── icon.png                          # App icon
└── README.md                         # Chinese README
```

## API Documentation

After starting the backend, visit http://localhost:8000/docs to view auto-generated Swagger UI API documentation.

### Main API Endpoints

- `GET /api/songs` - Get song list (supports pagination and search)
- `GET /api/songs/{pvid}` - Get single song details
- `GET /api/game/status` - Get game status
- `POST /api/game/switch` - Execute song switch

All API responses follow a unified format:

```json
{
  "success": true,
  "data": null,
  "error": null
}
```

## Additional Thanks

- Claude Code for vibe coding
- Kimi K2.5, GLM-5
- Nano Banana 2 for icon
- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
