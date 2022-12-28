from functools import reduce
from collections import OrderedDict
import json
import pickle
from urllib import request, response
from block import Block
from utility.hash_utils import hash_function
from transaction import Transaction
from utility.verification import Verification
from wallet import Wallet
import requests

MINING_REWARD = 10
# owner = ''
# participants = {owner}

class Blockchain:
    def __init__(self, public_key, node_id):
        genesis_block = Block(0, '', [], 100, 0)
        self.chain = [genesis_block]
        self.__open_transactions = []
        self.public_key = public_key
        self.__peer_nodes = set()
        self.node_id = node_id
        self.resolve_conflicts = False
        self.load_data()

        
    @property
    def chain(self):
        return self.__chain[:]
    
    
    @chain.setter
    def chain(self, val):
        self.__chain = val

    def get_open_transaction(self):
        return self.__open_transactions[:]
        
        
    def load_data(self):
        try:
            with open('blockchain-{}.txt'.format(self.node_id), mode='r') as f:
                #using pickling to read data 
                # file_content = pickle.loads(f.read())
                # global blockchain
                # global open_transactions
                # blockchain = file_content['chain']
                # open_transactions = file_content['ot']
                #using json to read data back to the program
                file_content = f.readlines()
                self.__chain = json.loads(file_content[0][:-1])
                updated_blockchain = []
                for block in self.__chain:
                    converted_txt = [Transaction(tx['sender'], tx['receiver'], tx['signature'], tx['amount']) for tx in block['transactions']]
                    updated_block = Block(block['index'], block['previous_hash'], converted_txt, block['proof'], block['timestamp'] )
                    updated_blockchain.append(updated_block)
                self.__chain = updated_blockchain
                self.__open_transactions = json.loads(file_content[1][:-1])
                updated_open_transactions = []
                # [OrderedDict([('sender', tx['sender']), ('receiver', tx['receiver']), ('amount', tx['amount'])]) for tx in open_transactions]
                for tx in self.__open_transactions:
                    updated_transaction = Transaction(tx['sender'], tx['receiver'], tx['signature'], tx['amount'])
                    updated_open_transactions.append(updated_transaction)
                self.__open_transactions = updated_open_transactions
                peer_nodes = json.loads(file_content[2])
                self.__peer_node = set(peer_nodes)
        except (IOError, IndexError):
            pass
        finally:
            print('Cleanup')



    def save_data(self):
        try:
            with open('blockchain-{}.txt'.format(self.node_id), mode='w') as f:
                saveable_chain = [block.__dict__ for block in [Block(block_el.index, block_el.previous_hash, [
                    tx.__dict__ for tx in block_el.transactions] , block_el.proof, block_el.timestamp) for block_el in self.__chain]]
                f.write(json.dumps(saveable_chain))
                f.write('\n')
                saveable_tx = [tx.__dict__ for tx in self.__open_transactions]
                f.write(json.dumps(saveable_tx))
                f.write('\n')
                f.write(json.dumps(list(self.__peer_nodes)))
                #using pickle to save data
                # save_data = {
                #     'chain': blockchain,
                #     'ot': open_transactions
                # }
                # f.write(pickle.dumps(save_data))
        except IOError:
            print('Saving Failed')


    def get_balance(self, sender=None):
        #returns total amount a certain participant has sent in the blockchain.
        #also returns an empty list in situations where the participant was never involved
        if sender == None:
            if self.public_key == None:
                return None
            participant = self.public_key
        else:
            participant = sender
        tx_sender = [[tx.amount for tx in block.transactions if tx.sender == participant] for block in self.__chain]
        tx_sender_open = [tx.amount for tx in self.__open_transactions if tx.sender == participant]
        tx_sender.append(tx_sender_open)
        amount_sent = reduce(lambda tx_sum, txt_amount: tx_sum + sum(txt_amount) if len(txt_amount) > 0 else tx_sum + 0, tx_sender, 0)
        # another way to calculate amount sent
        # amount_sent = 0
        # for tx in tx_sender:
        #     if len(tx) > 0:
        #         amount_sent += tx[0]
        tx_receiver = [[tx.amount for tx in block.transactions if tx.receiver == participant] for block in self.__chain]
        amount_received = reduce(lambda tx_sum, txt_amount: tx_sum + sum(txt_amount) if len(txt_amount) > 0 else tx_sum + 0, tx_receiver, 0)
        # amount_received = 0
        # for tx in tx_receiver:
        #     if len(tx) > 0:2
        #         amount_received += tx[0]
        return amount_received - amount_sent
    

# def hash_function(block):
#     return hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()
#     # return '-'.join([str(block[key]) for key in block])


    def proof_of_work(self):
        last_block = self.__chain[-1]
        last_hash = hash_function(last_block)
        proof = 0
        while not Verification.valid_proof(self.__open_transactions, last_hash, proof):
            proof += 1
        return proof


    def get_last_blockchain_item(self):
        if len(self.__chain) < 1:
            return None
        return self.__chain[-1]


    def add_transaction(self, receiver, sender, signature, amount=1.0, is_receiving=False):
        # transaction = {
        #     'sender': sender,
        #     'reciver': receiver,
        #     'amount': amount
        # }
        # if self.public_key == None:
        #     return False
        transaction = Transaction(sender, receiver, signature, amount)
        if Verification.verify_transaction(transaction, self.get_balance):
            self.__open_transactions.append(transaction)
            # participants.add(sender)
            # participants.add(receiver)
            self.save_data()
            if not is_receiving:
                for node in self.__peer_nodes:
                    url = 'http://{}/broadcast-transaction'.format(node)
                    try:
                        response = requests.post(url, json={'sender': sender, 'recepient': receiver, 'amount': amount, 'signature': signature})
                        if response.status_code == 400 or response.status_code == 500:
                            print('Transaction declined, needs resolving')
                            return False
                    except requests.exceptions.ConnectionError:
                        continue
            return True
        return False


    def mine_block(self):
        if self.public_key == None:
            return None
        last_block = self.__chain[-1]
        hashed_block = hash_function(last_block)
        proof = self.proof_of_work()   
        # for keys in last_block:
        #     value = last_block[keys]
        #     hashed_block = hashed_block + str(value)
        # reward_transaction = {
        #     'sender': 'Miner',
        #     'reciver': owner,
        #     'amount': MINING_REWARD
        # }
        reward_transaction = Transaction('MINING', self.public_key, '', MINING_REWARD)
        copied_transactions = self.__open_transactions[:] 
        for tx in copied_transactions:
            if not Wallet.verify_transaction(tx):
                return None
        copied_transactions.append(reward_transaction)
        block = Block(len(self.__chain), hashed_block, copied_transactions, proof)
        self.__chain.append(block)
        self.__open_transactions = []
        self.save_data()
        for node in self.__peer_nodes:
            url = 'http://{}/broadcast-block'.format(node)
            converted_block = block.__dict__.copy()
            converted_block['transctions'] = [tx.__dict__ for tx in converted_block['transactions']]
            try:
                response = requests.post(url, json={'block': converted_block})
                if response.status_code == 400 or response.status_code == 500:
                    print('Block declined, needs resolving')
                if response.status_code == 409:
                    self.resolve_conflicts = True
            except requests.exceptions.ConnectionError:
                continue
        return block

    def add_block(self, block):
        transactions = [Transaction(tx['sender'], tx['recepient'], tx['signature'], tx['amount']) for tx in block['transactions']]
        proof_is_valid = Verification.valid_proof(transactions[:-1], block['previous_hash'], block['valid_proof'])
        hashes_match = hash_function(self.chain[-1]) == block['previous_hash']
        if not proof_is_valid or not hashes_match:
            return False
        converted_block = Block(block['index'], block['previous_hash'], transactions, block['proof'], block['timestamp'])
        self.__chain.append(converted_block)
        stored_transactions = self.__open_transactions[:]
        for itx in block['transactions']:
            for opentx in stored_transactions:
                if opentx.sender == itx['sender'] and opentx.receiver == itx['receiver'] and opentx.amount == itx['amount'] and opentx.signature == itx['signature']:
                    try:
                        self.__open_transactions.remove(opentx)
                    except ValueError:
                        print('Item was removed')
        self.save_data()
        return True    


    def resolve(self):
        winner_chain = self.__chain
        replace = False
        for node in self.__peer_nodes:
            url = 'http://{}/chain'.format(node)  
            try:
                response = requests.get(url)
                node_chain = response.json()
                node_chain = [Block(block['index'], block['previous_hash'], [Transaction(tx['sender'], tx['receiver'], tx['signature'], tx['amount']) for tx in block['transactions']], block['proof'], block['timestamp']) for block in node_chain]
                node_chain_length = len(node_chain)
                local_chain_len = len(winner_chain)
                if node_chain_length > local_chain_len and Verification.verify_chain(node_chain):
                    winner_chain = node_chain
                    replace = True
            except requests.exceptions.ConnectionError:
                continue
        self.resolve_conflicts = False
        self.__chain = winner_chain
        if replace:
            self.__open_transactions = []
        self.save_data()
        return replace

    
    def add_peer_node(self, node):
        self.__peer_nodes.add(node)
        self.save_data()
  
    
    def remove_peer_node(self, node):
        self.__peer_nodes.discard(node)
        self.save_data()

    
    def get_peer_nodes(self):
        return list(self.__peer_nodes)
