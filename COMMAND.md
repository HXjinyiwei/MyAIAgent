# MyAIAgent 命令和配置指南

## 📁 项目结构
```
MyAIAgent/
├── app.py              # 主应用入口
├── config.yaml         # 主配置文件
├── .env                # 环境变量配置
├── .env.example        # 环境变量模板
├── memory.db           # 记忆数据库（自动生成）
├── src/
│   ├── agent_core.py   # Agent核心引擎
│   ├── tools/          # 工具模块
│   │   ├── weather.py  # 天气工具
│   │   ├── news.py     # 新闻工具
│   │   └── ...         # 其他工具
│   ├── utils/          # 工具类
│   │   ├── api_client.py  # API客户端
│   │   └── config.py   # 配置管理器
│   └── memory.py       # 记忆管理器
├── data/
│   └── output/         # 输出文件目录
└── README.md           # 项目说明
```

## ⚙️ 配置文件详解

### .env 环境变量配置
```env
# DeepSeek API配置（必需）
DEEPSEEK_API_KEY=your_deepseek_api_key

# 天气API配置（二选一）
WEATHER_API_KEY=your_openweathermap_key          # OpenWeatherMap密钥
JUHE_WEATHER_API_KEY=your_juhe_weather_key      # 聚合数据天气密钥

# 新闻API配置（二选一）  
NEWS_API_KEY=your_newsapi_key                   # NewsAPI密钥
JUHE_NEWS_API_KEY=your_juhe_news_key           # 聚合数据新闻密钥

# API提供商选择（必需）
WEATHER_PROVIDER=openweathermap    # 可选: openweathermap, juhe
NEWS_PROVIDER=newsapi             # 可选: newsapi, juhe
```

### config.yaml 主配置文件
```yaml
user:
  city: "北京"                    # 默认城市
  profession: "软件工程师"        # 职业信息
  interests: ["人工智能", "半导体"] # 兴趣领域
  features:
    quote: true                  # 是否启用每日寄语

api:
  weather_provider: juhe         # 天气提供商
  news_provider: juhe            # 新闻提供商
  timeout: 45                    # API超时时间（秒）
  retry_count: 2                 # 重试次数
  cache_enabled: true           # 是否启用缓存
  cache_weather_minutes: 30     # 天气缓存时间（分钟）
  cache_news_minutes: 60        # 新闻缓存时间（分钟）

memory:
  cleanup_interval_days: 180    # 数据清理间隔（天）
  max_habit_records: 1000       # 最大习惯记录数
```

## 🚀 常用命令

### 开发环境设置
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 复制环境变量模板
cp .env.example .env

# 3. 编辑.env文件，填入API密钥

# 4. 启动应用
streamlit run app.py
```

### 国内用户快速配置
```env
# .env 文件配置示例
DEEPSEEK_API_KEY=sk-xxxxxx
JUHE_WEATHER_API_KEY=xxxxxx
JUHE_NEWS_API_KEY=xxxxxx
WEATHER_PROVIDER=juhe
NEWS_PROVIDER=juhe
```

### 切换API提供商
只需修改 `.env` 文件中的 `WEATHER_PROVIDER` 和 `NEWS_PROVIDER`：
- `openweathermap` + `newsapi`：国际标准API
- `juhe` + `juhe`：国内聚合数据API（推荐国内用户）

### 清理缓存和记忆数据
```python
# 在Python中执行
from src.memory import MemoryManager
mm = MemoryManager()
deleted_count = mm.cleanup_old_data(months_to_keep=6)
print(f"清理了 {deleted_count} 条过期数据")
```

## 🔧 故障排除

### API调用失败
1. **检查API密钥**：确保 `.env` 中的密钥正确
2. **验证提供商配置**：确认 `WEATHER_PROVIDER` 和 `NEWS_PROVIDER` 设置正确
3. **查看日志**：程序会打印详细的错误信息
4. **网络连接**：国内用户建议使用 `juhe` 提供商

### 配置不生效
1. **重启应用**：配置文件修改后需要重启
2. **检查YAML格式**：确保 `config.yaml` 格式正确
3. **权限问题**：确保应用有读写配置文件的权限

### 缓存相关问题
- **数据不更新**：缓存有效期为30-60分钟，等待自动过期或手动清理
- **离线模式**：API不可用时会自动使用缓存数据
- **缓存文件**：所有缓存数据存储在 `memory.db` 中

## 📊 性能监控

### 查看用户习惯分析
```python
from src.memory import MemoryManager
mm = MemoryManager()
patterns = mm.analyze_user_patterns()
print(patterns)
```

### 检查API健康状态
程序会自动定期检查API健康状态，并在日志中显示警告信息。

## 🎯 最佳实践

### 国内部署建议
- 使用聚合数据(juhe) API提供商
- 设置合理的超时时间（45-60秒）
- 启用缓存机制减少API调用

### 开发者调试
- 使用 `.env.example` 作为配置模板
- 修改 `config.yaml` 进行参数调优
- 查看 `memory.db` 了解用户行为数据

### 生产环境优化
- 定期清理过期数据保持性能
- 监控API调用频率和成功率
- 根据用户反馈调整缓存策略
