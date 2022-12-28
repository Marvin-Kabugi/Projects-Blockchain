import hashlib
import json
def hash_string(string):
    return hashlib.sha256(string).hexdigest()

def hash_function(block):
    hashable_block = block.__dict__.copy()
    # print(hashable_block)
    hashable_block['transactions'] = [tx.to_ordered_dict() for tx in hashable_block['transactions']]
    return hash_string(json.dumps(hashable_block, sort_keys=True).encode())