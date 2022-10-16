from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from collector.models import (
    Network,
    Session,
    TelegramAccount, Device, TelegramMessage, TelegramChat,
)
from collector.utils import get_network_key


class NetworkSerializer(serializers.ModelSerializer):

    class Meta:
        model = Network
        read_only_fields = ["network_key"]
        fields = ["ssid", "description", "type", "network_key"]

    def to_internal_value(self, data):
        print(f"network serializer `to_internal_value` input data: {data}")
        internal_data = super().to_internal_value(data)
        network_key = get_network_key()
        if not network_key:
            raise ValidationError({"error": "network_key was not generated"})
        internal_data["network_key"] = network_key
        print(f"network serializer `to_internal_value` output data: {internal_data}")
        return internal_data


class UpdateCreateSessionSerializer(serializers.ModelSerializer):
    device_mac_addr = serializers.CharField(source="device.mac_addr")
    device_ipv4_addr = serializers.IPAddressField(source="device.ipv4")
    network_ssid = serializers.CharField(source="network.ssid")

    class Meta:
        model = Session
        fields = ["device_mac_addr", "device_ipv4_addr", "network_ssid"]

    def validate_network_ssid(self, value):
        if Network.objects.filter(ssid=value).exists():
            return value
        else:
            err = f"ssid: {value} does not exist - create it firstly"
            print(err)
            raise serializers.ValidationError(err)


class TelegramAccountSerializer(serializers.ModelSerializer):
    chat = serializers.IntegerField(source="chats.telegram_chat_id")

    class Meta:
        model = TelegramAccount
        fields = ["telegram_user_id", "nickname", "chat"]


class NetworkDevicesSerializer(serializers.ModelSerializer):
    # will find method with name -> `get_{variable_name}`
    is_followed_by_user = serializers.SerializerMethodField()

    class Meta:
        fields = [
            "id",
            "type",
            "name",
            "missed_pings",
            "last_modified",
            "is_followed_by_user",
        ]
        model = Device

    def get_is_followed_by_user(self, device: Device) -> bool:
        telegram_acc = (
            TelegramAccount.objects.get(
                telegram_user_id=self.context.get("telegram_id")
            )
        )
        return telegram_acc in device.subscribers.all()


class RegisterMessageSerializer(serializers.ModelSerializer):
    telegram_user_id = serializers.IntegerField(source="telegram_account.telegram_user_id")
    network_ssid = serializers.IntegerField(source="network.ssid")
    telegram_chat_id = serializers.IntegerField(source="telegram_chat.telegram_chat_id")

    class Meta:
        model = TelegramMessage
        fields = [
            "telegram_msg_id",
            "telegram_user_id",
            "network_ssid",
            "telegram_chat_id",
        ]

    def validate(self, data):
        print(f"RegisterMessageSerializer `validate()` initial data: {data}")
        telegram_user_id = data["telegram_account"]["telegram_user_id"]
        network_ssid = data["network"]["ssid"]

        stale_message_ids = TelegramMessage.objects.filter(
            telegram_account__telegram_user_id=telegram_user_id,
            network__ssid=network_ssid,
        )
        if stale_message_ids.exists():
            print(f"RegisterMessageSerializer delete stale messages: {stale_message_ids}")
            stale_message_ids.delete()

        return data

    def create(self, validated_data):
        print(f"RegisterMessageSerializer `create()` validated_data: {validated_data}")
        telegram_account_query = validated_data.get("telegram_account")
        network_query = validated_data.get("network")
        telegram_chat_query = validated_data.get("telegram_chat")

        try:
            telegram_chat = TelegramChat.objects.get(**telegram_chat_query)
        except ObjectDoesNotExist:
            telegram_chat = TelegramChat.objects.create(**telegram_chat_query)

        validated_data["telegram_account"] = TelegramAccount.objects.get(**telegram_account_query)
        validated_data["network"] = Network.objects.get(**network_query)
        validated_data["telegram_chat"] = telegram_chat

        return super().create(validated_data)


class DeviceFollowSerializer(serializers.ModelSerializer):
    device_id = serializers.PrimaryKeyRelatedField(
        queryset=Device.objects.filter(),
        write_only=True,
    )
    is_follow = serializers.BooleanField(write_only=True)

    class Meta:
        model = TelegramAccount
        fields = ["telegram_user_id", "device_id", "is_follow"]

    def create(self, validated_data):
        print(f"DeviceFollowSerializer update/create device follow/unfollow"
              f" with validated_data: {validated_data}")

        telegram_user_id = validated_data.get("telegram_user_id")
        device = validated_data.get("device_id")
        is_follow = validated_data.get("is_follow")

        telegram_account = TelegramAccount.objects.get(telegram_user_id=telegram_user_id)

        if is_follow:
            telegram_account.devices_to_track.add(device)
        else:
            telegram_account.devices_to_track.remove(device)

        return telegram_account
