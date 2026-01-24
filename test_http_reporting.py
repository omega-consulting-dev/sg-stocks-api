import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"
USERNAME = "admin@agribio.com"  # Ajustez selon votre admin
PASSWORD = "Admin123!"  # Ajustez selon votre password

# Login
login_url = f"{BASE_URL}/accounts/api/login/"
 
# Headers avec le hostname pour le tenant
tenant_headers = {
    "Host": "agribio.localhost:8000"
}
login_data = {
    "email": USERNAME,
    "password": PASSWORD
}

print("=" * 80)
print("TEST DE L'API REPORTING")
print("=" * 80)

try:
    # Login
    print(f"\n1. Connexion à {login_url}...")
    response = requests.post(login_url, json=login_data, headers=tenant_headers)
    if response.status_code == 200:
        token = response.json().get('access')
        print(f"✓ Connecté - Token: {token[:50]}...")
    else:
        print(f"✗ Erreur de connexion: {response.status_code}")
        print(response.text)
        exit(1)
    
    # Headers avec le token
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Host": "agribio.localhost:8000"
    }
    
    # Test reporting data
    print(f"\n2. Récupération des données de reporting...")
    reporting_url = f"{BASE_URL}/analytics/dashboard/generate-report-data/"
    
    # Dates pour le filtre (30 derniers jours)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    params = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }
    
    print(f"   Période: {params['start_date']} à {params['end_date']}")
    
    response = requests.get(reporting_url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print("\n" + "=" * 80)
        print("PRODUITS D'EXPLOITATION (Ventes)")
        print("=" * 80)
        
        sales = data.get('sales', [])
        for sale in sales:
            print(f"  {sale['category_name']:30} | Qté: {sale['count']:>6} | Montant: {sale['amount']:>15,.0f}")
        
        print("\n" + "=" * 80)
        print("CHARGES D'EXPLOITATION (Dépenses)")
        print("=" * 80)
        
        expenses = data.get('expenses', [])
        for expense in expenses:
            print(f"  {expense['category_name']:30} | Qté: {expense['count']:>6} | Montant: {expense['amount']:>15,.0f}")
        
        print("\n" + "=" * 80)
        print(f"Total Ventes: {data.get('total_sales', 0):,.0f} FCFA")
        print(f"Total Charges: {data.get('total_expenses', 0):,.0f} FCFA")
        print("=" * 80)
        
    else:
        print(f"✗ Erreur: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n✗ Erreur: {str(e)}")
    import traceback
    traceback.print_exc()
