#!/usr/bin/python

import zmq
import sys
import json
from datetime import datetime
from subprocess import Popen
from time import sleep

class Converter (object):
    def __init__(self):
        self.context = zmq.Context()

        self.server = Popen (["./pandoc_server"])
        #  Socket to talk to server
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://localhost:5555")

    def convert (self, informat, outformat, payload):
        job = json.dumps ({'informat': informat,
                           'outformat': outformat,
                           'payload': payload})
        self.socket.send(job)

        return self.socket.recv().decode('utf-8', errors='replace')

    def __del__ (self):
        self.server.terminate ()

pandoc_converter = Converter()

if __name__=="__main__":
    with open (sys.argv[1], 'r') as f:
        contents = f.read ()

    n = datetime.now ()
    out = pandoc_converter.convert (sys.argv[2], sys.argv[3], contents)
