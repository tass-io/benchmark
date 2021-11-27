import os, time, csv, random, subprocess, json, gc
from itertools import repeat

default_test_conf = {
    "payload_sizes": [0,1024,8192,16384,30720,35840,65536,131072,524288,1046528,1048576,2097152,4194304,8388608,16777216],
    "loop_times": 100,
    "warm_up_times": 5,
    "cold_times": 10,
    "res_file": "./result-%d.csv",
    "cold_res_file": "./cold-%d.csv"
}

name = "bench-03-passp"
param = '''{"workflowName": "%s", "flowName": "", "parameters": {"payload": ""}}''' %name
param_schema = {
    "workflowName": "%s" %name,
    "flowName": "",
    "parameters": {
        "payload": ""
    }
}
errors = 0
success = True

def cold_start_release(): # sleep 15min for warm resource released
    time.sleep(60)

def wait():
    time.sleep(10)

def sscmd(cmd):
    return subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8").stdout

def cmd(cmd):
    print(cmd)
    res = sscmd(cmd)
    print(res)
    return res

def scmd(cmd):
    print(cmd)
    return sscmd(cmd)

def clear_all():
    cmd("tass-cli function list | grep bench | awk '{print $2}' | xargs -n1 -I{} -P0 tass-cli function delete -n {}")
    cmd("kubectl get workflow | grep bench | awk '{print $1}' | xargs -n1 -I{} -P0 kubectl delete workflow {}")
    wait()

def post_json_file(url, filename):
    return scmd("curl --max-time 900 -s -S --header \"Content-Type: application/json\" --request POST --data @%s \"%s\"" %(filename, url))

def deploy():
    clear_all()
    # cli 部署函数
    cmd("tass-cli function create -c ./function/param-pass/plugin.so -n %s" %name)
    # 部署各种 yaml 文件
    cmd("kubectl apply -f ./function/param-pass/function.yaml -f ./workflow/param-pass/workflow.yaml")
    wait()

def create_json_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    sscmd("mkdir -p $(dirname %s)" %filepath)
    file = open(filepath, 'w')
    json.dump(object, file)
    file.close()

def generate_payload(payload):
    global param
    if payload == 0:
        param = '''{"workflowName": "%s", "flowName": "", "parameters": {"payload": ""}}''' %name
        return
    param_s = param_schema.copy()
    res = scmd('openssl rand -hex %d' %(payload/2))[:-1] # remove cmd tailling line break
    print("generated payload size: %d" %(len(res)))
    param_s['parameters']['payload'] = res
    param = json.dumps(param_s)
    gc.collect()

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
    global errors
    try:
        host = sscmd("kubectl get svc | grep %s | awk '{print $3}'" %name)[:-1]
        create_json_file(json.loads(param), './input.json')
        res = json.loads(post_json_file('http://%s/v1/workflow/' %host, "input.json"))
        execTime = parseTime(res['time'])
        status = res['success']
        if status != success:
            print(res)
            raise Exception('status == %s' %(str(status)))
        return status, execTime, len(str(res))
    except Exception as e:
        print(e)
        errors += 1
        return False, 0, 0

def must_req():
    status, execTime, resLen = req()
    while status != success:
        print("=================\nA err req occured\n=================")
        status, execTime, resLen = req()
    return status, execTime, resLen

def test_loop(loops, warmups, resFile, payload_size):
    if loops != 0:
        generate_payload(payload_size)  
        for i in repeat(None, warmups):
            req()
        resfile = open(resFile, 'w')
        writer = csv.writer(resfile, delimiter='@')
        writer.writerow(['execTime(µs)', 'status', 'resLen'])
        avgTime = validNum = 0
        for i in repeat(None, loops):
            if warmups == -1: # -1 warmups is recognized as cold test
                cold_start_release()
            status, execTime, resLen = must_req()
            if status == success:
                avgTime += execTime
                validNum += 1
            writer.writerow([execTime, status, resLen])
        writer.writerow(["avgTime(µs)"])
        writer.writerow([avgTime / validNum])
        resfile.close()

def test(conf):
    # warm tests
    for payload_size in conf["payload_sizes"]:
        test_loop(conf['loop_times'], conf['warm_up_times'], conf['res_file'] %payload_size,payload_size)
    # cold tests
    test_loop(conf['cold_times'], -1, conf['cold_res_file'] %(0), payload_size=0)

def get_model():
    sscmd('mkdir model')
    sscmd('mkdir data')
    scmd("kubectl cp $(kubectl get pod | grep %s | awk '{print $1}'):/tass/model ./model" %name)
    scmd("kubectl cp $(kubectl get pod | grep %s | awk '{print $1}'):/tass/data ./data" %name)

def do(input_conf):
    conf = default_test_conf.copy()
    conf.update(input_conf)
    deploy()
    test(conf)
    get_model()
    print("ERRORS REQS: %d. Automatically redo failed tests" %errors)

do({})