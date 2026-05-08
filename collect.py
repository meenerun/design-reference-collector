#!/usr/bin/env python3
"""
Design Reference Collector
Usage: python3 collect.py "pink gradient" "chemistry" "DNA" "mystery UI"
"""

import os, sys, json, time, argparse
import requests
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
PAGE_ID = "35a06261920e80e0b6c5d27d07c5c116"
NOTION_VERSION = "2022-06-28"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# ─── Notion helpers ──────────────────────────────────────────────────────────

def notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def verify_notion_token():
    r = requests.get("https://api.notion.com/v1/users/me", headers=notion_headers())
    if r.status_code != 200:
        print(f"❌ Notion 토큰 오류: {r.json().get('message', r.status_code)}")
        sys.exit(1)
    print(f"✅ Notion 연결됨: {r.json().get('name', 'Unknown')}")


# ─── Site scrapers ────────────────────────────────────────────────────────────

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_unsection(keywords, _page=None):
    """unsection.com — requests 기반, CDN 이미지 포함"""
    refs = []
    try:
        r = requests.get("https://www.unsection.com/", headers=HTTP_HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        imgs = soup.find_all("img")
        seen = set()
        for img in imgs[:12]:
            src = img.get("src", "")
            if not src.startswith("http") or src in seen:
                continue
            seen.add(src)
            parent_a = img.find_parent("a", href=True)
            href = parent_a["href"] if parent_a else ""
            full_url = (
                f"https://www.unsection.com{href}"
                if href.startswith("/")
                else href or "https://www.unsection.com"
            )
            alt = img.get("alt", "").strip() or full_url.split("/")[-1]
            refs.append({
                "source": "unsection.com",
                "title": alt,
                "url": full_url,
                "image_url": src,
            })
    except Exception as e:
        print(f"  ⚠ unsection.com 오류: {e}")
    return refs


def scrape_interfaceingame(keywords, _page=None):
    """interfaceingame.com — 게임 UI 특화, 링크 중심"""
    refs = []
    try:
        r = requests.get(
            "https://interfaceingame.com/screenshots/", headers=HTTP_HEADERS, timeout=12
        )
        soup = BeautifulSoup(r.text, "html.parser")
        articles = soup.find_all("article")
        seen = set()
        for art in articles[:12]:
            a = art.find("a", href=True)
            if not a or a["href"] in seen:
                continue
            seen.add(a["href"])
            title_el = art.find(["h1", "h2", "h3"])
            title = title_el.get_text(strip=True) if title_el else a["href"].split("/")[-2]
            refs.append({
                "source": "interfaceingame.com",
                "title": title,
                "url": a["href"],
                "image_url": None,
            })
    except Exception as e:
        print(f"  ⚠ interfaceingame.com 오류: {e}")
    return refs


def scrape_httpster(keywords, page):
    """httpster.net — Playwright 기반"""
    url = "https://httpster.net/"
    refs = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)

        cards = page.query_selector_all(".site-item, .item, article")
        seen = set()
        for card in cards[:10]:
            link = card.query_selector("a")
            if not link:
                continue
            href = link.get_attribute("href")
            if not href or href in seen:
                continue
            seen.add(href)
            img = card.query_selector("img")
            img_src = img.get_attribute("src") if img else None
            title_el = card.query_selector("h2, h3, .title")
            title = title_el.inner_text().strip() if title_el else href
            refs.append({
                "source": "httpster.net",
                "title": title,
                "url": href if href.startswith("http") else f"https://httpster.net{href}",
                "image_url": img_src,
            })
    except Exception as e:
        print(f"  ⚠ httpster.net 오류: {e}")
    return refs


def scrape_cssdesignawards(keywords, page):
    query = "+".join(keywords[:3])
    url = f"https://www.cssdesignawards.com/search?q={query}"
    refs = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)

        cards = page.query_selector_all(".wf-item, .gallery-item, article")
        seen = set()
        for card in cards[:8]:
            link = card.query_selector("a")
            if not link:
                continue
            href = link.get_attribute("href")
            if not href or href in seen:
                continue
            seen.add(href)
            full_url = f"https://www.cssdesignawards.com{href}" if href.startswith("/") else href
            img = card.query_selector("img")
            img_src = img.get_attribute("src") if img else None
            title_el = card.query_selector("h3, h2, .title")
            title = title_el.inner_text().strip() if title_el else "CSS Design Awards"
            refs.append({
                "source": "cssdesignawards.com",
                "title": title,
                "url": full_url,
                "image_url": img_src,
            })
    except Exception as e:
        print(f"  ⚠ cssdesignawards.com 오류: {e}")
    return refs


def scrape_brutalist(keywords, page):
    url = "https://brutalistwebsites.com/"
    refs = []
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)

        cards = page.query_selector_all(".item, figure, .site")
        seen = set()
        for card in cards[:8]:
            link = card.query_selector("a")
            if not link:
                continue
            href = link.get_attribute("href")
            if not href or href in seen:
                continue
            seen.add(href)
            img = card.query_selector("img")
            img_src = img.get_attribute("src") if img else None
            refs.append({
                "source": "brutalistwebsites.com",
                "title": href.replace("http://", "").replace("https://", "").split("/")[0],
                "url": href if href.startswith("http") else f"https://brutalistwebsites.com{href}",
                "image_url": img_src,
            })
    except Exception as e:
        print(f"  ⚠ brutalistwebsites.com 오류: {e}")
    return refs


# ─── Claude AI filtering ──────────────────────────────────────────────────────

def filter_with_claude(keywords, all_refs):
    """Use Claude to select most relevant references"""
    if not ANTHROPIC_API_KEY or not all_refs:
        return all_refs

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        refs_text = json.dumps(
            [{"i": i, "title": r["title"], "source": r["source"], "url": r["url"]}
             for i, r in enumerate(all_refs)],
            ensure_ascii=False, indent=2
        )

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a design curator. Keywords: {', '.join(keywords)}\n\n"
                    f"From these references, pick the 12 most relevant indices. "
                    f"Return only a JSON array of indices like [0, 3, 5, ...].\n\n"
                    f"{refs_text}"
                )
            }]
        )

        text = msg.content[0].text.strip()
        start = text.find("[")
        end = text.rfind("]") + 1
        indices = json.loads(text[start:end])
        filtered = [all_refs[i] for i in indices if 0 <= i < len(all_refs)]
        print(f"  🤖 Claude AI 필터링: {len(all_refs)} → {len(filtered)}개 선별")
        return filtered
    except Exception as e:
        print(f"  ⚠ Claude 필터링 건너뜀: {e}")
        return all_refs


# ─── Notion page builder ──────────────────────────────────────────────────────

def build_blocks(keywords, all_refs):
    timestamp = datetime.now().strftime("%Y.%m.%d %H:%M")
    blocks = []

    # 상단 요약 callout
    blocks.append({
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{
                "type": "text",
                "text": {"content": f"🎨  {' / '.join(keywords)}"},
                "annotations": {"bold": True}
            }],
            "icon": {"type": "emoji", "emoji": "🎨"},
            "color": "pink_background",
        }
    })

    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{
                "type": "text",
                "text": {"content": f"수집일: {timestamp}  |  레퍼런스 {len(all_refs)}개"},
                "annotations": {"color": "gray"}
            }]
        }
    })

    blocks.append({"object": "block", "type": "divider", "divider": {}})

    # 사이트별 그룹핑
    sources = {}
    for ref in all_refs:
        src = ref["source"]
        sources.setdefault(src, []).append(ref)

    site_emojis = {
        "unsection.com": "🖼",
        "interfaceingame.com": "🎮",
        "httpster.net": "🌐",
        "cssdesignawards.com": "🎖",
        "brutalistwebsites.com": "🧱",
    }

    for source, refs in sources.items():
        emoji = site_emojis.get(source, "📌")

        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": f"{emoji}  {source}"}}]
            }
        })

        for ref in refs:
            # 이미지 (외부 URL이 유효한 경우만)
            if ref.get("image_url") and ref["image_url"].startswith("http"):
                blocks.append({
                    "object": "block",
                    "type": "image",
                    "image": {
                        "type": "external",
                        "external": {"url": ref["image_url"]}
                    }
                })

            # 북마크 링크
            blocks.append({
                "object": "block",
                "type": "bookmark",
                "bookmark": {"url": ref["url"]}
            })

        blocks.append({"object": "block", "type": "divider", "divider": {}})

    return blocks


def create_notion_page(keywords, all_refs):
    title = " + ".join(keywords[:5])
    timestamp = datetime.now().strftime("%m/%d %H:%M")
    blocks = build_blocks(keywords, all_refs)

    # Notion API는 한 번에 최대 100개 블록 허용
    first_batch = blocks[:100]
    rest_batches = [blocks[i:i+100] for i in range(100, len(blocks), 100)]

    data = {
        "parent": {"page_id": PAGE_ID},
        "icon": {"type": "emoji", "emoji": "🔍"},
        "properties": {
            "title": {
                "title": [{"text": {"content": f"[{timestamp}] {title}"}}]
            }
        },
        "children": first_batch,
    }

    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers=notion_headers(),
        json=data,
    )

    if r.status_code != 200:
        print(f"❌ 페이지 생성 실패: {r.json()}")
        return None

    page = r.json()
    page_id = page["id"]

    # 나머지 블록 추가
    for batch in rest_batches:
        requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=notion_headers(),
            json={"children": batch},
        )
        time.sleep(0.3)

    return page.get("url", "")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="디자인 레퍼런스를 수집해 Notion에 저장합니다",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='예시: python3 collect.py "pink gradient" "chemistry" "DNA" "mystery UI"'
    )
    parser.add_argument(
        "keywords", nargs="*",
        help="컨셉 키워드 (여러 개 입력 가능)"
    )
    parser.add_argument(
        "--sites", nargs="+",
        choices=["unsection", "interfaceingame", "httpster", "css", "brutalist"],
        default=["unsection", "interfaceingame", "httpster", "css"],
        help="검색할 사이트 선택 (기본: unsection interfaceingame httpster css)"
    )
    parser.add_argument(
        "--no-ai", action="store_true",
        help="Claude AI 필터링 건너뛰기"
    )
    args = parser.parse_args()

    if not args.keywords:
        keywords_input = input("🎨 컨셉 키워드를 입력하세요 (예: pink gradient chemistry mystery): ")
        keywords = [k.strip() for k in keywords_input.split() if k.strip()]
    else:
        keywords = args.keywords

    if not keywords:
        print("키워드를 입력해주세요.")
        sys.exit(1)

    if not NOTION_TOKEN:
        print("❌ NOTION_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")
        sys.exit(1)

    print(f"\n🔍 키워드: {', '.join(keywords)}")
    print("─" * 50)

    verify_notion_token()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ playwright가 설치되지 않았습니다.")
        print("   pip3 install playwright && python3 -m playwright install chromium")
        sys.exit(1)

    all_refs = []

    # requests 기반 scrapers (playwright 불필요)
    requests_scrapers = {
        "unsection": scrape_unsection,
        "interfaceingame": scrape_interfaceingame,
    }
    # playwright 기반 scrapers
    playwright_scrapers = {
        "httpster": scrape_httpster,
        "css": scrape_cssdesignawards,
        "brutalist": scrape_brutalist,
    }

    # requests 기반 먼저 실행
    for site_key in args.sites:
        if site_key in requests_scrapers:
            print(f"\n📡 {site_key} 검색 중...")
            refs = requests_scrapers[site_key](keywords)
            print(f"  → {len(refs)}개 수집")
            all_refs.extend(refs)

    # playwright 기반 실행 (필요할 때만 브라우저 구동)
    pw_sites = [s for s in args.sites if s in playwright_scrapers]
    if pw_sites:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 900},
            )
            page = context.new_page()

            for site_key in pw_sites:
                print(f"\n📡 {site_key} 검색 중...")
                refs = playwright_scrapers[site_key](keywords, page)
                print(f"  → {len(refs)}개 수집")
                all_refs.extend(refs)

            browser.close()

    print(f"\n📦 총 {len(all_refs)}개 레퍼런스 수집됨")

    if not args.no_ai and ANTHROPIC_API_KEY and len(all_refs) > 12:
        print("🤖 Claude AI로 관련성 높은 레퍼런스 선별 중...")
        all_refs = filter_with_claude(keywords, all_refs)

    if not all_refs:
        print("⚠ 수집된 레퍼런스가 없습니다. 키워드를 바꿔서 다시 시도해보세요.")
        sys.exit(0)

    print("\n📝 Notion 페이지 생성 중...")
    notion_url = create_notion_page(keywords, all_refs)

    if notion_url:
        print(f"\n✅ 완료! Notion 페이지가 생성되었습니다:")
        print(f"   {notion_url}")
    else:
        print("❌ Notion 페이지 생성에 실패했습니다.")
        sys.exit(1)


if __name__ == "__main__":
    main()
