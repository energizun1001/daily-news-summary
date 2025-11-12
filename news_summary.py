import os
import feedparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from email.header import Header

# --- Gemini API 라이브러리 및 클라이언트 설정 ---
# pip install google-genai 
try:
    from google import genai
except ImportError:
    print("[FATAL ERROR] 'google-genai' 라이브러리가 설치되지 않았습니다. pip install google-genai를 실행해주세요.")
    genai = None

client = None
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key and genai:
        client = genai.Client(api_key=api_key)
except Exception as e:
    print(f"[FATAL ERROR] Gemini Client 초기화 실패: {e}")

# 뉴스 RSS 목록 (기존과 동일)
# ... (RSS_FEEDS 딕셔너리 내용은 이전 코드와 동일하게 유지됩니다) ...
RSS_FEEDS = {
    "📌 기독교/신앙": [
        {"source": "크리스천투데이", "url": "https://www.christiantoday.co.kr/rss/"}
    ],
    "⚖️ 정치 (보수/중도/진보)": [
        {"source": "조선일보 (보수)", "url": "http://rss.chosun.com/site/data/rss/politics.xml"},
        {"source": "동아일보 (보수)", "url": "https://rss.donga.com/politics.xml"},
        {"source": "국민일보 (보수)", "url": "https://www.kmib.co.kr/rss/data/kmibPolRss.xml"},
        {"source": "한국일보 (중도)", "url": "https://rss.hankookilbo.com/hankookilbo/rss/hankookilbo_politics.xml"},
        {"source": "경향신문 (진보)", "url": "https://www.khan.co.kr/rss/rss_section.html?section=pol"},
        {"source": "한겨레 (진보)", "url": "http://www.hani.co.kr/rss/politics/"}
    ],
    "📈 경제/부동산": [
        {"source": "매일경제 (부동산)", "url": "https://www.mk.co.kr/rss/30100041/"},
        {"source": "한국경제 (부동산)", "url": "https://www.hankyung.com/feed"},
        {"source": "동아일보 (경제)", "url": "https://rss.donga.com/economy.xml"},
        {"source": "국민일보 (경제)", "url": "https://www.kmib.co.kr/rss/data/kmibEcoRss.xml"},
        {"source": "한국일보 (경제)", "url": "https://rss.hankookilbo.com/hankookilbo/rss/hankookilbo_economy.xml"},
        {"source": "경향신문 (경제)", "url": "https://www.khan.co.kr/rss/rss_section.html?section=eco"},
        {"source": "머니투데이 (부동산)", "url": "http://rss.mt.co.kr/mt_rss.xml?section=economy"},
    ],
    "🧑‍🤝‍🧑 사회/이슈": [
        {"source": "조선일보 (사회)", "url": "http://rss.chosun.com/site/data/rss/rss_social.xml"},
        {"source": "동아일보 (사회)", "url": "https://rss.donga.com/society.xml"},
        {"source": "국민일보 (사회)", "url": "https://www.kmib.co.kr/rss/data/kmibSocRss.xml"},
        {"source": "한국일보 (사회)", "url": "https://rss.hankookilbo.com/hankookilbo/rss/hankookilbo_society.xml"},
        {"source": "경향신문 (사회)", "url": "https://www.khan.co.kr/rss/rss_section.html?section=soc"},
        {"source": "한겨레 (사회)", "url": "http://www.hani.co.kr/rss/society/"}
    ],
    "🧪 과학/기술/교통": [
        {"source": "ZDNet Korea (IT)", "url": "http://www.zdnet.co.kr/ArticleFeed.asp?type=xml"},
        {"source": "연합뉴스 (생활/교통)", "url": "http://www.yonhapnews.co.kr/RSS/l_society.xml"}
    ]
}


def fetch_news():
    # 이 부분은 동일
    ai_prompt_text = []
    full_headlines_list = []
    
    for category, feeds in RSS_FEEDS.items():
        category_articles = []
        full_headlines_list.append(f"\n\n\n========================================\n{category} - 원본 기사 목록\n========================================")
        
        for feed_info in feeds:
            source_name = feed_info["source"]
            url = feed_info["url"]
            
            try:
                feed = feedparser.parse(url)
                articles_for_summary = []
                for i, entry in enumerate(feed.entries[:3]): 
                    title = entry.title
                    link = entry.link
                    
                    articles_for_summary.append(f"- 제목: {title} (링크: {link})")
                    category_articles.append(f"- {title}\n  (출처: {source_name}, 링크: {link})")
                    
                if articles_for_summary:
                    prompt_block = f"\n\n<언론사: {source_name} - {category}>\n" + "\n".join(articles_for_summary)
                    ai_prompt_text.append(prompt_block)

            except Exception as e:
                print(f"[ERROR] RSS 파싱 실패 ({source_name}): {e}")
                
        full_headlines_list.append("\n".join(category_articles))
            
    return "\n".join(ai_prompt_text), "\n".join(full_headlines_list)

def summarize_news(news_text, full_headlines_list):
    if not client:
        summary_body = "⚠️ Gemini API 클라이언트 초기화 실패. API 키나 라이브러리를 확인해주세요. 요약은 생략됩니다."
        return summary_body + full_headlines_list
        
    prompt = f"""
    다음은 {datetime.now().strftime('%Y-%m-%d')} 기준, 다양한 언론사 및 카테고리별 뉴스 목록입니다.
    
    요청:
    1. 각 '<언론사: XXX - 카테고리>' 블록별로 핵심 논점을 정확히 집어내서 요약해줘.
    2. 요약은 충분한 정보를 전달하되 간결하게 작성하며, 줄 수 제한은 없어.
    3. 요약문은 명확히 [[언론사명 - 카테고리]] 형태로 구분해줘. 예: [[조선일보 - 정치]]
    
    뉴스 목록:
    {news_text}
    """
    try:
        # --- Gemini API 호출 부분 ---
        response = client.models.generate_content(
            model="gemini-2.5-flash", # 빠르고 효율적인 모델 사용
            contents=prompt
        )
        ai_summary = response.text.strip()
        
        if not ai_summary:
            raise Exception("Gemini 모델이 빈 응답을 반환했습니다.")

        return f"✅ Gemini AI 요약 성공!\n\n" + ai_summary + full_headlines_list
        
    except Exception as e:
        print(f"[ERROR] Gemini 요약 실패 (API 오류 등): {e}")
        # 요약 실패 시 예외 처리 메시지 뒤에 원본 헤드라인 목록을 붙여서 반환
        summary_body = "⚠️ Gemini API 호출에 실패했습니다. API 사용 한도를 확인해 주세요. 요약은 생략됩니다."
        return summary_body + full_headlines_list

def send_email(subject, body):
    # 이 부분은 동일
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    receiver = os.environ["EMAIL_TO"]

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, 'utf-8')
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

if __name__ == "__main__":
    print("뉴스 수집 및 파싱 중...")
    news_text, full_headlines_list = fetch_news()

    print("뉴스 요약 및 안전 검사 중...")
    summary_with_headlines = summarize_news(news_text, full_headlines_list)

    print("이메일 전송 중...")
    send_email(
        subject=f"📰 오늘의 관심사별 뉴스 요약 ({datetime.now().strftime('%Y-%m-%d')})",
        body=summary_with_headlines
    )

    print("✅ 모든 작업 완료!")
