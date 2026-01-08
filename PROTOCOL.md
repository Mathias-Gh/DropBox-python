# Protocol notes — Stories 6 / 7 / 12

Ce document résume les changements et recommandations pour implémenter :
- Story 6 : messages déclenchant un état intermédiaire (bloquant l'émetteur)
- Story 7 : préfixer chaque message avec la taille des données (int 32 bits)
- Story 12 : initiation P2P entre deux clients par le serveur

Contrainte importante : ne pas modifier le code déjà en place, respecter le protocole existant.

1) Encapsulation des messages (Story 7)
--------------------------------------
- Tous les messages transportés sur la socket doivent être encodés comme :

  [4 bytes length][payload bytes]

  - `length` : uint32 (4 octets) réseau (big-endian, `!I` en Python `struct`) indiquant la taille en octets du `payload` qui suit. Cette longueur concerne uniquement les données après ces 4 octets.
  - `payload` : octets — par convention on utilisera JSON UTF-8 (p.ex. un objet `{ "type": "MSG", "data": ... }`) ou un format binaire si nécessaire.

Pourquoi : facilite la lecture côté destinataire (on sait combien d'octets lire pour obtenir tout le message).

Exemple JSON payload minimal :

```json
{
  "type": "SEND_FILE",
  "seq": 42,
  "room": "room-1",
  "meta": { "filename": "doc.pdf", "size": 12345 },
  "data": "...base64..."
}
```

2) Etats intermédiaires et séquences (Story 6)
--------------------------------------------
Objectif : certains messages déclenchent une "séquence" / état intermédiaire. Tant que la séquence est active, l'émetteur est considéré bloqué pour cette action.

Principes :
- Chaque séquence possède un identifiant `seq` unique (32-bit ou string UUID). Le message initiateur inclut `seq`.
- Le destinataire (ou le serveur) peut renvoyer des réponses liées à `seq` : `ACK`, `VOTE`, `CONFIRM`, `COMPLETE`, `ERROR`.
- L'émetteur attend la résolution (p.ex. `COMPLETE` ou `ERROR`) avant de considérer la séquence terminée. L'attente peut être bloquante ou asynchrone selon l'implémentation client.

Exemple de séquence (vote) :

1. Client A envoie `BEGIN_SEQUENCE` -> payload: `{ "type": "BEGIN_SEQUENCE", "seq": 101, "action": "VOTE", "room": "r1", "details": {...}}`
2. Le serveur diffuse aux participants `VOTE_REQUEST` (avec `seq`)
3. Les autres clients renvoient `VOTE` (oui/non) avec `seq`
4. Serveur envoie `SEQUENCE_RESULT` (ou `COMPLETE`) à l'émetteur A
5. A reçoit `COMPLETE` -> sequence 101 terminée, débloquer l'émetteur

Blocage côté émetteur :
- Soit bloquer le thread/app qui a envoyé `BEGIN_SEQUENCE` jusqu'à réception de `COMPLETE` (approche simple),
- soit retourner un handle/promise au code appelant et poursuivre en asynchrone.

Timeouts et erreurs :
- Toujours prévoir timeout et gestion d'erreur si `COMPLETE` ne survient pas.

3) P2P initiation (Story 12)
----------------------------
But : le serveur peut initier une connexion P2P entre A et B. Après l'échange initial, A et B communiquent directement.

Séquence recommandée :

1. A demande une communication P2P vers B (via le serveur) ou le serveur décide d'initier.
2. Le serveur récupère les adresses/ports publiques connues d'A et B (ip:port) et envoie à A et B un message `P2P_INVITE` contenant l'IP/port de l'autre :
   - `{ "type": "P2P_INVITE", "peer": {"ip": "x.x.x.x", "port": 12345}, "role": "caller" }`
3. A et B essaient d'établir une connexion TCP directe l'un vers l'autre. Selon la topologie NAT, il faudra peut-être faire du UDP hole-punching ou fallback via serveur-relay.
4. Une fois la connexion P2P établie, les messages destinés à la `room` entre A et B peuvent transiter en P2P.

Remarques pratiques :
- Le serveur n'achemine pas les messages P2P après l'initiation (sauf fallback/relay).
- Gérer la sécurité : échange d'un token ou d'une signature pour vérifier l'authenticité du pair avant d'accepter la connexion.

4) Compatibilité et migration
------------------------------
- Ne pas casser le format de messages existant : si le code actuellement lit messages sans préfixe longueur, ajouter la logique qui accepte les deux formats temporairement, ou effectuer une migration coordonnée (serveur + clients).
- Documenter bien le format `length + payload` et ajouter des utilitaires pour l'encodage/décodage.

5) Pièces de code utiles
------------------------
- Voir `network/protocol.py` et `network/state_machine.py` dans le dépôt pour exemples d'implémentation (envoi/lecture avec 4-octets longueur, gestion simple d'états intermédiaires avec blocage et timeout).

Si tu veux, j'intègre ces utilitaires directement dans ton serveur/clients existants (sans modifier leur API), ou je peux créer des tests/exemples pour valider l'interaction.
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


