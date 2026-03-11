<div align="center">

# Quantum Switch

### _ねこみみは量子力学_

</div>

Quantum Switch 是一个用于 Hatsune Miku: Project DIVA Mega Mix+ 的网页版歌曲切换工具，可以通过浏览器快速选择并跳转到游戏中的任意歌曲。

## 特别感谢

- 感谢 hiki8man 的 [Select Song with PVID](https://gamebanana.com/tools/21051) 项目、原版歌曲 mod_pv_db，以及对切歌逻辑的讲解，对理解相关流程提供了很大帮助
- 感谢 sasnchis 的 [DivaSongViewer](https://gamebanana.com/tools/18296) 项目，本项目中歌曲切换核心逻辑、mod_pv_db 解析逻辑大量参考 DivaSongViewer 开源项目
- Project DIVA Mega Mix+ 社区，GameBanana 的 [mod_pv_db 结构说明](https://gamebanana.com/tuts/15681#H1_13)
- 各路 AI，没这个办不成事

---

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 (64位) |
| 游戏 | Hatsune Miku: Project DIVA MegaMix+ (Steam版) |
| Python | 3.11 或更高版本 |
| Node.js | 18 或更高版本 (仅开发/构建需要) |
| 浏览器 | Chrome、Edge、Firefox 等现代浏览器 |

---

## 快速安装

### 1. 获取代码

```bash
git clone https://github.com/Snapmali/QuantumSwitch.git
cd QuantumSwitch
```

### 2. 安装后端依赖

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 配置 Mods 目录

复制配置文件模板并编辑：

```bash
copy .env.template .env
notepad .env
```

修改以下配置项：

> **注意**：如果不配置 `GAME_MODS_DIRECTORY`，程序会尝试从 Steam 注册表自动检测路径。

```env
# 你的游戏 mods 文件夹路径
GAME_MODS_DIRECTORY='C:\Program Files (x86)\Steam\steamapps\common\Hatsune Miku Project DIVA Mega Mix Plus\mods'

# 服务器主机和端口
HOST=0.0.0.0
PORT=8000
```

### 4. 安装前端依赖（仅开发模式需要）

```bash
cd ..\frontend
npm install
```

---

## 使用方式

### 开发模式（前后端分离）

适合开发和调试，前端和后端分别运行。

**终端 1 - 启动后端：**
```bash
cd backend
.venv\Scripts\activate
python start.py
```

**终端 2 - 启动前端：**
```bash
cd frontend
npm run dev
```

访问 http://localhost:5173 使用工具。

### 生产模式（单服务）

适合日常使用，只需运行后端，前端页面由后端直接提供。

**步骤 1：构建前端**
```bash
cd frontend
npm run build
```

**步骤 2：启动服务**
```bash
cd ..\backend
.venv\Scripts\activate
python start.py
```

访问 http://localhost:8000 使用工具。

---

## 构建独立可执行文件

如果你想分发给别人使用，或者不想安装 Python 环境，可以打包成独立的 exe 程序。

### 准备工作

确保已安装：
- Python 3.11+ 和 pip
- Node.js 18+
- PyInstaller (`pip install pyinstaller`)

### 构建

项目提供了自动构建脚本：

```bash
build.bat
```

构建完成后，输出目录为 `backend/dist/QuantumSwitch/`，包含：

```
QuantumSwitch/
├── QuantumSwitch.exe    # 主程序
├── config/
│   └── .env.template    # 配置文件模板
├── frontend/dist/       # 前端资源
└── icon.ico             # 程序图标
```

### 部署步骤

1. 将 `QuantumSwitch` 文件夹复制到目标电脑
2. 进入 `config` 文件夹，复制 `.env.template` 为 `.env`
3. 编辑 `.env`，设置正确的 `GAME_MODS_DIRECTORY` 路径
4. 运行 `QuantumSwitch.exe`
5. 用浏览器访问 http://localhost:8000

---

## 使用流程

### 1. 启动游戏

先启动 Project DIVA MegaMix+，进入主菜单或歌曲选择界面。

### 2. 启动 Quantum Switch

运行 `python start.py`（开发/生产模式）或双击 `QuantumSwitch.exe`（打包版本）。

### 3. 打开网页界面

在浏览器中访问对应地址：
- 生产模式：http://localhost:8000
- 开发模式：http://localhost:5173

### 4. 切换歌曲

1. 在网页上浏览歌曲列表，可使用搜索功能快速查找
2. 点击想要切换的歌曲
3. 选择难度（EASY/NORMAL/HARD/EXTREME/EXTRA EXTREME）
4. 点击"切换到游戏"

### 5. 游戏内确认

根据你当前在游戏中的位置，切换行为有所不同：

| 游戏状态 | 切换行为 |
|----------|----------|
| 歌曲选择界面 | 立即跳转到指定歌曲 |
| PV 选择/其他界面 | 数据已写入，按空格键后生效 |
| 游戏中 | 需先返回菜单才能切换 |

---

## 配置文件说明

`.env` 文件支持的配置项：

```env
# Mods 目录路径（不填则自动检测）
GAME_MODS_DIRECTORY='C:\Path\To\mods'

# 服务器绑定地址（默认 127.0.0.1）
HOST=127.0.0.1

# 服务器端口（默认 8000）
PORT=8000

# 调试模式（默认 false）
DEBUG=false

# 游戏进程名（通常不需要修改）
GAME_PROCESS_NAME=DivaMegaMix.exe
```

---

## 故障排除

### 问题：启动时提示 "Mods 目录未找到"

**解决方案：**
1. 检查 `.env` 文件中的 `GAME_MODS_DIRECTORY` 路径是否正确
2. 确保路径使用反斜杠 `\` 或双反斜杠 `\\`
3. 确保路径指向的是游戏目录下的 mods 文件夹

### 问题：网页显示 "未检测到游戏进程"

**解决方案：**
1. 确保游戏已启动
2. 确保使用的是 Steam 版本的 Project DIVA Mega Mix+
3. 检查任务管理器中进程名是否为 `DivaMegaMix.exe`

### 问题：切换歌曲后游戏无反应

**解决方案：**
1. 确保游戏在可接受指令的状态
2. 如果正在菜单选择界面，需要手动进入节奏游戏菜单
3. 检查后端控制台是否有错误日志

### 问题：歌曲列表为空或不完整

**解决方案：**
1. 检查 mods 目录下是否有 `rom/mod_pv_db.txt` 或 `rom/mdata_pv_db.txt` 文件
2. 确保文件编码为 UTF-8
3. 重启后端服务重新加载

### 问题：前端构建失败

**解决方案：**
1. 确保 Node.js 版本 >= 18
2. 删除 `node_modules` 文件夹后重新运行 `npm install`
3. 检查是否有端口冲突（5173 或 8000）

---

## 注意事项

- 仅支持 Hatsune Miku: Project DIVA Mega Mix+ 的 Steam 版本
- 确保游戏正在运行后再尝试切换歌曲
- 游戏大更新后可能需要等待工具更新内存地址
- 某些情况下可能需要以管理员身份运行
- 本项目大部分代码为 vibe coding（包括这个readme），使用时请注意安全

---

## 技术栈

### 后端
- **Python 3.11+**
- **FastAPI** - 高性能异步 Web 框架
- **Pydantic** - 数据验证和序列化
- **pywin32** - Windows API 内存操作
- **loguru** - 日志记录

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript 超集
- **Element Plus** - Vue 3 组件库
- **Pinia** - 状态管理
- **Vite** - 构建工具

---

## 项目结构

```
QuantumSwitch/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/             # API 路由层
│   │   │   ├── songs.py     # 歌曲列表、搜索、分页
│   │   │   ├── game.py      # 游戏状态、歌曲切换
│   │   │   └── system.py    # 健康检查、配置
│   │   ├── core/            # 核心业务逻辑
│   │   │   ├── process_manager.py    # 进程管理
│   │   │   ├── memory_operator.py    # 内存读写操作
│   │   │   ├── song_selector.py      # 歌曲切换逻辑
│   │   │   └── pvdb_parser.py        # Mod 数据库解析
│   │   ├── models/          # 数据模型
│   │   │   ├── song.py      # 歌曲、难度相关模型
│   │   │   └── schemas.py   # API 请求/响应模型
│   │   └── utils/           # 工具函数
│   ├── .env                 # 配置文件（需手动创建）
│   ├── requirements.txt     # Python 依赖
│   └── start.py            # 启动入口
│
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── api/            # Axios API 客户端
│   │   ├── components/     # Vue 组件
│   │   ├── stores/         # Pinia 状态管理
│   │   ├── views/          # 页面级组件
│   │   └── types/          # TypeScript 类型定义
│   ├── package.json        # Node.js 依赖
│   └── vite.config.ts      # Vite 配置
│
└── README.md
```

## API 文档

启动后端后，访问 http://localhost:8000/docs 查看自动生成的 Swagger UI API 文档。

### 主要 API 端点

- `GET /api/songs` - 获取歌曲列表（支持分页和搜索）
- `GET /api/songs/{pvid}` - 获取单个歌曲详情
- `GET /api/game/status` - 获取游戏状态
- `POST /api/game/switch` - 执行歌曲切换

所有 API 响应遵循统一格式：
```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

## 另外致谢

- Claude Code
- Kimi K2.5
- Nano Banana 2 for icon
- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)