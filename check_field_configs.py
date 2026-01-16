#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.config')
django.setup()

from core.models import FieldConfiguration

print(f"Total configurations: {FieldConfiguration.objects.count()}")
print("\nConfigurations par formulaire:")
print("-" * 60)

for form_choice in ['product', 'customer', 'supplier']:
    configs = FieldConfiguration.objects.filter(form_name=form_choice)
    print(f"\n{form_choice.upper()}: {configs.count()} champs")
    for config in configs:
        visible = "✓" if config.is_visible else "✗"
        required = "✓" if config.is_required else "✗"
        print(f"  - {config.field_name:20s} | Visible: {visible} | Obligatoire: {required}")
