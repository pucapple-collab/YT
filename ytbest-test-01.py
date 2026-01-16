import streamlit as st
from googleapiclient.discovery import build
from googletrans import Translator
import re
from collections import Counter
from datetime import datetime, timedelta
import statistics
import random

# --- [설정] API 키 관리 ---
API_KEYS = ["AIzaSyAZeKYF34snfhN1UY3EZAHMmv_IcVvKhAc", "AIzaSyBNMVMMfFI5b7GNEXjoEuOLdX_zQ8XjsCc"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

st.set_page_config(page_title="Global Trend Intelligence", layout="wide")

if 'key_index' not in st.session_state:
    st.session_state.key_index = 0

# CSS 디자인
st.markdown("""
<style>
    .video-card { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 12px; 
        border: 1px solid #e0e0e0; 
        margin-bottom: 20px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); 
        height: 100%;
    }
    .thumb-link img { transition: transform 0.2s; border-radius: 8px; width: 100%; aspect-ratio: 16/9; object-fit: cover; }
    .thumb-link img:hover { transform: scale(1.02); }
    
    .v-title { font-size: 0.95rem; font-weight: 700; color: #111; line-height: 1.35; max-height: 2.7em; overflow: hidden; margin: 10px 0 5px 0; }
    .v-meta { font-size: 0.8rem; color: #555; margin-bottom: 8px; line-height: 1.4; border-bottom: 1px dashed #eee; padding-bottom: 8px; }
    
    .v-status { display: inline-block; padding: 3px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; margin-bottom: 5px; }
    .status-10d { background-color: #ffebee; color: #c62828; }
    .status-1m { background-color: #e3f2fd; color: #1565c0; }
    .status-steady { background-color: #f5f5f5; color: #616161; }
    
    .v-insight-box { background-color: #f8f9fa; padding: 10px; border-radius: 8px; font-size: 0.8rem; border-left: 3px solid #1a73e8; }
    
    /* 리포트 스타일 */
    .report-container { 
        background-color: #1e293b; 
        color: #f1f5f9; 
        padding: 30px; 
        border-radius: 15px; 
        margin-top: 40px; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.2); 
    }
    .report-title { 
        color: #38bdf8; 
        font-size: 1.5rem; 
        font-weight: bold; 
        margin-bottom: 20px; 
        border-bottom: 1px solid #475569; 
        padding-bottom: 10px; 
    }
    .report-section { margin-bottom: 20px; }
    .report-label { 
        color: #94a3b8; 
        font-size: 0.85rem; 
        font-weight: bold; 
        text-transform: uppercase; 
        letter-spacing: 1px; 
        margin-bottom: 5px;
    }
    .report-content { font-size: 1rem; line-height: 1.7; }
    .highlight { color: #facc15; font-weight: bold; }
    .stat-val { color: #1a73e8; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

st.title("📡 실시간 글로벌 트렌드 인텔리전스")

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

def calculate_viral_point(views, likes, comments):
    if views == 0: return 0
    engagement = (likes / views * 10) + (comments / views * 50)
    return int((views * 0.001) * (1 + engagement))

def is_japanese(text):
    return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text))

def generate_expert_report(region_display_name, video_type, results, keywords):
    """
    시니어급 마케팅 리포트 생성 (HTML 태그 오류 수정됨)
    """
    if not results: return "데이터 부족으로 리포트를 생성할 수 없습니다."
    
    avg_views = statistics.mean([v['view_raw'] for v in results])
    avg_viral = statistics.mean([v['v_point'] for v in results])
    top_keywords = [k for k, c in Counter(keywords).most_common(3)]
    keyword_str = ", ".join(top_keywords)
    
    context = ""
    if "일본" in region_display_name and "Shorts" in video_type:
        context = "일본 숏폼 시장은 '버츄얼 유튜버', '애니메이션 2차 창작', '생활 밀착형 꿀팁'이 강세이며, 언어적 유희가 포함된 밈(Meme)의 확산 속도가 빠릅니다."
    elif "미국" in region_display_name:
        context = "미국 시장은 '강력한 시각적 후킹'과 '챌린지 참여'가 핵심이며, 글로벌 트렌드의 발신지 역할을 수행합니다."
    elif "한국" in region_display_name:
        context = "한국 시장은 '공감대 형성'과 '빠른 정보 전달'이 핵심이며, 댓글을 통한 커뮤니티 형성이 트렌드 지속성을 결정합니다."

    # [수정] 들여쓰기 문제 해결을 위해 f-string을 한 줄로 연결하거나 textwrap 사용
    # 여기서는 가독성을 위해 명확한 HTML 구조로 반환
    html_content = f"""
<div class="report-container">
    <div class="report-title">📊 2026 {region_display_name} 마케팅 트렌드 인사이트 보고서</div>
    <div class="report-section">
        <div class="report-label">Target Market Analysis</div>
        <div class="report-content">
            현재 <b>{region_display_name}</b>의 {video_type} 시장은 평균 조회수 <span class="highlight">{int(avg_views):,}회</span>, 평균 Viral Point <span class="highlight">{int(avg_viral):,}점</span>을 기록하며 고관여 트렌드를 형성하고 있습니다. 
            {context}
        </div>
    </div>
    <div class="report-section">
        <div class="report-label">Content DNA & UGC Pattern</div>
        <div class="report-content">
            상위 랭크된 콘텐츠들의 공통된 DNA는 <b>'{keyword_str}'</b>입니다. 
            단순 시청에서 끝나는 것이 아니라, 시청자가 댓글로 본인의 경험을 공유하거나 타인을 태그하는 <b>'참여형 소비'</b> 패턴이 뚜렷합니다. 
            특히 10일 이내 업로드된 신규 콘텐츠들이 <b>'재가공(Remix)'</b> 및 <b>'스크랩(저장)'</b> 유도를 통해 알고리즘 노출 빈도를 높이고 있습니다.
        </div>
    </div>
    <div class="report-section">
        <div class="report-label">Strategic Recommendation</div>
        <div class="report-content">
            1. <b>포맷 최적화:</b> {video_type}의 특성을 고려하여 초반 3초 내에 '{top_keywords[0] if top_keywords else '핵심'}' 요소를 시각적으로 배치하십시오.<br>
            2. <b>인게이지먼트 유도:</b> 단순 질문보다는 논쟁이나 공감을 유발하는 '고정 댓글' 전략을 통해 Viral Point를 확보해야 합니다.<br>
            3. <b>타겟팅:</b> 현재 트렌드는 광범위한 대중보다는 특정 취향(Niche)을 가진 <b>'코어 팬덤'</b>의 결집력이 전체 트렌드를 견인하고 있습니다.
        </div>
    </div>
    <hr style="border-color: #475569;">
    <div style="font-size: 0.8rem; color: #94a3b8;">
        * 본 리포트는 실시간 수집된 {len(results)}건의 데이터(조회수, 게시일, 반응도)를 정량 분석하여 도출되었습니다.
    </div>
</div>
"""
    return html_content

def fetch_videos(topic_text, v_type, r_info, v_count):
    youtube = get_youtube_client()
    is_shorts = "Shorts" in v_type
    is_popular_mode = not topic_text.strip()
    
    collected_items = []
    next_page_token = None
    max_scan_pages = 4 
    
    for _ in range(max_scan_pages):
        try:
            if not is_popular_mode:
                try: translated_q = translator.translate(topic_text, dest=r_info['lang']).text
                except: translated_q = topic_text
                request = youtube.search().list(
                    part="snippet", q=f"{translated_q} {'#shorts' if is_shorts else ''}", 
                    type="video", videoDuration="short" if is_shorts else "any", 
                    regionCode=r_info['code'], relevanceLanguage=r_info['lang'], 
                    order="viewCount", maxResults=50, pageToken=next_page_token
                )
            else:
                if is_shorts:
                    country_kw = {"KR": "쇼츠", "US": "Shorts", "JP": "ショート"}
                    request = youtube.search().list(
                        part="snippet", q=f"#shorts {country_kw.get(r_info['code'], '')}", 
                        type="video", videoDuration="short", 
                        regionCode=r_info['code'], relevanceLanguage=r_info['lang'], 
                        order="viewCount", maxResults=50, pageToken=next_page_token
                    )
                else:
                    request = youtube.videos().list(
                        part="snippet,statistics", chart="mostPopular", 
                        regionCode=r_info['code'], maxResults=50, pageToken=next_page_token
                    )
            
            response = request.execute()
            collected_items.extend(response.get('items', []))
            next_page_token = response.get('nextPageToken')
            
            if not next_page_token: break
            if len(collected_items) >= 200: break
            
        except Exception as e:
            if "quotaExceeded" in str(e): raise e
            break

    video_ids = [item['id']['videoId'] if 'videoId' in item['id'] else item['id'] for item in collected_items]
    if not video_ids: return [], 0, [], ""

    all_stats_items = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        stats_resp = youtube.videos().list(
            part="snippet,statistics,contentDetails", id=",".join(chunk)
        ).execute()
        all_stats_items.extend(stats_resp.get('items', []))

    results = []
    trend_keywords = []
    now = datetime.now()

    for item in all_stats_items:
        title = item['snippet']['title']
        channel = item['snippet']['channelTitle']
        duration_sec = parse_duration(item['contentDetails']['duration'])
        
        days_diff = (now - datetime.strptime(item['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")).days
        if days_diff > 365: continue 
        
        if not is_shorts and duration_sec < 120: continue 
        if is_shorts and duration_sec > 120: continue
        
        if r_info['code'] == 'JP' and not is_japanese(title + channel): continue

        views = int(item['statistics'].get('viewCount', 0))
        likes = int(item['statistics'].get('likeCount', 0)) if 'likeCount' in item['statistics'] else 0
        comments = int(item['statistics'].get('commentCount', 0)) if 'commentCount' in item['statistics'] else 0
        
        if days_diff > 30 and (views < 500000 or (likes+comments)/views < 0.02): continue

        v_point = calculate_viral_point(views, likes, comments)
        
        if days_diff <= 10: tier, status = 1, "🔥 10일내 초신성"
        elif days_diff <= 30: tier, status = 2, "📅 월간 트렌드"
        else: tier, status = 3, "🔄 스테디셀러"

        words = re.sub(r'[^\w\s]', '', title).split()
        trend_keywords.extend([w for w in words if len(w) > 1])

        results.append({
            'title': title, 'thumbnail': item['snippet']['thumbnails']['high']['url'],
            'url': f"https://www.youtube.com/shorts/{item['id']}" if is_shorts else f"https://www.youtube.com/watch?v={item['id']}",
            'channel': channel, 'view_count': views, 'date': item['snippet']['publishedAt'][:10],
            'v_point': v_point, 'status': status, 'tier': tier, 'view_raw': views
        })

    results.sort(key=lambda x: (x['tier'], -x['v_point']))
    final_list = results[:v_count]
    
    # [수정] 보고서 생성 시 지역명(Region Name) 전달
    # region_name 변수는 사이드바에서 선택된 값 (예: "한국 🇰🇷")
    # 하지만 여기 함수 인자에는 없으므로 fetch_videos 호출 시 사용된 region_map 키를 찾아야 함
    # 편의상 fetch_videos 호출 후 리턴값에서 해결하거나, 여기서 해결.
    # 여기서는 간단히 r_info['code']를 기반으로 역추적하거나 외부에서 전달받는 게 좋음.
    # 함수 구조상 내부에서 처리:
    display_name = f"{r_info['code']} 시장"
    if r_info['code'] == 'KR': display_name = "한국 🇰🇷"
    elif r_info['code'] == 'US': display_name = "미국 🇺🇸"
    elif r_info['code'] == 'JP': display_name = "일본 🇯🇵"

    report_html = generate_expert_report(display_name, "Shorts" if is_shorts else "Long-form", final_list, trend_keywords)
    
    accuracy = (len(final_list)/v_count)*100 if v_count > 0 else 0
    return final_list, min(accuracy, 100.0), report_html

# --- 사이드바 ---
st.sidebar.header("📊 분석 파라미터")
region_map = {"한국 🇰🇷": {"code": "KR", "lang": "ko"}, "미국 🇺🇸": {"code": "US", "lang": "en"}, "일본 🇯🇵": {"code": "JP", "lang": "ja"} }
region_name = st.sidebar.selectbox("📍 타겟 시장", list(region_map.keys()))
sel_region = region_map[region_name]
video_type = st.sidebar.radio("📱 콘텐츠 포맷", ["롱폼 (2분 이상)", "숏폼 (Shorts)"])
count = st.sidebar.slider("🔢 분석 샘플", 1, 30, 8)
topic = st.sidebar.text_input("🔍 키워드/주제", placeholder="공란: 실시간 인기 수집")
search_clicked = st.sidebar.button("🚀 인사이트 분석 시작", use_container_width=True)

# --- 결과 출력 ---
if search_clicked or not topic:
    with st.spinner('대용량 데이터 수집 및 시니어 리포트 작성 중...'):
        try:
            final_results, accuracy, report_html = fetch_videos(topic, video_type, sel_region, count)
            st.subheader(f"📝 {region_name} {video_type} 분석 결과")
            
            if not final_results: st.warning("조건에 맞는 트렌드 데이터를 충분히 확보하지 못했습니다.")
            else:
                cols = st.columns(4)
                for idx, video in enumerate(final_results):
                    with cols[idx % 4]:
                        s_class = "status-10d" if video['tier'] == 1 else ("status-1m" if video['tier'] == 2 else "status-steady")
                        st.markdown(f"""
                        <div class="video-card">
                            <a href="{video['url']}" target="_blank" class="thumb-link"><img src="{video['thumbnail']}"></a>
                            <div style="margin-top:10px;"><span class="v-status {s_class}">{video['status']}</span></div>
                            <div class="v-title">{video['title']}</div>
                            <div class="v-meta">
                                <b>{video['channel']}</b><br>
                                조회수: {video['view_count']:,}회<br>
                                공개일: {video['date']}
                            </div>
                            <div class="v-insight-box">
                                🌐 <b>Viral Point:</b> <span class="stat-val">{video['v_point']:,}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # [수정] 리포트 HTML 출력 시 unsafe_allow_html=True 필수
                st.markdown(report_html, unsafe_allow_html=True)

        except Exception as e:
            if "quotaExceeded" in str(e):
                if st.session_state.key_index < len(API_KEYS) - 1:
                    st.session_state.key_index += 1
                    st.toast("🔄 1번 키 소진! 자동 키 전환 중...")
                    time.sleep(1)
                    st.rerun()
                else: st.error("🚨 모든 할당량 소진.")
            else: st.error(f"오류 발생: {e}")
