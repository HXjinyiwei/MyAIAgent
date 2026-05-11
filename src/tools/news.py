import asyncio
from typing import List, Dict, Optional
from ..utils.api_client import APIClient

async def get_news_data(interests: List[str], random_mode: bool = False) -> Optional[List[Dict]]:
    api_client = APIClient()
    return await api_client.get_news_data(interests, random_mode=random_mode)

async def process_news_for_briefing(interests: List[str], random_mode: bool = False) -> str:
    if not interests and not random_mode:
        return "## 📰 今日新闻\n（未设置兴趣领域。你可以对我说\"我想关注人工智能、半导体\"来定制。）"

    news_data = await get_news_data(interests, random_mode=random_mode)
    if not news_data:
        return "## 📰 今日新闻\n新闻服务暂时不可用，请稍后再试。"
    
    # 准备新闻数据供DeepSeek处理
    news_articles = []
    for article in news_data[:15]:  # 限制处理数量
        news_articles.append({
            'title': article.get('title', ''),
            'description': article.get('description', ''),
            'url': article.get('url', ''),
            'source': article.get('source', {}).get('name', '未知来源'),
            'published_at': article.get('publishedAt', '')
        })
    
    # 使用DeepSeek API处理新闻
    api_client = APIClient()
    
    prompt = f"""你是一个专业的新闻编辑，请根据以下候选新闻和用户兴趣领域，生成一份高质量的每日科技新闻简报。

用户兴趣领域：{', '.join(interests)}

候选新闻列表：
"""
    
    for i, article in enumerate(news_articles[:15], 1):  # 最多处理15条
        prompt += f"{i}. 标题：{article['title']}\n   摘要：{article['description']}\n   来源：{article['source']}\n   链接：{article['url']}\n\n"
    
    prompt += """请执行以下任务：
1. 去重：过滤掉报道同一事件的不同来源新闻
2. 低质过滤：过滤掉没有实质新闻价值的条目（如软件包版本发布、API文档更新等），优先选取有分析价值的报道
3. 筛选：从候选新闻中选出最重要的4-5条，优先选择与用户兴趣高度相关的
4. 生成简评：为每条选中的新闻写一句个性化简评，解释为什么这条新闻值得关注
5. 探索推荐：确保其中1条是跨界推荐（与核心兴趣交叉的内容）

输出格式要求：
- 简评**必须以句号结尾**，且**不包含链接**
- `[查看原文](链接)` **必须独占一行**，前后各空一行
- 简评和链接之间不要有任何标点符号粘连

严格按照以下Markdown格式：
## 📰 今日科技新闻 Top [数量]

1. **[新闻标题]**
   来源：[来源名称] | 相关度：⭐⭐⭐⭐⭐
   > 简评：[简评内容，以句号结尾。]

   [查看原文](链接)

2. **[新闻标题]**
   ...（以此类推）"""
    
    messages = [
        {"role": "system", "content": "你是一个专业的新闻编辑助手，用中文生成简洁、有价值的新闻简报。"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        result = await api_client.call_deepseek_api(messages)
        if result:
            return result
        else:
            # DeepSeek API失败时使用备用格式
            sample_news = [
                {
                    'title': 'AI技术取得重大突破',
                    'description': '相关技术进展值得关注',
                    'url': '#',
                    'source': '科技媒体',
                    'relevance': 5
                }
            ]
            
            news_items = []
            for i, article in enumerate(sample_news[:5], 1):
                stars = "⭐" * article['relevance']
                news_item = f"""{i}. **{article['title']}
   来源：{article['source']} | 相关度：{stars}
   > 简评：{article['description']}
   [查看原文]({article['url']})"""
                news_items.append(news_item)
            
            return "## 📰 今日科技新闻 Top " + str(len(news_items)) + "\n\n" + "\n\n".join(news_items)
    except Exception as e:
        print(f"DeepSeek news generation failed: {e}")
        return "## 📰 今日新闻\n新闻内容生成失败，请稍后再试。"