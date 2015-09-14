import sys

from dbusapi import interfaceparser

if __name__=='__main__':
    ip = interfaceparser.InterfaceParser(sys.argv[1])
    interfaces = ip.parse()
    for name, interface in interfaces.items():
        print ("One interface")
        print (name, interface.comment)
        for method_name, method in interface.methods.items():
            print ("One method")
            print (method_name, method.comment)
