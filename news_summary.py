import feedparser
import smtplib
from email.mime.text import MIMEText
from openai import OpenAI
from datetime import datetime
import os

# ==== 1. API 및 이메일 정보 ====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

client = OpenAI(api_key=OPENAI_API_KEY)

# ==== 2. 뉴스 RSS 피드 ====
rss_urls = [
    "https://rss.joins.com/joins_news_list.xml",  # 중앙일보
    "https://www.hankyung.com/feed",              # 한국경제
    "https://rss.donga.com/total.xml",            # 동아일보
]

def get_latest_news():
    articles = []
    for url in rss_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:
            articles.append(f"{entry.title} ({entry.link})")
    return "\n".join(articles)

# ==== 3. ChatGPT 요약 ====
def summarize_news(news_text):
    prompt = f"""
다음은 {datetime.now().strftime('%Y-%m-%d')} 한국 주요 뉴스 목록입니다.
핵심 내용을 5줄 이내로 간결하게 요약해줘:

{news_text}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()

# ==== 4. 이메일 발송 ====
def send_email(subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

# ==== 5. 실행 ====
if __name__ == "__main__":
    news = get_latest_news()
    summary = summarize_news(news)
    send_email(
        subject=f"🗞 오늘의 뉴스 요약 ({datetime.now().strftime('%Y-%m-%d')})",
        body=summary
    )
    print("메일 발송 완료!")
