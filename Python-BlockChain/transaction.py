from collections import OrderedDict
from utility.printable import Printable

class Transaction(Printable):
    def __init__(self, sender, receiver, signature, amount):
        self.sender = sender
        self.receiver = receiver
        self.signature = signature
        self.amount = amount
    
    
    def __repr__(self):
        return str(self.__dict__)
    
    def to_ordered_dict(self):
        return OrderedDict([('sender', self.sender), ('receiver', self.receiver), ('signature', self.signature),('amount', self.amount)])