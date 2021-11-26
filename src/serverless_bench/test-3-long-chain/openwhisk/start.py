import os, time, csv, subprocess, json
from itertools import repeat

default_test_conf = {
    "loop_times": 100,
    "warm_up_times": 5,
    'n': 6,
    "res_file": './result.csv',
    'cold_times': 10,
    'cold_res_file': './cold.csv'
}

name = "bench-02-chained"
param = "--param n %d"
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

def cold_start_release(): # sleep about 15min for warm resource released
    print("wait until all resource released")
    sscmd("""while [ -n "$(kubectl get pod -A | grep wskowdev-invoker | grep bench | awk '{print $2}')" ]; do sleep 30; done""")

def wait():
    time.sleep(1)

def create_sequence(n):
    if n > 1:
        sequence = ""
        for i in range(1, n+1):
            sequence = "%s%s%d," %(sequence, name, i)
        cmd("wsk -i action update %s --sequence %s --timeout 300000" %(name, sequence[:-1]))
    

def create_actions(n):
    if n == 1:
        cmd("wsk -i action update %s main.go --memory 128 --timeout 300000" %name)
    else:
        for i in range(1, n+1):
            cmd("wsk -i action update %s%d main.go --memory 128 --timeout 300000" %(name, i))

def deploy(conf):
    create_actions(int(conf['n']))
    create_sequence(int(conf['n']))
    wait()

def req():
    wait() # openwhisk can req one function at much 60 times a minute
    global errors
    try:
        res = scmd("wsk -i action invoke %s %s -b" %(name, param %(0)))
        cli_status = res.split("\n",1)[0].split(" ",1)[0][:-1]
        if cli_status != cli_success_status:
            print(res)
            raise Exception('cli_status == %s' %cli_status)
        activation = json.loads(res.split("\n",1)[-1][:-1])
        status = activation['response']['success']
        if status != success_status:
            print(res)
            raise Exception('status == %s' %(str(status)))
        result = json.dumps(activation['response']['result'])
        duration = activation['end'] - activation['start'] 
        waitTime = list(filter(lambda annotation: annotation['key'] == "waitTime",activation['annotations']))[0]["value"]
        return status, duration, waitTime, result
    except Exception as e:
        print(e)
        errors += 1
        return False, 0, 0, 0

def must_req():
    status, duration, waitTime, result = req()
    while status != success_status:
        print("=================\nA err req occured\n=================")
        status, duration, waitTime, result = req()
    return status, duration, waitTime, result

def test_loop(loops, warmups, resFile):
    if loops != 0:    
        for i in repeat(None, warmups):
            req()
        resfile = open(resFile, 'w')
        writer = csv.writer(resfile, delimiter='@')
        writer.writerow(['execTime(ms)', 'waitTime(s)(ms)', 'status', 'res'])
        avgTime = validNum = avgWaitTime = 0
        for i in repeat(None, loops):
            if warmups == -1: # -1 warmups is recognized as cold test
                cold_start_release()
            status, execTime, waitTime, res = must_req()
            if status == success_status:
                avgWaitTime += waitTime
                avgTime += execTime
                validNum += 1
            writer.writerow([execTime, waitTime, status, res])
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
    deploy(conf)
    test(conf)
    print("ERRORS REQS: %d. Automatically redo failed tests" %errors)

resfn = './result-%d.csv'
coldfn = './cold-%d.csv'

for i in range(1, 7):
    do({
        "n": i,
        "res_file": resfn %i,
        "cold_res_file": coldfn %i
    })