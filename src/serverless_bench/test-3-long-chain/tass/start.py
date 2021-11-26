import os, time, csv, yaml, subprocess, json
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
workflow_path = './workflow/chained/workflow.yaml'
function_path = './function/chained/function.yaml'
param = {
    'n': 0
}
param_schema = {
    "workflowName": "%s" %name,
    "flowName": "",
    "parameters": {}
}
success = True
errors = 0

def cold_start_release(): # sleep 15min for warm resource released
    time.sleep(60)

def wait():
    time.sleep(10)

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

def post_json(url, data):
    ps = param_schema.copy()
    ps['parameters'] = data
    return cmd("curl --max-time 600 -s -S --header \"Content-Type: application/json\" --request POST --data-raw \'%s\' \"%s\"" %(json.dumps(ps), url))

def clear_all():
    cmd("""tass-cli function list | grep bench | awk '{print $2}' | xargs -n1 -I{} -P0 tass-cli function delete -n {}""")
    cmd("""kubectl get workflow | grep bench | awk '{print $1}' | xargs -n1 -I{} -P0 kubectl delete workflow {}""")
    wait()

def create_yaml_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    file = open(filepath, 'w')
    yaml.dump(object, file, default_flow_style=False)
    file.close()

def create_workflow(n):
    output = {
        'apiVersion': 'serverless.tass.io/v1alpha1',
        'kind': 'Workflow',
        'metadata': {
            'namespace': 'default',
            'name': '%s' %name
        },
        'spec': {
            'env': {
                'lang': 'CH',
                'kind': 'pipeline'
            },
            'spec': []
        }
    }
    spec = {
        'name': 'flow',
        'function': '%s' %name,
        'statement': 'direct',
    }
    for i in range(1, n + 1):
        elem = spec.copy()
        elem['name'] += str(i)
        elem['function'] += str(i)
        elem['outputs'] = ['flow'+str(i+1)]
        output['spec']['spec'].append(elem)
    del output['spec']['spec'][-1]['outputs']
    if n == 1:
        elem['role'] = 'orphan'
    else:
        output['spec']['spec'][0]['role'] = 'start'
        output['spec']['spec'][-1]['role'] = 'end'
    create_yaml_file(output, workflow_path)
    scmd("kubectl apply -f %s" %workflow_path)

def create_function(n):
    output = {
        'apiVersion': 'serverless.tass.io/v1alpha1',
        'kind': 'Function',
        'metadata': {
            'namespace': 'default',
            'name': '%s' %name
        },
        'spec': {
            'environment': 'Golang',
            'resource': {
                'cpu': '1',
                'memory': '128Mi'
            }
        }
    }
    for i in range(1, n + 1):
        output['metadata']['name'] = "%s%d" %(name, i)
        create_yaml_file(output, function_path)
        scmd("tass-cli function create -c ./function/chained/plugin.so -n %s%d" %(name, i))
        scmd("kubectl apply -f " + function_path)

def deploy(conf):
    clear_all()
    # 创建 workflow 文件与 function 文件，然后 apply 它们，并 cli 部署函数
    create_workflow(int(conf['n']))
    create_function(int(conf['n']))
    wait()

def parseTime(timeStr):
    res = -1
    if timeStr[-2:] == 'µs':
        res = int(float(timeStr[:-2]))
    elif timeStr[-2:] == 'ms':
        res = int(float(timeStr[:-2]) * 1000) 
    elif timeStr[-1:] == 's':
        res = int(float(timeStr[:-1]) * 1000 * 1000) 
    elif timeStr[-1:] == 'm':
        res = int(float(timeStr[:-1]) * 1000 * 1000 * 60) 
    else:
        raise ValueError('Not supported time end from %s' %(timeStr))
    return res

def req():
    global errors
    try:
        host=sscmd("kubectl get svc | grep %s | awk '{print $3}'" %name)[:-1]
        res = json.loads(post_json('http://%s/v1/workflow/' %host, param.copy()))
        execTime = parseTime(res['time'])
        status = res['success']
        if status != success:
            print(res)
            raise Exception('status == %s' %(str(status)))
        return status, execTime, res
    except Exception as e:
        print(e)
        errors += 1
        return False, 0, 0

def must_req():
    status, execTime, res = req()
    while status != success:
        print("=================\nA err req occured\n=================")
        status, execTime, res = req()
    return status, execTime, res

def test_loop(loops, warmups, resFile):
    if loops != 0:    
        for i in repeat(None, warmups):
            req()
        resfile = open(resFile, 'w')
        writer = csv.writer(resfile, delimiter='@')
        writer.writerow(['execTime(µs)', 'status', 'res'])
        avgTime = validNum = 0
        for i in repeat(None, loops):
            if warmups == -1: # -1 warmups is recognized as cold test
                cold_start_release()
            status, execTime, res = must_req()
            if status == success:
                avgTime += execTime
                validNum += 1
            writer.writerow([execTime, status, res])
        writer.writerow(["avgTime(µs)"])
        writer.writerow([avgTime / validNum])
        resfile.close()

def get_model(conf):
    sscmd('mkdir model-chain-%d' %conf['n'])
    sscmd('mkdir data-chain-%d' %conf['n'])
    scmd("kubectl cp $(kubectl get pod | grep %s | awk '{print $1}'):/tass/model ./model-chain-%d"  %(name, conf['n']))
    scmd("kubectl cp $(kubectl get pod | grep %s | awk '{print $1}'):/tass/data ./data-chain-%d"  %(name, conf['n']))

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
    get_model(conf)
    print("ERRORS REQS: %d. Automatically redo failed tests" %errors)

resfn = './result-%d.csv'
coldfn = './cold-%d.csv'

for i in range(1, 7):
    do({
        "n": i,
        "res_file": resfn %i,
        "cold_res_file": coldfn %i
    })