import streamlit as st
import asyncio
from src.agent_core import AgentCore
from src.tools.weather import process_weather_for_briefing, process_weather_comparison
from src.tools.news import process_news_for_briefing  
from src.tools.calendar import process_calendar_for_briefing, process_schedule_management
from src.tools.quote import generate_daily_quote

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
    # 注册工具
    agent.register_tool('weather', process_weather_for_briefing)
    agent.register_tool('weather_comparison', process_weather_comparison)
    agent.register_tool('news', process_news_for_briefing)
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
- `我现在有哪些设置？` — 查询配置

### ☀️ 天气
- `我在广州` — 设置所在城市
- `中国广州和深圳天气对比` — 多城市对比表格

### 📰 新闻
- `关注AI、半导体` — 设置兴趣领域
- `今天不要AI新闻` — 临时排除（仅当天）
- `今天随机推送` — 随机探索

### 📅 日程
- `今天下午3点评审会` — 添加事项
- `把下午的会取消` — 删除事项
- `我今天有哪些事？` — 查询日程
- `接下来一周每天10点学习` — 重复日程

### ⚙️ 其他
- `我是Java开发工程师` — 设置职业
- `以后不要每日寄语了` — 开关控制
- 天气+日程冲突 → 自动触发智能提醒
""")

st.sidebar.header("项目状态")
st.sidebar.success("✅ 全部模块正常运行")