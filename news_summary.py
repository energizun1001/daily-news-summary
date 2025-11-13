import os
import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from email.header import Header
from google import genai # genai 라이브러리 사용 전제

# --- Gemini API 클라이언트 설정 (생략) ---
client = None
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
except Exception as e:
    # 이전에 발생했던 오류는 여기서 처리되므로 별도의 ImportError 체크는 생략
    pass

# 뉴스 RSS 목록 (최종 버전 유지)
RSS_FEEDS = {
    # 🚨 주의: SBS/JTBC RSS는 모든 분야의 뉴스를 포함하는 경향이 있어 여러 카테고리에 중복 배치될 수 있습니다.
    "⚖️ 정치": [
        {"source": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/politics/?outputType=xml"},
        {"source": "동아일보", "url": "https://rss.donga.com/politics.xml"},
        {"source": "국민일보", "url": "https://www.kmib.co.kr/rss/data/kmibPolRss.xml"},
        {"source": "한국일보", "url": "https://rss.hankookilbo.com/hankookilbo/rss/hankookilbo_politics.xml"},
        {"source": "한겨레", "url": "http://www.hani.co.kr/rss/politics/"},
        {"source": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/politic_news.xml"}
    ],
    "📈 경제": [
        {"source": "조선일보", "https://www.chosun.com/arc/outboundfeeds/rss/category/economy/?outputType=xml"}
        {"source": "한국경제", "url": "https://www.hankyung.com/feed/economy"},
        {"source": "동아일보", "url": "https://rss.donga.com/economy.xml"},
        {"source": "국민일보", "url": "https://www.kmib.co.kr/rss/data/kmibEcoRss.xml"},
        {"source": "한국일보", "url": "https://rss.hankookilbo.com/hankookilbo/rss/hankookilbo_economy.xml"},
        {"source": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/economy_news.xml"},
        {"source": "머니투데이", "url": "http://rss.mt.co.kr/mt_rss.xml?section=economy"},
    ],
    "🧑‍🤝‍🧑 사회": [
        {"source": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/national/?outputType=xml"},
        {"source": "동아일보", "url": "https://rss.donga.com/society.xml"},
        {"source": "국민일보", "url": "https://www.kmib.co.kr/rss/data/kmibSocRss.xml"},
        {"source": "한국일보", "url": "https://rss.hankookilbo.com/hankookilbo/rss/hankookilbo_society.xml"},
        {"source": "한겨레", "url": "http://www.hani.co.kr/rss/society/"},
        {"source": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/society_news.xml"}
    ],
    "🏘️ 부동산": [
        {"source": "매일경제", "url": "https://www.mk.co.kr/rss/30100041/"},
        {"source": "한국경제", "url": "https://www.hankyung.com/feed/realestate"},
        {"source": "머니투데이", "url": "http://rss.mt.co.kr/mt_rss.xml?section=realestate"}, # 부동산 전용 피드로 추정
        {"source": "연합뉴스 (부동산)", "url": "http://www.yonhapnews.co.kr/RSS/l_economy.xml"}
    ],
    "🖼️ 문화": [
        {"source": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/culture-life/?outputType=xml"},
        {"source": "동아일보", "url": "https://rss.donga.com/culture.xml"},
        {"source": "한겨레", "url": "http://www.hani.co.kr/rss/culture/"}
    ],
    "🌎 국제": [
        {"source": "조선일보", "url": "https://www.chosun.com/arc/outboundfeeds/rss/category/international/?outputType=xml"},
        {"source": "동아일보", "url": "https://rss.donga.com/international.xml"},
        {"source": "한국일보", "url": "https://rss.hankookilbo.com/hankookilbo/rss/hankookilbo_international.xml"},
        {"source": "한겨레", "url": "http://www.hani.co.kr/rss/international/"},
        {"source": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/kh_world.xml"}
    ],
    "🧪 과학/교통": [
        {"source": "한국철도", "url": "https://www.redaily.co.kr/rss/allArticle.xml"}, # IT/과학 피드로 활용
        {"source": "경향신문", "url": "https://www.khan.co.kr/rss/rssdata/science_news.xml"}
    ],
    "💻 IT": [
        {"source": "ZDNet Korea", "url": "http://www.zdnet.co.kr/ArticleFeed.asp?type=xml"},
        {"source": "한국경제 (IT)", "url": "https://www.hankyung.com/feed/it"}
    ]
}


def fetch_news():
    ai_prompt_text = []
    # HTML 생성을 위해 원본 기사 목록을 딕셔너리 형태로 저장
    raw_articles_data = {} 
    
    for category, feeds in RSS_FEEDS.items():
        category_articles = []
        
        for feed_info in feeds:
            source_name = feed_info["source"]
            url = feed_info["url"]
            
            try:
                feed = feedparser.parse(url)
                articles_for_summary = []
                for entry in feed.entries[:3]: 
                    title = entry.title
                    link = entry.link
                    
                    articles_for_summary.append(f"- 제목: {title} (링크: {link})")
                    # 원본 기사 목록 HTML 생성을 위한 데이터 저장
                    category_articles.append({"title": title, "source": source_name, "link": link})
                    
                if articles_for_summary:
                    prompt_block = f"\n\n<언론사: {source_name} - {category}>\n" + "\n".join(articles_for_summary)
                    ai_prompt_text.append(prompt_block)

            except Exception as e:
                print(f"[ERROR] RSS 파싱 실패 ({source_name}): {e}")
                
        # 카테고리별 원본 기사 데이터를 딕셔너리에 추가
        raw_articles_data[category] = category_articles
            
    return "\n".join(ai_prompt_text), raw_articles_data


def summarize_news(news_text, raw_articles_data):
    if not client:
        summary_html = """
        <p style="color: red; font-weight: bold;">⚠️ Gemini API 클라이언트 초기화에 실패했습니다. API 키를 확인해 주세요. 요약은 생략됩니다.</p>
        """
        return summary_html + generate_raw_articles_html(raw_articles_data, is_summary_failed=True)
        
    prompt = f"""
    다음은 {datetime.now().strftime('%Y-%m-%d')} 기준, 다양한 언론사 및 카테고리별 뉴스 목록입니다.
    
    요청:
    1. 각 '<언론사: XXX - 카테고리>' 블록별로 기사의 주요 내용과 세부 논점을 포함하여 자세히 요약해줘.
    2. 요약은 최대한 상세하게 작성해줘. 길이가 길어져도 좋으니, 기사의 맥락과 세부 사항을 빠짐없이 전달해줘.
    3. 요약문은 명확히 [[언론사명 - 카테고리]] 형태로 구분해줘. 예: [[조선일보 - 정치]].
       주의: 이 [[...]] 부분은 절대 삭제하거나 변경해서는 안 됩니다.
    4. 새로운기사가 아니어도 좋으니까 일단 줘.
    
    뉴스 목록:
    {news_text}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        ai_summary = response.text.strip()
        
        # HTML 변환 및 원본 목록 추가
        summary_html = generate_summary_html(ai_summary)
        return summary_html + generate_raw_articles_html(raw_articles_data)
        
    except Exception as e:
        print(f"[ERROR] Gemini 요약 실패 (API 오류 등): {e}")
        summary_html = f"""
        <p style="color: red; font-weight: bold;">⚠️ Gemini API 호출에 실패했습니다. 요약은 생략됩니다.</p>
        """
        return summary_html + generate_raw_articles_html(raw_articles_data, is_summary_failed=True)


def generate_summary_html(summary_text):
    # [[언론사 - 카테고리]] 제목을 굵고 배경색을 넣은 스타일로 변환
    html_content = summary_text.replace('\n', '<br>')
    
    # 정규표현식 대신 간단한 replace로 처리 ([[...]] 패턴에 맞춤)
    # 예: [[조선일보 - 정치]] -> <h2><span class="summary-title">[[조선일보 - 정치]]</span></h2>
    # 요약 문단은 <p> 태그로 감싸지 않고 그냥 텍스트로 둡니다.

    # 1. 요약 제목 스타일 정의 (HTML 내부에 삽입)
    style = """
    <style>
        .summary-title {
            display: inline-block;
            background-color: #e0f7fa; /* 밝은 하늘색 배경 */
            color: #00796b; /* 진한 청록색 글씨 */
            font-weight: bold;
            padding: 5px 10px;
            margin-top: 15px;
            margin-bottom: 5px;
            border-radius: 5px;
            font-size: 1.1em;
            border-left: 5px solid #00acc1; /* 왼쪽 테두리 */
        }
    </style>
    """
    
    # 2. 요약 제목을 스타일링된 <h2> 태그로 감싸기
    lines = html_content.split('<br>')
    styled_lines = []
    for line in lines:
        if line.startswith('[['):
            # [[...]] 제목을 찾으면 스타일 적용
            styled_line = f'<h2><span class="summary-title">{line}</span></h2>'
            styled_lines.append(styled_line)
        elif line.strip():
            # 일반 텍스트는 <p> 태그로 감싸기
            styled_lines.append(f'<p style="margin-top: 5px; margin-left: 20px;">{line.strip()}</p>')
            
    return f"{style}<h1>📝 상세 뉴스 요약 ({datetime.now().strftime('%Y년 %m월 %d일')})</h1>" + "\n".join(styled_lines)


def generate_raw_articles_html(raw_articles_data, is_summary_failed=False):
    html_parts = [
        '<br><br><hr style="border: 2px solid #bdbdbd;">',
        '<h1>📰 원본 기사 목록 (수집 출처)</h1>',
        '<p style="color: gray;">' + ('(요약 실패 시 전체 목록)' if is_summary_failed else '(요약 성공 시 참고용 목록)') + '</p>'
    ]
    
    for category, articles in raw_articles_data.items():
        # 카테고리별 헤더
        html_parts.append(f'<h2><span style="color: #424242;">{category}</span></h2>')
        
        if not articles:
            html_parts.append('<p style="color: #ff9800;">- 해당 카테고리에서는 새로운 기사를 수집하지 못했습니다.</p>')
            continue
            
        # 기사 목록
        html_parts.append('<ul style="list-style-type: none; padding-left: 15px;">')
        for item in articles:
            # <li>에 링크와 출처 정보를 포함
            list_item = f"""
            <li style="margin-bottom: 10px;">
                <a href="{item['link']}" style="color: #1976d2; text-decoration: none; font-weight: bold;">{item['title']}</a><br>
                <span style="color: #616161; font-size: 0.9em;">(출처: {item['source']}, <a href="{item['link']}">바로가기</a>)</span>
            </li>
            """
            html_parts.append(list_item)
        html_parts.append('</ul>')

    return "".join(html_parts)

def send_email(subject, body):
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    receiver = os.environ["EMAIL_TO"]

    # MIMEText 타입을 'html'로 변경
    msg = MIMEText(body, "html", "utf-8") 
    
    msg["Subject"] = Header(subject, 'utf-8')
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

if __name__ == "__main__":
    print("뉴스 수집 및 파싱 중...")
    news_text, raw_articles_data = fetch_news()

    print("뉴스 요약 및 안전 검사 중...")
    summary_with_headlines_html = summarize_news(news_text, raw_articles_data)

    print("이메일 전송 중...")
    send_email(
        subject=f"📰 오늘의 관심사별 뉴스 요약 ({datetime.now().strftime('%Y-%m-%d')})",
        body=summary_with_headlines_html
    )

    print("✅ 모든 작업 완료!")


