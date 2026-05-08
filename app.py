import streamlit as st
import os, time, requests, json
from datetime import datetime
from bs4 import BeautifulSoup

try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
except Exception:
    NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")

PAGE_ID = "35a06261920e80e0b6c5d27d07c5c116"
NOTION_VERSION = "2022-06-28"

BING_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

st.set_page_config(page_title="Design Reference Collector", page_icon="🎨", layout="wide")
st.title("🎨 Design Reference Collector")
st.divider()

# ─── 입력 UI ──────────────────────────────────────────────────────────────────
keyword_input = st.text_input(
    "컨셉 키워드",
    placeholder="예: cute cafe game UI / blue cyberpunk mystery / pink gradient chemistry",
)

st.markdown("**검색 카테고리 선택**")
col1, col2, col3 = st.columns(3)
with col1: use_gameui  = st.checkbox("🎮 Game UI / Web Design", value=True)
with col2: use_concept = st.checkbox("🎨 Concept Art / Illustration", value=True)
with col3: use_ref     = st.checkbox("📌 Pinterest / Reference", value=True)

run = st.button("🔍 레퍼런스 수집하기", type="primary", use_container_width=True)


# ─── Bing 이미지 검색 ─────────────────────────────────────────────────────────

def bing_image_search(query, count=16):
    try:
        r = requests.get(
            "https://www.bing.com/images/search",
            params={"q": query, "form": "HDRSC2", "first": "1"},
            headers=BING_HEADERS, timeout=15,
        )
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        seen = set()
        for card in soup.select("a.iusc"):
            try:
                m = json.loads(card.get("m", "{}"))
                img_url = m.get("murl", "")
                page_url = m.get("purl", "")
                title = m.get("t", "").strip()
                if img_url and page_url and img_url not in seen:
                    seen.add(img_url)
                    domain = page_url.split("//")[-1].split("/")[0].replace("www.", "")
                    results.append({
                        "title": title or domain,
                        "url": page_url,
                        "image_url": img_url,
                        "source": domain,
                    })
                    if len(results) >= count:
                        break
            except Exception:
                continue
        return results
    except Exception as e:
        st.warning(f"검색 오류: {e}")
        return []


# ─── 미리보기 그리드 ─────────────────────────────────────────────────────────

def show_preview(label, refs):
    if not refs:
        return
    st.subheader(label)
    cols = st.columns(4)
    for i, ref in enumerate(refs):
        with cols[i % 4]:
            proxy = f"https://images.weserv.nl/?url={ref['image_url']}&w=400&output=webp"
            try:
                st.image(proxy, use_container_width=True)
            except Exception:
                st.markdown("🖼")
            st.caption(f"[{ref['title'][:35]}]({ref['url']})")
    st.divider()


# ─── Notion 저장 ─────────────────────────────────────────────────────────────

def notion_req_headers():
    return {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": NOTION_VERSION}


def build_blocks(keywords, sections):
    timestamp = datetime.now().strftime("%Y.%m.%d %H:%M")
    total = sum(len(v) for v in sections.values())
    blocks = [
        {"object": "block", "type": "callout", "callout": {
            "rich_text": [{"type": "text", "text": {"content": f"🎨  {' / '.join(keywords)}"}, "annotations": {"bold": True}}],
            "icon": {"type": "emoji", "emoji": "🎨"}, "color": "pink_background"}},
        {"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": f"수집일: {timestamp}  |  {total}개"}, "annotations": {"color": "gray"}}]}},
        {"object": "block", "type": "divider", "divider": {}},
    ]
    for section_name, refs in sections.items():
        if not refs:
            continue
        blocks.append({"object": "block", "type": "heading_2", "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": section_name}}]}})
        for ref in refs:
            if ref.get("image_url", "").startswith("http"):
                blocks.append({"object": "block", "type": "image",
                    "image": {"type": "external", "external": {"url": ref["image_url"]}}})
            blocks.append({"object": "block", "type": "bookmark", "bookmark": {"url": ref["url"]}})
        blocks.append({"object": "block", "type": "divider", "divider": {}})
    return blocks


def save_to_notion(keywords, sections):
    title = " + ".join(keywords[:5])
    timestamp = datetime.now().strftime("%m/%d %H:%M")
    blocks = build_blocks(keywords, sections)
    data = {
        "parent": {"page_id": PAGE_ID},
        "icon": {"type": "emoji", "emoji": "🔍"},
        "properties": {"title": {"title": [{"text": {"content": f"[{timestamp}] {title}"}}]}},
        "children": blocks[:100],
    }
    r = requests.post("https://api.notion.com/v1/pages", headers=notion_req_headers(), json=data)
    if r.status_code != 200:
        return None, r.json().get("message", "오류")
    page = r.json()
    for batch in [blocks[i:i+100] for i in range(100, len(blocks), 100)]:
        requests.patch(f"https://api.notion.com/v1/blocks/{page['id']}/children",
            headers=notion_req_headers(), json={"children": batch})
        time.sleep(0.3)
    return page.get("url", ""), None


# ─── 실행 ─────────────────────────────────────────────────────────────────────

if run:
    if not keyword_input.strip():
        st.error("키워드를 입력해주세요.")
    else:
        kw = keyword_input.strip()
        keywords = kw.split()

        sections = {}
        total = sum([use_gameui, use_concept, use_ref])
        done = 0
        progress = st.progress(0)
        status = st.empty()

        if use_gameui:
            status.text("🎮 Game UI / Web Design 검색 중...")
            refs = bing_image_search(f"{kw} game UI web design")
            sections["🎮 Game UI / Web Design"] = refs
            done += 1; progress.progress(done / total)

        if use_concept:
            status.text("🎨 Concept Art / Illustration 검색 중...")
            refs = bing_image_search(f"{kw} concept art illustration")
            sections["🎨 Concept Art / Illustration"] = refs
            done += 1; progress.progress(done / total)

        if use_ref:
            status.text("📌 Pinterest / Reference 검색 중...")
            refs = bing_image_search(f"{kw} design reference site:pinterest.com OR site:in.pinterest.com")
            if not refs:
                refs = bing_image_search(f"{kw} design reference inspiration")
            sections["📌 Pinterest / Reference"] = refs
            done += 1; progress.progress(done / total)

        progress.empty()
        status.empty()

        total_refs = sum(len(v) for v in sections.values())
        if total_refs == 0:
            st.warning("검색 결과가 없어요. 키워드를 영문으로 입력해보세요.")
        else:
            st.success(f"✅ 총 **{total_refs}개** 수집 완료")

            for label, refs in sections.items():
                show_preview(label, refs)

            if NOTION_TOKEN:
                with st.spinner("Notion에 저장 중..."):
                    notion_url, error = save_to_notion(keywords, sections)
                if notion_url:
                    st.link_button("📖 Notion에서 보기", notion_url, use_container_width=True)
                else:
                    st.error(f"Notion 저장 실패: {error}")
