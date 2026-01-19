<!-- 유튜브 채널 갤러리 디자인 -->
<style>
    .yt-gallery { 
        display: grid; 
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); 
        gap: 20px; 
        padding: 20px 0; 
        font-family: 'Apple SD Gothic Neo', sans-serif;
    }
    .yt-card { 
        background: white; 
        border-radius: 12px; 
        border: 1px solid #eef0f2; 
        padding: 12px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
        transition: 0.3s ease; 
    }
    .yt-card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); }
    .yt-thumb { width: 100%; aspect-ratio: 16/9; border-radius: 8px; object-fit: cover; cursor: pointer; }
    .yt-title { 
        font-size: 15px; font-weight: bold; color: #111; margin: 12px 0 8px; line-height: 1.4; 
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; height: 42px;
    }
    .yt-meta { font-size: 12px; color: #777; border-top: 1px solid #f5f5f5; padding-top: 10px; line-height: 1.6; }
    .yt-stats { color: #ff4b4b; font-weight: bold; }
</style>

<div id="youtube-list" class="yt-gallery">
    <p style="text-align:center; width:100%;">콘텐츠를 실시간으로 불러오고 있습니다...</p>
</div>

<script>
    // 할당량 소진에 대비해 주현님의 3번 키로 세팅했어.
    const API_KEY = "AIzaSyCANj0BHbejmyaxFR7TLbOggOeykQe3-a8"; 
    const CHANNEL_ID = "UCBvwIQnt7nRglFUPB40kUwg"; // 요청하신 채널 ID (UC 접두사 추가)
    const MAX_RESULTS = 12; 

    async function fetchMyVideos() {
        try {
            // 1. 채널의 최신 영상 목록 가져오기
            const searchUrl = `https://www.googleapis.com/youtube/v3/search?key=${API_KEY}&channelId=${CHANNEL_ID}&part=snippet,id&order=date&maxResults=${MAX_RESULTS}&type=video`;
            const res = await fetch(searchUrl);
            const data = await res.json();

            if (data.error) {
                if (data.error.errors[0].reason === "quotaExceeded") {
                    throw new Error("API 한도 초과! 다음 키를 사용하거나 내일 다시 시도해.");
                }
                throw new Error(data.error.message);
            }

            if (!data.items || data.items.length === 0) throw new Error("불러올 영상이 없어. ID를 다시 확인해봐.");

            const videoIds = data.items.map(item => item.id.videoId).join(',');

            // 2. 영상의 상세 통계(조회수) 가져오기
            const statsUrl = `https://www.googleapis.com/youtube/v3/videos?key=${API_KEY}&id=${videoIds}&part=snippet,statistics`;
            const statsRes = await fetch(statsUrl);
            const statsData = await statsRes.json();

            const container = document.getElementById('youtube-list');
            container.innerHTML = ''; 

            statsData.items.forEach(video => {
                const title = video.snippet.title;
                const thumb = video.snippet.thumbnails.high.url;
                const views = parseInt(video.statistics.viewCount).toLocaleString();
                const date = video.snippet.publishedAt.split('T')[0];
                const videoId = video.id;

                const card = `
                    <div class="yt-card">
                        <a href="https://www.youtube.com/watch?v=${videoId}" target="_blank">
                            <img src="${thumb}" class="yt-thumb" alt="${title}">
                        </a>
                        <div class="yt-title">${title}</div>
                        <div class="yt-meta">
                            📅 공개일: ${date} <br>
                            👀 조회수: <span class="yt-stats">${views}회</span>
                        </div>
                    </div>
                `;
                container.innerHTML += card;
            });
        } catch (error) {
            document.getElementById('youtube-list').innerHTML = `<p style="color:#888; text-align:center; padding: 50px;">안내: ${error.message}</p>`;
        }
    }

    fetchMyVideos();
</script>
