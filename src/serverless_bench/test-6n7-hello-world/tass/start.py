import os, time, csv,subprocess, json
from itertools import repeat

default_test_conf = {
    "loop_times": 100,
    "warm_up_times": 5,
    "res_file": './result.csv',
    'cold_times': 10,
    'cold_res_file': './cold.csv'
}

name = "bench-01-hello"
param = {
    'name': 'tass-benchmark' 
}
param_schema = {
    "workflowName": "%s" %name,
    "flowName": "",
    "parameters": {}
}
success = True
errors = 0

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
    
def post_json(url, data):
    ps = param_schema.copy()
    ps['parameters'] = data
    return scmd("curl --max-time 900 -s -S --header \"Content-Type: application/json\" --request POST --data-raw \'%s\' \"%s\"" %(json.dumps(ps), url))

def deploy():
    clear_all()
    # cli 部署函数
    cmd("tass-cli function create -c ./function/hello/plugin.so -n %s" %name)
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
    global errors
    try:
        host=cmd("kubectl get svc | grep %s | awk '{print $3}'" %name)[:-1]
        res = json.loads(post_json('http://%s/v1/workflow/' %host, param.copy()))
        execTime = parseTime(res["time"])
        status = res['success']
        if status != success:
            print(res)
            raise Exception('status == %s' %(str(status)))
        return status, execTime, res
    except Exception as e:
        print(e)
        errors += 1
        return False, 0, 0

def must_req():
    status, execTime, res = req()
    while status != success:
        print("=================\nA err req occured\n=================")
        status, execTime, res = req()
    return status, execTime, res

def test_loop(loops, warmups, resFile):
    if loops != 0:    
        for i in repeat(None, warmups):
            req()
        resfile = open(resFile, 'w')
        writer = csv.writer(resfile, delimiter='@')
        writer.writerow(['execTime(µs)', 'status', 'res'])
        avgTime = validNum = 0
        for i in repeat(None, loops):
            if warmups == -1: # -1 warmups is recognized as cold test
                cold_start_release()
            status, execTime, res = must_req()
            if status == success:
                avgTime += execTime
                validNum += 1
            writer.writerow([execTime, status, res])
        writer.writerow(["avgTime(µs)"])
        writer.writerow([avgTime / validNum])
        resfile.close()

def test(conf):
    # warm tests
    test_loop(conf['loop_times'], conf['warm_up_times'], conf['res_file'])
    # cold tests
    test_loop(conf['cold_times'], -1, conf['cold_res_file'])

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