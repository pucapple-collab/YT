import streamlit as st
from googleapiclient.discovery import build
from googletrans import Translator
import re
from collections import Counter
from datetime import datetime, timedelta
import statistics
import random
import time

# --- [설정] API 키 관리 (자동 전환 시스템) ---
API_KEYS = [
    "AIzaSyAZeKYF34snfhN1UY3EZAHMmv_IcVvKhAc", 
    "AIzaSyBNMVMMfFI5b7GNEXjoEuOLdX_zQ8XjsCc"
]

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

st.set_page_config(page_title="Trend Lead SENA", layout="wide")

if 'key_index' not in st.session_state:
    st.session_state.key_index = 0

# --- CSS 디자인 (프레임 최적화 및 세나 리포트 스타일) ---
st.markdown("""
<style>
    .video-card { 
        background-color: #ffffff; padding: 18px; border-radius: 12px; border: 1px solid #e0e0e0; 
        margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); min-height: 600px; 
        display: flex; flex-direction: column; 
    }
    .thumb-link img { transition: transform 0.2s; border-radius: 8px; width: 100%; aspect-ratio: 16/9; object-fit: cover; }
    .thumb-link img:hover { transform: scale(1.02); }
    .v-title { font-size: 0.95rem; font-weight: 800; color: #111; line-height: 1.4; max-height: 2.8em; overflow: hidden; margin: 10px 0 5px 0; }
    .v-meta { font-size: 0.82rem; color: #555; margin-bottom: 5px; line-height: 1.4; padding-bottom: 5px; border-bottom: 1px dashed #eee; }
    .v-status { display: inline-block; padding: 3px 7px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; margin-bottom: 5px; }
    .status-hot { background-color: #ffebee; color: #c62828; }
    .status-steady { background-color: #e3f2fd; color: #1565c0; }
    .v-insight-box { background-color: #f8f9fa; padding: 12px; border-radius: 8px; font-size: 0.82rem; border-left: 4px solid #1a73e8; margin-top: 5px; }
    
    /* 세나 팀장 리포트 컨테이너 */
    .report-container { background-color: #1a1c1e; color: #e1e1e1; padding: 35px; border-radius: 20px; margin-top: 50px; border: 1px solid #333; }
    .report-header { font-size: 1.7rem; font-weight: 900; color: #ffeb3b; border-bottom: 2px solid #ffeb3b; padding-bottom: 10px; margin-bottom: 25px; }
    .report-sub { font-size: 1rem; color: #aaa; margin-bottom: 20px; }
    .section-title { font-size: 1.2rem; font-weight: bold; color: #4dabf7; margin-top: 25px; margin-bottom: 12px; }
    .section-content { background: #25282c; padding: 18px; border-radius: 12px; line-height: 1.8; font-size: 0.95rem; color: #eee; }
    .expert-tip { background-color: #d32f2f; color: white; padding: 15px; border-radius: 10px; font-weight: bold; margin-top: 30px; text-align: center; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; color: #eee; }
    th, td { border: 1px solid #444; padding: 10px; text-align: center; }
    th { background-color: #333; color: #ffeb3b; }
</style>
""", unsafe_allow_html=True)

# --- 광고 함수 ---
def show_ad(pos):
    ads = {
        "sidebar": {"img": "https://via.placeholder.com/300x250.png?text=SIDEBAR+AD+SPACE", "link": "#"},
        "top": {"img": "https://via.placeholder.com/468x60.png?text=TOP+BANNER+AD", "link": "#"},
        "bottom": {"img": "https://via.placeholder.com/300x250.png?text=REPORT+BOTTOM+AD", "link": "#"}
    }
    ad = ads.get(pos)
    st.markdown(f'<div style="text-align:right; margin-bottom:10px;"><a href="{ad["link"]}" target="_blank"><img src="{ad["img"]}" style="width:100%; border-radius:8px; border:1px solid #ddd;"></a><p style="font-size:9px; color:#999; margin:0;">ADVERTISEMENT</p></div>', unsafe_allow_html=True)

# 상단 레이아웃 (광고 포함)
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

# --- [세나 팀장 페르소나 리포트 생성] ---
def generate_sena_report(region_name, video_type, results, keywords):
    if not results: return ""
    avg_views = statistics.mean([v['view_raw'] for v in results])
    avg_viral = statistics.mean([v['v_point'] for v in results])
    top_k = [k for k, c in Counter(keywords).most_common(3)]
    keyword_str = ", ".join(top_k)
    
    html = f"""
    <div class="report-container">
        <div class="report-header">📑 TEAM SENA : 2026 {region_name} 트렌드 분석 리포트</div>
        <div class="report-sub">작성자: 세나 (10년 차 콘텐츠 전략 팀장) | 데이터 기반 의사결정 모드</div>
        
        <div class="section-title">1. [데이터 추출] 핵심 수치 도출</div>
        <div class="section-content">
            자, 데이터부터 깔고 시작하자. 현재 이 시장 씹어먹고 있는 핵심 숫자야.
            <table>
                <tr><th>평균 조회수 (Traffic)</th><th>평균 Viral Point (Engagement)</th><th>핵심 DNA (Keywords)</th></tr>
                <tr><td>{int(avg_views):,}회</td><td>{int(avg_viral):,}점</td><td>{keyword_str}</td></tr>
            </table>
        </div>

        <div class="section-title">2. [SWOT 분석] 현재 시장 판세</div>
        <div class="section-content">
            <ul>
                <li><b>Strength:</b> {int(avg_viral):,}점대의 높은 바이럴 지수로 알고리즘 점유율 최상단 확보.</li>
                <li><b>Weakness:</b> 숏폼 포맷 특성상 3초 내에 시각적 훅(Hook) 없으면 유저들 바로 이탈함.</li>
                <li><b>Opportunity:</b> '{top_k[0] if top_k else '트렌드'}' 소재는 현재 리믹스 및 챌린지 확산 가능성 매우 높음.</li>
                <li><b>Threat:</b> 유사 포맷의 무분별한 복제로 인한 시청자 피로도 급증 주의.</li>
            </ul>
        </div>

        <div class="section-title">3. [시청자 반응 예측] 그들은 왜 보는가?</div>
        <div class="section-content">
            시청자들은 지금 <b>'{top_k[0] if top_k else '이 콘텐츠'}'</b>에 대해 "진짜 대박이다", "이거 나만 그래?" 같은 <b>강한 공감과 경탄</b> 위주로 반응하고 있어. 
            특히 3초 후킹에 성공한 영상들이 Viral Point 상위권을 싹쓸이 중이야. 타겟 팬덤의 결집력이 이 트렌드를 유지시키는 핵심 동력임.
        </div>

        <div class="section-title">4. [실행 전략] 6하원칙 기획안</div>
        <div class="section-content">
            말 길게 안 할게. 내일 당장 이거 찍어와.
            <br>• <b>Who:</b> {region_name} 내 MZ/알파 세대 타겟
            <br>• <b>When:</b> 주말 저녁 알고리즘 피크 타임 타겟 업로드
            <br>• <b>Where:</b> 자극적인 자막과 함께 9:16 세로형 포맷 고수
            <br>• <b>What:</b> '{top_k[0] if top_k else '핵심'}'와 관련된 시각적 반전 요소 배치
            <br>• <b>How:</b> 도입 1초에 결론부터 박고 시작하는 '역순 스토리텔링' 기법 적용
            <br>• <b>Why:</b> 현재 수집된 영상 중 Viral Point 1위가 이 방식을 써서 대박 났거든.
        </div>

        <div class="expert-tip">💡 전문가의 한 줄 팁: "{top_k[0] if top_k else '키워드'}에 목숨 걸어. 제목 맨 앞에 안 박으면 클릭조차 안 일어난다!"</div>
    </div>
    """
    return html

def fetch_videos(topic_text, v_type, r_info, v_count):
    youtube = get_youtube_client()
    is_shorts = "Shorts" in v_type
    is_popular_mode = not topic_text.strip()
    
    collected = []
    next_token = None
    # [딥 스캔] 수량 확보를 위해 최대 400개까지 탐색
    for _ in range(8):
        try:
            if not is_popular_mode:
                try: trans_q = translator.translate(topic_text, dest=r_info['lang']).text
                except: trans_q = topic_text
                req = youtube.search().list(part="snippet", q=f"{trans_q} {'#shorts' if is_shorts else ''}", type="video", videoDuration="short" if is_shorts else "any", regionCode=r_info['code'], relevanceLanguage=r_info['lang'], order="viewCount", maxResults=50, pageToken=next_token)
            else:
                if is_shorts:
                    req = youtube.search().list(part="snippet", q=f"#shorts", type="video", videoDuration="short", regionCode=r_info['code'], relevanceLanguage=r_info['lang'], order="viewCount", maxResults=50, pageToken=next_token)
                else:
                    req = youtube.videos().list(part="snippet,statistics", chart="mostPopular", regionCode=r_info['code'], maxResults=50, pageToken=next_token)
            
            res = req.execute()
            collected.extend(res.get('items', []))
            next_token = res.get('nextPageToken')
            if not next_token or len(collected) >= 400: break
        except Exception as e:
            if "quotaExceeded" in str(e): raise e
            break

    v_ids = [i['id']['videoId'] if 'videoId' in item['id'] else i['id'] for i in collected if 'id' in i]
    # search API와 videos API의 ID 구조가 다를 수 있어 재정의
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
            'v_point': vp, 'tier': tier, 'view_raw': v, 'status': "🔥 초신성" if tier==1 else "🔄 스테디"
        })

    results.sort(key=lambda x: (x['tier'], -x['v_point']))
    final = results[:v_count]
    report = generate_sena_report(region_name, "Shorts" if is_shorts else "Long-form", final, kws)
    return final, (len(final)/v_count)*100 if v_count > 0 else 0, report

# --- 사이드바 ---
st.sidebar.header("📊 마케팅 분석 설정")
region_map = {"한국 🇰🇷": {"code": "KR", "lang": "ko"}, "미국 🇺🇸": {"code": "US", "lang": "en"}, "일본 🇯🇵": {"code": "JP", "lang": "ja"} }
region_name = st.sidebar.selectbox("📍 타겟 시장", list(region_map.keys()))
sel_region = region_map[region_name]
video_type = st.sidebar.radio("📱 콘텐츠 포맷", ["롱폼 (2분 이상)", "숏폼 (Shorts)"])
count = st.sidebar.slider("🔢 분석 샘플", 1, 30, 8)
topic = st.sidebar.text_input("🔍 키워드/주제", placeholder="공란: 국가별 트렌드 수집")
search_clicked = st.sidebar.button("🚀 인사이트 분석 시작", use_container_width=True)

st.sidebar.markdown("---")
with st.sidebar: show_ad("sidebar")

# --- 결과 출력 ---
if search_clicked or not topic:
    with st.spinner('세나 팀장이 데이터를 딥 스캔하는 중... (최대 1분 소요)'):
        try:
            final_res, acc, report = fetch_videos(topic, video_type, sel_region, count)
            st.subheader(f"📝 {region_name} {video_type} 분석 결과")
            if not final_res: st.warning("데이터를 확보하지 못했습니다. 조건을 변경해 보세요.")
            else:
                cols = st.columns(4)
                for idx, v in enumerate(final_res):
                    with cols[idx % 4]:
                        s_class = "status-hot" if v['tier'] == 1 else "status-steady"
                        st.markdown(f"""
                        <div class="video-card">
                            <a href="{v['url']}" target="_blank" class="thumb-link"><img src="{v['thumbnail']}"></a>
                            <div style="margin-top:10px;"><span class="v-status {s_class}">{v['status']}</span></div>
                            <div class="v-title">{v['title']}</div>
                            <div class="v-meta"><b>{v['channel']}</b><br>조회수: {v['view_count']:,}회<br>공개일: {v['date']}</div>
                            <div class="v-insight-box">🌐 <b>Viral Point:</b> <span class="stat-val">{v['v_point']:,}</span></div>
                        </div>
                        """, unsafe_allow_html=True)
                st.markdown(report, unsafe_allow_html=True)
                # [수정] SyntaxError 방지를 위한 코드 분리
                c1, c2 = st.columns([3, 1])
                with c2:
                    show_ad("bottom")
        except Exception as e:
            if "quotaExceeded" in str(e):
                if st.session_state.key_index < len(API_KEYS) - 1:
                    st.session_state.key_index += 1
                    st.toast("🔄 1번 키 소진! 자동 키 전환 중...")
                    time.sleep(1)
                    st.rerun()
                else: st.error("🚨 모든 할당량 소진.")
            else: st.error(f"오류 발생: {e}")
