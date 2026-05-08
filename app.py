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
st.caption("키워드를 공백 또는 쉼표로 구분해 입력하세요. 하나라도 포함된 레퍼런스를 가져옵니다.")
keyword_input = st.text_input(
    "컨셉 키워드",
    placeholder="예: sci-fi Brutalism pink ui",
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
        for img in soup.find_all("img")[:30]:
            src = img.get("src", "")
            if not src.startswith("http") or src in seen:
                continue
            seen.add(src)
            parent_a = img.find_parent("a", href=True)
            href = parent_a["href"] if parent_a else ""
            url = f"https://www.unsection.com{href}" if href.startswith("/") else href or "https://www.unsection.com"
            # 주변 텍스트도 수집
            extra = ""
            if parent_a:
                extra = parent_a.get_text(separator=" ", strip=True)
            refs.append({
                "source": "unsection.com",
                "title": img.get("alt", "").strip() or "Unsection",
                "url": url,
                "image_url": src,
                "extra": extra,
            })
    except Exception as e:
        st.warning(f"unsection: {e}")
    return refs


def scrape_interfaceingame():
    refs = []
    try:
        r = requests.get("https://interfaceingame.com/screenshots/", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for art in soup.find_all("article")[:30]:
            a = art.find("a", href=True)
            if not a or a["href"] in seen:
                continue
            seen.add(a["href"])
            title = art.find(["h1","h2","h3"])
            title_text = title.get_text(strip=True) if title else a["href"].split("/")[-2]
            # 태그/카테고리 텍스트 추가 수집
            extra = art.get_text(separator=" ", strip=True)
            img = art.find("img")
            img_src = img.get("src", "") if img else None
            refs.append({
                "source": "interfaceingame.com",
                "title": title_text,
                "url": a["href"],
                "image_url": img_src,
                "extra": extra,
            })
    except Exception as e:
        st.warning(f"interfaceingame: {e}")
    return refs


def scrape_httpster():
    refs = []
    try:
        r = requests.get("https://httpster.net/", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for art in soup.find_all("article")[:30]:
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
            extra = art.get_text(separator=" ", strip=True)
            refs.append({
                "source": "httpster.net",
                "title": title.get_text(strip=True) if title else href.split("/")[-2],
                "url": url,
                "image_url": img_src or None,
                "extra": extra,
            })
    except Exception as e:
        st.warning(f"httpster: {e}")
    return refs


def scrape_cssdesignawards():
    refs = []
    try:
        r = requests.get("https://www.cssdesignawards.com/website-gallery", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for art in soup.find_all("article")[:30]:
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
            extra = art.get_text(separator=" ", strip=True)
            refs.append({
                "source": "cssdesignawards.com",
                "title": title.get_text(strip=True) if title else href.split("/")[-2],
                "url": url,
                "image_url": img_src or None,
                "extra": extra,
            })
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
        for img in soup.find_all("img")[:30]:
            src = img.get("src", "")
            if not src.startswith("http") or src in seen or "logo" in src.lower():
                continue
            seen.add(src)
            parent_a = img.find_parent("a", href=True)
            href = parent_a["href"] if parent_a else ""
            url = f"https://www.pinterest.com{href}" if href.startswith("/") else href or f"https://www.pinterest.com/search/pins/?q={q}"
            refs.append({
                "source": "pinterest.com",
                "title": img.get("alt", "").strip() or "Pinterest",
                "url": url,
                "image_url": src,
                "extra": "",
            })
    except Exception as e:
        st.warning(f"pinterest: {e}")
    return refs


# ─── 키워드 필터 ──────────────────────────────────────────────────────────────

def keyword_score(ref, keywords):
    haystack = " ".join([
        ref.get("title", ""),
        ref.get("url", ""),
        ref.get("image_url", "") or "",
        ref.get("extra", "") or "",
    ]).lower()
    return sum(1 for kw in keywords if kw.lower() in haystack)


def filter_and_sort(all_refs, keywords):
    """하나 이상 키워드가 포함된 ref만 반환, 많이 매칭될수록 앞으로."""
    if not keywords:
        return all_refs

    scored = [(r, keyword_score(r, keywords)) for r in all_refs]
    matched = [(r, s) for r, s in scored if s >= 1]
    matched.sort(key=lambda x: x[1], reverse=True)
    return [r for r, _ in matched]


def no_match_guide(keywords):
    kw_str = ", ".join(f'**{k}**' for k in keywords)
    return f"""
**{kw_str}** 키워드와 매칭되는 레퍼런스를 찾지 못했습니다.

**이유:** unsection, httpster, cssdesignawards, interfaceingame은 최신 디자인을 큐레이션하는 갤러리 사이트입니다. 제목이 "Hero Section Design", "Studio Rebrand" 같은 형태라 컨셉 키워드('sci-fi', 'brutalism' 등)가 제목에 잘 등장하지 않습니다.

**더 잘 찾으려면:**
- 🔎 **키워드를 더 짧게** — `sci-fi game UI` → `game`, `sci-fi`, `UI` 처럼 단어 단위로
- 🌐 **Pinterest만 켜고 시도** — Pinterest는 실제 키워드 검색이 되므로 가장 정확합니다
- 🔤 **영어 단일 단어 사용** — `pink`, `dark`, `neon`, `brutal`, `retro`, `space` 등
- 📌 **Dribbble/Behance 직접 방문** — 키워드 검색이 잘 되는 사이트입니다
    """


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


# ─── 실행 ─────────────────────────────────────────────────────────────────────

if run:
    if not keyword_input.strip():
        st.error("키워드를 입력해주세요.")
    else:
        keywords = [k.strip() for k in keyword_input.replace(",", " ").split() if k.strip()]
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
            st.warning("사이트에서 수집된 항목이 없습니다. 잠시 후 다시 시도해주세요.")
        else:
            filtered = filter_and_sort(all_refs, keywords)

            if filtered:
                st.success(f"✅ 전체 **{len(all_refs)}개** 중 키워드 매칭 **{len(filtered)}개** 표시")
                st.markdown("## 📋 미리보기")
                show_preview(filtered)
            else:
                st.warning(no_match_guide(keywords))
                with st.expander("📋 키워드 무관 전체 결과 보기"):
                    show_preview(all_refs)

            # ── Notion 저장
            if NOTION_TOKEN:
                save_target = filtered if filtered else all_refs
                with st.spinner("Notion에 저장 중..."):
                    notion_url, error = save_to_notion(keywords, save_target)
                if notion_url:
                    st.link_button("📖 Notion에서 보기", notion_url, use_container_width=True)
                else:
                    st.error(f"Notion 저장 실패: {error}")
