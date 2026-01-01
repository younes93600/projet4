import webview
import csv
import os
import time
import hashlib
import secrets
import hmac
import logging
import re
import json
import requests  # --- AJOUT API : Nécessaire pour pwnedpasswords ---

# --- CONFIGURATION SÉCURITÉ & LOGS ---
fichier_csv = 'inventaire.csv'
fichier_users = 'utilisateurs.csv'
fichier_log = 'security.log'

logging.basicConfig(
    filename=fichier_log,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Variables globales
data = {}
max_id = 0
users_db = {}
current_user = None

# ... [TES FONCTIONS DE GESTION DE FICHIERS SONT ICI, INCHANGÉES] ...
# (Je ne les répète pas pour alléger, garde tes fonctions charger_users, sauver_user, etc.)

def charger_users():
    global users_db
    users_db = {}
    if not os.path.exists(fichier_users):
        with open(fichier_users, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['username', 'salt', 'hash'], delimiter=";")
            writer.writeheader()   
    try:
        with open(fichier_users, "r", newline="", encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                users_db[row['username']] = {'salt': row['salt'], 'hash': row['hash']}
    except Exception as e:
        logging.error(f"SYSTEM: Erreur chargement users DB - {e}")

def sauver_user(username, salt, hashed_pw):
    try:
        is_empty = not os.path.exists(fichier_users) or os.stat(fichier_users).st_size == 0
        with open(fichier_users, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['username', 'salt', 'hash'], delimiter=";")
            if is_empty: writer.writeheader()
            writer.writerow({'username': username, 'salt': salt, 'hash': hashed_pw})
    except Exception as e:
        logging.error(f"SYSTEM: Erreur sauvegarde user {username} - {e}")

def charger_inventaire():
    global data, max_id
    data = {}
    max_id = 0
    if not os.path.exists(fichier_csv):
        with open(fichier_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'nom', 'prix', 'quantite'], delimiter=";")
            writer.writeheader()
    try:
        with open(fichier_csv, "r", newline="", encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                id_prod = int(row["id"])
                data[id_prod] = {"id": id_prod, "nom": row["nom"], "prix": float(row["prix"]), "quantite": int(row["quantite"])}
                if id_prod > max_id: max_id = id_prod
    except Exception as e:
        logging.error(f"SYSTEM: Erreur chargement inventaire : {e}")

def sauver_inventaire():
    try:
        with open(fichier_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id', 'nom', 'prix', 'quantite']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            for item in data.values():
                writer.writerow(item)
    except Exception as e:
        logging.error(f"SYSTEM: Erreur sauvegarde inventaire : {e}")


# --- FONCTIONS CRYPTO ---

def hacher_mdp(password, salt):
    # Hash interne pour le stockage (SHA-256)
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def valider_complexite_mdp(password):
    if len(password) < 8: return False, "Trop court (min 8 chars)."
    if not re.search(r"\d", password): return False, "Manque un chiffre."
    if not re.search(r"[A-Z]", password): return False, "Manque une majuscule."
    return True, "Valide"

# --- NOUVELLE FONCTION API PWNED ---

def verifier_leak_pwned(password):
    """
    Vérifie si le mot de passe est dans la base de données des fuites.
    Retourne (True, count) si compromis, (False, 0) sinon.
    """
    # L'API demande du SHA-1 (pas SHA-256)
    sha1_password = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    
    # K-Anonymity : On envoie seulement les 5 premiers caractères
    prefix, suffix = sha1_password[:5], sha1_password[5:]
    
    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    
    try:
        response = requests.get(url, timeout=3) # Timeout court pour ne pas bloquer l'UI
        if response.status_code != 200:
            logging.warning(f"API PWNED: Erreur statut {response.status_code}")
            return False, 0 # En cas d'erreur API, on laisse passer (Fail Open)

        # On vérifie si notre suffixe est dans la réponse
        hashes = (line.split(':') for line in response.text.splitlines())
        for h, count in hashes:
            if h == suffix:
                return True, int(count)
        return False, 0
        
    except requests.RequestException as e:
        logging.warning(f"API PWNED: Erreur connexion - {e}")
        return False, 0 # Pas d'internet ? On laisse passer.

# ... [TON CODE HTML RESTE INCHANGÉ] ...
html_content = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gestion Stock - Dark Mode</title>
    <style>
        /* PALETTE SOMBRE */
        :root { 
            --bg-color: #121212;         /* Fond principal très sombre */
            --card-bg: #1e1e1e;          /* Fond des cartes (gris foncé) */
            --text-main: #e0e0e0;        /* Texte principal (blanc cassé) */
            --text-muted: #a0a0a0;       /* Texte secondaire */
            --input-bg: #2d2d2d;         /* Fond des inputs */
            --border-color: #333333;     /* Bordures */
            
            --accent: #3498db;           /* Bleu professionnel */
            --accent-hover: #2980b9;
            --danger: #cf6679;           /* Rouge doux pour dark mode */
            --success: #03dac6;          /* Vert sarcelle pour dark mode */
        }

        body { 
            font-family: 'Segoe UI', sans-serif; 
            background-color: var(--bg-color); 
            color: var(--text-main);
            margin: 0; padding: 0; 
            display: flex; flex-direction: column; height: 100vh; 
        }
        
        /* Containers */
        .container { max-width: 950px; margin: 0 auto; padding: 20px; width: 100%; box-sizing: border-box; }
        .card { 
            background: var(--card-bg); 
            padding: 25px; 
            border-radius: 8px; 
            box-shadow: 0 4px 10px rgba(0,0,0,0.5); 
            margin-bottom: 20px; 
            border: 1px solid #333;
        }
        .hidden { display: none !important; }
        
        /* Typography */
        h1, h2, h3 { color: white; margin-top: 0; font-weight: 500; }
        
        /* Forms */
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: var(--text-muted); font-size: 0.9em; }
        
        input { 
            width: 100%; padding: 12px; 
            background-color: var(--input-bg);
            border: 1px solid var(--border-color);
            color: white;
            border-radius: 4px; 
            box-sizing: border-box; 
            outline: none;
            transition: border-color 0.3s;
        }
        input:focus { border-color: var(--accent); }
        input::placeholder { color: #666; }
        
        /* Buttons */
        button { 
            padding: 10px 20px; border: none; border-radius: 4px; 
            cursor: pointer; font-size: 14px; font-weight: bold;
            transition: opacity 0.2s, transform 0.1s; color: #121212; 
        }
        button:active { transform: scale(0.98); }
        
        .btn-primary { background-color: var(--accent); color: white; }
        .btn-primary:hover { background-color: var(--accent-hover); }
        
        .btn-danger { background-color: var(--danger); color: #121212; }
        .btn-success { background-color: var(--success); color: #121212; }
        
        .btn-block { width: 100%; padding: 12px; font-size: 16px; }
        
        /* Links */
        a { color: var(--accent); text-decoration: none; }
        a:hover { text-decoration: underline; }

        /* Table */
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 14px; text-align: left; border-bottom: 1px solid var(--border-color); }
        th { background-color: #252525; color: var(--text-muted); font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; }
        tr:hover { background-color: #2c2c2c; }
        
        /* Header Dashboard */
        header { 
            background: #1f1f1f; 
            border-bottom: 1px solid #333;
            padding: 15px 30px; 
            display: flex; justify-content: space-between; align-items: center; 
        }
        .logo { font-weight: bold; font-size: 1.2em; color: var(--accent); letter-spacing: 1px; }
        
        /* Utils */
        .flex-row { display: flex; gap: 10px; }
        .error-msg { color: var(--danger); font-size: 0.9em; margin-top: 10px; min-height: 20px; }
        
        /* Scrollbar custom pour Webkit */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-color); }
        ::-webkit-scrollbar-thumb { background: #444; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #555; }
    </style>
</head>
<body>

    <div id="auth-view" class="container" style="display: flex; justify-content: center; align-items: center; height: 90vh;">
        <div class="card" style="width: 380px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 id="auth-title">Connexion</h2>
                <div style="color: var(--text-muted); font-size: 0.9em;">Accès sécurisé au stock</div>
            </div>
            
            <div class="form-group">
                <label>IDENTIFIANT</label>
                <input type="text" id="username" placeholder="Entrez votre nom">
            </div>
            <div class="form-group">
                <label>MOT DE PASSE</label>
                <input type="password" id="password" placeholder="••••••••">
            </div>
            
            <button class="btn-primary btn-block" onclick="tenterConnexion()" id="btn-login">Se connecter</button>
            
            <div id="auth-feedback" class="error-msg" style="text-align: center;"></div>
            
            <div style="text-align: center; margin-top: 20px; border-top: 1px solid #333; padding-top: 15px;">
                <a href="#" onclick="toggleAuthMode()" id="toggle-auth-text" style="font-size: 0.9em;">Créer un nouveau compte</a>
            </div>
        </div>
    </div>

    <div id="dashboard-view" class="hidden">
        <header>
            <div class="logo">📦 STOCK MANAGER</div>
            <div class="flex-row" style="align-items: center;">
                <span style="color: var(--text-muted); margin-right: 10px;">Utilisateur : <b style="color: white;" id="display-user">User</b></span>
                <button class="btn-danger" onclick="logout()" style="padding: 6px 14px; font-size: 12px;">QUITTER</button>
            </div>
        </header>

        <div class="container">
            <div class="card">
                <h3 style="border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 20px;">Ajouter un produit</h3>
                <div class="flex-row">
                    <input type="text" id="prod-nom" placeholder="Nom du produit" style="flex: 3;">
                    <input type="number" id="prod-prix" placeholder="Prix (€)" step="0.01" style="flex: 1;">
                    <input type="number" id="prod-qte" placeholder="Qté" style="flex: 1;">
                    <button class="btn-success" onclick="ajouterProduit()" style="flex: 1;">AJOUTER</button>
                </div>
            </div>

            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3>Inventaire en temps réel</h3>
                    <button onclick="chargerInventaireJS()" style="background:transparent; color:var(--accent); border:1px solid var(--accent);">Actualiser</button>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th style="width: 50px;">ID</th>
                            <th>Nom du produit</th>
                            <th style="width: 100px;">Prix</th>
                            <th style="width: 80px;">Stock</th>
                            <th style="width: 60px; text-align: center;">Action</th>
                        </tr>
                    </thead>
                    <tbody id="inventory-body">
                        </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let isLoginMode = true;

        function toggleAuthMode() {
            isLoginMode = !isLoginMode;
            document.getElementById('auth-title').innerText = isLoginMode ? "Connexion" : "Création";
            document.getElementById('btn-login').innerText = isLoginMode ? "Se connecter" : "S'inscrire";
            document.getElementById('toggle-auth-text').innerText = isLoginMode ? "Créer un nouveau compte" : "J'ai déjà un compte";
            document.getElementById('auth-feedback').innerText = "";
        }

        async function tenterConnexion() {
            const u = document.getElementById('username').value;
            const p = document.getElementById('password').value;
            const feedback = document.getElementById('auth-feedback');
            
            if(!u || !p) { feedback.innerText = "Champs requis."; return; }
            
            // Petit loading feedback pour l'utilisateur
            feedback.innerText = "Vérification...";
            feedback.style.color = "#a0a0a0";

            if (isLoginMode) {
                const res = await pywebview.api.login(u, p);
                if (res.success) { 
                    feedback.innerText = "";
                    showDashboard(u); 
                } else { 
                    feedback.style.color = "var(--danger)";
                    feedback.innerText = res.message; 
                }
            } else {
                const res = await pywebview.api.register(u, p);
                if (res.success) { 
                    alert("Compte créé avec succès !"); 
                    toggleAuthMode(); 
                } else { 
                    feedback.style.color = "var(--danger)";
                    feedback.innerText = res.message; 
                }
            }
        }

        function showDashboard(username) {
            document.getElementById('auth-view').classList.add('hidden');
            document.getElementById('dashboard-view').classList.remove('hidden');
            document.getElementById('display-user').innerText = username;
            chargerInventaireJS();
        }

        function logout() {
            pywebview.api.logout();
            document.getElementById('dashboard-view').classList.add('hidden');
            document.getElementById('auth-view').classList.remove('hidden');
            document.getElementById('username').value = "";
            document.getElementById('password').value = "";
            document.getElementById('auth-feedback').innerText = "";
        }

        async function chargerInventaireJS() {
            const stock = await pywebview.api.get_stock();
            const tbody = document.getElementById('inventory-body');
            tbody.innerHTML = "";
            
            stock.forEach(item => {
                const tr = document.createElement('tr');
                // Coloration du stock bas (optionnel)
                const stockColor = item.quantite < 5 ? '#cf6679' : 'inherit';
                
                tr.innerHTML = `
                    <td style="color: #666;">#${item.id}</td>
                    <td style="font-weight: 500;">${item.nom}</td>
                    <td>${item.prix.toFixed(2)} €</td>
                    <td style="color: ${stockColor}; font-weight: bold;">${item.quantite}</td>
                    <td style="text-align: center;">
                        <button class="btn-danger" style="padding: 4px 8px; font-size: 10px;" onclick="supprimerProduit(${item.id})">✖</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function ajouterProduit() {
            const nom = document.getElementById('prod-nom').value;
            const prix = document.getElementById('prod-prix').value;
            const qte = document.getElementById('prod-qte').value;
            if(!nom || !prix || !qte) return;
            await pywebview.api.add_product(nom, prix, qte);
            document.getElementById('prod-nom').value = "";
            document.getElementById('prod-prix').value = "";
            document.getElementById('prod-qte').value = "";
            chargerInventaireJS();
        }

        async function supprimerProduit(id) {
            if(confirm("Supprimer définitivement ce produit ?")) {
                await pywebview.api.delete_product(id);
                chargerInventaireJS();
            }
        }
    </script>
</body>
</html>
"""

# --- API PYTHON (BACKEND) ---

class Api:
    def __init__(self):
        self.user = None

    def login(self, username, password):
        username = username.strip()
        if username not in users_db:
            hacher_mdp("dummy", secrets.token_hex(16))
            logging.warning(f"LOGIN: Échec pour '{username}' (Inconnu).")
            return {"success": False, "message": "Identifiants incorrects."}

        stored_salt = users_db[username]['salt']
        stored_hash = users_db[username]['hash']
        
        if hmac.compare_digest(stored_hash, hacher_mdp(password, stored_salt)):
            self.user = username
            logging.info(f"LOGIN: Succès pour '{username}'.")
            return {"success": True, "message": "OK"}
        else:
            logging.warning(f"LOGIN: Échec pour '{username}' (Mauvais pass).")
            return {"success": False, "message": "Identifiants incorrects."}

    def register(self, username, password):
        username = username.strip()
        if username in users_db:
            return {"success": False, "message": "Utilisateur déjà existant."}
        
        # 1. Vérification complexité locale
        valid, msg = valider_complexite_mdp(password)
        if not valid: return {"success": False, "message": msg}

        # 2. --- AJOUT API --- Vérification Have I Been Pwned
        is_pwned, count = verifier_leak_pwned(password)
        if is_pwned:
            logging.warning(f"INSCRIPTION: Refus mot de passe Pwned pour '{username}' ({count} fois).")
            return {
                "success": False, 
                "message": f"Ce mot de passe a été vu {count} fois dans des fuites de données. Veuillez en choisir un autre."
            }

        try:
            salt = secrets.token_hex(16)
            hashed_pw = hacher_mdp(password, salt)
            users_db[username] = {'salt': salt, 'hash': hashed_pw}
            sauver_user(username, salt, hashed_pw)
            logging.info(f"INSCRIPTION: Nouvel utilisateur '{username}'.")
            return {"success": True, "message": "Compte créé."}
        except Exception as e:
            return {"success": False, "message": f"Erreur: {str(e)}"}

    def logout(self):
        logging.info(f"LOGOUT: {self.user} déconnecté.")
        self.user = None

    def get_stock(self):
        return sorted(list(data.values()), key=lambda x: x['id'])

    def add_product(self, nom, prix, quantite):
        global max_id
        try:
            max_id += 1
            data[max_id] = {"id": max_id, "nom": nom, "prix": float(prix), "quantite": int(quantite)}
            sauver_inventaire()
            logging.info(f"ACTION: Produit {max_id} ajouté par {self.user}.")
            return True
        except Exception as e:
            logging.error(f"Erreur ajout: {e}")
            return False

    def delete_product(self, pid):
        try:
            pid = int(pid)
            if pid in data:
                del data[pid]
                sauver_inventaire()
                logging.info(f"ACTION: Produit {pid} supprimé par {self.user}.")
                return True
        except Exception as e:
            logging.error(f"Erreur suppression: {e}")
        return False

# --- POINT DE LANCEMENT ---

if __name__ == "__main__":
    charger_users()
    charger_inventaire()
    
    api = Api()
    
    window = webview.create_window(
        title='Stock Sécurisé (Dark)',
        html=html_content,
        js_api=api,
        width=1000,
        height=750,
        resizable=True,
        background_color='#121212'
    )
    
    webview.start()