# README

## Intro (Tentative Content)

This is the benchmarker repo for Tass platform consists with test cases from ServerlessBench.

Testing targets includes Tass itself, AWS, OpenWhisk and Fission.

The repo is mainly programmed by bash and python.

The Serverless function language is Golang only.

## Test Cases

### bench-01 - Hello World, App\<Later\>

Reference to ServerlessBench - 6&7 Helloworld & App\<Later\> for Cold/Warm Start

该函数将参数中的 `name` 字段取出，format print 到输入中。

在 tass, openwhisk, aws lambda 均有测试其冷启动与热启动的开销。

### bench-02 - Sequence Chained (2 Modifications)

Reference to ServerlessBench - 3 Sequence Chained (Nested excluded) (2 Modifications)

Modification 1: Name Funcs by Different Names

The Same Func Name May Pass Cold Start Phase in Later Calls.

Name Funcs in Different Names Makes It's Easier to Do Practical Investigation into the Performance of Function Cold Starts During Chain Calls

Modification 2: Configure Function Chain Length

You May Want Different Func Chain Length For Investigation.

该函数将参数中的 `n` 取出，加一后传给下一个函数。

此测试测量了长度从 1 ～ 6 的链各自的冷启动和热启动的整条链路开销。（长度最高为 6 是因为 Azure Public Dataset 分析可知长度大于 6 的链式应用很少见）

测试对象包括：tass(开启/关闭预启动), openwhisk sequence, aws stepfunctions。

### bench-03 - Data Transfer Costs

Reference to ServerlessBench - 5 Data Transfer Costs

该函数将参数中的 `payload` 字符串取出，组成输出传给下一个函数。

此 benchmark 由两个上述函数组成，`payload` 字符串的大小取值如下：（单位：B）

````text
[0,1024,8192,16384,30720,35840,65536,131072,524288,1046528,1048576,2097152,4194304,8388608,16777216]
````

注意，aws stepfunction 和 openwhisk 平台数据传输有上限，其值分别为 32KB, 1MB。

在各个平台参数大小到达取值上限时，转用第三方存储进行中间数据的传输。stepfunctions 使用官方推荐的 s3，而 openwhisk 使用集群内搭建的 redis。

在传输上限的周围分别有取值点，方便画图（30720,35840,1046528,1048576）

该测试只进行了 `payload` 长度为 0 的冷启动测试

测试的时间包括：用户调用测试对象 + 测试对象的第一个函数处理数据 + 测试对象的第一个函数将数据传入第二个函数 + 第二个函数处理数据 + 用户收到测试对象返回测试状态（成功 / 失败）共五项时间

测试的时间不包括：在数量上限超过平台能力时，用户向第三方存储上传测试参数、下载测试返回值的时间这两项时间

测试对象包括 tass, openwhisk sequence, aws stepfunctions

### bench-04 - Real World

Reference to ServerlessBench - 11 Real World Emulation

将 Azure Public Dataset 的每个 App 含有的函数长度、每个 App 的平均调用时间与调用时间的 cv、每个函数的平均执行时间与占用内存这四项概率变量的累积概率分布函数计算出来，随机模拟 30 个 app 的长度、平均调用间隔、各个函数执行时间、各个函数执行内存这四个变量。（针对单个测试对象，上述四个值是随机的，但针对各个测试对象，每次调用的这些值都是各个测试对象间对齐的）

总共测试时间为 24 个小时。

若请求失败，测试将不会进行 redo 确保返回正确结果（因为 redo 后很可能把本该冷启动的请求变成热启动）

由于 stepfunction 与 openwhisk 的不稳定，以及 stepfunction 与 openwhisk 存在执行时间与内存占用上限，所以测试过程中的错误还挺多的。

测试平台包括：tass、openwhisk sequence、aws stepfunctions

### bench-05 - hotel-reservation

对应 DeathStarBench 中的 hotel-reservation 用例。

每个函数的拆分，每个函数的基准执行时长来自于 SoCC 论文。

每个函数的具体执行时间由该函数的基准执行时长进行 20% 的随机偏移。（各测试对象的用例已对齐）

每次调用中 workflow 的执行路径走向也是由固定的调用概率随机的。特别地，该用例中，下订单分支为 5%，查订单分支为 95%，这是拍脑袋想的（论文里并未提供）。

测试平台包括 tass，aws stepfunctions

### bench-06 - media-service

同上

分支概率也是拍脑袋想的。

### bench-07 - social-network

同上

分支概率来自 SoCC 论文。