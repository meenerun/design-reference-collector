import streamlit as st
import os, sys, json, time, requests
from datetime import datetime
from bs4 import BeautifulSoup

# ─── 환경변수 ─────────────────────────────────────────────────────────────────
NOTION_TOKEN = st.secrets.get("NOTION_TOKEN", os.getenv("NOTION_TOKEN", ""))
PAGE_ID = "35a06261920e80e0b6c5d27d07c5c116"
NOTION_VERSION = "2022-06-28"

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ─── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Design Reference Collector",
    page_icon="🎨",
    layout="centered",
)

st.title("🎨 Design Reference Collector")
st.caption("키워드를 입력하면 디자인 레퍼런스를 자동으로 수집해 Notion에 저장합니다.")
st.divider()

# ─── 입력 UI ──────────────────────────────────────────────────────────────────
keyword_input = st.text_input(
    "컨셉 키워드",
    placeholder="예: pink gradient chemistry DNA mystery UI",
    help="스페이스로 구분해서 입력하세요",
)

st.markdown("**수집할 사이트 선택**")
col1, col2, col3, col4 = st.columns(4)
with col1:
    use_unsection = st.checkbox("unsection", value=True)
with col2:
    use_game = st.checkbox("interfaceingame", value=True)
with col3:
    use_httpster = st.checkbox("httpster", value=True)
with col4:
    use_css = st.checkbox("cssdesignawards", value=True)

run = st.button("🔍 레퍼런스 수집하기", type="primary", use_container_width=True)

# ─── Scrapers ────────────────────────────────────────────────────────────────

def scrape_unsection():
    refs = []
    try:
        r = requests.get("https://www.unsection.com/", headers=HTTP_HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for img in soup.find_all("img")[:12]:
            src = img.get("src", "")
            if not src.startswith("http") or src in seen:
                continue
            seen.add(src)
            parent_a = img.find_parent("a", href=True)
            href = parent_a["href"] if parent_a else ""
            full_url = (
                f"https://www.unsection.com{href}"
                if href.startswith("/") else href or "https://www.unsection.com"
            )
            refs.append({"source": "unsection.com", "title": img.get("alt", full_url.split("/")[-1]), "url": full_url, "image_url": src})
    except Exception as e:
        st.warning(f"unsection.com 오류: {e}")
    return refs


def scrape_interfaceingame():
    refs = []
    try:
        r = requests.get("https://interfaceingame.com/screenshots/", headers=HTTP_HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for art in soup.find_all("article")[:12]:
            a = art.find("a", href=True)
            if not a or a["href"] in seen:
                continue
            seen.add(a["href"])
            title_el = art.find(["h1", "h2", "h3"])
            title = title_el.get_text(strip=True) if title_el else a["href"].split("/")[-2]
            refs.append({"source": "interfaceingame.com", "title": title, "url": a["href"], "image_url": None})
    except Exception as e:
        st.warning(f"interfaceingame.com 오류: {e}")
    return refs


def scrape_httpster():
    refs = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
            page.goto("https://httpster.net/", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            seen = set()
            for card in page.query_selector_all(".site-item, .item, article")[:10]:
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
                    "source": "httpster.net", "title": title,
                    "url": href if href.startswith("http") else f"https://httpster.net{href}",
                    "image_url": img_src,
                })
            browser.close()
    except Exception as e:
        st.warning(f"httpster.net 오류: {e}")
    return refs


def scrape_cssdesignawards(keywords):
    refs = []
    try:
        from playwright.sync_api import sync_playwright
        query = "+".join(keywords[:3])
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
            page.goto(f"https://www.cssdesignawards.com/search?q={query}", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            seen = set()
            for card in page.query_selector_all(".wf-item, .gallery-item, article")[:8]:
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
                refs.append({"source": "cssdesignawards.com", "title": title, "url": full_url, "image_url": img_src})
            browser.close()
    except Exception as e:
        st.warning(f"cssdesignawards.com 오류: {e}")
    return refs


# ─── Notion 업로드 ────────────────────────────────────────────────────────────

def notion_headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def build_blocks(keywords, all_refs):
    timestamp = datetime.now().strftime("%Y.%m.%d %H:%M")
    blocks = [
        {
            "object": "block", "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"🎨  {' / '.join(keywords)}"}, "annotations": {"bold": True}}],
                "icon": {"type": "emoji", "emoji": "🎨"},
                "color": "pink_background",
            }
        },
        {
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"수집일: {timestamp}  |  레퍼런스 {len(all_refs)}개"}, "annotations": {"color": "gray"}}]}
        },
        {"object": "block", "type": "divider", "divider": {}},
    ]

    site_emojis = {"unsection.com": "🖼", "interfaceingame.com": "🎮", "httpster.net": "🌐", "cssdesignawards.com": "🎖"}
    sources = {}
    for ref in all_refs:
        sources.setdefault(ref["source"], []).append(ref)

    for source, refs in sources.items():
        blocks.append({
            "object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": f"{site_emojis.get(source, '📌')}  {source}"}}]}
        })
        for ref in refs:
            if ref.get("image_url") and ref["image_url"].startswith("http"):
                blocks.append({"object": "block", "type": "image", "image": {"type": "external", "external": {"url": ref["image_url"]}}})
            blocks.append({"object": "block", "type": "bookmark", "bookmark": {"url": ref["url"]}})
        blocks.append({"object": "block", "type": "divider", "divider": {}})

    return blocks


def create_notion_page(keywords, all_refs):
    title = " + ".join(keywords[:5])
    timestamp = datetime.now().strftime("%m/%d %H:%M")
    blocks = build_blocks(keywords, all_refs)

    data = {
        "parent": {"page_id": PAGE_ID},
        "icon": {"type": "emoji", "emoji": "🔍"},
        "properties": {"title": {"title": [{"text": {"content": f"[{timestamp}] {title}"}}]}},
        "children": blocks[:100],
    }
    r = requests.post("https://api.notion.com/v1/pages", headers=notion_headers(), json=data)
    if r.status_code != 200:
        return None, r.json().get("message", "알 수 없는 오류")

    page = r.json()
    page_id = page["id"]
    for batch in [blocks[i:i+100] for i in range(100, len(blocks), 100)]:
        requests.patch(f"https://api.notion.com/v1/blocks/{page_id}/children", headers=notion_headers(), json={"children": batch})
        time.sleep(0.3)

    return page.get("url", ""), None


# ─── 실행 ─────────────────────────────────────────────────────────────────────

if run:
    if not keyword_input.strip():
        st.error("키워드를 입력해주세요.")
    elif not NOTION_TOKEN:
        st.error("NOTION_TOKEN이 설정되지 않았습니다. Streamlit Secrets를 확인하세요.")
    else:
        keywords = [k.strip() for k in keyword_input.split() if k.strip()]
        st.info(f"🔍 **{', '.join(keywords)}** 키워드로 수집 시작...")

        all_refs = []
        progress = st.progress(0)
        status = st.empty()
        sites_selected = [use_unsection, use_game, use_httpster, use_css]
        total = sum(sites_selected)
        done = 0

        if use_unsection:
            status.text("📡 unsection.com 수집 중...")
            refs = scrape_unsection()
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)
            st.write(f"✅ unsection.com — {len(refs)}개")

        if use_game:
            status.text("📡 interfaceingame.com 수집 중...")
            refs = scrape_interfaceingame()
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)
            st.write(f"✅ interfaceingame.com — {len(refs)}개")

        if use_httpster:
            status.text("📡 httpster.net 수집 중...")
            refs = scrape_httpster()
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)
            st.write(f"✅ httpster.net — {len(refs)}개")

        if use_css:
            status.text("📡 cssdesignawards.com 수집 중...")
            refs = scrape_cssdesignawards(keywords)
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)
            st.write(f"✅ cssdesignawards.com — {len(refs)}개")

        status.text("📝 Notion 페이지 생성 중...")
        notion_url, error = create_notion_page(keywords, all_refs)

        if notion_url:
            status.empty()
            progress.empty()
            st.success(f"🎉 완료! 총 **{len(all_refs)}개** 레퍼런스 수집")
            st.link_button("📖 Notion에서 보기", notion_url, use_container_width=True)
        else:
            st.error(f"Notion 페이지 생성 실패: {error}")
