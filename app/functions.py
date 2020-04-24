from pprint import pprint
import requests
import datetime
import copy
import progressbar
import xlsxwriter

def int_day_to_str(date):
    if len(str(date)) == 1:
        date = "0" + str(date)
    else:
        date = str(date)
    return date


def get_prometheus_data(promapi, promquery, startday, endday, step, label, promauth=False, user=None, password=None):
    '''
    Запрашивает данные у Prometheus API. Запрос - query, в указанный месяц и промежуток дат
    Отдает словарь label:[values]
    '''
    if promauth:
        promlogin = user
        prompass = password 
        auth = requests.auth.HTTPBasicAuth(promlogin, prompass)
    
    pbar = progressbar.ProgressBar(maxval=len(range((endday - startday).days))).start()
    iter = 0
    metrics_all = {}
    for day in range(startday.day, endday.day):
        mday = int_day_to_str(day)
    
        start = "2020-{}-{}T00:00:00.000Z".format(int_day_to_str(startday.month), mday)
        end = "2020-{}-{}T23:59:59.999Z".format(int_day_to_str(endday.month), mday)
        params = {
                    "start": start,
                    "end": end,
                    "step": str(step) + "s",
                    "query": promquery
        }
        if promauth:
            r = requests.get(promapi, auth=auth, params=params)
        else:
            r = requests.get(promapi, params=params)
    
        data = r.json()
        metrics = data["data"]["result"]
        for metric in metrics:
            if label in metric["metric"].keys():
                 if metric["metric"][label] not in metrics_all.keys():
                     metrics_all[metric["metric"][label]] = metric["values"]
                 else:
                     metrics_all[metric["metric"][label]].extend(metric["values"])
    
        iter += 1
        pbar.update(iter)
    return metrics_all


def parsing_data(metrics_all, label, step):
    '''
    Аггрегирует все метрики с одинаковым значением в одну
    Отдает список словарей [{label:label, outages:[start, end, duration], count, total_outage_time}]
    '''
    evstart = None
    result = []
    device_outage = {}
    for key, metrics in metrics_all.items():
        prev = None
        for metric in metrics:
            if key != device_outage.get(label):
                device_outage = {}
                device_outage[label] = key
                device_outage["outages"] = []
                outage = {}
                total_outage_time = 0
            timestamp = metric[0]
            if not evstart:
                evstart = timestamp
            evend = timestamp
            if not prev:
                outage = {}
                start = evstart
                end = evstart
            else:
                if timestamp - prev > step:
                    total_outage_time += duration
                    device_outage["outages"].append(outage)
                    evstart = metric[0]
                    outage = {}
                    start = evstart
                    end = evend
                    evstart = None  
                else:
                    evend = timestamp
                    end = evend
                    evstart = None
    
            prev = evend
            duration = end - start
            outage["start"] = datetime.datetime.fromtimestamp(start).isoformat()
            outage["end"] = datetime.datetime.fromtimestamp(end).isoformat()
            outage["duration"] = duration
    

        total_outage_time += duration
        device_outage["outages"].append(outage)
        max_outage = max(device_outage["outages"], key=lambda outages: outages["duration"])
        device_outage["max_outage"] = max_outage["duration"]
        device_outage["count"] = len(device_outage["outages"])
        device_outage["total_outage_time"] = total_outage_time
        result.append(device_outage)
    return result


def xls_export(data):
    workbook = xlsxwriter.Workbook("report.xlsx")
    worksheet = workbook.add_worksheet()
    row = 0
    col = 0    
    for key in data[0].keys():
        worksheet.write(row, col, key)
        col += 1
    row += 1
    for device in data:
        for key in device.keys():
            if key in ["total_outage_time", "max_outage"]:
                device[key] /= 60
        col = 0
        for value in device.values():
            worksheet.write(row, col, str(value))
            col += 1
        row += 1

    workbook.close()


if __name__ == "__main__":
    with open('config.yml') as f:
        config = yaml.load(f)
    promapi = config["promapi"]
    promquery = config["promquery"]
    step = config["step"]
    outputfile = config["outputfile"]
    promauth = config["promauth"]
    promlogin = config["promlogin"]
    prompass = config["prompass"]
    startday = config["startday"]
    endday = config["endday"]
    label = "nb_name"
       
    metrics_all = get_prometheus_data(promapi, promquery, startday, endday, step, label, promauth, promlogin, prompass) 

    result = parsing_data(metrics_all, label, step) 
    xls_export(result)
#    with open(outputfile, 'w') as f:
#        writer = csv.DictWriter(f, fieldnames=result[0].keys())
#        writer.writeheader()
#        for device in result:
#            writer.writerow(device)
    
