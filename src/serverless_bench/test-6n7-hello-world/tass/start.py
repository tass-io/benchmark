import os, requests, time, csv
from itertools import repeat

default_test_conf = {
    "loop_times": 3,
    "warm_up_times": 1,
    "type": "warm",
    "res_file": './result.csv'
}

def deploy():
    # cli 部署函数
    print(os.popen("tass-cli function create -c ./function/hello/code.zip -n bench-01-hello").read())
    # 部署各种 yaml 文件
    print(os.popen("kubectl apply -f ./function/hello/function.yaml -f ./workflow/hello/workflow.yaml").read())
    # 创建 Ingress 路由
    print(os.popen("tass-cli route create -n bench-01-hello -p /bench/01/hello").read())
    
def req():
    benchTime = int(round(time.time() * 1000))
    res = requests.post(url='http://<TODO>/bench/01/hello', data={
        'name': 'tass-benchmark' 
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