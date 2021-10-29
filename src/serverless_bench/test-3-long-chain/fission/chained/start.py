import os, requests, time, csv, yaml
from itertools import repeat

default_test_conf = {
    "loop_times": 3,
    "warm_up_times": 1,
    "type": "warm",
    'n': 0,
    "res_file": './result.csv'
}

workflow_path = './workflow.wf.yaml'

def create_yaml_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    file = open(filepath, 'w')
    yaml.dump(object, file)
    file.close()

def create_workflow(n):
    workflow = {
        'apiVersion': 1,
        'tasks': {},
    }
    task = {
        'run': 'bench-02-chained',
    }
    for i in range(1, n + 1):
        elem = task.copy()
        elem['run'] += str(i)
        if i > 1:
            elem['inputs'] = {
                'body': "{ output('Flow%d') }" %(i-1) 
            }
            elem['requires'] = ["Flow%d" %(i-1)]
        workflow['task']['Flow%d' %i] = elem
    create_yaml_file(workflow, workflow_path)
    workflow['output'] = 'Flow%d' %n,
    print(os.popen("fission fn create --name bench-02-chainedwf --env workflow --src " + workflow_path).read())
    print(os.popen("fission httptrigger create --method POST --url \"bench/02/chained\" --function bench-02-chainedwf").read())

def create_function(n):
    for i in range(1, n + 1):
        print(os.popen("fission fn create --name bench-02-chained%d --env go --src main.go --entrypoint Handler --maxmemory 128" %i).read())

def deploy(conf):
    # TODO: 如果没有 go env，创建一个
    # 部署 function，创建并部署 workflow 文件，创造路由
    create_function(int(conf['n']))
    create_workflow(int(conf['n']))
    
    
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