from flask import Flask, jsonify, request, render_template
from db import get_db_connection
import urllib.request
from bs4 import BeautifulSoup
import ssl
import re

app = Flask(__name__)
context = ssl._create_unverified_context()

def get_news(category):
    url = f"https://www.joongang.co.kr/{category}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req, context=context).read()
    soup = BeautifulSoup(html, 'html.parser')
    
    story_list = soup.select_one('.story_list')
    if not story_list:
        return []
    
    articles = story_list.select('li')
    items = []
    
    db = get_db_connection()
    cursor = db.cursor()

    for i in articles:
        headline = i.select_one('.headline') #제목       
        description = i.select_one('.description') #내용
        date = i.select_one('.meta p') # 날짜
        link_tag = i.select_one('.headline a')
        link = link_tag['href'] if link_tag and link_tag.has_attr('href') else'' #링크

        if headline and description and date: #and link: #3 요소가 있을 때만 데이터 추출
            title = re.sub(r'\s+', ' ', headline.text).strip() #re.sub(r'\s+', ' ', ..) = 공백 줄이기
            description = re.sub(r'\s+', ' ', description.text).strip() #.strip() = 앞 뒤 공백 제거 
            date = re.sub(r'\s+', ' ', date.text).strip()
            
            #데이터 중복 검사
            check_sql = "SELECT COUNT(*) FROM news WHERE title = %s AND date = %s" #title + date 조합이 같으면 중복처리
            cursor.execute(check_sql, (title, date)) 
            result = cursor.fetchone()

            #중복되는 데이터가 없을 때만 INSERT..
            if result[0] == 0:
              sql = "INSERT INTO news (category, title, description, date, link) VALUES (%s, %s, %s, %s,  %s)"
              val = (category, title, description, date, link)
              cursor.execute(sql, val)

            # 프론트로 보낼 데이터 저장
            items.append({
                'title': title,
                'description': description,
                'date': date,
                'link' : link
            })

    db.commit() #db에 영구 저장
    cursor.close() #커서 종료
    db.close() #db 종료
    return items

@app.route('/')
def home():
    return render_template('index.html') #홈페이지에 접근하면 index.html로 반환

# ✅ 여기에 추가
@app.route('/get_news')
def get_news_route():
    category = request.args.get('category') 
    if not category:
        return jsonify({'error': '없는 카테고리'}), 400 #json으로 반환

    news = get_news(category) #get_news 함수 실행 
    return jsonify(news) #json으로 html로 보냄

if __name__ == '__main__':
    app.run(port=5000, debug=True)
