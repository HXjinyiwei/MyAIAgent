import asyncio
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from ..utils.api_client import APIClient

async def get_weather_data(city: str) -> Optional[Dict]:
    api_client = APIClient()
    return await api_client.get_weather_data(city)

def _extract_weather_data(weather_data: Dict, city_name: str) -> Dict:
    weather_info = weather_data['weather'][0] if weather_data.get('weather') else {}
    main_data = weather_data.get('main', {})
    temp = main_data.get('temp', 0)
    return {
        'city_name': weather_data.get('name', city_name),
        'description': weather_info.get('description', '未知'),
        'condition_main': weather_info.get('main', ''),
        'temp': temp,
        'temp_min': main_data.get('temp_min', temp),
        'temp_max': main_data.get('temp_max', temp),
        'feels_like': main_data.get('feels_like', 0),
        'humidity': main_data.get('humidity', 0),
        'pressure': main_data.get('pressure', 0),
        'wind_speed': weather_data.get('wind', {}).get('speed', 0),
        'visibility': weather_data.get('visibility', 0),
        'clouds': weather_data.get('clouds', {}).get('all', 0),
    }

def _get_weather_icon(description: str) -> str:
    desc_lower = description.lower()
    mapping = {
        'clear': '☀️', 'sunny': '☀️',
        'few clouds': '⛅', 'scattered clouds': '⛅',
        'broken clouds': '☁️', 'overcast clouds': '☁️',
        'light rain': '🌧️', 'moderate rain': '🌧️',
        'heavy rain': '⛈️', 'thunderstorm': '⛈️',
        'snow': '❄️', 'mist': '🌫️', 'fog': '🌫️',
    }
    icon = '🌤️'
    for key in mapping:
        if key in desc_lower:
            icon = mapping[key]
            break
    return icon

def _is_extreme_weather(condition_main: str) -> bool:
    return condition_main.lower() in ['thunderstorm', 'snow', 'blizzard', 'hurricane', 'squall', 'tornado', 'squall']

async def _generate_ai_narrative(d: Dict) -> Optional[str]:
    api_client = APIClient()
    is_extreme = _is_extreme_weather(d['condition_main'])

    prompt = f"""根据以下天气数据，生成一段自然亲切的中文天气简报（不超过150字）。

城市：{d['city_name']}
天气：{d['description']}
温度：{d['temp']:.0f}°C（范围 {d['temp_min']:.0f}~{d['temp_max']:.0f}°C）
体感：{d['feels_like']:.0f}°C
湿度：{d['humidity']}%
风速：{d['wind_speed']} m/s
能见度：{d['visibility']}m

要求：
- 描述今天天气状况、温度区间、体感
- 给出穿衣建议和出行建议
- 语气亲切自然
- {"开头加上⚠️ 极端天气警告，语气要严肃醒目" if is_extreme else ""}
- 按以下格式输出：

🌡️ 温度：[一句话描述]
🤗 体感：[一句话描述]
💡 建议：[穿衣+出行建议]"""

    messages = [
        {"role": "system", "content": "你是专业气象播报员，用中文生成简洁亲切的天气描述。"},
        {"role": "user", "content": prompt}
    ]

    try:
        result = await api_client.call_deepseek_api(messages)
        return result.strip() if result else None
    except Exception:
        return None

def _rule_based_narrative(d: Dict) -> str:
    temp = d['temp']
    feels_like = d['feels_like']
    humidity = d['humidity']
    condition_main = d['condition_main'].lower()

    if _is_extreme_weather(d['condition_main']):
        return "⚠️ 今天有极端天气，建议留在室内，注意安全。"
    if condition_main in ('rain', 'drizzle', 'shower', 'mist'):
        advice = f"🌡️ 温度 {d['temp_min']:.0f}~{d['temp_max']:.0f}°C\n🤗 体感 {feels_like:.0f}°C，湿度较高\n💡 建议：天气不佳，如需外出请携带雨具"
        return advice

    if temp < 10:
        tag = "偏冷"
        clothing = "建议穿厚外套、毛衣等保暖衣物"
    elif temp < 18:
        tag = "微凉"
        clothing = "建议加一件外套，早晚注意保暖"
    elif temp < 26:
        tag = "舒适"
        clothing = "穿着舒适，适合轻薄衣物"
    elif temp < 32:
        tag = "偏热"
        clothing = "建议短袖短裤，注意防暑"
    else:
        tag = "炎热"
        clothing = "天气炎热，注意防暑降温，减少户外活动"

    feels_diff = feels_like - temp
    if feels_diff < -2:
        feels_str = f"体感 {feels_like:.0f}°C，比实际温度偏凉"
    elif feels_diff > 2:
        feels_str = f"体感 {feels_like:.0f}°C，比实际温度闷热"
    else:
        feels_str = f"体感 {feels_like:.0f}°C，与实际温度相近"

    if humidity > 70:
        feels_str += "，湿度较高"
    elif humidity < 40:
        feels_str += "，空气偏干燥"

    return f"🌡️ 温度 {d['temp_min']:.0f}~{d['temp_max']:.0f}°C，天气{tag}\n🤗 {feels_str}\n💡 建议：{clothing}，{'适合户外活动' if temp > 15 and temp < 30 else '注意适当调整活动'}"

async def process_weather_for_briefing(city: str) -> str:
    if not city:
        return "## ☀️ 今日天气\n（未设置城市，暂无法查询天气。对我说\"我在广州\"即可开启天气功能。）"

    weather_data = await get_weather_data(city)
    if not weather_data:
        return "## ☀️ 今日天气\n天气服务暂时不可用，请稍后再试。"

    try:
        d = _extract_weather_data(weather_data, city)
        icon = _get_weather_icon(d['description'])
        is_extreme = _is_extreme_weather(d['condition_main'])

        if abs(d['temp_max'] - d['temp_min']) >= 1.5:
            temp_header = f"{d['temp_min']:.0f} ~ {d['temp_max']:.0f}°C"
        else:
            temp_header = f"{d['temp']:.0f}°C"

        extreme_badge = " ⚠️极端天气" if is_extreme else ""
        narration = await _generate_ai_narrative(d) or _rule_based_narrative(d)

        briefing = f"""## ☀️ 今日天气 · {d['city_name']}{extreme_badge}
{icon} **{d['description']}** | {temp_header} | 💧{d['humidity']}%

{narration}

| 项目 | 数值 |
| :--- | :--- |
| 🌡️ 温度范围 | {temp_header} |
| 🤗 体感温度 | {d['feels_like']:.0f}°C |
| 💧 湿度 | {d['humidity']}% |
| 🌬️ 风速 | {d['wind_speed']} m/s |
| 👁️ 能见度 | {d['visibility']}m |"""

        return briefing

    except KeyError as e:
        print(f"Weather data parsing failed: {e}")
        return f"## ☀️ 今日天气\n天气数据解析失败：{str(e)}"

async def process_weather_comparison(cities: List[str]) -> str:
    tasks = [get_weather_data(city) for city in cities]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    city_data = {}
    for city, result in zip(cities, results):
        if isinstance(result, Exception) or not result:
            continue
        try:
            city_data[city] = _extract_weather_data(result, city)
        except Exception:
            continue

    if not city_data:
        return "## ☀️ 天气对比\n天气服务暂时不可用，请稍后再试。"

    table_rows = []
    for city, d in city_data.items():
        icon = _get_weather_icon(d['description'])
        table_rows.append(
            f"| {icon} {d['city_name']} | {d['temp_min']:.0f}~{d['temp_max']:.0f}°C | {d['description']} | {d['humidity']}% | {d['wind_speed']} m/s |"
        )

    table = "| 城市 | 温度 | 天气 | 湿度 | 风速 |\n| :--- | :--- | :--- | :--- | :--- |\n" + "\n".join(table_rows)

    if len(city_data) >= 2:
        d_list = list(city_data.values())
        temp_diffs = [d['temp'] for d in d_list]
        analysis_prompt = f"对比以下城市的天气数据，用2-3句话给出结论（哪个更适合户外、温差多少、有什么需要注意的）：\n"
        for d in d_list:
            analysis_prompt += f"- {d['city_name']}: {d['temp_min']:.0f}~{d['temp_max']:.0f}°C, {d['description']}, 湿度{d['humidity']}%\n"

        api_client = APIClient()
        messages = [
            {"role": "system", "content": "你是一个天气分析助手，用中文简洁对比多个城市的天气。"},
            {"role": "user", "content": analysis_prompt}
        ]
        try:
            analysis = await api_client.call_deepseek_api(messages)
        except Exception:
            analysis = None
    else:
        analysis = None

    result = f"""## ☀️ 今日天气对比

{table}
"""
    if analysis:
        result += f"\n> 🤔 **对比分析**：{analysis}"

    return result
