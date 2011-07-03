from django.contrib import admin

from linguo.tests.models import Bar


class BarAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'quantity', 'description',)
    list_filter = ('name',)
    search_fields = ('name', 'description',)


admin.site.register(Bar, BarAdmin)
