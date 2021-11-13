import os, time, csv, json, subprocess
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
machine_path = './stepfunctions'
errors = 0
succ_status = 'SUCCEEDED'


def cold_start_release(): # sleep 15min for warm resource released
    time.sleep(900)

def wait():
    time.sleep(6)

def cmd(cmd):
    print(cmd)
    res = subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8").stdout
    print(res)
    return res

def empty_str(str):
    return len(str) == 0

def clear_all():
    while not empty_str(cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep FunctionName | grep %s" %name)):
        cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep FunctionName | grep %s | cut -d \\\" -f 4 | xargs -n1 -P0 -I{} aws lambda --profile linxuyalun delete-function --function-name {}" %name)
        wait()
    while not empty_str(cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep \\\"name\\\" | grep %s" %name)):
        cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep \\\"name\\\" | grep %s | cut -d \\\" -f 4 | xargs -n1 -P0 -I{} aws stepfunctions delete-state-machine --profile linxuyalun --state-machine-arn %s{}" %(name, stepfuncs_arn))
        wait()

def create_json_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
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
    cmd("aws stepfunctions create-state-machine --profile linxuyalun --role-arn %s --definition file://stepfunctions --type EXPRESS --name %s" %(stepfuncs_role, name))
    # wait until machine created:
    while empty_str(cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep %s" %name)):
        wait()

def create_function(n):
    for i in range(1, n + 1):
        cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 128 --role %s --zip-file fileb://code.zip --function-name %s%d" %(func_role, name, i))
        # wait until function created:
        while empty_str(cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep %s%d" %(name, i))):
            wait()

def deploy(conf):
    # 清除所有的 lambda function 与 stepfunction machine
    clear_all()
    # 部署 lambda function，创建 machine 文件，并部署 stepfunctions machine
    create_function(int(conf['n']))
    create_machine(int(conf['n']))

def req():
    global errors
    benchTime = int(round(time.time() * 1000))
    res = cmd("aws stepfunctions start-sync-execution --profile linxuyalun --state-machine-arn %s%s --input '%s'" %(stepfuncs_arn, name, param))
    endTime = int(round(time.time() * 1000))
    res = json.loads(res)
    startTimes = []
    status = res['status']
    if status != succ_status:
        errors = errors + 1
        print(res['status'])
    else:
        output = json.loads(res['output'])
        startTimes = output['startTimes']
    return benchTime, startTimes, endTime, status

<<<<<<< HEAD
def test(conf):  
    # warm tests  
    if conf['loop_times'] != 0:    
        for i in repeat(None, conf['warm_up_times']):
            req()
        resfile = open(conf['res_file'], 'w')
        writer = csv.writer(resfile, delimiter=',')
        writer.writerow(['benchTime', 'startTimes', 'endTime'])
        avgTime = 0
        for i in repeat(None, conf['loop_times']):
            benchTime, startTimes, endTime, status = req()
            if status == succ_status:
                writer.writerow([benchTime, startTimes, endTime])
                avgTime += endTime - benchTime
        writer.writerow([avgTime / conf['loop_times']])
        resfile.close()
=======
def test(conf):
    # warm tests
    for i in repeat(None, conf['warm_up_times']):
        req()
    resfile = open(conf['res_file'], 'w')
    writer = csv.writer(resfile, delimiter=',')
    writer.writerow(['benchTime', 'startTimes', 'endTime'])
    avgTime = 0
    for i in repeat(None, conf['loop_times']):
        benchTime, startTimes, endTime, status = req()
        if status == succ_status:
            writer.writerow([benchTime, startTimes, endTime])
            avgTime += endTime - benchTime
    writer.writerow([avgTime / conf['loop_times']])
    resfile.close()
>>>>>>> 35da037467e73b8fa76001a8619eec3dec9fab16
    # cold tests
    if conf['cold_times'] != 0:
        resfile = open(conf['cold_res_file'], 'w')
        writer = csv.writer(resfile, delimiter=',')
        writer.writerow(['benchTime', 'startTimes', 'endTime'])
        cavgTime = 0
        for i in repeat(None, conf['cold_times']):
            cold_start_release()
            benchTime, startTimes, endTime, status = req()
            if status == succ_status:
                writer.writerow([benchTime, startTimes, endTime])
                cavgTime += endTime - benchTime
        writer.writerow([cavgTime / conf['cold_times']])
        print("Cold Start Avg Time: %d ms (%d - %d) " %(cavgTime-avgTime, cavgTime, avgTime))
        resfile.close()

def do(input_conf):
    conf = default_test_conf.copy()
    conf.update(input_conf)
    deploy(conf)
    test(conf)
    print("ERRORS REQS: %d" %errors)

do({})