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
    "Accept-Language": "en-US,en;q=0.9",
}

st.set_page_config(page_title="Design Reference Collector", page_icon="🎨", layout="wide")
st.title("🎨 Design Reference Collector")
st.divider()

keyword_input = st.text_input(
    "컨셉 키워드",
    placeholder="예: DNA graphic, mystery UI  (쉼표로 구분하면 각각 검색)",
)
run = st.button("🔍 레퍼런스 수집하기", type="primary", use_container_width=True)


# ─── Bing 검색 ───────────────────────────────────────────────────────────────

def bing_search(query, count=20):
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
                turl  = m.get("turl", "")   # Bing CDN 썸네일 (항상 로드됨)
                murl  = m.get("murl", "")   # 원본 이미지
                purl  = m.get("purl", "")   # 출처 페이지
                title = m.get("t", "").strip()
                if turl and purl and murl not in seen:
                    seen.add(murl)
                    domain = purl.split("//")[-1].split("/")[0].replace("www.", "").replace("kr.", "").replace("in.", "")
                    results.append({"title": title, "url": purl, "thumb": turl, "image_url": murl, "source": domain})
                    if len(results) >= count:
                        break
            except Exception:
                continue
        return results
    except Exception as e:
        st.warning(f"검색 오류: {e}")
        return []


# ─── 미리보기 ─────────────────────────────────────────────────────────────────

def show_grid(refs):
    cols = st.columns(4)
    for i, ref in enumerate(refs):
        with cols[i % 4]:
            st.image(ref["thumb"], use_container_width=True)
            st.caption(f"[{ref['title'][:35] or ref['source']}]({ref['url']})")


# ─── Notion 저장 ─────────────────────────────────────────────────────────────

def notion_headers():
    return {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": NOTION_VERSION}


def save_to_notion(keywords, all_refs):
    timestamp = datetime.now().strftime("%Y.%m.%d %H:%M")
    title = " + ".join(keywords[:5])

    blocks = [
        {"object": "block", "type": "callout", "callout": {
            "rich_text": [{"type": "text", "text": {"content": f"🎨  {' / '.join(keywords)}"}, "annotations": {"bold": True}}],
            "icon": {"type": "emoji", "emoji": "🎨"}, "color": "pink_background"}},
        {"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": f"수집일: {timestamp}  |  {len(all_refs)}개"}, "annotations": {"color": "gray"}}]}},
        {"object": "block", "type": "divider", "divider": {}},
    ]

    for ref in all_refs:
        # Notion에는 원본 이미지 URL 사용
        if ref.get("image_url", "").startswith("http"):
            blocks.append({"object": "block", "type": "image",
                "image": {"type": "external", "external": {"url": ref["image_url"]}}})
        blocks.append({"object": "block", "type": "bookmark", "bookmark": {"url": ref["url"]}})

    data = {
        "parent": {"page_id": PAGE_ID},
        "icon": {"type": "emoji", "emoji": "🔍"},
        "properties": {"title": {"title": [{"text": {"content": f"[{timestamp[:5]}] {title}"}}]}},
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
        groups = [g.strip() for g in keyword_input.split(",") if g.strip()]
        keywords = keyword_input.replace(",", " ").split()

        all_refs = []
        seen_imgs = set()
        per_group = max(10, 20 // len(groups))

        progress = st.progress(0)
        for i, group in enumerate(groups):
            # Pinterest UI 위주로 검색
            query = f"{group} UI design pinterest dribbble 2023 2024 2025"
            refs = bing_search(query, count=per_group)
            for ref in refs:
                if ref["image_url"] not in seen_imgs:
                    seen_imgs.add(ref["image_url"])
                    all_refs.append(ref)
            progress.progress((i + 1) / len(groups))

        progress.empty()

        if not all_refs:
            st.warning("결과가 없어요. 영문 키워드로 입력해보세요.")
        else:
            st.success(f"✅ **{len(all_refs)}개** 수집 완료")
            show_grid(all_refs)

            if NOTION_TOKEN:
                with st.spinner("Notion 저장 중..."):
                    url, err = save_to_notion(keywords, all_refs)
                if url:
                    st.link_button("📖 Notion에서 보기", url, use_container_width=True)
                else:
                    st.error(f"Notion 저장 실패: {err}")
