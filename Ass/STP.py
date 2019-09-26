

class STP_Segment():
    def __init__(self, syn_bit, ack_bit, fin_bit,seq_number, ack_number, payload,lengthofdata,checksum):
        self.syn_bit = syn_bit
        self.ack_bit = ack_bit
        self.fin_bit = fin_bit
        self.seq_number = seq_number
        self.ack_number = ack_number
        self.payload = payload
        self.lengthofdata = lengthofdata
        self.checksum = checksum


