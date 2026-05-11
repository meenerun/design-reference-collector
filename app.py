import streamlit as st
import os, time, requests, re
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
st.caption("기업 교육게임 그래픽 · UI 레퍼런스 수집기")
st.divider()

# ─── 세션 상태 초기화 ─────────────────────────────────────────────────────────
if "kw_value" not in st.session_state:
    st.session_state.kw_value = ""
if "active_preset" not in st.session_state:
    st.session_state.active_preset = ""

# ─── 프리셋 정의 ──────────────────────────────────────────────────────────────
PRESETS = {
    "🎮 UI": {
        "게임 HUD":        "game HUD interface UI",
        "게임화 대시보드": "gamification dashboard UI",
        "퀴즈/선택지":    "quiz game UI interaction",
        "팝업/모달":      "game popup modal UI",
        "인벤토리":       "game inventory item UI",
        "진행도/업적":    "progress achievement badge UI",
        "온보딩":         "game onboarding login screen UI",
    },
    "🖼 그래픽": {
        "캐릭터 일러스트": "character illustration flat design",
        "아이콘 세트":    "game icon set graphic design",
        "배경/환경":      "2D game background environment art",
        "인포그래픽":     "infographic data visualization design",
        "뱃지/트로피":    "badge trophy award graphic",
        "타이포그래피":   "bold typography poster graphic",
    },
    "🎨 스타일": {
        "Flat/미니멀":  "flat minimal colorful UI design",
        "다크 네온":    "dark neon cyberpunk UI",
        "기업/클린":    "corporate clean professional UI",
        "레트로 픽셀":  "retro pixel art game UI",
        "SF/미래":      "sci-fi futuristic interface design",
        "카툰/캐주얼":  "cartoon casual colorful game design",
    },
}

# ─── 레이아웃: 왼쪽 프리셋 | 오른쪽 입력+실행 ────────────────────────────────
left_col, right_col = st.columns([3, 2], gap="large")

with left_col:
    st.markdown("**빠른 키워드 선택**")
    for category, items in PRESETS.items():
        st.markdown(f"<small style='color:gray'>{category}</small>", unsafe_allow_html=True)
        btn_cols = st.columns(len(items))
        for idx, (label, kw) in enumerate(items.items()):
            is_active = st.session_state.active_preset == f"{category}_{label}"
            btn_label = f"✅ {label}" if is_active else label
            if btn_cols[idx].button(btn_label, key=f"p_{category}_{label}", use_container_width=True):
                st.session_state.kw_value = kw
                st.session_state.active_preset = f"{category}_{label}"
                st.rerun()

with right_col:
    st.markdown("**컨셉 키워드**")
    keyword_input = st.text_input(
        "컨셉 키워드",
        value=st.session_state.kw_value,
        placeholder="예: gamification dashboard dark UI",
        label_visibility="collapsed",
    )
    # 직접 타이핑 시 프리셋 선택 해제
    if keyword_input != st.session_state.kw_value:
        st.session_state.kw_value = keyword_input
        st.session_state.active_preset = ""

    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    with col1: use_behance         = st.checkbox("Behance",          value=True)
    with col2: use_interfaceingame = st.checkbox("interfaceingame",  value=True)
    with col3: use_pinterest       = st.checkbox("Pinterest",        value=True)
    with col4: use_latest          = st.checkbox("최신 트렌드",       value=False,
                                                  help="unsection · httpster · cssdesignawards")

    run = st.button("🔍 레퍼런스 수집하기", type="primary", use_container_width=True)

st.divider()


# ─── Scrapers ────────────────────────────────────────────────────────────────

def scrape_behance(keywords):
    """Behance 키워드 검색 — UI/UX 필드 + 그래픽 디자인 필드 병행"""
    refs = []
    q = "+".join(keywords)
    seen_hrefs = set()

    for url in [
        f"https://www.behance.net/search/projects?search={q}&field=ui%2Fux",
        f"https://www.behance.net/search/projects?search={q}&field=graphic-design",
        f"https://www.behance.net/search/projects?search={q}",
    ]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=14)
            soup = BeautifulSoup(r.text, "html.parser")
            imgs = soup.find_all("img", src=re.compile(r"mir-s3"))
            links = soup.find_all("a", href=re.compile(r"behance\.net/gallery/"))
            # img ↔ link 매핑 (순서 기반)
            full_links = [a["href"] for a in links if "behance.net/gallery/" in a["href"]]
            for i, img in enumerate(imgs):
                src = img.get("src", "")
                alt = img.get("alt", "").strip() or "Behance"
                href = full_links[i] if i < len(full_links) else "https://www.behance.net"
                if href in seen_hrefs:
                    continue
                seen_hrefs.add(href)
                refs.append({
                    "source": "behance.net",
                    "title": alt,
                    "url": href,
                    "image_url": src,
                    "extra": alt,
                })
        except Exception as e:
            st.warning(f"behance: {e}")
        if len(refs) >= 16:
            break
    return refs[:20]


def scrape_interfaceingame(keywords=None):
    """Game UI 스크린샷 — 키워드 URL 검색 시도 후 전체 수집"""
    refs = []
    urls_to_try = []

    # 키워드로 게임명/장르 검색 시도
    if keywords:
        q = "-".join(k.lower() for k in keywords[:2])
        urls_to_try.append(f"https://interfaceingame.com/search/?q={'+'.join(keywords)}")
    urls_to_try.append("https://interfaceingame.com/screenshots/")

    seen = set()
    for base_url in urls_to_try:
        try:
            r = requests.get(base_url, headers=HEADERS, timeout=12)
            soup = BeautifulSoup(r.text, "html.parser")
            for art in soup.find_all("article")[:24]:
                a = art.find("a", href=True)
                if not a or a["href"] in seen:
                    continue
                seen.add(a["href"])
                title_tag = art.find(["h1","h2","h3"])
                title = title_tag.get_text(strip=True) if title_tag else a["href"].split("/")[-2]
                img = art.find("img")
                img_src = img.get("src","") if img else None
                extra = art.get_text(separator=" ", strip=True)
                refs.append({
                    "source": "interfaceingame.com",
                    "title": title,
                    "url": a["href"],
                    "image_url": img_src,
                    "extra": extra,
                })
            if refs:
                break
        except Exception as e:
            st.warning(f"interfaceingame: {e}")
    return refs


def scrape_pinterest(keywords):
    refs = []
    try:
        q = "+".join(keywords[:5])
        r = requests.get(
            f"https://www.pinterest.com/search/pins/?q={q}",
            headers={**HEADERS, "Accept": "text/html"}, timeout=12
        )
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for img in soup.find_all("img")[:24]:
            src = img.get("src", "")
            if not src.startswith("http") or src in seen or "logo" in src.lower():
                continue
            seen.add(src)
            parent_a = img.find_parent("a", href=True)
            href = parent_a["href"] if parent_a else ""
            url = f"https://www.pinterest.com{href}" if href.startswith("/") else href or f"https://www.pinterest.com/search/pins/?q={q}"
            refs.append({
                "source": "pinterest.com",
                "title": img.get("alt","").strip() or "Pinterest",
                "url": url,
                "image_url": src,
                "extra": "",
            })
    except Exception as e:
        st.warning(f"pinterest: {e}")
    return refs


def scrape_unsection():
    refs = []
    try:
        r = requests.get("https://www.unsection.com/", headers=HEADERS, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        for img in soup.find_all("img")[:16]:
            src = img.get("src","")
            if not src.startswith("http") or src in seen:
                continue
            seen.add(src)
            parent_a = img.find_parent("a", href=True)
            href = parent_a["href"] if parent_a else ""
            url = f"https://www.unsection.com{href}" if href.startswith("/") else href or "https://www.unsection.com"
            refs.append({"source": "unsection.com", "title": img.get("alt","").strip() or "Unsection",
                         "url": url, "image_url": src, "extra": ""})
    except Exception as e:
        st.warning(f"unsection: {e}")
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
            img_src = img.get("src","") if img else ""
            if img_src.startswith("/"): img_src = f"https://httpster.net{img_src}"
            title = art.find(["h2","h3","h1"])
            refs.append({"source": "httpster.net",
                         "title": title.get_text(strip=True) if title else href.split("/")[-2],
                         "url": url, "image_url": img_src or None,
                         "extra": art.get_text(separator=" ", strip=True)})
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
            img_src = img.get("src","") if img else ""
            if img_src.startswith("/"): img_src = f"https://www.cssdesignawards.com{img_src}"
            title = art.find(["h3","h2","h1"])
            refs.append({"source": "cssdesignawards.com",
                         "title": title.get_text(strip=True) if title else href.split("/")[-2],
                         "url": url, "image_url": img_src or None,
                         "extra": art.get_text(separator=" ", strip=True)})
    except Exception as e:
        st.warning(f"cssdesignawards: {e}")
    return refs


# ─── Streamlit 미리보기 ───────────────────────────────────────────────────────

SITE_EMOJI = {
    "behance.net": "🎨",
    "interfaceingame.com": "🎮",
    "pinterest.com": "📌",
    "unsection.com": "🖼",
    "httpster.net": "🌐",
    "cssdesignawards.com": "🎖",
}

def show_preview(all_refs):
    sources = {}
    for ref in all_refs:
        sources.setdefault(ref["source"], []).append(ref)
    for source, refs in sources.items():
        st.subheader(f"{SITE_EMOJI.get(source,'📎')} {source}")
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
    return {"Authorization": f"Bearer {NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION}


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
    sources = {}
    for ref in all_refs:
        sources.setdefault(ref["source"], []).append(ref)
    for source, refs in sources.items():
        blocks.append({"object": "block", "type": "heading_2", "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": f"{SITE_EMOJI.get(source,'📎')}  {source}"}}]}})
        for ref in refs:
            if ref.get("image_url") and ref["image_url"].startswith("http"):
                blocks.append({"object": "block", "type": "image",
                                "image": {"type": "external", "external": {"url": ref["image_url"]}}})
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
        requests.patch(f"https://api.notion.com/v1/blocks/{page['id']}/children",
                       headers=notion_headers(), json={"children": batch})
        time.sleep(0.3)
    return page.get("url", ""), None


# ─── 실행 ─────────────────────────────────────────────────────────────────────

if run:
    if not keyword_input.strip():
        st.error("키워드를 입력해주세요.")
    else:
        keywords = [k.strip() for k in keyword_input.replace(",", " ").split() if k.strip()]
        all_refs = []

        tasks = []
        if use_behance:        tasks.append(("behance.net",         lambda: scrape_behance(keywords)))
        if use_interfaceingame:tasks.append(("interfaceingame.com", lambda: scrape_interfaceingame(keywords)))
        if use_pinterest:      tasks.append(("pinterest.com",       lambda: scrape_pinterest(keywords)))
        if use_latest:
            tasks.append(("unsection.com",      scrape_unsection))
            tasks.append(("httpster.net",        scrape_httpster))
            tasks.append(("cssdesignawards.com", scrape_cssdesignawards))

        total = len(tasks)
        done = 0
        progress = st.progress(0)
        status = st.empty()

        for name, fn in tasks:
            status.text(f"📡 {name} 수집 중...")
            refs = fn()
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)

        progress.empty()
        status.empty()

        if not all_refs:
            st.warning("사이트에서 수집된 항목이 없습니다. 잠시 후 다시 시도해주세요.")
        else:
            st.success(f"✅ **{len(all_refs)}개** 레퍼런스 수집 완료")
            st.markdown("## 📋 미리보기")
            show_preview(all_refs)

            if NOTION_TOKEN:
                with st.spinner("Notion에 저장 중..."):
                    notion_url, error = save_to_notion(keywords, all_refs)
                if notion_url:
                    st.link_button("📖 Notion에서 보기", notion_url, use_container_width=True)
                else:
                    st.error(f"Notion 저장 실패: {error}")
