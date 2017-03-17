import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.wsgi
from uuid import uuid4
import json

from tornado.options import define, options, parse_command_line

define("port", default=9000, help="run on the given port", type=int)
define("ip", default="192.168.0.11", help="IP Address to listen on.", type=str)

#WebSocketRoomsHandler
class ClientHandler(object):
    def __init__(self):
        self.clients_info = {}  # for each client id we'll store  {'wsconn': wsconn, 'nick':nick, 'roomId' : room_Id}
        self.rooms_info = {}  # dict to store room info{'roomId' : roomId, "roomName": roomName 'maxCapacity': cap 'clients' : clietsDict}

    def add_room(self, name, max_cap):
        room_id = str(uuid4())
        if max_cap > 10:
            max_cap = 10
        self.rooms_info[room_id] = {"roomId": room_id, "roomName": name, "maxCapacity": max_cap, "clients": {}}

    def show_all_rooms(self):
        for room in self.rooms_info:
            print room

    def join_to_room(self, nick, room_id, wsclient):
        self.clients_info[wsclient] = {'wsclient': wsclient, 'nick': nick, 'roomId': room_id}
        self.rooms_info[room_id]["clients"][wsclient] = self.clients_info[wsclient]
        self.send_message_to_roommates('joined room', wsclient)

    def leave_room(self, wsclient):
        if self.clients_info.has_key(wsclient):
            msg = {'type': 'text', 'nick': self.clients_info[wsclient]['nick'], 'text': 'left room'}
            msg_json = json.dumps(msg)
            room = self.rooms_info[self.clients_info[wsclient]['roomId']]
            room['clients'].pop(wsclient, None)
            self.rooms_info.pop(wsclient, None)
            for mate in room['clients']:
                mate.write_message(msg_json)
            print 'left'

    def send_message_to_roommates(self, message, wsclient):
        msg = {'type': 'text', 'nick' : self.clients_info[wsclient]['nick'], 'text' : message}
        msg_json = json.dumps(msg)
        for mate in self.rooms_info[self.clients_info[wsclient]['roomId']]['clients']:
            mate.write_message(msg_json)

    def check_room_in_room(self, roomID):
        return len(self.rooms_info[roomID]['clients']) < self.rooms_info[roomID]['maxCapacity']



#Httphandlers
class RoomHandler(tornado.web.RequestHandler):
    def initialize(self, room_handler):
        self._room_handler = room_handler
    @tornado.web.asynchronous
    def get(self):
        data = []
        for room in self._room_handler.rooms_info:
            data.append({"roomId": self._room_handler.rooms_info[room]['roomId'], "roomName": self._room_handler.rooms_info[room]['roomName'],  "maxCapacity": self._room_handler.rooms_info[room]['maxCapacity'], "clients": len(self._room_handler.rooms_info[room]['clients'])})
        self.write(json.dumps(data))
        self.finish()
    def post(self, *args, **kwargs):

            room_name = self.get_argument("roomName")
            room_cap = self.get_argument("maxCapacity")
            self._room_handler.add_room(room_name, room_cap)
            self.write("done")



class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def initialize(self, room_handler):
        """Store a reference to the "external" RoomHandler instance"""
        self._room_handler = room_handler

    def open(self, *args):
        self.stream.set_nodelay(True)

    def on_message(self, message):
        msg = json.loads(message)
        if msg['type'] == 'join':
            if self._room_handler.check_room_in_room(msg['roomId']):
                self._room_handler.join_to_room(msg['nick'], msg['roomId'], self)
            else :
                msg = {'type': 'noSpace'}
                msg_json = json.dumps(msg)
                self.write_message(msg_json)
        elif msg['type'] == 'text':
            self._room_handler.send_message_to_roommates(msg['text'], self)

    def on_close(self):
        pass

    def on_connection_close(self):
        self._room_handler.leave_room(self)
        super(WebSocketHandler, self).on_connection_close()

import os

if __name__ == '__main__':
    '''
    #Connected and working with django, commented just for heroku deployment test and because it's not needed now
    from django.core.wsgi import get_wsgi_application
    from tornado.wsgi import WSGIContainer
    parse_command_line()
    os.environ['DJANGO_SETTINGS_MODULE'] = 'AppAgainstCards_Server.settings'
    application = get_wsgi_application()
    container = WSGIContainer(application) without django test
    '''
    client_handler = ClientHandler()
    client_handler.add_room("Room1", 10)
    client_handler.add_room("Room2", 1)
    app = tornado.web.Application([
        (r'/', WebSocketHandler, {'room_handler':  client_handler}),
        (r'/Rooms', RoomHandler, {'room_handler':  client_handler}),
        #(r'/', container)
    ])
    #app.listen((os.environ.get("PORT", 5000)))
    app.listen(9000, "192.168.0.11")
    tornado.ioloop.IOLoop.instance().start()