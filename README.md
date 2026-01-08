# DropBox-python - Chat TCP avec partage de fichiers

Application de chat TCP avec interface Flet permettant le partage de fichiers dans des rooms.

## 📋 Fonctionnalités

- ✅ Chat en temps réel avec système de rooms
- ✅ Partage de fichiers entre utilisateurs
- ✅ Interface graphique moderne avec Flet
- ✅ Notifications admin
- ✅ Dashboard administrateur
- ✅ Téléchargement automatique dans le dossier Windows

## 🚀 Démarrage rapide

### 1. Installation des dépendances

```powershell
python -m pip install -r requirements.txt
```

### 2. Lancer le serveur

```powershell
python serveur.py
```

Le serveur démarre sur `127.0.0.1:54321` avec le dashboard administrateur.

### 3. Lancer un ou plusieurs clients

```powershell
python client.py
```

## 📂 Structure du projet

```
DropBox-python/
│
├── serveur.py              # Serveur TCP principal
├── client.py               # Client avec interface Flet
├── telechargement.py       # Module de gestion des fichiers
├── admin_dashboard.py      # Interface admin
├── parser.py               # Parseur de protocole
├── requirements.txt        # Dépendances
├── PROTOCOL.md            # Documentation du protocole
│
└── network/               # Modules réseau
    ├── protocol.py        # Framing et JSON
    └── state_machine.py   # Gestion des séquences
```

## 🎮 Utilisation

### Client

1. **Connexion** : Entrez votre pseudo et cliquez sur "Se connecter"
2. **Rejoindre une room** : Cliquez sur Room 1, 2 ou 3
3. **Envoyer des messages** : Tapez votre message et cliquez sur "Envoyer"
4. **Partager un fichier** :
   - Cliquez sur "Sélectionner un fichier"
   - Choisissez votre fichier
   - Cliquez sur "Envoyer un fichier"
5. **Télécharger un fichier** : Cliquez sur "Télécharger" dans le chat

Les fichiers téléchargés sont automatiquement sauvegardés dans votre dossier **Téléchargements** Windows.

### Serveur / Admin

Le dashboard admin permet de :
- Voir tous les clients connectés
- Envoyer des notifications broadcast
- Gérer les rooms
- Kicker des utilisateurs

## 🛠️ Développement

### Tests

```powershell
python -m unittest discover -v
```

### Protocole

Le protocole utilise :
- **Framing** : Préfixe 4-octets (uint32 big-endian) pour la taille du message
- **Messages texte** : Format `COMMAND|arg1|arg2|...`
- **Fichiers** : Messages JSON avec données en base64

Voir `PROTOCOL.md` pour plus de détails.

## 📦 Dépendances

- `flet` : Interface graphique
- Librairies standard Python : `socket`, `threading`, `json`, `base64`

## 🔧 Configuration

- **Port serveur** : 54321 (configurable dans `serveur.py`)
- **Dossier téléchargements serveur** : `downloads/`
- **Dossier téléchargements client** : Dossier Téléchargements Windows

## 👥 Commandes

```bash
# Lancer le serveur
python serveur.py

# Lancer un client
python client.py
```

C'est tout ! Simple et efficace.

## 📝 Notes

- Le serveur supporte plusieurs clients simultanés
- Chaque room est isolée (les messages ne sont visibles que dans la room)
- Les fichiers sont stockés côté serveur avec un identifiant unique
- L'authentification se fait uniquement par pseudo (pas de mot de passe)

## 🐛 Dépannage

**Le serveur ne démarre pas** :
- Vérifiez que le port 54321 est disponible
- Assurez-vous que les dépendances sont installées

**Le client ne se connecte pas** :
- Vérifiez que le serveur est démarré
- Vérifiez l'adresse IP et le port dans `client.py`

**Les fichiers ne s'envoient pas** :
- Rejoignez d'abord une room
- Vérifiez que le fichier existe
- Vérifiez la taille du fichier (limites de mémoire)
