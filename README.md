# Interface Flet — exemple

Ce dépôt contient un petit exemple d'interface construite avec `flet`.

- **Fichier principal**: `app.py` — crée un bouton par élément du tableau Python ("rooms").
- **Dépendances**: listées dans `requirements.txt` (`flet`).


Usage rapide (PowerShell):

```powershell
python -m pip install -r requirements.txt
python app.py
```

Comportement par défaut : si tu ne passes pas `--rooms`, l'application génère automatiquement un nombre aléatoire de rooms entre 1 et 6 à chaque lancement (ex : `Room 1`, `Room 2`, ...).

Pour fournir une liste personnalisée de rooms (JSON) :

```powershell
python app.py --rooms '["Salle A", "Salle B", "Salle C"]'
```

Explication succincte : `app.py` lit l'argument `--rooms` (une chaîne JSON) et crée un bouton `ElevatedButton` pour chaque entrée. Cliquer sur un bouton affichera une notification.

Si tu veux que l'application récupère le tableau depuis un autre module Python, importe `main_factory` et passe la liste voulue à `ft.app(target=main_factory(ta_liste))`.

## Utilitaires réseau & exemples (Stories 6/7/12)

J'ai ajouté des utilitaires et des exemples pour implémenter :
- Story 6 : séquences / états intermédiaires (BEGIN_SEQUENCE / COMPLETE)
- Story 7 : préfixe 32-bit (4 octets) indiquant la taille du payload
- Story 12 : initiation P2P (documentée dans `PROTOCOL.md`)

Fichiers ajoutés :
- `PROTOCOL.md` : spécifications et recommandations (format des messages, séquences, P2P)
- `network/protocol.py` : envoi / réception avec préfixe 4-octets et JSON payload
- `network/state_machine.py` : gestion légère des séquences intermédiaires (bloquantes)
- `tests/` : tests unitaires pour `network.protocol` et `network.state_machine`

Tester localement (PowerShell) :

1. Installer les dépendances si nécessaire (socket et stdlib sont suffisants) :

```powershell
python -m pip install -r .\requirements.txt
```

2. Lancer le serveur (serveur principal du repo) dans un terminal :

```powershell
python .\serveur.py
```

3. Lancer le client Flet dans un autre terminal :

```powershell
python .\client.py
```

Tests
-----
J'ai ajouté des tests unitaires dans `tests/`. Pour lancer les tests :

```powershell
python -m unittest discover -v
```

Remarques
---------
- Les fichiers `examples/demo_sequence_*` ont été supprimés et l'exemple a été intégré dans `serveur.py`/`client.py`.
- Le transport utilise maintenant un préfixe 4-octets (uint32 big-endian). Assure-toi que tous les clients utilisent le framing avant de déployer.

Intégration : utilise `network.protocol.send_json` / `recv_json` pour envoyer/recevoir des objets JSON encodés avec un préfixe 4-octets (uint32 big-endian). Le gestionnaire `IntermediateStateManager` dans `network/state_machine.py` peut être utilisé côté client pour bloquer ou gérer l'état en asynchrone.

Si tu veux, j'intègre ces utilitaires dans tes modules serveur/client existants — indique-moi les chemins des fichiers réseau à mettre à jour et je m'en occupe.
