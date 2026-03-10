<div align="center">

# Quantum Switch

### _ねこみみは量子力学_

</div>

一个用于 Hatsune Miku: Project DIVA MegaMix+ 的网页版歌曲列表查询和游戏歌曲切换工具。

## 特别感谢

- [DivaSongViewer](https://github.com/sasnchis/DivaSongViewer/tree/master): 本项目中歌曲切换、mod_pv_db 逻辑大量参考 DivaSongViewer 开源项目，感谢开发者对相关内存地址的研究
- 感谢 [hiki8man](https://gamebanana.com/members/2176530) 老师的原版歌曲 mod_pv_db，以及对切歌逻辑的讲解，对理解相关流程提供了很大帮助
- Project DIVA Mega Mix+ 社区，GameBanana 的 [mod_pv_db 结构说明](https://gamebanana.com/tuts/15681#H1_13)
- 各路 AI，没这个已经办不成事了

## 功能特性

- **实时歌曲切换** - 在游戏运行时动态切换歌曲和难度
- **完整的歌曲列表** - 解析 Mod 数据库，显示所有可用歌曲和难度信息
- **现代化界面** - 基于 Vue 3 的响应式 Web 界面

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

## 快速开始

### 环境要求

- Python 3.11 或更高版本
- Node.js 18 或更高版本
- Windows 操作系统（需要 Windows API）
- Hatsune Miku Project DIVA MegaMix+ 游戏

### 后端配置

1. 进入后端目录：
```bash
cd backend
```

2. 创建虚拟环境（推荐）：
```bash
python -m venv .venv
.venv\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 创建 `.env` 配置文件：
```env
GAME_MODS_DIRECTORY='C:\Path\To\mods'    # 游戏mods文件夹所在路径
HOST=127.0.0.1                           # 服务器绑定地址
PORT=8000                                # 服务器端口
DEBUG=false                              # 调试模式
```

5. 启动开发服务器：
```bash
python start.py
```

### 前端配置

1. 进入前端目录：
```bash
cd frontend
```

2. 安装依赖：
```bash
npm install
```

3. 启动开发服务器：
```bash
npm run dev
```

前端开发服务器将在 http://localhost:5173 启动，并代理 `/api` 请求到后端 8000 端口。

### 生产部署

1. 构建前端：
```bash
cd frontend
npm run build
```

2. 运行后端（自动服务 frontend/dist 目录）：
```bash
cd backend
python start.py
```

## 使用说明

1. 启动 Project DIVA MegaMix+ 游戏
2. 启动 Quantum Switch 后端服务
3. 打开浏览器访问 http://localhost:8000（生产模式）或 http://localhost:5173（开发模式）
4. 在网页界面中浏览歌曲列表
5. 点击想要切换的歌曲和难度
6. 根据游戏状态，切换将立即生效或等待你按下空格键确认

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

## 注意事项

- 仅支持 Hatsune Miku: Project DIVA Mega Mix+ 的 Steam 版本
- 确保游戏正在运行后再尝试切换歌曲
- 本项目大部分代码为 vibe coding（包括这个readme），使用时请注意安全

## 许可证

本项目仅供学习和个人使用。使用本工具时请遵守游戏的使用条款。

## 另外致谢

- Claude Code
- Kimi K2.5
- Nano Banana 2 for icon
- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)