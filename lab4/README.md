Pav Sethi
pssethi@ucsc.edu
pssethi
1800780

Final Project - CSE 150


In this lab, we were assigned the task of creating a IPv4 Router for a 2-story building. Our topology consists of multiple switches, subnets, and servers, interconnected by a core switch. The goal is to implement various requirements to ensure network security and proper communication between different devices.


The files included are:

project.pdf --> This pdf contains all my screenshots of commands I ran in order to ensure that my topology and controller were working efficiently according to the restrictions. 


finalcontroller_skel.py --> This file contains the actual implementation of our router within a POX controller. The router follows the restrictions specified in the assignment PDF. Taken from the PDF, this is a summary of the restrictions:
	All hosts are able to communicate, EXCEPT:
	- Untrusted Host cannot send ICMP traffic to Host 10 to 80, or the Server.
	- Untrusted Host cannot send any IP traffic to the Server.
	- Trusted Host cannot send ICMP traffic to Host 50 to 80 in Department B, or the Server.
	- Trusted Host cannot send any IP traffic to the Server.
	- Hosts in Department A (Host 10 to 40) cannot send any ICMP traffic to the hosts in
	Department B (Host 50 to 80), and vice versa. 


final_skel.py --> This file contains our topology. A picture of the topology is attached in the project.pdf


README --> Explains usage of program


Running the Code:

To run the controller, first move it to /pox/pox/misc directory and then:

...

$ sudo ~/pox/pox.py misc.finalcontroller_skel


...

To run the mininet script, run:

...

$ sudo python ~/final_skel.py


...


