import hashlib
from flask import Flask, make_response, jsonify, Response
from flask import request
import flask
from flask_script import Manager, Server
import json
import threading
import time
import signal
import sys
import psutil
import os
import requests
import node as nd 
import bisect
app = Flask(__name__)
#app = flask.Flask("after_response")



chord_nodes = {}
chord_ids = []
this_node = None

app_thread = None

### function to catch async responses
def fight(responses):
    return "Why can't we all just get along?"


def list_2_dict(lst):
    res_dct = {'node-'+str(i) : str(chord_nodes[i]) for i in range(0, len(lst))}
    return res_dct

@app.route('/')
def hello():
    return "Hello World!"



# @app.route('/jointest', methods=['GET', 'POST'])
# def join():
# 	domain = request.args.get('url')
# 	port = request.args.get('port')
# 	currentNode = nd.Node(domain,port)
# 	if currentNode.is_coordinator():
# 		chord_nodes.append([currentNode.getId(),currentNode.getIp(),currentNode.getPort()])
# 	this_node = currentNode 
# 	return currentNode.print()

@app.route('/insert', methods=['GET', 'POST'])
def insert_file():
	unhashed_key = request.args.get('key')
	value = request.args.get('value')
	client_ip = request.args.get('client_ip')
	client_port = request.args.get('client_port')
	print('Received new insert request from ip:{} and port:{}'.format(client_ip,client_port))

	### Produce hash of unhashed key
	m = hashlib.sha1()
	m.update(unhashed_key.encode('utf-8'))
	key = int(m.hexdigest(),16)

	message = ''

	print("Just produced this hash: {}, from this key: {}".format(key, unhashed_key))
	if(this_node.isMyKey(key)):
		if(this_node.replication_factor == 1 or (not this_node.isLinear)):
			### Store file in this node
			this_node.insertFile(key, unhashed_key, value)
			message = 'Saved the file'

			#Answer to cli for successful insert
			message_to_cli = 'File saved successfully'
			response_to_cli = requests.post(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'message':message_to_cli})

			### If replication_facor>1 --> eventual consistency --> propagate to next replica manager
			if(this_node.replication_factor >1):
				#Propagate insert to successors nodes with my replicas
				response = requests.get(url = "http://"+str(this_node.getSuccessor()['ip'])+":"+str(this_node.getSuccessor()['port'])+"/propagate_eventual_insert", \
					params = {'key':unhashed_key, 'value':value, 'origin_id':this_node.getId()})

		else:
			this_node.insertFile(key, unhashed_key, value)
			### Propagate write of file and last node answers with success message
			response = requests.get(url = "http://"+str(this_node.getSuccessor()['ip'])+":"+str(this_node.getSuccessor()['port'])+"/propagate_insert", \
				params = {'key':unhashed_key, 'value':value, 'origin_id':this_node.getId(), 'client_ip':client_ip, 'client_port':client_port})
			return jsonify(
				status='Propagating file to chain of replicas'
			)
	else:
		### Pass request to successor
		suc_ip = this_node.getSuccessor()['ip']
		suc_port = this_node.getSuccessor()['port']
		response = requests.get(url = "http://"+str(suc_ip)+":"+str(suc_port)+"/insert", \
			params = {'key':unhashed_key, 'value':value, 'client_ip':client_ip, 'client_port':client_port})
		json_data = json.loads(response.text)
		print(json_data)
		message = 'forwarding insert query to my successor: {}:{}'.format(suc_ip,suc_port)

	return jsonify(
			status=message
	)

### Propagating insert file for Chain Replication
@app.route('/propagate_insert', methods=['GET', 'POST'])
def propagate_insert():
	unhashed_key = request.args.get('key')
	value = request.args.get('value')
	client_ip = request.args.get('client_ip')
	client_port = request.args.get('client_port')
	origin_id = request.args.get('origin_id')

	### Produce hash of unhashed key
	m = hashlib.sha1()
	m.update(unhashed_key.encode('utf-8'))
	key = int(m.hexdigest(),16)

	#Check if this node is reponsible for replicas of origin_id
	if(not this_node.checkExistenceInReplicaManager(origin_id)):
		return jsonify(
			status="Failed",
			message="Replica not found"
		)
	else:
		this_node.addFileToReplicaManager(origin_id, key, unhashed_key, value)
		response = requests.get(url = "http://"+str(this_node.getSuccessor()['ip'])+":"+str(this_node.getSuccessor()['port'])+"/propagate_insert", \
			params = {'key':unhashed_key, 'value':value, 'origin_id':origin_id, 'client_ip':client_ip, 'client_port':client_port})
		if(not str(response.status_code) == '200'):
			response = requests.post(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'message':"Error: file could not be saved properly"})
		else:
			json_data = json.loads(response.text)
			if(json_data['message'] == "Replica not found"):
				message = 'File saved successfully'
				print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>http://"+str(client_ip)+":"+str(client_port)+"/")
				response = requests.post(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'message':message})
			elif(json_data['status'] != 'Success'):
				response = requests.post(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'message':"Error: file could not be saved properly"})
	return jsonify(
		status="Success",
		message="Replica found"
	)

### Propagating eventual insert of file for Eventual consistency
@app.route('/propagate_eventual_insert', methods=['GET', 'POST'])
def propagate_eventual_insert():
	unhashed_key = request.args.get('key')
	value = request.args.get('value')
	origin_id = request.args.get('origin_id')

	### Produce hash of unhashed key
	m = hashlib.sha1()
	m.update(unhashed_key.encode('utf-8'))
	key = int(m.hexdigest(),16)

	#Check if this node is reponsible for replicas of origin_id
	if(not this_node.checkExistenceInReplicaManager(origin_id)):
		return jsonify(
			status="Failed",
			message="Replica not found"
		)
	else:
		this_node.addFileToReplicaManager(origin_id, key, unhashed_key, value)
		response = requests.get(url = "http://"+str(this_node.getSuccessor()['ip'])+":"+str(this_node.getSuccessor()['port'])+"/propagate_eventual_insert", \
			params = {'key':unhashed_key, 'value':value, 'origin_id':origin_id})
	return jsonify(
		status="Success",
		message="Replica found"
	)

@app.route('/accept_files', methods=['POST'])
def accept_files():
	files = request.args.get('files')
	json_dict = json.loads(files)
	message = 'success'
	print("Just received new keys from:{}:{}".format(request.environ['REMOTE_ADDR'],request.environ['REMOTE_PORT']))

	this_node.appendDictionary(json_dict)

	return jsonify(
			status=message
	)

#Accept a replica from the file system of another node
@app.route('/accept_replicas', methods=['POST'])
def accept_replicas():
	id = request.args.get('id')
	files = request.args.get('files')
	json_dict = json.loads(files)
	message = 'success'
	print("Just received new replica keys from:{}:{}".format(request.environ['REMOTE_ADDR'],request.environ['REMOTE_PORT']))

	this_node.addToReplicaManager(int(id),json_dict)


	return jsonify(
			status=message
	)


@app.route('/delete', methods=['GET', 'POST'])
def delete_file():
	unhashed_key = request.args.get('key')
	client_ip = request.args.get('client_ip')
	client_port = request.args.get('client_port')
	### Produce hash of unhashed key
	m = hashlib.sha1()
	m.update(unhashed_key.encode('utf-8'))
	key = int(m.hexdigest(),16)
	key = str(key)

	message = ''

	print("Just produced this hash: {}, from this key: {}".format(key, unhashed_key))
	if(this_node.isMyKey(key)):
		### Store file in this node
		if(key in this_node.getFiles().keys()):
			### Check replication type
			if(this_node.replication_factor == 1 or (not this_node.isLinear)): #Eventual or no replication
				this_node.deleteFile(key)
				message = 'Deleted the file'

				### Amswer to CLI
				response = requests.post(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'message':"Success"})

				if(this_node.replication_factor > 1): #eventual consistency
					### Propagate delete to successors with my replica
					response = requests.get(url = "http://"+str(this_node.getSuccessor()['ip'])+":"+str(this_node.getSuccessor()['port'])+"/propagate_eventual_delete", \
						params = {'key':unhashed_key, 'origin_id':this_node.getId()})


			else:	#Chain replication
				this_node.deleteFile(key)
				### Propagate write of file and last node answers with success message
				response = requests.get(url = "http://"+str(this_node.getSuccessor()['ip'])+":"+str(this_node.getSuccessor()['port'])+"/propagate_delete", \
					params = {'key':unhashed_key, 'origin_id':this_node.getId(), 'client_ip':client_ip, 'client_port':client_port})
				return jsonify(
					status='Propagating deletion to chain of replicas'
				)
		else:
			message = 'File not found!'
		
	else:
		### Pass request to successor
		suc_ip = this_node.getSuccessor()['ip']
		suc_port = this_node.getSuccessor()['port']
		response = requests.get(url = "http://"+str(suc_ip)+":"+str(suc_port)+"/delete", params = {'key':unhashed_key, 'client_ip':client_ip, 'client_port':client_port})
		json_data = json.loads(response.text)
		print(json_data)
		message = 'forwarding delete query to my successor: {}:{}'.format(suc_ip,suc_port)

	return jsonify(
			status=message
	)

### Propagating file deletion for Chain Replication
@app.route('/propagate_delete', methods=['GET', 'POST'])
def propagate_delete():
	unhashed_key = request.args.get('key')
	client_ip = request.args.get('client_ip')
	client_port = request.args.get('client_port')
	origin_id = request.args.get('origin_id')

	### Produce hash of unhashed key
	m = hashlib.sha1()
	m.update(unhashed_key.encode('utf-8'))
	key = int(m.hexdigest(),16)
	key = str(key)

	#Check if this node is reponsible for replicas of origin_id
	if(not this_node.checkExistenceInReplicaManager(origin_id)):
		return jsonify(
			status="Failed",
			message="Replica not found"
		)
	else:
		this_node.deleteFileFromReplicaManager(origin_id, key)
		response = requests.get(url = "http://"+str(this_node.getSuccessor()['ip'])+":"+str(this_node.getSuccessor()['port'])+"/propagate_delete", \
			params = {'key':unhashed_key, 'origin_id':origin_id, 'client_ip':client_ip, 'client_port':client_port})
		if(not str(response.status_code) == '200'):
			response = requests.post(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'message':"Error: file could not be deleted properly"})
		else:
			json_data = json.loads(response.text)
			if(json_data['message'] == "Replica not found"):
				message = 'File deleted successfully'
				response = requests.post(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'message':message})
			elif(json_data['status'] != 'Success'):
				response = requests.post(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'message':"Error: file could not be deleted properly"})
	return jsonify(
		status="Success",
		message="Replica found"
	)

### Propagating file deletion for Eventual Consistency
@app.route('/propagate_eventual_delete', methods=['GET', 'POST'])
def propagate_eventual_delete():
	unhashed_key = request.args.get('key')
	origin_id = request.args.get('origin_id')

	### Produce hash of unhashed key
	m = hashlib.sha1()
	m.update(unhashed_key.encode('utf-8'))
	key = int(m.hexdigest(),16)
	key = str(key)

	#Check if this node is reponsible for replicas of origin_id
	if(not this_node.checkExistenceInReplicaManager(origin_id)):
		return jsonify(
			status="Failed",
			message="Replica not found"
		)
	else:
		this_node.deleteFileFromReplicaManager(origin_id, key)
	return jsonify(
		status="Success",
		message="Replica found"
	)

@app.route('/query', methods=['GET', 'POST'])
def query_file():
	unhashed_key = request.args.get('key')
	client_ip = request.args.get('client_ip')
	client_port = request.args.get('client_port')
	first_node_id = request.args.get('first_node_id')
	direct_reply = True
	message = ''
	r_value = ''
	if(first_node_id is None):
		first_node_id = this_node.getId()
	elif(str(first_node_id)==str(this_node.getId())):
		print("This node id:{} != first_node_id:{}".format(first_node_id,this_node.getId()))
		return jsonify(
			status="ok",
			value = message
		)
	if(client_ip is None or client_port is None):
		client_ip = request.environ['REMOTE_ADDR']
		client_port = request.environ['REMOTE_PORT']
		direct_reply = False
	if(unhashed_key == '*'):
		message = 'sending files from the whole ring'
		response = requests.post(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'node_id':this_node.getId(), 'files':json.dumps(this_node.getFiles())})
		suc_ip = this_node.getSuccessor()['ip']
		suc_port = this_node.getSuccessor()['port']
		response = requests.get(url = "http://"+str(suc_ip)+":"+str(suc_port)+"/query", params = {'key':unhashed_key, 'client_ip':client_ip, 'client_port':client_port, 'first_node_id':first_node_id})
	else:
		### Produce hash of unhashed key
		m = hashlib.sha1()
		m.update(unhashed_key.encode('utf-8'))
		key = int(m.hexdigest(),16)
		key = str(key)

		original_node = this_node.checkFileExistenceInReplicaManager(key)
		print("Just produced this hash: {}, from this key: {}".format(key, unhashed_key))
		if(this_node.isMyKey(key)):
			if(this_node.replication_factor == 1 or (not this_node.isLinear)): #Eventual or no replication
				### Search file in this node
				if(this_node.containsFile(key)):
					message = 'File found succesfully!'
					r_value = this_node.getFiles()[str(key)][1]
				else:
					message = 'File not found!'
					r_value = 'None'
				response = requests.get(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'key':unhashed_key, 'value':r_value})

			else:
				### Propagating query to last replica manager responsible for my files
				response = requests.get(url = "http://"+str(this_node.getSuccessor()['ip'])+":"+str(this_node.getSuccessor()['port'])+"/propagate_query", \
					params = {'key':unhashed_key, 'origin_id':this_node.getId(), 'client_ip':client_ip, 'client_port':client_port})
				return jsonify(
					status='Propagating query to chain of replicas'
				)
		elif original_node>=0:
			if not this_node.isLinear:
				### Reply to cli with value stored in dedicated replica
				file_value = this_node.getFileFromReplica(original_node, key)
				if not file_value is None:
					message = 'File found succesfully!'
					r_value = file_value
				else:
					message = 'File not found!'
					r_value = 'None'
				response = requests.get(url = "http://"+str(client_ip)+":"+str(client_port)+"/", \
					params = {'key':unhashed_key, 'value':r_value, 'message':message})
			else:
				### Propagating query to last replica manager responsible for my files
				response = requests.get(url = "http://"+str(this_node.getSuccessor()['ip'])+":"+str(this_node.getSuccessor()['port'])+"/propagate_query", \
					params = {'key':unhashed_key, 'origin_id':original_node, 'client_ip':client_ip, 'client_port':client_port})
				
				json_data = json.loads(response.text)
				if(json_data['message'] == "Replica not found"):

					### I am the last replica manager for original node ---> return the key-value pair
					file_value = this_node.getFileFromReplica(original_node, key)
					if not file_value is None:
						message = 'File found succesfully!'
						r_value = file_value
					else:
						message = 'File not found!'
						r_value = 'None'
					response = requests.get(url = "http://"+str(client_ip)+":"+str(client_port)+"/", \
						params = {'key':unhashed_key, 'value':r_value, 'message':message})
				return jsonify(
					status='Propagating query to chain of replicas'
				)


		else:
			### Pass request to successor
			suc_ip = this_node.getSuccessor()['ip']
			suc_port = this_node.getSuccessor()['port']
			response = requests.get(url = "http://"+str(suc_ip)+":"+str(suc_port)+"/query", params = {'key':unhashed_key, 'client_ip':client_ip, 'client_port':client_port})
			json_data = json.loads(response.text)
			print(json_data)
			message = 'forwarding query request to my successor: {}:{}'.format(suc_ip,suc_port)

	return jsonify(
			status="ok",
			value = message
	)

### Propagating query for Chain Replication
@app.route('/propagate_query', methods=['GET', 'POST'])
def propagate_query():
	unhashed_key = request.args.get('key')
	client_ip = request.args.get('client_ip')
	client_port = request.args.get('client_port')
	origin_id = request.args.get('origin_id')

	### Produce hash of unhashed key
	m = hashlib.sha1()
	m.update(unhashed_key.encode('utf-8'))
	key = int(m.hexdigest(),16)
	key = str(key)

	#Check if this node is reponsible for replicas of origin_id
	if(not this_node.checkExistenceInReplicaManager(origin_id)):
		return jsonify(
			status="Failed",
			message="Replica not found"
		)
	else:
		response = requests.get(url = "http://"+str(this_node.getSuccessor()['ip'])+":"+str(this_node.getSuccessor()['port'])+"/propagate_query", \
			params = {'key':unhashed_key, 'origin_id':origin_id, 'client_ip':client_ip, 'client_port':client_port})
		if(not str(response.status_code) == '200'):
			response = requests.post(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'message':"Error"})
		else:
			json_data = json.loads(response.text)
			if(json_data['message'] == "Replica not found"):

				### I am the last replica manager for original node ---> return the key-value pair
				file_value = this_node.getFileFromReplica(origin_id, key)
				if not file_value is None:
					message = 'File found succesfully!'
					r_value = file_value
				else:
					message = 'File not found!'
					r_value = 'None'
				response = requests.get(url = "http://"+str(client_ip)+":"+str(client_port)+"/", \
					params = {'key':unhashed_key, 'value':r_value, 'message':message})

			elif(json_data['status'] != 'Success'):
				response = requests.post(url = "http://"+str(client_ip)+":"+str(client_port)+"/", params = {'message':"Error"})
	return jsonify(
		status="Success",
		message="Replica found"
	)


@app.route('/send_keys_to_predecessor', methods=['GET', 'POST'])
def send_keys_to_predecessor():
	id = request.args.get('id')
	old_pred_id = request.args.get('old_pred_id')
	ip = request.args.get('ip')
	port = request.args.get('port')
	print("Request to send keys to predecessor")
	pred = {'id' : id, 'ip' : ip, 'port': port}

	new_pred_id = id

	if(this_node.getId() != new_pred_id):	#Do not do this to myself if I am the coordinator
		###Send appropriate files to predecessor
		#Compute dictionary to send to predecessor
		transfer_dict = {}
		mark_to_remove = []
		
		for key, value in this_node.getFiles().items():
			if(not this_node.isMyKey(key)):
				transfer_dict[key] = value
				mark_to_remove.append(key)

		#Remove entries from this node's dictionary
		for key in mark_to_remove:
			this_node.deleteFile(key)

		#Send dictionary with http POST request
		print("Sending http post to: {}:{}/{}".format(str(ip),str(port), "accept_files"))
		response = requests.post(url = "http://"+str(ip)+":"+str(port)+"/accept_files", params = {'files':json.dumps(transfer_dict)})

		### Notify coordinator to remove keys  - from the nodes that keep my replicas - that I just send to predecessor from my dedicated replica
		print("Sending http post to: {}:{}/{}".format(this_node.cord_ip,this_node.cord_port, "notify_replica_removals"))
		response = requests.post(url = "http://"+this_node.cord_ip+":"+this_node.cord_port+"/notify_replica_removals", \
			params = {'keys':json.dumps(mark_to_remove), 'id':this_node.getId()})


	### Completed File Transfer
	return jsonify(
			status="Success"
	)

### Forward list with keys to delete from a replica of a node to its keepers
@app.route('/notify_replica_removals', methods=['GET', 'POST'])
def notify_replica_removals():
	if this_node.is_coordinator():
		id_node = request.args.get('id')
		id_node = int(id_node)
		#list with keys to be deleted
		files = request.args.get('keys')
		if(not (files is None)):
			keys_to_delete = json.loads(files)
		else:
			return jsonify(
			message = "Empty key list",
			)
		

		#Find successor
		current_index = chord_ids.index(id_node)

		for k in range (1, this_node.replication_factor):
			index_suc = current_index + 1
			if(index_suc == len(chord_ids)):
				index_suc = 0

			ip_suc = chord_nodes[chord_ids[index_suc]]['ip']
			port_suc = chord_nodes[chord_ids[index_suc]]['port']
			response = requests.post(url = "http://"+ip_suc+":"+port_suc+"/remove_from_dedicated_replica", \
				params = {'keys':json.dumps(keys_to_delete), 'id':id_node})

		return jsonify(
			message = "Success",
		)

	else:
		return jsonify(
			message = "I am not the coordinator",
		)

###	My predecessor informs me that he has given keys to his (new) predecessor
### And I must delete them from his replica (that I keep)
@app.route('/remove_from_dedicated_replica', methods=['GET', 'POST'])
def remove_from_dedicated_replica():
	id = request.args.get('id')
	id = int(id)
	files = request.args.get('keys')

	if(not (files is None)):
		keys_to_delete = json.loads(files)
	else:
		return jsonify(
		message = "Empty key list",
		)

	for key in keys_to_delete:
		this_node.deleteFileFromReplicaManager(id,key)

	return jsonify(
		message = "Success",
		)
	

@app.route('/update_predecessor', methods=['GET', 'POST'])
def update_predecessor():
	id = request.args.get('id')
	ip = request.args.get('ip')
	port = request.args.get('port')
	print("Request to update predecessor")
	pred = {'id' : id, 'ip' : ip, 'port': port}
	old_pred_id = this_node.getPredecessor()['id']
	
	this_node.setPredecessor(pred)
	
	print("Just updated my predecessor with id:{}, ip:{}, port:{}".format(id,ip,port))

	### Completed Predecessor update
	return jsonify(
			status="Success"
	)

@app.route('/update_successor', methods=['GET', 'POST'])
def update_successor():
	id = request.args.get('id')
	ip = request.args.get('ip')
	port = request.args.get('port')
	print("Request to update successor")
	suc = {'id' : id, 'ip' : ip, 'port': port}
	this_node.setSuccessor(suc)
	print("Just updated my successor with id:{}, ip:{}, port:{}".format(id,ip,port))
	return jsonify(
			status="Success"
		)



@app.route('/node_list', methods=['GET', 'POST'])
def node_list():
	if(this_node.is_coordinator()):
		json_reply = {}
		for i in range(len(chord_ids)):
			curr_id = chord_ids[i]
			curr_ip = chord_nodes[curr_id]['ip']
			curr_port = chord_nodes[curr_id]['port']
			json_reply['node-'+str(i)] = 'ID: '+ str(curr_id)+ ' -- IP:'+ str(curr_ip) + ' -- PORT: '+ str(curr_port)

		return jsonify(
			# message="Connected nodes: " + str(len(chord_nodes)),
			# nodes = json.dumps(dict (chord_nodes))
			message = "Connected nodes: " + str(len(chord_ids)),
			nodes = json_reply
		)
	else:
		return jsonify(
			message = "I am not the coordinator",
		)

@app.route('/my_files', methods=['GET', 'POST'])
def my_files():
	all_files = this_node.getFiles()
	return jsonify(
		# message="Connected nodes: " + str(len(chord_nodes)),
		# nodes = json.dumps(dict (chord_nodes))
		message = "All files of this node : " + str(len(all_files)),
		files = all_files
	)

#Return all replicas kept for other nodes
@app.route('/my_replicas', methods=['GET', 'POST'])
def my_replicas():
	all_files = this_node.getReplicaManager()
	return jsonify(
		# message="Connected nodes: " + str(len(chord_nodes)),
		# nodes = json.dumps(dict (chord_nodes))
		message = "All replicas kept from other nodes of this node : " + str(len(all_files)),
		files = all_files
	)
	
### New node hits this endpoint when he is ready to accept files
@app.route('/accept_initialized_node', methods=['GET', 'POST'])
def acceptInitializedNode():
	if this_node.is_coordinator():
		id_node = request.args.get('id')
		id_node = int(id_node)
		ip_node = request.args.get('ip')
		port_node = request.args.get('port')

		#Find successor
		current_index = chord_ids.index(id_node)

		index_suc = current_index + 1
		if(index_suc == len(chord_ids)):
			index_suc = 0
		
		ip_suc = chord_nodes[chord_ids[index_suc]]['ip']
		port_suc = chord_nodes[chord_ids[index_suc]]['port']

		#Find predecessor of new node (to pass as old_pred_id to the successor)
		old_pred_id = current_index-1
		if(old_pred_id == -1):
			old_pred_id = len(chord_ids)-1
	
		###Notify Successor to send keys to predeccessor (who is the new node)
		response = requests.get(url = "http://"+ip_suc+":"+port_suc+"/send_keys_to_predecessor", params = {'id':id_node, 'ip':ip_node, 'port':port_node, 'old_pred_id': old_pred_id})
		print(response.content)
		json_data = json.loads(response.text)
		if(json_data['status'] == "Success"):
			#Tell new node that he is ready to send replicas of himself
			response = requests.get(url = "http://"+ip_node+":"+port_node+"/confirm_ready_to_send_replicas", params = {})


		return jsonify(
	    	answer="Success"
	    	#id=id_node
		)
	
	else:
		return jsonify(
	    answer="Fail, I am not the coordinator",
	    #id=id_node
		)

### Coordinator says I am ready to send my replicas to successors
### And subsequently we know it is time to seek replicas from sources
@app.route('/confirm_ready_to_send_replicas', methods=['GET', 'POST'])
def confirm_ready_to_send_replicas():
	### First take copies of replicas from successors
	this_node.find_replica_sources()

	### Send replicas of my keys to successor
	this_node.find_my_replicas_keepers()
	return jsonify(
	    	answer="Success"
	    	#id=id_node
		)

### A node has departed and his keys have been forwaded to his successor
### The coordinator now notifies nodes that must get a replica as a result from the departure
@app.route('/confirm_clean_exit', methods=['GET', 'POST'])
def confirm_clean_exit():
	### for replication factor k:
	### k - 1 nodes must learn a replica
	### node k-i (succesor) must learn the replica of node -i (predecessor)
	id_node = request.args.get('id')
	id_node = int(id_node)
	current_index = chord_ids.index(id_node)

	#Find first predecessor
	current_pred = current_index

	for k in range(1, this_node.replication_factor):
		#Find predecessor
		current_pred = current_index-1
		if(current_pred == -1):
			current_pred = len(chord_ids)-1

		#Find k-1 successor of current index
		index_suc = current_index + this_node.replication_factor - k
		if(index_suc >= len(chord_ids)):
			index_suc -= len(chord_ids) 

		### send request to current suc to learn replica from current_pred
		ip_suc = chord_nodes[chord_ids[index_suc]]['ip']
		port_suc = chord_nodes[chord_ids[index_suc]]['port']

		ip_pred = chord_nodes[chord_ids[current_pred]]['ip']
		port_pred = chord_nodes[chord_ids[current_pred]]['port']

		response = requests.get(url = "http://"+ip_suc+":"+port_suc+"/get_replicas_from_predecessor", params = {'id': chord_ids[current_pred],'ip':ip_pred, 'port':port_pred})
	
	### Also, the successor of the departed node gets new keys. The coordinator must tell his successors that have his replicas to renew them
	index_suc_new_keys = current_index + 1
	if(index_suc_new_keys >= len(chord_ids)):
		index_suc_new_keys -= len(chord_ids)
	ip_suc_new_keys = chord_nodes[chord_ids[index_suc_new_keys]]['ip']
	port_suc_new_keys = chord_nodes[chord_ids[index_suc_new_keys]]['port']
	
	cur_suc = index_suc_new_keys
	for k in range(1,this_node.replication_factor):
		cur_suc = cur_suc + 1
		if(cur_suc == len(chord_ids)):
			cur_suc = 0
		
		ip_suc = chord_nodes[chord_ids[cur_suc]]['ip']
		port_suc = chord_nodes[chord_ids[cur_suc]]['port']
		response = requests.get(url = "http://"+ip_suc+":"+port_suc+"/get_replicas_from_predecessor", \
			params = {'id': chord_ids[index_suc_new_keys],'ip':ip_suc_new_keys, 'port':port_suc_new_keys})

	
	### Notify successors of the departing node to delete his replicas
	suc_index = current_index
	for k in range(1, this_node.replication_factor):
		suc_index = suc_index + 1
		if(suc_index == len(chord_ids)):
			suc_index = 0
		ip_suc = chord_nodes[chord_ids[suc_index]]['ip']
		port_suc = chord_nodes[chord_ids[suc_index]]['port']

		response = requests.get(url = "http://"+ip_suc+":"+port_suc+"/delete_replicas", params = {'id': chord_ids[current_index]})


	### Remove the node that departs from ring
	del chord_nodes[id_node]
	del chord_ids[chord_ids.index(id_node)]

	return jsonify(
        status="Success"
    )

### After a node has departed, coordinator informs me of a replica I have to keep
@app.route('/get_replicas_from_predecessor', methods=['GET', 'POST'])
def get_replicas_from_predecessor():
	id_of_pred = request.args.get('id')
	id_of_pred = int(id_of_pred)
	ip_node = request.args.get('ip')
	port_node = request.args.get('port')
	response = requests.get(url = "http://"+ip_node+":"+port_node+"/my_files", params = {})
	json_data = json.loads(response.text)
	replica_dict = json_data['files']
	#print(replica_dict)
	this_node.replica_manager[int(id_of_pred)] = replica_dict

	return jsonify(
        status="Success"
    )



@app.route('/accept_node', methods=['GET', 'POST'])
def acceptNode():
	if this_node.is_coordinator():
		id_node = request.args.get('id')
		id_node = int(id_node)
		ip_node = request.args.get('ip')
		port_node = request.args.get('port')
		#Put new node in node list
		chord_nodes[id_node] = {'ip' : ip_node, 'port' : port_node}
		bisect.insort(chord_ids, id_node)	# Keep id in separate list
		
		current_index = chord_ids.index(id_node)
		### find pred 
		index_pred = current_index-1
		if(index_pred == -1):
			index_pred = len(chord_ids)-1
		
		ip_pred = chord_nodes[chord_ids[index_pred]]['ip']
		port_pred = chord_nodes[chord_ids[index_pred]]['port']

		### Update Successor of Predecessor
		#req1 = "http://"+str(ip_pred)+":"+str(port_pred)+"/update_successor?id="+str(id_node)+ '&ip='+str(ip_node)+'&port='+str(port_node)
		response = requests.get(url = "http://"+str(ip_pred)+":"+str(port_pred)+"/update_successor", params = {'id':id_node, 'ip':ip_node, 'port':port_node})

		### find successor
		index_suc = current_index + 1
		if(index_suc == len(chord_ids)):
			index_suc = 0

		ip_suc = chord_nodes[chord_ids[index_suc]]['ip']
		port_suc = chord_nodes[chord_ids[index_suc]]['port']

		### Update Predecessor of Successor
		#req2 = "http://"+ip_suc+":"+port_suc+"/update_predecessor?id="+str(id_node)+ '&ip='+str(ip_node)+'&port='+str(port_node)
		response = requests.get(url = "http://"+ip_suc+":"+port_suc+"/update_predecessor", params = {'id':id_node, 'ip':ip_node, 'port':port_node})

		# ##perform async requests
		# responses = loop.run_until_complete(asyncio.gather(
        # fetch(req1),
        # fetch(req2),
    	# ))
		# fight(responses)

		### Sending message to k-1 successors (k is the replication factor) to forget their (new) k-predecessor's replica
		current_index = chord_ids.index(id_node)
		pending_successors = this_node.replication_factor - 1
		current_successor = current_index
		while(pending_successors>0):
			current_successor = current_successor + 1
			if(current_successor == len(chord_ids)):
				current_successor = 0
			
			### Find k-predecessor id
			current_predecessor = current_successor
			pending_predecessors = this_node.replication_factor
			while(pending_predecessors>0):
				current_predecessor -= 1
				if(current_predecessor == -1):
					current_predecessor = len(chord_ids)-1
				
				# pair(current_successor forget about current_predecessor)
				cur_suc_ip = chord_nodes[chord_ids[current_successor]]['ip']
				cur_suc_port = chord_nodes[chord_ids[current_successor]]['port']

				if(ip_node != cur_suc_ip):
					response = requests.get(url = "http://"+cur_suc_ip+":"+cur_suc_port+"/delete_replicas", params = {'id':chord_ids[current_predecessor]})

					json_data = json.loads(response.text)
					if(json_data['status'] == "Success"):
						print("Informed {} to delete replicas of node: {}".format(current_successor, chord_ids[current_predecessor]))

				#Update pending predecessors
				pending_predecessors -= 1
				
			pending_successors -=1
		### 

		return jsonify(
        status="Success",
        pred_id = str(chord_ids[index_pred]),
		pred_ip = str(ip_pred),
		pred_port = str(port_pred),

		suc_id = str(chord_ids[index_suc]),
		suc_ip = str(ip_suc),
		suc_port = str(port_suc)
    )
	else:
		return jsonify(
        answer="Fail",
        #id=id_node
    )


### Coordinator hits this endpoint to inform a node about a predecessor that the node no longer needs to keep a replica
@app.route('/delete_replicas', methods=['GET', 'POST'])
def delete_replicas():
	id = request.args.get('id')
	id = int(id)

	this_node.deleteFromReplicaManager(id)
	
	return jsonify(
			status="Success"
		)


#Reply with the nodes that the client needs to keep replicas from
@app.route('/get_replica_sources', methods=['GET', 'POST'])
def get_replica_sources():
	if this_node.is_coordinator():
		id_node = request.args.get('id')
		id_node = int(id_node)
		ip_node = request.args.get('ip')
		port_node = request.args.get('port')
		
		current_index = chord_ids.index(id_node)
		pending_replicas = int(this_node.getReplicationFactor()) -1
		replica_sources_list = []

		index_pred = current_index-1
		while(pending_replicas >0):
			if(index_pred == -1):
				index_pred = len(chord_ids)-1
			if(index_pred == current_index): break
			#add index_pred info to return node list
			replica_sources_list.append([str(chord_ids[index_pred]), str(chord_nodes[chord_ids[index_pred]]['ip']), str(chord_nodes[chord_ids[index_pred]]['port'])])
			#check if there are not enough nodes for the replication factor
			index_pred -= 1
			pending_replicas -= 1
			
		return jsonify(
        status="Success",
        replica_sources = replica_sources_list
    	)
	else:
		return jsonify(
        answer="Fail: I am not the coordinator",
        #id=id_node
    	)



#Reply with the nodes responsible for the replicas of the asking node
@app.route('/get_replica_keepers', methods=['GET', 'POST'])
def get_replica_keepers():
	if this_node.is_coordinator():
		id_node = request.args.get('id')
		id_node = int(id_node)
		ip_node = request.args.get('ip')
		port_node = request.args.get('port')
		
		current_index = chord_ids.index(id_node)
		pending_replicas = int(this_node.getReplicationFactor()) -1
		replica_keepers_list = []

		index_suc = current_index+1
		while(pending_replicas >0):
			if(index_suc == len(chord_ids)):
				index_suc = 0
			if(index_suc == current_index): break
			#add index_pred info to return node list
			replica_keepers_list.append([str(chord_ids[index_suc]), str(chord_nodes[chord_ids[index_suc]]['ip']), str(chord_nodes[chord_ids[index_suc]]['port'])])
			#check if there are not enough nodes for the replication factor
			index_suc += 1
			pending_replicas -= 1
			
		return jsonify(
        status="Success",
        replica_keepers = replica_keepers_list
    	)
	else:
		return jsonify(
        answer="Fail: I am not the coordinator",
        #id=id_node
    )


@app.route('/depart_node', methods=['GET', 'POST'])
def acceptDeparture():
	if this_node.is_coordinator():
		id_node = request.args.get('id')
		id_node = int(id_node)
		ip_node = request.args.get('ip')
		port_node = request.args.get('port')

		### Find predecessor
		pred_id_index = chord_ids.index(id_node) - 1
		if(pred_id_index == -1):
			pred_id_index = len(chord_ids)-1

		pred_id = chord_ids[pred_id_index]
		pred_ip = chord_nodes[pred_id]["ip"]
		pred_port = chord_nodes[pred_id]["port"]
		
		### Find Successor
		suc_id_index = chord_ids.index(id_node) + 1
		if(suc_id_index == len(chord_ids)):
			suc_id_index = 0

		suc_id = chord_ids[suc_id_index]
		suc_ip = chord_nodes[suc_id]["ip"]
		suc_port = chord_nodes[suc_id]["port"]

		### Update Successor of Predecessor	
		response = requests.get(url = "http://"+str(pred_ip)+":"+str(pred_port)+"/update_successor", params = {'id':suc_id, 'ip':suc_ip, 'port':suc_port})

		### Update Precessor of Successor
		response = requests.get(url = "http://"+suc_ip+":"+suc_port+"/update_predecessor", params = {'id':pred_id, 'ip':pred_ip, 'port':pred_port})

		### id of departed node must be deleted from chord_ids, but we 
		### do that after the clean exit confirmation to properly circulate replicas


		return jsonify(
        status="Success",
		message="So long, and thanks for all the fish"
        #id=id_node
		)
		

	else:
		return jsonify(
        answer="Fail\n =Giati milas se mena",
        #id=id_node
		)

### Initiate self-departure
@app.route('/self_depart', methods=['GET'])
def self_depart():

    #New thread to request coordinator for files
	app_thread = threading.Thread(target=depart_fun, args=())
	app_thread.start()


	return jsonify(
        status="Success",
		message="So long, and thanks for all the fish"
        #id=id_node
		)

def kill_proc_tree(pid, including_parent=True):    
    parent = psutil.Process(pid)
    for child in parent.get_children(recursive=True):
        child.kill()
    if including_parent:
        # Set the db terminate flag.

        # the next step will kill the whole process
        parent.kill()

# when Db flag iss set run this function
def terminate():
    me = os.getpid()
    kill_proc_tree(me)

def depart_fun():
	time.sleep(1)
	### Initiate Departure Procedure

	#Announce Departure to Coordinator
	if(this_node.is_coordinator()):
		terminate()
	
	this_node.announce_departure()
	#Before dying, send keys to successor
	sendKeysToSuccessor()

	### Notify coordinator of clean exit to begin process of replica circulation
	cord_ip = this_node.getCoordIp()
	cord_port = this_node.getCoordPort()
	response = requests.get(url = "http://"+str(cord_ip)+":"+str(cord_port)+"/confirm_clean_exit", params = {'id':this_node.getId()})


	#terminate()
	os.kill(int(os.getpid()), signal.SIGINT)  	

def sendKeysToSuccessor():
	print("Sending all my files to my successor {}:{}".format(this_node.getSuccessor()['ip'], this_node.getSuccessor()['port']))
	#print("Sending my keys...")
	response = requests.post(url = "http://"+str(this_node.getSuccessor()['ip'])+":"+str(this_node.getSuccessor()['port'])+"/accept_files", params = {'files':json.dumps(this_node.getFiles())})
	json_data = json.loads(response.text)
	print("Response from key sending: ",json_data)

def signal_handler(sig, frame):
	print('You pressed Ctrl+C!')	
	print("This node will depart and die...")
	### Initiate Departure Procedure

	#Announce Departure to Coordinator
	if(this_node.is_coordinator()):
		sys.exit(0)
	
	this_node.announce_departure()
	#Before dying, send keys to successor
	sendKeysToSuccessor()

	### Notify coordinator of clean exit to begin process of replica circulation
	cord_ip = this_node.getCoordIp()
	cord_port = this_node.getCoordPort()
	response = requests.get(url = "http://"+str(cord_ip)+":"+str(cord_port)+"/confirm_clean_exit", params = {'id':this_node.getId()})

	sys.exit(0)


def thread_fun():
	if not currentNode.is_coordinator():
		#print("Perfectly executable code after new thread is up and running")
		cord_ip = this_node.getCoordIp()
		cord_port = this_node.getCoordPort()
		time.sleep(1)
		response = requests.get(url = "http://"+str(cord_ip)+":"+str(cord_port)+"/accept_initialized_node", params = {'id':this_node.getId(), 'ip':this_node.getIp(), 'port':this_node.getPort()})



#input parameters: coordinator: port & replication factor & consistency_type 
#input parameters: slave: port & replication factor &  consistency_type & coord_ip & coord_port 
if __name__ == '__main__':
	domain = '192.168.0.2'
	port = sys.argv[1]

	if len(sys.argv) == 6:
		currentNode = nd.Node(domain,port, cord_ip = sys.argv[4], cord_port = sys.argv[5], replication_factor = sys.argv[2], consistency_type = sys.argv[3])
	else:
		currentNode = nd.Node(domain,port, replication_factor = sys.argv[2], consistency_type = sys.argv[3])
	if currentNode.is_coordinator():
		#Update chord_nodes 
		chord_nodes[currentNode.getId()] = {"ip" : currentNode.getIp(), "port" : currentNode.getPort()}
		bisect.insort(chord_ids, currentNode.getId())
	this_node = currentNode

	#New thread to request coordinator for files
	app_thread = threading.Thread(target=thread_fun, args=())
	app_thread.start()

	### Create Handler for exit signal
	signal.signal(signal.SIGINT, signal_handler)

	app.run(host='192.168.0.2', threaded = True, port=int(sys.argv[1]))


	


	




