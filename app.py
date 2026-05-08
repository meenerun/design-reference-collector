import streamlit as st
import os, time, requests, random
from datetime import datetime
from bs4 import BeautifulSoup

# ─── 환경변수 ─────────────────────────────────────────────────────────────────
try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
except Exception:
    NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")

try:
    ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

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
st.set_page_config(page_title="Design Reference Collector", page_icon="🎨", layout="centered")
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
        # 여러 페이지에서 긁어서 풀을 넓힘
        for page_num in range(1, 4):
            url = f"https://www.unsection.com/?page={page_num}" if page_num > 1 else "https://www.unsection.com/"
            r = requests.get(url, headers=HTTP_HEADERS, timeout=12)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "html.parser")
            seen_srcs = {ref["image_url"] for ref in refs if ref.get("image_url")}
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if not src.startswith("http") or src in seen_srcs:
                    continue
                seen_srcs.add(src)
                parent_a = img.find_parent("a", href=True)
                href = parent_a["href"] if parent_a else ""
                full_url = (
                    f"https://www.unsection.com{href}"
                    if href.startswith("/") else href or "https://www.unsection.com"
                )
                refs.append({
                    "source": "unsection.com",
                    "title": img.get("alt", "").strip() or full_url.split("/")[-1],
                    "url": full_url,
                    "image_url": src,
                })
    except Exception as e:
        st.warning(f"unsection.com 오류: {e}")
    return refs


def scrape_interfaceingame():
    refs = []
    try:
        # 여러 UI 카테고리 페이지를 긁어서 풀을 넓힘
        urls = [
            "https://interfaceingame.com/screenshots/",
            "https://interfaceingame.com/screenshots/page/2/",
            "https://interfaceingame.com/screenshots/page/3/",
        ]
        seen = set()
        for url in urls:
            r = requests.get(url, headers=HTTP_HEADERS, timeout=12)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            for art in soup.find_all("article"):
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
        st.warning(f"interfaceingame.com 오류: {e}")
    return refs


def scrape_httpster():
    refs = []
    try:
        seen = set()
        for page_num in range(1, 4):
            url = f"https://httpster.net/page/{page_num}/" if page_num > 1 else "https://httpster.net/"
            r = requests.get(url, headers=HTTP_HEADERS, timeout=12)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "html.parser")
            for art in soup.find_all("article"):
                a = art.find("a", href=True)
                if not a or a["href"] in seen:
                    continue
                seen.add(a["href"])
                href = a["href"]
                full_url = f"https://httpster.net{href}" if href.startswith("/") else href
                img = art.find("img")
                img_src = img.get("src", "") if img else ""
                if img_src and img_src.startswith("/"):
                    img_src = f"https://httpster.net{img_src}"
                title_el = art.find(["h2", "h3", "h1"])
                title = title_el.get_text(strip=True) if title_el else href.split("/")[-2]
                refs.append({
                    "source": "httpster.net",
                    "title": title,
                    "url": full_url,
                    "image_url": img_src or None,
                })
    except Exception as e:
        st.warning(f"httpster.net 오류: {e}")
    return refs


def scrape_cssdesignawards():
    refs = []
    try:
        seen = set()
        for page_num in range(1, 4):
            url = (
                f"https://www.cssdesignawards.com/website-gallery?page={page_num}"
                if page_num > 1
                else "https://www.cssdesignawards.com/website-gallery"
            )
            r = requests.get(url, headers=HTTP_HEADERS, timeout=12)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "html.parser")
            for art in soup.find_all("article"):
                a = art.find("a", href=True)
                if not a or a["href"] in seen:
                    continue
                seen.add(a["href"])
                href = a["href"]
                full_url = f"https://www.cssdesignawards.com{href}" if href.startswith("/") else href
                img = art.find("img")
                img_src = img.get("src", "") if img else ""
                if img_src and img_src.startswith("/"):
                    img_src = f"https://www.cssdesignawards.com{img_src}"
                title_el = art.find(["h3", "h2", "h1"])
                title = title_el.get_text(strip=True) if title_el else href.split("/")[-2]
                refs.append({
                    "source": "cssdesignawards.com",
                    "title": title,
                    "url": full_url,
                    "image_url": img_src or None,
                })
    except Exception as e:
        st.warning(f"cssdesignawards.com 오류: {e}")
    return refs


# ─── Claude AI 필터링 ─────────────────────────────────────────────────────────

def score_ref(ref, keywords):
    """제목 + URL에 키워드가 얼마나 포함됐는지 점수 계산"""
    text = (ref.get("title", "") + " " + ref.get("url", "")).lower()
    score = 0
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in text:
            score += 3
        # 부분 일치도 점수 부여 (예: "mystery" → "myst")
        for word in text.split("/"):
            if kw_lower[:4] in word and len(kw_lower) >= 4:
                score += 1
    return score


def filter_by_keywords(keywords, all_refs):
    """키워드 점수 기반 필터링 — 점수 높은 순 + 나머지 랜덤 보충"""
    scored = [(score_ref(ref, keywords), i, ref) for i, ref in enumerate(all_refs)]
    scored.sort(key=lambda x: (-x[0], x[1]))

    # 점수 있는 것 우선, 나머지로 20개 채우기
    matched = [ref for score, _, ref in scored if score > 0]
    unmatched = [ref for score, _, ref in scored if score == 0]
    random.shuffle(unmatched)

    result = matched + unmatched
    return result[:20]


# ─── Notion ───────────────────────────────────────────────────────────────────

def notion_req_headers():
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
    r = requests.post("https://api.notion.com/v1/pages", headers=notion_req_headers(), json=data)
    if r.status_code != 200:
        return None, r.json().get("message", "알 수 없는 오류")

    page = r.json()
    page_id = page["id"]
    for batch in [blocks[i:i+100] for i in range(100, len(blocks), 100)]:
        requests.patch(f"https://api.notion.com/v1/blocks/{page_id}/children", headers=notion_req_headers(), json={"children": batch})
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
        sites_selected = [use_unsection, use_game, use_httpster, use_css]
        total = max(sum(sites_selected), 1)
        done = 0
        progress = st.progress(0)
        status = st.empty()

        if use_unsection:
            status.text("📡 unsection.com 수집 중...")
            refs = scrape_unsection()
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)
            st.write(f"✅ unsection.com — {len(refs)}개 수집")

        if use_game:
            status.text("📡 interfaceingame.com 수집 중...")
            refs = scrape_interfaceingame()
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)
            st.write(f"✅ interfaceingame.com — {len(refs)}개 수집")

        if use_httpster:
            status.text("📡 httpster.net 수집 중...")
            refs = scrape_httpster()
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)
            st.write(f"✅ httpster.net — {len(refs)}개 수집")

        if use_css:
            status.text("📡 cssdesignawards.com 수집 중...")
            refs = scrape_cssdesignawards()
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)
            st.write(f"✅ cssdesignawards.com — {len(refs)}개 수집")

        if all_refs:
            status.text(f"🔎 {len(all_refs)}개 중 키워드 관련 레퍼런스 선별 중...")
            all_refs = filter_by_keywords(keywords, all_refs)
            st.write(f"✅ 최종 선별: **{len(all_refs)}개**")

        status.text("📝 Notion 페이지 생성 중...")
        notion_url, error = create_notion_page(keywords, all_refs)

        if notion_url:
            status.empty()
            progress.empty()
            st.success(f"🎉 완료! **{len(all_refs)}개** 레퍼런스가 Notion에 저장됐습니다.")
            st.link_button("📖 Notion에서 보기", notion_url, use_container_width=True)
        else:
            st.error(f"Notion 페이지 생성 실패: {error}")
