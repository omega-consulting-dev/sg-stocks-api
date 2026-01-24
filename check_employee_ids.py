#!/usr/bin/env python
"""
Script pour lister tous les employee_id dans le tenant saker
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config.dev')
django.setup()

from django.db import connection
from apps.accounts.models import User

def check_employee_ids():
    schema_name = 'saker'
    connection.set_schema(schema_name)
    
    print(f"\n📋 Vérification des employee_id dans le tenant: {schema_name}\n")
    
    users = User.objects.all().order_by('employee_id')
    
    print(f"Nombre total d'utilisateurs: {users.count()}\n")
    
    for user in users:
        print(f"👤 {user.username:20} | employee_id: {user.employee_id or 'NULL':10} | Email: {user.email}")
    
    print(f"\n" + "="*80)
    
    # Vérifier les doublons
    from django.db.models import Count
    duplicates = User.objects.values('employee_id').annotate(
        count=Count('employee_id')
    ).filter(count__gt=1, employee_id__isnull=False)
    
    if duplicates.exists():
        print("\n⚠️  DOUBLONS DÉTECTÉS:")
        for dup in duplicates:
            print(f"   - {dup['employee_id']}: {dup['count']} fois")
            users_with_dup = User.objects.filter(employee_id=dup['employee_id'])
            for u in users_with_dup:
                print(f"      * {u.username} (ID: {u.id})")
    else:
        print("\n✅ Aucun doublon détecté")

if __name__ == '__main__':
    check_employee_ids()
