import sys
from socket import *
import os
import threading
from STP import STP_Segment
import pickle
import time
import hashlib
import random


class Sender:
    def __init__(self, receiver_host, receiver_port, filename, MWS, MSS, gamma, pDrop, pDuplicate, pCorrupt, pOrder, maxOrder, pDelay, maxDelay, seed):
        self.receiver_host = receiver_host
        try:
            self.receiver_port = int(receiver_port)
            if self.receiver_port <= 1024 or self.receiver_port >= 65536:
                raise ValueError
            if not os.path.exists(filename):
                raise ValueError
            self.filename = filename
            self.MWS = int(MWS)
            if self.MWS < 0:
                raise ValueError
            self.MSS = int(MSS)
            if self.MSS < 0:
                raise ValueError
            if self.MSS > self.MWS:
                self.MSS = self.MWS
            self.gamma = int(gamma)
            if self.gamma < 0:
                raise ValueError
            self.pDrop = float(pDrop)
            if self.pDrop < 0 or self.pDrop > 1:
                raise ValueError
            self.pDuplicate = float(pDuplicate)
            if self.pDuplicate < 0 or self.pDuplicate > 1:
                raise ValueError
            self.pCorrupt = float(pCorrupt)
            if self.pCorrupt < 0 or self.pCorrupt > 1:
                raise ValueError
            self.pOrder = float(pOrder)
            if self.pOrder < 0 or self.pOrder > 1:
                raise ValueError
            self.maxOrder = int(maxOrder)
            if self.maxOrder < 0 or self.maxOrder > 6:
                raise ValueError
            self.pDelay = float(pDelay)
            if self.pDelay <0 or self.pDelay > 1:
                raise ValueError

            self.maxDelay = int(maxDelay)
            self.seed = int(seed)
        except ValueError:
            print('invalid parameter!')
            sys.exit()

        self.seq_number = 0
        self.ack_number = 0
        self.socket = socket(AF_INET, SOCK_DGRAM)
        self.retransmit_packet = 0
        self.duplicate_packet = 0
        self.drop_packet = 0
        self.delay_packet = 0
        self.corrupt_packet = 0
        self.reorder_packet = 0
        self.count = 0
        self.DevRTT = 250/1000
        self.EstimatedRTT = 500/1000
        self.TimeoutInterval = self.EstimatedRTT + gamma * self.DevRTT
        self.loggerwritter = open('Sender_log.txt', 'w')
        self.Fin = None
        self.time_list = []
        self.trans_packet = 0
        self.retransmit_duetotimeout = 0
        self.dup_packet = 0
        self.fast_re = 0
        self.retransmitsu_packet  = 0
        self.handle_pld = 0
    def threehandshake(self):
        self.start_time = time.time()
        send_pkt = STP_Segment(1, 0, 0, 0, 0,None,0,0)
        current_time = time.time()
        self.loggerwritter.write('snd\t' + str(round((current_time - self.start_time) / 1000,
                              2)) + '\tS\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
        send_pkt = pickle.dumps(send_pkt)
        self.socket.sendto(send_pkt, (self.receiver_host,self.receiver_port))
        self.trans_packet+=1
        rec_pkt, sender_addr = self.socket.recvfrom(1024)
        rec_pkt = pickle.loads(rec_pkt)
        if(rec_pkt.syn_bit == 1) and (rec_pkt.ack_bit == 1):
            current_time = time.time()
            self.loggerwritter.write('rcv\t' + str(round(current_time - self.start_time, 2)) + '\tSA\t' + f'{rec_pkt.seq_number}\t{rec_pkt.lengthofdata}\t{rec_pkt.ack_number}\n')
            send_pkt = STP_Segment(rec_pkt.syn_bit, rec_pkt.ack_bit, 0, rec_pkt.ack_number, rec_pkt.seq_number+1, None, 0,0)
            self.seq_number =send_pkt.seq_number
            self.ack_number = send_pkt.ack_number
            current_time = time.time()
            self.loggerwritter.write('snd\t' + str(round((current_time - self.start_time) / 1000,
                                      2)) + '\tA\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
            send_pkt = pickle.dumps(send_pkt)
            self.socket.sendto(send_pkt, (self.receiver_host, self.receiver_port))
            self.trans_packet += 1
            self.status = 'datatransfer'
            return True
        else:
            print('TCP three hand shake failed.')
            return False

    def senddata(self, send_number):
        self.handle_pld +=1
        if len(self.LL) != 0 and self.count == self.maxOrder:
            current_time = time.time()
            send_pkt = STP_Segment(0, 0, 0, self.LL[0], self.ack_number, self.data_dict[self.LL[0]],
                                   len(self.data_dict[self.LL[0]]),
                                   hashlib.md5(self.data_dict[self.LL[0]]).hexdigest())
            self.loggerwritter.write('snd/rord\t' + str(round(current_time - self.start_time,
                                           2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
            self.time_list.append([self.LL[0]+len(self.data_dict[self.LL[0]]),current_time,self.LL[0]])
            self.reorder_packet += 1

        if random.random() <= self.pDrop:
            current_time = time.time()
            #self.loggerwritter.write('1111')
            self.loggerwritter.write('drop\t' + str(round(current_time - self.start_time, 2))
                  + '\tD\t' + f'{send_number}\t{len(self.data_dict[send_number])}\t{self.ack_number}\n')

            self.drop_packet += 1
            if len(self.LL) != 0:
                self.count += 1
            self.time_list.append([send_number + len(self.data_dict[send_number]), current_time, send_number])

        elif random.random() < self.pDuplicate:
            current_time = time.time()
            send_pkt = STP_Segment(0, 0, 0, send_number, self.ack_number,
                                   self.data_dict[send_number],
                                   len(self.data_dict[send_number]),
                                   hashlib.md5(self.data_dict[send_number]).hexdigest())
            self.loggerwritter.write('snd\t' + str(round(current_time - self.start_time,
                                      2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')

            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
            self.loggerwritter.write('snd/dup\t' + str(round(current_time - self.start_time,
                                          2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')

            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
            self.duplicate_packet += 1
            if len(self.LL) != 0:
                self.count += 1
            self.time_list.append([send_number + len(self.data_dict[send_number]), current_time, send_number])

        elif random.random() < self.pCorrupt:
            current_time = time.time()
            #random.random()
            #random.random()
            send_pkt = STP_Segment(0, 0, 0, send_number, self.ack_number, b'#',
                                   len(self.data_dict[send_number]),
                                   hashlib.md5(self.data_dict[send_number]).hexdigest())
            self.loggerwritter.write('snd/corr\t' + str(round(current_time - self.start_time, 2))
                  + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')

            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
            self.corrupt_packet += 1
            if len(self.LL) != 0:
                self.count += 1
            self.time_list.append([send_number + len(self.data_dict[send_number]), current_time, send_number])

        elif random.random() < self.pOrder:
            if len(self.LL) == 0:
                self.LL.append(send_number)
                self.reorder_packet += 1
            else:
                current_time = time.time()
                send_pkt = STP_Segment(0, 0, 0, send_number, self.ack_number,
                                       self.data_dict[send_number],
                                       len(self.data_dict[send_number]),
                                       hashlib.md5(self.data_dict[send_number]).hexdigest())
                self.loggerwritter.write('snd\t' + str(round(current_time - self.start_time,
                                                             2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')

                self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
                if len(self.LL) != 0:
                    self.count += 1
                self.time_list.append([send_number + len(self.data_dict[send_number]), current_time, send_number])
                self.trans_packet += 1

        elif random.random() < self.pDelay:
            current_time = time.time()
            self.time_list.append([send_number + len(self.data_dict[send_number]), current_time, send_number])
            time.sleep(random.random() * self.maxDelay)
            current_time = time.time()
            send_pkt = STP_Segment(0, 0, 0, send_number, self.ack_number,
                                   self.data_dict[send_number],
                                   len(self.data_dict[send_number]),
                                   hashlib.md5(self.data_dict[send_number]).hexdigest())
            self.loggerwritter.write('snd/dely\t' + str(round(current_time - self.start_time,
                                           2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
            self.delay_packet += 1
            if len(self.LL) != 0:
                self.count += 1


        else:
            current_time = time.time()
            send_pkt = STP_Segment(0, 0, 0, send_number, self.ack_number,
                                   self.data_dict[send_number],
                                   len(self.data_dict[send_number]),
                                   hashlib.md5(self.data_dict[send_number]).hexdigest())
            self.loggerwritter.write('snd\t' + str(round(current_time - self.start_time,
                                      2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
            if len(self.LL) != 0:
                self.count += 1
            self.time_list.append([send_number + len(self.data_dict[send_number]), current_time, send_number])
            self.trans_packet += 1

    def send(self):
        self.LL = []
        while self.status == 'datatransfer':
            if self.seq_number not in self.data_dict:
                self.Fin = self.seq_number
                break
            if self.LastByteSent - self.LastByteRecv + self.MSS <= self.MWS:
                self.senddata(self.seq_number)
                self.LastByteSent = self.seq_number
                self.seq_number = self.seq_number + len(self.data_dict[self.seq_number])

            else:
                time.sleep(0.001)

    def retransmit(self, send_number):
        if len(self.LL) != 0 and self.count == self.maxOrder:
            current_time = time.time()
            send_pkt = STP_Segment(0, 0, 0, self.LL[0], self.ack_number, self.data_dict[self.LL[0]],
                                   len(self.data_dict[self.LL[0]]),
                                   hashlib.md5(self.data_dict[self.LL[0]]).hexdigest())
            self.loggerwritter.write('snd/rord\t' + str(round(current_time - self.start_time,
                                           2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))

        if random.random() <= self.pDrop:
            current_time = time.time()
            self.loggerwritter.write('drop\t' + str(round(current_time - self.start_time, 2))
                  + '\tD\t' + f'{send_number}\t{len(self.data_dict[send_number])}\t{self.ack_number}\n')
            self.drop_packet += 1
            if len(self.LL) != 0:
                self.count += 1

        elif random.random() < self.pDuplicate:
            current_time = time.time()
            send_pkt = STP_Segment(0, 0, 0, send_number, self.ack_number,
                                   self.data_dict[send_number],
                                   len(self.data_dict[send_number]),
                                   hashlib.md5(self.data_dict[send_number]).hexdigest())
            self.loggerwritter.write('snd\t' + str(round(current_time - self.start_time,
                                      2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
            self.loggerwritter.write('snd/dup\t' + str(round(current_time - self.start_time,
                                          2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
            self.duplicate_packet += 1
            if len(self.LL) != 0:
                self.count += 1

        elif random.random() < self.pCorrupt:
            current_time = time.time()
            #random.random()
            #andom.random()
            send_pkt = STP_Segment(0, 0, 0, send_number, self.ack_number, b'#',
                                   len(self.data_dict[send_number]),
                                   hashlib.md5(self.data_dict[send_number]).hexdigest())
            self.loggerwritter.write('snd/corr\t' + str(round(current_time - self.start_time, 2))
                  + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
            self.corrupt_packet += 1
            if len(self.LL) != 0:
                self.count += 1

        elif random.random() < self.pOrder:
            if len(self.LL) == 0:
                self.LL.append(send_number)
                self.reorder_packet += 1
            else:
                current_time = time.time()
                send_pkt = STP_Segment(0, 0, 0, send_number, self.ack_number,
                                       self.data_dict[send_number],
                                       len(self.data_dict[send_number]),
                                       hashlib.md5(self.data_dict[send_number]).hexdigest())
                self.loggerwritter.write('snd\t' + str(round(current_time - self.start_time,
                                                             2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
                self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
                if len(self.LL) != 0:
                    self.count += 1
                self.trans_packet += 1

        elif random.random() < self.pDelay:
            time.sleep(random.random()*self.maxDelay)
            current_time = time.time()
            send_pkt = STP_Segment(0, 0, 0, send_number, self.ack_number,
                                   self.data_dict[send_number],
                                   len(self.data_dict[send_number]),
                                   hashlib.md5(self.data_dict[send_number]).hexdigest())
            self.loggerwritter.write('snd/dely\t' + str(round(current_time - self.start_time,
                                           2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
            self.delay_packet += 1
            if len(self.LL) != 0:
                self.count += 1

        else:
            current_time = time.time()
            send_pkt = STP_Segment(0, 0, 0, send_number, self.ack_number,
                                   self.data_dict[send_number],
                                   len(self.data_dict[send_number]),
                                   hashlib.md5(self.data_dict[send_number]).hexdigest())
            self.loggerwritter.write('snd/RXT\t' + str(round(current_time - self.start_time,
                                          2)) + '\tD\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
            self.socket.sendto(pickle.dumps(send_pkt), (self.receiver_host, self.receiver_port))
            if len(self.LL) != 0:
                self.count += 1
            self.retransmitsu_packet += 1

    def receive(self):

        self.receive_ack = {}
        while self.status == 'datatransfer':
            print(self.time_list)
            rec_pkt, addr = self.socket.recvfrom(1024)
            rec_pkt = pickle.loads(rec_pkt)
            current_time = time.time()

            if rec_pkt.ack_number in self.receive_ack:
                self.dup_packet +=1
                self.receive_ack[rec_pkt.ack_number] += 1
                self.loggerwritter.write('rcv\DA\t' + str(round(current_time - self.start_time,
                                             2)) + '\tA\t' + f'{rec_pkt.seq_number}\t{rec_pkt.lengthofdata}\t{rec_pkt.ack_number}\n')

                if self.receive_ack[rec_pkt.ack_number] >= 3:

                    self.receive_ack[rec_pkt.ack_number] = 0
                    for i in range(len(self.time_list)):
                        if self.time_list[i] == rec_pkt.ack_number:
                            self.time_list.remove(self.time_list[i])
                    self.retransmit(rec_pkt.ack_number)
                    self.retransmit_packet += 1
                    self.fast_re += 1

            else:
                self.receive_ack[rec_pkt.ack_number] = 0
                if rec_pkt.ack_number == 401:
                    print(111)
                if len(self.time_list)!=0:
                    self.LastByteRecv = rec_pkt.ack_number
                    threading.Semaphore().acquire()
                    for i in range(len(self.time_list)):
                        if self.time_list[i][0] == rec_pkt.ack_number:
                            SampleRTT = time.time()-self.time_list[i][1]
                            self.DevRTT = 0.75*self.DevRTT + 0.25*abs(SampleRTT-self.EstimatedRTT)
                            self.EstimatedRTT = (1 - 0.125) * self.EstimatedRTT + 0.125 * SampleRTT
                            self.TimeoutInterval = self.EstimatedRTT + gamma * self.DevRTT
                            self.time_list = self.time_list[i+1:]
                            break

                    threading.Semaphore().release()

                self.loggerwritter.write('rcv\t' + str(round(current_time - self.start_time,
                                          2)) + '\tA\t' + f'{rec_pkt.seq_number}\t{rec_pkt.lengthofdata}\t{rec_pkt.ack_number}\n')

            if rec_pkt.ack_number == self.Fin and self.Fin != None:
                self.status = 'close'
                self.closeTCPconnection()
                break

    def Timer(self):
        while self.status == 'datatransfer':
            for i in range(len(self.time_list)):
                if (time.time() - self.time_list[i][1]) > self.TimeoutInterval:
                    threading.Semaphore().acquire()
                    self.retransmit(self.time_list[i][2])
                    self.time_list[i][1]  = time.time()
                    self.retransmit_packet += 1
                    self.retransmit_duetotimeout += 1
                    break
            time.sleep(0.02)



    def datatransfer(self):
        self.data_dict = {}
        file = open(self.filename, 'rb')
        data = file.read()
        self.length =len(data)
        self.LastByteRecv = self.ack_number
        self.LastByteSent = self.seq_number
        random.seed(self.seed)
        for i in range(0, len(data), self.MSS):
            self.data_dict[self.seq_number + i] = data[i:i + self.MSS]
        if len(self.data_dict) != 0:
            threads = []
            threads.append(threading.Thread(target=self.send))
            threads.append(threading.Thread(target=self.Timer))
            threads.append(threading.Thread(target=self.receive))

        for item in threads:
            item.start()
        for item in threads:
            item.join(0.001)

    def closeTCPconnection(self):
        send_fin = STP_Segment(0, 0, 1, self.seq_number, self.ack_number, None, 0, 0)
        current_time = time.time()
        self.loggerwritter.write('snd\t' + str(round(current_time - self.start_time,
                                  2)) + '\tF\t' + f'{send_fin.seq_number}\t{send_fin.lengthofdata}\t{send_fin.ack_number}\n')
        self.socket.sendto(pickle.dumps(send_fin), (self.receiver_host, self.receiver_port))
        self.trans_packet += 1
        rec_fin, sender_addr = self.socket.recvfrom(1024)
        rec_fin = pickle.loads(rec_fin)
        if rec_fin.fin_bit == 1 and rec_fin.ack_bit == 1:
            current_time = time.time()
            self.loggerwritter.write('rcv\t' + str(round(current_time - self.start_time,
                                  2)) + '\tA\t' + f'{rec_fin.seq_number}\t{rec_fin.lengthofdata}\t{rec_fin.ack_number}\n')
            rec_fin, sender_addr = self.socket.recvfrom(1024)
            rec_fin = pickle.loads(rec_fin)
            if rec_fin.fin_bit == 1 and rec_fin.ack_bit == 0:
                current_time = time.time()
                self.loggerwritter.write('rcv\t' + str(round(current_time - self.start_time,
                                  2)) + '\tF\t' + f'{rec_fin.seq_number}\t{rec_fin.lengthofdata}\t{rec_fin.ack_number}\n')
                send_fin = STP_Segment(0, 1, 1, rec_fin.ack_number, rec_fin.seq_number + 1, None, 0, 0)
                self.socket.sendto(pickle.dumps(send_fin), (receiver_host, receiver_port))
                current_time = time.time()
                self.loggerwritter.write('snd\t' + str(round(current_time - self.start_time,
                                  2)) + '\tA\t' + f'{send_fin.seq_number}\t{send_fin.lengthofdata}\t{send_fin.ack_number}\n')
        else:
            sys.exit()
        self.trans_packet += 1
        self.loggerwritter.write('=============================================================\n')
        self.loggerwritter.write(f'Size of the file (in Bytes) {self.length}\n')
        self.loggerwritter.write(f'Segments transmitted (including drop & RXT) {self.trans_packet+self.drop_packet+self.retransmitsu_packet}\n')
        self.loggerwritter.write(f'Number of Segments handled by PLD {self.handle_pld+self.retransmit_packet}\n')
        self.loggerwritter.write(f'Number of Segments dropped {self.drop_packet}\n')
        self.loggerwritter.write(f'Number of Segments Corrupted {self.corrupt_packet}\n')
        self.loggerwritter.write(f'Number of Segments Re-ordered {self.reorder_packet}\n')
        self.loggerwritter.write(f'Number of Segments Duplicated {self.duplicate_packet}\n')
        self.loggerwritter.write(f'Number of Segments Delayed {self.delay_packet}\n')
        self.loggerwritter.write(f'Number of Retransmissions due to TIMEOUT {self.retransmit_duetotimeout}\n')
        self.loggerwritter.write(f'Number of FAST RETRANSMISSION {self.fast_re}\n')
        self.loggerwritter.write(f'Number of DUP ACKS received {self.dup_packet}\n')
        self.loggerwritter.write('=============================================================\n')

if not len(sys.argv) == 15:
    print("Not enough parameters")
    sys.exit()
receiver_host = str(sys.argv[1])
receiver_port = int(sys.argv[2])
filename = str(sys.argv[3])
MWS = int(sys.argv[4])
MSS = int(sys.argv[5])
gamma = int(sys.argv[6])
pDrop = float(sys.argv[7])
pDuplicate = float(sys.argv[8])
pCorrupt = float(sys.argv[9])
pOrder = float(sys.argv[10])
maxOrder = float(sys.argv[11])
pDelay = float(sys.argv[12])
maxDelay = int(sys.argv[13])
seed = int(sys.argv[14])
sender = Sender(receiver_host,receiver_port, filename, MWS, MSS, gamma, pDrop, pDuplicate, pCorrupt, pOrder, maxOrder, pDelay, maxDelay, seed)
if sender.threehandshake() is True:
    sender.datatransfer()
    if sender.status == 'close':
        sender.closeTCPconnection()