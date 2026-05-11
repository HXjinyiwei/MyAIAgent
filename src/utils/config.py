import os
import yaml
from pathlib import Path

class ConfigManager:
    """配置文件管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
    
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
                    'weather_provider': 'openweathermap'
                }
            }
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: dict):
        """保存配置到文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        self.config = config
    
    def get(self, key: str, default=None):
        """获取配置值，支持嵌套键如 'user.city'"""
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
        return self.config.get('user', {})
    
    def update_user_config(self, user_config: dict):
        """更新用户配置"""
        self.config['user'] = user_config
        self._save_config(self.config)