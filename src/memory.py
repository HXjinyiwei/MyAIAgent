import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional

class MemoryManager:
    """记忆管理器，使用SQLite数据库存储用户偏好和历史"""
    
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库和表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建用户偏好表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                click_count INTEGER DEFAULT 0,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建配置历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建行程历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trip_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                start_date DATE,
                end_date DATE,
                purpose TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 新增：用户交互习惯表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context_data TEXT
            )
        ''')
        
        # 新增：时间段偏好表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_period TEXT NOT NULL,
                preferred_content TEXT NOT NULL,
                interaction_count INTEGER DEFAULT 0,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 新增：缓存表（用于后续缓存机制）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT NOT NULL UNIQUE,
                cache_value TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def update_preference(self, domain: str, increment: int = 1):
        """更新用户偏好统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否存在该领域记录
        cursor.execute('SELECT click_count FROM user_preferences WHERE domain = ?', (domain,))
        result = cursor.fetchone()
        
        if result:
            new_count = result[0] + increment
            cursor.execute('''
                UPDATE user_preferences 
                SET click_count = ?, last_interaction = ?
                WHERE domain = ?
            ''', (new_count, datetime.now(), domain))
        else:
            cursor.execute('''
                INSERT INTO user_preferences (domain, click_count, last_interaction)
                VALUES (?, ?, ?)
            ''', (domain, increment, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def get_user_preferences(self) -> List[Dict]:
        """获取用户偏好列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT domain, click_count, last_interaction 
            FROM user_preferences 
            ORDER BY click_count DESC, last_interaction DESC
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'domain': row[0],
                'click_count': row[1],
                'last_interaction': row[2]
            })
        
        conn.close()
        return results
    
    def log_config_change(self, operation_type: str, old_value: str, new_value: str):
        """记录配置变更"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO config_history (operation_type, old_value, new_value)
            VALUES (?, ?, ?)
        ''', (operation_type, old_value, new_value))
        
        conn.commit()
        conn.close()
    
    def get_recent_config_changes(self, limit: int = 5) -> List[Dict]:
        """获取最近的配置变更记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT operation_type, old_value, new_value, timestamp
            FROM config_history
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'operation_type': row[0],
                'old_value': row[1],
                'new_value': row[2],
                'timestamp': row[3]
            })
        
        conn.close()
        return results
    
    # 新增方法：记录用户交互习惯
    def log_user_habit(self, interaction_type: str, context_data: Dict = None):
        """记录用户交互习惯"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        import json
        context_json = json.dumps(context_data) if context_data else None
        
        cursor.execute('''
            INSERT INTO user_habits (interaction_type, context_data)
            VALUES (?, ?)
        ''', (interaction_type, context_json))
        
        conn.commit()
        conn.close()
    
    def get_user_habits(self, interaction_type: str = None, limit: int = 10) -> List[Dict]:
        """获取用户交互习惯记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if interaction_type:
            cursor.execute('''
                SELECT interaction_type, timestamp, context_data
                FROM user_habits
                WHERE interaction_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (interaction_type, limit))
        else:
            cursor.execute('''
                SELECT interaction_type, timestamp, context_data
                FROM user_habits
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        results = []
        for row in cursor.fetchall():
            context_data = None
            if row[2]:
                try:
                    import json
                    context_data = json.loads(row[2])
                except:
                    context_data = row[2]
            
            results.append({
                'interaction_type': row[0],
                'timestamp': row[1],
                'context_data': context_data
            })
        
        conn.close()
        return results
    
    # 新增方法：记录时间段偏好
    def update_time_preference(self, time_period: str, preferred_content: str, increment: int = 1):
        """更新时间段偏好统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取当前时间
        now = datetime.now()
        
        # 检查是否存在该时间段偏好记录
        cursor.execute('''
            SELECT interaction_count FROM time_preferences 
            WHERE time_period = ? AND preferred_content = ?
        ''', (time_period, preferred_content))
        
        result = cursor.fetchone()
        
        if result:
            new_count = result[0] + increment
            cursor.execute('''
                UPDATE time_preferences 
                SET interaction_count = ?, last_interaction = ?
                WHERE time_period = ? AND preferred_content = ?
            ''', (new_count, now, time_period, preferred_content))
        else:
            cursor.execute('''
                INSERT INTO time_preferences (time_period, preferred_content, interaction_count, last_interaction)
                VALUES (?, ?, ?, ?)
            ''', (time_period, preferred_content, increment, now))
        
        conn.commit()
        conn.close()
    
    def get_time_preferences(self, time_period: str = None) -> List[Dict]:
        """获取时间段偏好列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if time_period:
            cursor.execute('''
                SELECT time_period, preferred_content, interaction_count, last_interaction
                FROM time_preferences
                WHERE time_period = ?
                ORDER BY interaction_count DESC
            ''', (time_period,))
        else:
            cursor.execute('''
                SELECT time_period, preferred_content, interaction_count, last_interaction
                FROM time_preferences
                ORDER BY interaction_count DESC, last_interaction DESC
            ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'time_period': row[0],
                'preferred_content': row[1],
                'interaction_count': row[2],
                'last_interaction': row[3]
            })
        
        conn.close()
        return results
    
    # 新增方法：数据清理策略
    def cleanup_old_data(self, months_to_keep: int = 6):
        """清理超过指定月数的历史数据"""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=months_to_keep * 30)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 清理用户交互习惯（保留6个月）
        cursor.execute('''
            DELETE FROM user_habits 
            WHERE timestamp < ?
        ''', (cutoff_date,))
        
        # 清理配置历史（保留6个月）
        cursor.execute('''
            DELETE FROM config_history 
            WHERE timestamp < ?
        ''', (cutoff_date,))
        
        # 清理过期缓存
        cursor.execute('''
            DELETE FROM cache_data 
            WHERE expires_at < ?
        ''', (datetime.now(),))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    
    # 新增方法：记忆分析
    def analyze_user_patterns(self) -> Dict:
        """分析用户使用模式"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 分析最常使用的功能
        cursor.execute('''
            SELECT interaction_type, COUNT(*) as count
            FROM user_habits
            GROUP BY interaction_type
            ORDER BY count DESC
            LIMIT 5
        ''')
        top_interactions = cursor.fetchall()
        
        # 分析活跃时间段
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN strftime('%H', timestamp) BETWEEN '06' AND '11' THEN 'morning'
                    WHEN strftime('%H', timestamp) BETWEEN '12' AND '17' THEN 'afternoon'
                    WHEN strftime('%H', timestamp) BETWEEN '18' AND '23' THEN 'evening'
                    ELSE 'night'
                END as time_period,
                COUNT(*) as count
            FROM user_habits
            GROUP BY time_period
            ORDER BY count DESC
        ''')
        active_periods = cursor.fetchall()
        
        # 分析兴趣领域趋势
        cursor.execute('''
            SELECT domain, click_count, last_interaction
            FROM user_preferences
            ORDER BY last_interaction DESC
            LIMIT 10
        ''')
        recent_interests = cursor.fetchall()
        
        conn.close()
        
        return {
            'top_interactions': [{'type': row[0], 'count': row[1]} for row in top_interactions],
            'active_periods': [{'period': row[0], 'count': row[1]} for row in active_periods],
            'recent_interests': [{'domain': row[0], 'click_count': row[1], 'last_interaction': row[2]} for row in recent_interests]
        }