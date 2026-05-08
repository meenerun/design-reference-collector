import streamlit as st
import os, time, requests
from datetime import datetime

try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
except Exception:
    NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")

PAGE_ID = "35a06261920e80e0b6c5d27d07c5c116"
NOTION_VERSION = "2022-06-28"

# ─── 검색 대상 사이트 정의 ────────────────────────────────────────────────────
DESIGN_SITES = (
    "site:cssdesignawards.com OR site:awwwards.com OR site:godly.website "
    "OR site:httpster.net OR site:unsection.com OR site:interfaceingame.com "
    "OR site:brutalistwebsites.com OR site:hoverstat.es"
)

PINTEREST_SITE = "site:pinterest.com OR site:kr.pinterest.com"

# ─── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Design Reference Collector", page_icon="🎨", layout="centered")
st.title("🎨 Design Reference Collector")
st.caption("키워드를 입력하면 관련 디자인 레퍼런스를 수집해 Notion에 저장합니다.")
st.divider()

# ─── 입력 UI ──────────────────────────────────────────────────────────────────
keyword_input = st.text_input(
    "컨셉 키워드",
    placeholder="예: pink gradient chemistry DNA mystery UI",
    help="스페이스로 구분해서 입력하세요",
)

col1, col2 = st.columns(2)
with col1:
    use_design = st.checkbox("🌐 디자인 사이트", value=True,
                              help="cssdesignawards, awwwards, godly, httpster 등")
with col2:
    use_pinterest = st.checkbox("📌 Pinterest", value=True)

run = st.button("🔍 레퍼런스 수집하기", type="primary", use_container_width=True)


# ─── DuckDuckGo 검색 ──────────────────────────────────────────────────────────

def ddg_search(query, max_results=15):
    try:
        from ddgs import DDGS
        results = list(DDGS().images(query, max_results=max_results))
        return results
    except Exception as e:
        st.warning(f"검색 오류: {e}")
        return []


def search_design_sites(keywords):
    query = f"{' '.join(keywords)} web design UI {DESIGN_SITES}"
    results = ddg_search(query, max_results=15)
    refs = []
    seen = set()
    for r in results:
        url = r.get("url", "") or r.get("source", "")
        if not url or url in seen:
            continue
        seen.add(url)
        refs.append({
            "source": extract_domain(url),
            "title": r.get("title", url)[:80],
            "url": url,
            "image_url": r.get("image", ""),
        })
    return refs


def search_pinterest(keywords):
    query = f"{' '.join(keywords)} design inspiration {PINTEREST_SITE}"
    results = ddg_search(query, max_results=10)
    refs = []
    seen = set()
    for r in results:
        url = r.get("url", "") or r.get("source", "")
        if not url or url in seen:
            continue
        seen.add(url)
        refs.append({
            "source": "pinterest.com",
            "title": r.get("title", url)[:80],
            "url": url,
            "image_url": r.get("image", ""),
        })
    return refs


def extract_domain(url):
    try:
        return url.split("//")[-1].split("/")[0].replace("www.", "").replace("kr.", "")
    except Exception:
        return url


# ─── Notion ───────────────────────────────────────────────────────────────────

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
            "paragraph": {"rich_text": [{"type": "text", "text": {
                "content": f"수집일: {timestamp}  |  레퍼런스 {len(all_refs)}개"
            }, "annotations": {"color": "gray"}}]}
        },
        {"object": "block", "type": "divider", "divider": {}},
    ]

    site_emojis = {
        "pinterest.com": "📌",
        "awwwards.com": "🏆",
        "cssdesignawards.com": "🎖",
        "godly.website": "✨",
        "httpster.net": "🌐",
        "unsection.com": "🖼",
        "interfaceingame.com": "🎮",
        "brutalistwebsites.com": "🧱",
        "hoverstat.es": "👁",
    }

    sources = {}
    for ref in all_refs:
        sources.setdefault(ref["source"], []).append(ref)

    for source, refs in sources.items():
        emoji = site_emojis.get(source, "📎")
        blocks.append({
            "object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": f"{emoji}  {source}"}}]}
        })
        for ref in refs:
            if ref.get("image_url") and ref["image_url"].startswith("http"):
                blocks.append({
                    "object": "block", "type": "image",
                    "image": {"type": "external", "external": {"url": ref["image_url"]}}
                })
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
        requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=notion_headers(), json={"children": batch}
        )
        time.sleep(0.3)

    return page.get("url", ""), None


# ─── 실행 ─────────────────────────────────────────────────────────────────────

if run:
    if not keyword_input.strip():
        st.error("키워드를 입력해주세요.")
    elif not NOTION_TOKEN:
        st.error("NOTION_TOKEN이 설정되지 않았습니다.")
    elif not use_design and not use_pinterest:
        st.error("최소 하나의 사이트를 선택해주세요.")
    else:
        keywords = [k.strip() for k in keyword_input.split() if k.strip()]
        st.info(f"🔍 **{', '.join(keywords)}** 키워드로 검색 시작...")

        all_refs = []
        total = sum([use_design, use_pinterest])
        done = 0
        progress = st.progress(0)
        status = st.empty()

        if use_design:
            status.text("🌐 디자인 사이트 검색 중...")
            refs = search_design_sites(keywords)
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)
            st.write(f"✅ 디자인 사이트 — {len(refs)}개")

        if use_pinterest:
            status.text("📌 Pinterest 검색 중...")
            refs = search_pinterest(keywords)
            all_refs.extend(refs)
            done += 1
            progress.progress(done / total)
            st.write(f"✅ Pinterest — {len(refs)}개")

        if not all_refs:
            st.warning("검색 결과가 없습니다. 키워드를 바꿔서 다시 시도해보세요.")
        else:
            status.text("📝 Notion 페이지 생성 중...")
            notion_url, error = create_notion_page(keywords, all_refs)

            if notion_url:
                status.empty()
                progress.empty()
                st.success(f"🎉 완료! **{len(all_refs)}개** 레퍼런스가 Notion에 저장됐습니다.")
                st.link_button("📖 Notion에서 보기", notion_url, use_container_width=True)
            else:
                st.error(f"Notion 페이지 생성 실패: {error}")
