import pygame

pygame.font.init()

font = pygame.font.SysFont('FreeMono', 16)

def display(surface, lines):
	for i in range(len(lines)):
		surface.blit(font.render(lines[i], False, (255,255,255)), (0, i*20))
