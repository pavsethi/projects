# Final Skeleton
#
# Hints/Reminders from Lab 3:
#
# To check the source and destination of an IP packet, you can use
# the header information... For example:
#
# ip_header = packet.find('ipv4')
#
# if ip_header.srcip == "1.1.1.1":
#   print "Packet is from 1.1.1.1"
#
# Important Note: the "is" comparison DOES NOT work for IP address
# comparisons in this way. You must use ==.
# 
# To send an OpenFlow Message telling a switch to send packets out a
# port, do the following, replacing <PORT> with the port number the 
# switch should send the packets out:
#
#    msg = of.ofp_flow_mod()
#    msg.match = of.ofp_match.from_packet(packet)
#    msg.idle_timeout = 30
#    msg.hard_timeout = 30
#
#    msg.actions.append(of.ofp_action_output(port = <PORT>))
#    msg.data = packet_in
#    self.connection.send(msg)
#
# To drop packets, simply omit the action.
#

from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()

class Final (object):
  """
  A Firewall object is created for each switch that connects.
  A Connection object for that switch is passed to the __init__ function.
  """
  def __init__ (self, connection):
    # Keep track of the connection to the switch so that we can
    # send it messages!
    self.connection = connection

    # This binds our PacketIn event listener
    connection.addListeners(self)

  def do_final (self, packet, packet_in, port_on_switch, switch_id):
    # This is where you'll put your code. The following modifications have 
    # been made from Lab 3:
    #   - port_on_switch: represents the port that the packet was received on.
    #   - switch_id represents the id of the switch that received the packet.
    #      (for example, s1 would have switch_id == 1, s2 would have switch_id == 2, etc...)
    # You should use these to determine where a packet came from. To figure out where a packet 
    # is going, you can use the IP header information.


    def accept(port_num):
     msg = of.ofp_flow_mod()
     msg.match = of.ofp_match.from_packet(packet)
     msg.idle_timeout = 30
     msg.hard_timeout = 30

     msg.actions.append(of.ofp_action_output(port = port_num))
     msg.data = packet_in
     self.connection.send(msg)

    def flood():
      msg = of.ofp_flow_mod()                                             #installs a "rule" in the switch
      msg.match = of.ofp_match.from_packet(packet)  
      msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))      #might need to use OFPP_ALL instead
      msg.idle_timeout = 30                                               #removes rule after 30 seconds
      msg.hard_timeout = 30
      msg.data = packet_in                                  #matches msg ID with the incoming packet ID for switch
      self.connection.send(msg)

    def drop():
      msg = of.ofp_flow_mod()
      msg.match = of.ofp_match.from_packet(packet)
      msg.idle_timeout = 30                       #removes rule after 30 seconds
      msg.hard_timeout = 30
      msg.data = packet_in                      #matches msg ID with the incoming packet ID for switch
      self.connection.send(msg)

    #1) ARP Broadcast (flood)
    #2) ICMP echo packet (accept)
    #3) 

    #make helper function accept(port_num) --> take psuedocode from top 
    #if ARP packet
      #flood 

    #check if packeet is IP or not
      #if it is IP:
        #if port in switch is 15 (untrusted host)
          #drop packet
        #if port in switch is 14 (trusted host)
          #direct packet to Host 10-40 but drop for anywhere else
        #if packet is from Host10-40 and going to host 50-80
          #drop the packet

    ip_addrMap = {"10.1.1.10": 12, "10.1.2.20": 12, "10.1.3.30": 13, "10.1.4.40": 13,
                  "10.2.5.50": 17, "10.2.6.60": 17, "10.2.7.70": 16, "10.2.8.80": 16,
                  "108.24.31.112": 14, "106.44.82.103": 15, "10.3.9.90": 18,
                  }       #dest ip to port number for Core Switch

    #accept(ip_addrMap[dst])

    # if packet.find('ipv4'):
    #   print("ipv4")
    # if packet.find('icmp'):
    #   print("icmp")
    # if packet.find('arp'):
    #   print('arp')
    # print("-------------------")

    ip = packet.find('ipv4')

    if ip is None:
      flood()

    elif ip:
      ip = packet.find('ipv4')
      dst = str(ip.dstip) #destination IP address
      src = str(ip.srcip) #source IP address

      if switch_id == 11:     #floor 1 switch 1
        #check dest ip's and do port
        print("this is switch 1")
        if dst == "10.1.1.10":
          accept(1)
        elif dst == "10.1.2.20":
          accept(2)
        elif packet.find('icmp'):   #if host 10-20 are sending ICMP packet to Host50-80 drop
          if port_on_switch == 1 or port_on_switch == 2:
            if dst == "10.2.5.50" or dst == "10.2.6.60" or dst == "10.2.7.70" or dst == "10.2.8.80":
              print("h10 pinging h50-80 --> drop")
              drop()
            else:
              accept(3)
          else:
            accept(3)
        else:
          accept(3)   #accept if not icmp
      
      elif switch_id == 12:   #floor 1 switch 2
        if dst == "10.1.3.30":
          accept(4)
        elif dst == "10.1.4.40":
          accept(5)
        elif packet.find('icmp'):   #if host 30-40 are sending ICMP packet to Host50-80 drop
          if port_on_switch == 4 or port_on_switch == 5:
            if dst == "10.2.5.50" or dst == "10.2.6.60" or dst == "10.2.7.70" or dst == "10.2.8.80":
              drop()
            else:
              accept(6)
          else:
            accept(6)
        else:
          accept(6)   #accept if not icmp
      
      elif switch_id == 21:   #floor 2 switch 1
        if dst == "10.2.5.50":
          accept(7)
        elif dst == "10.2.6.60":
          accept(8)
        elif packet.find('icmp'):   #if host 50-60 are sending ICMP packet to Host10-40 drop
          if port_on_switch == 7 or port_on_switch == 8:
            if dst == "10.1.1.10" or dst == "10.1.2.20" or dst == "10.1.3.30" or dst == "10.1.4.40":
              drop()
            else:
              accept(19)
          else:
            accept(19)
        else:
          accept(19)   #accept if not icmp
    

      elif switch_id == 22:   #floor 2 switch 2
        if dst == "10.2.7.70":
          accept(9)
        elif dst == "10.2.8.80":
          accept(10)
        elif packet.find('icmp'):   #if host 70-80 are sending ICMP packet to Host10-40 drop
          if port_on_switch == 9 or port_on_switch == 10:
            if dst == "10.1.1.10" or dst == "10.1.2.20" or dst == "10.1.3.30" or dst == "10.1.4.40":
              drop()
            else:
              accept(20)
          else:
            accept(20)
        else:
          accept(20)   #accept if not icmp
      
      elif switch_id == 5:    #core switch
        print("reached core switch")
        if port_on_switch == 15 and packet.find('ipv4') and dst == "10.3.9.90":     #if untrusted host is sending IP to server
          drop()
        elif port_on_switch == 15 and packet.find('icmp') and dst != "108.24.31.112": #if untrusted host is sending ICMP to anywhere but trusted host
          drop()
        elif port_on_switch == 14 and packet.find('ipv4') and dst == "10.3.9.90":     #if trusted host is sending IP to server
          drop()
        elif port_on_switch == 14 and packet.find('icmp'):     #if trusted host is sending an ICMP packet to host 50-80 or server
          if dst == "10.2.5.50" or dst == "10.2.6.60" or dst == "10.2.7.70" or dst == "10.2.8.80" or dst == "10.3.9.90":
            drop()
          else:
            accept(ip_addrMap[dst])
        else:
          accept(ip_addrMap[dst])

      elif switch_id == 6:    #data center switch
        if port_on_switch == 11:
          accept(21)
        else:
          accept(11)


    #   if ip.srcip == "106.44.82.103" && switch_id = "s5":       # && swtich_id == s5?? core switch
    #     msg = of.ofp_flow_mod()
    #     msg.match = of.ofp_match.from_packet(packet)
    #     msg.idle_timeout = 30                                       #removes rule after 30 seconds
    #     msg.hard_timeout = 30
    #     msg.buffer_id = packet_in.buffer_id                 #matches msg ID with the incoming packet ID for switch
    #     self.connection.send(msg)





    # if packet.type != packet.IP_TYPE:
    #  #flood the packet if it is TCP or ARP
    #   msg = of.ofp_flow_mod()           #installs a "rule" in the switch
    #   msg.match = of.ofp_match.from_packet(packet)  
    #   msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))      #might need to use OFPP_ALL instead
    #   msg.idle_timeout = 30                       #removes rule after 30 seconds
    #   msg.hard_timeout = 30
    #   msg.buffer_id = packet_in.buffer_id         #matches msg ID with the incoming packet ID for switch
    #   self.connection.send(msg)

    # else:
    #   msg = of.ofp_flow_mod()
    #   msg.match = of.ofp_match.from_packet(packet)
    #   msg.idle_timeout = 30                       #removes rule after 30 seconds
    #   msg.hard_timeout = 30
    #   msg.buffer_id = packet_in.buffer_id         #matches msg ID with the incoming packet ID for switch
    #   self.connection.send(msg)

  def _handle_PacketIn (self, event):
    """
    Handles packet in messages from the switch.
    """
    packet = event.parsed # This is the parsed packet data.
    if not packet.parsed:
      log.warning("Ignoring incomplete packet")
      return

    packet_in = event.ofp # The actual ofp_packet_in message.
    self.do_final(packet, packet_in, event.port, event.dpid)

def launch ():
  """
  Starts the component
  """
  def start_switch (event):
    log.debug("Controlling %s" % (event.connection,))
    Final(event.connection)
  core.openflow.addListenerByName("ConnectionUp", start_switch)