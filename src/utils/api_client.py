import os
import asyncio
import aiohttp
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class APIClient:
    """API客户端管理器"""
    
    def __init__(self):
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.weather_api_key = os.getenv('WEATHER_API_KEY')
        self.news_api_key = os.getenv('NEWS_API_KEY')
        self.weather_provider = os.getenv('WEATHER_API_PROVIDER', 'openweathermap')
        
        # API端点配置
        self.deepseek_base_url = "https://api.deepseek.com"
        self.openweathermap_base_url = "https://api.openweathermap.org/data/2.5"
        self.newsapi_base_url = "https://newsapi.org/v2"

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
                async with session.post(url, headers=headers, json=data, timeout=30) as response:
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
    
    async def _geocode_city(self, city: str) -> Optional[Dict]:
        CITY_COORDS = {
            '重庆': (29.431586, 106.912251),
            '北京': (39.9042, 116.4074),
            '上海': (31.2304, 121.4737),
            '天津': (39.3434, 117.3616),
            '成都': (30.5728, 104.0668),
            '西安': (34.3416, 108.9398),
            '香港': (22.3193, 114.1694),
        }
        if city in CITY_COORDS:
            return {'lat': CITY_COORDS[city][0], 'lon': CITY_COORDS[city][1], 'name': city}

        geo_url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {'q': city, 'limit': 1, 'appid': self.weather_api_key}
        try:
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(None, lambda: self._requests_session.get(geo_url, params=params, timeout=10))
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return {'lat': data[0]['lat'], 'lon': data[0]['lon'], 'name': data[0].get('local_names', {}).get('zh', data[0]['name'])}
                print(f"Geocode: city '{city}' not found")
                return None
            print(f"Geocode API error: {resp.status_code} - {resp.text}")
            return None
        except Exception as e:
            print(f"Geocode API call failed: {e}")
            return None

    async def get_weather_data(self, city: str) -> Optional[Dict]:
        if not self.weather_api_key:
            raise ValueError("Weather API key not configured")

        if self.weather_provider == 'openweathermap':
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
                resp = await loop.run_in_executor(None, lambda: self._requests_session.get(url, params=params, timeout=15))
                if resp.status_code == 200:
                    result = resp.json()
                    result['name'] = city
                    return result
                print(f"Weather API error: {resp.status_code} - {resp.text}")
                return None
            except Exception as e:
                print(f"Weather API call failed: {e}")
                return None
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

    async def get_news_data(self, interests: List[str], random_mode: bool = False) -> Optional[List[Dict]]:
        if not self.news_api_key:
            raise ValueError("NewsAPI key not configured")

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
            response = await loop.run_in_executor(None, lambda: self._requests_session.get(url, params=params, timeout=60))
            if response.status_code == 200:
                result = response.json()
                return result.get('articles', [])
            else:
                print(f"NewsAPI error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"NewsAPI call failed: {e}")
            return None