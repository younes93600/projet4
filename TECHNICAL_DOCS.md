# 📄 Fiche Technique & Documentation du Code

Ce document détaille l'utilité de chaque fichier du projet et explique les blocs de code importants pour la maintenance.

## 🗂 Structure des Fichiers

### 1. `api.py` (Cerveau de l'API)
C'est le fichier principal qui lance le serveur web. Il utilise **FastAPI** pour créer les "routes" (endpoints) accessibles via HTTP.
- **Rôle** : Reçoit les requêtes HTTP, vérifie la sécurité (Token), appelle la base de données, et renvoie la réponse JSON.
- **Points clés** :
  - `@app.post("/api/auth/login")` : Gère la connexion et la création du Token.
  - `@app.get` / `@app.post` : Définissent les actions possibles (Lire, Créer).
  - `Depends(auth.get_current_user)` : C'est le "gardien". Si cette fonction est présente dans les paramètres d'une route, l'utilisateur DOIT être connecté pour y accéder.

### 2. `auth.py` (Sécurité & Cryptographie)
Gère tout ce qui concerne l'authentification et la protection des mots de passe.
- **Rôle** : Vérifier les mots de passe et générer les "badges d'accès" (Tokens JWT).
- **Fonctions Clés** :
  - `verify_password` : Compare le mot de passe envoyé par l'utilisateur avec le hash stocké en base.
  - `create_access_token` : Crée un Token signé numériquement. Si on modifie le token, la signature casse (anti-triche).
  - `get_current_user` : Décode le token reçu pour savoir QUI fait la requête.

### 3. `database.py` (Accès aux Données)
C'est le seul fichier qui a le droit de toucher aux fichiers CSV.
- **Rôle** : Lire et écrire les données sur le disque dur.
- **Pourquoi séparer ça ?** : Si demain vous voulez passer sur une vraie base de données (SQL), vous n'avez que ce fichier à modifier. Tout le reste du code continuera de fonctionner.

### 4. `models.py` (Schémas de Données)
Définit la "forme" que doivent avoir les données.
- **Rôle** : Validation automatique. Si un utilisateur essaie d'envoyer un produit sans "prix", le code rejettera la demande automatiquement grâce à ces modèles.
- **Technologie** : Utilise **Pydantic**.

### 5. `projet 4.py` (Application Bureau)
L'ancien code de l'application Desktop.
- **Note** : Il fonctionne de manière indépendante de l'API mais partage les mêmes fichiers CSV.

---

## 🔒 Sécurité : Ce qu'il faut savoir

### Le Hashage (Salage)
Les mots de passe ne sont **jamais** stockés en clair.
```python
# Dans auth.py
computed_hash = hashlib.sha256((salt + plain_password).encode('utf-8')).hexdigest()
```
- On ajoute un "grain de sel" (`salt` aléatoire) au mot de passe avant de le mélanger (`sha256`).
- Cela empêche les pirates d'utiliser des "Rainbow Tables" (dictionnaires de hashs connus) pour retrouver les mots de passe.

### JWT (JSON Web Token)
C'est le mécanisme de session moderne.
- Au lieu de stocker une session sur le serveur, on donne un Jeton à l'utilisateur.
- Ce jeton contient son identité et une date d'expiration.
- **Secret Key** : C'est la clé maître qui permet de signer les jetons. 
  - ⚠️ **Important** : Dans `auth.py`, la variable `SECRET_KEY` est écrite en dur. Dans un vrai projet professionnel, elle devrait être cachée dans une variable d'environnement du serveur.

## 🧹 Maintenance

- **Ajouter une colonne aux produits** :
  1. Modifier `models.py` pour ajouter le champ.
  2. Modifier `database.py` (`get_all_products`, `save_all_products`, etc.) pour lire/écrire ce nouveau champ dans le CSV.
  3. Le reste suivra automatiquement.

- **Fichiers CSV** :
  - `inventaire.csv` : Liste des produits.
  - `utilisateurs.csv` : Comptes utilisateurs (avec hash et salt).
  - `ventes.csv` : Historique des transactions.
