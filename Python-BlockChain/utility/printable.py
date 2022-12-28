class Printable:
    def __repr__(self):
        # return "previos_hash: {}, index: {}, transaction: {}, proof: {}".format(self.previous_hash, self.index, self.transaction, self.proof)
        return str(self.__dict__)