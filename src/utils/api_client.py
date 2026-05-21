import os
import asyncio
import aiohttp
import requests
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from .config import ConfigManager

# 加载环境变量
load_dotenv()

class APIClient:
    """API客户端管理器"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.weather_api_key = os.getenv('WEATHER_API_KEY')
        self.news_api_key = os.getenv('NEWS_API_KEY')
        self.juhe_weather_api_key = os.getenv('JUHE_WEATHER_API_KEY') or os.getenv('WEATHER_API_KEY')
        self.juhe_news_api_key = os.getenv('JUHE_NEWS_API_KEY') or os.getenv('NEWS_API_KEY')
        self.weather_provider = os.getenv('WEATHER_PROVIDER', 'openweathermap')
        self.news_provider = os.getenv('NEWS_PROVIDER', 'newsapi')
        
        # 从配置文件获取API设置
        api_config = self.config_manager.get_api_config()
        self.timeout = api_config.get('timeout', 30)
        self.retry_count = api_config.get('retry_count', 3)
        
        # API端点配置
        self.deepseek_base_url = "https://api.deepseek.com"
        self.openweathermap_base_url = "https://api.openweathermap.org/data/2.5"
        self.newsapi_base_url = "https://newsapi.org/v2"
        self.juhe_weather_base_url = "https://apis.juhe.cn/simpleWeather/query"
        self.juhe_news_base_url = "https://v.juhe.cn/toutiao/index"

        self._requests_session = requests.Session()
    
    async def call_deepseek_api(self, messages: List[Dict], model: str = "deepseek-chat") -> Optional[str]:
        """调用DeepSeek API"""
        if not self.deepseek_api_key:
            raise ValueError("DeepSeek API key not configured")
        
        url = f"{self.deepseek_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=self.timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content'].strip()
                    else:
                        error_text = await response.text()
                        print(f"DeepSeek API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            print(f"DeepSeek API call failed: {e}")
            return None
    
    def _get_cache_key(self, service_type: str, **kwargs) -> str:
        """生成缓存键"""
        if service_type == 'weather':
            city = kwargs.get('city', '')
            return f"weather_{self.weather_provider}_{city}_{datetime.now().strftime('%Y-%m-%d')}"
        elif service_type == 'news':
            interests = kwargs.get('interests', [])
            random_mode = kwargs.get('random_mode', False)
            interest_str = '_'.join(sorted(interests)) if interests else 'all'
            mode_str = 'random' if random_mode else 'normal'
            return f"news_{self.news_provider}_{interest_str}_{mode_str}_{datetime.now().strftime('%Y-%m-%d')}"
        return None
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """从缓存获取数据"""
        try:
            from ..memory import MemoryManager
            memory_manager = MemoryManager()
            
            conn = sqlite3.connect(memory_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT cache_value FROM cache_data 
                WHERE cache_key = ? AND expires_at > ?
            ''', (cache_key, datetime.now()))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                import json
                return json.loads(result[0])
        except Exception as e:
            print(f"Cache read failed: {e}")
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict, expire_minutes: int = 30):
        """保存数据到缓存"""
        try:
            from ..memory import MemoryManager
            memory_manager = MemoryManager()
            
            expires_at = datetime.now() + timedelta(minutes=expire_minutes)
            import json
            cache_value = json.dumps(data, ensure_ascii=False, default=str)
            
            conn = sqlite3.connect(memory_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO cache_data (cache_key, cache_value, expires_at)
                VALUES (?, ?, ?)
            ''', (cache_key, cache_value, expires_at))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Cache save failed: {e}")
    
    async def _get_openweathermap_data(self, city: str) -> Optional[Dict]:
        # 检查缓存
        cache_key = self._get_cache_key('weather', city=city)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        if not self.weather_api_key:
            return None

        geo = await self._geocode_city(city)
        if not geo:
            return None

        url = f"{self.openweathermap_base_url}/weather"
        params = {
            'lat': geo['lat'],
            'lon': geo['lon'],
            'appid': self.weather_api_key,
            'units': 'metric',
            'lang': 'zh_cn'
        }

        try:
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(None, lambda: self._requests_session.get(url, params=params, timeout=self.timeout))
            if resp.status_code == 200:
                result = resp.json()
                result['name'] = city
                # 保存到缓存（30分钟）
                self._save_to_cache(cache_key, result, expire_minutes=30)
                return result
            print(f"Weather API error: {resp.status_code} - {resp.text}")
            return None
        except Exception as e:
            print(f"Weather API call failed: {e}")
            return None
    
    async def _get_juhe_weather_data(self, city: str) -> Optional[Dict]:
        # 检查缓存
        cache_key = self._get_cache_key('weather', city=city)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        if not self.juhe_weather_api_key:
            return None
        
        import urllib.parse
        encoded_city = urllib.parse.quote(city, encoding='utf-8')
        url = f"{self.juhe_weather_base_url}?key={self.juhe_weather_api_key}&city={encoded_city}"
        
        try:
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(None, lambda: self._requests_session.get(url, timeout=self.timeout))
            if resp.status_code == 200:
                result = resp.json()
                if result.get('error_code') == 0:
                    juhe_data = result.get('result', {})
                    if not juhe_data:
                        return None
                    
                    realtime = juhe_data.get('realtime', {})
                    future = juhe_data.get('future', [])
                    
                    # 构建标准化的天气数据结构
                    standardized_data = {
                        'name': juhe_data.get('city', city),
                        'weather': [{'description': realtime.get('info', '未知')}],
                        'main': {
                            'temp': float(realtime.get('temperature', 0)) if realtime.get('temperature') else 0,
                            'feels_like': float(realtime.get('temperature', 0)) if realtime.get('temperature') else 0,
                            'humidity': int(realtime.get('humidity', 0)) if realtime.get('humidity') else 0,
                            'pressure': 1013  # juhe不提供气压，使用标准值
                        },
                        'wind': {
                            'speed': 0  # juhe不提供风速，暂时设为0
                        },
                        'visibility': 10000,  # juhe不提供能见度，使用默认值
                        'clouds': {'all': 0}  # juhe不提供云量，设为0
                    }
                    
                    # 如果有未来天气数据，取第一天作为当前温度范围
                    if future:
                        day_data = future[0]
                        temp_str = day_data.get('temperature', '0/0℃')
                        # 解析温度字符串如 "1/7℃"
                        if '℃' in temp_str:
                            temp_parts = temp_str.replace('℃', '').split('/')
                            if len(temp_parts) == 2:
                                try:
                                    temp_min = float(temp_parts[0])
                                    temp_max = float(temp_parts[1])
                                    standardized_data['main']['temp_min'] = temp_min
                                    standardized_data['main']['temp_max'] = temp_max
                                    # 如果没有实时温度，使用平均温度
                                    if standardized_data['main']['temp'] == 0:
                                        standardized_data['main']['temp'] = (temp_min + temp_max) / 2
                                except ValueError:
                                    pass
                    
                    # 保存到缓存（30分钟）
                    self._save_to_cache(cache_key, standardized_data, expire_minutes=30)
                    return standardized_data
            return None
        except Exception as e:
            print(f"Juhe Weather API call failed: {e}")
            return None

    async def get_weather_data(self, city: str) -> Optional[Dict]:
        """获取天气数据 - 支持多提供商"""
        if self.weather_provider == 'openweathermap':
            return await self._get_openweathermap_data(city)
        elif self.weather_provider == 'juhe':
            return await self._get_juhe_weather_data(city)
        else:
            return None
    
    async def _expand_keywords_with_ai(self, interests: List[str]) -> List[str]:
        prompt = f"""请将以下中文兴趣领域扩展为3-5个适合搜索新闻的英文关键词（只返回逗号分隔的关键词，不要其他内容）。

兴趣领域：{', '.join(interests[:3])}

要求：
- 每个兴趣扩展1-2个同义或下位英文关键词
- 保持关键词精准，适合NewsAPI搜索
- 如果输入已经是英文，保留原词并补充同义词

示例：
输入：人工智能, 半导体
输出：artificial intelligence, AI, large language model, semiconductor, chip"""
        messages = [
            {"role": "system", "content": "你是一个关键词扩展助手，只返回逗号分隔的英文关键词。"},
            {"role": "user", "content": prompt}
        ]
        try:
            result = await self.call_deepseek_api(messages)
            if result:
                return [kw.strip() for kw in result.split(',') if kw.strip()]
        except Exception as e:
            print(f"AI keyword expansion failed: {e}")
        return []

    async def _get_newsapi_data(self, interests: List[str], random_mode: bool = False) -> Optional[List[Dict]]:
        # 检查缓存
        cache_key = self._get_cache_key('news', interests=interests, random_mode=random_mode)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        if not self.news_api_key:
            return None

        if random_mode:
            interests = ['technology', 'science', 'startup', 'future', 'innovation']

        english_keywords = []
        keyword_mapping = {
            '人工智能': 'artificial intelligence', 'AI': 'AI',
            '半导体': 'semiconductor', '科技': 'technology',
            '开源': 'open source', '新能源': 'renewable energy',
            '航天': 'space', '生物科技': 'biotechnology',
        }

        unmapped = []
        for interest in interests[:3]:
            if interest in keyword_mapping:
                english_keywords.append(keyword_mapping[interest])
            else:
                unmapped.append(interest)

        if unmapped:
            ai_keywords = await self._expand_keywords_with_ai(unmapped)
            english_keywords.extend(ai_keywords)

        if not english_keywords:
            english_keywords = ['technology']

        query = ' OR '.join(english_keywords[:5])
        
        url = f"{self.newsapi_base_url}/everything"
        params = {
            'q': query,
            'apiKey': self.news_api_key,
            # 移除 country=cn 参数，避免免费账户限制
            'language': 'en',  # 使用英文内容，兼容性更好
            'sortBy': 'publishedAt',
            'pageSize': 30
        }
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: self._requests_session.get(url, params=params, timeout=self.timeout * 2))  # 新闻API可能需要更长时间
            if response.status_code == 200:
                result = response.json()
                articles = result.get('articles', [])
                # 保存到缓存（60分钟）
                self._save_to_cache(cache_key, articles, expire_minutes=60)
                return articles
            else:
                print(f"NewsAPI error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"NewsAPI call failed: {e}")
            return None
    
    async def _get_juhe_news_data(self, news_type: str = 'top') -> Optional[List[Dict]]:
        # 检查缓存
        cache_key = self._get_cache_key('news', interests=[], random_mode=False)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        if not self.juhe_news_api_key:
            return None
        
        url = f"{self.juhe_news_base_url}?key={self.juhe_news_api_key}&type={news_type}&page_size=30"
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: self._requests_session.get(url, timeout=self.timeout))
            if response.status_code == 200:
                result = response.json()
                if result.get('error_code') == 0:
                    data = result.get('result', {}).get('data', [])
                    # 保存到缓存（60分钟）
                    self._save_to_cache(cache_key, data, expire_minutes=60)
                    return data
            return None
        except Exception as e:
            print(f"Juhe News API call failed: {e}")
            return None

    async def get_news_data(self, interests: List[str], random_mode: bool = False) -> Optional[List[Dict]]:
        """获取新闻数据 - 支持多提供商"""
        if self.news_provider == 'newsapi':
            return await self._get_newsapi_data(interests, random_mode)
        elif self.news_provider == 'juhe':
            return await self._get_juhe_news_data('top')  # juhe不支持兴趣过滤，使用推荐
        else:
            return None
    
    async def check_weather_provider_health(self) -> bool:
        """检查天气提供商健康状态"""
        try:
            if self.weather_provider == 'openweathermap':
                # 检查OpenWeatherMap API密钥有效性
                test_city = "London"
                geo_url = "http://api.openweathermap.org/geo/1.0/direct"
                params = {'q': test_city, 'limit': 1, 'appid': self.weather_api_key}
                resp = requests.get(geo_url, params=params, timeout=self.timeout)
                return resp.status_code == 200 and len(resp.json()) > 0
            
            elif self.weather_provider == 'juhe':
                # 检查聚合数据天气API密钥有效性
                test_city = "北京"
                import urllib.parse
                encoded_city = urllib.parse.quote(test_city, encoding='utf-8')
                url = f"{self.juhe_weather_base_url}?key={self.juhe_weather_api_key}&city={encoded_city}"
                resp = requests.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    result = resp.json()
                    return result.get('error_code') == 0
                return False
            
            return False
        except Exception:
            return False
    
    async def check_news_provider_health(self) -> bool:
        """检查新闻提供商健康状态"""
        try:
            if self.news_provider == 'newsapi':
                # 检查NewsAPI密钥有效性
                url = f"{self.newsapi_base_url}/top-headlines"
                params = {'country': 'us', 'apiKey': self.news_api_key, 'pageSize': 1}
                resp = requests.get(url, params=params, timeout=self.timeout)
                return resp.status_code == 200
            
            elif self.news_provider == 'juhe':
                # 检查聚合数据新闻API密钥有效性
                url = f"{self.juhe_news_base_url}?key={self.juhe_news_api_key}&type=top&page_size=1"
                resp = requests.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    result = resp.json()
                    return result.get('error_code') == 0
                return False
            
            return False
        except Exception:
            return False
