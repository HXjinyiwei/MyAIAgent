# 个人每日智能简报 AI Agent

为职场人提供的、用自然语言驱动的每日信息聚合助手。

## 项目结构

```
.
├── .env                 # API密钥配置文件
├── requirements.txt     # Python依赖列表
├── README.md           # 项目说明
├── app.py              # Streamlit主应用入口
├── config.yaml         # 用户配置文件（自动生成）
├── memory.db           # SQLite数据库文件（自动生成）
├── src/                # 核心源代码目录
│   ├── __init__.py
│   ├── agent_core.py   # Agent编排引擎
│   ├── memory.py       # 记忆管理模块
│   ├── tools/          # 工具调度层
│   │   ├── __init__.py
│   │   ├── weather.py  # 天气工具
│   │   ├── news.py     # 新闻工具
│   │   ├── calendar.py # 日程工具
│   │   └── quote.py    # 寄语工具
│   └── utils/          # 工具函数
│       ├── __init__.py
│       └── config.py   # 配置管理
└── data/               # 数据存储目录
    ├── tasks.json      # 当日日程文件（自动生成）
    └── output/         # 简报输出目录（自动生成）
```

## 环境准备

1. 创建虚拟环境：
```bash
python -m venv venv
```

2. 激活虚拟环境（Windows）：
```bash
venv\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置API密钥：
   - 编辑 `.env` 文件，填入你的API密钥

5. 运行应用：
```bash
streamlit run app.py
```