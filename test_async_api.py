import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_apis():
    print("=== 异步 API 测试（改进版）===\n")
    
    # 测试 OpenWeatherMap (异步)
    print("1. 测试 OpenWeatherMap API (异步)")
    weather_key = os.getenv('WEATHER_API_KEY')
    if weather_key:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.openweathermap.org/data/2.5/weather?q=Guangzhou&appid={weather_key}&units=metric&lang=zh_cn",
                    timeout=30
                ) as response:
                    print(f"   状态码: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ 温度: {data['main']['temp']:.1f}°C")
                        print(f"   🌤️  天气: {data['weather'][0]['description']}")
                    else:
                        text = await response.text()
                        print(f"   ❌ 错误: {text}")
        except Exception as e:
            print(f"   ❌ 异常: {e}")
    
    # 测试 NewsAPI (异步) - 改进版本
    print("\n2. 测试 NewsAPI (异步 - 改进版)")
    news_key = os.getenv('NEWS_API_KEY')
    if news_key:
        try:
            async with aiohttp.ClientSession() as session:
                # 使用改进的参数：移除country，使用英文language
                async with session.get(
                    f"https://newsapi.org/v2/everything?q=technology&apiKey={news_key}&language=en",
                    timeout=60
                ) as response:
                    print(f"   状态码: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ 新闻数量: {len(data.get('articles', []))}")
                        # 显示第一条新闻标题（如果有）
                        if data.get('articles'):
                            print(f"   📰  示例: {data['articles'][0].get('title', '无标题')[:50]}...")
                    else:
                        text = await response.text()
                        print(f"   ❌ 错误: {text}")
        except Exception as e:
            print(f"   ❌ 异常: {e}")

if __name__ == "__main__":
    asyncio.run(test_apis())