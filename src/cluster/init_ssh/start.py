import subprocess

pem_path = '~/.ssh/renrui-aws-cn.pem'

def cmd(cmd):
    print(cmd)
    res = subprocess.run(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8").stdout
    print(res)
    return res

def empty_str(str):
    return len(str) == 0

def scp(src, dst):
    cmd('scp %s %s -i %s' %(src, dst, pem_path))
    
def ssh(user, ip, c):
    cmd("ssh %s@%s -i %s '%s'" %(user, ip, pem_path, c))

def init_node_ssh(ips):
    for ip in ips:
        ssh("ubuntu", ip, 'sudo sed -i -e "1,1c $(cat ~/.ssh/authorized_keys | grep renrui)" /root/.ssh/authorized_keys')

# master node should be the first elem
def init_kubernetes(ips):
    init_node_ssh(ips)
    # upload cert
    ssh('root', ips[0], '')
    # install sealos on the master
    ssh('root', ips[0], 'wget -c https://sealyun.oss-cn-beijing.aliyuncs.com/latest/sealos && chmod +x sealos && mv sealos /usr/bin')
    # download k8s offline package
    ssh('root', ips[0], 'wget -c https://sealyun.oss-cn-beijing.aliyuncs.com/05a3db657821277f5f3b92d834bbaf98-v1.22.0/kube1.22.0.tar.gz')
    # prepare k8s cluster

    ips[0]
    


    