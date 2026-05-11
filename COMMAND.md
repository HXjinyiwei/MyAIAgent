# 项目启动与终止命令

## 启动项目

### 1. 环境准备（首次运行时需要）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows）
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置API密钥
# 编辑 .env 文件，填入你的API密钥
```

### 2. 启动应用

```bash
# 激活虚拟环境（如果还没有激活）
venv\Scripts\activate

# 启动Streamlit应用
streamlit run app.py
```

应用启动后，会在默认浏览器中自动打开，或者显示访问地址（通常是 `http://localhost:8501`）。

## 终止项目

### 方法1：通过终端终止（推荐）

在运行 `streamlit run app.py` 的终端窗口中，按 `Ctrl + C` 两次即可终止应用。

### 方法2：通过任务管理器终止

如果终端窗口已关闭或无法响应：

1. 打开Windows任务管理器（Ctrl + Shift + Esc）
2. 在"进程"选项卡中查找以下进程：
   - `python.exe` 或 `streamlit`
3. 选中相关进程并点击"结束任务"

### 方法3：通过命令行终止

```bash
# 查找并终止所有Python进程（谨慎使用，会终止所有Python程序）
taskkill /f /im python.exe

# 或者更精确地查找Streamlit相关进程
tasklist | findstr streamlit
# 然后根据PID终止特定进程
taskkill /f /pid <进程ID>
```

## 注意事项

- 确保在启动前已正确配置 `.env` 文件中的API密钥
- 如果遇到端口占用问题，可以指定其他端口：`streamlit run app.py --server.port 8502`
- 应用数据会保存在 `memory.db` 和 `data/` 目录中，终止应用不会删除这些数据
- 如果需要完全重置应用状态，可以删除 `memory.db` 和 `data/` 目录下的文件