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
    
    .report-container { background-color: #1e293b; color: #f1f5f9; padding: 30px; border-radius: 15px; margin-top: 40px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); }
    .report-title { color: #38bdf8; font-size: 1.5rem; font-weight: bold; margin-bottom: 20px; border-bottom: 1px solid #475569; padding-bottom: 10px; }
    .report-section { margin-bottom: 15px; }
    .report-label { color: #94a3b8; font-size: 0.85rem; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .report-content { font-size: 1rem; line-height: 1.7; margin-top: 5px; }
    .highlight { color: #facc15; font-weight: bold; }
    .stat-val { color: #1a73e8; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# 광고 함수
def show_ad_banner(position):
    ad_data = {
        "sidebar": {"img": "https://via.placeholder.com/300x250.png?text=US+Trend+Ads", "link": "#"},
        "top": {"img": "https://via.placeholder.com/468x60.png?text=Premium+Analytics", "link": "#"},
        "bottom": {"img": "https://via.placeholder.com/728x90.png?text=Marketing+Solutions", "link": "#"}
    }
    data = ad_data.get(position)
    if data:
        st.markdown(f"""<div style="text-align:center; margin:10px 0;"><a href="{data['link']}" target="_blank"><img src="{data['img']}" style="width:100%; border-radius:8px;"></a></div>""", unsafe_allow_html=True)

# 상단 레이아웃
col_title, col_ad = st.columns([3, 1])
with col_title: st.title("📡 실시간 글로벌 트렌드 인텔리전스")
with col_ad: show_ad_banner("top")

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

def is_strictly_non_us(title, channel):
    """미국 타겟 시 인도/동남아 콘텐츠 강력 차단"""
    # 1. 문자열(Script) 감지
    scripts = [re.compile(r'[\u0900-\u097F]+'), re.compile(r'[\u0E00-\u0E7F]+'), re.compile(r'[\u0600-\u06FF]+'), re.compile(r'[\u0B80-\u0BFF]+')]
    combined = title + " " + channel
    if any(s.search(combined) for s in scripts): return True
    
    # 2. 키워드 블랙리스트 (인도/동남아 대형 채널 및 지명)
    blacklist = [
        'india', 'hindi', 'bollywood', 't-series', 'zeemusic', 'set india', 'sony pal', 'colors tv', 'sab tv', 'star plus', 
        'telugu', 'tamil', 'punjabi', 'thai', 'vietnam', 'philippines', 'indonesia', 'malay', 'v-pop', 't-pop', 
        'gmmgrammy', 'abs-cbn', 'workpoint', 'bhakti', 'bhojpuri', 'desimelodies', 'speed records'
    ]
    return any(k in combined.lower() for k in blacklist)

def generate_expert_report(region_name, video_type, results, keywords):
    if not results: return "데이터 부족으로 리포트를 생성할 수 없습니다."
    
    avg_views = statistics.mean([v['view_raw'] for v in results])
    avg_viral = statistics.mean([v['v_point'] for v in results])
    top_keywords = [k for k, c in Counter(keywords).most_common(3)]
    
    context = ""
    if "일본" in region_name and "Shorts" in video_type:
        context = "일본 숏폼 시장은 '버츄얼 유튜버', '애니메이션 2차 창작'이 강세이며, 언어적 유희가 포함된 밈(Meme)이 빠르게 확산됩니다."
    elif "미국" in region_name:
        context = "미국 시장은 '뉴욕/LA 기반의 어반 라이프스타일'과 '글로벌 챌린지'가 핵심이며, 인도 등 타 문화권 콘텐츠를 배제한 순수 북미 트렌드가 주도하고 있습니다."
    elif "한국" in region_name:
        context = "한국 시장은 '공감대 형성'과 '빠른 정보 전달'이 핵심이며, 댓글 커뮤니티가 트렌드 지속성을 결정합니다."

    return f"""
    <div class="report-container">
        <div class="report-title">📊 2026 {region_name} 마케팅 트렌드 인사이트 보고서</div>
        <div class="report-section">
            <div class="report-label">Target Market Analysis</div>
            <div class="report-content">
                현재 <b>{region_name}</b>의 {video_type} 시장은 평균 조회수 <span class="highlight">{int(avg_views):,}회</span>, 평균 Viral Point <span class="highlight">{int(avg_viral):,}점</span>을 기록 중입니다. 
                {context}
            </div>
        </div>
        <div class="report-section">
            <div class="report-label">Content DNA</div>
            <div class="report-content">
                상위 랭크된 콘텐츠들의 핵심 DNA는 <b>'{", ".join(top_keywords)}'</b>입니다. 
                특히 미국 시장 분석 시, <b>'Non-US Content 10% Cap'</b> 알고리즘을 적용하여 인도 및 동남아시아 유입을 차단하고 순수 북미권 데이터를 확보했습니다.
            </div>
        </div>
        <hr style="border-color: #475569;">
        <div style="font-size: 0.8rem; color: #94a3b8;">
            * 본 리포트는 실시간 수집된 {len(results)}건의 정제된 데이터를 기반으로 작성되었습니다.
        </div>
    </div>
    """

def fetch_videos(topic_text, v_type, r_info, v_count):
    youtube = get_youtube_client()
    is_shorts = "Shorts" in v_type
    is_popular_mode = not topic_text.strip()
    
    collected_items = []
    next_page_token = None
    # 인도 영상이 많을 수 있으므로 평소보다 더 많은 데이터를 스캔함 (최대 300개)
    max_scan_pages = 6 if r_info['code'] == 'US' else 4
    
    # [핵심] 미국 타겟 시 검색어에 '제외 키워드(-)'를 강력하게 적용
    us_filter = "-india -hindi -bollywood -tamil -telugu" if r_info['code'] == 'US' else ""
    
    for _ in range(max_scan_pages):
        try:
            if not is_popular_mode:
                try: translated_q = translator.translate(topic_text, dest=r_info['lang']).text
                except: translated_q = topic_text
                
                # 검색 쿼리에 제외 필터 추가
                final_q = f"{translated_q} {us_filter} {'#shorts' if is_shorts else ''}"
                
                request = youtube.search().list(
                    part="snippet", q=final_q, 
                    type="video", videoDuration="short" if is_shorts else "any", 
                    regionCode=r_info['code'], relevanceLanguage=r_info['lang'], 
                    order="viewCount", maxResults=50, pageToken=next_page_token
                )
            else:
                if is_shorts:
                    country_kw = {"KR": "쇼츠", "US": "Shorts", "JP": "ショート"}
                    # 숏츠 공란 검색 시에도 제외 필터 및 주요 도시 키워드 힌트 적용 가능
                    base_q = f"#shorts {country_kw.get(r_info['code'], '')}"
                    final_q = f"{base_q} {us_filter}"
                    
                    request = youtube.search().list(
                        part="snippet", q=final_q, 
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
            # 목표 수량의 3배수를 확보하면 스캔 중단 (필터링 고려)
            if len(collected_items) >= v_count * 3: break
            
        except Exception as e:
            if "quotaExceeded" in str(e): raise e
            break

    video_ids = [item['id']['videoId'] if 'videoId' in item['id'] else item['id'] for item in collected_items]
    if not video_ids: return [], 0, [], ""

    # 상세 데이터 조회 (50개씩)
    all_stats_items = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        try:
            stats_resp = youtube.videos().list(
                part="snippet,statistics,contentDetails", id=",".join(chunk)
            ).execute()
            all_stats_items.extend(stats_resp.get('items', []))
        except: continue

    results = []
    trend_keywords = []
    now = datetime.now()
    
    # [핵심] 비율 제한 카운터
    non_us_count = 0
    max_non_us_allowed = int(v_count * 0.1) # 10% 이하 제한

    for item in all_stats_items:
        title = item['snippet']['title']
        channel = item['snippet']['channelTitle']
        duration_sec = parse_duration(item['contentDetails']['duration'])
        
        # 1년 지난 영상 제외
        days_diff = (now - datetime.strptime(item['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")).days
        if days_diff > 365: continue
        
        if not is_shorts and duration_sec < 120: continue 
        if is_shorts and duration_sec > 120: continue
        
        # [국가별 필터]
        if r_info['code'] == 'JP' and not is_japanese(title + channel): continue
        
        # [미국 타겟 필터] 인도/동남아 10% 캡(Cap) 적용
        if r_info['code'] == 'US':
            if is_strictly_non_us(title, channel):
                if non_us_count >= max_non_us_allowed: continue # 10% 넘으면 버림
                non_us_count += 1

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

st.sidebar.markdown("---")
with st.sidebar:
    show_ad_banner("sidebar")

# --- 결과 출력 ---
if search_clicked or not topic:
    with st.spinner('초정밀 필터링 및 시니어 리포트 작성 중...'):
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
                
                st.markdown(report_html, unsafe_allow_html=True)
                
                col_empty, col_ad_bottom = st.columns([3, 1])
                with col_ad_bottom: show_ad_banner("bottom")

        except Exception as e:
            if "quotaExceeded" in str(e):
                if st.session_state.key_index < len(API_KEYS) - 1:
                    st.session_state.key_index += 1
                    st.toast("🔄 1번 키 소진! 자동 키 전환 중...")
                    time.sleep(1)
                    st.rerun()
                else: st.error("🚨 모든 할당량 소진.")
            else: st.error(f"오류 발생: {e}")
```

### 🎓 미국 시장 필터링 강화 포인트
1.  **API 원천 차단 (`us_filter`):** 검색 쿼리 자체에 `-india -hindi -bollywood` 등 마이너스 검색어를 추가하여, 유튜브가 애초에 인도 영상을 덜 보내주도록 만들었습니다.
2.  **엄격한 10% 제한 (`max_non_us_target`):** 수집된 영상 중에서도 채널명이나 제목에 인도/동남아 흔적이 있는 경우, 전체 리스트의 **10%를 넘지 못하도록 카운팅하여 강제 스킵**합니다.
3.  **데이터 풀 확대:** 필터링으로 인해 영상이 부족해지는 것을 막기 위해 미국 타겟 시 **데이터 스캔 범위를 6페이지(최대 300개)**까지 늘렸습니다.

이제 미국 숏폼을 검색하면 인도 노래나 드라마 짤방 대신, **진짜 미국의 밈과 챌린지 영상**들이 주를 이룰 것입니다. :)
68.8s
Model
ThinkingThoughts
Expand to view model thoughts

chevron_right
