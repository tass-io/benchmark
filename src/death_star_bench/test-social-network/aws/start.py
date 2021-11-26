import os, time, csv, json, subprocess, sys, random, threading
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

func_role = "arn:aws-cn:iam::648513213171:role/sail-serverless"
func_arn = "arn:aws-cn:lambda:cn-northwest-1:648513213171:function:"
stepfuncs_role = "arn:aws-cn:iam::648513213171:role/sail-step-functions"
stepfuncs_arn = "arn:aws-cn:states:cn-northwest-1:648513213171:stateMachine:"
log_arn = 'arn:aws-cn:logs:cn-northwest-1:648513213171:log-group:'
log_name_prefix = '/aws/vendedlogs/states/'
log_suffix = ':*'
log_mutex = threading.Lock()
logs_procc_num=0
logs_procc_num_max=50
stepfuncs_log_tepl = {
    "level": "ALL",
    "includeExecutionData": False,
    "destinations": [
        {
            "cloudWatchLogsLogGroup": {
                "logGroupArn": ""
            }
        }
    ]
}
errors = 0
succ_status = 'SUCCEEDED'

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
    return {"path": path, "exec": exec, "seed": seed, "depth": 0}

def wait_for_log():
    time.sleep(600) 

def cold_start_release(): # sleep 15min for warm resource released
    time.sleep(900) 

def wait():
    time.sleep(6)

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

def clear_all():
    sscmd("aws logs --profile linxuyalun delete-log-group --log-group-name %s%s" %(log_name_prefix, name))
    while not empty_cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep FunctionName | grep %s" %name):
        cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep FunctionName | grep %s | cut -d \\\" -f 4 | xargs -n1 -P0 -I{} aws lambda --profile linxuyalun delete-function --function-name {}" %name)
        wait()
    while not empty_cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep \\\"name\\\" | grep %s" %name):
        cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep \\\"name\\\" | grep %s | cut -d \\\" -f 4 | xargs -n1 -P0 -I{} aws stepfunctions delete-state-machine --profile linxuyalun --state-machine-arn %s{}" %(name, stepfuncs_arn))
        wait()

def create_machine():
    stepfuncs_log_conf = stepfuncs_log_tepl.copy()
    stepfuncs_log_conf['destinations'][0]['cloudWatchLogsLogGroup']['logGroupArn'] = "%s%s%s%s" %(log_arn, log_name_prefix, name, log_suffix)
    cmd("aws logs --profile linxuyalun create-log-group --log-group-name %s%s" %(log_name_prefix, name))
    cmd("aws stepfunctions create-state-machine --logging-configuration '%s' --profile linxuyalun --role-arn %s --definition file://stepfunctions --type EXPRESS --name %s" %(json.dumps(stepfuncs_log_conf), stepfuncs_role, name))
    # wait until machine created:
    while empty_cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep %s" %name):
        cmd("aws stepfunctions create-state-machine --logging-configuration '%s' --profile linxuyalun --role-arn %s --definition file://stepfunctions --type EXPRESS --name %s" %(json.dumps(stepfuncs_log_conf), stepfuncs_role, name))
        wait()

def create_function():
    for funcName in funcNames:
        cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 128 --role %s --zip-file fileb://code.zip --function-name %s-%s" %(func_role, name, funcName))
        # wait until function created:
        while empty_cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep %s-%s" %(name, funcName)):
            cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 128 --role %s --zip-file fileb://code.zip --function-name %s-%s" %(func_role, name, funcName))
            wait()

def deploy():
    # 清除所有的 lambda function 与 stepfunction machine
    clear_all()
    # 部署 lambda function，并部署 stepfunctions machine
    create_function()
    create_machine()

def get_res_from_log(invoke):
    global logs_procc_num
    # assure logs are completed logged
    wait_for_log()
    log_mutex.acquire()
    while logs_procc_num + 1 == logs_procc_num_max:
        log_mutex.release()
        wait_for_log()
        log_mutex.acquire()
    logs_procc_num += 1
    log_mutex.release()
    all_logged = False
    res = {}
    another_res = {}
    while not all_logged:
        try:
            res = json.loads(sscmd("""aws logs filter-log-events --profile linxuyalun --log-group-name '%s%s' --filter-pattern '{ $.execution_arn = "%s" && ( $.type = "ExecutionStarted" || $.type = "ExecutionSucceeded" ) }'""" %(log_name_prefix, name, invoke['execArn'])))
            if len(res['events']) != 2:
                raise Exception("len(events) is %d rather than 2" %(len(res['events'])))
            another_res = json.loads(scmd("""aws logs filter-log-events --profile linxuyalun --log-group-name '%s%s' --filter-pattern '{ $.execution_arn = "%s" && ( $.type = "LambdaFunctionScheduled" || $.type = "LambdaFunctionSucceeded" ) }'""" %(log_name_prefix, name, invoke['execArn'])))
            if len(another_res['events']) %2 != 0:
                raise Exception('ERROR! the log res len of the path is not a even number')
            all_logged = True
            break
        except Exception as e:
            print(e)
            wait_for_log()
    # get execution time of the whole stepfunctions
    for event in res['events']: event['message'] = json.loads(event['message'])
    res['events'].sort(key=lambda event: int(event['message']['id']))
    times = list(map(lambda event: int(event['message']['event_timestamp']), res['events']))
    execTime = times[1] - times[0]
    # get each function execution time and the function path 
    for event in another_res['events']: event['message'] = json.loads(event['message'])
    another_res['events'].sort(key=lambda event: int(event['message']['id']))
    times = list(map(lambda event: int(event['message']['event_timestamp']), another_res['events']))
    funcTimes = []
    last = -1
    for t in times:
        if last != -1:
            funcTimes.append(t-last) 
        last = t
    funcPath = list(map(lambda sevent: sevent['message']['details']['resource'][len(func_arn):], filter(lambda event: event['message']['type'] == 'LambdaFunctionScheduled', another_res['events'])))
    output =  {"execTime": execTime, "funcTimes": funcTimes, "funcPath": funcPath}
    invoke.update(output)
    log_mutex.acquire()
    logs_procc_num-=1
    log_mutex.release()
    print("I'm done!")

def req(param):
    global errors
    try:
        res = json.loads(scmd("aws stepfunctions start-sync-execution --profile linxuyalun --state-machine-arn %s%s --input '%s'" %(stepfuncs_arn, name, json.dumps(param))))
        status = res['status']
        if status != succ_status:
            errors = errors + 1
            print(status)
            return {"status": status}
        else:
            output = json.loads(res['output'])
            execArn = res['executionArn']
            return {"status": status, "execArn": execArn, "output": output}
    except Exception as e:
        print(e)
        return {"status": "FAILED"}

def must_req(param):
    res = req(param)
    while res['status'] != succ_status:
        print("=================\nA err req occured\n=================")
        res = req(param)
    return res

def init_results(n):
    results = []
    for i in range(n):
        results.append({"status": 0, "execTime": 0, "funcTimes": 0, "funcPath": 0, "output": 0})
    return results

def test_loop(loops, warmups, resFile):
    if loops != 0:  
        results = init_results(loops)
        log_threads = []
        for i in repeat(None, warmups):
            req(generate_param())
        for i in range(loops):
            if warmups == -1: # -1 warmups is recognized as cold test
                cold_start_release()
            param = generate_param()
            results[i].update(must_req(param))
            results[i]['designedFuncTimes'] = param['exec']
            results[i]['designedFuncPath'] = param['path']
            t = threading.Thread(target=get_res_from_log,args=[results[i]])
            t.start()
            log_threads.append(t)
        for thread in log_threads:
            thread.join()
        avgTime = validNum = 0
        resfile = open(resFile, 'w')
        writer = csv.writer(resfile, delimiter='@')
        writer.writerow(['execTime(ms)', 'status', 'funcTimes', 'funcPath', 'output', 'designedFuncTimes', 'designedFuncPath'])
        for result in results:
            if result['status'] == succ_status:
                avgTime += result['execTime']
                validNum = validNum + 1
            writer.writerow([result['execTime'], result['status'], result['funcTimes'], result['funcPath'], result['output'], result['designedFuncTimes'], result['designedFuncPath']])
        writer.writerow(["avgTime(ms)"])
        writer.writerow([avgTime / validNum])
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