### Protocole

## requêtes

# Pour se connecter:
LOGIN "pseudo" -> envoye au serveur pour la conection

DISPLAY_ROOM "room1" "room2" "room3" -> reponse du serveur si LOGIN OK, va permettre d'envoyé au client les différentes room pour que l'appli côté client puisse lui permettre de choisir sa room
KO -> reponse du serveur si LOGIN NOK

# Pour rejoindre une room
exemple pour rejondre room1
JOIN_ROOM "room1" -> demande coté client pour le serveur afin de rejoindre la room 1

OK -> reponse du serveur qui va dire au client que le user à bien rejoint la room
KO -> reponse du serveur si impossible de rentrer dans la room 

# Pour envoyer un message dans une room
exemple pour envoyé un message dans la room 1
MSG "room1" "pseudo" "msg" -> demande coté client pour le serveur afin d'envoyer un message dans la room 1

OK -> reponse côté serveur pour dire que le message a bien été envoyé
KO -> reponse du serveur si impossible d'envoyer un message'

# Pour envoyer un fichier dans une room
exemple pour envoyé un fichier dans la room1
FILE "room1" "pseudo" "file" ->demande coté client pour le serveur afin d'envoyer un fichier dans la room 1



# Pour se deconnecter 
exemple pour se déconnecter de la room 1
BYE "room" "pseudo" -> demande coté client pour se déconnecter de la room 1

OK -> reponse côté serveur pour dire que le user à bien été déconnecté


