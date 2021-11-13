import os, time, csv, json, subprocess, random
from itertools import repeat
import gc

default_test_conf = {
    # 0,1024,8192,16384,30720,35840,65536,131072,524288,2097152,16777216,4194304,8388608, ,134217728
    #"payload_sizes": [1046528,1048576],
    "payload_sizes": [0,1024,8192,16384,30720],
    "loop_times": 100,
    "warm_up_times": 5,
    "cold_times": 10
}

name = "bench-03-passp"
param = '{"payload":""}'
param_schema = {
    "payload": ""
}

func_role = "arn:aws-cn:iam::648513213171:role/sail-serverless"
func_arn = "arn:aws-cn:lambda:cn-northwest-1:648513213171:function:"
stepfuncs_role = "arn:aws-cn:iam::648513213171:role/sail-step-functions"
stepfuncs_arn = "arn:aws-cn:states:cn-northwest-1:648513213171:stateMachine:"
machine_path = './stepfunctions'
errors = 0
succ_status = 'SUCCEEDED'
sample_pool = 'zyxwvutsrqponmlkjihgfedcba'

def generate_payload(payload):
    global param
    if payload == 0:
        param = '{"payload":""}'
        return
    param_s = param_schema.copy()
    res = cmd('openssl rand -hex %d' %(payload/2))
    res = res[:-1] # remove cmd tailling line break
    param_s['payload'] = res
    gc.collect()
    param = json.dumps(param_s)

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
    cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 512 --role %s --zip-file fileb://code.zip --function-name %s1 --timeout 900" %(func_role, name))    
    cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 512 --role %s --zip-file fileb://code.zip --function-name %s2 --timeout 900" %(func_role, name))    
    # wait until function created:
    while empty_str(cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep %s" %name)):
        wait()

def deploy(conf):
    # 清除所有的 lambda function 与 stepfunction machine 
    clear_all()
    # 部署 lambda function，创建 machine 文件，并部署 stepfunctions machine
    create_function()
    create_machine()
    
def req():
    global errors
    benchTime = int(round(time.time() * 1000))
    if len(param) > 1 * 1024 * 32:
        create_json_file(json.loads(param), './input')
        cmd("aws s3 cp ./input s3://params/param0 --profile linxuyalun")
        cmd("rm ./input")
        req_param = '{"payload": "s3"}'
    else:
        req_param = param
    res = cmd("aws stepfunctions start-sync-execution --profile linxuyalun --state-machine-arn %s%s --input '%s'" %(stepfuncs_arn, name, req_param))
    if len(param) > 1 * 1024 * 32:
        cmd("aws s3 cp s3://params/param2 ./output  --profile linxuyalun")
        cmd("rm ./output")
    endTime = int(round(time.time() * 1000))
    res = json.loads(res)
    startTime = 0
    status = res['status']
    if status != succ_status:
        errors = errors + 1
        print(res['status'])
    else:
        startTime = json.loads(res['output'])['startTime']
    return benchTime, startTime, endTime, status

def test(conf):  
    for payload_size in conf["payload_sizes"]:
        generate_payload(payload_size)
        # warm tests   
        if conf['loop_times'] != 0:    
            for i in repeat(None, conf['warm_up_times']):
                req()
            resfile = open("./result%d.csv" %payload_size, 'w')
            writer = csv.writer(resfile, delimiter=',')
            writer.writerow(['benchTime', 'startTime', 'endTime'])
            avgTime = 0
            for i in repeat(None, conf['loop_times']):
                benchTime, startTime, endTime, status = req()
                if status == succ_status:
                    writer.writerow([benchTime, startTime, endTime])
                    avgTime += endTime - benchTime
            writer.writerow([avgTime / conf['loop_times']])
            resfile.close()
    generate_payload(0)
    # cold tests
    if conf['cold_times'] != 0:
        resfile = open("./cold0.csv", 'w')
        writer = csv.writer(resfile, delimiter=',')
        writer.writerow(['benchTime', 'startTime', 'endTime'])
        cavgTime = 0
        for i in repeat(None, conf['cold_times']):
            cold_start_release()
            benchTime, startTime, endTime, status = req()
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

#do({})
#payload_sizes=[0,1024,8192,16384,30720]
#for payload in payload_sizes:
#	generate_payload(payload)
#	create_json_file(json.loads(param), './payload%d' %payload)
	#cmd("aws s3 cp ./input s3://params/param0 --profile linxuyalun")
generate_payload(8388608)
create_json_file(json.loads(param), './input')
cmd("aws s3 cp ./input s3://params/param0 --profile linxuyalun")
