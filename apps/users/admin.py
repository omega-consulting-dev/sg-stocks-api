from django.contrib import admin

from apps.users.models import User 

class UserAdmin(admin.ModelAdmin):
    list_display = ('pk', 'username', 'email', 'is_staff', 'is_active')

admin.site.register(User, UserAdmin)
