from receiver import do_something, run_requests_from_file
from flask import Flask, make_response, jsonify, Response
from flask import request
from flask_script import Manager, Server
import json
import threading
from datetime import datetime
import signal
import sys
import shlex

import requests
import node as nd 
import bisect
app = Flask(__name__)

###Disable network messages
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

### Receive messages from Server Side CLI
@app.route('/', methods=['GET', 'POST'])
def print_server_message_contents():    
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    multi_dict = request.args
    for key in multi_dict:
        if request.method == 'POST':
            file_list = json.loads(multi_dict.get(key))
            print("Number of received files:{} --- Time".format(len(file_list.keys()), current_time))
        print(multi_dict.get(key)+ " ---- Time:"+ str(current_time))
        #print(multi_dict.getlist(key))
	
    return jsonify(
	    status="Success"
	)


### Receive overlay messages from Server Side CLI
@app.route('/extract_overlay', methods=['GET', 'POST'])
def extract_overlay():
    coord_ip = request.args.get('coordinator_ip')
    coord_port = request.args.get('coordinator_port')

    message = request.args.get('message')
    json_overlay = json.loads(message)

    nodes = json_overlay['nodes']
    print("Coordinator: {}:{}".format(coord_ip, coord_port))
    for item in nodes:
        print("{} --- {}".format(item, nodes[item]))
	
    return jsonify(
	    status="Success"
	)
    


def signal_handler(sig, frame):
	print('You pressed Ctrl+C!')	
	print("This node will depart and die...")
	sys.exit(0)

def insert(params, server_cli_ip, server_cli_port):
    # Pass insert request to SERVER SIDE CLIE
    if not (len(params) == 3 or len(params) == 5):
        print("Wrong Command --- Please type 'help' to see correct usage")

    ip = None
    port = None
    if len(params) == 5:
        ip = params[3]
        port = params[4]

    key = params[1]
    value = params[2]
    if key.startswith('"') and key.endswith('"'):
        key = key[1:-1]
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    #Pass message to server side cli
    response = requests.get(url = "http://"+server_cli_ip+":"+server_cli_port+"/insert_cli", \
        params = {'key':key, 'value':value, 'ip':ip, 'port':port})
    

def delete(params, server_cli_ip, server_cli_port):
    # Pass insert request to SERVER SIDE CLIE
    if not (len(params) == 2 or len(params) == 4):
        print("Wrong Command --- Please type 'help' to see correct usage")

    ip = None
    port = None
    if len(params) == 4:
        ip = params[2]
        port = params[3]

    key = params[1]
    if key.startswith('"') and key.endswith('"'):
        key = key[1:-1]
    #Pass message to server side cli
    response = requests.get(url = "http://"+server_cli_ip+":"+server_cli_port+"/delete_cli", \
        params = {'key':key, 'ip':ip, 'port':port})
    

def query(params, server_cli_ip, server_cli_port):
    # Pass insert request to SERVER SIDE CLIE
    if not (len(params) == 2 or len(params) == 4):
        print("Wrong Command --- Please type 'help' to see correct usage")

    ip = None
    port = None
    if len(params) == 4:
        ip = params[2]
        port = params[3]

    key = params[1]
    if key.startswith('"') and key.endswith('"'):
        key = key[1:-1]
    #Pass message to server side cli
    response = requests.get(url = "http://"+server_cli_ip+":"+server_cli_port+"/query_cli", \
        params = {'key':key, 'ip':ip, 'port':port})
    

def departure(params, server_cli_ip, server_cli_port):
    # Pass insert request to SERVER SIDE CLIE
    if not (len(params) == 3):
        print("Wrong Command --- Please type 'help' to see correct usage")


    ip = params[1]
    port = params[2]

    #Pass message to server side cli
    response = requests.get(url = "http://"+server_cli_ip+":"+server_cli_port+"/departure_cli", \
        params = {'ip':ip, 'port':port})

def insert_sample_files(params, server_cli_ip, server_cli_port):
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    # Pass insert request to SERVER SIDE CLIE
    if not (len(params) == 2):
        print("Wrong Command --- Please type 'help' to see correct usage")

    print("Initiating batch insert: {}".format(current_time))

    file_name = params[1]
    #Pass message to server side cli
    response = requests.get(url = "http://"+server_cli_ip+":"+server_cli_port+"/insert_from_file_cli", \
        params = {'file':file_name})

def request_file(params, server_cli_ip, server_cli_port):
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    # Pass insert request to SERVER SIDE CLIE
    if not (len(params) == 2):
        print("Wrong Command --- Please type 'help' to see correct usage")

    print("Initiating batch requesting: {}".format(current_time))
    file_name = params[1]
    #Pass message to server side cli
    response = requests.get(url = "http://"+server_cli_ip+":"+server_cli_port+"/run_requests_from_file_cli", \
        params = {'file':file_name})

def query_file(params, server_cli_ip, server_cli_port):
    # Pass insert request to SERVER SIDE CLIE
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    if not (len(params) == 2):
        print("Wrong Command --- Please type 'help' to see correct usage")

    print("Initiating batch querying: {}".format(current_time))
    file_name = params[1]
    #Pass message to server side cli
    response = requests.get(url = "http://"+server_cli_ip+":"+server_cli_port+"/run_queries_from_file_cli", \
        params = {'file':file_name})

def view_node_files(params, server_cli_ip, server_cli_port):
    # Pass insert request to SERVER SIDE CLI
    if not (len(params) == 3):
        print("Wrong Command --- Please type 'help' to see correct usage")

    ip = params[1]
    port = params[2]

    #Pass message to server side cli
    response = requests.get(url = "http://"+server_cli_ip+":"+server_cli_port+"/view_files_cli", \
        params = {'ip':ip, 'port':port})
    

def help(params):
    # Put your submenus here
    with open('help.txt', 'r') as f:
        print(f.read())
    

def overlay(params, server_cli_ip, server_cli_port):
    # Pass insert request to SERVER SIDE CLIE
    if not (len(params) == 1 or len(params) == 3):
        print("Wrong Command --- Please type 'help' to see correct usage")

    ip = None
    port = None

    if len(params) == 3:
        ip = params[1]
        port = params[2]

    #Pass message to server side cli
    response = requests.get(url = "http://"+server_cli_ip+":"+server_cli_port+"/topology_cli", \
        params = {'ip':ip, 'port':port})
    

def thread_menu(server_cli_ip, server_cli_port):
    # Print logo
    with open('logo.txt', 'r') as f:
        print(f.read())

    while True:
        command = input("Enter command. Press help for command list\n")
        #params = command.split(' ')
        params = shlex.split(command)
        
        if params[0] == "insert":
            insert(params, server_cli_ip, server_cli_port)
        elif params[0] == "delete":
            delete(params, server_cli_ip, server_cli_port)
        elif params[0] == "query":
            query(params, server_cli_ip, server_cli_port)
        elif params[0] == "depart":
            departure(params, server_cli_ip, server_cli_port)
        elif params[0] == "overlay":
            overlay(params, server_cli_ip, server_cli_port)
        elif params[0] == "help":
            help(params)
        elif params[0] == "view_node_files":
            view_node_files(params, server_cli_ip, server_cli_port)
        elif params[0] == "insert_sample_files":
            insert_sample_files(params, server_cli_ip, server_cli_port)
        elif params[0] == "request_file":
            request_file(params, server_cli_ip, server_cli_port)
        elif params[0] == "query_file":
            query_file(params, server_cli_ip, server_cli_port)
        else:
            print("Invalid command. Please type help.")

#input parameters: 1. server_cli_ip, 2. server_cli_port, 3. my port
if __name__ == '__main__':
	server_cli_ip = sys.argv[1] ### MUST BE THE SAME WITH MY IP (both modules run on the same machine)
	server_cli_port = sys.argv[2]

	#New thread to request coordinator for files
	app_thread = threading.Thread(target=thread_menu, args=(server_cli_ip, server_cli_port))
	app_thread.start()

	### Create Handler for exit signal
	signal.signal(signal.SIGINT, signal_handler)

	app.run(host=server_cli_ip,threaded = True, port=int(sys.argv[3]))

	#threading.Thread(target=app.run, args=('localhost',sys.argv[1])).start()
