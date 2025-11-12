import os
import feedparser
import smtplib
from email.mime.text import MIMEText
from openai import OpenAI

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# 뉴스 RSS 목록
RSS_FEEDS = {
    "기독교": "https://www.christiantoday.co.kr/rss/",
    "정치": "https://rss.donga.com/politics.xml",
    "경제": "https://rss.donga.com/economy.xml",
    "사회": "https://rss.donga.com/society.xml",
    "과학": "https://rss.donga.com/science.xml",
    "교통": "https://rss.donga.com/national.xml",  # 교통 뉴스가 자주 포함됨
}

def fetch_news():
    news = []
    for category, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:  # 각 분야 3건씩
            news.append(f"[{category}] {entry.title}\n{entry.link}")
    return "\n\n".join(news)

def summarize_news(news_text):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 오늘의 한국 뉴스를 간결하게 요약하는 기자야."},
                {"role": "user", "content": f"다음 뉴스들을 5줄로 요약해줘:\n{news_text}"}
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] 요약 실패: {e}")
        # 요약 실패 시 헤드라인만 반환
        return "⚠️ 요약 생성에 실패했습니다. 아래는 주요 헤드라인입니다:\n\n" + news_text

def send_email(summary):
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    receiver = os.environ["EMAIL_RECEIVER"]

    msg = MIMEText(summary, "plain", "utf-8")
    msg["Subject"] = "📰 오늘의 뉴스 요약"
    msg["From"] = sender
    msg["To"] = receiver

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

if __name__ == "__main__":
    print("뉴스 수집 중...")
    news = fetch_news()

    print("요약 중...")
    summary = summarize_news(news)

    print("이메일 전송 중...")
    send_email(summary)

    print("✅ 완료!")
