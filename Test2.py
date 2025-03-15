import network, sys, time

sock = network.Sock()
address = ("0.0.0.0", 33077)

sock.listen(address)
while True:
	for d, a in sock.get():
		print(a, d)
	time.sleep(0.1)
