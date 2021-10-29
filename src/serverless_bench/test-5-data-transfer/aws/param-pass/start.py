import os, time, csv, json, subprocess, random
from itertools import repeat

default_test_conf = {
    "payload_sizes": [0,1024,5120,10240,15360,20480,25600,30720,35840,40960,46080,51200],
    "loop_times": 1,
    "warm_up_times": 1,
    "cold_times": 1
}

name = "bench-03-passp"
param = '{"payload":""}'

func_role = "arn:aws-cn:iam::648513213171:role/sail-serverless"
func_arn = "arn:aws-cn:lambda:cn-northwest-1:648513213171:function:"
stepfuncs_role = "arn:aws-cn:iam::648513213171:role/sail-step-functions"
stepfuncs_arn = "arn:aws-cn:states:cn-northwest-1:648513213171:stateMachine:"
machine_path = './stepfunctions'
errors = 0
succ_status = 'SUCCEEDED'

def generate_payload(payload):
    global param
    param = json.loads(param)
    for i in repeat(None, payload):
        param['payload'] = param['payload'].join(random.sample('zyxwvutsrqponmlkjihgfedcba', 1))
    param = json.dumps(param)

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

def create_machine():
    output = {
        "Comment": "Tass ServerlessBench test 3 - param passing",
        "StartAt": "%s1" %name,
        "TimeoutSeconds": 300, # maximum is 5 min
        "States": {
            "%s1" %name: {
                "Type": "Task",
                "Resource": "%s%s1" %(func_arn, name),
                "Next": "%s2" %name
            },
            "%s2" %name: {
                "Type": "Task",
                "Resource": "%s%s2" %(func_arn, name),
                "End": True
            }
        }
    }
    create_json_file(output, machine_path)
    cmd("aws stepfunctions create-state-machine --profile linxuyalun --role-arn %s --definition file://stepfunctions --type EXPRESS --name %s" %(stepfuncs_role, name))
    # wait until machine created:
    while empty_str(cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep %s" %name)):
        wait()

def create_function():
    cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 512 --role %s --zip-file fileb://code.zip --function-name %s1" %(func_role, name))    
    cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 512 --role %s --zip-file fileb://code.zip --function-name %s2" %(func_role, name))    
    # wait until function created:
    while empty_str(cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep %s" %name)):
        wait()

def deploy(conf):
    # 清除所有的 lambda function 与 stepfunction machine 
    clear_all()
    # 部署 lambda function，创建 machine 文件，并部署 stepfunctions machine
    create_function()
    create_machine()
    
def req(payload_size):
    global errors, param
    generate_payload(payload_size)
    benchTime = int(round(time.time() * 1000))
    if len(param) > 1 * 1024 * 32:
        create_json_file(param, './input')
        cmd("aws s3 cp ./input s3://param0 --profile linxuyalun")
        param = '{"payload": "s3"}'
        cmd("rm ./input")
    res = cmd("aws stepfunctions start-sync-execution --profile linxuyalun --state-machine-arn %s%s --input '%s'" %(stepfuncs_arn, name, param))
    endTime = int(round(time.time() * 1000))
    res = json.loads(res)
    startTime = 0
    status = res['status']
    if status != succ_status:
        errors = errors + 1
        print(res['status'])
    else:
        if param == '{"payload": "s3"}':
            cmd("aws s3 cp s3://param2 ./output  --profile linxuyalun")
            f = open('./output',)
            output = json.load(f)
            cmd("rm ./output")
            f.close()
        else:
            output = json.loads(res['output'])
        startTime = output['startTime']
    return benchTime, startTime, endTime, status

def test(conf):  
    for payload_size in conf["payload_sizes"]:
        # warm tests      
        for i in repeat(None, conf['warm_up_times']):
            req(payload_size)
        resfile = open("./result%d.csv" %payload_size, 'w')
        writer = csv.writer(resfile, delimiter=',')
        writer.writerow(['benchTime', 'startTime', 'endTime'])
        avgTime = 0
        for i in repeat(None, conf['loop_times']):
            benchTime, startTime, endTime, status = req(payload_size)
            if status == succ_status:
                writer.writerow([benchTime, startTime, endTime])
                avgTime += endTime - benchTime
        writer.writerow([avgTime / conf['loop_times']])
        resfile.close()
        # cold tests
        resfile = open("./cold%d.csv" %payload_size, 'w')
        writer = csv.writer(resfile, delimiter=',')
        writer.writerow(['benchTime', 'startTime', 'endTime'])
        cavgTime = 0
        for i in repeat(None, conf['cold_times']):
            cold_start_release()
            benchTime, startTime, endTime, status = req(payload_size)
            if status == succ_status:
                writer.writerow([benchTime, startTime, endTime])
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