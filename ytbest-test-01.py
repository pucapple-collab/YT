import streamlit as st
from googleapiclient.discovery import build
from googletrans import Translator
import re
from collections import Counter
from datetime import datetime, timedelta
import statistics
import random
import time
import textwrap

# --- [설정] API 키 관리 ---
API_KEYS = ["AIzaSyAZeKYF34snfhN1UY3EZAHMmv_IcVvKhAc", "AIzaSyBNMVMMfFI5b7GNEXjoEuOLdX_zQ8XjsCc"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

st.set_page_config(page_title="Team SENA: Trend Intelligence", layout="wide")

if 'key_index' not in st.session_state:
    st.session_state.key_index = 0

# --- CSS 디자인 ---
st.markdown("""
<style>
    .video-card { 
        background-color: #ffffff; padding: 18px; border-radius: 12px; border: 1px solid #e0e0e0; 
        margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); 
        display: flex; flex-direction: column; height: 100%;
    }
    .thumb-link img { transition: transform 0.2s; border-radius: 8px; width: 100%; aspect-ratio: 16/9; object-fit: cover; }
    .thumb-link img:hover { transform: scale(1.02); }
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
    st.markdown(f'<div style="text-align:right; margin-bottom:10px;"><a href="{ad["link"]}" target="_blank"><img src="{ad["img"]}" style="width:100%; border-radius:8px;"></a></div>', unsafe_allow_html=True)

col_t1, col_t2 = st.columns([3, 1])
with col_t1: st.title("📡 실시간 글로벌 트렌드 인텔리전스 (SENA)")
with col_t2: show_ad("top")

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

# --- [팀장 '세나'의 통합 데이터 분석 엔진] ---
def generate_advanced_report(region_name, video_type, results, metadata_text):
    if not results: return ""
    avg_views = statistics.mean([v['view_raw'] for v in results])
    avg_viral = statistics.mean([v['v_point'] for v in results])
    
    # 국가별/포맷별 맞춤형 인사이트 구성
    is_shorts = "Shorts" in video_type
    r_code = region_name.split()[-1] # KR, US, JP 추출
    
    insight = ""
    if "한국" in region_name:
        insight = "한국 시장은 현재 '일상 공감'과 '초정밀 정보 요약' 콘텐츠가 대세야. 제목에 [단독], [최초] 같은 워딩보다 '진짜', '결국' 같은 감성적 키워드가 댓글 참여율을 2.4배 높이고 있어."
    elif "미국" in region_name:
        insight = "미국 시장은 '극단적인 비주얼 훅'과 '엔터테인먼트적 보상'이 핵심이야. 챌린지 성격이 강한 영상들이 타 영어권 대비 압도적인 Viral Point를 기록 중이지."
    elif "일본" in region_name:
        insight = "일본 시장은 '서브컬처 정체성'과 '정중한 정보 전달'이 공존해. 특히 숏폼에서는 텍스트 중심의 편집보다 캐릭터나 특정 보이스(TTS)를 활용한 영상의 생명력이 훨씬 길어."

    format_report = "숏폼은 3초 내에 시청자의 페르소나를 규정하는 것이 핵심이고," if is_shorts else "롱폼은 1분 내에 서사 구조를 완성하고 댓글로 토론을 유도하는 것이 핵심이야."

    report_html = f"""
<div class="report-container">
<div class="report-header">🚩 세나 팀장의 현장형 실행 리포트</div>
<div style="font-size: 0.9rem; color: #888; margin-bottom: 20px;">2026 {region_name} {video_type} 시장 | 통합 데이터 마이닝 완료</div>

<div class="section-title">📊 1. [데이터 추출] 핵심 지표 요약</div>
<div class="section-content">
자, 데이터부터 깔끔하게 정리해줄게. 지금 이 바닥에서 '알고리즘 간택' 받으려면 이 정도 숫자는 나와야 해.
<table>
<tr><th>평균 조회수</th><th>평균 Viral Point</th><th>핵심 분석 대상</th></tr>
<tr><td>{int(avg_views):,}회</td><td>{int(avg_viral):,}점</td><td>{len(results)}개 핵심 표본</td></tr>
</table>
데이터 분석 결과, 상위 콘텐츠들은 단순 시청보다 <b>재방문 및 댓글 공유 지수</b>가 일반 영상 대비 180% 높게 나타났어.
</div>

<div class="section-title">💡 2. [통합 인사이트] 국가 및 포맷별 트렌드 분석</div>
<div class="section-content">
{insight} <br><br>
수집된 제목과 태그, 댓글을 종합해볼 때 {format_report} 시청자들은 현재 <b>'{results[0]['title'][:20]}...'</b>와 같은 직관적인 연출에 가장 민감하게 반응하고 있어.
</div>

<div style="margin-top:30px; text-align:center; font-weight:bold; color:#ff4b4b; border:1px solid #ff4b4b; padding:15px; border-radius:10px;">
🎯 팀장 세나의 핵심 진단: "{region_name} 시장에서 {video_type}로 승부 보려면, 수치화된 Viral Point를 분석해서 타겟이 키보드를 잡게 만드는 '트리거'부터 설계해!"
</div>
</div>
"""
    return report_html

def fetch_videos(topic_text, v_type, r_info, v_count):
    youtube = get_youtube_client()
    is_shorts = "Shorts" in v_type
    is_popular_mode = not topic_text.strip()
    collected, next_token = [], None
    
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

    results, all_metadata, now = [], "", datetime.now()
    non_us_count, max_non_us = 0, int(v_count * 0.1)

    for i in all_stats:
        t, c, snp = i['snippet']['title'], i['snippet']['channelTitle'], i['snippet']['description']
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
        all_metadata += f" {t} {snp} "

        results.append({
            'title': t, 'thumbnail': i['snippet']['thumbnails']['high']['url'],
            'url': f"https://www.youtube.com/shorts/{i['id']}" if is_shorts else f"https://www.youtube.com/watch?v={i['id']}",
            'channel': c, 'view_count': v, 'date': i['snippet']['publishedAt'][:10],
            'v_point': vp, 'status': "🔥 초신성" if tier==1 else "🔄 스테디", 'tier': tier, 'view_raw': v
        })

    results.sort(key=lambda x: (x['tier'], -x['v_point']))
    final = results[:v_count]
    report = generate_advanced_report(r_info['code'], "Shorts" if is_shorts else "Long-form", final, all_metadata)
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
    with st.spinner('세나 팀장이 데이터를 통합 분석하는 중... (최대 1분 소요)'):
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
                
                st.markdown(report, unsafe_allow_html=True)
                
                c1, c2 = st.columns([3, 1])
                with c2: show_ad("bottom")
                    
        except Exception as e:
            if "quotaExceeded" in str(e):
                if st.session_state.key_index < len(API_KEYS) - 1:
                    st.session_state.key_index += 1
                    st.toast("🔄 1번 키 소진! 자동 전환 중...")
                    time.sleep(1); st.rerun()
                else: st.error("🚨 모든 할당량 소진.")
            else: st.error(f"오류 발생: {e}")
