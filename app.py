import requests
from requests import Session
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import re
from argparse import ArgumentParser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import smtplib
import os
from dotenv import load_dotenv
from flask import Flask, jsonify
import os

load_dotenv()

app = Flask(__name__)

@app.route('/')
def scraper():
    URL = 'https://www.vintepila.com.br/trabalhos-freelance/'
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'}

    def scrape_url(url: str, headers: Dict[str, str], session: Session) -> BeautifulSoup:
        response = session.get(url=url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup

    def get_urls(url: str, headers: Dict[str, str], session: Session) -> List[str]:
        links = []
        links.append(url)
        response = session.get(url=url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        try:
            max_page_index = soup.find('div', {'class': 'pagination'}).find_all('a')[-2].text
            
            for i in range(2, int(max_page_index)+1):
                links.append(f"{url}?page={i}")

            return links
        except Exception as error:
            print(error.__class__, error.__cause__)

    def scrape_data(links: List[str], terms: List[str], headers: Dict[str, str], session: Session) -> List[str]:
        results = []
        r_dict = {'link': [], 'title': [], 'desc': []}
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor_results = [executor.submit(scrape_url, link, headers, session) for link in links]
            for f in as_completed(executor_results):
                html = f.result()
                elements = html.findAll('div', {'class': 'content'})
                for element in elements:
                    try:
                        title = element.find('a', {'class': 'header'}, href=True)
                        desc = element.find('div', {'class': 'description'})
                        desc = desc.find('p')
                        number_of_candidates = element.find('div', {'class': 'extra'})
                        number_of_candidates = number_of_candidates.find('span', {'data-content': 'Número de candidatos concorrendo ao projeto '}).text
                        # os.system('pause')
                        for term in terms:
                            term = r"\b{}\b".format(re.escape(term))
                            if int(number_of_candidates) < 5:
                                if re.search(term, title.text) or re.search(term, desc.text):
                                    if title.get('href') not in results:
                                        results.append(title.get('href'))
                                        r_dict['link'].append(title.get('href'))
                                        r_dict['title'].append(title.text)
                                        r_dict['desc'].append(desc.text)


                    except AttributeError:
                        pass
            return r_dict
    terms = ["desenvolvedor", "programador", "programação", "desenvolvimento", "html", "css", "javascript", "python", "flask", "nextjs", "react", "sveltkit", "crawler", "crawller", "scraper", "scraping", "webscraping", "webscraper", "site", "sistema", "software"]


    with requests.Session() as session:
        print("Getting possible job links...")
        links = get_urls(url=URL, headers=HEADERS, session=session)
        r_dict = scrape_data(links=links, terms=terms, headers=HEADERS, session=session)

        inner = []

        for i in range(len(r_dict['link'])):
            inner.append(f"""
                        <section>
                            <div class="title">
                                <a href="{r_dict['link'][i]}"><h1>{r_dict['title'][i]}</h1></a>
                            </div>
                            <div class="desc">
                                <p>{r_dict['desc'][i]}</p>
                            </div>
                        </section>
                        <hr>
                    """)
        


        email_sender = os.getenv('EMAIL_SENDER')
        email_pass = os.getenv('SMTP_PASSWORD')
        email_reciever = os.getenv('EMAIL_RECIEVER')
        

        subject = 'Possíveis freelas no VintePila'

        content = ''.join(inner)

        body = """
        <!DOCTYPE html>
        <html lang="pt-br">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email</title>
        </head>
        <style>
            * {
                box-sizing: border-box;
                padding: 0;
                margin: 0;
            }
            section {
                font-family: Lucida Sans;
                display: flex;
                flex-wrap: wrap;
                flex-direction: column;
                box-shadow: -1px 1px 5px 1px;
                padding: 1rem;
                gap: 1rem;
            }

            .info {
                display: flex;
                gap: 1rem;
            }

            .title a{
                text-decoration: none;
                color: black;
            }

        </style>
        """ + f"""
        <body>
            <main>
                {content}
            </main>
        </body>
        </html>

        """


        em = MIMEMultipart('alternatives')

        em['From'] = email_sender
        em['To'] = email_reciever
        em['Subject'] = subject

    
        html_part = MIMEText(body, 'html')

        em.attach(html_part)

        context = ssl.create_default_context()


        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            print("Sending email...")
            smtp.login(email_sender, email_pass)
            smtp.sendmail(email_sender, email_reciever, em.as_string())
    
    
    return jsonify({
        "message": "Script executado com sucesso!"
    }), 200