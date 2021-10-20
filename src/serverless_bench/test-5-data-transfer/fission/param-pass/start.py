import os, requests, time, csv, random
from itertools import repeat

default_test_conf = {
    "payload_sizes": [0,1024,5120,10240,15360,20480,25600,30720,35840,40960,46080,51200],
    "res_file": './result.csv'
}

def deploy():
    # TODO: 如果没有 go env，创建一个
    # cli 部署函数
    print(os.popen("fission fn create --name bench-03-passp --env go --src main.go --entrypoint Handler --maxmemory 128").read())
    # cli 部署 workflow
    print(os.popen("fission fn create --name bench-03-passpwf --env workflow --src ./workflow.wf.yaml").read())
    # 部署 http trigger
    print(os.popen("fission httptrigger create --method POST --url \"bench/03/passp\" --function bench-03-passpwf").read())


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