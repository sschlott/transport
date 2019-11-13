# File: TCPSimulator.py

"""
This module implements the starter version of the TCP simulator assignment.
"""

# Implementation notes for Problem Set 5
# --------------------------------------
# For Problem 1, you will need to add more state information to both the
# TCPClient and TCPServer classes to keep track of which bytes have been
# acknowledged.  You will also need to implement a new TCPEvent subclass
# called TimeoutEvent that implements the response to a packet timeout. (CHECK)
# Sending a packet should also post a TimeoutEvent for a later time.
# If the packet has been acknowledged, the TimeoutEvent handler can simply
# ignore it.  If not, the TimeoutEvent handler should resend the packet.
#
# Problem 2 requires relatively little code beyond Problem 1, assuming
# that you have coded Problem 1 correctly (bugs in Problem 1 are likely
# to manifest themselves here when there are multiple pipelined messages).
# The priority queue strategy means that you don't need to use any
# Python primitives for parallelism such as timeouts and threads.
#
# Problem 3 means that you need to have the client keep track of the
# number of unacknowledged packets and to pay attention to the receive
# window in the acknowledgments that come in from the server.

from packet import TCPPacket,checksum16
from pqueue import PriorityQueue
import random
# Constants

MAX_PACKET_DATA = 4
TRANSMISSION_DELAY = 5
LOST_PACKET_PROBABILITY = 0.25
ROUND_TRIP_TIME = 2 * TRANSMISSION_DELAY
TIMEOUT = 2 * ROUND_TRIP_TIME

EVENT_TRACE = True              # Set this flag to enable event tracing

def TCPSimulator():
    """
    This function implements the test program for the assignment.
    It begins by creating the client and server objects and then
    executes an event loop driven by a priority queue for which
    the priority value is time.
    """
    eventQueue = PriorityQueue()
    client = TCPClient()
    server = TCPServer()
    client.server = server
    server.client = client
    client.queueRequestMessage(eventQueue, 0)
    # server.queueTimeoutMessage(eventQueue)
    # client.queueRequestMessage()
    while not eventQueue.isEmpty():
        e,t = eventQueue.dequeueWithPriority()
        if EVENT_TRACE:
            print(str(e) + " at time " + str(t))
        e.dispatch(eventQueue, t)


class TCPClient:
    """
    This class implements the client side of the simulation, which breaks
    up messages into small packets and then sends them to the server.
    """

    def __init__(self):
        """Initializes the client structure."""
        self.awaitingAck = {}

    def requestMessage(self, eventQueue, t):
        """Initiates transmission of a message requested from the user."""
        msg = input("Enter a message: ")
        if (len(msg) != 0):
            print("Client sends \"" + msg + "\"")
            self.msgBytes = msg.encode("UTF-8")
            self.seq = 0
            self.ack = 0
    
            self.sendNextPacket(eventQueue, t)

    def sendNextPacket(self, eventQueue, t):
        """Sends the next packet in the message."""
        nBytes = min(MAX_PACKET_DATA, len(self.msgBytes) - self.seq)
        data = self.msgBytes[self.seq:self.seq + nBytes]
        p = TCPPacket(seq=self.seq, ack=self.ack, ACK=True, data=data)
        if self.seq + nBytes == len(self.msgBytes):
            p.FIN = True
        self.awaitingAck[checksum16(p.toBytes())] = p
        if keepPacketBool():
            e = ReceivePacketEvent(self.server, p)
            eventQueue.enqueue(e, t + TRANSMISSION_DELAY)
        self.queueTimeoutMessage(p,eventQueue,t)   
        if p.FIN:
            self.queueRequestMessage(eventQueue, t + TIMEOUT)

    def receivePacket(self, p, eventQueue, t):
        """Handles receipt of the acknowledgment packet."""
        self.seq = p.ack
        self.ack = p.seq + 1
        if self.seq < len(self.msgBytes):
            self.sendNextPacket(eventQueue, t)

    def queueRequestMessage(self, eventQueue, t):
        """Enqueues a RequestMessageEvent at time t."""
        e = RequestMessageEvent(self)
        eventQueue.enqueue(e, t)



class TCPServer:
    """
    This class implements the server side of the simulation, which
    receives packets from the client side.
    """

    def __init__(self):
        self.resetForNextMessage()

    def receivePacket(self, p, eventQueue, t):
        """
        Handles packets sent from the server and sends an acknowledgment
        back in return.  This version assumes that the sequence numbers
        appear in the correct order.
        """
        self.msgBytes.extend(p.data)
        self.seq = p.ack
        self.ack = p.seq + len(p.data)
        reply = TCPPacket(seq=self.seq, ack=self.ack, ACK=True, checksum = ~checksum16(p.toBytes()))
        if p.FIN:
            reply.FIN = True
            print("Server receives \"" + self.msgBytes.decode("UTF-8") + "\"")
            self.resetForNextMessage()
        e = ReceivePacketEvent(self.client, reply)
        eventQueue.enqueue(e, t + TRANSMISSION_DELAY)

    def resetForNextMessage(self):
        """Initializes the data structures for holding the message."""
        self.msgBytes = bytearray()
        self.ack = 0

    def queueTimeoutMessage(self,packet,eventQueue,t):
        event = TimeoutEvent(packet)
        eventQueue.enqueue(event,TIMEOUT)

class TCPEvent:
    """
    This abstract class is the base class of all events that can be
    entered into the event queue in the simulation.  Every TCPEvent subclass
    must define a dispatch method that implements that event.
    """

    def __init__(self):
        """Each subclass should call this __init__ method."""

    def dispatch(self, eventQueue, t):
        raise Error("dispatch must be implemented in the subclasses")

class TimeoutEvent(TCPEvent):
    '''
    For pt 2.1
    '''
    def __init__(self,handler,packet):
        """Each subclass should call this __init__ method."""
        TCPEvent.__init__(self)
        self.handler = handler
        self.packet = packet
    def dispatch(self, eventQueue, t):
        #if the thing has been ACK or FIN, do nothing , otherwise ERROR
        if self.awaitingAck[self.checksum]:
            self.handler.ReceivePacket(packet, eventQueue, t)
            print("this event has  timed out  ") 
        else:
            pass



class RequestMessageEvent(TCPEvent):
    """
    This TCPEvent subclass triggers a message transfer by asking
    the user for a line of text and then sending that text as a
    TCP message to the server.
    """

    def __init__(self, client):
        """Creates a RequestMessageEvent for the client process."""
        TCPEvent.__init__(self)
        self.client = client

    def __str__(self):
        return "RequestMessage(client)"

    def dispatch(self, eventQueue, t):
        self.client.requestMessage(eventQueue, t)




class ReceivePacketEvent(TCPEvent):
    """
    This TCPEvent subclass is called on each packet.
    """

    def __init__(self, handler, packet):
        """
        Creates a new ReceivePacket event.  The handler parameter is
        either the client or the server.  The packet parameter is the
        TCPPacket object.
        """
        TCPEvent.__init__(self)
        self.handler = handler
        self.packet = packet

    def __str__(self):
        return "ReceivePacket(" + str(self.packet) + ")"

    def dispatch(self, eventQueue, t):
        self.handler.receivePacket(self.packet, eventQueue, t)

def keepPacketBool():
    if LOST_PACKET_PROBABILITY > random.random():
        return False
    else:
        return True 


# Startup code

if __name__ == "__main__":
    TCPSimulator()
