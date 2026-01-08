from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

import database
import auth
import models

app = FastAPI(title="SaaS Stock Manager API", version="1.0.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AUTH ENDPOINTS ---

@app.post("/api/auth/login", response_model=models.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    creds = database.get_user_credentials(form_data.username)
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not auth.verify_password(form_data.password, creds['salt'], creds['hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- PRODUCTS ENDPOINTS ---

@app.get("/api/products", response_model=List[models.Product])
def get_products(current_user: str = Depends(auth.get_current_user)):
    return database.get_all_products()

@app.get("/api/products/{product_id}", response_model=models.Product)
def get_product_detail(product_id: int, current_user: str= Depends(auth.get_current_user),dependencies=[oauth2_scheme]):
    product = database.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/api/products", response_model=models.Product)
def create_product(product: models.ProductCreate, current_user: str=Depends(auth.get_current_user),dependencies=[oauth2_scheme]):
    new_product = database.add_new_product(product.nom, product.prix, product.quantite)
    return new_product

@app.put("/api/products/{product_id}")
def update_product(product_id: int, product: models.ProductCreate, current_user: str= Depends(auth.get_current_user),dependencies=[oauth2_scheme]):
    success = database.update_product_data(product_id, product.nom, product.prix, product.quantite)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product updated successfully"}

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, current_user: str= Depends(auth.get_current_user),dependencies=[oauth2_scheme]):
    success = database.delete_product_data(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

# --- ORDERS ENDPOINTS ---

@app.post("/api/orders", response_model=models.OrderResponse)
def create_order(order: models.OrderCreate, current_user: str= Depends(auth.get_current_user),dependencies=[oauth2_scheme]):
    products = database.get_all_products()
    products_map = {p['id']: p for p in products}
    
    # Validation step
    final_items = []
    
    for item in order.items:
        if item.id not in products_map:
            raise HTTPException(status_code=400, detail=f"Product ID {item.id} not found")
        
        prod_in_stock = products_map[item.id]
        if item.qte > prod_in_stock['quantite']:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {prod_in_stock['nom']}")
            
        final_items.append({
            "id": item.id,
            "nom": prod_in_stock['nom'],
            "prix": prod_in_stock['prix'],
            "qte": item.qte
        })

    # Execution step (Stock deduction)
    for item in final_items:
        prod_in_stock = products_map[item['id']]
        # Update stock in memory map
        prod_in_stock['quantite'] -= item['qte']
        # Update in DB
        database.update_product_data(item['id'], prod_in_stock['nom'], prod_in_stock['prix'], prod_in_stock['quantite'])
    
    # Record transaction
    tid = database.record_sale_transaction(final_items, order.client)
    
    return {"success": True, "message": "Order processed successfully", "transaction_id": tid}

@app.get("/api/orders", response_model=List[dict])
def get_orders(current_user: str = Depends(auth.get_current_user),dependencies=[oauth2_scheme]):
    # Simple aggregation for order history list
    raw_sales = database.get_raw_stats()
    grouped = defaultdict(lambda: {'total': 0, 'items': [], 'date': '', 'client': ''})
    
    for row in raw_sales:
        tid = row['tid']
        grouped[tid]['date'] = row['date']
        grouped[tid]['client'] = row['client']
        grouped[tid]['total'] += float(row['total'])
        grouped[tid]['items'].append(f"{row['nom']} (x{row['qte']})")
    
    result = []
    for tid, data in grouped.items():
        result.append({
            "tid": tid,
            "date": data['date'],
            "client": data['client'],
            "total": round(data['total'], 2),
            "items": ", ".join(data['items'])
        })
    return sorted(result, key=lambda x: x['date'], reverse=True)


# --- STATS ENDPOINT ---

@app.get("/api/stats")
def get_stats(current_user: str = Depends(auth.get_current_user),dependencies=[oauth2_scheme]):
    raw_sales = database.get_raw_stats()
    
    ca_total = 0.0
    volume_total = 0
    ventes_par_produit = Counter()
    ventes_par_jour = defaultdict(float)
    
    for row in raw_sales:
        qte = int(row['qte'])
        total_ligne = float(row['total'])
        date = row['date']
        nom = row['nom']
        
        ca_total += total_ligne
        volume_total += qte
        ventes_par_produit[nom] += qte
        ventes_par_jour[date] += total_ligne

    today = datetime.now()
    dates_labels = []
    valeurs_data = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        dates_labels.append(d)
        valeurs_data.append(ventes_par_jour.get(d, 0.0))
        
    top_5 = ventes_par_produit.most_common(5)
    
    return {
        "ca_total": round(ca_total, 2),
        "marge_estimee": round(ca_total * 0.30, 2),
        "volume_ventes": volume_total,
        "evol": {
            "dates": dates_labels,
            "valeurs": valeurs_data
        },
        "top_products": [{"nom": x[0], "qte": x[1]} for x in top_5]
    }
