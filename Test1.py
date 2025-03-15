import network, sys, time

sock = network.Sock()
destination = ['192.168.0.2', 33077]

sock.send("test", destination)
