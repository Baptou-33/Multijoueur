import socket, os, sys, json
from threading import Thread, Lock

NETTRACE = str(os.environ.get("NETTRACE", "0")) == "1"

class Sock:
	def __init__(self):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.queue = []
		self.queue_lock = Lock()
		self.sock_thread = None
	
	def send_raw(self, message, address):
		if type(message) == str:
			message = message.encode()
		if NETTRACE:
			print("Send to", tuple(address), ":", message, file=sys.stderr)
		self.sock.sendto(message, tuple(address))
	
	def send(self, message, address):
		message = json.dumps(message)
		if NETTRACE:
			print("Send to", tuple(address), ":", message, file=sys.stderr)
		self.sock.sendto(message.encode(), tuple(address))
	
	def listen(self, address, length=65535):
		self.sock_thread = SockThread(self, tuple(address), length)
		self.sock_thread.setDaemon(True)
		self.sock_thread.start()
	
	def get_raw(self):
		if len(self.queue) == 0:
			return []
		with self.queue_lock:
			queue = self.queue
			self.queue = []
		return queue
	
	def get(self):
		if len(self.queue) == 0:
			return []
		queue = []
		with self.queue_lock:
			for r in self.queue:
				try:
					queue.append([json.loads(r[0].decode()), r[1]])
				except:
					pass
			self.queue.clear()
		return queue

class SockThread(Thread):
	def __init__(self, sock, address, length):
		Thread.__init__(self)
		self.sock = sock
		self.length = length
		self.sock.sock.bind(tuple(address))
	
	def run(self):
		while True:
			r = self.sock.sock.recvfrom(self.length)
			if NETTRACE:
				print("Rec from", r[1], ":", r[0], file=sys.stderr)
			with self.sock.queue_lock:
				self.sock.queue.append(r)
