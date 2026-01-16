#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from apps.tenants.models import Company

companies = Company.objects.all()
print(f'Tenants disponibles ({companies.count()}):')
for c in companies:
    domains = c.domains.all()
    domain_str = ', '.join([d.domain for d in domains])
    print(f'  - {c.name:20s} | schema: {c.schema_name:15s} | domains: {domain_str}')
