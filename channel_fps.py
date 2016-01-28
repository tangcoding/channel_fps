

"""
Channel First Person Shooter

"""

import datetime
import time
import logging
import os
import re
import json
import math
import random 
from copy import deepcopy

import webapp2
from google.appengine.api import channel
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext.webapp import template

class Scoreboard(ndb.Model):
  """save the game for login user"""
  score_info = ndb.JsonProperty()

class Game(ndb.Model):
  """All the data we store for a game"""
  create_time = ndb.IntegerProperty()
  user1 = ndb.StringProperty()
  user2 = ndb.StringProperty()
  game_data = ndb.JsonProperty()
  winner = ndb.StringProperty()
  user1_name = ndb.StringProperty()
  user2_name = ndb.StringProperty()
  user1_online = ndb.BooleanProperty()
  user2_online = ndb.BooleanProperty()
  player_num = ndb.IntegerProperty()
  game_type = ndb.StringProperty()

  @classmethod
  def _get_avail_gameid(self, game_type):
    q = Game.query( ndb.AND( Game.game_type == game_type, ndb.AND( Game.player_num == 2, ndb.OR(Game.user2 == '', Game.user2 == None) ) ) ).fetch(keys_only=True)
    db_data   =[]
    for result in q:
      db_data.append({'data_id':result.string_id()}) 

    return json.dumps(db_data)

  @classmethod
  def _clear_game(self):
    time_limit = int(time.time() - 86400)
    # time_limit = int(time.time() - 1200)
    game_keys = Game.query( Game.create_time < time_limit).fetch(keys_only=True)
    ndb.delete_multi(game_keys)
    return 

class GameUpdater():
  game = None

  def __init__(self, game):
    self.game = game

    if self.game.game_data == None:
      self.game.game_data = {"map":1, "change_map": 0}  #AI, ice cube, medicine and two player
      # self.game.game_data = {}

    self.map1 = {}
    self.map1['map'] = [ # 1  2  3  4  5  6  7  8  9
           [1, 1, 1, 1, 1, 1, 1, 1, 1, 1,], 
           [1, 1, 0, 0, 1, 0, 0, 1, 0, 1,], 
           [1, 1, 0, 0, 0, 0, 0, 1, 0, 1,], 
           [1, 0, 0, 1, 0, 2, 0, 0, 0, 1,], 
           [1, 0, 0, 2, 0, 0, 2, 0, 0, 1,], 
           [1, 1, 0, 0, 2, 1, 1, 1, 1, 1,], 
           [1, 0, 0, 0, 0, 2, 0, 0, 0, 1,], 
           [1, 0, 0, 1, 0, 0, 0, 1, 0, 1,], 
           [1, 1, 0, 0, 1, 0, 0, 1, 0, 1,], 
           [1, 1, 1, 1, 1, 1, 1, 1, 1, 1,],
           ]
    self.map1['goal'] = [810,800]
    # self.map1['goal'] = [-900,770]
    self.map1['player1_org'] = [-1020, 750]
    self.map1['player2_org'] = [-1060, 800]

    self.map2 = {}
    self.map2['map'] = [ # 1  2  3  4  5  6  7  8  9
           [1, 1, 1, 1, 1, 1, 1, 1, 1, 1,], 
           [1, 0, 0, 1, 1, 0, 0, 1, 0, 1,], 
           [1, 1, 0, 1, 0, 0, 0, 0, 0, 1,], 
           [1, 0, 0, 0, 0, 1, 1, 0, 0, 1,],
           [1, 0, 0, 2, 0, 1, 2, 1, 0, 1,], 
           [1, 1, 0, 0, 2, 0, 1, 0, 1, 1,], 
           [1, 0, 1, 0, 0, 0, 0, 0, 0, 1,], 
           [1, 0, 0, 0, 1, 1, 0, 0, 0, 1,], 
           [1, 1, 0, 0, 1, 1, 0, 1, 1, 1,], 
           [1, 1, 1, 1, 1, 1, 1, 1, 1, 1,], 
           ]
    self.map2['goal'] = [520,710]
    self.map2['player1_org'] = [-1020, 750]
    self.map2['player2_org'] = [-1060, 800]

    self.map3 = {}       
    self.map3['map'] = [ # 1  2  3  4  5  6  7  8  9
           [1, 1, 1, 1, 1, 1, 1, 1, 1, 1,], 
           [1, 0, 0, 0, 1, 0, 0, 1, 0, 1,], 
           [1, 1, 0, 0, 1, 0, 0, 0, 0, 1,], 
           [1, 0, 1, 0, 0, 0, 1, 1, 2, 1,], 
           [1, 0, 0, 0, 0, 1, 2, 0, 0, 1,], 
           [1, 1, 1, 0, 2, 0, 0, 0, 1, 1,], 
           [1, 0, 1, 0, 0, 0, 0, 0, 0, 1,], 
           [1, 0, 0, 0, 0, 1, 0, 1, 0, 1,], 
           [1, 1, 0, 0, 1, 1, 0, 1, 1, 1,], 
           [1, 1, 1, 1, 1, 1, 1, 1, 1, 1,], 
           ]
    self.map3['goal'] = [520,710]
    self.map3['player1_org'] = [-1020, 750]
    self.map3['player2_org'] = [-1060, 800]

    self.game_map = self.map1['map']
    self.mapW = len(self.game_map)
    self.mapH = len(self.game_map[0])
    self.UNITSIZE = 250
    self.NUMAI = 5

  def current_empty_sites(self):
    currentEmptySites=[]

    emptySitesMap = deepcopy(self.game_map)

    if(len(self.game.game_data ) > 0):
      for key in self.game.game_data:
        if  key != "map" and  key != "change_map" and key != "update_time":
          p = self.getMapSector(self.game.game_data[key]["x"],self.game.game_data [key]["z"])
          m = int(p['x']); n = int(p['z'])
          emptySitesMap[m][n] = 1

    for i in range(0, self.mapW):
      for j in range(0, len(self.game_map[i])):

        if emptySitesMap[i][j] == 0:
          currentEmptySites.append({"x": i , "z": j })

    return currentEmptySites

  # get the position in 2D map
  def getMapSector(self, vx, vz):
    x = math.floor((vx + self.UNITSIZE / 2.0) / self.UNITSIZE + self.mapW/2.0)
    z = math.floor((vz + self.UNITSIZE / 2.0) / self.UNITSIZE + self.mapW/2.0)
    return {"x": x, "z": z}

  # calculate distance between 2 points
  def distance(self, x1, z1, x2, z2):
    return math.sqrt((x1-x2)**2+(z1-z2)**2)

  def setup_cubes(self):
    # self.game.game_data  = {}
    self.game.winner = '';

    if self.game.game_data["map"] == 1:
      self.game_map = self.map1['map']
      p1 = self.map1['player1_org']
      p2 = self.map1['player2_org']
      self.game.game_data["goal"] = {"x":self.map1['goal'][0], "z":self.map1['goal'][1]}

    elif self.game.game_data["map"] == 2:
      self.game_map = self.map2['map']
      self.game.game_data["change_map"] = 1
      p1 = self.map2['player1_org']
      p2 = self.map2['player2_org']
      self.game.game_data["goal"] = {"x":self.map2['goal'][0], "z":self.map2['goal'][1]}

    else:
      self.game_map = self.map3['map']
      self.game.game_data["change_map"] = 1
      p1 = self.map3['player1_org']
      p2 = self.map3['player2_org']
      self.game.game_data["goal"] = {"x":self.map3['goal'][0], "z":self.map3['goal'][1]}

    # set player
    self.game.game_data["player1"] = {"x":p1[0], "z":p1[1], "score": 0, "health": 100, "powerbullets": 0, "org_x":p1[0], "org_z":p1[1]} 
    self.game.game_data["player2"] = {"x":p2[0], "z":p2[1], "score": 0, "health": 100, "powerbullets": 0, "org_x":p2[0], "org_z":p2[1]} 

    for i in range(self.NUMAI):
      name = "ai"+ str(i)
      self.create_cube(name, 500);
    
    self.create_cube("medicine",0)
    self.create_cube("ice",0)

    self.game.game_data["update_time"] = time.time()*1000

    return json.dumps(self.game.game_data)

  def create_cube(self, name, dist):
    availSites = self.current_empty_sites()
    n = random.randint(0, len(availSites)-1)

    x = math.floor(availSites[n]["x"]- self.mapW/2.0) * self.UNITSIZE
    z = math.floor(availSites[n]["z"] - self.mapW/2.0) * self.UNITSIZE

    while self.distance(x, z, self.game.game_data["player1"]["x"], self.game.game_data["player1"]["z"]) < dist:
        n = random.randint(0, len(availSites)-1)
        x = math.floor(availSites[n]["x"]- self.mapW/2.0) * self.UNITSIZE
        z = math.floor(availSites[n]["z"] - self.mapW/2.0) * self.UNITSIZE


    lastRandomX = random.uniform(0,1) * 2 - 1;
    lastRandomZ = random.uniform(0,1) * 2 - 1;

    self.game.game_data[name]= {"x":x, "z":z, "freezeStart": time.time()*1000-10000, "hideStart": time.time()*1000-5000, "lastRandomX": lastRandomX, "lastRandomZ": lastRandomZ}

  def get_game_message(self):

    gameUpdate = {
      'game_data': self.game.game_data,
      'user1': self.game.user1,
      'user2': '' if not self.game.user2 else self.game.user2,
      'user1_online': self.game.user1_online,
      'user2_online': self.game.user2_online,
      'winner': self.game.winner,
      'game_id':self.game.key.id(),
      'player_num': self.game.player_num,
      'game_type': self.game.game_type
    }
    return json.dumps(gameUpdate)

  def send_update(self, reciever):
    message = self.get_game_message()

    if reciever == "both":
      if self.game.user1_online:
        channel.send_message(self.game.user1 + self.game.key.id(), message)

      if self.game.user2 and self.game.user2_online:
        channel.send_message(self.game.user2 + self.game.key.id(), message)

    elif reciever == "player2":
      if self.game.user2 and self.game.user2_online:
        channel.send_message(self.game.user2 + self.game.key.id(), message)
    elif reciever == "player1":
      if self.game.user1_online:
        channel.send_message(self.game.user1 + self.game.key.id(), message)

  def send_start(self):
    message = "start"
    channel.send_message(self.game.user1 + self.game.key.id(), message)
    if self.game.user2:
      channel.send_message(self.game.user2 + self.game.key.id(), message)

  def send_offline_update(self, reciever):

    if reciever == "player1":
      if self.game.user1_online:
        message = 'offline_player2'
        channel.send_message(self.game.user1 + self.game.key.id(), message)

    elif reciever == "player2":
      if self.game.user2_online:
        message = 'offline_player2'
        channel.send_message(self.game.user2 + self.game.key.id(), message)
    else:
      pass

  def update_game(self, data_list):

    self.game.game_data = json.loads(self.game.game_data)
    player = data_list["player"] 
    self.game.game_data[player] = data_list[player]
    self.game.game_data["change_map"] = 0

    if self.game.game_data["update_time"] < data_list["update_time"]:

      # update medicine box and ice cube
      self.game.game_data["medicine"] = data_list["medicine"]
      self.game.game_data["ice"] = data_list["ice"]
      self.game.game_data["update_time"] = data_list["update_time"]

      # update ai
      for i in range(self.NUMAI):
        ai_name = "ai"+ str(i)
        self.game.game_data[ai_name] = data_list[ai_name]

    self.game.game_data = json.dumps(self.game.game_data)

    self.game.put()

    if player == "player1":
      self.send_update("player2")
    elif player == "player2":
      self.send_update("player1")

    return

  def update_map(self, data_list):
      self.game.game_data = json.loads(self.game.game_data)

      self.game.game_data["change_map"] = 1
      self.game.game_data["map"] = int(data_list)

      self.setup_cubes()
      self.game.game_data = json.dumps(self.game.game_data)
      self.game.put()

      self.send_update("both")

      return

  def update_winner(self, data_list):
    if self.game.winner == '':
      self.game.winner = data_list["player"]
      self.game.put()
      self.send_update("both")

      # - update scoreboard
     
      if(self.game.winner == "player1"):
        winner = self.game.user1_name
      else:
        winner = self.game.user2_name
      data_list["player"] = winner
      self.update_scoreboard(data_list)

      return

  def update_offline(self, player_id):
    if player_id== "player1":
      if  self.game.user2_online == False:
        self.game.key.delete()
        return

      self.game.user1_online = False
      self.game.put()
      self.send_update("player2")

    elif player_id== "player2":
      if  self.game.user1_online == False:
        self.game.key.delete()
        return

      self.game.user2_online = False
      self.game.put()
      self.send_update("player1")
    
    return

  def update_scoreboard(self, data_list):
      # - update scoreboard
      if self.game.game_type == "cf" and self.game.player_num == 2:
        scoreboard_name = "cf_2player"
      elif self.game.game_type == "cf" and self.game.player_num == 1:
        scoreboard_name = "cf_1player"
      elif self.game.game_type == "s3" and self.game.player_num == 2:
        scoreboard_name = "s3_2player"
      elif self.game.game_type == "s3" and self.game.player_num == 1:
        scoreboard_name = "s3_1player"
      print "scoreboard", scoreboard_name

      item = Scoreboard.get_by_id(scoreboard_name)

      if not item:
        item =  Scoreboard(id= scoreboard_name)
        item.score_info = [{"user": data_list["player"], "score": data_list["score"], "time": data_list["time"]}]
        item.score_info = json.dumps(item.score_info)
        item.put()
      else:  
        q = json.loads(item.score_info)

        if self.game.game_type == "cf":
          insert_idx = -1
          for idx in range(0, len(q)):
            if data_list["time"] < q[idx]["time"]:
              insert_idx = idx
              break

          if insert_idx == -1 and len(q) < 5:
            insert_idx = len(q)
            q.insert(insert_idx, {"user": data_list["player"], "score": data_list["score"], "time": data_list["time"]})
          elif insert_idx >= 0 and insert_idx <= 4:
            q.insert(insert_idx, {"user": data_list["player"], "score": data_list["score"], "time": data_list["time"]})
            if len(q) > 5:
              q = q[:5]

        elif self.game.game_type == "s3":
          insert_idx = -1
          for idx in range(0, len(q)):
            if data_list["score"] > q[idx]["score"]:
              insert_idx = idx
              break

          if insert_idx == -1 and len(q) < 5:
            insert_idx = len(q)
            q.insert(insert_idx, {"user": data_list["player"], "score": data_list["score"]})
          elif insert_idx >= 0 and insert_idx <= 4:
            q.insert(insert_idx, {"user": data_list["player"], "score": data_list["score"]})
            if len(q) > 5:
              q = q[:5]

        item.score_info = json.dumps(q)
        item.put()
      return

class GameFromRequest():
  game = None;

  def __init__(self, request):
    user = users.get_current_user()
    if not user:
      user =  os.environ["REMOTE_ADDR"]
    game_key = request.get('g')
    if user and game_key:
      self.game = Game.get_by_id(game_key)

  def get_game(self):
    return self.game

class UpdateGame(webapp2.RequestHandler):
  def post(self):
    game = GameFromRequest(self.request).get_game()
    if game.winner == '':
      user = users.get_current_user()
      if not user:
        user =  os.environ["REMOTE_ADDR"]
      if game and user:
        data_list = self.request.get('data')
        data_list = json.loads(data_list)
        GameUpdater(game).update_game(data_list)

class UpdateMap(webapp2.RequestHandler):
  def post(self):
    game = GameFromRequest(self.request).get_game()
    user = users.get_current_user()
    if not user:
      user =  os.environ["REMOTE_ADDR"]
    if game and user:
      data_list = self.request.get('data')
      data_list = json.loads(data_list)
      GameUpdater(game).update_map(data_list)

class UpdateWinner(webapp2.RequestHandler):
  def post(self):
    game = GameFromRequest(self.request).get_game()
    if game.winner == '':
      user = users.get_current_user()
      if not user:
        user =  os.environ["REMOTE_ADDR"]
      if game and user:
        data_list = self.request.get('data')
        data_list = json.loads(data_list)
        GameUpdater(game).update_winner(data_list)

class UpdateScore(webapp2.RequestHandler):
  # update score at the end of game
  def post(self):
    game = GameFromRequest(self.request).get_game()
    user = users.get_current_user()
    if not user:
      user =  os.environ["REMOTE_ADDR"]
    if game and user:
      data_list = self.request.get('data')
      data_list = json.loads(data_list)
      if data_list["player"] == "player1":
        data_list["player"] = game.user1_name
      elif data_list["player"] == "player2":
        data_list["player"] = game.user2_name
      GameUpdater(game).update_scoreboard(data_list)

class Get_CF2P_Scoreboard(webapp2.RequestHandler):
  def get(self):
    item = Scoreboard.get_by_id('cf_2player')
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(item.score_info)

class Get_CF1P_Scoreboard(webapp2.RequestHandler):
  def get(self):
    item = Scoreboard.get_by_id('cf_1player')
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(item.score_info)

class Get_S31P_Scoreboard(webapp2.RequestHandler):
  def get(self):
    item = Scoreboard.get_by_id('s3_1player')
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(item.score_info)

class Get_S32P_Scoreboard(webapp2.RequestHandler):
  def get(self):
    item = Scoreboard.get_by_id('s3_2player')
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(item.score_info)

class Get_Avail_GameID(webapp2.RequestHandler):
  def get(self):
    game_type = self.request.get('game_type')
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(Game._get_avail_gameid(game_type))

class ClearGame(webapp2.RequestHandler):
  def get(self):
    Game._clear_game()

class ChangeGameInfo(webapp2.RequestHandler):
  def post(self):
    game = GameFromRequest(self.request).get_game()
    data_list = self.request.get('data')
    if data_list == '2':
      game.player_num = 2
    elif data_list == 's3':
      game.game_type = 's3'
    elif data_list == 'cf':
      game.game_type = 'cf'
    elif data_list == 'em':
      game.game_type = 'em'
    game.put()
    GameUpdater(game).send_update("both")

class StartGame(webapp2.RequestHandler):
  def post(self):
    game = GameFromRequest(self.request).get_game()
    if game:
      GameUpdater(game).send_start()

class ClosedPage(webapp2.RequestHandler):
  def post(self):
    game = GameFromRequest(self.request).get_game()
    user = users.get_current_user()
    if not user:
      user =  os.environ["REMOTE_ADDR"]
    if game and user:
      data_list = self.request.get('data')
      GameUpdater(game).update_offline(data_list)

class OpenedPage(webapp2.RequestHandler):
  def post(self):
    game = GameFromRequest(self.request).get_game()
    GameUpdater(game).send_update("both")

class MainPage(webapp2.RequestHandler):
  """The main UI page, renders the 'index.html' template."""

  def get(self):
    """Renders the main page. When this page is shown, we create a new
    channel to push asynchronous updates to the client."""


    # - get user
    user = users.get_current_user()
    if user:
        login_key = users.create_logout_url(self.request.uri)
        gate =  'Logout'
        user_name = user.nickname()
    else: # - logged out
      login_key = users.create_login_url(self.request.uri)
      gate = 'Sign in'
      user_name = ''

    current_user = None

    # - get game key
    game = None
    user_game = None
    game_key = self.request.get('g')
    player_num = self.request.get('player_num')
    game_type = self.request.get('game_type')

    if player_num: 
      player_num = int(player_num)
    else: 
      player_num = 1

    if not game_type:
      game_type = "em"

    if not game_key:
      game_key = str(int(time.time())) + str(random.randint(10,99)) #generate new game key

      # set player1 name
      if user:
        current_user = user.user_id()
        user1_name = user.nickname()
      else:
        current_user = os.environ["REMOTE_ADDR"]
        user1_name = "Anonymous"

      #generate game data
      game = Game(id = game_key, user1 = current_user, user1_name = user1_name, user1_online = True, user2_online = False, game_type = game_type, create_time = int(time.time()))  

      game.player_num = player_num     
      game.game_data = GameUpdater(game).setup_cubes()

      game.put()

    else:
      game = Game.get_by_id(game_key)
      if not game:
        self.redirect('/')
        return

      if not game.user2:
        # set player2 name
        if user:
          current_user = user.user_id()
          user2_name = user.nickname()
        else:
          user2_name = "Anonymous"
          current_user = os.environ["REMOTE_ADDR"]
          if  current_user== game.user1:
            current_user += '2' 

        game.user2 = current_user
        game.user2_online = True
        game.user2_name = user2_name
        game.put()

      else:
        if user:
          current_user = user.user_id()
        else:
          current_user = os.environ["REMOTE_ADDR"]

        if current_user == game.user1:
          game.user1_online = True
        elif current_user == game.user2:
          game.user2_online = True
        else:
          self.redirect('/')

    # game_link = 'http://firstpersonshooter-1138.appspot.com/?g=' + game_key
    # game_link = 'localhost:10080/?g=' + game_key
    game_link =  game_key

    if game:
      token = channel.create_channel(current_user + game_key)
      template_values = {
                         'login_key': login_key,
                         'gate': gate,
                         'user_name': user_name,
                         'token': token,
                         'me': current_user,
                         'game_key': game_key,
                         'game_link': game_link,
                         'initial_message': GameUpdater(game).get_game_message(),
                        }
      path = os.path.join(os.path.dirname(__file__), 'index.html')
      self.response.out.write(template.render(path, template_values))
    else:
      self.redirect('/')

#-------------------------------------------------------------#
#                                                             #
#-------------------------------------------------------------#   

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/opened', OpenedPage), 
    ('/closed', ClosedPage), 
    # ('/_ah/channel/disconnected/', ClosedPage), 
    ('/start_game', StartGame), 
    ('/update_map', UpdateMap),
    ('/update_game', UpdateGame),
    ('/update_winner', UpdateWinner),
    ('/change_game_info', ChangeGameInfo),   
    ('/update_score', UpdateScore),
    ('/get_cf_2p_scoreboard', Get_CF2P_Scoreboard),
    ('/get_cf_1p_scoreboard', Get_CF1P_Scoreboard),
    ('/get_s3_1p_scoreboard', Get_S31P_Scoreboard),
    ('/get_s3_2p_scoreboard', Get_S32P_Scoreboard),
    ('/get_avail_gameid/?', Get_Avail_GameID),
    ('/clear_game/?', ClearGame),
    ],
    debug=True)



