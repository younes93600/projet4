import csv
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

# Configuration
FICHIER_CSV = 'inventaire.csv'
FICHIER_USERS = 'utilisateurs.csv'
FICHIER_VENTES = 'ventes.csv'
FICHIER_LOG = 'security.log'

logging.basicConfig(filename=FICHIER_LOG, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- USERS ---

def get_user_credentials(username: str) -> Optional[Dict[str, str]]:
    if not os.path.exists(FICHIER_USERS):
        return None
    
    try:
        with open(FICHIER_USERS, "r", newline="", encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                if row['username'] == username:
                    return {'salt': row['salt'], 'hash': row['hash']}
    except Exception as e:
        print(f"Error reading users: {e}")
    return None

# --- INVENTORY ---

def get_all_products() -> List[Dict]:
    products = []
    if not os.path.exists(FICHIER_CSV):
        return products
    
    try:
        with open(FICHIER_CSV, "r", newline="", encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                products.append({
                    "id": int(row["id"]),
                    "nom": row["nom"],
                    "prix": float(row["prix"]),
                    "quantite": int(row["quantite"])
                })
    except Exception as e:
        print(f"Error reading inventory: {e}")
    return sorted(products, key=lambda x: x['id'])

def get_product(product_id: int) -> Optional[Dict]:
    products = get_all_products()
    for p in products:
        if p['id'] == product_id:
            return p
    return None

def save_all_products(products: List[Dict]):
    try:
        with open(FICHIER_CSV, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'nom', 'prix', 'quantite']
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            for p in products:
                writer.writerow(p)
    except Exception as e:
        logging.error(f"SYSTEM: Error saving inventory - {e}")

def add_new_product(nom: str, prix: float, quantite: int):
    products = get_all_products()
    max_id = max([p['id'] for p in products]) if products else 0
    new_id = max_id + 1
    new_prod = {"id": new_id, "nom": nom, "prix": prix, "quantite": quantite}
    products.append(new_prod)
    save_all_products(products)
    logging.info(f"INVENTAIRE: Ajout produit #{new_id} {nom}")
    return new_prod

def update_product_data(product_id: int, nom: str, prix: float, quantite: int):
    products = get_all_products()
    found = False
    for p in products:
        if p['id'] == product_id:
            p['nom'] = nom
            p['prix'] = prix
            p['quantite'] = quantite
            found = True
            break
    
    if found:
        save_all_products(products)
        logging.info(f"INVENTAIRE: Update produit #{product_id}")
        return True
    return False

def delete_product_data(product_id: int):
    products = get_all_products()
    new_products = [p for p in products if p['id'] != product_id]
    if len(new_products) < len(products):
        save_all_products(new_products)
        logging.info(f"INVENTAIRE: Delete produit #{product_id}")
        return True
    return False

# --- SALES ---

def record_sale_transaction(items: List[Dict], client_name: str) -> str:
    transaction_id = str(uuid.uuid4())[:8]
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    is_empty = not os.path.exists(FICHIER_VENTES) or os.stat(FICHIER_VENTES).st_size == 0
    fieldnames = ['date', 'tid', 'id_prod', 'nom', 'prix', 'qte', 'total', 'client']
    
    try:
        with open(FICHIER_VENTES, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            if is_empty: writer.writeheader()
            
            for item in items:
                total = item['prix'] * item['qte']
                writer.writerow({
                    'date': date_str,
                    'tid': transaction_id,
                    'id_prod': item['id'],
                    'nom': item['nom'],
                    'prix': item['prix'],
                    'qte': item['qte'],
                    'total': total,
                    'client': client_name
                })
    except Exception as e:
        logging.error(f"SYSTEM: Error recording sale - {e}")
        
    return transaction_id

def get_raw_stats():
    # Helper to read raw sales data for stats endpoint
    sales = []
    if os.path.exists(FICHIER_VENTES):
        with open(FICHIER_VENTES, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                sales.append(row)
    return sales
