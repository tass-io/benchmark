import os, time, csv, json, subprocess
from itertools import repeat

default_test_conf = {
    "loop_times": 100,
    "warm_up_times": 5,
    "cold_times": 0,
    "res_file": './result.csv',
    "cold_res_file": './cold.csv'
}

name = "bench-01-hello"
param = '{"name":"kony"}'

func_role = "arn:aws-cn:iam::648513213171:role/sail-serverless"
errors = 0
succ_status_code = 200

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

def create_json_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    file = open(filepath, 'w')
    json.dump(object, file)
    file.close()

def create_function():
    cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 128 --role %s --zip-file fileb://code.zip --function-name %s" %(func_role, name))
    # wait until function created:
    while empty_str(cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep %s" %name)):
        wait()

def deploy(conf):
    # 清除所有的 lambda function
    clear_all()
    # 部署 lambda function
    create_function()
    
def req():
    global errors
    benchTime = int(round(time.time() * 1000))
    res = cmd("aws lambda invoke --profile linxuyalun --function-name %s --payload '%s' ./output --cli-binary-format raw-in-base64-out" %(name, param))
    endTime = int(round(time.time() * 1000))
    res = json.loads(res)
    f = open('./output','r',encoding='utf-8')
    output = json.load(f)
    f.close()
    cmd("rm ./output")
    startTime = 0
    status_code = res['StatusCode']
    if status_code != succ_status_code:
        errors = errors + 1
        print(res['status'])
    else:
        startTime = output['startTime']
    return benchTime, startTime, endTime, status_code

def test(conf):  
    # warm tests    
    if conf['loop_times'] != 0:      
        for i in repeat(None, conf['warm_up_times']):
            req()
        resfile = open(conf['res_file'], 'w')
        writer = csv.writer(resfile, delimiter=',')
        writer.writerow(['benchTime', 'startTime', 'endTime'])
        avgTime = 0
        for i in repeat(None, conf['loop_times']):
            benchTime, startTime, endTime, status_code = req()
            if status_code == succ_status_code:
                writer.writerow([benchTime, startTime, endTime])
                print(endTime - benchTime)
                avgTime += endTime - benchTime
        writer.writerow([avgTime / conf['loop_times']])
        resfile.close()
    # cold tests
    if conf['cold_times'] != 0:
        resfile = open(conf['cold_res_file'], 'w')
        writer = csv.writer(resfile, delimiter=',')
        writer.writerow(['benchTime', 'startTime', 'endTime'])
        cavgTime = 0
        for i in repeat(None, conf['cold_times']):
            cold_start_release()
            benchTime, startTime, endTime, status_code = req()
            if status_code == succ_status_code:
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
