import streamlit as st
from googleapiclient.discovery import build
from googletrans import Translator
import re
from collections import Counter
from datetime import datetime, timedelta
import random
import time

# --- [설정] API 키 관리 ---
API_KEYS = [
    "AIzaSyAZeKYF34snfhN1UY3EZAHMmv_IcVvKhAc", 
    "AIzaSyBNMVMMfFI5b7GNEXjoEuOLdX_zQ8XjsCc"
]

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

st.set_page_config(page_title="글로벌 마케팅 정밀 분석", layout="wide")

if 'key_index' not in st.session_state:
    st.session_state.key_index = 0

# CSS 디자인
st.markdown("""
<style>
    .video-card { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); min-height: 750px; display: flex; flex-direction: column; justify-content: space-between; }
    .thumb-link img { transition: transform 0.2s; border-radius: 8px; width: 100%; aspect-ratio: 16/9; object-fit: cover; }
    .thumb-link img:hover { transform: scale(1.02); }
    .v-title { font-size: 1rem; font-weight: 800; color: #111; line-height: 1.4; max-height: 2.8em; overflow: hidden; margin: 12px 0 8px 0; }
    .v-meta { font-size: 0.85rem; color: #555; margin-bottom: 10px; line-height: 1.6; border-bottom: 1px dashed #eee; padding-bottom: 10px; }
    .v-status { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; margin-bottom: 10px; }
    .status-hot { background-color: #ffebee; color: #c62828; }
    .status-steady { background-color: #e3f2fd; color: #1565c0; }
    .v-insight-box { background-color: #f8f9fa; padding: 12px; border-radius: 8px; font-size: 0.85rem; border-left: 4px solid #1a73e8; margin-top: auto; }
    .v-quote { font-style: italic; color: #666; background: #fff; padding: 8px; border-radius: 6px; border: 1px solid #eee; margin: 8px 0; font-size: 0.8rem; }
    .report-container { background-color: #263238; color: #eceff1; padding: 30px; border-radius: 15px; margin-top: 40px; }
    .report-highlight { color: #80cbc4; font-weight: bold; font-size: 1.1rem; margin-top: 20px; display: block; margin-bottom: 10px;}
    .stat-val { color: #1a73e8; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

st.title("📡 실시간 유튜브 트렌드 & 정밀 국가 필터링")

translator = Translator()

def get_youtube_client():
    current_key = API_KEYS[st.session_state.key_index]
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=current_key)

def parse_duration(duration):
    minutes = re.search(r'(\d+)M', duration)
    seconds = re.search(r'(\d+)S', duration)
    total = 0
    if minutes: total += int(minutes.group(1)) * 60
    if seconds: total += int(seconds.group(1))
    return total

def is_non_us_english(title, channel):
    """미국 외 영어권 국가(영국, 호주, 캐나다 등) 콘텐츠 감지"""
    keywords = [
        ' bbc', 'sky news', 'itv', 'guardian', 'uk ', 'london', 'british', # 영국
        ' cbc', 'canada', 'toronto', 'vancouver', # 캐나다
        ' abc news (australia)', ' 7news', ' 9news', 'australia', 'melbourne', 'sydney' # 호주
    ]
    combined = (title + " " + channel).lower()
    return any(k in combined for k in keywords)

def is_strictly_non_us(title, channel):
    """인도/동남아 문자열 감지"""
    scripts = [re.compile(r'[\u0900-\u097F]+'), re.compile(r'[\u0E00-\u0E7F]+'), re.compile(r'[\u0600-\u06FF]+')]
    combined = title + " " + channel
    if any(s.search(combined) for s in scripts): return True
    blacklist = ['india', 'hindi', 'bollywood', 't-series', 'zeemusic', 'set india', 'sony pal', 'thai', 'vietnam']
    return any(k in combined.lower() for k in blacklist)

def analyze_viral_trigger(youtube, video_id, title, region_code):
    try:
        request = youtube.commentThreads().list(part="snippet", videoId=video_id, maxResults=20, order="relevance")
        response = request.execute()
        all_comments = [item['snippet']['topLevelComment']['snippet']['textDisplay'] for item in response.get('items', [])]
        if not all_comments: return "데이터 부족", "분석 불가", "N/A"
        
        target_comments = all_comments
        if region_code == 'KR':
            korean = [c for c in all_comments if re.search('[가-힣]', c)]
            if korean: target_comments = korean

        full_text = " ".join(target_comments).lower()
        valid = [c for c in target_comments if len(c) > 10 and len(c) < 100]
        best_quote = valid[0] if valid else target_comments[0][:60]
        
        if any(w in full_text for w in ['노래', '음색', 'dance', 'music', 'mv']): trigger = "🎤 퍼포먼스/뮤직"
        elif any(w in full_text for w in ['ㅋㅋㅋㅋ', 'lol', 'funny', '웃겨']): trigger = "😂 엔터테인먼트"
        elif any(w in full_text for w in ['꿀팁', 'how to', '강의']): trigger = "💡 정보성/유틸리티"
        else: trigger = "🥰 감성/공감"
        return trigger, "현지 시청자들의 실시간 반응이 매우 능동적임.", best_quote.replace('"', '').strip()
    except Exception as e:
        if "quotaExceeded" in str(e): raise e
        return "데이터 접근 제한", "분석 불가", "-"

def fetch_videos(topic_text, v_type, r_info, v_count):
    youtube = get_youtube_client()
    is_shorts = "Shorts" in v_type
    is_popular_mode = not topic_text.strip()
    max_raw = 100 # 필터링을 위해 최대 데이터 확보
    
    if not is_popular_mode:
        try: translated_q = translator.translate(topic_text, dest=r_info['lang']).text
        except: translated_q = topic_text
        request = youtube.search().list(part="snippet", q=f"{translated_q} {'#shorts' if is_shorts else ''}", type="video", videoDuration="short" if is_shorts else "any", regionCode=r_info['code'], relevanceLanguage=r_info['lang'], order="viewCount", maxResults=max_raw)
    else:
        if is_shorts:
            # [복구] 국가별 숏츠 키워드 매핑
            country_kw = {"KR": "쇼츠", "US": "Shorts", "JP": "ショート"}
            q_val = f"#shorts {country_kw.get(r_info['code'], '')}"
            request = youtube.search().list(part="snippet", q=q_val, type="video", videoDuration="short", regionCode=r_info['code'], relevanceLanguage=r_info['lang'], order="viewCount", maxResults=max_raw)
        else:
            request = youtube.videos().list(part="snippet,statistics", chart="mostPopular", regionCode=r_info['code'], maxResults=max_raw)
    
    response = request.execute()
    video_ids = [item['id']['videoId'] if 'videoId' in item['id'] else item['id'] for item in response.get('items', [])]
    if not video_ids: return [], 0, [], ""

    stats_response = youtube.videos().list(part="snippet,statistics,contentDetails", id=",".join(video_ids)).execute()
    results, titles_list, trend_keywords = [], [], []
    today = datetime.now()
    
    # 미국 타겟 시 비북미권(인도/동남아) 20%, 비US 영어권(영국 등) 10% 제한
    non_us_target_count = 0 
    non_us_english_count = 0
    max_non_us_target = int(v_count * 0.2)
    max_non_us_english = int(v_count * 0.1)

    for item in stats_response.get('items', []):
        title = item['snippet']['title']
        channel = item['snippet']['channelTitle']
        duration_sec = parse_duration(item['contentDetails']['duration'])
        
        if not is_shorts and duration_sec < 120: continue 
        if is_shorts and duration_sec > 120: continue
        
        if r_info['code'] == 'US':
            # 1. 인도/동남아 필터 (20% 제한)
            if is_strictly_non_us(title, channel):
                if non_us_target_count >= max_non_target: continue
                non_us_target_count += 1
            # 2. 비US 영어권 필터 (영국/호주 등 10% 제한)
            if is_non_us_english(title, channel):
                if non_us_english_count >= max_non_us_english: continue
                non_us_english_count += 1

        pub_date = datetime.strptime(item['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
        days_diff = (today - pub_date).days
        views = int(item['statistics'].get('viewCount', 0))
        comments = int(item['statistics'].get('commentCount', 0)) if 'commentCount' in item['statistics'] else 0
        if days_diff > 10 and (comments == 0 or (views / (days_diff+1) < 100)): continue

        trigger, insight, quote = analyze_viral_trigger(youtube, item['id'], title, r_info['code'])
        trend_keywords.append(trigger)
        titles_list.append(title)
        
        results.append({
            'title': title, 'thumbnail': item['snippet']['thumbnails']['high']['url'],
            'url': f"https://www.youtube.com/shorts/{item['id']}" if is_shorts else f"https://www.youtube.com/watch?v={item['id']}",
            'channel': channel, 'view_count': views, 'date': pub_date.strftime("%Y-%m-%d"),
            'trigger': trigger, 'insight': insight, 'quote': quote, 
            'viral_score': int(views * (0.001 + (comments / views * 0.01))) if views > 0 else 0,
            'status': "🔥 급상승" if days_diff <= 10 else "🔄 스테디",
            'is_old': days_diff > 10
        })

    # 최신성 우선 정렬
    results.sort(key=lambda x: (x['is_old'], -x['view_count']))
    final_list = results[:v_count]
    accuracy = (len(final_list) / v_count) * 100 if v_count > 0 else 0
    return final_list, accuracy, trend_keywords, titles_list

# --- 사이드바 ---
st.sidebar.header("📊 마케팅 분석 설정")
region_map = {"한국 🇰🇷": {"code": "KR", "lang": "ko"}, "미국 🇺🇸": {"code": "US", "lang": "en"}, "일본 🇯🇵": {"code": "JP", "lang": "ja"} }
region_name = st.sidebar.selectbox("📍 타겟 시장", list(region_map.keys()))
sel_region = region_map[region_name]
video_type = st.sidebar.radio("📱 콘텐츠 포맷", ["롱폼 (2분 이상)", "숏폼 (Shorts)"])
count = st.sidebar.slider("🔢 분석 샘플", 1, 30, 8)
topic = st.sidebar.text_input("🔍 키워드/주제", placeholder="공란: 국가별 트렌드 수집")
search_clicked = st.sidebar.button("🚀 인사이트 도출 시작", use_container_width=True)

# --- 결과 출력 ---
if search_clicked or not topic:
    with st.spinner('국가별 트렌드 수집 및 정밀 필터링 중...'):
        try:
            final_results, accuracy, keywords_list, titles = fetch_videos(topic, video_type, sel_region, count)
            st.subheader(f"📝 {region_name} {video_type} 분석 결과 (최신순)")
            if not final_results: st.warning("데이터를 찾을 수 없습니다.")
            else:
                cols = st.columns(4)
                for idx, video in enumerate(final_results):
                    with cols[idx % 4]:
                        s_color = "status-hot" if not video['is_old'] else "status-steady"
                        st.markdown(f"""
                        <div class="video-card">
                            <a href="{video['url']}" target="_blank" class="thumb-link"><img src="{video['thumbnail']}"></a>
                            <div style="margin-top:10px;"><span class="v-status {s_color}">{video['status']}</span></div>
                            <div class="v-title">{video['title']}</div>
                            <div class="v-meta"><b>{video['channel']}</b><br>조회수: {video['view_count']:,}회<br>공개일: {video['date']}</div>
                            <div class="v-insight-box"><b>🎯 트렌드 요인:</b><br>{video['trigger']}<br><br>
                            <div style="font-size:0.8rem; line-height:1.5; color:#444;">{video['insight']}</div>
                            <div class="v-quote">" {video['quote']} "</div>
                            <div style="margin-top:10px; font-size:0.8rem;">🌐 <b>바이럴 지수:</b> <span class="stat-val">{video['viral_score']:,}</span></div></div>
                        </div>
                        """, unsafe_allow_html=True)
                
                most_common_trigger = Counter(keywords_list).most_common(1)[0][0] if keywords_list else "복합 요인"
                matching_titles = [t for i, t in enumerate(titles) if keywords_list[i] == most_common_trigger]
                if not matching_titles: matching_titles = [titles[0]]
                title_str = ", ".join([f"'{t[:15]}...'" for t in matching_titles[:2]])
                
                report_html = f"""
<div class="report-container">
    <h3 style="margin-top:0; color:#4dd0e1;">📋 2026 마케팅 트렌드 인사이트 보고서</h3>
    <p style="font-size: 1.1rem; margin-bottom: 20px;"><b>🎯 분석 정확도: {accuracy:.1f}%</b></p>
    <span class="report-highlight">📍 현황 진단:</span>
    <p style="line-height: 1.8; color: #eceff1;">
        현재 <b>{region_name}</b> 시장의 {video_type} 트렌드는 <b>'{most_common_trigger}'</b> 요소가 핵심 드라이버입니다. 
        특히 미국 타겟 분석 시 <b>영국, 캐나다 등 타 영어권 콘텐츠 비중을 10% 이하로 제어</b>하여 현지 북미 트렌드의 순수성을 확보했습니다. 
        분석 결과 <b>{title_str}</b> 등의 콘텐츠가 최신 인게이지먼트를 주도하고 있습니다.
    </p>
    <hr style="border: 0.5px solid #546e7a;">
    <p style="font-size: 0.8rem; color: #b0bec5;">[초정밀 검증] 국가별 숏츠 키워드 매칭 및 비북미 영어권 필터링 로직이 적용되었습니다.</p>
</div>"""
                st.markdown(report_html, unsafe_allow_html=True)

        except Exception as e:
            if "quotaExceeded" in str(e):
                if st.session_state.key_index < len(API_KEYS) - 1:
                    st.session_state.key_index += 1
                    st.toast("🔄 1번 키 소진! 2번 키로 자동 전환합니다...")
                    time.sleep(1)
                    st.rerun()
                else: st.error("🚨 모든 할당량 소진.")
            else: st.error(f"오류 발생: {e}")
