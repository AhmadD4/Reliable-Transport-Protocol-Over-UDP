import socket
import argparse
import time
from struct import *
from queue import Queue
import select

header_format = '!IIHH'
HEADER_SIZE = 12

 #create a packet by combining a header and data
 #using the provided sequence number, acknowledgment number, flags, window size, and data.
def create_packet(seq, ack, flags, win, data):
    #creates a packet with header information and application data
    #the input arguments are sequence number, acknowledgment number
    #flags (we only use 4 bits),  receiver window and application data 
    #struct.pack returns a bytes object containing the header values
    #packed according to the header_format !IIHH
    header = pack (header_format, seq, ack, flags, win)

    #once we create a header, we add the application data to create a packet
    #of 1472 bytes
    packet = header + data
    #return the created packet
    return packet

 #parse the header from the provided packet
def parse_header(header):
     #taks a header of 12 bytes as an argument,
     #unpacks the value based on the specified header_format
     #and return a tuple with the values
    header_from_msg = unpack(header_format, header)
     #return the parsed header values
    return header_from_msg

#extract individual flags from the provided flags value
def parse_flags(flags):
    #we only parse the first 3 fields because we're not 
    #using rst in our implementation
    #check if the SYN flag is set by performing bitwise AND with the appropriate bit position
    syn = flags & (1 << 3)
    ack = flags & (1 << 2)
    fin = flags & (1 << 1)
    #return the parsed flags as a tuple (syn, ack, fin)
    return syn, ack, fin


#here is receive_stop_and_wait function 
def receive_stop_and_wait(server_socket, expected_seq, test_case):
    #set to keep track of received sequence numbers
    recv_seq = set()
     #variable to store the received file data
    received_file = b''

    #initialize the variable skip_ack with the value False
    skip_ack = False
     #check if the test_case variable is equal to the string 'skip-ack'
    if test_case == 'skip-ack':
        #if test_case is equal to 'skip-ack', set skip_ack to True
        skip_ack = True
        #the sequence number to skip the ACK
        skip_ack_seq = 3  

    while True:
        #receive a packet from the client and get the client address
        packet, client_address = server_socket.recvfrom(1472)
        #extract the header from the packet
        header = packet[:HEADER_SIZE]
         #parse the header to extract relevant information
        seq, _, flag, _ = parse_header(header)
        if seq not in recv_seq:
             #check if the received packet is the expected one
            if seq == expected_seq:
                print(f"Received packet with seq {seq}")
                data = packet[HEADER_SIZE:]
                #if not skip_ack: Checks if the skip_ack variable is False. In other words, it checks if skipping acknowledgement is not enabled.
                #seq != skip_ack_seq: Checks if the current sequence number (seq) is not equal to the skip_ack_seq value.
                if not skip_ack or seq != skip_ack_seq:
                    #add the received sequence number to the set
                    recv_seq.add(seq)
                     #create an ACK packet with the given sequence number
                     #create_packet function with specific arguments. 
                     #The purpose of the ACK packet is to acknowledge the receipt of a packet with the corresponding sequence number (seq).
                    ack_packet = create_packet(0,seq,0,0,b'')
                    print (f'packet containing header + data of size {len(ack_packet)}')
                    server_socket.sendto(ack_packet, client_address)
                    print(f"Sent ack for seq: {seq}")
                    #update the expected sequence number
                    expected_seq += 1
                    #append the received data to the file
                    received_file += data
                else:
                    skip_ack = False
                    print(f"Skipped ack for seq: {seq}")
                #check if the FIN flag is set 
                if flag == 2: 
                    break
            else:
                print(f"Out of order packet. Expected seq: {expected_seq}, received seq: {seq}")
      #return the received file data           
    return received_file

#here is receive_gbn function
def receive_gbn(server_socket, expected_seq, test_case, WINDOW_SIZE):
    received_file = b''
    #queue to hold packets within the window size
    window = Queue(maxsize=WINDOW_SIZE)
    #flag to indicate if STOP flag is received
     #flag that indicates whether the skip-ack test case is enabled. 
    #it is initially set to False.
    stop_received = False
    #flag that indicates whether the skip-ack test case is enabled. 
    #it is initially set to False.
    skip_ack = False
    if test_case == 'skip-ack':
        #if test_case is equal to 'skip-ack', set skip_ack to True
        skip_ack = True
        skip_ack_seq = 3  

    while True:
         #receive a packet from the client and get the client address
        packet, client_address = server_socket.recvfrom(1472)
        header = packet[:HEADER_SIZE]
         #parse the header to get sequence number and flags
        seq, _, flag, _ = parse_header(header)

        if seq == expected_seq:
            print(f"Received packet with seq {seq}")
            data = packet[HEADER_SIZE:]
             #add the packet to the window queue
            window.put((seq, data, flag))
            #if not skip_ack: Checks if the skip_ack variable is False. In other words, it checks if skipping acknowledgement is not enabled.
            ##seq != skip_ack_seq: Checks if the current sequence number (seq) is not equal to the skip_ack_seq value.
            if not skip_ack or seq != skip_ack_seq:
               #create_packet function with specific arguments. 
               #The purpose of the ACK packet is to acknowledge the receipt of a packet with the corresponding sequence number (seq).
                ack_packet = create_packet(0, seq, flag, 0, b'')
                #the code sends an acknowledgment packet to the client, prints a confirmation message, and appends the received data to a file or buffer.
                server_socket.sendto(ack_packet, client_address)
                print(f"Sent ack for seq: {seq}")
                received_file += data
                 #update the expected sequence number
                expected_seq += 1
            #here is the code handles the case where the received sequence number does not match the expected sequence number. 
            #it disables the skip-ack behavior, prints a message, and updates the expected sequence number accordingly.    
            else:
                skip_ack = False
                print(f"Skipped ack for seq: {seq}")
                expected_seq = seq
              #check if the window is full or if the flag is set to 1 (STOP flag)   
            if window.full() or flag == 1:
                 #process all packets in the window
                 #the code processes packets in the window while it is not empty. 
                 #if a packet with a flag value of 1 (indicating a STOP flag) is encountered, it sets the stop_received flag and prints a corresponding message.
                while not window.empty():
                    seq, data, flag = window.get()
                    #it checks if the flag value is equal to 1.
                    if flag == 1:
                        print(f"Received STOP flag")
                        #it sets the stop_received flag to True, indicating that the STOP flag has been received.
                        stop_received = True 
            
        else:
            print(f"Out of order packet. Expected seq: {expected_seq}, received seq: {seq}")
            #clear the window queue since the received packet is out of order
            window.queue.clear()
        if stop_received:
            break

    return received_file

#here is selective repeat function 
#the code sets up variables and flags required for the selective repeat algorithm in the context of receiving packets.
def receive_sr(server_socket, expected_seq, test_case):
     #size of the sliding window
     #is set to 5, indicating the size of the sliding window.
    WINDOW_SIZE = 5
    received_file = b''
    #buffer to store out-of-order packets
    #is initialized as an empty dictionary, which will be used to store out-of-order 
    buffer = {}
    recv_seq = set()
    stop_received = False
    skip_ack = False
    if test_case == 'skip-ack':
        skip_ack = True
        skip_ack_seq = 3  
   
   #the code continuously receives packets from the server, 
   #extracts the header from each packet, and parses the header to obtain the sequence number (seq) and flag value for further processing.
    while True:
        #receive packet from the server
        packet, client_address = server_socket.recvfrom(1472)
        header = packet[:HEADER_SIZE]
        seq, _, flag, _ = parse_header(header)
 
      #the code processes non-duplicate packets by extracting the data, 
      #sending an acknowledgment, and updating the set of received sequence numbers.
        if seq not in recv_seq:
            data = packet[HEADER_SIZE:]
            if not skip_ack or seq != skip_ack_seq:
                ack_packet = create_packet(0,seq,0,0,b'')
                 #send the ACK packet to the client at client_address
                server_socket.sendto(ack_packet, client_address)
                # Print a message indicating that an acknowledgment has been sent for the specific sequence number
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

                #process all consecutive packets in the buffer
                while expected_seq in buffer:
                    received_file += buffer[expected_seq][0]
                     #remove the packet from the buffer
                    del buffer[expected_seq]
                    recv_seq.add(expected_seq)
                    expected_seq += 1
                
            else:
                print(f"Out of order packet. Expected seq: {expected_seq}, received seq: {seq}")
                buffer[seq] = (packet[HEADER_SIZE:], flag)
                
            if flag == 1:
                break
    return received_file


#here is server function
#the server function establishes a connection with the client, 
#receives a file using the specified reliability function, checks the file's completeness, 
#writes the file to disk, and sends an acknowledgment before closing the connection.
def server(args):
    #define server address and port
    HOST = args.ip
    PORT = args.port
    test_case = args.test_case
    window_size = args.window_size

    #create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    #bind the socket to a specific address and port
    server_socket.bind((HOST, PORT))

    #wait for SYN from client
    print('Waiting for SYN from client...')

     #receive SYN packet from client
    syn, address = server_socket.recvfrom(1460)
    _,_, flag, _ = parse_header(syn[:12])

    #check the SYN flag
    syn_flag, _, _ = parse_flags(flag)
    if syn_flag:
        print('SYN received from client')

        #send SYN ACK to client
        syn_ack = create_packet(0,0,12,0,b'')
        server_socket.sendto(syn_ack, address)
        print('SYN-ACK sent to client')

        #wait for ACK from client
        print('Waiting for ACK from client...')
        ack, address = server_socket.recvfrom(1460)
        _,_, flag_check, _ = parse_header(syn_ack[:12])
        _, ack_flag, _ = parse_flags(flag_check)

        if ack_flag:
            print('ACK received from client:', ack.decode())
            print('Connection established successfully!')

            #receive file from client using the specified reliability function
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

            #check if the received file is complete
            fin, address = server_socket.recvfrom(1460)
            _,_, flag_check, _ = parse_header(fin[:12])
            _, _, fin_flag = parse_flags(flag_check)
            if fin_flag:
                print('File transfer complete')
            else:
                print('File transfer incomplete:')

            #write received file to disk
            with open('received_file.jpg', 'wb') as f:
                f.write(received_file)

            #send ACK to client
            ack = create_packet(0,0,4,0,b'')
            #print (f'packet containing header + data of size {len(ack)}')
            server_socket.sendto(ack, address)
            print('ACK sent to client')

            #close the connection
            server_socket.close()
        else:
            print('No ACK received from client')
    else:
        print('No SYN received from client')

#here is client function 
#the client function establishes a connection with the server, 
#sends a file using the specified reliability function, waits for the acknowledgment, 
#and closes the connection after the file transfer is complete.
def client(args):

    #define server address and port
    HOST = args.ip
    PORT = args.port
    FILE = args.filename
    window_size = args.window_size
    timeout = 5
    sent_bytes = 0

    #create a socket object
    #a socket object is created using socket.socket() with the appropriate address family and socket type.
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    #send SYN to server
    #The client sends a SYN packet to the server to initiate the connection. 
    #The SYN packet contains the necessary flags and information.
    syn = create_packet(0,0,8,0,b'')
    client_socket.sendto(syn, (HOST, PORT))
    print('SYN sent to server')

    #wait for SYN-ACK from server
    #the client waits to receive a SYN-ACK packet from the server, confirming the establishment of the connection. 
    #it sets a timeout for receiving the SYN-ACK packet and retries until the timeout period has elapsed.
    syn_ack = None
    start_time = time.time()
    while not syn_ack:
        #check if timeout period has elapsed
        if time.time() - start_time > timeout:
            print('Timeout waiting for SYN-ACK')
            return

        #receive SYN ACK from server
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
    
    #If the reliability function is "stop_and_wait," the client sends each packet and waits for the acknowledgment before sending the next packet. 
    #it handles cases where packets may be skipped or received out of order.
    if reliability_function == 'stop_and_wait':
        # Start measuring time
        start_time == time.time()
        if test_case == 'skip-seq':
            test_case = 2
        seq = 0
        chunk_size = 1472 - HEADER_SIZE
        received_acks = set()

        # Loop through the file content in chunks
        for i in range(0, len(file_content), chunk_size):
            
            # Repeat until the acknowledgment is received
            while True:
                # Get the data chunk
                data_chunk = file_content[i:i + chunk_size]
                flags = 0
                if i + chunk_size >= len(file_content):
                    flags = 2
                packet = create_packet(seq, 0, flags, 0, data_chunk)
                print (f'packet containing header + data of size {len(packet)}')
                start_time_packet=0
                if seq not in received_acks:
                    if test_case != 2 or seq != 1:  # Add this condition
                        client_socket.sendto(packet, address)
                        start_time_packet = time.time()
                        sent_bytes += len(packet)
                        print(f"Sent packet with seq: {seq}")
                    else:
                        print(f"Skipped packet with seq: {seq}")
                        socket.timeout

                try:
                     # Set the timeout for receiving acknowledgment
                    client_socket.settimeout(0.5)
                    ack_packet, server_address = client_socket.recvfrom(HEADER_SIZE)
                    _, ack_seq, _, _ = parse_header(ack_packet[:HEADER_SIZE])

                    if ack_seq == seq:
                        received_acks.add(seq)
                        end_time_packet=time.time()
                        print(f"Received ack for seq {seq}")
                        time_packet=end_time_packet - start_time_packet
                        rtt_pakke=round(time_packet*1000 , 2)
                        print(f"rtt for seq {seq}= {rtt_pakke}")
                        seq += 1
                        break
                    else:
                        print(f"Received out-of-order ACK: {ack_seq}")
                except socket.timeout:
                    print(f"Timeout for seq: {seq}")
                     # Set the test case to 0 (indicating no skipping)
                    test_case = 0
         # Stop measuring time
        end_time = time.time()
        # Calculate the duration
        duration = end_time - start_time

        # Calculate the throughput rate
        rate = round((sent_bytes / duration) * 8 / 1000000, 2)

        # Calculate the number of bytes sent in KB
        no_of_bytes = round(sent_bytes / 1024, 2)
        print(f'Total throughput: {rate} and the number of bytes sent {no_of_bytes} KB' ) 

        
    #If the reliability function is "gbn" (Go-Back-N), the client sends packets within the specified window size. 
    #it handles cases where packets may be skipped or received out of order.
    elif reliability_function == 'gbn':
        start_time == time.time()
        base = 0
        next_seq_num = 0
        data_queue = Queue()
        WINDOW_SIZE = window_size
        flags = 0
        test_case == 0
        if test_case == 'skip-seq':
            # Set test_case to 2 if it is 'skip-seq'
            test_case = 2
        
        for i in range(0, len(file_content), chunk_size):
            data_queue.put(file_content[i:i+chunk_size])

        window = Queue(maxsize=WINDOW_SIZE)
        while base < len(file_content):
            #send packets within the window size and while there is data in the queue
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
                        #remove packets from the window up to the acknowledged sequence number
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
                    

    #if the reliability function is "sr" (Selective Repeat), the client sends packets with sequence numbers and maintains a window of sent packets. 
    #it handles cases where packets may be skipped or received out of order.
    elif reliability_function == 'sr':
        start_time == time.time()
        base = 0
        next_seq_num = 0
        #dictionary to store sequence number and corresponding timeout
        seq_timeout = {}
        #dictionary to store sequence number and corresponding packets in the window
        window = {}
        acked_seq = set()
        WINDOW_SIZE = window_size
        test_case == 0
        if test_case == 'skip-seq':
            test_case = 2
     #snippet implements the SR protocol's sliding window mechanism to send packets from the client to the server. 
     #it handles timeouts, retransmissions, and acknowledgment tracking to ensure reliable file transfer.
        while base < len(file_content):
            #this while loop is responsible for iterating over the desired sequence numbers 
            #within the window size and extracting corresponding 
            #data chunks from the file content for further processing or transmission.
            while next_seq_num < base + WINDOW_SIZE and next_seq_num * chunk_size < len(file_content):
                data_chunk = file_content[next_seq_num * chunk_size: (next_seq_num + 1) * chunk_size]
                flags = 0
                #the if statement checks if the next sequence number (next_seq_num + 1) multiplied by the chunk size is greater than or equal to the length of the file_content. 
                #if this condition is true, it means that the current data chunk being processed is the last one in the file.
                if (next_seq_num + 1) * chunk_size >= len(file_content):
                    flags = 1

                packet = create_packet(next_seq_num, 0, flags, 0, data_chunk)
                #test_case != 2: This condition verifies if the test_case variable is not equal to 2. It is used to determine if a specific test case is being executed or not. 
                #if test_case is not equal to 2, it means that the test case being executed is different, and the code inside the if statement should be executed.
               #next_seq_num != 3: This condition checks if the value of next_seq_num is not equal to 3. If the condition is true, it means that the current sequence number is not 3, and the code inside the if statement should be executed.
                if test_case != 2 or next_seq_num != 3:
                    client_socket.sendto(packet, address)
                    sent_bytes += len(packet)
                    print(f"Sent packet with seq: {next_seq_num}")
                    
                else:
                    print(f"Skipped packet with seq: {next_seq_num}")
                    
                #t assigns the current time (obtained using time.time()) to the seq_timeout dictionary with the key next_seq_num. 
                #This is used to keep track of the time at which a packet with the sequence number next_seq_num was sent.
                seq_timeout[next_seq_num] = time.time()
                #it assigns the packet to the window dictionary with the key next_seq_num. 
                #This is done to keep a reference to the sent packet within the window, which is used for retransmission if needed.
                window[next_seq_num] = packet
                #It increments the next_seq_num variable by 1 to prepare for the next iteration and the next sequence number.
                next_seq_num += 1
            #It uses the select.select() function to check if the client_socket is ready to be read. 
            #The function waits for a maximum of 0.5 seconds (0.5 is the timeout value). 
            #If the socket becomes ready for reading within the timeout period, the variable ready will be set to a non-empty list. 
            #Otherwise, it will be an empty list. This is used to handle any incoming acknowledgment packets from the server.
            ready, _, _ = select.select([client_socket], [], [], 0.5)
            #This if statement checks if the variable ready is evaluated as True, 
            #indicating that the client_socket is ready to be read, meaning there is an incoming acknowledgment packet from the server.
            if ready:
                ack_packet, _ = client_socket.recvfrom(HEADER_SIZE)
                _, ack, _, _ = parse_header(ack_packet)
                print(f"Received ACK for seq: {ack} the base is: {base}")

                #this code block updates the state of the program by removing the acknowledged packet from the window and associated timeout record, 
                #and adds the acknowledgement number to a set for further tracking.
                if ack in window:
                    # If ack exists as a key in the window dictionary, 
                    #this line removes the corresponding entry from the dictionary. 
                    #This is done to remove the packet that has been acknowledged from the window.
                    del window[ack]
                    #: If ack exists as a key in the seq_timeout dictionary, 
                    #this line removes the corresponding entry from the dictionary. 
                    #This is done to remove the timeout record for the acknowledged packet.
                    del seq_timeout[ack]
                    #This line adds the ack value to the acked_seq set. 
                    #The purpose of this set is to keep track of the acknowledged sequence numbers.
                    acked_seq.add(ack)
                    
                   # this code block handles the processing of acknowledgments. 
                   #It advances the base sequence number if it has been acknowledged, 
                   #and if the last ACK has been received, it prints a corresponding message and terminates the loop to stop further transmissions.
                    while base in acked_seq:
                        base += 1
                #This condition checks if the flags variable is equal to 1. 
                #In the previous code, flags is set to 1 when the last packet (or chunk of data) is being sent.        
                if flags == 1:
                        print(f"Received last ACK for seq: {ack}")
                        break
            # this code block handles the case of a timeout where unacknowledged packets need to be resent. 
            #It iterates through the unacknowledged packets in the window, checks if they have exceeded the timeout duration, and resends them if necessary. It also calculates and prints the transmission statistics.
            else:

                #This condition checks if there are still packets to be sent (i.e., the base sequence number multiplied by the chunk size is less than the length of the file content).
                #If there are remaining packets to be sent, the code proceeds with resending the unacknowledged packets.
                if base * chunk_size < len(file_content):
                    #This line prints a message indicating that a timeout has occurred, 
                    #and unacknowledged packets are being resent.
                    #The value of base is also printed, indicating the current base sequence number.
                    print("Timeout. Resending unacknowledged packets.", base)
                    #This for loop iterates over the items in the window dictionary, 
                    #which contains the sequence number as the key and the corresponding packet as the value.
                    #It loops through each unacknowledged packet in the window.
                    for seq, packet in window.items():
                        #This condition checks if the current sequence number (seq) is not in the acked_seq set (meaning it has not been acknowledged) 
                        #and if the time elapsed since the packet was sent (time.time() - seq_timeout[seq]) is greater than 0.5 seconds.
                        #This condition ensures that only unacknowledged packets that have exceeded the timeout threshold are resent.
                        if seq not in acked_seq and time.time() - seq_timeout[seq] > 0.5:
                            #This line resends the packet by sending it to the specified address via the client_socket.
                            client_socket.sendto(packet, address)
                            #This line prints a message indicating that the packet with the sequence number seq has been resent.
                            print(f"Resent packet with seq: {seq}")
                            #This line updates the timeout value for the resent packet by assigning the current time to the seq_timeout dictionary with the sequence number seq as the key.
                            seq_timeout[seq] = time.time()
        #calculates the duration of the transmission, calculates the throughput rate and the number of bytes sent, 
        #and prints the total throughput and the number of bytes sent.                    
        end_time = time.time()
        duration = end_time - start_time
        #This line calculates the throughput rate in Mbps.
        rate = round((sent_bytes / duration) * 8 / 1000000, 2)
        #calculates the number of bytes sent in kilobytes (KB).
        #It divides the total number of bytes sent (sent_bytes) by 1024 to convert it from bytes to kilobytes.
        #The round() function is used to round the result to two decimal places.
        no_of_bytes = round(sent_bytes / 1024, 2)
        print(f'Total throughput: {rate} and the number of bytes sent {no_of_bytes} KB' )    


            

    #send FIN packet to server
    #This line creates a FIN packet using the create_packet function.
    #The arguments passed to the function specify the sequence number (0), 
    #acknowledgement number (0), flags (2 indicating the FIN flag), data length (0), and empty data (b'').
    fin = create_packet(0,0,2,0,b'')
    #This line sends the FIN packet to the server using the sendto method of the client_socket.
    #The fin packet is sent to the server address specified by (HOST, PORT).
    client_socket.sendto(fin, (HOST, PORT))
    #This line prints a message indicating that the file transfer is complete.
    print('File transfer complete')

    #wait for ACK from server
    #This line prints a message indicating that the client is waiting for an ACK (acknowledgment) packet from the server.
    print('Waiting for ACK from server...')
    #This line receives an ACK packet from the server using the recvfrom method of the client_socket.
    #The received packet is stored in the ack variable, and the server address from which it was received is stored in the address variable.
    ack, address = client_socket.recvfrom(1460)
    #This line extracts the flag field from the received ACK packet using the parse_header function.
    #The flag field is stored in the flag_check variable.
    _,_, flag_check, _ = parse_header(syn_ack[:12])
    #This line extracts the ACK flag from the flag_check variable using the parse_flags function.
    #The ACK flag is stored in the ack_flag variable.
    _, ack_flag, _ = parse_flags(flag_check)
    #This line checks if the ack_flag is True, indicating that the received packet is an ACK packet.
    if ack_flag:
        print('ACK received from server')
        print('Connection closed successfully!')
    #This line is the start of an else block, indicating that the ack_flag is False, 
    #indicating that the received packet is not an ACK packet.    
    else:
        print('No ACK received from server')

    #close the connection
    #the client closes the connection by closing the client socket.
    client_socket.close()

#here is main function
#the main() function parses the command line arguments, checks for server or client mode, 
#and calls the respective functions based on the mode specified. It ensures that only one mode is enabled at a time and provides the necessary arguments to the server and client functions.
def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='RTP file transfer application')
    parser.add_argument('-c', '--client',action='store_true', help='run as client')
    parser.add_argument('-s', '--server',action='store_true', help='run as server')
    parser.add_argument('-i', '--ip', default='127.0.0.1', help='Server IP address')
    parser.add_argument('-p', '--port',type=int, default=8088, help='Server port number')
    parser.add_argument('-f', '--filename',nargs='?', default=None, help='File to transfer (client mode only)')
    parser.add_argument('-r', '--reliability_function', choices=['stop_and_wait', 'gbn', 'sr'], help='Reliability function to use')
    parser.add_argument('-t', '--test_case',help='Server IP address')
    parser.add_argument('-w', '--window_size', type=int, choices=[5,10,15], default= 5, help='Reliability function to use')

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
