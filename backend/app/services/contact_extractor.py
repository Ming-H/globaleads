"""
联系方式提取器

从网页内容中提取联系方式（免费，无 API 调用）。
使用正则表达式提取邮箱、电话号码、社交媒体链接。
"""
import re
import logging
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# 邮箱正则（排除常见的非联系邮箱）
EMAIL_RE = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
)

# 排除的邮箱域名（noreply、notification 等非人邮箱）
EXCLUDED_EMAIL_DOMAINS = {
    'example.com', 'test.com', 'email.com',
    'noreply', 'no-reply', 'notification', 'newsletter',
    'sentry.io', 'github.com', 'wixpress.com',
}

# 电话正则（国际格式），使用 \b 词边界避免匹配到纯数字串
PHONE_RE = re.compile(
    r'\b(?:\+?1\s*[.\-\s]?)?'  # 美国国家码
    r'(?:\(\d{3}\)|\d{3})'     # 区号
    r'\s*[.\-\s]?\s*'           # 分隔符
    r'\d{3}'                    # 前三位
    r'\s*[.\-\s]?\s*'           # 分隔符
    r'\d{4}\b'                  # 后四位
    r'|\b\+\d{1,3}[\s.\-]?\d[\d\s.\-]{6,14}\d\b',  # 国际格式：必须 + 开头
)

# 社交媒体链接正则
TWITTER_RE = re.compile(
    r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]{1,15})',
    re.IGNORECASE,
)
LINKEDIN_RE = re.compile(
    r'(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/([a-zA-Z0-9\-_%]+)',
    re.IGNORECASE,
)
FACEBOOK_RE = re.compile(
    r'(?:https?://)?(?:www\.)?facebook\.com/([a-zA-Z0-9.\-]+)',
    re.IGNORECASE,
)

# mailto: 链接
MAILTO_RE = re.compile(r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})', re.IGNORECASE)

# URL 正则
URL_RE = re.compile(r'https?://[^\s<>"\')\]]+', re.IGNORECASE)


def _is_valid_email(email: str) -> bool:
    """检查邮箱是否有效（排除 noreply、图片文件等）"""
    email_lower = email.lower()
    local_part = email_lower.split('@')[0]

    # 排除常见非联系邮箱
    for excluded in EXCLUDED_EMAIL_DOMAINS:
        if excluded in email_lower:
            return False

    # 排除图片文件
    if email_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
        return False

    # 排除过短或过长的
    if len(local_part) < 2 or len(email) > 254:
        return False

    return True


def _clean_phone(phone: str) -> str:
    """清理电话号码格式"""
    # 移除非数字字符（保留 + 和空格）
    cleaned = re.sub(r'[^\d+\s\-\(\)\.]', '', phone)
    # 去掉前后空格
    cleaned = cleaned.strip()
    # 基本长度验证
    digits_only = re.sub(r'[^\d]', '', cleaned)
    if len(digits_only) < 7 or len(digits_only) > 15:
        return ''
    return cleaned


def extract_contacts_from_text(text: str) -> dict:
    """
    从文本中提取联系方式

    Args:
        text: 要分析的文本

    Returns:
        {"emails": [...], "phones": [...], "twitter": [...], "linkedin": [...], "facebook": [...], "websites": [...]}
    """
    if not text:
        return {"emails": [], "phones": [], "twitter": [], "linkedin": [], "facebook": [], "websites": []}

    # 提取 mailto 链接（优先级最高）
    mailto_emails = [m.group(1) for m in MAILTO_RE.finditer(text)]

    # 提取普通邮箱
    all_emails = [m.group(0) for m in EMAIL_RE.finditer(text)]
    emails = list(dict.fromkeys(mailto_emails + [e for e in all_emails if _is_valid_email(e)]))

    # 提取电话
    phones = []
    for m in PHONE_RE.finditer(text):
        cleaned = _clean_phone(m.group(0))
        if cleaned:
            phones.append(cleaned)
    phones = list(dict.fromkeys(phones))

    # 提取社交账号
    twitter = list(dict.fromkeys(m.group(1) for m in TWITTER_RE.finditer(text)))
    linkedin = list(dict.fromkeys(m.group(0) for m in LINKEDIN_RE.finditer(text)))
    facebook = list(dict.fromkeys(m.group(0) for m in FACEBOOK_RE.finditer(text)))

    # 提取网站（排除社交媒体和常见非公司网站）
    excluded_domains = {'twitter.com', 'x.com', 'facebook.com', 'linkedin.com',
                        'youtube.com', 'reddit.com', 'bsky.app', 'google.com',
                        'wikipedia.org', 'github.com'}
    websites = []
    for m in URL_RE.finditer(text):
        url = m.group(0)
        try:
            domain = urlparse(url).netloc.lower()
            domain = domain.replace('www.', '')
            if not any(exc in domain for exc in excluded_domains) and domain:
                websites.append(url)
        except Exception:
            continue
    websites = list(dict.fromkeys(websites))

    return {
        "emails": emails[:5],
        "phones": phones[:3],
        "twitter": twitter[:3],
        "linkedin": linkedin[:3],
        "facebook": facebook[:3],
        "websites": websites[:5],
    }


def extract_contacts_from_website(url: str, timeout: float = 15.0) -> dict:
    """
    从网站页面提取联系方式

    优先抓取首页和 /contact、/about 页面。

    Args:
        url: 网站 URL
        timeout: 请求超时时间

    Returns:
        提取的联系方式
    """
    all_contacts = {
        "emails": [], "phones": [], "twitter": [],
        "linkedin": [], "facebook": [], "websites": [],
    }

    # 规范化 URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # 尝试抓取 3 个页面（首页 + 联系页）
    paths_to_try = ['/', '/contact', '/about']

    with httpx.Client(timeout=timeout, follow_redirects=True, headers={
        "User-Agent": "Mozilla/5.0 (compatible; GlobalLeads/1.0)",
    }) as client:
        for path in paths_to_try:
            try:
                page_url = f"{base_url}{path}"
                resp = client.get(page_url)
                if resp.status_code != 200:
                    continue

                text = resp.text
                contacts = extract_contacts_from_text(text)

                # 合并结果
                for key in all_contacts:
                    for item in contacts.get(key, []):
                        if item not in all_contacts[key]:
                            all_contacts[key].append(item)

                # 如果首页已经找到邮箱，跳过后续页面
                if all_contacts["emails"]:
                    break

            except Exception:
                continue

            # 同域名请求间隔 1 秒，避免被封
            time.sleep(1.0)

    return all_contacts


def extract_contacts_from_html(html: str) -> dict:
    """
    从 HTML 内容中提取联系方式

    Args:
        html: HTML 文本

    Returns:
        提取的联系方式
    """
    # 移除 script 和 style 标签内容，减少误匹配
    clean_html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    clean_html = re.sub(r'<style[^>]*>.*?</style>', '', clean_html, flags=re.DOTALL | re.IGNORECASE)

    # 提取 href 属性中的链接
    href_links = re.findall(r'href=["\']([^"\']+)["\']', clean_html, re.IGNORECASE)
    href_text = ' '.join(href_links)

    # 合并正文和 href 文本
    combined = clean_html + ' ' + href_text

    return extract_contacts_from_text(combined)
