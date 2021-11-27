import os, time, csv, json, subprocess, sys
from itertools import repeat

default_test_conf = {
    "loop_times": 100,
    "warm_up_times": 5,
    "cold_times": 10,
    'n':6,
    "res_file": './result.csv',
    "cold_res_file": './cold.csv'
}

name = "bench-02-chained"
param = '{"n":0}'

func_role = "arn:aws-cn:iam::648513213171:role/sail-serverless"
func_arn = "arn:aws-cn:lambda:cn-northwest-1:648513213171:function:"
stepfuncs_role = "arn:aws-cn:iam::648513213171:role/sail-step-functions"
stepfuncs_arn = "arn:aws-cn:states:cn-northwest-1:648513213171:stateMachine:"
log_arn = 'arn:aws-cn:logs:cn-northwest-1:648513213171:log-group:'
log_name_prefix = '/aws/vendedlogs/states/'
log_suffix = ':*'
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
machine_path = './stepfunctions'
errors = 0
succ_status = 'SUCCEEDED'


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

def create_json_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    sscmd("mkdir -p $(dirname %s)" %filepath)
    file = open(filepath, 'w')
    json.dump(object, file)
    file.close()

def create_machine(n):
    output = {
        "Comment": "Tass ServerlessBench test 2 - long chain",
        "StartAt": "%s1" %name,
        "TimeoutSeconds": 300, # maximum is 5 min
        "States": {}
    }
    state = {
        "Type": "Task",
        "Resource": "%s%s" %(func_arn, name),
        "Next": "%s" %name
    }
    for i in range(1, n + 1):
        elem = state.copy()
        elem['Resource'] += str(i)
        elem['Next'] += str(i + 1)
        output['States']['%s%d' %(name, i)] = elem
    output["States"]["bench-02-chained%d" %n]["End"] = True
    del output["States"]["bench-02-chained%d" %n]["Next"]
    create_json_file(output, machine_path)
    stepfuncs_log_conf = stepfuncs_log_tepl.copy()
    stepfuncs_log_conf['destinations'][0]['cloudWatchLogsLogGroup']['logGroupArn'] = "%s%s%s%s" %(log_arn, log_name_prefix, name, log_suffix)
    cmd("aws logs --profile linxuyalun create-log-group --log-group-name %s%s" %(log_name_prefix, name))
    cmd("aws stepfunctions create-state-machine --logging-configuration '%s' --profile linxuyalun --role-arn %s --definition file://stepfunctions --type EXPRESS --name %s" %(json.dumps(stepfuncs_log_conf), stepfuncs_role, name))
    # wait until machine created:
    while empty_cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep %s" %name):
        wait()

def create_function(n):
    for i in range(1, n + 1):
        cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 128 --role %s --zip-file fileb://code.zip --function-name %s%d" %(func_role, name, i))
        # wait until function created:
        while empty_cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep %s%d" %(name, i)):
            wait()

def deploy(conf):
    # 清除所有的 lambda function 与 stepfunction machine
    clear_all()
    # 部署 lambda function，创建 machine 文件，并部署 stepfunctions machine
    create_function(int(conf['n']))
    create_machine(int(conf['n']))

def get_res_from_log(exec_arn):
    # assure logs are completed logged
    all_logged = False
    while not all_logged:
        try:
            res = json.loads(sscmd("""aws logs filter-log-events --profile linxuyalun --log-group-name '%s%s' --filter-pattern '{ $.execution_arn = "%s" && ( $.type = "ExecutionStarted" || $.type = "ExecutionSucceeded" ) }'""" %(log_name_prefix, name, exec_arn)))
            if len(res['events']) != 2:
                raise Exception("len(events) is %d rather than 2" %(len(res['events'])))
            all_logged = True
            break
        except:
            print("waiting for logging finished get err:", sys.exc_info()[0])
            wait()
    # get execution time of the whole stepfunctions
    res = json.loads(scmd("""aws logs filter-log-events --profile linxuyalun --log-group-name '%s%s' --filter-pattern '{ $.execution_arn = "%s" && ( $.type = "ExecutionStarted" || $.type = "ExecutionSucceeded" ) }'""" %(log_name_prefix, name, exec_arn)))
    for event in res['events']: event['message'] = json.loads(event['message'])
    res['events'].sort(key=lambda event: int(event['message']['id']))
    times = list(map(lambda event: int(event['message']['event_timestamp']), res['events']))
    execTime = times[1] - times[0]
    # get each function execution time and the function path 
    res = json.loads(scmd("""aws logs filter-log-events --profile linxuyalun --log-group-name '%s%s' --filter-pattern '{ $.execution_arn = "%s" && ( $.type = "LambdaFunctionScheduled" || $.type = "LambdaFunctionSucceeded" ) }'""" %(log_name_prefix, name, exec_arn)))
    for event in res['events']: event['message'] = json.loads(event['message'])
    res['events'].sort(key=lambda event: int(event['message']['id']))
    times = list(map(lambda event: int(event['message']['event_timestamp']), res['events']))
    funcTimes = []
    last = -1
    for t in times:
        if last != -1:
            funcTimes.append(t-last) 
        last = t
    funcPath = list(map(lambda sevent: sevent['message']['details']['resource'][len(func_arn):], filter(lambda event: event['message']['type'] == 'LambdaFunctionScheduled', res['events'])))
    return {"execTime": execTime, "funcTimes": funcTimes, "funcPath": funcPath}

def req():
    global errors
    try:
        res = json.loads(scmd("aws stepfunctions start-sync-execution --profile linxuyalun --state-machine-arn %s%s --input '%s'" %(stepfuncs_arn, name, param)))
        status = res['status']
        if status != succ_status:
            errors = errors + 1
            print(status)
            return {"status": status}
        else:
            output = json.loads(res['output'])
            execArn = res['executionArn']
            return {"status": status, "execArn": execArn, "output": output}
    except:
        return {"status": "FAILED"}

def must_req():
    res = req()
    while res['status'] != succ_status:
        print("=================\nA err req occured\n=================")
        res = req()
    return res

def init_results(n):
    results = []
    for i in range(n):
        results.append({"status": 0, "execTime": 0, "funcTimes": 0, "funcPath": 0, "output": 0})
    return results

def test_loop(loops, warmups, resFile):
    if loops != 0:  
        results = init_results(loops)
        for i in repeat(None, warmups):
            req()
        for i in range(loops):
            if warmups == -1: # -1 warmups is recognized as cold test
                cold_start_release()
            results[i].update(must_req())
        results[0]['execTime'] = "okidoki"
        avgTime = validNum = 0
        resfile = open(resFile, 'w')
        writer = csv.writer(resfile, delimiter='@')
        writer.writerow(['execTime(ms)', 'status', 'funcTimes', 'funcPath', 'output'])
        for result in results:
            if result['status'] == succ_status:
                result.update(get_res_from_log(result['execArn']))
                avgTime += result['execTime']
                validNum = validNum + 1
            writer.writerow([result['execTime'], result['status'], result['funcTimes'], result['funcPath'], result['output']])
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