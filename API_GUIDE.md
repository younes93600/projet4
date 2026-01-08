# 📘 Guide d'utilisation de l'API SaaS Stock Manager

Ce document explique comment installer, lancer et utiliser l'API RESTful de l'application de gestion de stock.

## 📋 Prérequis

- **Python 3.8** ou supérieur installé sur votre machine.
- Accès au dossier du projet contenant `api.py`, `database.py`, etc.

## 🚀 Installation

Il est recommandé d'utiliser un environnement virtuel, mais vous pouvez aussi installer les dépendances globalement.

1. **Ouvrir un terminal** dans le dossier du projet :
   ```powershell
   cd c:\Users\robin\Documents\projet4-robin3
   ```

2. **Installer les dépendances** via le fichier `requirements.txt` fourni :
   ```powershell
   pip install -r requirements.txt
   ```
   *Si vous n'avez pas le fichier `requirements.txt`, installez manuellement :*
   `pip install fastapi uvicorn python-jose[cryptography] python-multipart`

## ⚡ Lancement de l'API

Pour démarrer le serveur de développement, exécutez la commande suivante :

```powershell
uvicorn api:app --reload
```

> [!NOTE]
> **Si la commande `uvicorn` n'est pas reconnue** (erreur "terme non reconnu") :
> Essayez de lancer via python directement :
> ```powershell
> python -m uvicorn api:app --reload
> ```

- **`api:app`** : Fait référence à l'instance FastAPI `app` dans le fichier `api.py`.
- **`--reload`** : Permet de redémarrer automatiquement le serveur si vous modifiez le code.

Vous devriez voir un message indiquant que le serveur tourne, généralement sur :
`http://127.0.0.1:8000`

## 📖 Utilisation de la Documentation Interactive (Swagger UI)

FastAPI génère automatiquement une documentation interactive que vous pouvez utiliser pour tester l'API sans écrire de code.

1. **Ouvrez votre navigateur** à l'adresse suivante :
   👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

2. **S'authentifier (Login)** :
   La plupart des routes sont protégées. Vous devez obtenir un token.
   - Cliquez sur le bouton **Authorize** (cadenas) en haut à droite ou sur l'endpoint `POST /api/auth/login`.
   - Entrez un `user_id` (nom d'utilisateur, ex: un utilisateur présent dans `utilisateurs.csv`) et son `password`.
   - Cliquez sur **Authorize**.
   - Si les identifiants sont corrects, le cadenas se fermera et vous serez authentifié pour les futures requêtes.

3. **Tester un endpoint** :
   - Cliquez sur une route (ex: `GET /api/products`).
   - Cliquez sur **Try it out**.
   - Cliquez sur **Execute**.
   - Vous verrez la réponse JSON en dessous (liste des produits).

## 🔑 Points Clés de l'Architecture

- **Sécurité** : L'API utilise des tokens **JWT (JSON Web Tokens)**. Une fois connecté, le token est envoyé automatiquement dans le header `Authorization: Bearer <token>`.
- **Base de Données** : L'API partage les mêmes fichiers CSV (`inventaire.csv`, `utilisateurs.csv`, etc.) que l'application Desktop (`projet 4.py`).
  - ⚠️ **Attention** : Évitez de modifier les fichiers CSV manuellement pendant que l'API ou l'application Desktop tourne pour éviter des conflits d'écriture si le trafic est élevé (bien que pour un usage local, le risque est faible).
- **Fichiers Importants** :
  - `api.py` : Le contrôleur principal de l'API.
  - `auth.py` : Gestion de la sécurité et des tokens.
  - `database.py` : Fonctions de lecture/écriture CSV partagées.
  - `models.py` : Schémas de données Pydantic pour la validation.

## 🛠 Dépannage

- **Erreur "ModuleNotFoundError"** : Vérifiez que vous avez bien lancé `pip install` et que vous êtes dans le bon environnement virtuel.
- **Erreur 401 Unauthorized** : Votre token a peut-être expiré (30 minutes par défaut). Reconnectez-vous via le bouton **Authorize**.
