from string import ascii_uppercase, digits
from random import choices
from datetime import datetime

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.utils import timezone

from collector.constants import (
    NETWORK_KEY_LENGTH,
    UPDATE_NETWORK_STATUS_ENDPOINT,
)
from collector.models import (
    Network,
    Device,
    Session,
    TelegramAccount,
    TelegramChat,
    TelegramMessage,
)


def get_or_create_device(mac_addr, ipv4):

    try:
        device = Device.objects.get(mac_addr=mac_addr)
        device.ipv4 = ipv4
        device.save()
    except ObjectDoesNotExist:
        device = Device.objects.create(mac_addr=mac_addr, ipv4=ipv4)
        print(f"new device was created: {device}")

    return device


def maintain_device_sessions(ssid, device):
    now = datetime.now(tz=timezone.utc)
    network = Network.objects.get(ssid=ssid)

    active_sessions = device.sessions.filter(status="A")
    active_sessions.exclude(network=network).update(end=now, status="F")

    try:
        active_session_current_ssid = active_sessions.get(network=network)
        print(f"{device} has active session for `{ssid}`: {active_session_current_ssid}")
    except ObjectDoesNotExist:
        session_data = {"network": network, "device": device}
        active_session_current_ssid = Session.objects.create(**session_data)
        print(f"session for device:{device} in network:{network} "
              f"was created:{active_session_current_ssid}")


def maintain_missed_pings(ssid: str, live_mac_addresses: list):
    network = Network.objects.get(ssid=ssid)
    query = {"sessions__network": network, "sessions__status": "A"}
    devices = Device.objects.filter(**query)

    (devices.exclude(mac_addr__in=live_mac_addresses).
     update(missed_pings=F("missed_pings") + 1))

    devices.filter(mac_addr__in=live_mac_addresses).update(missed_pings=0)
    lost_devices = devices.filter(missed_pings__gt=F("missed_pings_threshold"))
    Session.objects.filter(device__in=lost_devices).update(status="C")
    lost_devices.update(missed_pings=0)


def verify_telegram_account(data, user):
    print(f"`get_telegram_account_status` data: {data}")
    telegram_user_id = data.get("telegram_user_id")
    telegram_chat_id = data.get("chat")
    nickname = data.get("nickname")

    try:
        TelegramAccount.objects.get(telegram_user_id=telegram_user_id)
        return "exist"
    except ObjectDoesNotExist:
        data = {"telegram_user_id": telegram_user_id, "nickname": nickname, "owner": user}
        acc = TelegramAccount.objects.create(**data)

        if telegram_chat_id != telegram_user_id:
            chat = TelegramChat.objects.create(telegram_chat_id=telegram_chat_id)
            acc.chats.add(chat)
        return "created"


def get_network_key():
    try_counter = 0
    try_counter_threshold = 100
    key = None

    while try_counter < try_counter_threshold:
        symbols = choices(ascii_uppercase + digits, k=NETWORK_KEY_LENGTH)
        try_key = ''.join(symbols)

        if Network.objects.filter(network_key=try_key).exists():
            try_counter += 1
        else:
            key = try_key
            break

    print(f"network key generated: {key}")
    return key


def notify_network_subscribers(ssid):
    network = Network.objects.get(ssid=ssid)
    subscribed_telegram_accounts = network.subscribers
    print(f"network: {network} has subscribers: {subscribed_telegram_accounts.all()}")
    for subscribed_telegram_account in subscribed_telegram_accounts.all():
        subscribed_devices = subscribed_telegram_account.devices_to_track.filter(
            sessions__network__ssid=ssid,
            sessions__status="A",
        )
        print(f"{subscribed_telegram_account} subscribed for devices: {subscribed_devices}")

        if subscribed_devices.exists():
            telegram_messages = TelegramMessage.objects.filter(
                telegram_account=subscribed_telegram_account,
                network=network,
            )
            print(f"{subscribed_telegram_account} has {network} messages: {telegram_messages}")
            for msg in telegram_messages:
                notify(msg.telegram_chat.telegram_chat_id, ssid)


def notify(chat_id, network_ssid):
    data = {"chat_id": chat_id, "network_ssid": network_ssid}
    response = requests.post(url=UPDATE_NETWORK_STATUS_ENDPOINT, json=data)
    print(f"{UPDATE_NETWORK_STATUS_ENDPOINT} response: {response}")


def get_telegram_msg_for_network(telegram_id, network_ssid):
    try:
        telegram_msg_id = TelegramMessage.objects.get(
            telegram_account__telegram_user_id=telegram_id,
            network__ssid=network_ssid,
        ).telegram_msg_id
    except ObjectDoesNotExist:
        telegram_msg_id = 0

    return telegram_msg_id
