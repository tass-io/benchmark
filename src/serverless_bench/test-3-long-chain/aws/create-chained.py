import os, time, json, subprocess

func_role = "arn:aws-cn:iam::648513213171:role/sail-serverless"
func_arn = "arn:aws-cn:lambda:cn-northwest-1:648513213171:function:"
stepfuncs_role = "arn:aws-cn:iam::648513213171:role/sail-step-functions"
stepfuncs_arn = "arn:aws-cn:states:cn-northwest-1:648513213171:stateMachine:"
machine_path = './stepfunctions'


def wait():
    time.sleep(6)

def cmd(cmd):
    print(cmd)
    res = subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8").stdout
    print(res)
    return res

def empty_str(str):
    return len(str) == 0

def clear_all(chain_name):
    while not empty_str(cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep FunctionName | grep %s" %chain_name)):
        cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep FunctionName | grep %s | cut -d \\\" -f 4 | xargs -n1 -P0 -I{} aws lambda --profile linxuyalun delete-function --function-name {}" %chain_name)
        wait()
    while not empty_str(cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep \\\"name\\\" | grep %s" %chain_name)):
        cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep \\\"name\\\" | grep %s | cut -d \\\" -f 4 | xargs -n1 -P0 -I{} aws stepfunctions delete-state-machine --profile linxuyalun --state-machine-arn %s{}" %(chain_name, stepfuncs_arn))
        wait()

def create_json_file(object, filepath):
    if os.path.exists(filepath):
        os.remove(filepath)
    file = open(filepath, 'w')
    json.dump(object, file)
    file.close()

def create_machine(n, chain_name):
    output = {
        "Comment": "Tass ServerlessBench test 2 - long chain",
        "StartAt": "%s1" %chain_name,
        "TimeoutSeconds": 300, # maximum is 5 min
        "States": {}
    }
    state = {
        "Type": "Task",
        "Resource": "%s%s" %(func_arn, chain_name),
        "Next": "%s" %chain_name
    }
    for i in range(1, n + 1):
        elem = state.copy()
        elem['Resource'] += str(i)
        elem['Next'] += str(i + 1)
        output['States']['%s%d' %(chain_name, i)] = elem
    output["States"]["bench-02-chained%d" %n]["End"] = True
    del output["States"]["bench-02-chained%d" %n]["Next"]
    create_json_file(output, machine_path)
    cmd("aws stepfunctions create-state-machine --profile linxuyalun --role-arn %s --definition file://stepfunctions --type EXPRESS --name %s" %(stepfuncs_role, chain_name))
    # wait until machine created:
    while empty_str(cmd("aws stepfunctions list-state-machines --profile linxuyalun --max-items 200 | grep %s" %chain_name)):
        wait()

def create_function(n, chain_name):
    for i in range(1, n + 1):
        cmd("aws lambda create-function --profile linxuyalun --runtime go1.x --handler main --memory-size 128 --role %s --zip-file fileb://code.zip --function-name %s%d" %(func_role, chain_name, i))
        # wait until function created:
        while empty_str(cmd("aws lambda list-functions --profile linxuyalun --max-items 200 | grep %s%d" %(chain_name, i))):
            wait()

def deploy(length, chain_name):
    # 清除所有的 lambda function 与 stepfunction machine
    clear_all(chain_name)
    # 部署 lambda function，创建 machine 文件，并部署 stepfunctions machine
    create_function(length, chain_name)
    create_machine(length, chain_name)

def do():
    for i in range(1,7) :
        chain_name = "bench-02-chained-0" + str(i)
        deploy(i, chain_name)
    print("All done!")

do()