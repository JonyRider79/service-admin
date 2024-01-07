from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import json2html
import uvicorn
import requests
import zipfile
import os
import yaml
import json

with open('config.yml', encoding='utf-8') as fh:
    config = yaml.safe_load(fh)

version = '0.0.4'
filename = 'temp/script.zip'
path = 'temp/script/scripts/org'
username = config['username']
pass_bitbucket = config['pass_bitbucket']
pass_teemcity = config['pass_teemcity']
url = config['url_bitbucket']
head = """
        <html> <head> <title>Сервис админов!</title> </head>
            <body> 
            <h1>Сервис админов!</h1>
            Версия """ + version + """ <a href="/docs">(swagger)</a><br/><br/> """
back = """ <br/>            
            <form action="/">
                <input type="submit" value="Назад" />
            </form> </body> </html>"""

Branchs = config['Branchs']

app = FastAPI()


def CompareVersion (url, text, current):
    data = open(path+url, encoding='utf-8')
    file = url.split('/')[-1]
    for line in data:
        if text in line:
            line = line[:-1]
            if line == current:
                return {"Скрипт": f"{file}", "Актуально": "<center><font color=""green"">Да</font></center>", "bitbaket": f"{line}", "Текущая": f"{current}"}
            else:
                return {"Скрипт": f"{file}", "Актуально": "<center><font color=""red"">Нет</font></center>", "bitbaket": f"{line}", "Текущая": f"{current}"}
            break
    data.close()



@app.get("/", response_class=HTMLResponse)
def hello_index():
    html_content = head + """
            <form action="/sforms/">
                <input type="submit" value="Версии скриптов форм" />
            </form>
            <form action="/stends/">
                <input type="submit" value="Доступность стендов" />
            </form>
            <form action="/teamcity/">
                <input type="submit" value="Билды в TeamCity" />
            </form>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get ("/sforms/", response_class=HTMLResponse)
def script_forms():
    r = requests.get(url, auth=(username,pass_bitbucket))

    if r.status_code == 200:
        with open(filename, 'wb') as out:
            for bits in r.iter_content():
                out.write(bits)

    with zipfile.ZipFile(filename, 'r') as zip_ref:
        zip_ref.extractall(r'./temp/script/')
    answer = []
    for script in config['Scripts']:
        answer.append(CompareVersion(script['Path'], script['Search'], script['Version']))
    html_content = head + "<b>Проверка версий скриптов форм на bitbucket</b><br/><br/>"+ json2html.json2html.convert(json=answer, escape=False) + back
    return HTMLResponse(content=html_content, status_code=200)

@app.get ("/stends/", response_class=HTMLResponse)
def stends_alive():
    answer=[]
    for stend in config['Stends']:
        try:
            r = requests.get(stend['Path'], verify=False, timeout=0.2)
            if r.status_code == 200:
                answer.append({"Описание": f"{stend['Description']}","Стенд": f"{stend['Path']}", "Доступен": "<center><font color=""green"">Да</font></center>"})
            else:
                answer.append({"Описание": f"{stend['Description']}","Стенд": f"{stend['Path']}", "Доступен": f"{r.status_code}"})
        except requests.exceptions.ConnectTimeout:
            answer.append({"Описание": f"{stend['Description']}","Стенд": f"{stend['Path']}", "Доступен": "<center><font color=""red"">Нет</font></center>"})
        except requests.exceptions.ConnectionError:
            answer.append({"Описание": f"{stend['Description']}","Стенд": f"{stend['Path']}", "Доступен": "<center><font color=""red"">Нет</font></center>"})
    html_content = head + "<b>Проверка доступности стендов</b><br/><br/>"+json2html.json2html.convert(json=answer, escape=False) + back
    return HTMLResponse(content=html_content, status_code=200)

@app.get ("/teamcity/", response_class=HTMLResponse)
def build_teamcity():
    answer=[]
    for branch in config['Branchs']:
        r = requests.get("http://srv-tmct-ice-1.bft.local:8111/app/rest/builds/?locator=status:success,buildType:"+branch['Branch']+",count:1", auth=(username,pass_teemcity), headers={"Accept":"application/json"})
        if r.status_code != 200:
            answer = answer.append({"Билд": "-", "Дата": "-", "Ветка": f"{branch['Branch']}", "Ссылка": "-", "Артефакт": "-", "Стенды": f"{branch['Stends']}"})
        else:
            data=json.loads(r.text)
            number=data['build'][0]['number']
            branche=data['build'][0]['buildTypeId']
            finish=data['build'][0]['finishOnAgentDate']
            webUrl=data['build'][0]['webUrl']
            webUrl='<a href="'+webUrl+'">TeamCity</a>'
            appUrl='<a href="http://srv-tmct-ice-1.bft.local:8111/repository/download/'+branch['Branch']+'/'+str(data['build'][0]['id'])+':id/app.war">app.war</a>'
            fin_data = finish[6:8]+'.'+finish[4:6]+'.'+finish[0:4]
            answer.append({"Билд": f"{number}", "Дата": f"{fin_data}", "Ветка": f"{branche}", "Ссылка": f"{webUrl}","Артефакт": f"{appUrl}", "Стенды": f"{branch['Stends']}"})
    html_content = head + "<b>Последние, удачно собранные, билды по веткам в TeamCity</b><br/><br/>" + json2html.json2html.convert(json=answer, escape=False) + back
    return HTMLResponse(content=html_content, status_code=200)


@app.get ("/bbforms/", response_class=HTMLResponse)
def bb_forms():
    answer = []
    for script in config['Scripts']:
        spath=script['Path']
        r = requests.get("https://bitbucket.bftcom.com/rest/api/1.0/projects/D-SUD/repos/bftdsud-mdm-cl-volgograd/browse/scripts/org/"+script['Path']+"?at=release/0.1", auth=(username,pass_bitbucket))
        if r.status_code != 200:
            answer.append({"Скрипт": "-", "Актуально": "-", "Bitbaket": "-", "Текущая": f"{script['Version']}"})
        else:
            data = json.loads(r.content)
            for line in data['lines']:
                if script['Search'] in line['text']:
                    if line['text'] == script['Version']:
                        answer.append({"Скрипт": f"{spath}", "Актуально": "<center><font color=""green"">Да</font></center>", "Bitbaket": f"{line['text']}", "Текущая": f"{script['Version']}"})
                    else:
                        answer.append({"Скрипт": f"{script['Path']}", "Актуально": "<center><font color=""red"">Нет</font></center>","Bitbaket": f"{line['text']}", "Текущая": f"{script['Version']}"})
                    break
    html_content = head + "<b>Проверка версий скриптов форм на bitbucket</b><br/><br/>"+ json2html.json2html.convert(json=answer, escape=False) + back
    return HTMLResponse(content=html_content, status_code=200)


if __name__ == '__main__':
    if not os.path.exists('temp'):
        os.mkdir('temp')
    uvicorn.run ("main:app")