import hashlib
import json
from time import time

from textwrap import dedent
from uuid import uuid4

from flask import Flask, jsonify, request
from urllib.parse import urlparse
import requests


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transations = []

        # create the genesis block
        self.new_block(previous_hash=1,proof= 100)

        # use a set collection to keep the registered nodes
        self.nodes = set()

    def valid_chain(self,chain):

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(last_block)
            print(block)
            print("\n######\n")

            if block['previous_hash'] != self.hash(last_block):
                return False
            # check the pow
            if not self.valid_proof(last_block['proof'],block['proof']):
                return False
            last_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        """
        resolves conlicts by replacing chain with longest one in the network.
        :return:
        """
        neighbors = self.nodes
        new_chain = None

        # looking for the chain longer than self
        max_len = len(self.chain)

        for node in neighbors:
            # get the neighbour node's chain
            response = requests.get(str.format("http://{0}/chain",node))
            if response.status_code == 200:
                length = response.json()['lenght']
                chain = response.json()['chain']

                if length > max_len and self.valid_chain(chain):
                    max_len = length;
                    new_chain = chain

        # replace current chain with the longer one
        if new_chain:
            self.chain = new_chain
            return True

        return False









    def register_node(self,address):
        """
         add a new node to the list of nodes
        :param address:  <str> address of node , eg: "http://192.168.1.1:5000"
        :return:  None
        """
        parsed_url = urlparse(address)

        self.nodes.add(parsed_url.netloc)



    def new_block(self,proof,previous_hash=None):
        """
        Create a new Block in the BlcokChain

        :param proof: <int> the proof given by the proof of work algorithm
        :param previous_hash:  (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """
        block = {
            'index': len(self.chain)+1,
            'timestamp':time(),
            'transactions':self.current_transations,
            'proof':proof,
            'previous_hash':previous_hash or self.hash(self.chain[-1]),
        }
        # reset the current list of transactions
        self.current_transations = []
        self.chain.append(block)
        return block

    def new_transaction(self,sender,recipient,amount):
        """
        Create a new transation to go into the next mined Block

        :param sender: <str> Address of the Sender
        :param recipient:  <str> Address of the Recipient
        :param amount:  <int> Amount
        :return: <int> the index of the Block that will hold this transation
        """
        self.current_transations.append({
            'sender':sender,
            'recipient':recipient,
            'amount':amount,
        })
        return self.last_block['index']+1


    @staticmethod
    def hash(block):
        # Hashes a Block
        """
         create a SHA-256 hash of a Block

        :param block: <dict> Block
        :return: <str> the hash code the the given block
        """
        block_string = json.dumps(block,sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # Returns the last Block in the chain
        return self.chain[-1]


    def proof_of_work(self,last_proof):
        """

        :param last_proof:
        :return:
        """
        proof = 0
        while self.valid_proof(last_proof,proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof,proof):
        #guess = f'{last_proof}{proof}'.encode()
        guess = str.format("{0}{1}",last_proof,proof)
        guess = guess.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    # we run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    # get the last proof and work out the proof of current block.
    proof = blockchain.proof_of_work(last_proof)
    print("mined out a proof->",proof)

    # we must receive a reward for finding the proof.
    # the sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof,previous_hash)

    # return the message of new block.
    response = {
        'message':"New Block Forged",
        'index':block['index'],
        'transactions':block['transactions'],
        'proof':block['proof'],
        'previous_hash':block['previous_hash'],
    }

    #return "We'll mine a new Block"\
    return jsonify(response),200



@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    print(values)


    required = ['sender','recipient','amount']
    if not all(k in values for k in required):
        return 'Missing values',400

    index = blockchain.new_transaction(values['sender'],values['recipient'],values['amount'])
    response = {'message':str.format("Transacton will be added to Block ",index)}
    return jsonify(response),201

@app.route('/tt',methods=["POST"])
def new_tt():
    return "post method works"


# export registe_node method as an api
@app.route('/nodes/register',methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return "Error please supply a valid list of nodes",400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message':'New nodes have been added',
        'total_nodes':list(blockchain.nodes),
    }
    return jsonify(response),201

@app.route('/nodes/resolve',methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message':'current chain was replaced',
            'new_chain':blockchain.chain,
        }
    else:
        response = {
            'message':'current chain is main chain',
            'chain':blockchain.chain,
        }
    return jsonify(response),200

# NOTE!! this line of code must be under all @app.route(),
# or it won't match the urls. and return 404 error.
if __name__ == '__main__':
    app.run(host=None, port=5001)

