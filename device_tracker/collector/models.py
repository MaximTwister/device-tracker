from django.db import models
from django.db.models import CheckConstraint, Q, F

from collector.constants import NETWORK_KEY_LENGTH


class TelegramAccount(models.Model):
    telegram_user_id = models.IntegerField()
    nickname = models.CharField(max_length=30)
    owner = models.OneToOneField(
        to="auth.User",
        related_name="telegram_account",
        on_delete=models.CASCADE,
    )
    chats = models.ManyToManyField(to="TelegramChat", related_name="users")
    devices_to_track = models.ManyToManyField(to="Device", related_name="subscribers")
    networks_to_track = models.ManyToManyField(to="Network", related_name="subscribers")
    networks_to_admin = models.ManyToManyField(to="Network", related_name="admins")


class TelegramMessage(models.Model):
    telegram_msg_id = models.IntegerField()
    telegram_chat = models.ForeignKey(
        to="TelegramChat",
        related_name="view_network_messages",
        on_delete=models.CASCADE,
    )
    telegram_account = models.ForeignKey(
        to="TelegramAccount",
        related_name="view_network_messages",
        on_delete=models.CASCADE,
    )
    network = models.ForeignKey(
        to="Network",
        related_name="view_network_messages",
        on_delete=models.CASCADE,
    )


class TelegramChat(models.Model):
    telegram_chat_id = models.IntegerField()


class Network(models.Model):

    class NetworkTypes(models.TextChoices):
        # value, label
        WIFI = "W", "wi-fi"
        LAN = "L", "lan"

    ssid = models.CharField(max_length=20, unique=True)
    network_key = models.CharField(max_length=NETWORK_KEY_LENGTH, unique=True)
    description = models.CharField(max_length=50)
    type = models.CharField(max_length=1, choices=NetworkTypes.choices)
    known_devices = models.ManyToManyField(to="Device", related_name="known_networks")
    added_by = models.ForeignKey(
        to="auth.User",
        related_name="added_networks",
        on_delete=models.SET_NULL,
        null=True,
    )


class Session(models.Model):

    class StatusTypes(models.TextChoices):
        ACTIVE = "A", "active"
        CLOSED = "C", "closed"
        CLOSED_FORCIBLY = "F", "closed forcibly"

    network = models.ForeignKey(
        to="Network",
        related_name="sessions",
        on_delete=models.CASCADE,
    )
    device = models.ForeignKey(
        to="Device",
        related_name="sessions",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=1,
        choices=StatusTypes.choices,
        default=StatusTypes.ACTIVE,
    )
    start = models.DateTimeField(auto_now=True)
    end = models.DateTimeField(null=True)

    #
    # 1. We receive info from pinger {network: HomeWiFi, mac_addr: <>}
    # 2. [table Device] -> Device.objects.get(mac_addr=mac_addr) -> get device_model
    # 3. [table Network] -> Device.objects.get(ssid=HomeWiFi) -> get network_model
    # 4. [table Sessions] -> Device.objects.get(
    #                                  network=network_model
    #                                  device=device_model
    #                                  status = ACTIVE
    #                                  ) -> session_model -> NOTHING TO DO
    #


class Device(models.Model):

    class DeviceTypes(models.TextChoices):
        SMARTPHONE = "SM", "smartphone"
        TV = "TV", "tv"
        TABLET = "TB", "tablet"
        LAPTOP = "LP", "laptop"
        PC = "PC", "personal computer"
        WATCH = "WT", "watch"
        ROUTER = "RT", "router"

    ipv4 = models.GenericIPAddressField(protocol="IPv4")
    mac_addr = models.CharField(max_length=17, unique=True)
    name = models.CharField(max_length=20)
    type = models.CharField(max_length=2, choices=DeviceTypes.choices)
    owner = models.ForeignKey(
        to="auth.User",
        related_name="devices",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    use_icmp = models.BooleanField(default=True)
    use_tcp = models.BooleanField(default=False)
    missed_pings = models.IntegerField(default=0)
    missed_pings_threshold = models.IntegerField(default=2)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            CheckConstraint(check=~Q(use_icmp=F("use_tcp")), name="protocol_constraint")
        ]
