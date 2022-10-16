# Generated by Django 4.1.1 on 2022-09-11 09:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Device",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("ipv4", models.GenericIPAddressField(protocol="IPv4")),
                ("mac_addr", models.CharField(max_length=17)),
                ("name", models.CharField(max_length=20)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("SM", "smartphone"),
                            ("LP", "laptop"),
                            ("PC", "personal computer"),
                            ("WT", "watch"),
                            ("RT", "router"),
                        ],
                        max_length=2,
                    ),
                ),
                ("use_icmp", models.BooleanField(default=True)),
                ("use_tcp", models.BooleanField(default=False)),
                ("failed_ping_cycles", models.IntegerField(default=0)),
                ("failed_ping_cycles_threshold", models.IntegerField(default=2)),
            ],
        ),
        migrations.CreateModel(
            name="Network",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("ssid", models.CharField(max_length=20, unique=True)),
                ("description", models.CharField(max_length=50)),
                (
                    "type",
                    models.CharField(
                        choices=[("W", "wi-fi"), ("L", "lan")], max_length=1
                    ),
                ),
                (
                    "known_devices",
                    models.ManyToManyField(
                        related_name="known_networks", to="collector.device"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TelegramAccount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("telegram_id", models.IntegerField()),
                ("nickname", models.CharField(max_length=30)),
                (
                    "devices_to_track",
                    models.ManyToManyField(
                        related_name="subscribers", to="collector.device"
                    ),
                ),
                (
                    "networks_to_track",
                    models.ManyToManyField(
                        related_name="subscribers", to="collector.network"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Session",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("A", "active"),
                            ("P", "closed by ping"),
                            ("C", "closed by collector"),
                        ],
                        default="A",
                        max_length=1,
                    ),
                ),
                ("start", models.DateTimeField(auto_now=True)),
                ("end", models.DateTimeField(null=True)),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="session",
                        to="collector.device",
                    ),
                ),
                (
                    "network",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="session",
                        to="collector.network",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="DeviceOwner",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=30)),
                ("description", models.CharField(max_length=50)),
                (
                    "telegram_account",
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="collector.telegramaccount",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="device",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="collector.deviceowner"
            ),
        ),
        migrations.AddConstraint(
            model_name="device",
            constraint=models.CheckConstraint(
                check=models.Q(("use_icmp", models.F("use_tcp")), _negated=True),
                name="protocol_constraint",
            ),
        ),
    ]
