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
