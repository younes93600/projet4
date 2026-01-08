import webview
import csv
import os
import hashlib
import secrets
import hmac
import logging
import re
import uuid  # NOUVEAU : Pour générer un ID unique par panier
from datetime import datetime, timedelta
from collections import Counter, defaultdict

# --- CONFIGURATION & LOGS ---
fichier_csv = 'inventaire.csv'
fichier_users = 'utilisateurs.csv'
fichier_ventes = 'ventes.csv'
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

# --- GESTION PERSISTANCE (CSV) ---

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
        logging.error(f"SYSTEM: Erreur chargement users - {e}")

def sauver_user(username, salt, hashed_pw):
    try:
        is_empty = not os.path.exists(fichier_users) or os.stat(fichier_users).st_size == 0
        with open(fichier_users, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['username', 'salt', 'hash'], delimiter=";")
            if is_empty: writer.writeheader()
            writer.writerow({'username': username, 'salt': salt, 'hash': hashed_pw})
    except Exception as e:
        logging.error(f"SYSTEM: Erreur sauvegarde user - {e}")

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
        logging.error(f"SYSTEM: Erreur chargement inventaire - {e}")

def sauver_inventaire():
    try:
        with open(fichier_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['id', 'nom', 'prix', 'quantite']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            for item in data.values():
                writer.writerow(item)
    except Exception as e:
        logging.error(f"SYSTEM: Erreur sauvegarde inventaire - {e}")

# --- GESTION VENTES (MODIFIÉ POUR TID) ---
def enregistrer_vente(id_prod, nom, prix_unitaire, qte, client_nom, tid):
    try:
        is_empty = not os.path.exists(fichier_ventes) or os.stat(fichier_ventes).st_size == 0
        # Ajout de 'tid' (Transaction ID)
        fieldnames = ['date', 'tid', 'id_prod', 'nom', 'prix', 'qte', 'total', 'client']
        
        with open(fichier_ventes, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            if is_empty: writer.writeheader()
            
            total = float(prix_unitaire) * int(qte)
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            writer.writerow({
                'date': date_str,
                'tid': tid,
                'id_prod': id_prod,
                'nom': nom,
                'prix': prix_unitaire,
                'qte': qte,
                'total': total,
                'client': client_nom
            })
            logging.info(f"VENTE: {qte}x {nom} ({total}€) - Client: {client_nom} [ID: {tid}]")
            
    except Exception as e:
        logging.error(f"SYSTEM: Erreur enregistrement vente - {e}")

# --- SECURITY UTILS ---
def hacher_mdp(password, salt):
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def valider_complexite_mdp(password):
    if len(password) < 8: return False, "Trop court (min 8 chars)."
    if not re.search(r"\d", password): return False, "Manque un chiffre."
    if not re.search(r"[A-Z]", password): return False, "Manque une majuscule."
    return True, "Valide"

def verifier_leak_pwned(password):
    sha1_password = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix, suffix = sha1_password[:5], sha1_password[5:]
    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code != 200: return False, 0
        hashes = (line.split(':') for line in response.text.splitlines())
        for h, count in hashes:
            if h == suffix: return True, int(count)
        return False, 0
    except:
        return False, 0

# --- FRONTEND ---
html_content = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SaaS Dashboard Complet</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { 
            --bg-color: #121212; --card-bg: #1e1e1e; --text-main: #e0e0e0; 
            --text-muted: #a0a0a0; --input-bg: #2d2d2d; --border-color: #333333; 
            --accent: #3498db; --danger: #cf6679; --success: #03dac6; --warning: #f1c40f;
            --info: #3498db;
        }
        body { font-family: 'Segoe UI', sans-serif; background-color: var(--bg-color); color: var(--text-main); margin: 0; padding: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        header { background: #1f1f1f; border-bottom: 1px solid #333; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; height: 50px; }
        .main-layout { display: flex; flex: 1; overflow: hidden; }
        
        .sidebar { width: 220px; background: #181818; border-right: 1px solid #333; padding-top: 20px; display: flex; flex-direction: column; }
        .nav-btn { background: transparent; color: var(--text-muted); border: none; padding: 15px 25px; text-align: left; font-size: 16px; cursor: pointer; border-left: 3px solid transparent; transition: 0.2s; }
        .nav-btn:hover { background: #252525; color: white; }
        .nav-btn.active { background: #252525; color: var(--accent); border-left-color: var(--accent); font-weight: bold; }
        
        .content { flex: 1; padding: 25px; overflow-y: auto; }
        .card { background: var(--card-bg); padding: 20px; border-radius: 8px; border: 1px solid #333; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        
        .kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px; }
        .kpi-card { background: linear-gradient(145deg, #252525, #1e1e1e); padding: 15px; border-radius: 8px; border: 1px solid #333; text-align: center; }
        .kpi-value { font-size: 1.8em; font-weight: bold; color: white; margin: 5px 0; }
        .kpi-label { font-size: 0.85em; color: var(--text-muted); text-transform: uppercase; }
        .grid-2 { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        
        input, select { width: 100%; padding: 10px; background: var(--input-bg); border: 1px solid var(--border-color); color: white; border-radius: 4px; margin-bottom: 5px; box-sizing: border-box; }
        button { padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; color: #121212; }
        .btn-primary { background: var(--accent); color: white; }
        .btn-success { background: var(--success); }
        .btn-danger { background: var(--danger); }
        .btn-warning { background: var(--warning); }
        .btn-info { background: var(--info); color: white; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
        th { background: #252525; color: var(--text-muted); font-size: 0.85em; }
        
        #cart-table tr td { padding: 8px; border-bottom: 1px solid #444; font-size: 0.9em; }
        .cart-summary { margin-top: 10px; padding-top: 10px; border-top: 1px solid #555; text-align: right; font-weight: bold; color: var(--success); }
        
        .hidden { display: none !important; }
        .flex-row { display: flex; gap: 10px; }
        .auth-container { display: flex; justify-content: center; align-items: center; height: 100vh; width: 100%; }
        .chart-container { position: relative; height: 300px; width: 100%; }
    </style>
</head>
<body>

    <div id="auth-view" class="auth-container">
        <div class="card" style="width: 350px; text-align: center;">
            <h2 id="auth-title">Connexion SaaS</h2>
            <input type="text" id="username" placeholder="Utilisateur">
            <input type="password" id="password" placeholder="Mot de passe" style="margin-top:10px;">
            <button class="btn-primary" style="width:100%; margin-top:15px;" onclick="tenterConnexion()" id="btn-login">ENTRER</button>
            <p id="auth-feedback" style="color: var(--danger); font-size: 0.9em; min-height: 20px; margin-top: 10px;"></p>
            <a href="#" onclick="toggleAuthMode()" style="color: var(--accent); font-size: 0.9em;">Créer un compte / Se connecter</a>
        </div>
    </div>

    <div id="app-view" class="hidden" style="height: 100vh; display: flex; flex-direction: column;">
        <header>
            <div style="font-weight:bold; color:var(--accent); font-size:1.2em;">📦 STOCK MANAGER PRO</div>
            <div>
                <span style="color:#888; margin-right:15px;">Utilisateur: <b style="color:white;" id="display-user">User</b></span>
                <button class="btn-danger" style="padding: 5px 10px; font-size:0.8em;" onclick="logout()">Déconnexion</button>
            </div>
        </header>

        <div class="main-layout">
            <div class="sidebar">
                <button class="nav-btn active" onclick="switchTab('tab-stock')" id="btn-tab-stock">📋 Inventaire & Gestion</button>
                <button class="nav-btn" onclick="switchTab('tab-stats')" id="btn-tab-stats">📊 Statistiques & DATA</button>
            </div>

            <div class="content">
                
                <div id="tab-stock">
                    <div class="grid-2">
                        <div class="card">
                            <h3>Ajouter un produit</h3>
                            <div class="flex-row">
                                <input id="prod-nom" placeholder="Nom" style="flex:2">
                                <input id="prod-prix" type="number" placeholder="Prix" style="flex:1">
                                <input id="prod-qte" type="number" placeholder="Qté" style="flex:1">
                                <button class="btn-success" onclick="ajouterProduit()">AJOUTER</button>
                            </div>
                        </div>
                        
                        <div class="card" style="border: 1px solid var(--warning);">
                            <h3 style="color:var(--warning)">🛒 Panier / Caisse</h3>
                            <input id="sim-client" type="text" placeholder="Nom du client (pour toute la commande)" style="margin-bottom: 10px;">
                            
                            <div class="flex-row" style="margin-bottom: 5px;">
                                <select id="sim-select" style="flex:2"><option>Chargement...</option></select>
                                <input id="sim-qte" type="number" value="1" style="flex:1; max-width: 80px;" placeholder="Qté">
                                <button class="btn-info" style="flex:1" onclick="ajouterAuPanier()">+ PANIER</button>
                            </div>

                            <div style="background:#252525; padding:10px; border-radius:4px; margin-top:10px; max-height:150px; overflow-y:auto;">
                                <table id="cart-table" style="width:100%; margin:0;">
                                    <tbody id="cart-body">
                                        <tr><td colspan="3" style="text-align:center; color:#666;">Panier vide</td></tr>
                                    </tbody>
                                </table>
                            </div>
                            <div class="cart-summary" id="cart-total">Total: 0.00 €</div>
                            
                            <button class="btn-success" style="width:100%; margin-top:10px;" onclick="validerCommande()">VALIDER LA COMMANDE</button>
                        </div>
                    </div>

                    <div class="card">
                        <div style="display:flex; justify-content:space-between;">
                            <h3>Inventaire Temps Réel</h3>
                            <button class="btn-primary" style="padding:5px 10px;" onclick="chargerInventaireJS()">Rafraîchir</button>
                        </div>
                        <table>
                            <thead><tr><th>ID</th><th>Produit</th><th>Prix</th><th>Stock</th><th>Action</th></tr></thead>
                            <tbody id="inventory-body"></tbody>
                        </table>
                    </div>
                </div>

                <div id="tab-stats" class="hidden">
                    <h2>Tableau de bord Analytique</h2>
                    
                    <div class="kpi-grid">
                        <div class="kpi-card">
                            <div class="kpi-label">Chiffre d'Affaires</div>
                            <div class="kpi-value" id="kpi-ca">0.00 €</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Marge Estimée (30%)</div>
                            <div class="kpi-value" id="kpi-marge" style="color: var(--success);">0.00 €</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Volume Ventes</div>
                            <div class="kpi-value" id="kpi-vol">0</div>
                        </div>
                    </div>

                    <div class="grid-2">
                        <div class="card">
                            <h3>📈 Évolution des Ventes (7 jours)</h3>
                            <div class="chart-container">
                                <canvas id="chartEvolution"></canvas>
                            </div>
                        </div>
                        <div class="card">
                            <h3>🏆 Top 5 Produits</h3>
                            <div class="chart-container">
                                <canvas id="chartTop"></canvas>
                            </div>
                        </div>
                    </div>

                    <div class="card">
                        <h3>📋 Historique des Transactions Groupées</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Client</th>
                                    <th>Détail Commande</th>
                                    <th>Total Commande</th>
                                </tr>
                            </thead>
                            <tbody id="sales-history-body"></tbody>
                        </table>
                    </div>

                </div>

            </div>
        </div>
    </div>

    <div id="edit-modal" class="hidden" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:99; display:flex; justify-content:center; align-items:center;">
        <div class="card" style="width:300px; border: 1px solid var(--accent);">
            <h3>Modifier Stock</h3>
            <input type="hidden" id="edit-id">
            <label>Nom</label><input id="edit-nom">
            <label>Prix</label><input id="edit-prix" type="number">
            <label>Quantité</label><input id="edit-qte" type="number">
            <div class="flex-row" style="margin-top:15px;">
                <button class="btn-success" style="flex:1" onclick="sauverEdit()">Valider</button>
                <button class="btn-danger" style="flex:1" onclick="document.getElementById('edit-modal').classList.add('hidden')">Annuler</button>
            </div>
        </div>
    </div>

    <script>
        let isLoginMode = true;
        let chartInstanceEvol = null;
        let chartInstanceTop = null;
        let currentStock = [];
        let cart = []; 

        function toggleAuthMode() {
            isLoginMode = !isLoginMode;
            document.getElementById('auth-title').innerText = isLoginMode ? "Connexion SaaS" : "Création Compte";
            document.getElementById('btn-login').innerText = isLoginMode ? "ENTRER" : "S'INSCRIRE";
            document.getElementById('auth-feedback').innerText = "";
        }

        async function tenterConnexion() {
            const u = document.getElementById('username').value;
            const p = document.getElementById('password').value;
            if(!u || !p) return;
            
            let res;
            if(isLoginMode) res = await pywebview.api.login(u, p);
            else res = await pywebview.api.register(u, p);

            if(res.success) {
                document.getElementById('auth-view').style.display = 'none';
                document.getElementById('app-view').classList.remove('hidden');
                document.getElementById('display-user').innerText = u;
                chargerInventaireJS();
                chargerStatsJS(); 
            } else {
                document.getElementById('auth-feedback').innerText = res.message;
            }
        }

        async function logout() {
            await pywebview.api.logout_user();
            document.getElementById('app-view').classList.add('hidden');
            document.getElementById('password').value = "";
            document.getElementById('auth-feedback').innerText = "Déconnecté.";
            document.getElementById('auth-view').style.display = 'flex';
        }

        function switchTab(tabId) {
            document.getElementById('tab-stock').classList.add('hidden');
            document.getElementById('tab-stats').classList.add('hidden');
            document.getElementById('btn-tab-stock').classList.remove('active');
            document.getElementById('btn-tab-stats').classList.remove('active');

            document.getElementById(tabId).classList.remove('hidden');
            document.getElementById('btn-' + tabId).classList.add('active');

            if(tabId === 'tab-stats') chargerStatsJS();
        }

        async function chargerInventaireJS() {
            currentStock = await pywebview.api.get_stock();
            const tbody = document.getElementById('inventory-body');
            const select = document.getElementById('sim-select');
            
            tbody.innerHTML = "";
            select.innerHTML = "<option value=''>-- Sélectionner Produit --</option>";

            currentStock.forEach(p => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="color:#666">#${p.id}</td>
                    <td>${p.nom}</td>
                    <td>${p.prix} €</td>
                    <td style="${p.quantite < 5 ? 'color:var(--danger);font-weight:bold' : ''}">${p.quantite}</td>
                    <td>
                        <button class="btn-primary" style="padding:4px 8px;" onclick="ouvrirEdit(${p.id}, '${p.nom}', ${p.prix}, ${p.quantite})">✏️</button>
                        <button class="btn-danger" style="padding:4px 8px;" onclick="suppr(${p.id})">✖</button>
                    </td>
                `;
                tbody.appendChild(tr);

                const opt = document.createElement('option');
                opt.value = p.id;
                opt.innerText = `${p.nom} (${p.prix}€)`;
                select.appendChild(opt);
            });
        }

        async function ajouterProduit() {
            await pywebview.api.add_product(
                document.getElementById('prod-nom').value,
                document.getElementById('prod-prix').value,
                document.getElementById('prod-qte').value
            );
            chargerInventaireJS();
        }

        async function suppr(id) {
            if(confirm('Supprimer ?')) {
                await pywebview.api.delete_product(id);
                chargerInventaireJS();
            }
        }

        function ouvrirEdit(id, nom, prix, qte) {
            document.getElementById('edit-id').value = id;
            document.getElementById('edit-nom').value = nom;
            document.getElementById('edit-prix').value = prix;
            document.getElementById('edit-qte').value = qte;
            document.getElementById('edit-modal').classList.remove('hidden');
        }
        
        async function sauverEdit() {
            await pywebview.api.update_product(
                document.getElementById('edit-id').value,
                document.getElementById('edit-nom').value,
                document.getElementById('edit-prix').value,
                document.getElementById('edit-qte').value
            );
            document.getElementById('edit-modal').classList.add('hidden');
            chargerInventaireJS();
        }

        function ajouterAuPanier() {
            const pid = parseInt(document.getElementById('sim-select').value);
            const qte = parseInt(document.getElementById('sim-qte').value);
            
            if(!pid || qte <= 0) return alert("Sélection invalide");

            const product = currentStock.find(p => p.id === pid);
            if(!product) return;

            cart.push({
                id: product.id,
                nom: product.nom,
                prix: product.prix,
                qte: qte
            });

            renderCart();
        }

        function renderCart() {
            const tbody = document.getElementById('cart-body');
            tbody.innerHTML = "";
            let total = 0;

            if (cart.length === 0) {
                tbody.innerHTML = "<tr><td colspan='3' style='text-align:center; color:#666;'>Panier vide</td></tr>";
                document.getElementById('cart-total').innerText = "Total: 0.00 €";
                return;
            }

            cart.forEach((item, index) => {
                const subtotal = item.prix * item.qte;
                total += subtotal;
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${item.qte}x ${item.nom}</td>
                    <td>${subtotal.toFixed(2)}€</td>
                    <td style="text-align:right;"><button class="btn-danger" style="padding:2px 6px; font-size:0.8em;" onclick="removeFromCart(${index})">X</button></td>
                `;
                tbody.appendChild(tr);
            });

            document.getElementById('cart-total').innerText = `Total: ${total.toFixed(2)} €`;
        }

        function removeFromCart(index) {
            cart.splice(index, 1);
            renderCart();
        }

        async function validerCommande() {
            if(cart.length === 0) return alert("Le panier est vide !");
            
            let client = document.getElementById('sim-client').value;
            if(!client || client.trim() === "") client = "Client Anonyme";

            const res = await pywebview.api.process_cart(cart, client);
            alert(res.message);

            if(res.success) {
                cart = [];
                renderCart();
                document.getElementById('sim-client').value = "";
                chargerInventaireJS();
            }
        }

        async function chargerStatsJS() {
            const data = await pywebview.api.get_stats_data();
            
            document.getElementById('kpi-ca').innerText = data.ca_total + " €";
            document.getElementById('kpi-marge').innerText = data.marge_estimee + " €";
            document.getElementById('kpi-vol').innerText = data.volume_ventes;

            Chart.defaults.color = '#a0a0a0';
            Chart.defaults.borderColor = '#333';

            const ctxEvol = document.getElementById('chartEvolution').getContext('2d');
            if(chartInstanceEvol) chartInstanceEvol.destroy();
            
            chartInstanceEvol = new Chart(ctxEvol, {
                type: 'line',
                data: {
                    labels: data.evol_dates,
                    datasets: [{
                        label: "Chiffre d'Affaires (€)",
                        data: data.evol_valeurs,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });

            const ctxTop = document.getElementById('chartTop').getContext('2d');
            if(chartInstanceTop) chartInstanceTop.destroy();

            chartInstanceTop = new Chart(ctxTop, {
                type: 'bar',
                data: {
                    labels: data.top_noms,
                    datasets: [{
                        label: 'Unités Vendues',
                        data: data.top_qtes,
                        backgroundColor: ['#3498db', '#9b59b6', '#2ecc71', '#f1c40f', '#e74c3c']
                    }]
                },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: { legend: { display: false } }
                }
            });

            // Tableau historique GROUPÉ
            const historique = await pywebview.api.get_sales_history();
            const tbody = document.getElementById('sales-history-body');
            tbody.innerHTML = "";
            
            if(historique.length === 0) {
                tbody.innerHTML = "<tr><td colspan='4' style='text-align:center'>Aucune vente enregistrée.</td></tr>";
            } else {
                historique.forEach(v => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${v.date}</td>
                        <td style="color: var(--accent); font-weight:bold;">${v.client || 'Anonyme'}</td>
                        <td style="font-size:0.9em; color:#bbb;">${v.items}</td>
                        <td style="color: var(--success); font-weight:bold;">${parseFloat(v.total).toFixed(2)} €</td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        }
    </script>
</body>
</html>
"""

# --- API BACKEND ---

class Api:
    def __init__(self):
        self.user = None

    def login(self, username, password):
        username = username.strip()
        if username not in users_db:
            logging.warning(f"SECURITY: Tentative connexion utilisateur inconnu - {username}")
            return {"success": False, "message": "Inconnu."}
        
        stored_salt = users_db[username]['salt']
        if hmac.compare_digest(users_db[username]['hash'], hacher_mdp(password, stored_salt)):
            self.user = username
            logging.info(f"SECURITY: Connexion reussie - User: {username}")
            return {"success": True}
        
        logging.warning(f"SECURITY: Echec mot de passe - User: {username}")
        return {"success": False, "message": "Mot de passe incorrect."}

    def register(self, username, password):
        if username in users_db: return {"success": False, "message": "Existe déjà."}
        
        valid, msg = valider_complexite_mdp(password)
        if not valid: return {"success": False, "message": msg}
        
        is_pwned, count = verifier_leak_pwned(password)
        if is_pwned:
            logging.warning(f"SECURITY: Refus MDP compromis ({count} fois) - User: {username}")
            return {"success": False, "message": f"DANGER : Ce mot de passe est apparu dans {count} fuites de données ! Choisissez-en un autre."}
        
        salt = secrets.token_hex(16)
        hashed = hacher_mdp(password, salt)
        users_db[username] = {'salt': salt, 'hash': hashed}
        sauver_user(username, salt, hashed)
        logging.info(f"SECURITY: Nouveau compte cree - User: {username}")
        return {"success": True}

    def logout_user(self):
        if self.user:
            logging.info(f"SECURITY: Deconnexion - User: {self.user}")
        self.user = None
        return True

    def get_stock(self):
        return sorted(list(data.values()), key=lambda x: x['id'])

    def add_product(self, nom, prix, qte):
        global max_id
        try:
            max_id += 1
            data[max_id] = {"id": max_id, "nom": nom, "prix": float(prix), "quantite": int(qte)}
            sauver_inventaire()
            logging.info(f"INVENTAIRE: Ajout produit #{max_id} {nom} (Qté: {qte})")
            return True
        except: return False

    def delete_product(self, pid):
        if int(pid) in data:
            nom = data[int(pid)]['nom']
            del data[int(pid)]
            sauver_inventaire()
            logging.info(f"INVENTAIRE: Suppression produit #{pid} {nom}")
            return True
        return False

    def update_product(self, pid, nom, prix, qte):
        pid = int(pid)
        if pid in data:
            data[pid]['nom'] = nom
            data[pid]['prix'] = float(prix)
            data[pid]['quantite'] = int(qte)
            sauver_inventaire()
            logging.info(f"INVENTAIRE: Mise a jour produit #{pid} {nom}")
            return True
        return False

    def process_cart(self, cart_items, client_name):
        # 1. Validation des stocks
        for item in cart_items:
            pid = int(item['id'])
            qte_demandee = int(item['qte'])
            if pid not in data:
                return {"success": False, "message": f"Erreur: Produit ID {pid} introuvable."}
            if qte_demandee > data[pid]['quantite']:
                 return {"success": False, "message": f"Stock insuffisant pour {item['nom']} (Stock: {data[pid]['quantite']})"}

        # 2. Génération d'un ID de transaction UNIQUE pour ce panier
        transaction_id = str(uuid.uuid4())[:8]

        # 3. Traitement
        for item in cart_items:
            pid = int(item['id'])
            qte_demandee = int(item['qte'])
            
            data[pid]['quantite'] -= qte_demandee
            # On passe le transaction_id à l'enregistrement
            enregistrer_vente(pid, data[pid]['nom'], data[pid]['prix'], qte_demandee, client_name, transaction_id)
        
        sauver_inventaire()
        return {"success": True, "message": "Commande validée avec succès !"}

    def get_stats_data(self):
        ca_total = 0.0
        volume_total = 0
        ventes_par_produit = Counter()
        ventes_par_jour = defaultdict(float)
        
        if os.path.exists(fichier_ventes):
            with open(fichier_ventes, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    qte = int(row['qte'])
                    total_ligne = float(row['total'])
                    date = row['date']
                    nom = row['nom']
                    
                    ca_total += total_ligne
                    volume_total += qte
                    ventes_par_produit[nom] += qte
                    ventes_par_jour[date] += total_ligne

        dates_labels = []
        valeurs_data = []
        today = datetime.now()
        for i in range(6, -1, -1):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            dates_labels.append(d)
            valeurs_data.append(ventes_par_jour.get(d, 0.0))

        top_5 = ventes_par_produit.most_common(5)
        top_noms = [x[0] for x in top_5]
        top_qtes = [x[1] for x in top_5]
        marge_estimee = ca_total * 0.30

        return {
            "ca_total": f"{ca_total:.2f}",
            "marge_estimee": f"{marge_estimee:.2f}",
            "volume_ventes": volume_total,
            "nb_users": len(users_db),
            "evol_dates": dates_labels,
            "evol_valeurs": valeurs_data,
            "top_noms": top_noms,
            "top_qtes": top_qtes
        }

    # MODIFICATION MAJEURE ICI : Regroupement par TID
    def get_sales_history(self):
        grouped_history = {}
        
        if os.path.exists(fichier_ventes):
            with open(fichier_ventes, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    # On utilise le TID comme clé de regroupement
                    tid = row.get('tid', 'unknown')
                    
                    if tid not in grouped_history:
                        grouped_history[tid] = {
                            'date': row['date'],
                            'client': row['client'],
                            'total': 0.0,
                            'items_list': []
                        }
                    
                    # On ajoute les infos de la ligne au groupe
                    grouped_history[tid]['total'] += float(row['total'])
                    grouped_history[tid]['items_list'].append(f"{row['nom']} (x{row['qte']})")
        
        # Transformation du dictionnaire en liste propre pour l'affichage
        final_list = []
        for tid, data in grouped_history.items():
            final_list.append({
                'date': data['date'],
                'client': data['client'],
                'total': data['total'],
                'items': ", ".join(data['items_list']) # On crée une belle chaîne de caractères
            })
            
        return final_list[::-1] # Plus récents en premier

if __name__ == "__main__":
    charger_users()
    charger_inventaire()
    api = Api()
    window = webview.create_window(
        title='SaaS Analytics & Stock',
        html=html_content,
        js_api=api,
        width=1200,
        height=850,
        background_color='#121212'
    )
    webview.start() 