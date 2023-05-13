import socket
import argparse
import time
from struct import *
from queue import Queue
import select

header_format = '!IIHH'
HEADER_SIZE = 12


def create_packet(seq, ack, flags, win, data):
    header = pack (header_format, seq, ack, flags, win)
    packet = header + data
    #print (f'packet containing header + data of size {len(packet)}') #just to show the length of the packet
    return packet

def parse_header(header):
    header_from_msg = unpack(header_format, header)
    return header_from_msg

def parse_flags(flags):
    syn = flags & (1 << 3)
    ack = flags & (1 << 2)
    fin = flags & (1 << 1)
    return syn, ack, fin



def receive_stop_and_wait(server_socket, expected_seq, test_case):
    recv_seq = set()
    received_file = b''
    skip_ack = False
    if test_case == 'skip-ack':
        skip_ack = True
        skip_ack_seq = 3  # The sequence number for which you want to skip the ACK
    while True:
        packet, client_address = server_socket.recvfrom(1472)
        header = packet[:HEADER_SIZE]
        seq, _, flag, _ = parse_header(header)
        if seq not in recv_seq:
            if seq == expected_seq:
                print(f"Received packet with seq {seq}")
                data = packet[HEADER_SIZE:]
                if not skip_ack or seq != skip_ack_seq:
                    recv_seq.add(seq)
                    ack_packet = create_packet(0,seq,0,0,b'')
                    print (f'packet containing header + data of size {len(ack_packet)}')
                    server_socket.sendto(ack_packet, client_address)
                    print(f"Sent ack for seq: {seq}")
                    expected_seq += 1
                    received_file += data
                else:
                    skip_ack = False
                    print(f"Skipped ack for seq: {seq}")
                if flag == 2:
                    break
            else:
                print(f"Out of order packet. Expected seq: {expected_seq}, received seq: {seq}")
    return received_file

def receive_gbn(server_socket, expected_seq, test_case, WINDOW_SIZE):
    received_file = b''
    window = Queue(maxsize=WINDOW_SIZE)
    stop_received = False
    skip_ack = False
    if test_case == 'skip-ack':
        skip_ack = True
        skip_ack_seq = 3  

    while True:
        packet, client_address = server_socket.recvfrom(1472)
        header = packet[:HEADER_SIZE]
        seq, _, flag, _ = parse_header(header)

        if seq == expected_seq:
            print(f"Received packet with seq {seq}")
            data = packet[HEADER_SIZE:]
            window.put((seq, data, flag))
            if not skip_ack or seq != skip_ack_seq:
                ack_packet = create_packet(0, seq, flag, 0, b'')
                server_socket.sendto(ack_packet, client_address)
                print(f"Sent ack for seq: {seq}")
                received_file += data
                expected_seq += 1
            else:
                skip_ack = False
                print(f"Skipped ack for seq: {seq}")
                expected_seq = seq
            if window.full() or flag == 1:
                while not window.empty():
                    seq, data, flag = window.get()
                    
                    if flag == 1:
                        print(f"Received STOP flag")
                        stop_received = True 
            
        else:
            print(f"Out of order packet. Expected seq: {expected_seq}, received seq: {seq}")
            window.queue.clear()
        if stop_received:
            break

    return received_file
   
def receive_sr(server_socket, expected_seq, test_case):
    WINDOW_SIZE = 5
    received_file = b''
    buffer = {}
    recv_seq = set()
    stop_received = False
    skip_ack = False
    if test_case == 'skip-ack':
        skip_ack = True
        skip_ack_seq = 3  

    while True:
        packet, client_address = server_socket.recvfrom(1472)
        header = packet[:HEADER_SIZE]
        seq, _, flag, _ = parse_header(header)

        if seq not in recv_seq:
            data = packet[HEADER_SIZE:]
            if not skip_ack or seq != skip_ack_seq:
                ack_packet = create_packet(0,seq,0,0,b'')
                server_socket.sendto(ack_packet, client_address)
                print(f"Sent ack for seq: {seq}")
                recv_seq.add(seq)
                
            else:
                print(f"Skipped ack for seq: {seq}")
                skip_ack = False 
                expected_seq = seq

            if seq == expected_seq:
                print(f"Received packet with seq {seq}")
                received_file += data
                expected_seq += 1

                while expected_seq in buffer:
                    received_file += buffer[expected_seq][0]
                    del buffer[expected_seq]
                    recv_seq.add(expected_seq)
                    expected_seq += 1
                
            else:
                print(f"Out of order packet. Expected seq: {expected_seq}, received seq: {seq}")
                buffer[seq] = (packet[HEADER_SIZE:], flag)
                
            if flag == 1:
                break
    return received_file



def server(args):
    # Define server address and port
    HOST = args.ip
    PORT = args.port
    test_case = args.test_case
    window_size = args.window_size

    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind the socket to a specific address and port
    server_socket.bind((HOST, PORT))

    # Wait for SYN from client
    print('Waiting for SYN from client...')
    syn, address = server_socket.recvfrom(1460)
    _,_, flag, _ = parse_header(syn[:12])
    syn_flag, _, _ = parse_flags(flag)
    if syn_flag:
        print('SYN received from client')

        # Send SYN ACK to client
        syn_ack = create_packet(0,0,12,0,b'')
        server_socket.sendto(syn_ack, address)
        print('SYN-ACK sent to client')

        # Wait for ACK from client
        print('Waiting for ACK from client...')
        ack, address = server_socket.recvfrom(1460)
        _,_, flag_check, _ = parse_header(syn_ack[:12])
        _, ack_flag, _ = parse_flags(flag_check)

        if ack_flag:
            print('ACK received from client:', ack.decode())
            print('Connection established successfully!')

            # Receive file from client using the specified reliability function
            if args.reliability_function == 'stop_and_wait':
                received_file = receive_stop_and_wait(server_socket, 0, test_case)
            elif args.reliability_function == 'gbn':
                received_file = receive_gbn(server_socket, 0, test_case, window_size)
            elif args.reliability_function == 'sr':
                received_file = receive_sr(server_socket, 0, test_case)
            else:
                print("Invalid reliability function specified.")
                server_socket.close()
                return

            # Check if the received file is complete
            fin, address = server_socket.recvfrom(1460)
            _,_, flag_check, _ = parse_header(fin[:12])
            _, _, fin_flag = parse_flags(flag_check)
            if fin_flag:
                print('File transfer complete')
            else:
                print('File transfer incomplete:')

            # Write received file to disk
            with open('received_file.jpg', 'wb') as f:
                f.write(received_file)

            # Send ACK to client
            ack = create_packet(0,0,4,0,b'')
            #print (f'packet containing header + data of size {len(ack)}')
            server_socket.sendto(ack, address)
            print('ACK sent to client')

            # Close the connection
            server_socket.close()
        else:
            print('No ACK received from client')
    else:
        print('No SYN received from client')


def client(args):

    # Define server address and port
    HOST = args.ip
    PORT = args.port
    FILE = args.filename
    window_size = args.window_size
    timeout = 5
    sent_bytes = 0

    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Send SYN to server
    syn = create_packet(0,0,8,0,b'')
    client_socket.sendto(syn, (HOST, PORT))
    print('SYN sent to server')

    # Wait for SYN-ACK from server
    syn_ack = None
    start_time = time.time()
    while not syn_ack:
        # Check if timeout period has elapsed
        if time.time() - start_time > timeout:
            print('Timeout waiting for SYN-ACK')
            return

        # Receive SYN ACK from server
        try:
            syn_ack, address = client_socket.recvfrom(1460)
            _,_, flag_check, _ = parse_header(syn_ack[:12])
            syn_flag, ack_flag, _ = parse_flags(flag_check)
        except socket.timeout:
            continue

        if syn_flag and ack_flag:
            print('SYN-ACK received from server')

            # Send ACK to server
            ack = create_packet(0,0,4,0,b'')
            client_socket.sendto(ack, address)
            print('ACK sent to server')

            print('Connection established successfully!')
        else:
            print('No SYN-ACK received from server')

    # Read file to be sent in chunks
    with open(FILE, 'rb') as f:
        file_content = f.read()

    # Send file in chunks
    chunk_size = 1460
    seq = 0

    reliability_function = args.reliability_function
    test_case = args.test_case
    
    if reliability_function == 'stop_and_wait':
        start_time == time.time()
        if test_case == 'skip-seq':
            test_case = 2
        seq = 0
        chunk_size = 1472 - HEADER_SIZE
        received_acks = set()

        for i in range(0, len(file_content), chunk_size):
            

            while True:
                data_chunk = file_content[i:i + chunk_size]
                flags = 0
                if i + chunk_size >= len(file_content):
                    flags = 2
                packet = create_packet(seq, 0, flags, 0, data_chunk)
                print (f'packet containing header + data of size {len(packet)}')
                
                if seq not in received_acks:
                    if test_case != 2 or seq != 1:  # Add this condition
                        client_socket.sendto(packet, address)
                        sent_bytes += len(packet)
                        print(f"Sent packet with seq: {seq}")
                    else:
                        print(f"Skipped packet with seq: {seq}")
                        socket.timeout

                try:
                    client_socket.settimeout(0.5)
                    ack_packet, server_address = client_socket.recvfrom(HEADER_SIZE)
                    _, ack_seq, _, _ = parse_header(ack_packet[:HEADER_SIZE])

                    if ack_seq == seq:
                        received_acks.add(seq)
                        print(f"Received ack for seq {seq}")
                        seq += 1
                        break
                    else:
                        print(f"Received out-of-order ACK: {ack_seq}")
                except socket.timeout:
                    print(f"Timeout for seq: {seq}")
                    test_case = 0

        end_time = time.time()
        duration = end_time - start_time

        rate = round((sent_bytes / duration) * 8 / 1000000, 2)
        no_of_bytes = round(sent_bytes / 1024, 2)
        print(f'Total throughput: {rate} and the number of bytes sent {no_of_bytes} KB' ) 

        

    elif reliability_function == 'gbn':
        start_time == time.time()
        base = 0
        next_seq_num = 0
        data_queue = Queue()
        WINDOW_SIZE = window_size
        flags = 0
        test_case == 0
        if test_case == 'skip-seq':
            test_case = 2
        
        for i in range(0, len(file_content), chunk_size):
            data_queue.put(file_content[i:i+chunk_size])

        window = Queue(maxsize=WINDOW_SIZE)
        while base < len(file_content):
            while next_seq_num < base + WINDOW_SIZE and not data_queue.empty():
                packet_data = data_queue.get()
                if data_queue.empty():
                    flags = 1
                packet = create_packet(next_seq_num, 0, flags, 0, packet_data)
                print (f'packet {next_seq_num} containing header + data of size {len(packet)}')
                if test_case != 2 or next_seq_num != 6:
                    client_socket.sendto(packet, address)
                    sent_bytes += len(packet)
                    print(f"Sent packet with seq: {next_seq_num}")
                    
                else:
                    print(f"Skipped packet with seq: {next_seq_num}")
                window.put(packet)
                next_seq_num += 1

            client_socket.settimeout(0.5)
            try:
                ack_packet, _ = client_socket.recvfrom(1472)
                _, ack, flag, _ = parse_header(ack_packet)
                print(f"Received ACK for seq: {ack}")
                if ack == base:
                    while not window.empty() and base <= ack:
                        window.get()
                        base += 1

                    if flag == 1:
                        print(f"Received last ACK for seq: {ack}")
                        break

            except socket.timeout:
                print("Timeout. Resending window.")
                test_case == 0
                for packet in list(window.queue):
                    client_socket.sendto(packet, address)
                    seq, _, _, _ = parse_header(packet[:HEADER_SIZE])
                    print(f"Resent packet with seq: {seq}")

        end_time = time.time()
        duration = end_time - start_time

        rate = round((sent_bytes / duration) * 8 / 1000000, 2)
        no_of_bytes = round(sent_bytes / 1024, 2)
        print(f'Total throughput: {rate} and the number of bytes sent {no_of_bytes} KB' )            
                    


    elif reliability_function == 'sr':
        start_time == time.time()
        base = 0
        next_seq_num = 0
        seq_timeout = {}
        window = {}
        acked_seq = set()
        WINDOW_SIZE = window_size
        test_case == 0
        if test_case == 'skip-seq':
            test_case = 2

        while base < len(file_content):
            while next_seq_num < base + WINDOW_SIZE and next_seq_num * chunk_size < len(file_content):
                data_chunk = file_content[next_seq_num * chunk_size: (next_seq_num + 1) * chunk_size]
                flags = 0
                if (next_seq_num + 1) * chunk_size >= len(file_content):
                    flags = 1

                packet = create_packet(next_seq_num, 0, flags, 0, data_chunk)
                if test_case != 2 or next_seq_num != 3:
                    client_socket.sendto(packet, address)
                    sent_bytes += len(packet)
                    print(f"Sent packet with seq: {next_seq_num}")
                    
                else:
                    print(f"Skipped packet with seq: {next_seq_num}")
                    

                seq_timeout[next_seq_num] = time.time()
                window[next_seq_num] = packet
                next_seq_num += 1

            ready, _, _ = select.select([client_socket], [], [], 0.5)
            if ready:
                ack_packet, _ = client_socket.recvfrom(HEADER_SIZE)
                _, ack, _, _ = parse_header(ack_packet)
                print(f"Received ACK for seq: {ack} the base is: {base}")

                if ack in window:
                    del window[ack]
                    del seq_timeout[ack]
                    acked_seq.add(ack)
                    

                    while base in acked_seq:
                        base += 1
                if flags == 1:
                        print(f"Received last ACK for seq: {ack}")
                        break

            else:
                if base * chunk_size < len(file_content):
                    print("Timeout. Resending unacknowledged packets.", base)
                    for seq, packet in window.items():
                        if seq not in acked_seq and time.time() - seq_timeout[seq] > 0.5:
                            client_socket.sendto(packet, address)
                            print(f"Resent packet with seq: {seq}")
                            seq_timeout[seq] = time.time()
        end_time = time.time()
        duration = end_time - start_time

        rate = round((sent_bytes / duration) * 8 / 1000000, 2)
        no_of_bytes = round(sent_bytes / 1024, 2)
        print(f'Total throughput: {rate} and the number of bytes sent {no_of_bytes} KB' )    


            

    # Send FIN packet to server
    fin = create_packet(0,0,2,0,b'')
    client_socket.sendto(fin, (HOST, PORT))
    print('File transfer complete')

    # Wait for ACK from server
    print('Waiting for ACK from server...')
    ack, address = client_socket.recvfrom(1460)
    _,_, flag_check, _ = parse_header(syn_ack[:12])
    _, ack_flag, _ = parse_flags(flag_check)
    if ack_flag:
        print('ACK received from server')
        print('Connection closed successfully!')
    else:
        print('No ACK received from server')

    # Close the connection
    client_socket.close()

def main():


    # Parse command line arguments
    parser = argparse.ArgumentParser(description='RTP file transfer application')
    parser.add_argument('-c', '--client',action='store_true', help='run as client')
    parser.add_argument('-s', '--server',action='store_true', help='run as server')
    parser.add_argument('-i', '--ip',help='Server IP address')
    parser.add_argument('-p', '--port',type=int, help='Server port number')
    parser.add_argument('-f', '--filename',nargs='?', default=None, help='File to transfer (client mode only)')
    parser.add_argument('-r', '--reliability_function', choices=['stop_and_wait', 'gbn', 'sr'], help='Reliability function to use')
    parser.add_argument('-t', '--test_case',help='Server IP address')
    parser.add_argument('-w', '--window_size', type=int, choices=[5,10,15], help='Reliability function to use')

    args = parser.parse_args()

    #A server or client cannot run –s and –c at the same time
    if args.server and args.client:
        print('Cannot specify both server and client mode')
        return

    #Check if neither server nor client mode is enabled, and print an error message if so
    if not args.server and not args.client:
        print('Must specify either server or client mode')
        return

    #if server mode is enabled, call the server() function
    if args.server:
        server(args)

    #if client mode is enabled, call the client() function
    if args.client:
        client(args)

if __name__ == '__main__':
    main()