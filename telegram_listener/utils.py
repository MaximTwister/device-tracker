from datetime import datetime

from requests import Response
from telebot.types import (
    Message,
    InlineKeyboardButton, CallbackQuery, InlineKeyboardMarkup,
)

from pinger.sender import get_url, send_data
from telegram_listener.constants import (
    DEVICE_ICONS,
    PLUS_SIGN,
    HEADERS,
)


def prepare_kb(network_ssid: str, devices: list, edit_mode: bool) -> InlineKeyboardMarkup:
    print(f"create kb for {devices} - edit mode is {edit_mode}")
    row_width_map = {True: 2, False: 1}
    kb = InlineKeyboardMarkup(row_width=row_width_map[edit_mode])

    for device in devices:
        row_buttons = []
        device_status = get_device_status(device.get("missed_pings"))
        last_modified = get_device_last_modified(device.get("last_modified"))
        name = device.get("name")
        device_icon = DEVICE_ICONS.get(device.get("device_type"))
        device_id = device.get("id")
        is_followed_by_user = device.get("is_followed_by_user")

        text = f"{device_icon} {name} is {device_status} - {last_modified}"
        device_btn = InlineKeyboardButton(text=text, callback_data=f"device_{device_id}")

        if not edit_mode:
            if is_followed_by_user:
                row_buttons.append(device_btn)

        elif edit_mode:
            row_buttons.append(device_btn)

            if is_followed_by_user:
                unfollow_btn = InlineKeyboardButton(
                    text="Unfollow",
                    callback_data=f"unfollow_dev_{device_id}{PLUS_SIGN}{network_ssid}"
                )
                row_buttons.append(unfollow_btn)

            else:
                follow_btn = InlineKeyboardButton(
                    text="Follow",
                    callback_data=f"follow_dev_{device_id}{PLUS_SIGN}{network_ssid}"
                )
                row_buttons.append(follow_btn)

        kb.add(*row_buttons)

    return kb


def create_edit_mode_btn(network_ssid):
    return InlineKeyboardButton(
        text=f"[{network_ssid}] Edit devices",
        callback_data=f"edit_devices_{network_ssid}",
    )


def create_view_mode_btn(network_ssid):
    return InlineKeyboardButton(
        text=f"[{network_ssid}] Leave edit mode",
        callback_data=f"view_devices_{network_ssid}",
    )


def parse_message(message: Message):
    network_ssid = message.text.strip()
    user_id = message.from_user.id
    chat_id = message.chat.id
    return network_ssid, user_id, chat_id


def parse_callback(message: CallbackQuery):
    data = message.data.strip()
    for prefix in ["edit_devices_", "view_devices_"]:
        data = data.replace(prefix, "")
    network_ssid = data
    user_id = message.from_user.id
    chat_id = user_id
    return network_ssid, user_id, chat_id


def send_initial_message(bot, msg_data, data):
    msg: Message = bot.send_message(**msg_data)
    data.update({"telegram_msg_id": msg.message_id, "telegram_chat_id": msg.chat.id})
    url = get_url("register-message")
    res: Response = send_data(url=url, data=data, headers=HEADERS, http_method="post")
    print(f"{url} response: {res.json()}")


def follow_unfollow_device(cq: CallbackQuery, prefix: str, is_follow: bool):
    url = get_url(endpoint="device-follow")
    cleaned_data = cq.data.strip(prefix)
    print(f"follow/unfollow cleaned date: {cleaned_data}")
    device_id, network_id = cleaned_data.split(PLUS_SIGN)
    data = {
        "telegram_user_id": cq.from_user.id,
        "device_id": device_id,
        "is_follow": is_follow,
    }
    res: Response = send_data(url=url, data=data, headers=HEADERS, http_method="post")
    print(f"{prefix}device: {device_id}, response: {res.json()}")
    cq.data = network_id
    return cq


def get_device_status(missed_pings):
    return "Up" if missed_pings == 0 else "Degraded"


def get_device_last_modified(date_time: str) -> str:
    print(f"date from django: {date_time}")
    date_time = date_time.split(".")[0].replace("T", " ")
    date_time_object = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
    date_time = date_time_object.strftime("%d.%m.%y %H:%M")
    return date_time
