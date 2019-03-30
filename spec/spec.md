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
