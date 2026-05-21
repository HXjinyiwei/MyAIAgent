import streamlit as st
import asyncio
from src.agent_core import AgentCore
from src.tools.weather import process_weather_for_briefing, process_weather_comparison
from src.tools.news import process_news_for_briefing  
from src.tools.calendar import process_calendar_for_briefing, process_schedule_management
from src.tools.quote import generate_daily_quote
from src.utils.api_client import APIClient

# 页面配置
st.set_page_config(
    page_title="个人每日智能简报 AI Agent",
    page_icon="📋",
    layout="wide"
)

st.title("📋 个人每日智能简报 AI Agent")

# 初始化Agent核心
@st.cache_resource
def get_agent():
    agent = AgentCore()
    api_client = APIClient()
    
    # 注册工具，传递API提供商配置
    def weather_tool(city):
        return process_weather_for_briefing(
            city, 
            weather_provider=api_client.weather_provider,
            weather_api_key=api_client.juhe_weather_api_key if api_client.weather_provider == 'juhe' else api_client.weather_api_key
        )
    
    def weather_comparison_tool(cities):
        return process_weather_comparison(
            cities,
            weather_provider=api_client.weather_provider,
            weather_api_key=api_client.juhe_weather_api_key if api_client.weather_provider == 'juhe' else api_client.weather_api_key
        )
    
    def news_tool(interests, random_mode=False):
        return process_news_for_briefing(
            interests,
            random_mode=random_mode
        )
    
    # 注册工具
    agent.register_tool('weather', weather_tool)
    agent.register_tool('weather_comparison', weather_comparison_tool)
    agent.register_tool('news', news_tool)
    agent.register_tool('calendar', process_calendar_for_briefing)
    agent.register_tool('schedule_manage', process_schedule_management)
    agent.register_tool('quote', generate_daily_quote)
    return agent

agent = get_agent()

# 用户输入
user_input = st.text_input("请输入您的请求：", placeholder="例如：生成今天的简报 / 我在广州，关注AI和半导体...")

# 处理按钮
if st.button("提交") and user_input:
    with st.spinner("正在处理您的请求..."):
        # 异步执行
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(agent.process_input(user_input))
            st.markdown(result)
        except Exception as e:
            st.error(f"处理过程中出现错误: {e}")

# 显示使用说明
st.sidebar.header("使用说明")
st.sidebar.markdown("""
### 📋 基本
- `生成今天的简报` — 生成完整日报
- `我在[城市名]` — 设置所在城市
- `关注[领域1]、[领域2]` — 设置兴趣领域

### 🌤️ 天气
- `[城市名]天气` — 查询指定城市天气
- `[城市1]和[城市2]天气对比` — 对比两个城市天气

### 🗓️ 日程
- `今天下午3点有个会议` — 添加日程
- `今天有哪些安排` — 查看今日日程

### 🔄 配置管理
- 支持自然语言配置修改
- 所有配置自动持久化保存

> 💡 **提示**：首次使用请先设置城市和兴趣领域！
""")

st.sidebar.header("项目状态")
st.sidebar.success("✅ 全部模块正常运行")