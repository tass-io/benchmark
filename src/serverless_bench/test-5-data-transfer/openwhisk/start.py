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
param = "--param-file ./payload.json"
param_schema = {
    "payload": ""
}
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

def cold_start_release(): # sleep 15min for warm resource released
    print("wait until all resource released")
    sscmd("""while [ -n "$(kubectl get pod -A | grep wskowdev-invoker | grep bench | awk '{print $2}')" ]; do sleep 30; done""")

def wait():
    time.sleep(1)

def create_json_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    sscmd("mkdir -p $(dirname %s)" %filepath)
    file = open(filepath, 'w')
    json.dump(object, file)
    file.close()

def create_sequence():
    sequence = ""
    for i in range(1,3):
        sequence = "%s%s%d," %(sequence, name, i)
    cmd("wsk -i action update %s --sequence %s --timeout 300000" %(name, sequence[:-1]))

def create_actions():
    for i in range(1,3):
        cmd("wsk -i action update %s%i ./main-bin.zip --main main --docker openwhisk/action-golang-v1.16:nightly --memory 512 --timeout 300000" %(name, i))

def deploy():
    create_actions()
    create_sequence()
    wait()

def generate_payload(payload):
    global param
    if payload == 0:
        param ='''--param payload ""'''
        return
    p = param_schema.copy()
    res = scmd('openssl rand -hex %d' %(payload/2))[:-1] # remove cmd tailling line break
    print("generated payload size: %d" %(len(res)))
    sscmd("rm -rf ./payload.json")
    param = "--param-file ./payload.json"
    p['payload'] = res
    create_json_file(p, "./payload.json")
    if len(res) >= 1*1024*1024:
        scmd("redis-cli -h $(kubectl get svc -o custom-columns=IP:.spec.clusterIP redis | grep -v IP) -p 6379 -n 0 -x set param0 < ./payload.json")
        p['payload'] = "redis"
        create_json_file(p, "./payload.json")
    gc.collect()

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

def must_req():
    status, duration, waitTime, result = req()
    while status != success_status:
        print("=================\nA err req occured\n=================")
        status, duration, waitTime, result = req()
    return status, duration, waitTime, result

def test_loop(loops, warmups, resFile, payload_size):
    if loops != 0:
        generate_payload(payload_size)
        for i in repeat(None, warmups):
            req()
        resfile = open(resFile, 'w')
        writer = csv.writer(resfile, delimiter='@')
        writer.writerow(['execTime(ms)', 'waitTime(ms)', 'status', 'resLen'])
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
    for payload_size in conf["payload_sizes"]:
        test_loop(conf['loop_times'], conf['warm_up_times'], conf['res_file'] %payload_size, payload_size)
    # cold tests
    test_loop(conf['cold_times'], -1, conf['cold_res_file'] %(0), payload_size=0)

def do(input_conf):
    conf = default_test_conf.copy()
    conf.update(input_conf)
    deploy()
    test(conf)
    print("ERRORS REQS: %d. Automatically redo failed tests" %errors)

do({})