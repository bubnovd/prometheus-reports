import os
from flask import Flask, url_for, request, render_template, send_file
from markupsafe import escape
from datetime import datetime
from functions import get_prometheus_data, parsing_data, xls_export

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

@app.route('/download')
def download():
    return send_file('report.xlsx')

@app.route('/', methods=['POST', 'GET'])
def main():
    error = None
    device_type = None
    promapi = os.environ['PROMAPI']
    step = int(os.environ['STEP'])
    promauth = os.environ['PROMAUTH']
    promlogin = os.getenv('PROMLOGIN', 'promlogin')
    prompass = os.getenv('PROMPASS', 'prompass')
    label = "nb_name"
    if request.method == 'POST':
        device_type = request.form['device_type']
        start = request.form['start']
        end = request.form['end']
        if device_type is None:
            error = 'Тип оборудования не задан'
        elif start == '':
            error = 'Начало периода не задано'
            if end == '':
                error = 'Период не задан'
        elif end == '':
            error = 'Конец периода не задан'
        elif start > end:
            error = 'Период начинается позже, чем заканчивается'
        elif end > str(datetime.now()):
            error = 'Я не умею предсказывать будущее'
        
        if error is None:
            promquery =  'avg_over_time(probe_success{job="'+device_type+'"}[10m]) < 0.6'
            startday = datetime.strptime(start, '%Y-%m-%d').date()
            endday = datetime.strptime(end, '%Y-%m-%d').date()
            metrics_all = get_prometheus_data(promapi, promquery, startday, endday, step, label, promauth, promlogin, prompass) 
            result = parsing_data(metrics_all, label, step)
            xls_export(result) 
       
            return render_template('index.html', device_type=device_type, start=start, end=end, error=error, result=result)
        else:
            return render_template('index.html', device_type=device_type, error=error)
    else:
        return render_template('index.html', device_type=device_type, error=error)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
