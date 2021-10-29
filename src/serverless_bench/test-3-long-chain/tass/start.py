import os, requests, time, csv, yaml
from itertools import repeat

default_test_conf = {
    "loop_times": 3,
    "warm_up_times": 1,
    "type": "warm",
    'n': 0,
    "res_file": './result.csv'
}

workflow_path = './workflow/chained/workflow.yaml'
function_path = './function/chained/function.yaml'

def create_yaml_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    file = open(filepath, 'w')
    yaml.dump(object, file)
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
    print(os.popen("kubectl apply -f " + workflow_path).read())

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
        print(os.popen("kubectl apply -f " + function_path).read())
        print(os.popen("tass-cli function create -c ./function/chained/code.zip -n " + name + str(i)).read())

def deploy(conf):
    # 创建 workflow 文件与 function 文件，然后 apply 它们，并 cli 部署函数
    create_workflow(int(conf['n']))
    create_function(int(conf['n']))
    # 创建 Ingress 路由
    print(os.popen("tass-cli route create -n bench-02-chained -p /bench/02/chained").read())
    
def req(n):
    benchTime = int(round(time.time() * 1000))
    res = requests.post(url='http://<TODO>/bench/02/chained', data={
        'n': n
    })
    endTime = int(round(time.time() * 1000))
    res = res.json()
    startTime = int(res['startTime'])
    return benchTime, startTime, endTime

def test(conf):
    csvfile = open(conf['res_file'], 'w')
    writer = csv.writer(csvfile, delimiter=',')
    writer.writerow(['benchTime', 'startTime', 'endTime'])
    for i in repeat(None, conf['loop_times']):
        benchTime, startTime, endTime = req(int(conf['n']))
        writer.writerow([benchTime, startTime, endTime])
    csvfile.close()

def do(input_conf):
    conf = default_test_conf.copy()
    conf.update(input_conf)
    deploy(conf)
    if conf['type'] == 'warm':
        for i in repeat(None, conf['warm_up_times']):
            req()
    test(conf)