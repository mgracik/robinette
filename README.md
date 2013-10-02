robinette
=========

robinette is a simple IRC bot composed of two main components, client and server.

The Client
----------

Client uses the twisted library. It's a thin client, which just receives and sends messages from and to the IRC server.
Upon receiving an IRC message, it sends a request to the backend, and sends it's response back to IRC (if any).

The Server (backend)
--------------------

Server is an asynchronous XML-RPC service which does all the work. It processes the IRC message sent from the client
and based on it's context creates a response, which is sent back to the client. It also logs all the events and messages
to a MongoDB database.

This client/server architecture allows us to add new features/commands to the bot without having to restart and disconnect
the client from the IRC server, because all new features just need to be added to the server, and the client can then
use them instantialy.

Implemented functionality (available commands)
----------------------------------------------

* Seen - `!seen <nick>` (returns the last time `nick` was seen)
* Backlog - `!backlog`

  Backlog returns a list of messages with timestamps less than the last user login time. This allows to user to see
  messages that were sent to the channel when he was logged out. Backlog returns the last 10 messages, if the user 
  needs older messages, he can issue another `!backlog` command, fetching another 10 messages from the buffer. The buffer
  duration is set to 10 minutes, then it gets reset, and another !backlog command returns the last 10 messages again.

* Stock quotes - `!quote <symbol>` (returns the realtime bid and ask stock prices for `symbol`)
* Youtube - parses a youtube link, if it appears in the message, and sends a message with the title of the video
* Chat - a simple markov chain chatbot responds to messages addressed to the bot
