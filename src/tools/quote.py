import asyncio
from typing import Optional
from ..utils.api_client import APIClient

async def generate_daily_quote(profession: str = "", has_schedule: bool = False, is_weekend: bool = True) -> str:
    """
    生成每日寄语
    使用DeepSeek API根据用户职业、日程等信息生成个性化寄语
    """
    api_client = APIClient()
    
    # 构建寄语生成提示
    context_info = []
    if profession:
        context_info.append(f"用户职业：{profession}")
    if has_schedule:
        context_info.append("今日有安排的日程")
    else:
        context_info.append("今日无具体日程安排")
    
    if is_weekend:
        context_info.append("今天是周末")
    else:
        context_info.append("今天是工作日")
    
    prompt = f"""你是一个温暖而智慧的人生导师，请根据以下用户信息生成一句简短、贴合语境的每日寄语。

用户信息：
{'；'.join(context_info)}

要求：
1. 寄语要简短有力，不超过50字
2. 要贴合用户的当前状态和身份
3. 如果是周末且无日程，强调休息和灵感
4. 如果有日程安排，给予鼓励和支持  
5. 如果用户有明确职业，可以适当结合职业特点
6. 绝对不要提及任何具体地名（城市、国家、景点、地区等）

输出格式严格按照以下Markdown格式：
## ✍️ 今日寄语
“[你的寄语]”"""
    
    messages = [
        {"role": "system", "content": "你是一个温暖的人生导师，用中文生成简洁、贴切的每日寄语。不要提及任何地名。"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        result = await api_client.call_deepseek_api(messages)
        if result:
            return result
        else:
            # DeepSeek API失败时使用通用寄语
            if is_weekend and not has_schedule:
                quote = "偶尔的留白，是为了让灵感有机会敲门。好好享受这个周末。"
            elif has_schedule:
                quote = "今天的每一步都在为更好的明天铺路。加油！"
            else:
                quote = "新的一天，新的可能。相信自己，你比想象中更强大。"
            
            return f"""## ✍️ 今日寄语
“{quote}”"""
    except Exception as e:
        print(f"DeepSeek quote generation failed: {e}")
        # 完全失败时返回基础寄语
        return """## ✍️ 今日寄语
“保持好奇，持续学习，每一天都是成长的机会。”"""