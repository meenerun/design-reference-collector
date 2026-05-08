import streamlit as st
import os, time, requests
from datetime import datetime
from bs4 import BeautifulSoup

try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
except Exception:
    NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")

PAGE_ID = "35a06261920e80e0b6c5d27d07c5c116"
NOTION_VERSION = "2022-06-28"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

st.set_page_config(page_title="Design Reference Collector", page_icon="🎨", layout="wide")
st.title("🎨 Design Reference Collector")
st.divider()

# ─── 입력 UI ──────────────────────────────────────────────────────────────────
keyword_input = st.text_input(
    "컨셉 키워드",
    placeholder="예: pink gradient chemistry DNA mystery UI",
)

col1, col2, col3, col4, col5 = st.columns(5)
with col1: use_unsection     = st.checkbox("unsection",       value=True)
with col2: use_interfaceingame = st.checkbox("interfaceingame", value=True)
with col3: use_httpster       = st.checkbox("httpster",        value=True)
with col4: use_css            = st.checkbox("cssdesignawards", value=True)
with col5: use_pinterest      = st.checkbox("pinterest",       value=True)

run = st.button("🔍 레퍼런스 수집하기", type="primary", use_container_width=True)


# ─── Scrapers ────────────────────────────────────────────────────────────────

def scrape_unsection():
    refs = []
    try:
        r = requests.get("https://www.unsection.com/", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for img in soup.find_all("img")[:16]:
            src = img.get("src", "")
            if not src.startswith("http") or src in seen:
                continue
            seen.add(src)
            parent_a = img.find_parent("a", href=True)
            href = parent_a["href"] if parent_a else ""
            url = f"https://www.unsection.com{href}" if href.startswith("/") else href or "https://www.unsection.com"
            refs.append({"source": "unsection.com", "title": img.get("alt", "").strip() or "Unsection", "url": url, "image_url": src})
    except Exception as e:
        st.warning(f"unsection: {e}")
    return refs


def scrape_interfaceingame():
    refs = []
    try:
        r = requests.get("https://interfaceingame.com/screenshots/", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for art in soup.find_all("article")[:16]:
            a = art.find("a", href=True)
            if not a or a["href"] in seen:
                continue
            seen.add(a["href"])
            title = art.find(["h1","h2","h3"])
            refs.append({"source": "interfaceingame.com", "title": title.get_text(strip=True) if title else a["href"].split("/")[-2], "url": a["href"], "image_url": None})
    except Exception as e:
        st.warning(f"interfaceingame: {e}")
    return refs


def scrape_httpster():
    refs = []
    try:
        r = requests.get("https://httpster.net/", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for art in soup.find_all("article")[:16]:
            a = art.find("a", href=True)
            if not a or a["href"] in seen:
                continue
            seen.add(a["href"])
            href = a["href"]
            url = f"https://httpster.net{href}" if href.startswith("/") else href
            img = art.find("img")
            img_src = img.get("src", "") if img else ""
            if img_src.startswith("/"): img_src = f"https://httpster.net{img_src}"
            title = art.find(["h2","h3","h1"])
            refs.append({"source": "httpster.net", "title": title.get_text(strip=True) if title else href.split("/")[-2], "url": url, "image_url": img_src or None})
    except Exception as e:
        st.warning(f"httpster: {e}")
    return refs


def scrape_cssdesignawards():
    refs = []
    try:
        r = requests.get("https://www.cssdesignawards.com/website-gallery", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for art in soup.find_all("article")[:16]:
            a = art.find("a", href=True)
            if not a or a["href"] in seen:
                continue
            seen.add(a["href"])
            href = a["href"]
            url = f"https://www.cssdesignawards.com{href}" if href.startswith("/") else href
            img = art.find("img")
            img_src = img.get("src", "") if img else ""
            if img_src.startswith("/"): img_src = f"https://www.cssdesignawards.com{img_src}"
            title = art.find(["h3","h2","h1"])
            refs.append({"source": "cssdesignawards.com", "title": title.get_text(strip=True) if title else href.split("/")[-2], "url": url, "image_url": img_src or None})
    except Exception as e:
        st.warning(f"cssdesignawards: {e}")
    return refs


def scrape_pinterest(keywords):
    refs = []
    try:
        q = "+".join(keywords[:4])
        r = requests.get(f"https://www.pinterest.com/search/pins/?q={q}", headers={**HEADERS, "Accept": "text/html"}, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for img in soup.find_all("img")[:16]:
            src = img.get("src", "")
            if not src.startswith("http") or src in seen or "logo" in src.lower():
                continue
            seen.add(src)
            parent_a = img.find_parent("a", href=True)
            href = parent_a["href"] if parent_a else ""
            url = f"https://www.pinterest.com{href}" if href.startswith("/") else href or f"https://www.pinterest.com/search/pins/?q={q}"
            refs.append({"source": "pinterest.com", "title": img.get("alt", "").strip() or "Pinterest", "url": url, "image_url": src})
    except Exception as e:
        st.warning(f"pinterest: {e}")
    return refs


# ─── Streamlit 미리보기 ───────────────────────────────────────────────────────

def show_preview(all_refs):
    sources = {}
    for ref in all_refs:
        sources.setdefault(ref["source"], []).append(ref)

    site_emojis = {"unsection.com": "🖼", "interfaceingame.com": "🎮", "httpster.net": "🌐", "cssdesignawards.com": "🎖", "pinterest.com": "📌"}

    for source, refs in sources.items():
        st.subheader(f"{site_emojis.get(source,'📎')} {source}")
        cols = st.columns(4)
        for i, ref in enumerate(refs):
            with cols[i % 4]:
                if ref.get("image_url"):
                    proxy = f"https://images.weserv.nl/?url={ref['image_url']}&w=400&output=webp"
                    st.image(proxy, use_container_width=True)
                else:
                    st.markdown("🔗")
                st.markdown(f"[{ref['title'][:40]}]({ref['url']})")
        st.divider()


# ─── Notion 저장 ─────────────────────────────────────────────────────────────

def notion_headers():
    return {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": NOTION_VERSION}


def build_blocks(keywords, all_refs):
    timestamp = datetime.now().strftime("%Y.%m.%d %H:%M")
    blocks = [
        {"object": "block", "type": "callout", "callout": {
            "rich_text": [{"type": "text", "text": {"content": f"🎨  {' / '.join(keywords)}"}, "annotations": {"bold": True}}],
            "icon": {"type": "emoji", "emoji": "🎨"}, "color": "pink_background"}},
        {"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": f"수집일: {timestamp}  |  {len(all_refs)}개"}, "annotations": {"color": "gray"}}]}},
        {"object": "block", "type": "divider", "divider": {}},
    ]
    site_emojis = {"unsection.com": "🖼", "interfaceingame.com": "🎮", "httpster.net": "🌐", "cssdesignawards.com": "🎖", "pinterest.com": "📌"}
    sources = {}
    for ref in all_refs:
        sources.setdefault(ref["source"], []).append(ref)
    for source, refs in sources.items():
        blocks.append({"object": "block", "type": "heading_2", "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": f"{site_emojis.get(source,'📎')}  {source}"}}]}})
        for ref in refs:
            if ref.get("image_url") and ref["image_url"].startswith("http"):
                blocks.append({"object": "block", "type": "image", "image": {"type": "external", "external": {"url": ref["image_url"]}}})
            blocks.append({"object": "block", "type": "bookmark", "bookmark": {"url": ref["url"]}})
        blocks.append({"object": "block", "type": "divider", "divider": {}})
    return blocks


def save_to_notion(keywords, all_refs):
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
        return None, r.json().get("message", "오류")
    page = r.json()
    for batch in [blocks[i:i+100] for i in range(100, len(blocks), 100)]:
        requests.patch(f"https://api.notion.com/v1/blocks/{page['id']}/children", headers=notion_headers(), json={"children": batch})
        time.sleep(0.3)
    return page.get("url", ""), None


# ─── 키워드 필터 ──────────────────────────────────────────────────────────────

def keyword_score(ref, keywords):
    """키워드가 title/url/image_url에 몇 개 포함되는지 반환 (대소문자 무시)"""
    haystack = " ".join([
        ref.get("title", ""),
        ref.get("url", ""),
        ref.get("image_url", "") or "",
    ]).lower()
    return sum(1 for kw in keywords if kw.lower() in haystack)


def filter_refs(all_refs, keywords):
    """
    키워드가 1개면 OR(전체 반환),
    2개 이상이면 모든 키워드가 포함된 것만 반환(AND).
    AND 결과가 0이면 하나라도 포함된 것 반환 + 안내 메시지.
    """
    if len(keywords) <= 1:
        return all_refs, "and"

    matched = [r for r in all_refs if keyword_score(r, keywords) == len(keywords)]
    if matched:
        return matched, "and"

    # AND 결과 없을 때 → OR fallback (1개 이상 포함)
    partial = [r for r in all_refs if keyword_score(r, keywords) >= 1]
    return partial, "or"


# ─── 실행 ─────────────────────────────────────────────────────────────────────

if run:
    if not keyword_input.strip():
        st.error("키워드를 입력해주세요.")
    else:
        keywords = [k.strip() for k in keyword_input.split() if k.strip()]
        all_refs = []

        selected = [
            (use_unsection,      scrape_unsection,      "unsection.com"),
            (use_interfaceingame,scrape_interfaceingame,"interfaceingame.com"),
            (use_httpster,       scrape_httpster,       "httpster.net"),
            (use_css,            scrape_cssdesignawards,"cssdesignawards.com"),
        ]
        total = sum(v for v, _, _ in selected) + (1 if use_pinterest else 0)
        done = 0
        progress = st.progress(0)
        status = st.empty()

        for enabled, fn, name in selected:
            if not enabled:
                continue
            status.text(f"📡 {name} 수집 중...")
            refs = fn()
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)

        if use_pinterest:
            status.text("📡 pinterest.com 수집 중...")
            refs = scrape_pinterest(keywords)
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)

        progress.empty()
        status.empty()

        if not all_refs:
            st.warning("수집된 레퍼런스가 없습니다.")
        else:
            filtered, mode = filter_refs(all_refs, keywords)

            if len(keywords) >= 2:
                if mode == "and":
                    st.success(f"✅ **{len(filtered)}개** 수집 완료 — 키워드 **전부 포함** 필터 적용")
                else:
                    st.warning(
                        f"⚠️ 키워드를 **모두** 포함한 레퍼런스가 없어 **하나 이상** 포함된 {len(filtered)}개를 표시합니다.\n\n"
                        f"> 디자인 갤러리 사이트들은 제목에 컨셉 키워드('DNA', 'chemistry' 등)를 잘 쓰지 않습니다. "
                        f"**Pinterest**에서 더 구체적인 결과를 얻으려면 영어 키워드로 시도해보세요."
                    )
            else:
                st.success(f"✅ 총 **{len(filtered)}개** 수집 완료")

            # ── 미리보기
            st.markdown("## 📋 미리보기")
            show_preview(filtered)

            # ── Notion 저장
            if NOTION_TOKEN:
                with st.spinner("Notion에 저장 중..."):
                    notion_url, error = save_to_notion(keywords, filtered)
                if notion_url:
                    st.link_button("📖 Notion에서 보기", notion_url, use_container_width=True)
                else:
                    st.error(f"Notion 저장 실패: {error}")
