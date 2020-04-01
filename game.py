# each player has 6 cards
# deck is 8 copies of cards 1-6 and llamas

import random
import json
import copy

from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('templates'))


class player(object):
    def __init__(self, session_id, name, sock_id):
        self.session_id = session_id
        self.name = name
        self.sock_id = sock_id
        self.cards = []
        self.face_card = None
        self.points = 0
        self.active = True
        self.last_action = ''

def get_deck():
    cards = []
    for i in range(0, 7):
        for _ in range(8):
            cards.append(i)
    random.shuffle(cards)
    return cards

def get_card_name(card_num):
    if card_num == 6:
        return 'llama'
    return str(card_num+1)

class game(object):
    def __init__(self):
        self.players = []
        self.state = 'wait'
        self.current_player = None

    def join(self, session_id, player_name, sock_id):
        for x in self.players:
            if x.session_id == session_id:
                print('updating existing player with new sock and name')
                x.sock_id = sock_id
                x.name = player_name
                return
        if self.state != 'wait':
            print('got a request to join a pre-started game')
            return
        x = player(session_id, player_name, sock_id)
        self.players.append(x)
        return

    def draw_card(self):
        return self.draw_cards(1)[0]

    def draw_cards(self, n):
        cards = self.deck[:n]
        assert(len(cards) == n)
        self.deck = self.deck[n:]
        return cards

    def start(self):
        if self.state != 'wait':
            print('got start game for game that is not in wait state')
            return
        self.state = 'playing'
        self._setup_round()

    def reset(self):
        self.state = 'wait'
        for x in self.players:
            x.points = 0
        self._setup_round()

    def _setup_round(self):
        self.deck = get_deck()
        for x in self.players:
            x.cards = self.draw_cards(8)
            x.active = True
            x.last_action = ''
        self.current_player = random.randint(0, len(self.players)-1)
        self.face_card = self.draw_card()
        self.can_draw = True
        self.play_sound = ''

    def advance_player(self):
        num_active = sum(int(x.active) for x in self.players)
        if num_active == 0:
            return self.handle_round_end()
        if num_active == 1:
            self.can_draw = False

        last_player = self.current_player
        while 1:
            self.current_player = (self.current_player + 1) % len(self.players)
            if self.players[self.current_player].active:
                break

    def get_points(self, cards):
        points = 0
        for card in set(cards):
            if card == 6:
                points += 10
            else:
                points += card+1
        return points

    def handle_round_end(self):
        game_end = False
        for x in self.players:
            points = self.get_points(x.cards)
            if points == 0:
                if x.points >= 10:
                    x.points -= 10
                else:
                    x.points -= 1
            else:
                x.points += points
                if x.points >= 40:
                    game_end = True

        if game_end:
            print('end of game')
            self.state = 'end'
            self.play_sound = 'end-of-game'
        else:
            print('end of round')
            self._setup_round()
            self.play_sound = 'end-of-round'


    def _get_player(self, session_id):
        for i, x in enumerate(self.players):
            if x.session_id == session_id:
                return x, i == self.current_player
        raise KeyError(session_id)

    def handle_draw_card(self, session_id):
        player, is_active = self._get_player(session_id)
        if not is_active:
            print('got action for non-active player; ignoring!')
            return
        player.cards.append(self.draw_card())
        player.last_action = 'drew a card';
        self.play_sound = ''
        self.advance_player()

    def _can_play(self, card):
        return card == self.face_card or card == ((self.face_card+1) % 7)

    def handle_play_card(self, session_id, card):
        player, is_active = self._get_player(session_id)
        if not is_active:
            print('got action for non-active player; ignoring!')
            return
        if not self._can_play(card):
            print('got an illegal move; ignoring!')
            return
        print(f'removing {card}')
        player.cards.remove(card)
        if not player.cards:
            self.handle_round_end()
            return
        self.face_card = card
        player.last_action = 'played a ' + get_card_name(card)
        if card == 6:
            self.play_sound = 'llama'
        else:
            self.play_sound = 'bip'
        self.advance_player()

    def handle_pass(self, session_id):
        player, is_active = self._get_player(session_id)
        if not is_active:
            print('got action for non-active player; ignoring!')
            return
        player.active = False;
        player.last_action = 'passed'
        self.play_sound = 'pass'
        self.advance_player()

    def kick_user(self, session_id):
        print(f'kicking {session_id}')
        if self.state == 'wait':
            self.players = [x for x in self.players if x.session_id != session_id]
        else:
            player, is_active = self._get_player(session_id)
            player.last_action = 'kicked'
            player.active = False
            if is_active:
                self.advance_player()


    def send_state(self):
        if self.state == 'wait':
            state = {
                'state': 'wait',
                'players': [
                    {
                        'name': x.name,
                        'session_id': x.session_id,
                        }
                    for x in self.players
                    ],
                }
            for i, x in enumerate(self.players):
                print(f'sending state to {x.sock_id}')
                state['you'] = i
                emit('state', state, room=x.sock_id)
            return

        if self.state == 'playing':
            pub_state = {
                'state': 'playing',
                'players': [
                    {
                        'name': x.name,
                        'cards': len(x.cards),
                        'points': x.points,
                        'still_in': x.active,
                        'last_action': x.last_action,
                        'session_id': x.session_id,
                        }
                    for x in self.players
                    ],
                'current_player': self.current_player,
                'face_card': self.face_card,
                'deck_size': len(self.deck),
                'can_draw': self.can_draw,
                'sound': self.play_sound,
                }
            for i, x in enumerate(self.players):
                state = copy.deepcopy(pub_state)
                state['active'] = bool(i == self.current_player)
                state['cards'] = x.cards
                state['you'] = i
                print(state)
                print(f'sending state to {x.sock_id}')
                emit('state', state, room=x.sock_id)
            return

        if self.state == 'end':
            state = {
                'state': 'end',
                'players': [
                    {'name': x.name, 'points': x.points}
                    for x in self.players
                    ],
                }
            for i, x in enumerate(self.players):
                state['you'] = i
                emit('state', state, room=x.sock_id)
            return

        assert 0, f'unhandled state: {self.state}'

nicknames = {}
def get_nickname(session_id):
    return nicknames.get(session_id, '')

def store_nickname(session_id, nick):
    nicknames[session_id] = nick

games = {}
def get_or_create_game(game_id):
    if game_id not in games:
        g = game()
        games[game_id] = g
    else:
        g = games[game_id]
    return g

from flask import Flask, request, make_response
from flask_socketio import SocketIO, send, emit
from functools import wraps
import uuid

def set_session_cookie(f):
    @wraps(f)
    def decorated_function(*args, **kws):
        #your code here
        sid = request.cookies.get('sid', str(uuid.uuid4()))
        kws['sid'] = sid
        resp = f(*args, **kws)
        if isinstance(resp, str):
            resp = make_response(resp)
        if 'sid' not in request.cookies:
            resp.set_cookie('sid', sid)
        return resp
    return decorated_function

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

def encode_string_singlequote(s):
    return '\'' + s.replace('\'', '\\\'') + '\'';

@app.route('/')
@set_session_cookie
def index(sid):
    print(f'sid: {sid}')
    return env.get_template('index.html').render()

@app.route('/game/<game_id>')
@set_session_cookie
def hello_world(game_id, sid):
    print(f'sid: {sid}')
    nick = get_nickname(sid)
    return env.get_template('game.html').render(
            game_id=game_id,
            nick=encode_string_singlequote(nick),
            )

@app.route('/static/<path:path>')
def serve_static_content(path):
    return flask.send_from_directory('static', path)

@socketio.on('connect')
def handle_connect():
    sid = request.cookies['sid']
    if not sid:
        print('no sid')
        return
    addr = request.environ['REMOTE_ADDR']
    port = request.environ['REMOTE_PORT']
    sock_id = request.sid
    print(f'received connect event: {addr}:{port} sid={sid} sock_id={sock_id}')

# TODO this isn't getting called
@socketio.on('disconnect')
def handle_disconnect():
    print('disconnect')
    print(request.sid)
    sid = request.cookies['sid']
    print(sid)

@socketio.on('join_game')
def handle_json(e):
    sid = request.cookies['sid']
    if not sid:
        print('no sid')
        return

    addr = request.environ['REMOTE_ADDR']
    port = request.environ['REMOTE_PORT']
    sock_id = request.sid
    print(f'received join_game event: {addr}:{port} sid={sid} sock_id={sock_id}')

    g = get_or_create_game(e['game_id'])
    store_nickname(sid, e['name'])
    g.join(sid, e['name'], request.sid)
    g.send_state()

@socketio.on('start_game')
def handle_start_game(e):
    sid = request.cookies['sid']
    if not sid:
        print('no sid')
        return

    addr = request.environ['REMOTE_ADDR']
    port = request.environ['REMOTE_PORT']
    sock_id = request.sid
    print(f'received start_game event: {addr}:{port} sid={sid} sock_id={sock_id}')

    g = get_or_create_game(e['game_id'])
    g.start();
    g.send_state()

@socketio.on('draw_card')
def handle_start_game(e):
    sid = request.cookies['sid']
    if not sid:
        print('no sid')
        return

    g = get_or_create_game(e['game_id'])
    g.handle_draw_card(sid)
    g.send_state()

@socketio.on('play_card')
def handle_start_game(e):
    sid = request.cookies['sid']
    if not sid:
        print('no sid')
        return

    g = get_or_create_game(e['game_id'])
    g.handle_play_card(sid, e['card'])
    g.send_state()

@socketio.on('pass')
def handle_start_game(e):
    sid = request.cookies['sid']
    if not sid:
        print('no sid')
        return

    g = get_or_create_game(e['game_id'])
    g.handle_pass(sid)
    g.send_state()

@socketio.on('kick_user')
def handle_kick_user(e):
    sid = request.cookies['sid']
    if not sid:
        print('no sid')
        return

    addr = request.environ['REMOTE_ADDR']
    port = request.environ['REMOTE_PORT']
    sock_id = request.sid
    print(f'received start_game event: {addr}:{port} sid={sid} sock_id={sock_id}')

    g = get_or_create_game(e['game_id'])
    g.kick_user(e['player_sid']);
    g.send_state()

@socketio.on('reset_game')
def handle_start_game(e):
    sid = request.cookies['sid']
    if not sid:
        print('no sid')
        return

    addr = request.environ['REMOTE_ADDR']
    port = request.environ['REMOTE_PORT']
    sock_id = request.sid
    print(f'received start_game event: {addr}:{port} sid={sid} sock_id={sock_id}')

    g = get_or_create_game(e['game_id'])
    g.reset();
    g.send_state()

def get_host():
    import netifaces
    for interface in ('eth0','wlp2s0'):
        try:
            return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
        except:
            pass
    return '127.0.0.1'

if __name__ == '__main__':
    host = get_host()
    print(host)
    debug = host.startswith('192.')
    socketio.run(app, debug=debug, host=host, port=5001)

#g = game()
#g.join('alex')
#g.join('lindsay')
#g.start()
#
#
#while 1:
#    state = g.get_state()
#    print(state)
#    break
