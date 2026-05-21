import os
import yaml
from pathlib import Path
import time
from typing import List

class ConfigManager:
    """配置文件管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self._last_modified = 0
        self._check_config_modification()
    
    def _load_config(self) -> dict:
        """加载配置文件，如果不存在则创建默认配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        else:
            # 创建默认配置
            default_config = {
                'user': {
                    'city': '',
                    'profession': '',
                    'interests': [],
                    'features': {
                        'quote': True
                    }
                },
                'api': {
                    'weather_provider': 'openweathermap',  # 可选: openweathermap, juhe
                    'news_provider': 'newsapi',  # 可选: newsapi, juhe
                    'timeout': 30,
                    'retry_count': 3,
                    'cache_enabled': True,  # 是否启用缓存
                    'cache_weather_minutes': 30,  # 天气数据缓存时间（分钟）
                    'cache_news_minutes': 60,  # 新闻数据缓存时间（分钟）
                    'providers': {
                        'weather': {
                            'openweathermap': {
                                'base_url': 'https://api.openweathermap.org/data/2.5'
                            },
                            'juhe': {
                                'base_url': 'https://apis.juhe.cn/simpleWeather/query'
                            }
                        },
                        'news': {
                            'newsapi': {
                                'base_url': 'https://newsapi.org/v2'
                            },
                            'juhe': {
                                'base_url': 'https://v.juhe.cn/toutiao/index'
                            }
                        }
                    }
                },
                'memory': {
                    'cleanup_interval_days': 180,  # 数据清理间隔（天）
                    'max_habit_records': 1000  # 最大习惯记录数
                }
            }
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: dict):
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        self.config = config
        self._last_modified = os.path.getmtime(self.config_path) if os.path.exists(self.config_path) else time.time()
    
    def _check_config_modification(self):
        """检查配置文件是否被修改"""
        if os.path.exists(self.config_path):
            current_modified = os.path.getmtime(self.config_path)
            if current_modified > self._last_modified:
                self.config = self._load_config()
                self._last_modified = current_modified
    
    def get(self, key: str, default=None):
        """获取配置值，支持嵌套键如 'user.city'"""
        self._check_config_modification()  # 检查配置文件是否被外部修改
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value):
        """设置配置值，支持嵌套键如 'user.city'"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._save_config(self.config)
    
    def get_user_config(self) -> dict:
        """获取用户配置"""
        self._check_config_modification()
        return self.config.get('user', {})
    
    def update_user_config(self, user_config: dict):
        """更新用户配置"""
        self.config['user'] = user_config
        self._save_config(self.config)
    
    def get_api_config(self) -> dict:
        """获取API配置"""
        self._check_config_modification()
        return self.config.get('api', {})
    
    def validate_config(self) -> List[str]:
        """验证配置的有效性"""
        errors = []
        
        # 验证天气提供商
        weather_provider = self.get('api.weather_provider')
        if weather_provider not in ['openweathermap', 'juhe']:
            errors.append(f"Invalid weather provider: {weather_provider}")
        
        # 验证新闻提供商
        news_provider = self.get('api.news_provider')
        if news_provider not in ['newsapi', 'juhe']:
            errors.append(f"Invalid news provider: {news_provider}")
        
        # 验证超时设置
        timeout = self.get('api.timeout', 30)
        if not isinstance(timeout, int) or timeout < 1 or timeout > 300:
            errors.append("Timeout must be an integer between 1 and 300")
        
        # 验证重试次数
        retry_count = self.get('api.retry_count', 3)
        if not isinstance(retry_count, int) or retry_count < 0 or retry_count > 10:
            errors.append("Retry count must be an integer between 0 and 10")
        
        return errors
