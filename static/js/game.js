function get_socket() {
  if( window.hasOwnProperty('game_socket') ) {
    if( window.game_socket.connected ) {
      return window.game_socket
    }
  }
  console.log('connecting to websocket');
  var socket = io.connect('//' + document.domain + ':' + location.port);
  // verify our websocket connection is established
  socket.on('connect', function() {
    window.game_socket = socket;
    console.log('Websocket connected!');
  });
  socket.on('state', function(msg) {
      console.log(msg);
    handle_state(msg);
  });
  return socket;
}

function sound(src) {
    this.sound = document.createElement("audio");
    this.sound.src = src;
    this.sound.setAttribute("preload", "auto");
    this.sound.setAttribute("controls", "none");
    this.sound.setAttribute('crossorigin', 'anonymous');
    this.sound.style.display = "none";
    document.body.appendChild(this.sound);
    this.play = function(){
        this.sound.play();
    }
    this.stop = function(){
        this.sound.pause();
    }
}

function get_llama_name() {
  var names = ['WWAMA', 'BBAMAMA', 'GUYAMA', 'BAHAMA', 'JJAMA', 'JUMANJI', 'SAMBA', 'SMEGMA', 'LLAMA'];
  return names[Math.floor(Math.random() * names.length)];
}

function game_setup(game_id, nickname) {
  window.game_id = game_id;
  get_socket();
  display_name_prompt(game_id, nickname);
  window.sounds = {
    'llama': new sound('/static/mp3/llama.mp3'),
    'bip': new sound('/static/mp3/bip.mp3'),
    'knock': new sound('/static/mp3/knock.mp3'),
    'pass': new sound('/static/mp3/pass.mp3'),
    'endround': new sound('/static/mp3/end-of-round.mp3'),
    'endgame': new sound('/static/mp3/end-of-game.mp3')
  };
}

function display_name_prompt(game_id, nickname) {
  var div = $('#thegame');
  console.log(div);
  div.empty();
  var form = $('<form>');
  var label = $('<label>Enter your name</label>');
  var name_input = $('<input type="text">');
  name_input.val(nickname);
  var button = $('<input type="submit">');
  button.val(get_llama_name());
  label.append(name_input);
  form.append(label);
  form.append(button);
  form.submit(function(e) {
    e.preventDefault();
    var name = name_input.val();
    enter_game(game_id, name);
    return false;
  });
  div.append(form);
  name_input.focus();
}

function enter_game(game_id, name)
{
  console.log('sending message');
  get_socket().emit('join_game', {'name': name, 'game_id': game_id}, function(error, message){
    console.log('join game emit callback');
    console.log(error);
    console.log(message);
  });
  var div = $('#thegame');
  div.empty();
  div.append($('<p>connecting to game...</p>'));
}

function handle_state(state)
{
  console.log('handle state');
  console.log(state);
  if( state['state'] == 'wait' ) {
    return handle_wait_state(state);
  }
  if( state['state'] == 'playing' ) {
    return handle_playing_state(state);
  }
  if( state['state'] == 'end' ) {
    return handle_game_end(state);
  }
}

function handle_wait_state(state)
{
  var div = $('#thegame');
  div.empty();
  div.append($('<p>waiting for game to begin; current players in lobby:</p>'));
  var ol = $('<ol>');
  $.each(state['players'], function(i, v) {
    var you = '';
    if( state['you'] == i ) { you = ' (you)'; } else {
      you = '<a href="#" onclick="kick(\'' + v['session_id'] + '\')">kick</a>';
    }
    ol.append($('<li>' + v['name'] + you + '</li>'));
  });
  div.append(ol);
  var button = $('<input type="submit" value="Start the game!">');
  button.click(function(e) {
    var game_id = window.game_id;
    get_socket().emit('start_game', {'game_id': game_id}, function(error, message){
      console.log('start game emit callback');
      console.log(error);
      console.log(message);
    });
  });
  div.append(button);
  window.sounds.knock.play();
}

function get_card(i)
{
  return $('<img src="/static/img/card_' + i + '.jpg" alt="' + i + '" class="card">');
}

function canplay(card, facecard)
{
  var ok = (card == facecard) || (((facecard+1) % 7) == card );
  console.log('card: ' + card + ' face: ' + facecard + ' ok? ' + ok);
  return ok;
}

function kick(player_sid)
{
  if( !confirm("Are you sure you want to force this user to pass?") ) {
    return;
  }
  get_socket().emit('kick_user', {'game_id': game_id, 'player_sid': player_sid}, function(error, message){
    console.log(error);
    console.log(message);
  });
}

function handle_playing_state(state)
{
  var game_id = window.game_id;
  var div = $('#thegame');
  div.empty();
  var tbl = $('<table>');
  tbl.append($('<tr><th>Player</th><th>Number of cards</th><th>Points</th><th>still in?</th><th>last action</th><th>kick</th></tr>'));
  $.each(state['players'], function(i, v) {
    var active = false;
    var last_action = v['last_action'];
    if( i == state['current_player'] ) {
      active = true;
      last_action = '* current move *';
    }

    tbl.append($('<tr><td>' + v['name'] + '</td><td>' + v['cards'] + '</td><td>' + v['points'] + '</td><td>' + v['still_in'] + '</td><td>' + last_action + '</td><td><a href="#" onclick="kick(\'' + v['session_id'] + '\')">skip</a></tr>'));
  });
  div.append(tbl);

  var tbltop = $('<div class="tabletop">');

  tbltop.append(get_card(state['face_card']));
  tbltop.append($('<p class="deck_size">Number of cards remaining: ' + state['deck_size'] + '</p>'));

  div.append(tbltop);

  var can_play = false;
  var cards_div = $('<div>');
  $.each(state['cards'], function(i, v) {
    var card = v;
    var img = $('<img src="/static/img/card_' + v + '.jpg" alt="' + v + '" class="card">');
    if( state['active'] == true && canplay(v, state['face_card'])) {
      can_play = true;
      img.hover(
        function() {
          $( this ).addClass( "hover" );
        }, function() {
          $( this ).removeClass( "hover" );
        }
      );
      img.click(function(img) {

        console.log(card)
        get_socket().emit('play_card', {'game_id': game_id, 'card': card}, function(error, message){
          console.log('start game emit callback');
          console.log(error);
          console.log(message);
        });

      });
    }
    cards_div.append(img);
  });

  console.log('is active?');
  console.log(state['active']);
  if( state['active'] == true ) {
    console.log('i am active!');
    var p = $('<p>');
    p.append($('<b>It\'s your turn!</b><br>'));
    if( can_play ) {
      p.append($('<span>pick a card below</span><i> or </i>'));
    } else {
      p.append($('<span>Your hand sucks </span>'));
    }
    if( state['can_draw'] ) {
    var draw_link = $('<a href="#">Draw a new card</a> ');
    draw_link.click(function(e) {

      get_socket().emit('draw_card', {'game_id': game_id}, function(error, message){
        console.log(error);
        console.log(message);
      });

    });
      p.append(draw_link);
      p.append($('<i> or </i>'));
    } else {
      p.append($('<b>no draws allowed since you\'re the last player in the round </b>'));
    }

    var pass_link = $('<a href="#">pass and sit out the rest of the round</a>');
    pass_link.click(function(e) {

      get_socket().emit('pass', {'game_id': game_id}, function(error, message){
        console.log(error);
        console.log(message);
      });

    });
    p.append(pass_link);

    div.append(p)
  }
  div.append(cards_div);

  var button = $('<input type="submit" value="reset the game">');
  button.click(function(e) {
    var game_id = window.game_id;
    if( confirm('You will reset the game for everyone; are you sure?') ) {
      get_socket().emit('reset_game', {'game_id': game_id}, function(error, message){
        console.log(error);
        console.log(message);
      });
    }
  });
  div.append(button);

  if( state['sound'] == 'llama' ) {
    window.sounds.llama.play();
  } else if( state['sound'] == 'end-of-round' ) {
    window.sounds.endround.play();
  } else if( state['sound'] == 'pass' ) {
    window.sounds.pass.play();
  } else if( state['sound'] == 'bip' ) {
    window.sounds.bip.play();
  }

}


function handle_game_end(state)
{
  var game_id = window.game_id;
  var div = $('#thegame');
  div.empty();

  div.append($('<h1>Game End!</h1>'));

  $.each(state['players'], function(i, v) {
  });

  var players = [];
  for( var i = 0; i < state['players'].length; i++ ) {
    players.push(i);
  }

  players = players.sort(function(x, y) {
    xp = state['players'][x]['points'];
    yp = state['players'][y]['points'];
    console.log(xp);
    console.log(yp);
    if (xp < yp) {
      return -1;
    }
    if (xp > yp) {
      return 1;
    }
    return 0;
  });
  console.log(players);

  div.append($('<p>' + state['players'][players[0]]['name'] + ' is the winner!!!</p>'));


  var tbl = $('<table>');
  tbl.append($('<tr><th>Player</th><th>Points</th></tr>'));
  $.each(players, function(i, v) {
    var player = state['players'][v];
    var active = '';
    var you = '';
    if( v == state['you'] ) {
      you = ' (you)';
    }
    tbl.append($('<tr><td>' + player['name'] + you + '</td><td>' + player['points'] + '</td></tr>'));
  });
  div.append(tbl);

  var button = $('<input type="submit" value="reset the game">');
  button.click(function(e) {
    var game_id = window.game_id;
    get_socket().emit('reset_game', {'game_id': game_id}, function(error, message){
      console.log(error);
      console.log(message);
    });
  });
  div.append(button);

  window.sounds.endgame.play();

}
