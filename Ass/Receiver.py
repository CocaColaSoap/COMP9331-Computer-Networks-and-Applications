import sys
from socket import *
import time
import pickle
from STP import STP_Segment
import hashlib
if not len(sys.argv) == 3:
    print('Not enough parameters')
    sys.exit(-1)
receiver_port = int(sys.argv[1])
file_name = sys.argv[2]
socket = socket(AF_INET, SOCK_DGRAM)
socket.bind(('127.0.0.1',receiver_port))
print("Receiver is waiting...")


rece_pkt = 0
data_pkt = 0
biterror_pkt = 0
duplicate_pkt = 0
duplicate_pkt_sent = 0
datalength = 0

def threehandshake(socket, logwritter):
    rec_pkt, sender_addr = socket.recvfrom(1024)
    global start_time
    global rec_seq_number_require
    global rec_ack_number_pre
    global rece_pkt
    start_time = time.time()
    rec_pkt = pickle.loads(rec_pkt)
    if rec_pkt.syn_bit == 1:
        current_time = time.time()
        logwritter.write('rcv\t' + str(round(current_time - start_time,
                                  2)) + '\tS\t' + f'{rec_pkt.seq_number}\t{rec_pkt.lengthofdata}\t{rec_pkt.ack_number}\n')
        rece_pkt += 1
        send_pkt = STP_Segment(rec_pkt.syn_bit, 1, 0, 0, rec_pkt.seq_number + 1, '', 0, 0)
        current_time = time.time()
        logwritter.write('snd\t' + str(round(current_time - start_time,
                                  2)) + '\tSA\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
        send_pkt = pickle.dumps(send_pkt)
        socket.sendto(send_pkt, sender_addr)
        rec_pkt, sender_addr = socket.recvfrom(1024)
        rec_pkt = pickle.loads(rec_pkt)
        if rec_pkt.ack_bit == 1 and rec_pkt.syn_bit == 1:
            current_time = time.time()
            logwritter.write('rcv\t' + str(round(current_time - start_time,
                                      2)) + '\tA\t' + f'{rec_pkt.seq_number}\t{rec_pkt.lengthofdata}\t{rec_pkt.ack_number}\n')
            rece_pkt += 1
            rec_seq_number_require = rec_pkt.seq_number
            rec_ack_number_pre = rec_pkt.ack_number
            print("TCP three hand shake succeeded.")
            return True
        else:
            logwritter.write("TCP three hand shake failed.")
            return False


def receiverdata(socket,file_name):
    rec_pkt_dict = {}
    global rec_seq_number_require
    global rec_ack_number_pre
    global start_time
    global rece_pkt
    global data_pkt
    global biterror_pkt
    global duplicate_pkt
    global duplicate_pkt_sent
    global datalength
    while True:
        rec_pkt, sender_addr = socket.recvfrom(2048)
        rec_pkt = pickle.loads(rec_pkt)

        if rec_pkt.fin_bit == 1:
            file = open('test1.pdf', 'wb')
            #print(rec_pkt_dict)
            LL = list(rec_pkt_dict)
            LL = sorted(LL)
            print(LL)
            for item in LL:
                file.write(rec_pkt_dict[item])
                datalength += len(rec_pkt_dict[item])
            file.close()
            closeTCPConnection(socket, rec_pkt, sender_addr,logwritter)
            break
        else:
            if rec_pkt.seq_number not in rec_pkt_dict:
                if hashlib.md5(rec_pkt.payload).hexdigest() == rec_pkt.checksum:
                    current_time = time.time()
                    rec_pkt_dict[rec_pkt.seq_number] = rec_pkt.payload
                    logwritter.write('rcv\t' + str(
                        round(current_time - start_time,
                              2)) + '\tD\t' + f'{rec_pkt.seq_number}\t{rec_pkt.lengthofdata}\t{rec_pkt.ack_number}\n')
                    rece_pkt += 1
                    data_pkt += 1
                else:
                    current_time = time.time()
                    logwritter.write('rcv/corr\t' + str(
                                round(current_time - start_time,
                                      2)) + '\tD\t' + f'{rec_pkt.seq_number}\t{rec_pkt.lengthofdata}\t{rec_pkt.ack_number}\n')
                    rece_pkt += 1
                    data_pkt += 1
                    biterror_pkt += 1
            else:
                logwritter.write('rcv\t' + str(
                    round(current_time - start_time,
                          2)) + '\tD\t' + f'{rec_pkt.seq_number}\t{rec_pkt.lengthofdata}\t{rec_pkt.ack_number}\n')
                rece_pkt += 1
                data_pkt += 1
                duplicate_pkt += 1
            sorted(rec_pkt_dict.keys())
            print(rec_seq_number_require)
            if rec_seq_number_require == rec_pkt.seq_number:
                while rec_seq_number_require in rec_pkt_dict:
                    rec_seq_number_require += len(rec_pkt_dict[rec_seq_number_require])
                send_pkt = STP_Segment(0, 0, 0, rec_ack_number_pre, rec_seq_number_require, None, 0, 0)
                logwritter.write('snd\t' + str(
                    round(current_time - start_time,
                          2)) + '\tA\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
                socket.sendto(pickle.dumps(send_pkt), sender_addr)
            else:
                send_pkt = STP_Segment(0, 0, 0, rec_ack_number_pre, rec_seq_number_require, None, 0, 0)
                logwritter.write('snd/DA\t' + str(
                    round(current_time - start_time,
                          2)) + '\tA\t' + f'{send_pkt.seq_number}\t{send_pkt.lengthofdata}\t{send_pkt.ack_number}\n')
                socket.sendto(pickle.dumps(send_pkt), sender_addr)
                duplicate_pkt_sent += 1






def closeTCPConnection(socket,rec_fin,sender_addr, logwritter):
    global rece_pkt
    global data_pkt
    global biterror_pkt
    global duplicate_pkt
    global duplicate_pkt_sent
    global datalength

    current_time = time.time()
    logwritter.write('rcv\t' + str(
            round(current_time - start_time,
                  2)) + '\tF\t' + f'{rec_fin.seq_number}\t{rec_fin.lengthofdata}\t{rec_fin.ack_number}\n')
    rece_pkt += 1
    send_Fin = STP_Segment(0, 1, 1, rec_fin.ack_number, rec_fin.seq_number + 1, None, 0, 0)
    current_time = time.time()
    logwritter.write('snd\t' + str(
                round(current_time - start_time,
                      2)) + '\tA\t' + f'{send_Fin.seq_number}\t{send_Fin.lengthofdata}\t{send_Fin.ack_number}\n')
    socket.sendto(pickle.dumps(send_Fin), sender_addr)
    send_Fin = STP_Segment(0, 0, 1, rec_fin.ack_number, rec_fin.seq_number + 1, None, 0, 0)
    current_time = time.time()
    logwritter.write('snd\t' + str(
        round(current_time - start_time,
              2)) + '\tF\t' + f'{send_Fin.seq_number}\t{send_Fin.lengthofdata}\t{send_Fin.ack_number}\n')
    socket.sendto(pickle.dumps(send_Fin), sender_addr)
    rec_fin, sender_addr = socket.recvfrom(1024)
    rec_fin = pickle.loads(rec_fin)
    logwritter.write('rcv\t' + str(
            round(current_time - start_time,
                  2)) + '\tA\t' + f'{rec_fin.seq_number}\t{rec_fin.lengthofdata}\t{rec_fin.ack_number}\n')
    rece_pkt += 1
    logwritter.write('==============================================\n')
    logwritter.write(f'Amount of data received (bytes) {datalength}\n')
    logwritter.write(f'Total Segments Received {rece_pkt}\n')
    logwritter.write(f'Data segments received {data_pkt}\n')
    logwritter.write(f'Data segments with Bit Errors {biterror_pkt}\n')
    logwritter.write(f'Duplicate data segments received {duplicate_pkt}\n')
    logwritter.write(f'Duplicate ACKs sent {duplicate_pkt_sent}\n')
    logwritter.write('==============================================\n')







logwritter = open('Receiver_log.txt', 'w')
if threehandshake(socket, logwritter) is True:
    receiverdata(socket, file_name)
    #closeTCPConnection(socket, logwritter)