# Functional requirements 
(in addition to the requirements defined in the homework handout)

## channels
* the size of a channel is not limited
* there can be multiple channels
* a channel can be created by a single user
* each user in a channel can add new users to that channel

## general usage
* upon starting the application, user must supply username and password (to private key)
* if password is correct list of channels (that the user is part of) is displayed
* user can go back to main menu from any sub-menu
* user can create new channel or select existing one to enter
	* if new channel option is selected:
		* prompt for channel name
	* if existing channel is selected:
		* message history is displayed
		* new messages can be sent
		* new users can be added

# Attacker model

## Goals of the attacker 

### Including server
* recover private key of some other participant
* recover symmetric key of a channel she is not part of
* add a user in a channel that the attacker is not part of
* read or send messages in channels she is not part of
* replay or modify messages
* send, messages in the name of someone else

### Not including the server
* remove users in a channel that the attacker is not part of

## Capabilities
* the attacker knows the public key of every user (as do every user)
* the attacker can be a user invited to a number of channels (in this case we want to protect channels that she is not part of, and the source of the messages)
* the attacker has man-in-the-middle positions in every link and can view, modify and delay (for an indefinite period of time) messages
* the attacker can view all data that is available to the server

# Security requirements

## Attacker that isn't part of any channel
* can't view, modify or send messages 
* can't invite users to channels that the attacker isn't part of

## Attacker that is part of some channels
* can't view, modify or send messages in channels she isn't part of
* can only send messages in her own name in the channels she is part of
* can't invite users to channels that the attacker isn't part of

# System architecture

There are two types of entities in our system: server and user. The users communicate with each other through the server. Users can communicate with each other via channels: when a user sends a message to a channel, each user that is part of that channel will receive that message. Any user can create new channels, and each user that is part of the channel, can add new users to that channel.

## Server

Each time a client wants to send a message, it is sent to the server. The servers main message handler determines the type of message is, and acts accordingly: after performing some basic checks, broadcasting the message to all parties that need to receive it (i.e. the users that are part of the channel in question), and making a persistent copy of it, so offline users can later receive it.

## User

A user is identified by a unique user ID. Every user has signing and an encryption key, and the public parts of these keys are pre-shared with each user, so it is known to each participant what user IDs belong to what public keys. Messages received by the user are stored locally. The private keys of the user are stored in persistent storage, encrypted with a secret password, the user has to provide this password when she starts the client.

## Channel

A channel is identified by its channel ID. A channel holds the following information: the IDs of users that are part of the channel, for each user, the channel key, encrypted with her public encryption key, and the messages that have been sent in the channel, encrypted with the channel key.

# Cryptographic protocols

## Message types

### Add user to channel

```
|| userID(B) || channelID(C) || E(pkEnc(userID(B)), channel-key) || S(pkSig(userID(A)), eddigiek) || 
```

* This message is used for creating a new channel or adding a new member to it.
* The above message is user `A` adding user `B` to `C` channel.
* The channel-key is encrypted with the public key of user `B`, this way sharing it with her and only her.
* The whole message is signed by user `A`, proving that the message is originating from a user that is part of channel `C`.
* If `A` == `B`, and `C` doesn't exist yet, this is the creation of a new channel
	* if `C` already exists, this message is ignored
* This message is also ignored if `A` is not part of channel `C`, or if the signature is invalid.
* This message is broadcasted (by the server) to all users in channel `C`, including the new user `B`.

### Communication message

```
E(GCMmode, channel-key, channelID(C), userID(from) || ChanSeqNum || messageText || S(pkSig(userID(from)), eddigiek))
                     (associated data)                           (encrypted data)
```

* This message is encrypted with the channel-key, in GCM mode, with channeldID being the associated data so the server can determine the channel. The rest of the data is encrypted. Both the encrypted data and associated data are signed with the senders signing key, so the sender cannot be impersonated. 
* This message is used for sending a text message to channel `C`, the senders id being `from`.
* The server broadcasts this message to all channel `C` participants.
* Recipients check the following, and only accepts the message if all checks are successful:
	* user `from` is part of the channel `C` 
	* the `ChanSeqNum` is higher than all previous values in this channel 
	* all MACs and signatures are valid

