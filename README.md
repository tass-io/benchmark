# README

## Intro (Tentative Content)

This is the benchmarker repo for Tass platform consists with test cases from ServerlessBench.

Testing targets includes Tass itself, AWS, OpenWhisk and Fission.

The repo is mainly programmed by bash and python.

The Serverless function language is Golang only.

## Test Cases

### bench-01 - Hello World, App\<Later\>

Reference to ServerlessBench - 6&7 Helloworld & App\<Later\> for Cold/Warm Start

### bench-02 - Sequence Chained (2 Modifications)

Reference to ServerlessBench - 3 Sequence Chained (Nested excluded) (2 Modifications)

Modification 1: Name Funcs by Different Names

The Same Func Name May Pass Cold Start Phase in Later Calls.

Name Funcs in Different Names Makes It's Easier to Do Practical Investigation into the Performance of Function Cold Starts During Chain Calls

Modification 2: Configure Function Chain Length

You May Want Different Func Chain Length For Investigation.

### bench-03 - Data Transfer Costs

Reference to ServerlessBench - 5 Data Transfer Costs

### bench-04 - Real World

Reference to ServerlessBench - 11 Real World Emulation