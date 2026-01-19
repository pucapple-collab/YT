import streamlit as st
from googleapiclient.discovery import build
from googletrans import Translator
import re
from collections import Counter
from datetime import datetime, timedelta
import statistics
import random
import time

# --- [설정] API 키 관리 ---
API_KEYS = [
    "AIzaSyAZeKYF34snfhN1UY3EZAHMmv_IcVvKhAc", 
    "AIzaSyBNMVMMfFI5b7GNEXjoEuOLdX_zQ8XjsCc"
]

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

st.set_page_config(page_title="Team SENA: Trend Intelligence", layout="wide")

if 'key_index' not in st.session_state:
    st.session_state.key_index = 0

# --- CSS 디자인 ---
st.markdown("""
<style>
.video-card { background-color: #ffffff; padding: 18px; border-radius: 12px; border: 1px solid #e0e0e0; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); display: flex; flex-direction: column; height: 100%; }
.thumb-link img { transition: transform 0.2s; border-radius: 8px; width: 100%; aspect-ratio: 16/9; object-fit: cover; }
.v-title { font-size: 0.95rem; font-weight: 800; color: #111; line-height: 1.4; max-height: 2.8em; overflow: hidden; margin: 10px 0 5px 0; }
.v-meta { font-size: 0.82rem; color: #555; margin-bottom: 5px; line-height: 1.4; padding-bottom: 5px; border-bottom: 1px dashed #eee; }
.v-status { display: inline-block; padding: 3px 7px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; margin-bottom: 5px; }
.status-hot { background-color: #ffebee; color: #c62828; }
.status-steady { background-color: #e3f2fd; color: #1565c0; }
.v-insight-box { background-color: #f8f9fa; padding: 12px; border-radius: 8px; font-size: 0.82rem; border-left: 4px solid #1a73e8; margin-top: 5px; }
.report-container { background-color: #1a1c1e; color: #e1e1e1; padding: 35px; border-radius: 20px; margin-top: 40px; border: 2px solid #ff4b4b; }
.report-header { font-size: 1.7rem; font-weight: 900; color: #ff4b4b; border-bottom: 2px solid #ff4b4b; padding-bottom: 10px; margin-bottom: 25px; }
.section-title { font-size: 1.2rem; font-weight: bold; color: #ffeb3b; margin-top: 25px; margin-bottom: 12px; }
.section-content { background: #25282c; padding: 18px; border-radius: 12px; line-height: 1.8; font-size: 0.95rem; color: #eee; border: 1px solid #333; }
.expert-tip { background-color: #ff4b4b; color: white; padding: 15px; border-radius: 10px; font-weight: bold; margin-top: 30px; text-align: center; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; color: #eee; background: #333; }
th, td { border: 1px solid #444; padding: 10px; text-align: center; }
th { color: #ffeb3b; }
</style>
""", unsafe_allow_html=True)

def show_ad(pos):
    ads = {
        "sidebar": {"img": "https://via.placeholder.com/300x250.png?text=SIDEBAR+AD", "link": "#"},
        "top": {"img": "https://via.placeholder.com/468x60.png?text=TOP+AD", "link": "#"},
        "bottom": {"img": "https://via.placeholder.com/300x250.png?text=REPORT+AD", "link": "#"}
    }
    ad = ads.get(pos)
    st.markdown(f'<div style="text-align:right;"><a href="{ad["link"]}" target="_blank"><img src="{ad["img"]}" style="width:100%; border-radius:8px;"></a></div>', unsafe_allow_html=True)

t_col1, t_col2 = st.columns([3, 1])
with t_col1: st.title("📡 글로벌 트렌드 인텔리전스 (Deep Scan)")
with t_col2: show_ad("top")

translator = Translator()

def get_youtube_client():
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEYS[st.session_state.key_index])

def parse_duration(duration):
    minutes = re.search(r'(\d+)M', duration)
    seconds = re.search(r'(\d+)S', duration)
    total = 0
    if minutes: total += int(minutes.group(1)) * 60
    if seconds: total += int(seconds.group(1))
    return total

def is_japanese(text):
    return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text))

def is_strictly_non_us(title, channel):
    scripts = [re.compile(r'[\u0900-\u097F]+'), re.compile(r'[\u0E00-\u0E7F]+'), re.compile(r'[\u0600-\u06FF]+')]
    combined = title + " " + channel
    if any(s.search(combined) for s in scripts): return True
    blacklist = ['india', 'hindi', 'bollywood', 't-series', 'zeemusic']
    return any(k in combined.lower() for k in blacklist)

def calculate_v_point(views, likes, comments):
    if views == 0: return 0
    return int((views * 0.001) * (1 + (likes/views*10) + (comments/views*50)))

# --- [수정 핵심: 모든 줄의 들여쓰기를 제거한 평탄한 HTML] ---
def generate_sena_report(region_name, video_type, results, keywords):
    if not results: return ""
    avg_views = statistics.mean([v['view_raw'] for v in results])
    avg_viral = statistics.mean([v['v_point'] for v in results])
    top_k = [k for k, c in Counter(keywords).most_common(3)]
    keyword_str = ", ".join(top_k)
    
    # 제작 가능성 분석 로직
    feasibility = "매우 높음. 기획만 나오면 1시간 컷이야." if "Shorts" in video_type else "중간. 스크립트랑 편집에 공 좀 들여야 해."

    # 문자열 앞에 공백이 있으면 안됨 (절대 왼쪽 정렬 필수)
    report_html = f"""
<div class="report-container">
<div class="report-header">🚩 세나 팀장의 현장형 실행 리포트</div>
<div style="font-size: 0.9rem; color: #888; margin-bottom: 20px;">2026 {region_name} {video_type} 시장 | 데이터 기반 의사결정 완료</div>
<div class="section-title">📊 1. [데이터 추출] 핵심 수치 도출</div>
<div class="section-content">
자, 데이터부터 깔끔하게 정리해줄게. 지금 이 바닥에서 '알고리즘 간택' 받으려면 이 정도 숫자는 나와야 해.
<table>
<tr><th>평균 조회수</th><th>평균 Viral Point</th><th>핵심 DNA</th></tr>
<tr><td>{int(avg_views):,}회</td><td>{int(avg_viral):,}점</td><td>{keyword_str}</td></tr>
</table>
특히 Viral Point 튀는 애들은 <b>댓글 반응(인게이지먼트)</b>이 깡패라는 거 잊지 마.
</div>
<div class="section-title">🛠️ 2. [콘텐츠 제작 가능성] 당장 만들 수 있어?</div>
<div class="section-content">
솔직히 말할게. 이 트렌드는 <b>{feasibility}</b><br>
• <b>기술적 난이도:</b> 하(Low). 핵심은 "{top_k[0] if top_k else '트렌드'}" 소재를 얼마나 빨리 선점하느냐야.<br>
• <b>비용 예측:</b> 기존 소스 재가공(Remix)만 잘해도 제작비 0원으로 떡상 가능해.
</div>
<div class="section-title">🗨️ 3. [실제 시청자 반응 예측] 왜 댓글 전쟁터가 됐을까?</div>
<div class="section-content">
시청자들은 지금 <b>"{top_k[0] if top_k else '이 주제'}"</b>에 대해 단순히 보는 게 아니라 <b>'자기 얘기'</b>라고 느껴서 댓글창으로 달려오고 있어.<br>
👉 <b>심리 분석:</b> 상위권 영상들은 전부 <b>'공감'</b> 아니면 <b>'비교'</b>를 건드려. "너는 어때?"라고 묻는 순간 Viral Point 폭발하는 구조야.
</div>
<div class="section-title">🛡️ 4. [보안 검토 및 추천] 리스크는 피하고 우위는 점하자</div>
<div class="section-content">
• <b>보안/저작권:</b> 관련 해외 소스 쓸 때 출처 꼭 박고, 우리만의 독자적인 자막 디자인으로 경쟁사랑 차별화해.<br>
• <b>우위 전략:</b> 뻔한 정보 전달 말고, <b>고정 댓글로 논쟁</b> 하나만 던져봐. 그게 알고리즘 태우는 가장 빠른 지름길이야.
</div>
<div class="section-title">📝 5. [6하원칙 기획안] 내일 당장 찍어!</div>
<div class="section-content">
• <b>Who:</b> {region_name} 내 MZ/알파 타겟군<br>
• <b>When:</b> 알고리즘 피크 타임(주말 저녁) 업로드<br>
• <b>Where:</b> 세로형 9:16 최적화 숏폼 피드<br>
• <b>What:</b> '{top_k[0] if top_k else '트렌드'}' 주제의 반전 결과 혹은 순위 매기기<br>
• <b>How:</b> 첫 1초에 "절대 모르는 사실" 같은 후킹 자막 필수로 박기<br>
• <b>Why:</b> 현재 수집 데이터 중 성공 확률이 가장 높은 포맷임
</div>
<div class="expert-tip">💡 10년 차 세나 팀장의 한 줄 팁: "조회수는 알고리즘이 주고, 바이럴은 댓글이 만든다. 시청자 손가락을 움직이게 만들어!"</div>
</div>
"""
    return report_html

def fetch_videos(topic_text, v_type, r_info, v_count):
    youtube = get_youtube_client()
    is_shorts = "Shorts" in v_type
    is_popular_mode = not topic_text.strip()
    collected = []
    next_token = None
    for _ in range(8):
        try:
            if not is_popular_mode:
                try: trans_q = translator.translate(topic_text, dest=r_info['lang']).text
                except: trans_q = topic_text
                req = youtube.search().list(part="snippet", q=f"{trans_q} {'#shorts' if is_shorts else ''}", type="video", videoDuration="short" if is_shorts else "any", regionCode=r_info['code'], relevanceLanguage=r_info['lang'], order="viewCount", maxResults=50, pageToken=next_token)
            else:
                if is_shorts:
                    country_q = {"KR": "쇼츠", "US": "Shorts", "JP": "ショート"}
                    req = youtube.search().list(part="snippet", q=f"#shorts {country_q.get(r_info['code'], '')}", type="video", videoDuration="short", regionCode=r_info['code'], relevanceLanguage=r_info['lang'], order="viewCount", maxResults=50, pageToken=next_token)
                else:
                    req = youtube.videos().list(part="snippet,statistics", chart="mostPopular", regionCode=r_info['code'], maxResults=50, pageToken=next_token)
            res = req.execute()
            collected.extend(res.get('items', []))
            next_token = res.get('nextPageToken')
            if not next_token or len(collected) >= 400: break
        except Exception as e:
            if "quotaExceeded" in str(e): raise e
            break

    v_ids = []
    for i in collected:
        if 'id' in i:
            vid = i['id']['videoId'] if isinstance(i['id'], dict) and 'videoId' in i['id'] else i['id']
            v_ids.append(vid)

    if not v_ids: return [], 0, ""

    all_stats = []
    for i in range(0, len(v_ids), 50):
        chunk = v_ids[i:i+50]
        stats = youtube.videos().list(part="snippet,statistics,contentDetails", id=",".join(chunk)).execute()
        all_stats.extend(stats.get('items', []))

    results, kws, now = [], [], datetime.now()
    non_us_count, max_non_us = 0, int(v_count * 0.1)

    for i in all_stats:
        t, c = i['snippet']['title'], i['snippet']['channelTitle']
        d_sec = parse_duration(i['contentDetails']['duration'])
        p_date = datetime.strptime(i['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
        days = (now - p_date).days
        if days > 365 or (not is_shorts and d_sec < 120) or (is_shorts and d_sec > 120): continue
        if r_info['code'] == 'JP' and not is_japanese(t + c): continue
        if r_info['code'] == 'US' and is_strictly_non_us(t, c):
            if non_us_count >= max_non_us: continue
            non_us_count += 1
        v = int(i['statistics'].get('viewCount', 0))
        l = int(i['statistics'].get('likeCount', 0)) if 'likeCount' in i['statistics'] else 0
        cm = int(i['statistics'].get('commentCount', 0)) if 'commentCount' in i['statistics'] else 0
        if days > 30 and (v < 500000 or (l+cm)/v < 0.02): continue
        vp = calculate_v_point(v, l, cm)
        tier = 1 if days <= 10 else (2 if days <= 30 else 3)
        kws.extend([w for w in re.sub(r'[^\w\s]', '', t).split() if len(w) > 1])
        results.append({
            'title': t, 'thumbnail': i['snippet']['thumbnails']['high']['url'],
            'url': f"https://www.youtube.com/shorts/{i['id']}" if is_shorts else f"https://www.youtube.com/watch?v={i['id']}",
            'channel': c, 'view_count': v, 'date': i['snippet']['publishedAt'][:10],
            'v_point': vp, 'status': "🔥 초신성" if tier==1 else "🔄 스테디", 'tier': tier, 'view_raw': v
        })

    results.sort(key=lambda x: (x['tier'], -x['v_point']))
    final = results[:v_count]
    report = generate_sena_report(region_name, "Shorts" if is_shorts else "Long-form", final, kws)
    return final, (len(final)/v_count)*100 if v_count > 0 else 0, report

# --- 사이드바 및 실행 ---
st.sidebar.header("📊 마케팅 분석 설정")
region_map = {"한국 🇰🇷": {"code": "KR", "lang": "ko"}, "미국 🇺🇸": {"code": "US", "lang": "en"}, "일본 🇯🇵": {"code": "JP", "lang": "ja"} }
region_name = st.sidebar.selectbox("📍 타겟 시장", list(region_map.keys()))
sel_region = region_map[region_name]
video_type = st.sidebar.radio("📱 콘텐츠 포맷", ["롱폼 (2분 이상)", "숏폼 (Shorts)"])
count = st.sidebar.slider("🔢 분석 샘플", 1, 30, 8)
topic = st.sidebar.text_input("🔍 키워드/주제", placeholder="공란: 국가별 트렌드 수집")
search_clicked = st.sidebar.button("🚀 인사이트 분석 시작", use_container_width=True)

if search_clicked or not topic:
    with st.spinner('세나 팀장이 데이터를 딥 스캔하는 중...'):
        try:
            final_res, acc, report = fetch_videos(topic, video_type, sel_region, count)
            st.subheader(f"📝 {region_name} {video_type} 분석 결과")
            if not final_res: st.warning("데이터를 확보하지 못했습니다.")
            else:
                grid = st.columns(4)
                for idx, v in enumerate(final_res):
                    with grid[idx % 4]:
                        s_class = "status-hot" if v['tier'] == 1 else "status-steady"
                        st.markdown(f"""
                        <div class="video-card">
                            <a href="{v['url']}" target="_blank" class="thumb-link"><img src="{v['thumbnail']}"></a>
                            <div style="margin-top:10px;"><span class="v-status {s_class}">{v['status']}</span></div>
                            <div class="v-title">{v['title']}</div>
                            <div class="v-meta"><b>{v['channel']}</b><br>조회수: {v['view_count']:,}회<br>공개일: {v['date']}</div>
                            <div class="v-insight-box">🌐 <b>Viral Point:</b> <span style="color:#1a73e8; font-weight:800;">{v['v_point']:,}</span></div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # 정제된 HTML 리포트 출력
                st.markdown(report, unsafe_allow_html=True)
                
                c1, c2 = st.columns([3, 1]); with c2: show_ad("bottom")
        except Exception as e:
            if "quotaExceeded" in str(e):
                if st.session_state.key_index < len(API_KEYS) - 1:
                    st.session_state.key_index += 1
                    st.toast("🔄 키 소진! 자동 전환 중...")
                    time.sleep(1); st.rerun()
                else: st.error("🚨 모든 할당량 소진.")
            else: st.error(f"오류 발생: {e}")
