import array
import random
import pickle
import datetime
from socket import *


# If a packet is not lost, return true, else, false
def rdt_rcv(rcvpkt):
    if rcvpkt:
        #print('True 1')
        return True
    else:
        return False


# If the recomputed checksum equals the one sent in the packet, return true, else, false
def notcorrupt(data, chksm):
    if data == chksm:
        #print('True 2')
        return True
    else:
        return False


# Checks the sequence # from the packet and compares it to the serverside expected value
def hasseqnum(extractedseqnum, expectedseqnum):
    if extractedseqnum == expectedseqnum:
        #print('True 3')
        return True
    else:
        return False


# Writes the confirmed data to the file
def deliver_data(data):
    new_file.write(data)
    return


# (Re)calculates the checksum given byte data (appends a "0" to the end if indivisible by 2)
def checksum(data):
    if len(data) % 2 != 0:
        data += b'\0'
    chksm_recalc = sum(array.array('H', data))
    chksm_recalc = (chksm_recalc >> 16) + (chksm_recalc & 0xffff)
    chksm_recalc += chksm_recalc >> 16
    chksm_recalc = (~chksm_recalc) & 0xffff
    return str(chksm_recalc).encode()


# Makes the ACK packet using the confirmed expected number and the recalculated checksum
def make_pkt(expectedseqnum, checksum):
    return [str(expectedseqnum).encode(), checksum]


# Sends the data it is given and returns
def udt_send(sndpkt, addr):
    server_socket.sendto(sndpkt, addr)


# If the random chance triggers, the data will be rotated 1 byte, enough to create a different checksum (arbitrary)
def data_error(data, err_rate):
    err_chance = random.randint(1, 101)
    if err_chance < err_rate:
        #print('!!! DATA ERROR !!!')
        l_shift_data = data[0:1]
        r_shift_data = data[1:]
        shifted_data = r_shift_data + l_shift_data
        data = shifted_data
    return data


# If the random chance triggers, deletes the data packet
def data_loss(rcvpkt, lss_rate):
    lss_chance = random.randint(1, 101)
    if lss_chance < lss_rate:
        #print('!!! DATA LOSS !!!')
        rcvpkt = False
    return rcvpkt


HOST = 'localhost'
PORT = 12000
server_socket = socket(AF_INET, SOCK_DGRAM)
server_socket.bind((HOST, PORT))

expectedseqnum = 0
new_file = open('output.jpg', 'wb')

rcvpkt, addr = server_socket.recvfrom(2048)

# Data error and loss default to 0
data_err = 0
data_lss = 0
# If the received value is either 3 or 5, adjust the data error/loss accordingly
if rcvpkt == b'3':
    data_err = 70
elif rcvpkt == b'5':
    data_lss = 70

while True:
    rcvpkt, addr = server_socket.recvfrom(2048)

    if rcvpkt == b'EOF':
        break

    rcvpkt = pickle.loads(rcvpkt)

    extractedseqnum = int(rcvpkt[0].decode())
    data            = data_error(rcvpkt[1], data_err)
    chksm           = rcvpkt[2]
    chksm_recalc = checksum(data)

    rcvpkt = data_loss(rcvpkt, data_lss)

    if rdt_rcv(rcvpkt) is True and notcorrupt(chksm_recalc, chksm) is True and hasseqnum(extractedseqnum, expectedseqnum) is True:
        deliver_data(data)
        sndpkt = pickle.dumps(make_pkt(expectedseqnum, chksm_recalc))
        udt_send(sndpkt, addr)
        expectedseqnum += 1
    else:
        # This error triggers if the very first packet gets corrupted and sndpkt() hasn't even had a chance to be made
        try:
            udt_send(sndpkt, addr)
        except NameError:
            pass

new_file.close()
print('Done.')
