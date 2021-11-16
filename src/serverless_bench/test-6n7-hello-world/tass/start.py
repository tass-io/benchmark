import os, time, csv,subprocess, json
from itertools import repeat

default_test_conf = {
    "loop_times": 100,
    "warm_up_times": 5,
    "res_file": './result.csv',
    'cold_times': 10,
    'cold_res_file': './cold.csv'
}

def cold_start_release(): # sleep 15min for warm resource released
    time.sleep(60)

def wait():
    time.sleep(10)

def cmd(cmd):
    print(cmd)
    res = subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8").stdout
    print(res)
    return res

def clear_all():
    cmd("tass-cli function list | grep bench | awk '{print $2}' | xargs -n1 -I{} -P0 tass-cli function delete -n {}")
    cmd("kubectl get workflow | grep bench | awk '{print $1}' | xargs -n1 -I{} -P0 kubectl delete workflow {}")
    wait()
    
def post_json(url, data):
    data = {
        "workflowName": "bench-01-hello",
        "flowName": "",
        "parameters": data
    }
    return cmd("curl --connect-timeout 900 -s -S --header \"Content-Type: application/json\" --request POST --data-raw \'%s\' \"%s\"" %(json.dumps(data), url))

def deploy():
    clear_all()
    # cli 部署函数
    cmd("tass-cli function create -c ./function/hello/code.zip -n bench-01-hello")
    # 部署各种 yaml 文件
    cmd("kubectl apply -f ./function/hello/function.yaml -f ./workflow/hello/workflow.yaml")
    wait()

def parseTime(timeStr):
    res = -1
    if timeStr[-2:] == 'µs':
        res = int(float(timeStr[:-2]))
    elif timeStr[-2:] == 'ms':
        res = int(float(timeStr[:-2]) * 1000) 
    elif timeStr[-1:] == 's':
        res = int(float(timeStr[:-1]) * 1000 * 1000) 
    elif timeStr[-1:] == 'm':
        res = int(float(timeStr[:-1]) * 1000 * 1000 * 60) 
    else:
        raise ValueError('Not supported time end from %s' %(timeStr))
    return res

def req():
    host=cmd("kubectl get svc | grep bench-01-hello | awk '{print $3}'")[:-1]
    res = json.loads(post_json('http://%s/v1/workflow/' %host, {
        'name': 'tass-benchmark' 
    }))
    execTime = parseTime(res["time"])
    return execTime, res

def test(conf):
    # warm tests
    if conf['loop_times'] != 0:
        for i in repeat(None, conf['warm_up_times']):
            req()
        csvfile = open(conf['res_file'], 'w')
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(['execTime(µs)', 'res'])
        avgTime=0
        for i in repeat(None, conf['loop_times']):
            execTime, res = req()
            avgTime += execTime
            writer.writerow([execTime, res])
        writer.writerow([avgTime / conf['loop_times']])
        csvfile.close()
    # cold tests
    if conf['cold_times'] != 0:
        resfile = open(conf['cold_res_file'], 'w')
        writer = csv.writer(resfile, delimiter=',')
        writer.writerow(['execTime(µs)', 'res'])
        cavgTime = 0
        for i in repeat(None, conf['cold_times']):
            cold_start_release()
            execTime, res = req()
            cavgTime += execTime
            writer.writerow([execTime, res])
        writer.writerow([cavgTime / conf['cold_times']])
        print("Cold Start Avg Time: %d µs (%d - %d) " %(cavgTime-avgTime, cavgTime, avgTime))
        resfile.close()

def do(input_conf):
    conf = default_test_conf.copy()
    conf.update(input_conf)
    deploy()
    test(conf)

do({})