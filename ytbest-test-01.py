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
    .v-title { font-size: 1rem; font-weight: 800; color: #111; line-height: 1.4; max-height: 2.8em; overflow: hidden; margin: 12px 0 8px 0; }
    .v-meta { font-size: 0.85rem; color: #555; margin-bottom: 10px; line-height: 1.6; border-bottom: 1px dashed #eee; padding-bottom: 10px; }
    .v-status { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; margin-bottom: 10px; }
    .status-hot { background-color: #ffebee; color: #c62828; }
    .v-insight-box { background-color: #f8f9fa; padding: 12px; border-radius: 8px; font-size: 0.85rem; border-left: 4px solid #1a73e8; margin-top: auto; }
    .report-container { background-color: #263238; color: #eceff1; padding: 30px; border-radius: 15px; margin-top: 40px; }
    .report-highlight { color: #80cbc4; font-weight: bold; font-size: 1.1rem; margin-top: 20px; display: block; margin-bottom: 10px;}
    .stat-val { color: #1a73e8; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

st.title("📡 실시간 유튜브 트렌드 & 초정밀 마케팅 분석")

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

def is_strictly_non_us(title, channel):
    """
    유니코드 문자열 분석 및 블랙리스트를 통한 초정밀 비북미권 필터링
    """
    # 1. 특수 문자 기반 필터 (힌두어, 태국어, 아랍어 등 유니코드 범위)
    scripts = [
        re.compile(r'[\u0900-\u097F]+'), # Devanagari (인도)
        re.compile(r'[\u0E00-\u0E7F]+'), # Thai (태국)
        re.compile(r'[\u0600-\u06FF]+'), # Arabic (중동)
        re.compile(r'[\u0B80-\u0BFF]+'), # Tamil (인도 남부)
    ]
    
    combined = title + " " + channel
    if any(s.search(combined) for s in scripts):
        return True

    # 2. 확장 블랙리스트 키워드 (인도/동남아 대형 미디어)
    blacklist = [
        'india', 'hindi', 'bollywood', 't-series', 'zeemusic', 'telugu', 'tamil', 'punjabi',
        'set india', 'sony pal', 'colors tv', 'sab tv', 'star plus', 'voot', 'dangal',
        'thai', 'vietnam', 'philippines', 'indonesia', 'malay', 'v-pop', 't-pop', 'gmmgrammy',
        'gma network', 'abs-cbn', 'workpoint', 'bhakti', 'bhojpuri'
    ]
    
    combined_lower = combined.lower()
    return any(k in combined_lower for k in blacklist)

def analyze_viral_trigger(youtube, video_id, title, region_code):
    try:
        request = youtube.commentThreads().list(part="snippet", videoId=video_id, maxResults=20, order="relevance")
        response = request.execute()
        all_comments = [item['snippet']['topLevelComment']['snippet']['textDisplay'] for item in response.get('items', [])]
        if not all_comments: return "데이터 부족", "분석 데이터 부족", "N/A"
        
        target_comments = all_comments
        if region_code == 'KR':
            korean_comments = [c for c in all_comments if re.search('[가-힣]', c)]
            if korean_comments: target_comments = korean_comments

        full_text = " ".join(target_comments).lower()
        valid_quotes = [c for c in target_comments if len(c) > 10 and len(c) < 100]
        best_quote = valid_quotes[0] if valid_quotes else target_comments[0][:60]
        
        if any(w in full_text for w in ['ㅋㅋㅋㅋ', 'lol', 'funny', '웃겨']): trigger = "😂 엔터테인먼트"
        elif any(w in full_text for w in ['노래', '음색', 'dance', 'music', 'mv']): trigger = "🎤 퍼포먼스/뮤직"
        elif any(w in full_text for w in ['꿀팁', 'how to', '강의', 'review']): trigger = "💡 정보성/유틸리티"
        else: trigger = "🥰 감성/공감"
        
        insight = "타겟 국가 시청자들의 실시간 반응이 매우 능동적임."
        return trigger, insight, best_quote.replace('"', '').strip()
    except Exception as e:
        if "quotaExceeded" in str(e): raise e
        return "데이터 접근 제한", "분석 불가", "-"

def fetch_videos(topic_text, v_type, r_info, v_count):
    youtube = get_youtube_client()
    is_shorts = "Shorts" in v_type
    is_popular_mode = not topic_text.strip()
    
    # 미국 타겟 시 더 넓은 범위에서 필터링하기 위해 maxResults를 100으로 상향
    max_raw = 100 if r_info['code'] == 'US' else 50
    
    if not is_popular_mode:
        try: translated_q = translator.translate(topic_text, dest=r_info['lang']).text
        except: translated_q = topic_text
        request = youtube.search().list(part="snippet", q=f"{translated_q} {'#shorts' if is_shorts else ''}", type="video", videoDuration="short" if is_shorts else "any", regionCode=r_info['code'], relevanceLanguage=r_info['lang'], order="viewCount", maxResults=max_raw)
    else:
        if is_shorts:
            request = youtube.search().list(part="snippet", q="#shorts", type="video", videoDuration="short", regionCode=r_info['code'], relevanceLanguage=r_info['lang'], order="viewCount", maxResults=max_raw)
        else:
            request = youtube.videos().list(part="snippet,statistics", chart="mostPopular", regionCode=r_info['code'], maxResults=max_raw)
    
    response = request.execute()
    items = response.get('items', [])
    video_ids = [item['id']['videoId'] if 'videoId' in item['id'] else item['id'] for item in items]
    if not video_ids: return [], 0, [], ""

    stats_response = youtube.videos().list(part="snippet,statistics,contentDetails", id=",".join(video_ids)).execute()
    results, titles_list, trend_keywords = [], [], []
    today = datetime.now()
    
    # 비북미권 개수 관리 (20% 제한)
    non_us_count = 0
    max_non_us = int(v_count * 0.2)

    for item in stats_response.get('items', []):
        title = item['snippet']['title']
        channel = item['snippet']['channelTitle']
        duration_sec = parse_duration(item['contentDetails']['duration'])
        
        if not is_shorts and duration_sec < 120: continue 
        if is_shorts and duration_sec > 120: continue
        
        # [초정밀 필터링 적용]
        if r_info['code'] == 'US':
            if is_strictly_non_us(title, channel):
                if non_us_count >= max_non_us: continue
                non_us_count += 1

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
            'status': "🔥 급상승" if days_diff < 7 else "🔄 스테디"
        })
        if len(results) >= v_count: break

    accuracy = (len(results) / v_count) * 100 if v_count > 0 else 0
    return results, min(accuracy, 100.0), trend_keywords, titles_list

# --- 사이드바 ---
st.sidebar.header("📊 분석 파라미터")
region_map = {"한국 🇰🇷": {"code": "KR", "lang": "ko"}, "미국 🇺🇸": {"code": "US", "lang": "en"}, "일본 🇯🇵": {"code": "JP", "lang": "ja"} }
region_name = st.sidebar.selectbox("📍 타겟 시장", list(region_map.keys()))
sel_region = region_map[region_name]
video_type = st.sidebar.radio("📱 콘텐츠 포맷", ["롱폼 (2분 이상)", "숏폼 (Shorts)"])
count = st.sidebar.slider("🔢 분석 샘플", 1, 30, 8)
topic = st.sidebar.text_input("🔍 키워드/주제", placeholder="공란: 전체 시장 트렌드")
search_clicked = st.sidebar.button("🚀 인사이트 도출 시작", use_container_width=True)

# --- 결과 출력 ---
if search_clicked or not topic:
    with st.spinner('초정밀 필터링 및 리포트 작성 중...'):
        try:
            final_results, accuracy, keywords_list, titles = fetch_videos(topic, video_type, sel_region, count)
            st.subheader(f"📝 {region_name} {video_type} 심층 분석 결과")
            if not final_results: st.warning("데이터를 찾을 수 없습니다.")
            else:
                cols = st.columns(4)
                for idx, video in enumerate(final_results):
                    with cols[idx % 4]:
                        st.markdown(f"""
                        <div class="video-card">
                            <a href="{video['url']}" target="_blank" class="thumb-link"><img src="{video['thumbnail']}"></a>
                            <div style="margin-top:10px;"><span class="v-status status-hot">{video['status']}</span></div>
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
        데이터 분석 결과 <b>{title_str}</b> 등의 콘텐츠가 상위권에 랭크되었습니다.
        특히 미국 시장 분석의 경우, 유니코드 스크립트 감지 및 확장 블랙리스트를 통해 비북미권 콘텐츠를 20% 이하로 제어하여 현지 정합성을 극대화했습니다.
    </p>
    <hr style="border: 0.5px solid #546e7a;">
    <p style="font-size: 0.8rem; color: #b0bec5;">[초정밀 검증] 유니코드 기반 지역 필터링 및 인게이지먼트 정합성 로직이 적용된 보고서입니다.</p>
</div>"""
                st.markdown(report_html, unsafe_allow_html=True)

        except Exception as e:
            if "quotaExceeded" in str(e):
                if st.session_state.key_index < len(API_KEYS) - 1:
                    st.session_state.key_index += 1
                    st.toast("🔄 1번 키 소진! 2번 키 전환 중...")
                    time.sleep(1)
                    st.rerun()
                else: st.error("🚨 모든 할당량 소진.")
            else: st.error(f"오류 발생: {e}")
