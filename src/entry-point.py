import logging
import sys, getopt
import scaffold.log
# import serverless_bench.test

def main(argv):
   log = scaffold.log.init()
   scaffold.log.oki()
   scaffold.log.doki()



main(sys.argv[1:])