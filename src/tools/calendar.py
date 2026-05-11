import json
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..utils.api_client import APIClient

SCHEDULE_FILE = "data/tasks.json"

GEO_STRIP_RE = re.compile(r'(浙江|广州|深圳|杭州|南京|成都|西安|武汉|重庆|北京|上海|维也纳|巴黎|伦敦|东京|纽约|悉尼|天津|长沙|郑州|青岛|大连|厦门|苏州)')

def _ensure_data_dir():
    os.makedirs("data", exist_ok=True)

def load_schedule() -> List[Dict]:
    _ensure_data_dir()
    if not os.path.exists(SCHEDULE_FILE):
        return []
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_schedule(schedule: List[Dict]):
    _ensure_data_dir()
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def _weekday_name() -> str:
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return weekdays[datetime.now().weekday()]

def _is_weekend() -> bool:
    return datetime.now().weekday() >= 5

def _sanitize_task(task_text: str) -> str:
    t = GEO_STRIP_RE.sub('', task_text).strip()
    return t if t else '未命名事项'

def _get_today_tasks(schedule: List[Dict]) -> List[Dict]:
    today = _today_str()
    result = []
    for task in schedule:
        if task.get('date') == today:
            result.append(task)
            continue
        if task.get('type') == 'recurring':
            rec = task.get('recurrence', {})
            if rec.get('type') == 'daily':
                start = task.get('date', today)
                end = rec.get('end_date', today)
                if start <= today <= end:
                    result.append(task)
    return sorted(result, key=lambda t: t.get('time', ''))

async def process_schedule_management(user_input: str) -> str:
    schedule = load_schedule()
    today = _today_str()

    prompt = f"""你是一个日程解析器，请解析用户的日程请求，只返回JSON，不要添加解释。

当前日期：{today}（{_weekday_name()}）

用户请求："{user_input}"

操作类型：add / delete / modify / query

JSON格式：
{{"operation":"操作类型","tasks":[{{"time":"HH:MM或模糊时间","task":"事项描述","type":"normal|fuzzy|recurring","recurrence":{{"type":"daily","end_date":"YYYY-MM-DD"}},"query_match":"删除/修改用于匹配的关键词"}}]}}

示例：
"下午3点评审会" → {{"operation":"add","tasks":[{{"time":"15:00","task":"评审会","type":"normal","recurrence":null}}]}}
"每天9点健身到5月10日" → {{"operation":"add","tasks":[{{"time":"09:00","task":"健身","type":"recurring","recurrence":{{"type":"daily","end_date":"2026-05-10"}}}}]}}
"取消下午的会" → {{"operation":"delete","tasks":[{{"query_match":"下午"}}]}}
"今天有什么安排" → {{"operation":"query","tasks":[]}}"""

    messages = [
        {"role": "system", "content": "你是日程解析器，严格返回JSON，不添加解释，不虚构任务内容。"},
        {"role": "user", "content": prompt}
    ]

    api_client = APIClient()
    try:
        result = await api_client.call_deepseek_api(messages)
        if not result:
            return "日程管理功能暂时不可用，请稍后再试。"

        import json as json_module
        result_clean = result.strip()
        brace_start = result_clean.find('{')
        brace_end = result_clean.rfind('}')
        if brace_start == -1 or brace_end == -1:
            return "日程解析失败，请换个方式描述，如'今天下午3点评审会'。"
        result_clean = result_clean[brace_start:brace_end + 1]
        op = json_module.loads(result_clean)
        operation = op.get('operation', '')

        if operation == 'add' and op.get('tasks'):
            names = []
            for task in op['tasks']:
                task_name = _sanitize_task(task.get('task', ''))
                task['task'] = task_name
                task['date'] = task.get('date', today)
                task['id'] = str(uuid.uuid4())[:8]
                schedule.append(task)
                t = task['time']
                tp = task.get('type', 'normal')
                if tp == 'recurring' and task.get('recurrence'):
                    end = task['recurrence'].get('end_date', '')
                    names.append(f"每天{t} {task_name}（至{end}）")
                elif tp == 'fuzzy':
                    names.append(f"{t}(待定) {task_name}")
                else:
                    names.append(f"{t} {task_name}")
            save_schedule(schedule)
            return "已添加日程：" + "、".join(names)

        elif operation == 'delete':
            query = op.get('tasks', [{}])[0].get('query_match', '')
            before = len(schedule)
            if query:
                def _match(task):
                    if query in task.get('task', ''):
                        return True
                    if query in task.get('time', ''):
                        return True
                    t = task.get('time', '')
                    if t and ':' in t:
                        h = int(t.split(':')[0])
                        parts = {'下午': (12, 18), '上午': (6, 12), '中午': (11, 13), '晚上': (18, 24), '早上': (6, 10)}
                        for k, (lo, hi) in parts.items():
                            if k in query and lo <= h < hi:
                                return True
                    return any(kw in query for kw in ['今天', '全部', '所有', '都'])
                schedule = [t for t in schedule if not _match(t)]
            else:
                schedule = [t for t in schedule if t.get('date') != today]
            removed = before - len(schedule)
            save_schedule(schedule)
            if removed == 0:
                today_tasks = _get_today_tasks(schedule)
                if today_tasks:
                    names = '、'.join(f"{t.get('time','')} {t.get('task','')}" for t in today_tasks)
                    return f"未找到匹配的日程。当前日程有：{names}"
                return "未找到匹配的日程。当前暂无日程。"
            return f"已移除 {removed} 项日程"

        elif operation == 'modify' and op.get('tasks'):
            query = op['tasks'][0].get('query_match', '')
            new_task = op['tasks'][0]
            if new_task:
                new_task['task'] = _sanitize_task(new_task.get('task', ''))
                for i, t in enumerate(schedule):
                    if query and (query in t.get('task', '') or query in t.get('time', '')):
                        new_task['id'] = t.get('id', str(uuid.uuid4())[:8])
                        new_task['date'] = t.get('date', today)
                        schedule[i] = new_task
                        save_schedule(schedule)
                        return f"已修改日程为：{new_task.get('time','')} {new_task['task']}"
            return "未找到匹配的日程进行修改。"

        elif operation == 'query':
            today_tasks = _get_today_tasks(schedule)
            if not today_tasks:
                return f"今天是{_weekday_name()}，暂无日程安排。"
            lines = [f"  {t.get('time','待定')}  {t.get('task','')}" for t in today_tasks]
            return f"今天{_weekday_name()}的日程：\n" + "\n".join(lines)

        else:
            return "没能理解你的日程请求，请试试：'今天下午3点评审会' 或 '我今天有哪些事'"

    except Exception as e:
        print(f"Schedule management failed: {e}")
        return "日程管理功能暂时不可用，请稍后再试。"

async def process_calendar_for_briefing() -> str:
    schedule = load_schedule()
    today_tasks = _get_today_tasks(schedule)

    if not today_tasks:
        return "## 📅 今日日程\n（暂无日程录入）"

    rows = []
    has_fuzzy = False
    for item in today_tasks:
        time_str = item.get('time', '待定')
        task_str = item.get('task', '未命名事项')
        task_type = item.get('type', 'normal')
        if task_type == 'fuzzy':
            has_fuzzy = True
            rows.append(f"| {time_str} (待定) | {task_str} |")
        else:
            rows.append(f"| {time_str} | {task_str} |")

    table = "| 时间 | 事项 |\n| :--- | :--- |\n" + "\n".join(rows)

    briefing = f"## 📅 今日日程\n\n{table}"

    if has_fuzzy:
        briefing += "\n\n> ℹ️ **提示**：你有一些待定时间的安排，建议你说'把会议安排在16:00'来确认具体时间。"

    if len(today_tasks) > 6:
        briefing += "\n\n> ⚠️ **提示**：你今天的日程较满，建议预留缓冲时间。"

    return briefing
