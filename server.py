import copy
import math
import os
import random

import cherrypy

"""
This is a simple Battlesnake server written in Python.
For instructions see https://github.com/BattlesnakeOfficial/starter-snake-python/README.md
"""


class Battlesnake(object):
	global neighbours
	
	@cherrypy.expose
	@cherrypy.tools.json_out()
	def index(self):
		# This function is called when you register your Battlesnake on play.battlesnake.com
		# It controls your Battlesnake appearance and author permissions.
		# TIP: If you open your Battlesnake URL in browser you should see this data
		return {
			"apiversion": "1",
			"author": "",  # TODO: Your Battlesnake Username
			"color": "#B765CD",  # TODO: Personalize
			"head": "default",  # TODO: Personalize
			"tail": "default",  # TODO: Personalize
		}
	
	@cherrypy.expose
	@cherrypy.tools.json_in()
	def start(self):
		# This function is called everytime your snake is entered into a game.
		# cherrypy.request.json contains information about the game that's about to be played.
		data = cherrypy.request.json
		
		print("START")
		return "ok"
	
	def get_head_radii_coordinates(self, head):
		top_btm_coordinates = [
			{
				'x': head['x'],
				'y': head['y'] - 1
			}
			,
			{
				'x': head['x'],
				'y': head['y'] + 1
			}
		]
		left_right_coordinates = [
			{
				'x': head['x'] - 1,
				'y': head['y']
			}
			,
			{
				'x': head['x'] + 1,
				'y': head['y']
			}
		]
		diagonal_coord = [
			{
				'x': head['x'] + 1,
				'y': head['y'] + 1
			}
			,
			{
				'x': head['x'] - 1,
				'y': head['y'] - 1
			}
		]
		return top_btm_coordinates + left_right_coordinates + diagonal_coord
	
	def get_distance_bw_2_points(self, p1, p2):
		return math.sqrt(((p1[0] - p2[0]) ** 2) + ((p1[1] - p2[1]) ** 2))
	
	def get_neighbours(self, data):
		neighbours = []
		min_dist = 9999999
		min_dist_id = ""
		for snek in data['board']['snakes']:
			if snek['id'] != data['you']['id']:
				p1 = [data['you']['head']['x'], data['you']['head']['y']]
				p2 = [snek['head']['x'], snek['head']['y']]
				dist = self.get_distance_bw_2_points(p1, p2)
				if dist < min_dist:
					min_dist_id = snek['id']
				neigh_coord = self.get_head_radii_coordinates(data['you']['head'])
				for snek_bdy_coord in snek['body']:
					if snek_bdy_coord in neigh_coord:
						neighbours.append(snek['id'])
						break
		if len(neighbours) == 0:
			neighbours.append(min_dist_id)
		return neighbours
	
	def will_go_out_of_bounds(self, data, direction):
		head = data['you']['head']
		if direction == "up" and head['y'] == data['board']['height'] - 1:
			return True
		elif direction == "down" and head['y'] == 0:
			return True
		elif direction == "right" and head['x'] == data['board']['width'] - 1:
			return True
		elif direction == "left" and head['x'] == 0:
			return True
		
		return False
	
	def will_collide_with_self(self, data, direction):
		head = data['you']['head']
		your_body = data['you']['body']
		if direction == "up" and {
			'x': head['x'],
			'y': head['y'] + 1
		} in your_body:
			return True
		elif direction == "down" and {
			'x': head['x'],
			'y': head['y'] - 1
		} in your_body:
			return True
		elif direction == "right" and {
			'x': head['x'] + 1,
			'y': head['y']
		} in your_body:
			return True
		elif direction == "left" and {
			'x': head['x'] - 1,
			'y': head['y']
		} in your_body:
			return True
		
		return False
	
	def will_hit_another_snake(self, data, direction, neighbours):
		head = data['you']['head']
		for snake in data['board']['snakes']:
			res = True
			if len(neighbours) > 0:
				res = data['you']['id'] != snake['id'] and snake['id'] in neighbours
			else:
				res = data['you']['id'] != snake['id']
			if res:
				opponent_body = snake['body']
				if direction == "up":
					if {
						'x': head['x'],
						'y': head['y'] + 1
					} in opponent_body:
						return True
				elif direction == "down":
					if {
						'x': head['x'],
						'y': head['y'] - 1
					} in opponent_body:
						return True
				elif direction == "right":
					if {
						'x': head['x'] + 1,
						'y': head['y']
					} in opponent_body:
						return True
				elif direction == "left":
					if {
						'x': head['x'] - 1,
						'y': head['y']
					} in opponent_body:
						return True
		
		return False
	
	def get_safe_move_x_from_data(self, moves_data, data):
		move = None
		for key in moves_data:
			will_hit_another_snake = moves_data[key]['will_hit_another_snake']
			will_go_out_of_bounds = moves_data[key]['will_go_out_of_bounds']
			will_hit_self = moves_data[key]['will_hit_self']
			if not will_hit_another_snake and not will_go_out_of_bounds and not will_hit_self and \
					self.check_if_move_is_safe(data, key):
				move = key
				break
		# if there's no move that looks to be safe after checking with self.check_if_move_is_safe(data, key); then
		# for survival leaving it to its fate; LUCK :D
		if move is None:
			for key in moves_data:
				will_hit_another_snake = moves_data[key]['will_hit_another_snake']
				will_go_out_of_bounds = moves_data[key]['will_go_out_of_bounds']
				will_hit_self = moves_data[key]['will_hit_self']
				if not will_hit_another_snake and not will_go_out_of_bounds and not will_hit_self:
					move = key
					break
		return move
	
	def should_eat_food(self, data):
		if data['you']['health'] < 40:
			return True
		return False
	
	def get_distance_to_food(self, food_pos, head):
		return abs(food_pos['x'] - head['x']) + abs(food_pos['y'] - head['y'])
	
	def find_nearest_food(self, data):
		if len(data['board']['food']) == 0:
			return None
		
		nearest = data['board']['food'][0]
		min_distance = self.get_distance_to_food(data['board']['food'][0], data['you']['head'])
		for food in data['board']['food']:
			current_distance = self.get_distance_to_food(food, data['you']['head'])
			if min_distance > current_distance:
				nearest = food
				min_distance = current_distance
		return nearest
	
	def get_direction_to_eat(self, data, moves_data):
		nearest_food = self.find_nearest_food(data)
		if nearest_food is not None:
			print(f"there is food at: {nearest_food}")
			shouldGoUp = False
			shouldGoRight = False
			shouldGoLeft = False
			shouldGoDown = False
			if nearest_food['x'] > data['you']['head']['x']:
				# need to move right
				shouldGoRight = True
				print("1")
			elif nearest_food['x'] < data['you']['head']['x']:
				# need to move left
				shouldGoLeft = True
				print("2")
			if nearest_food['y'] > data['you']['head']['y']:
				# need to move up
				shouldGoUp = True
				print("3")
			elif nearest_food['y'] < data['you']['head']['y']:
				# need to move down
				shouldGoDown = True
				print("4")
			
			if shouldGoRight and self.can_go_in_direction(moves_data, data, "right"):
				return "right"
			elif shouldGoLeft and self.can_go_in_direction(moves_data, data, "left"):
				return "left"
			elif shouldGoUp and self.can_go_in_direction(moves_data, data, "up"):
				return "up"
			elif shouldGoDown and self.can_go_in_direction(moves_data, data, "down"):
				return "down"
		return None
	
	def can_go_in_direction(self, moves_data, data, key):
		can_go = False
		will_hit_another_snake = moves_data[key]['will_hit_another_snake']
		will_go_out_of_bounds = moves_data[key]['will_go_out_of_bounds']
		will_hit_self = moves_data[key]['will_hit_self']
		if not will_hit_another_snake and not will_go_out_of_bounds and not will_hit_self and \
				self.check_if_move_is_safe(data, key):
			can_go = True
		if not can_go:
			return not will_hit_another_snake and not will_go_out_of_bounds and not will_hit_self
		return can_go
	
	@cherrypy.expose
	@cherrypy.tools.json_in()
	@cherrypy.tools.json_out()
	def move(self):
		# This function is called on every turn of a game. It's how your snake decides where to move.
		# Valid moves are "up", "down", "left", or "right".
		# TODO: Use the information in cherrypy.request.json to decide your next move.
		data = cherrypy.request.json
		print("data is:****************")
		print(data)
		print("data is:****************")
		
		neighbours = self.get_neighbours(data)
		possible_moves = ["up", "down", "left", "right"]
		# random.shuffle(possible_moves)
		
		# moves_data stores data for all 4 directions with their values for will_hit_another_snake and
		# will_go_out_of_bounds
		moves_data = {
			"up": {}, "down": {}, "left": {}, "right": {}
		}
		for possible_move in possible_moves:
			will_go_out_of_bounds = self.will_go_out_of_bounds(data, possible_move)
			if not will_go_out_of_bounds:
				will_hit_self = self.will_collide_with_self(data, possible_move)
				will_hit_another_snake = self.will_hit_another_snake(
					data, possible_move, neighbours)
				moves_data[possible_move] = {
					'will_hit_another_snake': will_hit_another_snake,
					'will_hit_self': will_hit_self,
					'will_go_out_of_bounds': will_go_out_of_bounds
				}
			else:
				moves_data[possible_move] = {
					'will_hit_another_snake': True,
					'will_hit_self': True,
					'will_go_out_of_bounds': will_go_out_of_bounds
				}
		move = None
		# if self.should_eat_food(data):
		# 	move = self.get_direction_to_eat(data, moves_data)
		
		if move is None:
			move = self.get_safe_move_x_from_data(moves_data,
			                                      data)
		
		if move is None:
			print("************* making a random move ****************")
			move = random.choice(possible_moves)
		
		print(f"MOVE: {move}")
		return {"move": move}
	
	def check_if_move_is_safe(self, data, move):
		your_head_nxt_pos = copy.deepcopy(data['you']['head'])
		if move == "up":
			your_head_nxt_pos['y'] += 1
			possible_heads = [{'x': your_head_nxt_pos['x'] - 1, 'y': your_head_nxt_pos['y']},
			                  {'x': your_head_nxt_pos['x'] + 1, 'y': your_head_nxt_pos['y']},
			                  {'x': your_head_nxt_pos['x'], 'y': your_head_nxt_pos['y'] + 1}]
			for snake in data['board']['snakes']:
				if snake['id'] != data['you']['id'] and snake['head'] in possible_heads:
					return False
		if move == "down":
			your_head_nxt_pos['y'] -= 1
			possible_heads = [{'x': your_head_nxt_pos['x'] - 1, 'y': your_head_nxt_pos['y']},
			                  {'x': your_head_nxt_pos['x'], 'y': your_head_nxt_pos['y'] - 1},
			                  {'x': your_head_nxt_pos['x'] + 1, 'y': your_head_nxt_pos['y']}]
			for snake in data['board']['snakes']:
				if snake['id'] != data['you']['id'] and snake['head'] in possible_heads:
					return False
		if move == "left":
			your_head_nxt_pos['x'] -= 1
			possible_heads = [{'x': your_head_nxt_pos['x'] - 1, 'y': your_head_nxt_pos['y']},
			                  {'x': your_head_nxt_pos['x'], 'y': your_head_nxt_pos['y'] + 1},
			                  {'x': your_head_nxt_pos['x'], 'y': your_head_nxt_pos['y'] - 1}]
			for snake in data['board']['snakes']:
				if snake['id'] != data['you']['id'] and snake['head'] in possible_heads:
					return False
		if move == "right":
			your_head_nxt_pos['x'] += 1
			possible_heads = [{'x': your_head_nxt_pos['x'] + 1, 'y': your_head_nxt_pos['y']},
			                  {'x': your_head_nxt_pos['x'], 'y': your_head_nxt_pos['y'] + 1},
			                  {'x': your_head_nxt_pos['x'], 'y': your_head_nxt_pos['y'] - 1}]
			for snake in data['board']['snakes']:
				if snake['id'] != data['you']['id'] and snake['head'] in possible_heads:
					return False
		return True
	
	@cherrypy.expose
	@cherrypy.tools.json_in()
	def end(self):
		# This function is called when a game your snake was in ends.
		# It's purely for informational purposes, you don't have to make any decisions here.
		data = cherrypy.request.json
		
		print("END")
		return "ok"


if __name__ == "__main__":
	server = Battlesnake()
	cherrypy.config.update({"server.socket_host": "0.0.0.0"})
	cherrypy.config.update({
		"server.socket_port":
			int(os.environ.get("PORT", "8080")),
	})
	print("Starting Battlesnake Server...")
	cherrypy.quickstart(server)
