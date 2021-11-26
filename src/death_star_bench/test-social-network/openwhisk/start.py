import time, csv, json, subprocess, random, threading, os
from itertools import repeat

default_test_conf = {
    "loop_times": 1000,
    "warm_up_times": 400,
    "cold_times": 100,
    "res_file": './result.csv',
    "cold_res_file": './cold.csv'
}

name = "bench-07-social"
seed = 7 << 14 # seed will grow as test proceed (in generate_param())
probTable = [[[0.08,1],[0.48,2],[0.8,3],[1,4]],[],[[0.5,5],[0.8,6],[0.9,7],[1,8]],[[1,10]],[],[[1,9]],[[1,9]],[[1,9]],[[1,9]],[[1,10]],[]]
funcNames = ['nginx', 'search', 'make-post', 'read-timeline', 'follow', 'text', 'media', 'user-tag', 'url-shortener', 'compose-post', 'post-storage']
funcTimes = [[20,0.1],[370,0.1],[37,0.1],[4,0.1],[11,0.1],[60,0.1],[40,0.1],[36,0.1],[32,0.1],[186,0.1],[5,0.1]]

param_filename = "./param.json"
param = "--param-file %s" %param_filename
success_status = True
cli_success_status = "ok"
errors = 0

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

def empty_cmd(cmd):
    return len(sscmd(cmd)) == 0

def create_json_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    file = open(filepath, 'w')
    json.dump(object, file)
    file.close()

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
    p = {"path": path, "exec": exec, "seed": seed, "depth": 0}
    create_json_file(p, param_filename) 
    return p

def cold_start_release(): # sleep 15min for warm resource released
    print("wait until all resource released")
    sscmd("""while [ -n "$(kubectl get pod -A | grep wskowdev-invoker | grep bench | awk '{print $2}')" ]; do sleep 30; done""")

def wait():
    time.sleep(1)

def create_conduct():
    cmd("wsk -i action update %s conductor.js -a conductor true" %name)

def create_action():
    for funcName in funcNames:
        cmd("wsk -i action update %s-%s main.go --memory 512 --timeout 300000" %(name, funcName))

def deploy():
    create_action()
    create_conduct()

def req():
    wait() # openwhisk can req one function at much 60 times a minute
    global errors
    try:
        res = scmd("wsk -i action invoke %s %s -b" %(name, param))
        cli_status = res.split("\n",1)[0].split(" ",1)[0][:-1]
        if cli_status != cli_success_status:
            print(res)
            raise Exception('cli_status == %s' %cli_status)
        activation = json.loads(res.split("\n",1)[-1][:-1])
        status = activation['response']['success']
        if status != success_status:
            print(res)
            raise Exception('status == %s' %(str(status)))
        result = len(json.dumps(activation['response']['result']))
        duration = activation['end'] - activation['start'] 
        waitTime = list(filter(lambda annotation: annotation['key'] == "waitTime",activation['annotations']))[0]["value"]
        return status, duration, waitTime, result
    except Exception as e:
        print(e)
        errors += 1
        return False, 0, 0, 0

def must_req(cold):
    status, duration, waitTime, result = req()
    while status != success_status:
        if cold == True:
            cold_start_release()
        print("=================\nA err req occured\n=================")
        status, duration, waitTime, result = req()
    return status, duration, waitTime, result


def test_loop(loops, warmups, resFile):
    if loops != 0:    
        for i in repeat(None, warmups):
            generate_param()
            req()
        resfile = open(resFile, 'w')
        writer = csv.writer(resfile, delimiter='@')
        writer.writerow(['execTime(ms)', 'waitTime(s)(ms)', 'status', 'designedFuncTimes', 'designedFuncPath', 'res'])
        avgTime = validNum = avgWaitTime = 0
        for i in repeat(None, loops):
            if warmups == -1: # -1 warmups is recognized as cold test
                cold_start_release()
            p = generate_param()
            status, execTime, waitTime, res = must_req(warmups == -1)
            if status == success_status:
                avgWaitTime += waitTime
                avgTime += execTime
                validNum += 1
            writer.writerow([execTime, waitTime, status, p['exec'], p['path'], res])
        writer.writerow(["avgTime(ms)", "avgWaitTime(ms)"])
        writer.writerow([avgTime / validNum, avgWaitTime / validNum])
        resfile.close()

def test(conf):  
    # warm tests
    test_loop(conf['loop_times'], conf['warm_up_times'], conf['res_file'])
    # cold tests
    test_loop(conf['cold_times'], -1, conf['cold_res_file'])

def do(input_conf):
    conf = default_test_conf.copy()
    conf.update(input_conf)
    print("Configuration:", conf)
    random.seed(seed)
    deploy()
    test(conf)
    print("ERRORS REQS: %d. Automatically redo failed tests" %errors)

do({})
