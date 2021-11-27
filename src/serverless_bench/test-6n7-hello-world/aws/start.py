import os, time, csv, json, subprocess
from itertools import repeat
from functools import reduce

default_test_conf = {
    "loop_times": 150,
    "warm_up_times": 10,
    "cold_times": 15,
    "res_file": './result.csv',
    "cold_res_file": './cold.csv'
}

name = "bench-01-hello"
param = '{"name":"kony"}'

func_role = "arn:aws-cn:iam::648513213171:role/sail-serverless"
log_arn = 'arn:aws-cn:logs:cn-northwest-1:648513213171:log-group:'
log_name_prefix = '/aws/lambda/'
errors = 0
succ_status_code = 200

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

def create_json_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    sscmd("mkdir -p $(dirname %s)" %filepath)
    file = open(filepath, 'w')
    json.dump(object, file)
    file.close()

def create_function():
    cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 128 --role %s --zip-file fileb://code.zip --function-name %s" %(func_role, name))
    # wait until function created:
    while empty_cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep %s" %name):
        wait()

def deploy():
    # 清除所有的 lambda function
    clear_all()
    # 部署 lambda function
    create_function()
    
def req():
    global errors
    try:
        res = json.loads(cmd("aws lambda invoke --profile linxuyalun --function-name %s --payload '%s' ./output --cli-binary-format raw-in-base64-out" %(name, param)))
        sscmd("rm ./output")
        status_code = res['StatusCode']
        if status_code != succ_status_code:
            errors = errors + 1
            print("request ERR. status code is: ", status_code)
        return {"status_code": status_code}
    except:
        return {"status": "FAILED"}

def must_req():
    res = req()
    while res['status_code'] !=  succ_status_code:
        print("=================\nA err req occured\n=================")
        res = req()
    return res

def test_loop(loops, warmups):
    if loops != 0: 
        for i in repeat(None, warmups):
            req()
        for i in range(loops):
            if warmups == -1: # -1 warmups is recognized as cold test
                cold_start_release()
            must_req()

def get_res_from_log(query):
    res = json.loads(scmd("""aws logs filter-log-events --profile linxuyalun --log-group-name '%s%s' --filter-pattern '%s'""" %(log_name_prefix, name, query)))
    return list(map(lambda event: event['message'], res['events']))
    
def get_res(res_file, query, handle_res):
    res_arr = handle_res(get_res_from_log(query))
    resfile = open(res_file, 'w')
    writer = csv.writer(resfile, delimiter='@')
    writer.writerow(['execTime(ms)'])
    for res in res_arr: writer.writerow([res])
    writer.writerow(['avgTime(ms)'])
    writer.writerow([reduce(lambda x, y: x+y, res_arr) / len(res_arr)])

def test(conf):  
    # warm tests
    test_loop(conf['loop_times'], conf['warm_up_times'])
    # cold tests
    test_loop(conf['cold_times'], -1)

def parseTime(timeStr):
    res = -1
    if timeStr[-2:] == 'µs':
        res = float(timeStr[:-3]) / 1000
    elif timeStr[-2:] == 'ms':
        res = float(timeStr[:-3])
    elif timeStr[-1:] == 's':
        res = float(timeStr[:-2]) * 1000
    elif timeStr[-1:] == 'm':
        res = float(timeStr[:-2]) * 1000 * 60 
    else:
        raise ValueError('Not supported time end from %s' %(timeStr))
    return res

def do(input_conf):
    conf = default_test_conf.copy()
    conf.update(input_conf)
    deploy()
    test(conf)
    # get test results
    wait()
    # generate warm test result
    if conf['loop_times'] > 0:
        get_res(conf['res_file'], '"Duration:" - "Init Duration:"', lambda arr: list(map(lambda str: parseTime(list(filter( lambda item: item != "", str.split("\t")))[1][len('Duration: '):]), arr)))
    # generate cold test result
    if conf['cold_times'] > 0:
        get_res(conf['cold_res_file'], '"Init Duration:"', lambda arr: list(map(lambda str: parseTime(list(filter( lambda item: item != "", str.split("\t")))[5][len('Init Duration: '):]), arr)))
    print("ERRORS REQS: %d. Automatically redo failed tests" %errors)

do({})
