import streamlit as st
from googleapiclient.discovery import build
from googletrans import Translator
import re
from collections import Counter
from datetime import datetime, timedelta
import statistics
import random
import time
import streamlit.components.v1 as components

# --- [설정] 관리 및 API 키 ---
MASTER_ACCESS_KEY = "CLOUD-ENT-VIP" 
API_KEYS = [
    "AIzaSyCS0ITaVrJ4D8bbYS8zxWpLIN7h5qpz47Q",
    "AIzaSyDOm5iXZPgVVQiD9UrrhGrW_X1goigl0eU",
    "AIzaSyCANj0BHbejmyaxFR7TLbOggOeykQe3-a8",
    "AIzaSyAovyzahHB-Bw2oZ4x4eXblIzws_3mXKL0",
    "AIzaSyAN_J7dDXuThijWabzxEZXnjjXSvNMO2hw"
]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

st.set_page_config(page_title="Team SENA: Trend Intelligence", layout="wide")

if 'key_index' not in st.session_state:
    st.session_state.key_index = 0

# --- CSS 디자인 ---
st.markdown("""
<style>
    .video-card { 
        background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #eef0f2; 
        margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
        display: flex; flex-direction: column; min-width: 260px; height: 100%;
    }
    .thumb-link img { border-radius: 8px; width: 100%; aspect-ratio: 16/9; object-fit: cover; }
    .thumb-link img:hover { transform: scale(1.02); transition: 0.2s; }
    .v-title { font-size: 0.95rem; font-weight: 800; color: #111; line-height: 1.4; height: 2.8em; overflow: hidden; margin: 10px 0 5px 0; }
    .v-meta { font-size: 0.8rem; color: #555; margin-bottom: 8px; line-height: 1.5; border-bottom: 1px dashed #eee; padding-bottom: 8px; }
    .v-status { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; margin-bottom: 10px; }
    .status-hot { background-color: #ffebee; color: #c62828; }
    .status-steady { background-color: #e3f2fd; color: #1565c0; }
    .v-insight-box { background-color: #f0f7ff; padding: 12px; border-radius: 8px; font-size: 0.82rem; border-left: 5px solid #1a73e8; margin-top: auto; }
    .stat-val { color: #1a73e8; font-weight: 800; font-size: 1.1rem; }
    .report-container { background-color: #1a1c1e; color: #e1e1e1; padding: 30px; border-radius: 20px; margin-top: 40px; border: 2px solid #ff4b4b; }
</style>
""", unsafe_allow_html=True)

translator = Translator()

def get_youtube_client(custom_key=None):
    selected_key = custom_key if custom_key else API_KEYS[st.session_state.key_index]
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=selected_key)

def parse_duration(duration):
    minutes = re.search(r'(\d+)M', duration)
    seconds = re.search(r'(\d+)S', duration)
    total = 0
    if minutes: total += int(minutes.group(1)) * 60
    if seconds: total += int(seconds.group(1))
    return total

def has_korean(text): return bool(re.search(r'[가-힣]', text))
def has_japanese(text): return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text))

# --- [수정] 미국 시장용 초정밀 필터 (글로벌 K-POP 레이블 추가) ---
def is_strictly_non_us(title, channel):
    # 힌두어/아시아 문자 감지
    if bool(re.search(r'[\u0900-\u097F\u0E00-\u0E7F\u0600-\u06FF]', title + channel)): return True
    # 미국 차트 점령하는 글로벌 아시아 채널 블랙리스트
    blacklist = [
        't-series', 'set india', 'zee music', 'sony pal', 'colors tv', 'goldmines',
        'hybe', 'jyp', 'smtown', 'starship', 'yg entertainment', 'mnet', 'kbs world'
    ]
    combined = (title + channel).lower()
    return any(k in combined for k in blacklist)

def calculate_v_point(views, likes, comments):
    if views == 0: return 0
    return int((views * 0.001) * (1 + (likes/views*10) + (comments/views*50)))

def generate_sena_report(region_name, video_type, results, keywords):
    if not results: return ""
    avg_views = statistics.mean([v['view_raw'] for v in results])
    avg_viral = statistics.mean([v['v_point'] for v in results])
    top_k = [k for k, c in Counter(keywords).most_common(3)]
    k_str = ", ".join(top_k)
    return f"""
<div class="report-container">
<div style="font-size: 1.7rem; font-weight: 900; color: #ff4b4b; border-bottom: 2px solid #ff4b4b; padding-bottom: 10px; margin-bottom: 25px;">리포트</div>
<div style="font-size: 0.9rem; color: #888; margin-bottom: 20px;">2026 {region_name} {video_type} 시장 | 글로벌 중복 데이터 제거 완료</div>
<div style="font-size: 1.2rem; font-weight: bold; color: #ffeb3b; margin-top: 25px; margin-bottom: 12px;">📊 1. [데이터 추출] 핵심 지표 요약</div>
<div style="background: #25282c; padding: 18px; border-radius: 12px; line-height: 1.8; font-size: 0.95rem; color: #eee; border: 1px solid #333;">
데이터 까보자. 이번 {region_name} 차트에서 겹치는 글로벌 노이즈는 다 걷어냈어. 순수 현지 반응 지표야.
<table><tr><th>평균 조회수</th><th>평균 Viral Point</th><th>핵심 DNA</th></tr>
<tr><td>{int(avg_views):,}회</td><td>{int(avg_viral):,}점</td><td>{k_str}</td></tr></table>
</div>
<div style="font-size: 1.2rem; font-weight: bold; color: #ffeb3b; margin-top: 25px; margin-bottom: 12px;">🗨️ 2. [시청자 반응 예측] 심리 분석</div>
<div style="background: #25282c; padding: 18px; border-radius: 12px; line-height: 1.8; font-size: 0.95rem; color: #eee; border: 1px solid #333;">
현재 {region_name} 유저들은 <b>"{top_k[0] if top_k else '이 주제'}"</b>에 대해 매우 능동적이야. 특히 단순히 보는 걸 넘어 댓글로 본인 의견을 피력하는 비중이 높은 영상들이 Viral Point를 독점하고 있어.
</div>
</div>"""

def fetch_videos(api_key, topic_text, v_type, r_info, v_count):
    youtube = get_youtube_client(api_key)
    is_shorts = "Shorts" in v_type
    is_popular_mode = not topic_text.strip()
    
    # [핵심] 한국 상위권을 미리 가져와서 중복 리스트 생성
    kr_top_ids = []
    if r_info['code'] == 'US': # 미국 검색 시에만 작동
        try:
            kr_req = youtube.videos().list(part="id", chart="mostPopular", regionCode="KR", maxResults=20).execute()
            kr_top_ids = [item['id'] for item in kr_req.get('items', [])]
        except: pass

    collected, next_token = [], None
    scan_limit = 10 if is_shorts else 5
    for _ in range(scan_limit):
        try:
            if not is_popular_mode:
                try: trans_q = translator.translate(topic_text, dest=r_info['lang']).text
                except: trans_q = topic_text
                req = youtube.search().list(part="snippet", q=f"{trans_q} {'#shorts' if is_shorts else ''}", type="video", videoDuration="short" if is_shorts else "any", regionCode=r_info['code'], relevanceLanguage=r_info['lang'], order="viewCount", maxResults=50, pageToken=next_token)
            else:
                if is_shorts:
                    if r_info['code'] == 'KR': country_q = "#shorts #쇼츠"
                    elif r_info['code'] == 'JP': country_q = "#shorts #日本人"
                    else: country_q = "#shorts"
                    req = youtube.search().list(part="snippet", q=country_q, type="video", videoDuration="short", regionCode=r_info['code'], relevanceLanguage=r_info['lang'], order="viewCount", maxResults=50, pageToken=next_token)
                else:
                    req = youtube.videos().list(part="snippet,statistics", chart="mostPopular", regionCode=r_info['code'], maxResults=50, pageToken=next_token)
            
            res = req.execute()
            collected.extend(res.get('items', []))
            next_token = res.get('nextPageToken')
            if not next_token or len(collected) >= 400: break
        except Exception: break

    v_ids = [i['id']['videoId'] if isinstance(i['id'], dict) else i['id'] for i in collected]
    if not v_ids: return [], 0, ""

    all_stats = []
    for i in range(0, len(v_ids), 50):
        chunk = v_ids[i:i+50]
        stats = youtube.videos().list(part="snippet,statistics,contentDetails", id=",".join(chunk)).execute()
        all_stats.extend(stats.get('items', []))

    results, kws, now = [], [], datetime.now()
    for i in all_stats:
        t, c, vid = i['snippet']['title'], i['snippet']['channelTitle'], i['id']
        d_sec = parse_duration(i['contentDetails']['duration'])
        p_date = datetime.strptime(i['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
        days = (now - p_date).days
        
        # [조건 필터링]
        if days > 365 or (not is_shorts and d_sec < 120) or (is_shorts and d_sec > 120): continue
        
        # [중요] 한국 차트와 겹치는 영상 미국 리스트에서 제외 (K-POP 중복 제거)
        if r_info['code'] == 'US' and vid in kr_top_ids: continue

        if r_info['code'] == 'KR' and not has_korean(t+c): continue
        if r_info['code'] == 'JP' and not has_japanese(t+c): continue
        if r_info['code'] == 'US' and is_strictly_non_us(t, c): continue

        v = int(i['statistics'].get('viewCount', 0))
        l = int(i['statistics'].get('likeCount', 0)) if 'likeCount' in i['statistics'] else 0
        cm = int(i['statistics'].get('commentCount', 0)) if 'commentCount' in i['statistics'] else 0
        if days > 30 and (v < 300000 or (l+cm)/v < 0.015): continue

        vp = calculate_v_point(v, l, cm)
        tier = 1 if days <= 10 else (2 if days <= 30 else 3)
        kws.extend([w for w in re.sub(r'[^\w\s]', '', t).split() if len(w) > 1])
        results.append({'title': t, 'thumbnail': i['snippet']['thumbnails']['high']['url'], 'url': f"https://www.youtube.com/shorts/{i['id']}" if is_shorts else f"https://www.youtube.com/watch?v={i['id']}", 'channel': c, 'view_count': v, 'date': i['snippet']['publishedAt'][:10], 'v_point': vp, 'status': "🔥 초신성" if tier==1 else "🔄 스테디", 'tier': tier, 'view_raw': v})

    results.sort(key=lambda x: (x['tier'], -x['v_point']))
    final = results[:v_count]
    report = generate_sena_report(region_name, "Shorts" if is_shorts else "Long-form", final, kws)
    return final, (len(final)/v_count)*100 if v_count > 0 else 0, report

# --- UI 레이아웃 ---
components.html("<div style='background:#f1f3f4; height:90px; line-height:90px; text-align:center; color:#999; border:1px solid #ddd; border-radius:5px;'>TOP AD UNIT</div>", height=90)
st.title("📡 글로벌 트렌드")

st.sidebar.header("📊 분석 설정")
region_map = {"한국 🇰🇷": {"code": "KR", "lang": "ko"}, "미국 🇺🇸": {"code": "US", "lang": "en"}, "일본 🇯🇵": {"code": "JP", "lang": "ja"} }
region_name = st.sidebar.selectbox("📍 타겟 시장", list(region_map.keys()))
sel_region = region_map[region_name]
video_type = st.sidebar.radio("📱 콘텐츠 포맷", ["롱폼 (2분 이상)", "숏폼 (Shorts)"])
count = st.sidebar.slider("🔢 분석 샘플", 1, 30, 1)
topic = st.sidebar.text_input("🔍 분석 키워드", placeholder="공란: 실시간 인기 수집")
search_clicked = st.sidebar.button("🚀 분석 시작", use_container_width=True)

with st.sidebar.expander("⚙️ 할당량 소진 시 본인 키 사용"):
    personal_key = st.text_input("개인 API Key 입력", type="password")
access_key = st.sidebar.text_input("🔑 VIP 액세스 키", type="password")

st.sidebar.markdown("---")
with st.sidebar:
    st.write("📢 Sponsored")
    components.html("<div style='background:#f1f3f4; height:600px; line-height:600px; text-align:center; color:#999; border:1px solid #ddd; border-radius:10px;'>VERTICAL AD</div>", height=600)

if search_clicked or not topic.strip():
    access_granted = True
    if topic.strip() and access_key != MASTER_ACCESS_KEY:
        access_granted = False
        st.sidebar.error("❌ VIP 키가 필요합니다.")
    
    if access_granted:
        with st.spinner('데이터를 딥 스캔하는 중...'):
            try:
                final_res, acc, report = fetch_videos(personal_key if personal_key else None, topic, video_type, sel_region, count)
                if final_res:
                    st.subheader(f"📝 {region_name} {video_type} 분석 결과")
                    grid = st.columns(4)
                    for idx, v in enumerate(final_res):
                        with grid[idx % 4]:
                            s_class = "status-hot" if v['tier'] == 1 else "status-steady"
                            st.markdown(f"""
                            <div class="video-card">
                                <a href="{v['url']}" target="_blank" class="thumb-link"><img src="{v['thumbnail']}"></a>
                                <div style="margin-top:10px;"><span class="v-status {s_class}">{v['status']}</span></div>
                                <div class="v-title">{v['title']}</div>
                                <div class="v-meta">
                                    <b>{v['channel']}</b><br>
                                    조회수: {v['view_count']:,}회<br>
                                    공개일: {v['date']}
                                </div>
                                <div class="v-insight-box">
                                    🌐 <b>Viral Point:</b> <span style="color:#1a73e8; font-weight:800; font-size:1.1rem;">{v['v_point']:,}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    st.markdown(report, unsafe_allow_html=True)
                    st.markdown("---")
                    bc1, bc2 = st.columns([3, 1])
                    with bc2: components.html("<div style='background:#f1f3f4; height:250px; line-height:250px; text-align:center; color:#999; border:1px solid #ddd; border-radius:10px;'>BOTTOM AD</div>", height=250)
            except Exception as e:
                if "quotaExceeded" in str(e):
                    if not personal_key and st.session_state.key_index < len(API_KEYS) - 1:
                        st.session_state.key_index += 1
                        time.sleep(1); st.rerun()
                    else: st.error("🚨 모든 할당량 소진.")
                else: st.error(f"오류: {e}")
