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

workflow_path = './workflow/chained/workflow.yaml'
function_path = './function/chained/function.yaml'

def cold_start_release(): # sleep 15min for warm resource released
    time.sleep(60)

def wait():
    time.sleep(10)

def cmd(cmd):
    print(cmd)
    res = subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8").stdout
    print(res)
    return res

def get_result():
    cmd("""kubectl get pod | grep bench | awk '{print $1}' | xargs -n1 -P0 -I{} kubectl logs {} | grep -F "[GIN]" | awk '{print $8}'""")

def empty_str(str):
    return len(str) == 0

def post_json(url, data):
    data = {
        "workflowName": "bench-02-chained",
        "flowName": "",
        "parameters": data
    }
    return cmd("curl --connect-timeout 600 -s -S --header \"Content-Type: application/json\" --request POST --data-raw \'%s\' \"%s\"" %(json.dumps(data), url))

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
            'name': 'bench-02-chained'
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
        'function': 'bench-02-chained',
        'statement': 'direct',
    }
    for i in range(1, n + 1):
        elem = spec.copy()
        elem['name'] += str(i)
        elem['function'] += str(i)
        elem['output'] = ['flow'+str(i+1)]
        output['spec']['spec'].append(elem)
    del output['spec']['spec'][-1]['output']
    if n == 1:
        elem['role'] = 'orphan'
    else:
        output['spec']['spec'][0]['role'] = 'start'
        output['spec']['spec'][-1]['role'] = 'end'
    create_yaml_file(output, workflow_path)
    cmd("kubectl apply -f %s" %workflow_path)

def create_function(n):
    name = 'bench-02-chained'
    output = {
        'apiVersion': 'serverless.tass.io/v1alpha1',
        'kind': 'Function',
        'metadata': {
            'namespace': 'default',
            'name': name
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
        output['metadata']['name'] = name + str(i)
        create_yaml_file(output, function_path)
        cmd("tass-cli function create -c ./function/chained/code.zip -n " + name + str(i))
        cmd("kubectl apply -f " + function_path)

def deploy(conf):
    clear_all()
    # 创建 workflow 文件与 function 文件，然后 apply 它们，并 cli 部署函数
    create_workflow(int(conf['n']))
    create_function(int(conf['n']))
    wait()
    
def req():
    host=cmd("kubectl get svc | grep bench-02-chained | awk '{print $3}'")[:-1]
    benchTime = int(round(time.time() * 1000))
    res = post_json('http://%s/v1/workflow/' %host, {
        'n': 0
    })
    endTime = int(round(time.time() * 1000))
    return benchTime, endTime, res

def test(conf):
    # warm tests
    if conf['loop_times'] != 0:
        for i in repeat(None, conf['warm_up_times']):
            req()
        csvfile = open(conf['res_file'], 'w')
        writer = csv.writer(csvfile, delimiter=',')
        writer.writerow(['benchTime', 'endtime', 'res'])
        avgTime=0
        for i in repeat(None, conf['loop_times']):
            benchTime, endTime, res = req()
            avgTime += endTime - benchTime
            writer.writerow([benchTime, endTime, res])
        writer.writerow([avgTime / conf['loop_times']])
        csvfile.close()
    # cold tests
    if conf['cold_times'] != 0:
        resfile = open(conf['cold_res_file'], 'w')
        writer = csv.writer(resfile, delimiter=',')
        writer.writerow(['benchTime', 'endTime', 'res'])
        cavgTime = 0
        for i in repeat(None, conf['cold_times']):
            cold_start_release()
            benchTime, endTime, res = req()
            cavgTime += endTime - benchTime
            writer.writerow([benchTime, endTime, res])
        writer.writerow([cavgTime / conf['cold_times']])
        print("Cold Start Avg Time: %d ms (%d - %d) " %(cavgTime-avgTime, cavgTime, avgTime))
        resfile.close()

def do(input_conf):
    conf = default_test_conf.copy()
    conf.update(input_conf)
    deploy(conf)
    test(conf)

do({})