from DrissionPage import ChromiumPage,ChromiumOptions
import csv
import re
import time
from urllib.parse import urlsplit


co=ChromiumOptions()
co.set_browser_path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
# co.headless()
page=ChromiumPage(addr_or_opts=co)
LIST_URL='https://mitadmissions.org/blogs/'
# eager 模式在 DOMContentLoaded 后就停止加载，Disqus 的 count.js 不会执行，
# 评论数会一直是空。列表页必须用 normal 模式等 count.js 把评论数渲染出来；
# 详情页不依赖 count.js，稍后再切回 eager 提高速度。
page.set.load_mode.normal()
#加载页面和等待加载
page.get(LIST_URL)
page.wait.eles_loaded('.blog-list',timeout=15)

article_links=[]
all_links=page.eles('tag:a')
for link in all_links:
    href=link.attr('href')
    if not href:
        continue
    if 'mitadmissions.org/blogs/entry/' in href and href != LIST_URL:
        # 排除明显的分页链接（含 /page/ 等）
        if '/page/' not in href and '#' not in href:
            article_links.append(href)

#把每个链接转换成key去重，再转换成列表
article_links=list(dict.fromkeys(article_links))

print(f'共找到{len(article_links)}篇博客链接')


def normalize_url(url):
    """去掉锚点、查询参数和末尾斜杠，方便用链接匹配评论数"""
    parts = urlsplit(url)
    return f'{parts.scheme}://{parts.netloc}{parts.path}'.rstrip('/')


def collect_comment_counts(timeout=15):
    """
    评论数由 Disqus 的 count.js 异步写入列表页的 #disqus_thread 链接里，
    详情页的评论区是跨域 iframe，DOM 里读不到评论数，所以先在列表页收集。
    """
    links = []
    end_time = time.time() + timeout
    while time.time() < end_time:
        links = [a for a in page.eles('tag:a') if '#disqus_thread' in (a.attr('href') or '')]
        # count.js 会把每个链接的文字改成 “N comments”，全部有文字才算渲染完成
        if links and all(a.text.strip() for a in links):
            break
        time.sleep(0.5)

    counts = {}
    for link in links:
        match = re.search(r'\d+', link.text)
        href = link.attr('href') or ''
        if match and href:
            counts[normalize_url(href)] = int(match.group())
    return counts


comment_counts = collect_comment_counts()
if len(comment_counts) < len(article_links):
    print(f'[警告] 只获取到{len(comment_counts)}/{len(article_links)}篇文章的评论数，请检查能否正常访问 Disqus')

# 列表页的工作已完成，详情页切回 eager 模式加快加载
page.set.load_mode.eager()

# 定义CSV文件
CSV_FILE='mit_blogs.csv'
FIELDS=['标题', '作者', '评论数', '时间', '文章内容', '文章图片']
with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
print('csv表头已写入')

#逐个访问详情页获取对应的信息
def extract_article(url, comment_count=None):
    try:
        page.get(url)
        data = {}

        # 获取标题（字符串切割法，最稳）
        title_ele = page.ele('@class:page-topper__title')
        data['标题'] = title_ele.text.split('by')[0].strip() if title_ele else ''

        # 获取作者信息
        auther_ele = page.ele('@class:page-topper__title__name')
        data['作者'] = auther_ele.text.strip() if auther_ele else ''

        # 评论数用列表页收集到的值（详情页没有可直接读取的评论数）
        data['评论数'] = comment_count if comment_count is not None else ''

        # 获取时间
        time_ele = page.ele('@class:page-topper__date') or page.ele('tag:time')
        data['时间'] = time_ele.text.strip() if time_ele else ''

        # 获取正文内容
        content_ele = page.ele('css:div.article__body')
        if content_ele:
            raw_text = content_ele.text
            # 把特定废话删掉
            clean_text = re.sub(r'An arrow pointing right\s*PreviousAn arrow pointing right\s*Next', '', raw_text)
            # 删掉多余空行
            clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
            data['文章内容'] = clean_text.strip()

        # 获取图片（如果没有正文，直接用空列表防止报错）
        img_urls = []
        img_eles = content_ele.eles('tag:img') if content_ele else []

        for img in img_eles:
            src = img.attr('src')
            if src:
                img_urls.append(src)

        data['文章图片'] = ';'.join(img_urls)

        return data
    except Exception as e:
        print(f'[失败]{url} -> {e}')
        return None  # 出错时返回 None，防止继续写入 CSV

#主循环
success=0
for i, url in enumerate(article_links,1):
    print(f'[正在处理：{i}/{len(article_links)}条...]')
    data=extract_article(url, comment_counts.get(normalize_url(url)))
    if data:
        with open(CSV_FILE,'a',newline='',encoding='utf-8-sig')as f:
            writer=csv.DictWriter(f,fieldnames=FIELDS)
            writer.writerow(data)
        success+=1
        print(f'已保存：{data['标题'][:10]}')
    else:
        print('跳过')

print(f"采集成功:{success}篇，csv文件:{CSV_FILE}")
page.quit()
