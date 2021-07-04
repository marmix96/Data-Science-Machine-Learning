import hashlib
import json
import requests 

class Node:
	def __init__(self,ip,port,cord_ip=None,cord_port=None, replication_factor=1, consistency_type=None):
		m = hashlib.sha1()
		self.my_ip = str(ip)
		#print("Just encoded this: {}".format(self.my_ip))
		self.my_port = str(port)
		m.update(self.my_ip.encode('utf-8')+self.my_port.encode('utf-8'))
		self.id = int(m.hexdigest(),16)
		self.my_ip = self.my_ip
		self.my_port = self.my_port
		self.files = {}	# keys are str
		self.replication_factor = int(replication_factor)
		self.replica_manager = {}	# Replica Manager Dictionary: {node, replicas_of_that_node_dict} SOS: to key einai int
		#Save the appropriate consistency mode
		if(consistency_type == 'linearizability'):
			self.isLinear = True
		else:
			self.isLinear = False
		if cord_ip is None:
			self.cord_ip = self.my_ip
			self.cord_port = self.my_port
			self.nodes = []
			self.predecessor = {'id': self.id, 'ip' : self.my_ip, 'port' : self.my_port}
			self.successor = {'id': self.id, 'ip' : self.my_ip, 'port' : self.my_port}
		else:
			self.cord_ip = cord_ip
			self.cord_port = cord_port
			self.next_previous()
			#self.find_replica_sources()
			#self.find_my_replicas_keepers() cannot call here

	def print(self):
		return 'I am '.encode("utf-8")+self.my_ip+' with port '.encode("utf-8")+self.my_port +' and hash id '.encode("utf-8")+str(self.id).encode('utf-8')

	def announce_departure(self):
		response = requests.get(url = "http://"+self.cord_ip+":"+self.cord_port+"/depart_node", params = {'id':self.id, 'ip':self.my_ip, 'port':self.my_port})
		json_data = json.loads(response.text)
		print(json_data)

	def find_replica_sources(self):
		response = requests.get(url = "http://"+self.cord_ip+":"+self.cord_port+"/get_replica_sources", params = {'id':self.id, 'ip':self.my_ip, 'port':self.my_port})
		json_data = json.loads(response.text)

		#read list with replication sources
		source_list = json_data['replica_sources'] #replica_sources_cell : {id, ip, port} : list
		for node_info_list in source_list:
			print(node_info_list)
			#ask current_node for files
			current_node_id = node_info_list[0]
			current_node_ip = node_info_list[1]
			current_node_port = node_info_list[2]
			response = requests.get(url = "http://"+current_node_ip+":"+current_node_port+"/my_files", params = {})
			json_data = json.loads(response.text)

			replica_dict = json_data['files']
			#print(replica_dict)
			self.replica_manager[int(current_node_id)] = replica_dict

	# Ask coordinator for successors responsibles for my replicas and send my files to them
	def find_my_replicas_keepers(self):
		response = requests.get(url = "http://"+self.cord_ip+":"+self.cord_port+"/get_replica_keepers", params = {'id':self.id, 'ip':self.my_ip, 'port':self.my_port})
		json_data = json.loads(response.text)

		#read list with replication sources
		keepers_list = json_data['replica_keepers'] #replica_sources_cell : {id, ip, port} : list
		for node_info_list in keepers_list:
			print("list of keepers")
			print(node_info_list)
			#send files to current node
			current_node_id = node_info_list[0]
			current_node_ip = node_info_list[1]
			current_node_port = node_info_list[2]
			response = requests.post(url = "http://"+current_node_ip+":"+current_node_port+"/accept_replicas", params = {'id':self.id, 'files':json.dumps(self.files)})
			print(response)

	def next_previous(self):
		response = requests.get(url = "http://"+self.cord_ip+":"+self.cord_port+"/accept_node", params = {'id':self.id, 'ip':self.my_ip, 'port':self.my_port})
		json_data = json.loads(response.text)

		### Read predecessor
		id_pred = json_data['pred_id']
		ip_pred = json_data['pred_ip']
		port_pred = json_data['pred_port']
		self.predecessor = {'id': id_pred, 'ip' : ip_pred, 'port' : port_pred}
	
		### Read successor
		id_suc = json_data['suc_id']
		ip_suc = json_data['suc_ip']
		port_suc = json_data['suc_port']
		self.successor = {'id': id_suc, 'ip' : ip_suc, 'port' : port_suc}

		print("My pred is: {}:{} and my successor is: {}:{}".format(self.predecessor['ip'], self.predecessor['port'], self.successor['ip'], self.successor['port']))

	def is_coordinator(self):
		return self.my_ip == self.cord_ip and self.my_port == self.cord_port
	
	def getCoordIp(self):
		return self.cord_ip

	def getCoordPort(self):
		return self.cord_port

	def getIp(self):
		return self.my_ip

	def getPort(self):
		return self.my_port

	def getId(self):
		return self.id

	def getPredecessor(self):
		return self.predecessor

	def setPredecessor(self, new_pred):
		self.predecessor = new_pred

	def getSuccessor(self):
		return self.successor
	
	def setSuccessor(self, new_suc):
		self.successor = new_suc

	def insertFile(self, key, unhashed_key, value):
		self.files[str(key)] = (unhashed_key, value)

	def containsFile(self, key):
		return str(key) in self.files

	def deleteFile(self, key):
		del self.files[str(key)]
		return

	def getReplicationFactor(self):
		return self.replication_factor

	def isMyKey(self, key):
		if(self.predecessor['id'] == self.successor['id'] and self.predecessor['id'] == self.getId()):
			return True
		if(int(self.predecessor['id'])>int(self.id) and (int(key) > int(self.predecessor['id']) or int(key) < int(self.id))):
			return True
		return (int(key)>int(self.predecessor['id']) and int(key) <= int(self.id))

	def getFiles(self):
		return self.files
	
	def getReplicaManager(self):
		return self.replica_manager

	def appendDictionary(self, dict):
		self.files.update(dict)

	def addToReplicaManager(self, node_id, dict):
		self.replica_manager[int(node_id)] = dict
	
	def addFileToReplicaManager(self, node_id, key, unhashed_key, value):
		self.replica_manager[int(node_id)][str(key)] = (unhashed_key, value)
	
	def deleteFromReplicaManager(self, id):
		try:
			self.replica_manager.pop(int(id))
		except KeyError: #replica is not present in replica manager
			return
		
	def checkExistenceInReplicaManager(self, id):
		return int(id) in self.replica_manager.keys()
	
	#Return the original node responsible for the file or -1
	def checkFileExistenceInReplicaManager(self, file_key):
		for node_id, replica in self.replica_manager.items():
			if(file_key in replica.keys()):
				return node_id
		return -1
	
	#Return key-value pair from a replica for a node-key
	def getFileFromReplica(self, original_node_id, key):
		if int(original_node_id) in self.replica_manager.keys():
			if str(key) in self.replica_manager[int(original_node_id)].keys():
				return self.replica_manager[int(original_node_id)][str(key)][1]
		return None

	
	# Given an id and a key, delete from id's replica the key-value record (if it exists)
	def deleteFileFromReplicaManager(self, id, key):
		if int(id) in self.replica_manager.keys():
			temp_dict = self.replica_manager[int(id)]
			temp_dict.pop(str(key))
			self.replica_manager[int(id)] = temp_dict