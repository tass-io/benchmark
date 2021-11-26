import os, time, csv, random, subprocess, json, gc
from itertools import repeat

default_test_conf = {
    "loop_times":1000,
    "warm_up_times": 400,
    "cold_times": 100,
    "res_file": './result.csv',
    'cold_res_file': './cold.csv',
    
}

name = "bench-05-hotel"
seed = 5 << 14 # seed will grow as test proceed (in generate_param())
probTable = [[[0.95,1],[1,2]],[[1,3]],[],[[1,4]],[]]
funcNames = ['nginx','check-reservation','make-reservation','get-profiles','search']
funcTimes = [[13,0.1],[220,0.1],[329,0.1],[34,0.1],[310,0.1]]
inner_param_schema = {
    "path": [],
    "exec": [],
    "depth": 0
}
param_schema = {
    "workflowName": "%s" %name, 
    "flowName": "",
    "parameters": {}
}
success = True
errors = 0

def get_random_exec(funcTime):
    return random.gauss(funcTime[0], funcTime[0]*funcTime[1])

def generate_param():
    global seed
    seed += 1
    path = [funcNames[0]]
    exec = [0, get_random_exec(funcTimes[0])] # set a offset to make time work
    cur = 0
    while True:
        if len(probTable[cur]) == 0:
            # The last function will get value from this, too
            path.append("placeholder")
            break 
        p_cur = 0
        r = random.random()
        while True:
            if p_cur == len(probTable[cur]):
                p_cur -= 1
                break
            if r < probTable[cur][p_cur][0]:
                break
            p_cur += 1
        cur = probTable[cur][p_cur][1]
        path.append(funcNames[cur])
        exec.append(get_random_exec(funcTimes[cur]))
    return {"path": path, "exec": exec, "seed": seed}
    
def get_param_str(param):
    ps = param_schema.copy()
    ps['parameters'] = inner_param_schema.copy()
    ps['parameters'].update(param)
    return json.dumps(ps)

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

def post_json(url, param):
    return scmd("""curl --max-time 900 -s -S --header "Content-Type: application/json" --request POST --data-raw '%s' "%s" """ %(get_param_str(param), url))

def deploy():
    clear_all()
    # 部署函数
    cmd("cd ./function; ls | while IFS= read -r i; do tass-cli function create -c ./$i/plugin.so -n %s-$i && kubectl apply -f ./$i/function.yaml; done" %name)
    # 部署工作流
    cmd("kubectl apply -f ./workflow/hotel/workflow.yaml")
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

def req(param):
    global errors
    try:
        host = sscmd("kubectl get svc | grep %s | awk '{print $3}'" %name)[:-1]
        res = json.loads(post_json('http://%s/v1/workflow/' %host, param))
        execTime = parseTime(res['time'])
        status = res['success']
        if status != success:
            print(res)
            raise Exception("status == %s" %status)
        return status, execTime, res
    except Exception as e:
        print(e)
        errors += 1
        return False, 0, 0

def must_req(param):
    status, execTime, res = req(param)
    while status != success:
        print("=================\nA err req occured\n=================")
        status, execTime, res = req(param)
    return status, execTime, res

def test_loop(loops, warmups, resFile):
    if loops != 0:    
        for i in repeat(None, warmups):
            req(generate_param())
        resfile = open(resFile, 'w')
        writer = csv.writer(resfile, delimiter='@')
        writer.writerow(['execTime(µs)', 'status', 'designedFuncTimes', 'designedFuncPath', 'res'])
        avgTime = validNum = 0
        for i in repeat(None, loops):
            if warmups == -1: # -1 warmups is recognized as cold test
                cold_start_release()
            param = generate_param()
            status, execTime, res = must_req(param)
            if status == success:
                avgTime += execTime
                validNum += 1
            writer.writerow([execTime, status, param['exec'], param['path'], res])
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
    random.seed(seed)
    deploy()
    test(conf)
    get_model()
    print("ERRORS REQS: %d. Automatically redo failed tests" %errors)

do({})