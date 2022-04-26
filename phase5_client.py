import os
import time
import math
import array
import random
import pickle
import datetime
from socket import *


# Reads the file one line at a time in 1024 byte chunks
def rdt_send(data):
    return data.read(1024)


# Calculates the checksum given byte data (appends a "0" to the end if indivisible by 2)
def checksum(data):
    if len(data) % 2 != 0:
        data += b'\0'
    byte = sum(array.array('H', data))
    byte = (byte >> 16) + (byte & 0xffff)
    byte += byte >> 16
    chksm = (~byte) & 0xffff
    chksm = str(chksm).encode()
    return chksm


# Creates a list packet using sequence, data, and checksum
def make_pkt(nextseqnum, data, chksm):
    return [str(nextseqnum).encode(), data, chksm]


# Sends the data it is given and returns
def udt_send(sndpkt, HOST = 'localhost', PORT = 12000):
    client_socket.sendto(sndpkt, (HOST, PORT))
    return


# Blank function to represent unused data as seen in the FSM
def refuse_data(data):
    return


# Returns the decoded sequence number as an int so it can be compared and added to
def getacknum(rcvpkt):
    return int(rcvpkt[0].decode())


# If a packet is not lost, return true, else, false
def rdt_rcv(rcvpkt):
    if rcvpkt:
        return True
    else:
        return False


# If the second item in the list (the returned checksum) equals the earlier computed checksum, return true, else, false
def notcorrupt(rcvpkt, chksm):
    if rcvpkt[1] == chksm:
        return True
    else:
        return False


# The same operation as notcorrupt() but reversed
def corrupt(rcvpkt, chksm):
    if rcvpkt[1] == chksm:
        return False
    else:
        return True


# If the random chance triggers, a random number between 1 and 100 will be added to the ACK (arbitrary error algorithm)
def ack_error(rcvpkt, err_rate):
    err_chance = random.randint(1, 101)
    if err_chance < err_rate:
        #print('!!! ACK ERROR !!!')
        rcvpkt[0] = str(int(rcvpkt[0].decode()) + random.randint(1, 101)).encode()
    return rcvpkt


# If the random chance triggers, the ACK packet is deleted ("lost")
def ack_loss(rcvpkt, lss_rate):
    lss_chance = random.randint(1, 101)
    if lss_chance < lss_rate:
        #print('!!! ACK LOSS !!!')
        rcvpkt = None
    return rcvpkt


HOST = 'localhost'
PORT = 12000
client_socket = socket(AF_INET, SOCK_DGRAM)
client_socket.settimeout(0.01) # Smallest timeout value that works in testing

file_name = input('Input filename: ')
file_data = open(file_name, 'rb')
data = rdt_send(file_data)
sndpkt_size = math.ceil(os.stat(file_name).st_size / 1024)

base = 0
nextseqnum = 0
N = 7
sndpkt = [None] * sndpkt_size

done = False
timeout = False
rcvpkt = False

option = input('Selection option'
               '[1: No Error (Default)/ 2: ACK Error/ 3: Data Error/ 4: ACK Loss/ 5: Data Loss]: ')

# By default, the ACK error/loss values are 0 and only change if option 2 or 4 is chosen
ack_err = 0
ack_lss = 0

# If the inputted option is 1-5, perform the action related to that number. If not, default to 1 (no errors)
if int(option) in range(1, 6):
    if option.encode() == b'2':
        ack_err = 20
    elif option.encode() == b'4':
        ack_lss = 20
    option = option.encode()
else:
    option = b'1'

start_time = datetime.datetime.now()

udt_send(option)

while not done:
    if nextseqnum < base + N:
        chksm = checksum(data)
        sndpkt[nextseqnum] = pickle.dumps((make_pkt(nextseqnum, data, chksm)))
        udt_send(sndpkt[nextseqnum])
        if base == nextseqnum:
            start_timer = time.time()
        nextseqnum += 1
        data = rdt_send(file_data)
    else:
        refuse_data(data)

    try:
        rcvpkt, addr = client_socket.recvfrom(1024)
        rcvpkt = pickle.loads(rcvpkt)
        rcvpkt = ack_error(rcvpkt, ack_err)
        rcvpkt = ack_loss(rcvpkt, ack_lss)
    # This is the timeout function; it resends the current window when a data error causes a timeout
    except:
        for packet_in_window in range(base, nextseqnum):
            udt_send(sndpkt[packet_in_window])

    # Updates the base to the last successfully received packet
    if rdt_rcv(rcvpkt) is True and notcorrupt(rcvpkt, chksm) is True:
        base = getacknum(rcvpkt) + 1

    # Do nothing otherwise (this is here to satisfy the FSM and could be removed)
    if rdt_rcv(rcvpkt) is True and corrupt(rcvpkt, chksm) is True:
        pass

    # Completes after the final packet is sent
    if nextseqnum == sndpkt_size:
        done = True
        udt_send(b'EOF')

client_socket.close()
end_time = datetime.datetime.now()
print('Finished in ' + str((end_time - start_time)))
