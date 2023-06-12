# Reliable-Transport-Protocol-Over-UDP


General description of the Reliable Transport Protocol (DRTP).
Here I will explain about Reliable Transport Protocol. The Reliable Transport Protocol (RTP) is a communications protocol that ensures reliable and ordered delivery of data packets over a network. It is primarily used for streaming multimedia applications such as voice and video transmission. Overall, RTP provides a reliable and ordered transport mechanism for real-time multimedia applications. Ensuring the delivery of packets, maintaining packet order, and supporting flow control, error detection, and timestamping, enables the smooth transmission and playback of audio and video content over networks. In this protocol, there is something called Three-Way Handshake, and it is dis1nguished primarily in that it guarantees reliable reliability in the communica1on process that is, making sure that all data packets arrive between the two devices and that none of them is lost in the way for any reason. This process is named three-way because it takes place in three stages: A sends a packet containing a signal called SYN to B. The packet reaches B, and it responds by sending a packet containing a SYN-ACK to device A. When the response reaches A, it retransmits another packet with ACK signal to B, indica1ng that the negotiation is complete, and only then is the actual connec1on started, and the connection at this point becomes ESTABLISHED STATE.
Explana1on GBN, SR and Stop-and-Wait.

We have three algorithms: 1, Stop and wait 2, Go back n 3, Selec1ve repeat. I will explain each of those algorithms:


Stop-and-Wait:
is the simplest of the three. In this algorithm, the sender sends a data packet to the receiver and then waits for an acknowledgment (ACK) from the receiver. Once the receiver receives the packet, it sends back an ACK to the sender to indicate successful recep1on. If the sender does not receive an ACK within a specified 1meout period, it assumes that the packet was lost or corrupted and retransmits the packet. The sender then waits for the ACK again before sending the next packet. This process con1nues un1l all packets have been successfully transmiYed and acknowledged.

Go-Back-N:
is a sliding window-based algorithm. In this approach, the sender is allowed to transmit
mul1ple packets without wai1ng for individual acknowledgments. The sender maintains a window of packets that can be transmiYed without acknowledgment. The receiver acknowledges the packets by sending back cumula1ve ACKs, indica1ng the highest packet sequence number received successfully. If the sender does not receive an ACK for a specific packet within a 1meout period, it assumes that the packet or some subsequent packets were lost and retransmits all the packets star1ng from that lost packet. The receiver discards duplicate packets received due to retransmission. This protocol provides efficient transmission for a high-bandwidth network but can suffer from unnecessary retransmissions if only a few packets are lost.

Selec1ve Repeat:
is also a sliding window-based algorithm, but it improves upon the Go-Back-N protocol byallowing individual packet retransmission. Both the sender and receiver maintain a window of packets. The sender can transmit mul1ple packets within this window, and the receiver can buffer out-of-order packets un1l all previous packets have been received successfully. The receiver sends individual ACKs for each received packet. If the sender does not receive an ACK for a specific packet within a 1meout period, it retransmits only that packet. This selec1ve retransmission feature minimizes unnecessary retransmissions and reduces network conges1on compared to Go-Back-N.


So, in the end, we can say, Stop-and-Wait is a simple but inefficient protocol, Go-Back-N allows sending mul1ple packets before receiving ACKs but can cause unnecessary retransmissions, and Selec1ve Repeat improves efficiency by allowing selec1ve retransmission of lost or corrupted packets. The choice of which protocol to use depends on the specific requirements of the network and the level of reliability needed for data transmission.
