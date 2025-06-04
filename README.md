<div align="center">
  
# 忘忧露🎬✨ - Nepenthe Video Manager

</div>

<p align="center">
  <img src="https://img.shields.io/badge/Electron-亮蓝?style=for-the-badge&logo=electron&logoColor=white" alt="Electron"/>
  <img src="https://img.shields.io/badge/Vue.js-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white" alt="Vue.js"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite"/>
</p>


> [!TIP]
> 这个项目是给我自己做的自用桌面程序，找了很多项目都不是很满意，又想要一个能给点播电影的电脑里弄一个轻量化标签管理的程序，相比于WPF开发的桌面应用会更流畅一些，考虑到了大视频库的卡顿问题，Releases有打包好可以直接使用的程序。

## 🌟 项目说明

*   **所有视频数据和元信息均使用本地路径的文件夹**
*   **管理**：
    *   📁 **视频库扫描**：扫描指定文件夹中的视频文件["mp4", "mkv", "avi", "mov", "webm", "flv", "ts"] 。
    *   🖼️ **缩略图生成**：为视频自动生成缩略图，方便快速预览。
    *   🏷️ **标签管理**：为视频添加、编辑、删除自定义标签。
    *   👤 **人物标记**：记录视频中出现的人物，方便按人物查找。
    *   ✏️ **信息编辑**：轻松修改视频文件名（显示名）和关联的标签、人物。
*   **浏览**：
    *   🔍 **强大搜索**：支持按视频名称、标签、人物进行搜索。
    *   📊 **灵活排序**：支持按默认推荐、名称、时长、播放量、添加日期等多种方式排序。
    *   🎞️ **悬停预览**：鼠标悬停在视频卡片上时，进行快速（5倍速）静音预览。
*   **调用本地播放器**：直接调用你系统上安装的默认或指定视频播放器（如 VLC, PotPlayer 等）进行播放。

## 🛠️ 使用到的技术

*   **桌面外壳**: [Electron](https://www.electronjs.org/)
*   **前端**: [Vue 3](https://vuejs.org/) + [Vite](https://vitejs.dev/) + [Element Plus](https://element-plus.org/) + [Vue Router](https://router.vuejs.org/) + [Axios](https://axios-http.com/)
*   **后端**: [FastAPI (Python)](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
*   **数据库**: [SQLite](https://www.sqlite.org/index.html)
*   **视频元数据/缩略图**: [FFmpeg](https://ffmpeg.org/) (通过后端调用)
*   **发送到回收站**: [send2trash (Python库)](https://github.com/hsoft/send2trash)
*   **包管理器**: [npm](https://www.npmjs.com/) / [pnpm](https://pnpm.io/) (根据你的选择)

---
### 部分界面的截图

<p align="center">
  <img src="https://s2.loli.net/2025/06/04/TBVd9svAcMi6zU3.png" width="100%">
</p>

<p align="center">
  <img src="https://s2.loli.net/2025/06/04/AZQYDHbFWBCL2Je.png" width="100%">
</p>

<p align="center">
  <img src="https://s2.loli.net/2025/06/04/bolatJqxT7n5UkB.png" width="100%">
</p>

## 🚀 项目开发

### 前提条件

*   [Node.js](https://nodejs.org/) (建议 LTS 版本)
*   [Python](https://www.python.org/) (建议 3.8 或更高版本)
*   [FFmpeg](https://ffmpeg.org/download.html) (需要将其可执行文件路径添加到系统 PATH 环境变量，或在后端配置中指定其路径)
*   (可选) [Git](https://git-scm.com/)

### 安装与运行 (开发模式)

1.  **克隆仓库**:
    ```bash
    git clone --depth=1 https://github.com/GuGuNiu/Nepenthe-VideoManager
    cd Nepenthe-VideoManager
    ```

2.  **安装前端依赖**:
    (进入 `nepenthe_web_ui` 或你的前端项目目录)
    ```bash
    cd nepenthe_web_ui 
    npm install 
    # 或者 pnpm install / yarn install
    ```

3.  **安装并启动后端服务**:
    (进入 FastAPI 后端项目目录，并激活虚拟环境)
    ```bash
    cd Nepenthe-VideoManager
    # python -m venv venv 
    # source venv/bin/activate  (Linux/macOS)
    # venv\Scripts\activate  (Windows)
    # venv\Scripts\Activate.ps1 （Windows PS)
    pip install -r requirements.txt 
    python run_backend_server.py 
    ```
    后端默认运行在 `http://127.0.0.1:8000`。

4.  **运行 Electron 应用 (开发模式)**:
    (回到前端项目目录 `nepenthe_web_ui`)
    ```bash
    npm run electron:serve 
    ```
    这将启动 Vite 开发服务器和 Electron 应用，Electron 会加载 Vite 的 URL，支持热重载。
    
    开发服务器地址：http://localhost:5174/ 或 http://localhost:5173/
    
### 打包应用方法

(在前端项目目录 `nepenthe_web_ui` 中)
```bash
npm run electron:build
打包后的可执行文件/安装包会生成在 nepenthe_web_ui/dist_electron 目录下。
 ```
## ⚙️ 配置
后端配置: 位于 config/backend_settings.py，可以配置 API 地址、端口、数据库路径、缩略图存储路径等。

FFmpeg/FFprobe 路径: 如果 FFmpeg/FFprobe 没有在系统 PATH 中，需要在 components/video_metadata_extractor.py 中硬编码其完整路径。

视频库路径: 通过启动直接在后端配置中设置你要扫描的视频文件夹路径。

## 📝 未来计划
更完善的播放列表功能

智能推荐或“猜你喜欢”

主题切换 (暗色/亮色模式)

国际化支持

更详细的视频元数据显示 (码率、编码器等)

允许自定义本地播放器路径


<div align="left"> 
  
  [![访问量](https://profile-counter.glitch.me/Nepenthe-VideoManager/count.svg)](https://github.com/GuGuNiu/Nepenthe-VideoManager)
  
</div>


