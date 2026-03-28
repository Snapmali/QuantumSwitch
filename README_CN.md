<div align="center">

# Quantum Switch

### _ねこみみは量子力学_

简体中文 | [English](README.md)

</div>

Quantum Switch 是一个用于 Hatsune Miku: Project DIVA Mega Mix+ 的本地 Web 工具，通过浏览器界面实现快速歌曲切换。

## 功能特点
- 通过网页界面快速切换任意歌曲
- 支持 Arcade/Console/Mixed 谱面风格切换
- 支持歌曲搜索、别名搜索、Mod 筛选
- 收藏功能，快速访问常用歌曲
- 响应式设计，支持手机/平板访问

## 特别感谢

- 特别感谢 hiki8man 大佬的测试，以及对相关内存地址的开源和读写逻辑讲解，对工程落地提供了很大帮助
- 使用了 hiki8man 的 [Select Song with PVID](https://gamebanana.com/tools/21051) 项目的原版歌曲 mod_pv_db
- 感谢 sasnchis 的 [DivaSongViewer](https://gamebanana.com/tools/18296) 项目，本项目中歌曲切换核心逻辑、mod_pv_db 解析逻辑大量参考 DivaSongViewer 开源项目
- 感谢 vixen256 的 [DIVA Mod Archive](https://github.com/vixen256/divamodarchive)，pv_db 和 nc_db 的解析逻辑参考了此项目
- Project DIVA Mega Mix+ 社区，GameBanana 的 [mod_pv_db 结构说明](https://gamebanana.com/tuts/15681#H1_13)
- 各路 AI，没这个办不成事

---

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 (64位) |
| 游戏 | Hatsune Miku: Project DIVA MegaMix+ (Steam版) |
| 浏览器 | Chrome、Edge、Firefox 等现代浏览器 |

---

## 使用已构建版本

如果你已经下载了构建好的版本（包含 `QuantumSwitch.exe`），按以下步骤部署：

### 1. 部署

1. 解压 `QuantumSwitch` 文件夹到任意位置
2. 进入 `config` 文件夹，复制 `.env.template` 为 `.env`
3. 编辑 `.env` 配置文件

### 2. 配置文件说明

`.env` 文件支持的配置项：

```env
# Mods 目录路径（不填则自动检测）
GAME_MODS_DIRECTORY='C:\Path\To\mods'

# 服务器绑定地址（默认 127.0.0.1，可选 0.0.0.0）
HOST=127.0.0.1

# 服务器端口（默认 8000）
PORT=8000

# 调试模式（默认 false）
DEBUG=false

# 游戏进程名（通常不需要修改）
GAME_PROCESS_NAME=DivaMegaMix.exe
```

### 3. 使用流程

**步骤 1：启动游戏**

先启动 Project DIVA MegaMix+，进入主菜单或歌曲选择界面。

**步骤 2：启动 Quantum Switch**

双击运行 `QuantumSwitch.exe`。

**步骤 3：打开网页界面**

在浏览器中访问 http://localhost:8000

---

## 从源码开始

### 1. 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.11 或更高版本 |
| Node.js | 18 或更高版本 (仅开发/构建需要) |

### 2. 获取代码

```bash
git clone https://github.com/Snapmali/QuantumSwitch.git
cd QuantumSwitch
```

### 3. 安装后端依赖

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 配置 Mods 目录

编辑配置文件：

```bash
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

### 5. 安装前端依赖（仅开发模式需要）

```bash
cd ..\frontend
npm install
```

### 6. 启动方式

#### 开发模式（前后端分离）

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

#### 生产模式（单服务）

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

### 7. 构建可执行文件

#### 准备工作

确保已安装：
- Python 3.11+ 和 pip
- Node.js 18+

#### 构建步骤

项目根目录提供了自动构建脚本 `build.bat`：

```bash
build.bat
```

构建流程说明：
1. **前端构建**：自动安装依赖（如需要）并执行 `npm run build`
2. **环境准备**：自动创建虚拟环境并安装依赖
3. **PyInstaller 打包**：使用 `build.spec` 配置打包后端
4. **资源复制**：复制前端构建产物、配置文件模板、数据文件等

构建完成后，输出目录为 `backend/dist/QuantumSwitch/`，包含：

```
QuantumSwitch/
├── QuantumSwitch.exe      # 主程序
├── config/
│   └── .env.template      # 配置文件模板
├── data/                  # 数据文件（别名、收藏等）
│   ├── vanilla/           # 原版游戏数据文件目录
│   ├── aliases.json
│   └── favorites.json
├── frontend/dist/         # 前端构建资源
├── logs/                  # 日志目录
└── icon.ico               # 程序图标
```

将 `QuantumSwitch` 文件夹复制到目标电脑即可部署使用。详见上方【使用已构建版本】章节。

#### 手动构建（备选）

如需手动构建：

```bash
# 1. 构建前端
cd frontend
npm install
npm run build
cd ..

# 2. 准备后端环境
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller

# 3. 打包
python -m PyInstaller build.spec

# 4. 复制资源到 dist/QuantumSwitch/
# （参见 build.bat 中的资源复制步骤）
```

---

## 故障排除

### 问题：歌曲列表为空或不完整

**解决方案：**
1. 点击歌曲搜索框旁的刷新按钮重新加载歌曲列表
2. 检查 `.env` 文件中的 `GAME_MODS_DIRECTORY` 路径是否正确
3. 确保路径使用反斜杠 `\` 或双反斜杠 `\\`
4. 确保路径指向的是游戏目录下的 mods 文件夹
5. 重启后端服务重新加载

### 问题：网页中游戏状态显示 "未运行"

**解决方案：**
1. 确保游戏已启动
2. 点击 "刷新状态" 按钮
3. 确保使用的是 Steam 版本的 Project DIVA Mega Mix+
4. 检查任务管理器中进程名是否为 `DivaMegaMix.exe`

### 问题：游戏已安装 NewClassics，而网页中游戏状态未显示，或切换谱面风格失败

**解决方案：**
1. 点击 "重连游戏进程" 按钮
2. 重启后端服务重新加载

### 问题：切换歌曲后游戏无反应

**解决方案：**
1. 确保游戏在可接受指令的状态
2. 如果正在菜单选择界面，需要手动进入节奏游戏菜单
3. 检查后端控制台是否有错误日志

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
- **FastAPI** - Web 框架
- **Pydantic** - 数据验证和序列化
- **pywin32** - Windows API 内存操作
- **loguru** - 日志记录

### 前端
- **TypeScript**
- **Vue 3**
- **Element Plus** - Vue 3 组件库
- **Pinia** - 状态管理
- **Vite** - 构建工具

---

## 项目结构

```
QuantumSwitch/
├── backend/                          # FastAPI 后端
│   ├── app/
│   │   ├── api/                      # API 路由层
│   │   │   ├── __init__.py
│   │   │   ├── songs.py              # 歌曲列表、搜索、分页
│   │   │   └── game.py               # 游戏状态、歌曲切换
│   │   ├── core/                     # 核心业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── process_manager.py    # 游戏进程查找与附加
│   │   │   ├── memory_operator.py    # 内存读写操作
│   │   │   ├── song_selector.py      # 歌曲切换逻辑
│   │   │   ├── pvdb_parser.py        # Mod 数据库解析
│   │   │   ├── alias_manager.py      # 歌曲别名管理
│   │   │   ├── favorites_manager.py  # 收藏管理
│   │   │   ├── game_status_processor.py  # 游戏状态处理
│   │   │   ├── bootstrap.py          # 启动初始化
│   │   │   └── container.py          # 依赖注入容器
│   │   ├── models/                   # 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── song.py               # 歌曲、难度相关模型
│   │   │   ├── schemas.py            # API 请求/响应模型
│   │   │   ├── chart.py              # 谱面模型
│   │   │   ├── difficulty_type.py    # 难度类型定义
│   │   │   ├── game_state.py         # 游戏状态模型
│   │   │   ├── mod_info.py           # Mod 信息模型
│   │   │   └── process_module.py     # 进程模块模型
│   │   ├── utils/                    # 工具函数
│   │   │   ├── __init__.py
│   │   │   ├── game_dir_processor.py # 游戏目录处理
│   │   │   └── logger.py             # 日志配置
│   │   ├── config.py                 # 应用配置
│   │   └── main.py                   # FastAPI 应用入口
│   ├── data/                         # 数据文件目录
│   │   ├── vanilla/                  # 原版游戏数据文件目录
│   │   ├── aliases.json
│   │   └── favorites.json
│   ├── .env                          # 配置文件（需手动创建）
│   ├── .env.template                 # 配置模板
│   ├── requirements.txt              # Python 依赖
│   ├── build.spec                    # PyInstaller 构建配置
│   ├── build_entry.py                # 打包入口
│   └── start.py                      # 开发启动入口
│
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── api/
│   │   │   └── index.ts              # Axios API 客户端
│   │   ├── components/               # Vue 组件
│   │   │   ├── SongList.vue          # 歌曲列表组件
│   │   │   ├── SongDetail.vue        # 歌曲详情组件
│   │   │   ├── GameStatus.vue        # 游戏状态组件
│   │   │   ├── AliasManager.vue      # 别名管理组件
│   │   │   ├── LanguageSwitch.vue    # 语言切换组件
│   │   │   ├── SearchAliasDropdown.vue   # 别名搜索下拉
│   │   │   ├── SearchModDropdown.vue     # Mod搜索下拉
│   │   │   └── WarningDialog.vue     # 警告对话框
│   │   ├── locales/                  # 国际化文件
│   │   │   ├── index.ts
│   │   │   ├── zh-CN.ts              # 简体中文
│   │   │   └── en-US.ts              # 英文
│   │   ├── router/
│   │   │   └── index.ts              # Vue Router 配置
│   │   ├── stores/                   # Pinia 状态管理
│   │   │   ├── songs.ts              # 歌曲状态
│   │   │   ├── game.ts               # 游戏状态
│   │   │   └── locale.ts             # 语言状态
│   │   ├── types/
│   │   │   └── index.ts              # TypeScript 类型定义
│   │   ├── views/
│   │   │   └── HomeView.vue          # 主页面
│   │   ├── App.vue                   # 根组件
│   │   └── main.ts                   # 入口文件
│   ├── public/
│   ├── package.json                  # Node.js 依赖
│   ├── vite.config.ts                # Vite 配置
│   └── tsconfig.json                 # TypeScript 配置
│
├── build.bat                         # Windows 构建脚本
├── icon.png                          # 应用图标
└── README.md                         # 项目说明
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
  "data": null,
  "error": null
}
```

## 另外致谢

- Claude Code for vibe coding
- Kimi K2.5, GLM-5
- Nano Banana 2 for icon
- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)