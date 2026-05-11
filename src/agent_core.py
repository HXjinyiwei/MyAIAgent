import asyncio
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from .utils.config import ConfigManager
from .memory import MemoryManager
from .utils.api_client import APIClient

class AgentCore:
    """Agent编排引擎核心类"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.memory_manager = MemoryManager()
        self.api_client = APIClient()
        self.tools = {}  # 工具注册表
    
    def register_tool(self, name: str, tool_func):
        """注册工具函数"""
        self.tools[name] = tool_func
    
    async def recognize_intent(self, user_input: str) -> Dict[str, Any]:
        """
        使用DeepSeek API进行意图识别
        返回格式: {'intent': 'generate_briefing' | 'modify_config' | 'chat', 'details': {...}}
        """
        prompt = f"""请分析以下用户输入的意图，并严格按照指定格式返回结果。

用户输入："{user_input}"

可能的意图类型：
1. generate_briefing - 用户想要生成每日简报（关键词：简报、日报、生成今天的简报）
2. modify_config - 用户想要修改配置（关键词：设置、配置、修改、添加、删除、关注、我在等）
3. chat - 其他所有请求

重要判断规则：
- 如果用户说"添加/新增/安排一个议程/会议/日程"，这是chat（日程管理），不是modify_config
- 如果用户说"今天下午X点有X"、"下午有个X"，这是chat（日程添加）
- 如果用户只问"今天有哪些事/安排/日程"，这是chat（日程查询）
- 如果用户问"某地天气"，这是chat（天气查询）
- 如果用户说"把X取消"、"删除X"且X与会议/日程相关，这是chat
- 只有用户明确说"生成简报/日报"才算generate_briefing

请只返回JSON格式的结果，不要包含其他任何内容：
{{"intent": "意图类型", "details": {{"raw_input": "原始输入"}}}}"""
        
        messages = [
            {"role": "system", "content": "你是一个意图识别助手，严格按照JSON格式返回结果。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result = await self.api_client.call_deepseek_api(messages)
            if result:
                import json
                return json.loads(result)
        except Exception as e:
            print(f"Intent recognition failed: {e}")
            pass
        
        # DeepSeek失败时使用规则匹配作为备用
        user_input_lower = user_input.lower()
        has_schedule_kw = any(kw in user_input for kw in ['日程', '安排', '会议', '面试', '开会', '事件', '事项', '哪些事', '什么事', '有事', '议程', '一个会', '有个会', '有个事'])
        has_add_delete = any(kw in user_input for kw in ['添加', '增加', '新增', '安排', '删除', '移除', '取消'])
        if has_schedule_kw or has_add_delete:
            return {'intent': 'chat', 'details': {'message': user_input}}
        if any(keyword in user_input_lower for keyword in ['简报', '日报', '生成', '今天']):
            return {'intent': 'generate_briefing', 'details': {}}
        elif any(keyword in user_input_lower for keyword in ['设置', '配置', '修改', '添加', '删除', '关注', '我在']):
            return {'intent': 'modify_config', 'details': {'raw_input': user_input}}
        else:
            return {'intent': 'chat', 'details': {'message': user_input}}
    
    async def generate_intelligent_reminder(self, weather_content: str, schedule_content: str) -> Optional[str]:
        """生成智能关联提醒（天气+日程联合推理）"""
        if not weather_content or not schedule_content:
            return None
            
        prompt = f"""你是一个智能生活助手，请分析以下天气信息和日程安排，检查是否存在潜在冲突或需要特别提醒的情况。

天气信息：
{weather_content}

日程安排：
{schedule_content}

请执行以下任务：
1. 检查天气是否会对日程中的外出事项产生负面影响
2. 如果有冲突，生成一条明确的警告，并给出调整建议  
3. 如果没有明显冲突，但有值得注意的信息（如降温明显），也给出温馨提醒
4. 如果完全没有关联，返回空字符串

输出格式：
- 如果有提醒："> ⚠️ **天气 + 日程冲突**：[具体提醒内容]" 或 "> ℹ️ **温馨提醒**：[提醒内容]"
- 如果无提醒：空字符串"""
        
        messages = [
            {"role": "system", "content": "你是一个智能生活助手，专注于发现天气与日程的潜在冲突。"},
            {"role": "user", "content": prompt}
        ]
        
        try:
            result = await self.api_client.call_deepseek_api(messages)
            if result and result.strip():
                return f"## ⚡ 智能提醒\n\n{result}"
            return None
        except Exception as e:
            print(f"Intelligent reminder generation failed: {e}")
            return None
    
    async def generate_briefing(self, user_input: str = "") -> str:
        """生成每日简报"""
        # 获取用户配置
        user_config = self.config_manager.get_user_config()
        
        # 并行执行各模块任务
        tasks = []
        
        # 天气模块
        weather_result = None
        if user_config.get('city'):
            weather_result = await self._execute_tool('weather', {'city': user_config['city']})
        
        # 新闻模块  
        news_result = None
        is_random = '随机' in user_input if user_input else False
        all_interests = user_config.get('interests', [])
        disabled_today = user_config.get('disabled_today', [])
        active_interests = [i for i in all_interests if i not in disabled_today]
        if disabled_today:
            user_config['disabled_today'] = []
            self.config_manager.update_user_config(user_config)
        if is_random or active_interests:
            news_result = await self._execute_tool('news', {
                'interests': active_interests if not is_random else all_interests,
                'random_mode': is_random
            })
        
        # 日程模块
        schedule_result = await self._execute_tool('calendar', {})
        
        # 寄语模块
        quote_result = None
        if user_config.get('features', {}).get('quote', True):
            is_weekend = datetime.now().weekday() >= 5
            quote_result = await self._execute_tool('quote', {
                'profession': user_config.get('profession', ''),
                'has_schedule': bool(schedule_result and '未录入' not in schedule_result),
                'is_weekend': is_weekend
            })
        
        # 生成智能关联提醒
        intelligent_reminder = None
        if weather_result and schedule_result:
            intelligent_reminder = await self.generate_intelligent_reminder(weather_result, schedule_result)
        
        # 检测日报内是否包含多城市天气对比请求
        comparison_section = None
        cities = self._extract_multi_cities(user_input) if user_input else None
        if cities:
            if len(cities) == 1:
                user_city = user_config.get('city', '')
                if user_city and user_city not in cities:
                    cities.append(user_city)
            if len(cities) >= 2:
                comparison_tool = self.tools.get('weather_comparison')
                if comparison_tool:
                    comparison_section = await comparison_tool(cities)

        # 组合简报
        briefing_parts = []
        if weather_result:
            briefing_parts.append(weather_result)
        if comparison_section:
            briefing_parts.append(comparison_section)
        if news_result:
            briefing_parts.append(news_result)
        if schedule_result:
            briefing_parts.append(schedule_result)
        if intelligent_reminder:
            briefing_parts.append(intelligent_reminder)
        if quote_result:
            briefing_parts.append(quote_result)
        
        is_empty = not briefing_parts

        # 偏好洞察（仅非空简报时加入）
        if not is_empty:
            preferences = self.memory_manager.get_user_preferences()
            insight = self._generate_preference_insight(user_config, preferences)
            if insight:
                briefing_parts.append(insight)
        
        if not briefing_parts:
            now = datetime.now()
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            weekday_str = weekdays[now.weekday()]
            is_weekend = now.weekday() >= 5
            day_type = "休息日" if is_weekend else "工作日"
            fallback_briefing_parts = [
                "## ☀️ 今日天气\n（未设置城市，暂无法查询天气。对我说\"我在广州\"即可开启天气功能。）",
                "## 📰 今日新闻\n（未设置兴趣领域。你可以对我说\"我想关注人工智能、半导体\"来定制。）",
                f"## 📅 今日日程\n（未录入日程）今天是{weekday_str}，已为你预留为灵活{day_type}。",
                f"## ✍️ 今日寄语\n\"一个人知道自己为什么而活，就可以忍受任何一种生活。好好享受这个{weekday_str}吧。\"",
                "---\n💡 你还没有告诉我你的城市和兴趣。要现在告诉我吗？"
            ]
            briefing_parts = fallback_briefing_parts
        
        briefing = "# 📋 您的每日简报 | " + self._get_current_date() + "\n\n" + "\n\n".join(briefing_parts)
        self._save_briefing(briefing)
        self._record_briefing_memory(user_config.get('interests', []))
        return briefing
    
    def _save_briefing(self, content: str):
        output_dir = os.path.join("data", "output")
        os.makedirs(output_dir, exist_ok=True)

        now = datetime.now()
        filename_ts = now.strftime("简报_%Y-%m-%d_%H%M%S.md")
        filepath_ts = os.path.join(output_dir, filename_ts)
        with open(filepath_ts, 'w', encoding='utf-8') as f:
            f.write(content)

        latest_path = os.path.join(output_dir, "简报_最新.md")
        with open(latest_path, 'w', encoding='utf-8') as f:
            f.write(content)

        all_files = sorted(
            [f for f in os.listdir(output_dir) if f.startswith("简报_") and f != "简报_最新.md" and f.endswith(".md")],
            reverse=True
        )
        keep = 30
        if len(all_files) > keep:
            for old in all_files[keep:]:
                os.remove(os.path.join(output_dir, old))

        print(f"简报已保存: {filepath_ts}")

    def _extract_multi_cities(self, user_input: str) -> Optional[List[str]]:
        cleaned = re.sub(r'天气|温度|气候|对比|比较|加上|和|与|的|怎么样', ' ', user_input)
        potential = re.findall(r'[\u4e00-\u9fff]{2,3}', cleaned)
        stopwords = {'生成', '今天', '明天', '日报', '简报', '当前', '本地', '给我', '我想', '看看', '重庆今', '怎么样'}
        return [c for c in dict.fromkeys(potential) if c not in stopwords] or None

    def _generate_preference_insight(self, user_config: dict, preferences: List[Dict]) -> Optional[str]:
        interests = user_config.get('interests', [])
        if not interests:
            return None

        pref_map = {p['domain']: p for p in preferences}
        now = datetime.now()

        suggestions = []
        for interest in interests:
            pref = pref_map.get(interest)
            if not pref:
                suggestions.append(f"你对「{interest}」还没有浏览记录，想多看看吗？")
            else:
                last = datetime.strptime(pref['last_interaction'], '%Y-%m-%d %H:%M:%S.%f')
                days_since = (now - last).days
                if days_since > 21:
                    suggestions.append(f"你已 {days_since} 天未关注「{interest}」，是否需要移除这个领域？")

        if not suggestions:
            top = sorted(preferences, key=lambda p: p['click_count'], reverse=True)[:3]
            if top:
                hot = '、'.join(f"「{p['domain']}」" for p in top)
                return f"> ℹ️ **偏好洞察**：你近期最常关注 {hot}。今天已为你加重这些领域的权重。"
            return None

        return "> ℹ️ **偏好洞察**：" + " ".join(suggestions)

    def _record_briefing_memory(self, interests: List[str]):
        for interest in interests:
            self.memory_manager.update_preference(interest, increment=1)

    def _get_current_date(self) -> str:
        """获取当前日期字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y年%m月%d日 %A")
    
    async def _execute_tool(self, tool_name: str, params: Dict) -> Optional[str]:
        """执行指定工具"""
        if tool_name in self.tools:
            try:
                return await self.tools[tool_name](**params)
            except Exception as e:
                print(f"Tool {tool_name} failed: {e}")
                return None
        return None
    
    async def handle_config_modification(self, user_input: str) -> str:
        user_config = self.config_manager.get_user_config()

        is_temporary = '今天' in user_input and any(kw in user_input for kw in ['不要', '不看', '不想', '取消'])

        prompt = f"""你是一个配置管理助手，请根据用户的自然语言请求，解析出具体的配置修改操作。

当前用户配置：
- 城市：{user_config.get('city', '未设置')}
- 职业：{user_config.get('profession', '未设置')}  
- 兴趣领域：{', '.join(user_config.get('interests', [])) if user_config.get('interests') else '未设置'}
- 寄语功能：{'开启' if user_config.get('features', {}).get('quote', True) else '关闭'}

用户请求："{user_input}"

请返回JSON格式的操作指令，包含以下字段：
- operation: "set_city" | "set_profession" | "add_interests" | "remove_interests" | "toggle_quote" | "clear_all" | "unknown"
- value: 具体的值（对于add/remove_interests，value是兴趣列表）
- confirmation_message: 给用户的确认回复消息（不要包含技术术语如set_city/add_interests等）

重要：
- 如果用户只是查询当前配置（如"我现在有哪些设置"、"看看配置"等），operation设为unknown，confirmation_message中用自然语言列出所有配置，并向用户介绍可以用自然语言修改（如"要改城市可以说：我在上海"）
- 绝对不要在confirmation_message中输出set_city/set_profession/add_interests等技术操作名
- 如果用户只说了"今天不要某领域"，这可能是临时取消，请在value中标明。
- 如果用户说的兴趣与现有配置不完全匹配（如"航空航太"vs"航天"），先尝试语义匹配。
- 如果用户提到某个城市名，优先判断是否是设置城市操作（set_city），而不是添加兴趣。"""

        messages = [
            {"role": "system", "content": "你是一个配置管理助手，严格按照JSON格式返回操作指令。"},
            {"role": "user", "content": prompt}
        ]

        try:
            result = await self.api_client.call_deepseek_api(messages)
            if result:
                import json
                config_op = json.loads(result)

                if is_temporary and config_op['operation'] in ('remove_interests',):
                    disabled = config_op.get('value', [])
                    if disabled:
                        user_config['disabled_today'] = list(set(user_config.get('disabled_today', []) + disabled))
                        self.config_manager.update_user_config(user_config)
                        names = '、'.join(disabled)
                        return f"好的，今天的简报将不包含{names}相关新闻。明天会自动恢复。"
                    return config_op.get('confirmation_message', "好的，已按你的要求调整。")

                if config_op['operation'] == 'set_city':
                    user_config['city'] = config_op['value']
                elif config_op['operation'] == 'set_profession':
                    user_config['profession'] = config_op['value']
                elif config_op['operation'] == 'add_interests':
                    current_interests = user_config.get('interests', [])
                    new_values = config_op.get('value', [])
                    city = user_config.get('city', '')
                    filtered = [v for v in new_values if v != city and not v.endswith('天气') and not v.endswith('温度')]
                    if not filtered:
                        return f"「{city}」是城市不是兴趣领域，已为你设置城市为{city}。要说兴趣请用'关注AI'这样的格式。"
                    user_config['interests'] = list(set(current_interests + filtered))
                elif config_op['operation'] == 'remove_interests':
                    current_interests = user_config.get('interests', [])
                    user_config['interests'] = [i for i in current_interests if i not in config_op['value']]
                elif config_op['operation'] == 'toggle_quote':
                    features = user_config.get('features', {})
                    features['quote'] = not features.get('quote', True)
                    user_config['features'] = features
                elif config_op['operation'] == 'clear_all':
                    user_config = {'city': '', 'profession': '', 'interests': [], 'features': {'quote': True}, 'disabled_today': []}

                self.config_manager.update_user_config(user_config)
                return config_op['confirmation_message']
        except Exception as e:
            print(f"Config modification parsing failed: {e}")

        return "配置修改功能暂时不可用，请稍后再试。"
    
    async def process_input(self, user_input: str) -> str:
        """处理用户输入的主入口"""
        intent_result = await self.recognize_intent(user_input)
        
        if intent_result['intent'] == 'generate_briefing':
            return await self.generate_briefing(user_input)
        elif intent_result['intent'] == 'modify_config':
            return await self.handle_config_modification(user_input)
        else:
            # 检测多城市天气对比
            cities = self._extract_multi_cities(user_input)
            if cities and len(cities) >= 2:
                comparison_tool = self.tools.get('weather_comparison')
                if comparison_tool:
                    result = await comparison_tool(cities)
                    return result

            # 检测单城市天气查询
            if any(kw in user_input for kw in ['的天气', '天气怎么样', '气温怎么样', '天气如何']):
                city_names = self._extract_multi_cities(user_input) or []
                if not city_names:
                    cleaned = re.sub(r'天气|温度|气温|怎么样|如何|的', ' ', user_input)
                    found = re.findall(r'[\u4e00-\u9fff]{2,3}', cleaned)
                    stopwords = {'今天', '明天', '后天', '给我', '看看', '我想', '当前'}
                    city_names = [c for c in found if c not in stopwords]
                if city_names:
                    weather_tool = self.tools.get('weather')
                    if weather_tool:
                        result = await weather_tool(city_names[0])
                        return result

            # 检测日程查询/管理
            schedule_kw = ['日程', '安排', '会议', '学习', '面试', '开会', '评审', '事件', '事项', '取消', '修改日程', '同步', '周会', '例会', '培训', '哪些事', '什么事', '有事', '有个会', '有个事', '议程', '会要开']
            has_time_pattern = bool(re.search(r'(\d{1,2}[点:]|下午|上午|中午|晚上|明天|今天)', user_input))
            if has_time_pattern or any(kw in user_input for kw in schedule_kw):
                schedule_tool = self.tools.get('schedule_manage')
                if schedule_tool:
                    result = await schedule_tool(user_input)
                    return result

            # 聊天模式，调用DeepSeek API
            messages = [
                {"role": "system", "content": "你是一个智能简报助手，帮助用户管理每日信息。你可以回答一般性问题，但用户关于天气、日程、新闻等具体信息请引导他们使用'生成今天的简报'功能。"},
                {"role": "user", "content": user_input}
            ]
            result = await self.api_client.call_deepseek_api(messages)
            return result if result else f"我收到了您的消息：{user_input}"