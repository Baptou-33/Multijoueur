import network, sys, pygame, random, xlog, time, colorsys

pygame.init()

w, h = 800, 800 # Taille de la fenêtre
size = [w, h]
black = [0, 0, 0] # Couleur noire
speed = 2 # Vitesse de notre joueur

sock = network.Sock()
destination = ["192.168.0.255", 33077] # adresse à laquelle on envoie les messages
# \-> elle se termine par 255 car c'est l'adresse de broadcast,
#     c'est-à-dire de diffusion à toutes les machines du réseau local.
#     Si ça ne marche pas chez vous, essayez de la remplacer par 192.168.1.255
address = ("0.0.0.0", 33077) # adresse par laquelle on reçoit les messages
# \-> cette adresse est spéciale, elle signifie qu'on écoute partout,
#     aussi bien sur la machine que sur le réseau local.
#     Le port 33077 peut être remplacé par n'importe quel nombre entre 1024 et 65535,
#     Il faut juste que tous les joueurs utilisent le même (dans destination et
#     dans address) sinon ils n'entendront pas leurs messages !

# Créer une couleur aléatoire
def random_color():
	return [int(i*255) for i in colorsys.hsv_to_rgb(random.random(), 0.8, 1)]

# Créer un identifiant d'objet aléatoire
def new_oid():
	return random.randint(0,2147483648)

# Définit les méthodes par défaut d'un objet
class Obj:
	def __init__(self, oid):
		self.oid = oid
	def update(self): pass
	def draw(self, surface): pass
	def print_debug(self, lines): pass
	def damage(self, dmg): pass
	def blocking(self):
		return False

# Définit un joueur
class Player(Obj):
	def __init__(self, oid, pos, color):
		Obj.__init__(self, oid)
		self.pos = pos
		self.speed = [0, 0]
		self.color = color
		self.direction = [2, 0]
		self.life = 100
	
	# Mise à jour de l'état du joueur
	def update(self):
		if self.speed != [0, 0]:
			self.direction = [self.speed[0], self.speed[1]]
		self.pos[0] += self.speed[0]
		self.pos[1] += self.speed[1]
	
	# Dessiner le joueur
	def draw(self, surface):
		pygame.draw.rect(surface, self.color, (self.pos[0]-8, self.pos[1]-8, 16, 16))
		pygame.draw.rect(surface, [64,255,64], (self.pos[0]-8, self.pos[1]-16, self.life*16//100, 4))
	
	# Afficher le texte d'information
	def print_debug(self, lines):
		lines.append("Player {} pos=({}, {}) speed=({}, {})".format(self.oid, self.pos[0], self.pos[1], self.speed[0], self.speed[1]))
	
	# Est-ce que l'objet bloque les balles
	def blocking(self):
		return True
	
	# Recevoir des dégâts
	def damage(self, dmg):
		global removable, me
		self.life -= dmg # perdre des points de vie
		if self.life <= 0: # si le joueur n'a plus de vie
			if self == me: # si c'est moi
				# Réapparaître avec la vie max à un endroit aléatoire
				self.life = 100
				self.pos = [random.randint(16, w-16), random.randint(16, h-16)]
				send_move() # donner à tout le monde notre nouvelle position
			else: # si c'est un autre joueur
				# Supprimer son cadavre
				removable.append(self.oid)
				# (s'il veut réapparaître, il nous enverra sa nouvelle position plus tard)

# Définit une balle
class Bullet(Obj):
	def __init__(self, oid, pos, speed, color):
		Obj.__init__(self, oid)
		self.pos = pos
		self.speed = speed
		self.color = color
	
	# Mise à jour de l'état de la balle
	def update(self):
		global objects, removable
		
		# Faire bouger la balle
		self.pos[0] += self.speed[0]
		self.pos[1] += self.speed[1]
		
		# Si la balle est en-dehors de l'écran, la supprimer
		if abs(self.pos[0]) > w or abs(self.pos[1]) > h:
			removable.append(self.oid)
		
		# Vérifier les collisions avec tous les objets
		for oid in objects: # pour tous les objets...
			obj = objects[oid]
			if obj.blocking(): # si l'objet est bloquant
				# si la balle est très près de l'objet
				if abs(self.pos[0]-obj.pos[0]) < 8 and abs(self.pos[1]-obj.pos[1]) < 8:
					obj.damage(10) # causer des dommages
					removable.append(self.oid) # supprimer la balle
	
	# Dessiner la balle
	def draw(self, surface):
		pygame.draw.rect(surface, self.color, (self.pos[0]-2, self.pos[1]-2, 4, 4))
	
	# Afficher le texte d'information
	def print_debug(self, lines):
		lines.append("Bullet {} pos=({}, {}) speed=({}, {})".format(self.oid, self.pos[0], self.pos[1], self.speed[0], self.speed[1]))

screen = pygame.display.set_mode(size) # définir la taille de la fenêtre
clock = pygame.time.Clock()
sock.listen(address) # commencer à écouter les messages du réseau

# Créer notre propre joueur
me = Player("Pascal", [random.randint(16, w-16), random.randint(16, h-16)], random_color())
objects = {me.oid: me} # dictionnaire de tous les objets
players = {me.oid: me} # dictionnaire de tous les joueurs (qui sont aussi des objets)
removable = [] # identifiants des objets à supprimer

# Supprimer les objets à supprimer
def remove_objects():
	global removable, objects, players
	for oid in removable:
		if oid in objects:
			objects.pop(oid)
		if oid in players:
			players.pop(oid)
	removable.clear()

# Envoyer notre nouvelle position
def send_move():
	global me, destination
	sock.send({
		"type": "move",
		"x": me.pos[0],
		"y": me.pos[1],
		"oid": me.oid,
		"color": me.color,
		"life": me.life
	}, destination)

# Dire à tout le monde qu'on envoie une balle
def send_fire(bullet):
	global me, destination
	sock.send({"type": "fire", "pos": bullet.pos, "oid": me.oid, "speed": bullet.speed}, destination)

# Dire à tout le monde qu'on quitte la partie
def send_exit():
	global me, destination
	sock.send({"type": "exit", "oid": me.oid}, destination)

# Dès le début, prévenir les autres qu'on existe
send_move()

# Boucle principale
while True:
	# Lecture des événements
	for event in pygame.event.get():
		if event.type == pygame.QUIT: # fenêtre fermée
			send_exit()
			sys.exit()
		if event.type == pygame.KEYDOWN: # touche pressée
			if event.key == pygame.K_ESCAPE: # échap
				send_exit()
				sys.exit()
			if event.key == pygame.K_RIGHT:
				me.speed[0] = speed
			elif event.key == pygame.K_LEFT:
				me.speed[0] = -speed
			elif event.key == pygame.K_DOWN:
				me.speed[1] = speed
			elif event.key == pygame.K_UP:
				me.speed[1] = -speed
			elif event.key == pygame.K_SPACE:
				# Créer une balle
				bullet = Bullet( # avec ses informations :
					new_oid(), # son identifiant
					[me.pos[0] + me.direction[0] * 8, me.pos[1] + me.direction[1] * 8], # sa position
					[me.direction[0] * 5, me.direction[1] * 5], # sa vitesse
					[255, 255, 255] # couleur blanche
				)
				# Mettre le nouveau joueur dans les listes des joueurs et des objets
				objects[bullet.oid] = bullet
				# Dire à tout le monde qu'on a envoyé une balle
				send_fire(bullet)
		elif event.type == pygame.KEYUP: # touche relâchée
			if event.key == pygame.K_RIGHT:
				me.speed[0] = 0
			elif event.key == pygame.K_LEFT:
				me.speed[0] = 0
			elif event.key == pygame.K_DOWN:
				me.speed[1] = 0
			elif event.key == pygame.K_UP:
				me.speed[1] = 0

	# Lecture du réseau
	for d, a in sock.get():
		# Vérifier que le message contient bien l'identifiant du joueur
		if not "oid" in d:
			continue
		
		# Ne pas écouter nos propres messages
		if d["oid"] == me.oid: # si ce message vient de nous...
			continue # ...passer au message suivant
		
		# Un joueur nous dit sa nouvelle position
		if d["type"] == "move":
			if not "x" in d or not "y" in d:
				continue
			if d["oid"] in players: # si on connaît déjà ce joueur
				players[d["oid"]].pos = [d["x"], d["y"]]
			else: # sinon (on ne le connaît pas encore)
				# Créer le nouveau joueur
				new_player = Player( # avec ses informations :
					d["oid"], # son identifiant
					[d["x"], d["y"]], # sa position
					d["color"] if "color" in d else random_color() # sa couleur s'il en a donné une
				)
				# Mettre le nouveau joueur dans les listes des joueurs et des objets
				players[d["oid"]] = new_player
				objects[d["oid"]] = new_player
		
		# Un joueur quitte la partie
		elif d["type"] == "exit":
			removable.append(d["oid"]) # supprimer le joueur
		
		# Un joueur a tiré une balle
		elif d["type"] == "fire":
			# Créer la balle
			bullet = Bullet( # avec ses informations :
				new_oid(), # son identifiant
				d["pos"], # sa position
				d["speed"], # sa vitesse
				[255, 255, 255] # couleur blanche
			)
			# Mettre la balle dans la liste des objets
			objects[d["oid"]] = bullet

	remove_objects()
	
	screen.fill(black) # colorier le fond en noir
	
	# Mettre à jour tous les objets
	lines = []
	for oid in objects:
		obj = objects[oid]
		obj.update()
		obj.draw(screen)
		obj.print_debug(lines)

	remove_objects()
	
	# Envoyer notre nouvelle position, mais seulement si on bouge
	if me.speed[0] != 0 or me.speed[1] != 0:
		send_move()
	
	xlog.display(screen, lines) # afficher le texte d'information
	
	pygame.display.flip() # mettre à jour l'écran
	clock.tick(30) # attendre un peu
