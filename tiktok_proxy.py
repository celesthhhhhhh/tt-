from flask import Flask, request, jsonify
from flask_cors import CORS
from TikTokApi import TikTokApi
import asyncio
import os
import threading
import requests

app = Flask(__name__)
CORS(app)

# Helper to run async code in a sync Flask route
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def format_proxy(proxy_url):
    """
    Преобразует строку прокси в формат, который ожидает Playwright/TikTokApi.
    Ожидается формат: http://username:password@host:port или http://host:port
    """
    if not proxy_url:
        return None
    
    # Playwright ожидает словарь с ключом 'server'
    return {"server": proxy_url}

async def get_trending_videos(count=10):
    results = []
    proxy_url = os.environ.get("PROXY_URL", None)
    
    # TikTokApi/Playwright ожидает список объектов-прокси
    proxies_list = [format_proxy(proxy_url)] if proxy_url else None
    
    async with TikTokApi() as api:
        # ВНИМАНИЕ: timeout в TikTokApi указывается в МИЛЛИСЕКУНДАХ
        # 60000 мс = 60 секунд
        await api.create_sessions(
            ms_tokens=[os.environ.get("ms_token", None)], 
            num_sessions=1, 
            sleep_after=5, 
            headless=True,
            proxies=proxies_list,
            timeout=60000, 
            browser='chromium' # Chromium обычно стабильнее на серверах
        )
        async for video in api.trending.videos(count=count):
            if not video:
                continue
            v_dict = video.as_dict
            results.append({
                "id": v_dict.get("id"),
                "desc": v_dict.get("desc"),
                "author": v_dict.get("author", {}).get("uniqueId"),
                "video_url": v_dict.get("video", {}).get("playAddr"),
                "cover": v_dict.get("video", {}).get("cover"),
                "stats": v_dict.get("stats", {})
            })
    return results

async def search_tiktok_videos(query, count=10):
    results = []
    proxy_url = os.environ.get("PROXY_URL", None)
    proxies_list = [format_proxy(proxy_url)] if proxy_url else None
    
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[os.environ.get("ms_token", None)], 
            num_sessions=1, 
            sleep_after=5, 
            headless=True,
            proxies=proxies_list,
            timeout=60000,
            browser='chromium'
        )
        async for video in api.search.search_type(query, "video", count=count):
            if not video:
                continue
            v_dict = video.as_dict
            results.append({
                "id": v_dict.get("id"),
                "desc": v_dict.get("desc"),
                "author": v_dict.get("author", {}).get("uniqueId"),
                "video_url": v_dict.get("video", {}).get("playAddr"),
                "cover": v_dict.get("video", {}).get("cover"),
                "stats": v_dict.get("stats", {})
            })
    return results

@app.route('/api/trending', methods=['GET'])
def trending():
    count = int(request.args.get('count', 10))
    try:
        videos = run_async(get_trending_videos(count))
        return jsonify(videos)
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    count = int(request.args.get('count', 10))
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    try:
        videos = run_async(search_tiktok_videos(query, count))
        return jsonify(videos)
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug/ip', methods=['GET'])
def check_ip():
    proxy = os.environ.get("PROXY_URL")
    proxies = {"http": proxy, "https": proxy} if proxy else None
    try:
        response = requests.get('https://api.ipify.org?format=json', proxies=proxies, timeout=10)
        return jsonify({
            "proxy_used": proxy is not None,
            "ip": response.json().get("ip"),
            "proxy_url_configured": proxy[:15] + "..." if proxy else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
