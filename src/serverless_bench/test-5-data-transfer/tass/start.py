import os, requests, time, csv, random
from itertools import repeat

default_test_conf = {
    "payload_sizes": [0,1024,5120,10240,15360,20480,25600,30720,35840,40960,46080,51200],
    "res_file": './result.csv'
}

def deploy():
    # cli 部署函数
    print(os.popen("tass-cli function create -c ./function/param-pass/code.zip -n bench-03-passp").read())
    # 部署各种 yaml 文件
    print(os.popen("kubectl apply -f ./function/param-pass/function.yaml -f ./workflow/param-pass/workflow.yaml").read())
    # 创建 Ingress 路由
    print(os.popen("tass-cli route create -n bench-03-passp -p /bench/03/passp").read())


def generate_payload(payload):
    return random.sample('zyxwvutsrqponmlkjihgfedcba', payload)

def req(payload):
    benchTime = int(round(time.time() * 1000))
    res = requests.post(url='http://<TODO>/bench/03/passp', data={
        "payload": generate_payload(payload)
    })
    endTime = int(round(time.time() * 1000))
    res = res.json()
    startTime = int(res['startTime'])
    return benchTime, startTime, endTime

def test(input_conf):
    conf = default_test_conf.copy()
    conf.update(input_conf)
    csvfile = open(conf['res_file'], 'w')
    writer = csv.writer(csvfile, delimiter=',')
    writer.writerow(['benchTime', 'startTime', 'endTime'])
    for payload in conf["payload_sizes"]:
        benchTime, startTime, endTime = req(int(payload))
        writer.writerow([benchTime, startTime, endTime])
    csvfile.close()