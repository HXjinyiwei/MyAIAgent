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