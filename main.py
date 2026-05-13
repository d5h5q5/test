import requests
import json
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from typing import List, Dict, Optional
import urllib3

from sdk import CoreSDK

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SunonNewsCollector:
    def __init__(self, base_url: str = "https://mmm.isunon.com/news/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.verify = False

        proxy_domain = "10.2.3.112:7000"
        proxy_auth = os.environ.get("PROXY_AUTH")

        proxy_url = f"socks5://{proxy_auth}@{proxy_domain}" if proxy_auth else None
        self.proxy = proxy_url
        if proxy_url:
            self.session.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

    def download_image(self, img_url: str, save_dir: str = "news_images") -> Optional[str]:
        try:
            os.makedirs(save_dir, exist_ok=True)
            filename = os.path.basename(urlparse(img_url).path) or f"news_{int(time.time())}.jpg"
            filepath = os.path.join(save_dir, filename)
            response = self.session.get(img_url, timeout=10, verify=False)
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return filepath
        except Exception as e:
            CoreSDK.Log.error(f"下载图片失败 {img_url}: {e}")
            return None

    def parse_news_list(self, html_content: str, max_items: int = 10, download_images: bool = False) -> List[Dict]:
        soup = BeautifulSoup(html_content, 'html.parser')
        news_items = []
        for i, element in enumerate(soup.select('ul.swiper-e1.ul-news li')[:max_items]):
            news_data = {}
            title_elem = element.select_one('.tit')
            link_elem = element.select_one('a.con')
            desc_elem = element.select_one('.desc')
            date_elem = element.select_one('.date')
            category_elem = element.select_one('.span')
            img_elem = element.select_one('.pic img')

            if title_elem:
                news_data['title'] = title_elem.get_text(strip=True)
            if link_elem and link_elem.get('href'):
                news_data['link'] = urljoin(self.base_url, link_elem['href'])
            if desc_elem:
                news_data['description'] = desc_elem.get_text(strip=True)
            if date_elem:
                news_data['publish_time'] = date_elem.get_text(strip=True)
            if category_elem:
                news_data['category'] = category_elem.get_text(strip=True)
            if img_elem and img_elem.get('src'):
                img_url = urljoin(self.base_url, img_elem['src'])
                news_data['image_url'] = img_url
                if img_elem.get('alt'):
                    news_data['image_alt'] = img_elem['alt']
                if download_images:
                    news_data['local_image_path'] = self.download_image(img_url)

            if news_data.get('title'):
                news_data['index'] = i + 1
                news_items.append(news_data)
        return news_items

    def collect_page(self, url: str, max_items: int = 10, download_images: bool = False) -> List[Dict]:
        try:
            response = self.session.get(url, timeout=15, verify=False)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return self.parse_news_list(response.text, max_items, download_images)
        except Exception as e:
            CoreSDK.Log.error(f"采集页面失败 {url}: {e}")
            return []

    def save_to_json(self, data: List[Dict], filename: str):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            CoreSDK.Log.error(f"保存JSON失败: {e}")

    def save_to_txt(self, data: List[Dict], filename: str):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for item in data:
                    f.write(f"序号: {item.get('index', 'N/A')}\n")
                    f.write(f"标题: {item.get('title', '无标题')}\n")
                    f.write(f"链接: {item.get('link', '无链接')}\n")
                    f.write(f"描述: {item.get('description', '无描述')}\n")
                    f.write(f"发布时间: {item.get('publish_time', '未知')}\n")
                    f.write(f"分类: {item.get('category', '未知')}\n")
                    f.write(f"图片URL: {item.get('image_url', '无图片')}\n")
                    if item.get('image_alt'):
                        f.write(f"图片描述: {item.get('image_alt')}\n")
                    if item.get('local_image_path'):
                        f.write(f"本地图片路径: {item.get('local_image_path')}\n")
                    f.write("=" * 60 + "\n\n")
        except Exception as e:
            CoreSDK.Log.error(f"保存TXT失败: {e}")


if __name__ == "__main__":
    input_json_dict = CoreSDK.Parameter.get_input_json_dict()
    collector = SunonNewsCollector()

    # 测试代理
    if collector.proxy:
        try:
            ip_resp = requests.get("https://ipinfo.io/ip", proxies={"http": collector.proxy, "https": collector.proxy}, timeout=10, verify=False)
            CoreSDK.Log.info(f"当前代理出口IP: {ip_resp.text.strip()}")
        except Exception as e:
            CoreSDK.Log.info(f"无法获取代理出口 IP: {e}")

    # 采集新闻
    news_data = collector.collect_page(input_json_dict["url"], input_json_dict["maximum"], input_json_dict["download_images"])
    CoreSDK.Log.info(f"采集到 {len(news_data)} 条新闻")

    if news_data:
        collector.save_to_json(news_data, "sunon_news_sample.json")
        collector.save_to_txt(news_data, "sunon_news_sample.txt")

        # 推送数据到 SDK
        headers = [
            {"label": "标题", "key": "title", "format": "text"},
            {"label": "时间", "key": "publish_time", "format": "text"},
            {"label": "分类", "key": "category", "format": "text"},
        ]
        CoreSDK.Result.set_table_header(headers)

        for news in news_data:
            obj = {
                "title": news.get('title'),
                "publish_time": news.get('publish_time'),
                "category": news.get('category'),
            }
            CoreSDK.Result.push_data(obj)