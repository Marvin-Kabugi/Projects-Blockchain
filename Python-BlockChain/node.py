from importlib.resources import read_text
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from wallet import Wallet
from blockchainOOP import Blockchain

app = Flask(__name__)
CORS(app)


@app.route('/', methods=['GET'])
def get_node_ui():
    return send_from_directory('ui', 'node.html')


@app.route('/network', methods=['GET'])
def get_network_ui(): 
    return send_from_directory('ui', 'network.html')


@app.route('/wallet', methods=['POST'])
def create_keys():
    global blockchain
    wallet.create_keys()
    if wallet.save_keys():
        blockchain = Blockchain(wallet.public_key, port)
        response = {
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
            'funds': blockchain.get_balance()
        }
     
        return jsonify(response), 201
    else:
        response = {
            'message': 'Failed saving keys'
        }
        return jsonify(response), 500


@app.route('/wallet', methods = ['GET'])
def load_keys():
    global blockchain
    if wallet.load_keys():
        blockchain = Blockchain(wallet.public_key, port)
        response = {
            'public_key': wallet.public_key,
            'private_key': wallet.private_key,
            'funds': blockchain.get_balance()
        }
        return jsonify(response), 201
    else:
        response = {
            'Message': 'Failed loading keys'
        }
        return jsonify(response), 500

        
@app.route('/balance', methods=['GET'])
def balance():
    balance = blockchain.get_balance()
    if balance != None:
        response = {
            'message': 'Got balance succefully',
            'balance': balance
        }
        return jsonify(response), 200
    else:
        response = {
            'message': 'Error fetching balance',
            'wallet_set_up': wallet.public_key != None
        }
        return jsonify(response), 500


@app.route('/broadcast-transaction', methods=['POST'])
def broadcast_transaction():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found'
        }
        return jsonify(response), 400
    required_data = ['sender', 'recepient', 'amount', 'signature']
    if not all(key in values for key in required_data):
        response = {
        'message': 'Some data is missing'
        }
        return jsonify(response), 400
    success = blockchain.add_transaction(values['recepient'], values['sender'], values['signature'], values['amount'], is_receiving=True)
    if success:
        response = {
            'message': 'Success',
            'transaction': {
                'sender': values['sender'],
                'receiver': values['recepient'],
                'amount': values['amount'],
                'signature': values['signature']
            }
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Creating a transaction failed'
        }
        return jsonify(response), 500


@app.route('broadcast-block', methods=['POST'])
def broadcast_block():
    values = request.get_json()
    if not values:
        response = {'message': 'No data found'}
        return jsonify(response), 400
    if 'block' not in values:
        response = {'message': 'some data is missing'}
        return jsonify(response), 400
    block = values['block']
    if block['index'] == blockchain.chain[-1].index + 1:
        if blockchain.add_block(block):
            response = {'message': 'Block added'}
            return jsonify(response), 201
        else:
            response = {'message': 'Block seems invalid'}
            return jsonify(response), 409
    elif block['index'] > blockchain.chain[-1].index:
        response = {'message: blockchain seems to differ from local blockchain'}
        blockchain.resolve_conflicts = True
        return jsonify(response), 200
    else:
        response = {'message: blockchain seems to be shorter, block not added'}
        return jsonify(response), 409

@app.route('/transaction', methods=['POST'])
def add_transactions():
    if wallet.public_key == None:
        response = {
            'message': 'Failed',
            'wallet-set-up': wallet.public_key != None
        }
        return jsonify(response), 400
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data found'
        }
        return jsonify(response), 400
    
    required_fields = ['receiver', 'amount']
    if not all(field in values for field in required_fields):
        response = {
            'message': 'Missing values'
        }
        return jsonify(response), 400
    receiver = values['receiver']
    amount = values['amount']
    signature = wallet.sign_transaction(wallet.public_key, receiver, amount)
    transaction = blockchain.add_transaction(receiver, wallet.public_key, signature, amount)
    if transaction:
        response = {
            'message': 'Success',
            'transaction': {
                'sender': wallet.public_key,
                'receiver': receiver,
                'amount': amount
            },
            'balance': blockchain.get_balance()
        }
        return jsonify(response), 201
    else:
        response = {
            'message': 'Creating a transaction failed'
        }
        return jsonify(response), 500


@app.route('/mine', methods=['POST'])
def mine():
    if blockchain.resolve_conflicts:
        response = {'message': 'Resolve conflicts first, block not added'}
        return jsonify(response), 409
    block = blockchain.mine_block()
    if block != None:
        dict_block  = block.__dict__.copy()
        dict_block['transactions'] = [tx.__dict__ for tx in dict_block['transactions']]
        response = {
            'message': 'Mined block succefully',
            'block': dict_block,
            'balance': blockchain.get_balance()       
        } 
        return jsonify(response), 200
    else:
        response = {
            'message': 'Block Mining Failed',
            'wallet-set-up': wallet.public_key != None
        }
        return jsonify(response), 500

@app.route('/resolve-conflicts', methods=['POST'])
def resolve_conflicts():
    replaced = blockchain.resolve()
    if replaced:
        response = {'message': 'Chain was replaced'}
    else:
        response = {'message': 'local chain kept'}
        return jsonify(response), 200


@app.route('/transactions', methods=['GET'])
def get_open_transactions():
    transactions = blockchain.get_open_transaction()
    dict_transactions = [tx.__dict__ for tx in transactions]
    return jsonify(dict_transactions), 200
    

@app.route('/chain', methods=['GET'])
def get_chain():
    chain = blockchain.chain
    copied_chain = [block.__dict__.copy() for block in chain]
    for dict_block in copied_chain:
        dict_block['transactions'] = [tx.__dict__ for tx in dict_block['transactions']]
    return jsonify(copied_chain), 200 


@app.route('/node', methods=['Post'])
def add_node():
    values = request.get_json()
    if not values:
        response = {
            'message': 'No data attached'
        }
        return jsonify(response), 400
    
    if 'node' not in values:
        response = {
            'message': 'No node data found'
        }
        return jsonify(response), 400
    
    node = values['node']
    blockchain.add_peer_node(node)
    response = {
        'message': 'Node added successfully',
        'all_nodes': blockchain.get_peer_nodes()
    }
    return jsonify(response), 201

@app.route('/node/<node_url>', methods=['DELETE'])
def remove_node(node_url):
    if node_url == '' or node_url == None:
        response = {
            'message': 'No node found'
        }
        return jsonify(response), 400
    blockchain.remove_peer_node(node_url)
    response = {
        'message': 'Node removed',
        'all_nodes': blockchain.get_peer_nodes()
    }
    return jsonify(response), 200

@app.route('/nodes', methods=['GET'])
def get_nodes():
    nodes = blockchain.get_peer_nodes
    response = {
        'all_nodes': nodes
    }
    return jsonify(response), 200

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=3000)
    args = parser.parse_args()
    port = args.port
    wallet = Wallet(port)
    blockchain = Blockchain(wallet.public_key, port)
    app.run(host='0.0.0.0', port = port)