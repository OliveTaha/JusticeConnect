from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Account, Client, Lawyer, Profile


@admin.register(Account)
class AccountAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_verified")
    list_filter = ("role", "is_verified")
    actions = ["verify_selected"]
    # show our extra fields on the edit page
    fieldsets = UserAdmin.fieldsets + (("Justice Connect", {"fields": ("role", "is_verified")}),)

    @admin.action(description="Verify selected accounts")
    def verify_selected(self, request, queryset):
        for account in queryset:
            account.verify_account()


admin.site.register(Client)
admin.site.register(Lawyer)
admin.site.register(Profile)
