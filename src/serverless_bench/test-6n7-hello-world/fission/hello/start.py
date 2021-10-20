import os, requests, time, csv
from itertools import repeat

default_test_conf = {
    "loop_times": 3,
    "warm_up_times": 1,
    "type": "warm",
    "res_file": './result.csv'
}

def deploy():
    # TODO: 如果没有 go env，创建一个
    # cli 部署函数
    print(os.popen("fission fn create --name bench-01-hello --env go --src main.go --entrypoint Handler --maxmemory 128").read())
    # 部署 http trigger
    print(os.popen("fission httptrigger create --method POST --url \"bench/01/hello\" --function bench-01-hello").read())
    
def req():
    benchTime = int(round(time.time() * 1000))
    res = requests.get(url='http://<TODO>/bench/01', data = {
            "name": "tass-benchmark"
    })
    res = res.json()
    endTime = int(round(time.time() * 1000))
    startTime = int(res['startTime'])
    return benchTime, startTime, endTime

def test(input_conf):
    conf = default_test_conf.copy()
    conf.update(input_conf)
    if conf['type'] == 'warm':
        for i in repeat(None, conf['warm_up_times']):
            req()
    csvfile = open(conf['res_file'], 'w')
    writer = csv.writer(csvfile, delimiter=',')
    writer.writerow(['benchTime', 'startTime', 'endTime'])
    for i in repeat(None, conf['loop_times']):
        benchTime, startTime, endTime = req()
        writer.writerow([benchTime, startTime, endTime])
    csvfile.close()