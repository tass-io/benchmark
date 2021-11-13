import os, time, csv, random, subprocess, json, gc
from itertools import repeat

default_test_conf = {
    "payload_sizes": [0,1024,8192,16384,30720,35840,65536,131072,524288,1046528,1048576,2097152,16777216,134217728],
    "loop_times": 100,
    "warm_up_times": 5,
    "cold_times": 10
}

param = '{"workflowName": "bench-03-passp", "flowName": "", "parameters": {"payload": ""}}'
param_schema = {
    "workflowName": "bench-03-passp",
    "flowName": "",
    "parameters": {
        "payload": ""
    }
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

def empty_str(str):
    return len(str) == 0

def clear_all():
    cmd("tass-cli function list | grep bench | awk '{print $2}' | xargs -n1 -I{} -P0 tass-cli function delete -n {}")
    cmd("kubectl get workflow | grep bench | awk '{print $1}' | xargs -n1 -I{} -P0 kubectl delete workflow {}")
    wait()

def post_json_file(url, filename):
    cmd = "curl --connect-timeout 900 -s -S --header \"Content-Type: application/json\" --request POST --data @%s \"%s\"" %(filename, url)
    print(cmd)
    res = subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8").stdout
    return res

def deploy():
    clear_all()
    # cli 部署函数
    cmd("tass-cli function create -c ./function/param-pass/code.zip -n bench-03-passp")
    # 部署各种 yaml 文件
    cmd("kubectl apply -f ./function/param-pass/function.yaml -f ./workflow/param-pass/workflow.yaml")
    wait()

def create_json_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    file = open(filepath, 'w')
    json.dump(object, file)
    file.close()

def generate_payload(payload):
    global param
    if payload == 0:
        param = '{"workflowName": "bench-03-passp", "flowName": "", "parameters": {"payload": ""}}'
        return
    param_s = param_schema.copy()
    cmd = 'openssl rand -hex %d' %(payload/2)
    print(cmd)
    res = subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8").stdout
    res = res[:-1] # remove cmd tailling line break
    print("generated payload size: %d" %(len(res)))
    param_s['parameters']['payload'] = res
    param = json.dumps(param_s)
    gc.collect()

def req():
    host=cmd("kubectl get svc | grep bench-03-passp | awk '{print $3}'")[:-1]
    benchTime = int(round(time.time() * 1000))
    create_json_file(json.loads(param), './input.json')
    res = post_json_file('http://%s/v1/workflow/' %host, "input.json")
    endTime = int(round(time.time() * 1000))
    return benchTime, endTime, len(res)

def test(conf):
    for payload_size in conf["payload_sizes"]:
        generate_payload(payload_size)
        # warm tests   
        if conf['loop_times'] != 0:    
            for i in repeat(None, conf['warm_up_times']):
                req()
            resfile = open("./result%d.csv" %payload_size, 'w')
            writer = csv.writer(resfile, delimiter=',')
            writer.writerow(['benchTime', 'endTime', 'len(res)'])
            avgTime = 0
            for i in repeat(None, conf['loop_times']):
                benchTime, endTime, res = req()
                avgTime += endTime - benchTime
                writer.writerow([benchTime, endTime, res])
            writer.writerow([avgTime / conf['loop_times']])
            resfile.close()
    generate_payload(0)
    # cold tests
    if conf['cold_times'] != 0:
        resfile = open("./cold0.csv", 'w')
        writer = csv.writer(resfile, delimiter=',')
        writer.writerow(['benchTime', 'endTime', 'len(res)'])
        cavgTime = 0
        for i in repeat(None, conf['cold_times']):
            cold_start_release()
            benchTime, endTime, res = req()
            cavgTime += endTime - benchTime
            writer.writerow([benchTime, endTime, res])
        writer.writerow([cavgTime / conf['cold_times']])
        print("Cold Start Avg Time: %d ms (%d - %d) " %(cavgTime-avgTime, cavgTime, avgTime))
        resfile.close()

def do(input_conf):
    conf = default_test_conf.copy()
    conf.update(input_conf)
    deploy()
    test(conf)

do({})