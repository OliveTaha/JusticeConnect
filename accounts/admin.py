from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Account, Client, Lawyer, Profile




admin.site.register(Client)
