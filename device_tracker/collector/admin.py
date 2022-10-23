from django.contrib import admin

from collector.models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["ipv4", "mac_addr", "name", "type", "owner"]
