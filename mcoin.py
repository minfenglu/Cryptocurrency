import datetime
import hashlib
import json
from flask import Flask, jsonify, request
import requests
from uuid import uuid4
from urllib.parse import urlparse

####################################
# buid a Blockchain
####################################
class Blockchain:
    
    def __init__(self):
        # initialize the chain
        self.chain = []
        self.transactions = []
        # create genesis block
        self.create_block(proof = 1, previous_hash = '0')
        self.nodes = set()
        
    def create_block(self, proof, previous_hash):
        block = {'index': len(self.chain) + 1,
                 'timestamp': str(datetime.datetime.now()),
                 'proof': proof,
                 'previous_hash': previous_hash,
                 'transactions': self.transactions}
        self.transactions = []
        self.chain.append(block)
        return block    
    
    def get_previous_block(self):
        return self.chain[-1]
    
    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while check_proof is False:
            # operation should not be symmetrical 
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            # 4 leading 0's
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof = new_proof + 1
        return new_proof

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            # check previous_hash
            if block['previous_hash'] != self.hash(previous_block):
                return False
            # each proof is valid
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':    
                return False
            previous_block = block
            block_index = block_index+ 1
        return True
    
    def add_transaction(self, sender, receiver, amount):
        self.transactions.append({'sender': sender,
                                  'receiver': receiver,
                                  'amount': amount})
        previous_block = self.get_previous_block()
        return previous_block['index'] + 1
    
    def add_node(self, address):
        parsed_url = urlparse(address)
        # if the address is 'http://127.0.0.1:5000/'
        # the netloc will be 127.0.0.1:5000
        self.nodes.add(parsed_url.netloc)
    
    # replace the chain with the longest valid one
    def replace_chain(self):
        # a decentralized network
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            # make a request with different port number
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        return False
    
####################################        
# mine the Blockchain
####################################        
# create a web app
app = Flask(__name__)

# create an address for the node on Port 5000
node_address = str(uuid4()).replace('-','')

# create a block chain
blockchain = Blockchain()

# mine a new block
@app.route('/mine_block', methods = ['GET'])
def mine_block():
    previous_block = blockchain.get_previous_block()
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)
    previous_hash = blockchain.hash(previous_block)
    blockchain.add_transaction(sender = node_address, receiver = 'Minfeng', amount = 1)
    block = blockchain.create_block(proof, previous_hash)
    response = {'message': 'Congratulations! You just mined a block.',
                'index': block['index'],
                'timestamp': block['timestamp'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
                'transactions': block['transactions']}
    return jsonify(response), 200

# get the full blockchain
@app.route('/get_chain', methods = ['GET'])    
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200

@app.route('/is_valid', methods = ['GET'])
def is_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    if is_valid:
        response = {'message': 'The blockchain is valid'}
    else:
        response = {'message': 'The blockchain is not valid'}
    return jsonify(response), 200

# add a new transaction to the blockchain
@app.route('/add_transaction', methods = ['POST'])
def add_transaction():
    json = request.get_json()
    transaction_keys = ['sender', 'receiver', 'amount']
    if not all (key in json for key in transaction_keys):
        return 'Missing some keys for the transaction information', 400, 
    sender = json['sender']
    receiver = json['receiver']
    amount = json['amount']
    index = blockchain.add_transaction(sender, receiver, amount)
    response = {'message': f'This transaction will be added to Block {index} from {sender} to {receiver} with {amount} M coins'}
    return jsonify(response), 201
    
####################################
# Decentralize the blockchain
####################################

# connect new nodes
# example json to post: {'nodes': ['http://127.0.0.1:5000', 'http://127.0.0.1:5001', 'http://127.0.0.1:5002']}
@app.route('/connect_node', methods = ['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes')
    if nodes is None:
        return "No node", 400
    for node in nodes:
        blockchain.add_node(node)
    response = {'message': 'All the nodes are now connected',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201    
 
# replace the chain by the longest chain if needed
@app.route('/replace_chain', methods = ['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message': 'The nodes have different chains and the chain is replaced by the longest one',
                    'new_chain': blockchain.chain}
    else:
        response = {'message': 'The chain does not need to be replaced',
                    'actual_chain': blockchain.chain}
    return jsonify(response), 200    
    
        
    

# run the app
app.run(host = '0.0.0.0', port = 5000)    


