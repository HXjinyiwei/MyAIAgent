import os
from dotenv import load_dotenv
import requests

# 加载环境变量
load_dotenv()

print("=== API 连接测试脚本 ===\n")

# 测试 DeepSeek API
print("1. 测试 DeepSeek API")
deepseek_key = os.getenv('DEEPSEEK_API_KEY')
if deepseek_key:
    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {deepseek_key}"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hello"}]},
            timeout=10
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ DeepSeek API 连接成功")
            # 检查是否有用量信息
            usage_info = response.json().get('usage', {})
            if usage_info:
                print(f"   💡 用量信息: {usage_info}")
        else:
            print(f"   ❌ DeepSeek API 错误: {response.text}")
    except Exception as e:
        print(f"   ❌ DeepSeek API 异常: {e}")
else:
    print("   ⚠️ DeepSeek 密钥未设置")

# 测试 OpenWeatherMap
print("\n2. 测试 OpenWeatherMap API")
weather_key = os.getenv('WEATHER_API_KEY')
if weather_key:
    try:
        response = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q=Guangzhou&appid={weather_key}&units=metric&lang=zh_cn",
            timeout=10
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ OpenWeatherMap API 连接成功")
            weather_data = response.json()
            print(f"   🌡️  广州当前温度: {weather_data['main']['temp']:.1f}°C")
            print(f"   🌤️  天气状况: {weather_data['weather'][0]['description']}")
        else:
            print(f"   ❌ OpenWeatherMap API 错误: {response.text}")
    except Exception as e:
        print(f"   ❌ OpenWeatherMap API 异常: {e}")
else:
    print("   ⚠️ Weather API 密钥未设置")

# 测试 NewsAPI  
print("\n3. 测试 NewsAPI")
news_key = os.getenv('NEWS_API_KEY')
if news_key:
    try:
        response = requests.get(
            f"https://newsapi.org/v2/top-headlines?country=cn&apiKey={news_key}",
            timeout=10
        )
        print(f"   状态码: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ NewsAPI 连接成功")
            news_data = response.json()
            article_count = len(news_data.get('articles', []))
            print(f"   📰  获取到 {article_count} 条新闻")
        else:
            print(f"   ❌ NewsAPI 错误: {response.text}")
    except Exception as e:
        print(f"   ❌ NewsAPI 异常: {e}")
else:
    print("   ⚠️ NewsAPI 密钥未设置")

print("\n=== 测试完成 ===")