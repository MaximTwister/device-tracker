from threading import Thread
from typing import Union

from flask import (
    Flask,
    request,
    jsonify,
)
import telebot
from requests import Response
from telebot.apihelper import ApiTelegramException
from telebot.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    User,
    Chat,
)

from pinger.sender import get_url, send_data
from telegram_listener.constants import TELEGRAM_API_TOKEN, HEADERS
from telegram_listener.utils import (
    parse_message,
    parse_callback,
    create_edit_mode_btn,
    create_view_mode_btn,
    prepare_kb,
    send_initial_message,
    follow_unfollow_device,
)

bot = telebot.TeleBot(token=TELEGRAM_API_TOKEN)
app = Flask(__name__)

@app.route("/update-network-status", methods=["POST"])
def update_network_status():
    data = request.get_json()
    chat_id = data.get("chat_id")
    network_ssid = data.get("network_ssid")

    user = User(id=chat_id, first_name="", is_bot=False)
    chat = Chat(id=chat_id, type="")
    message = Message(
        message_id=0,
        chat=chat,
        from_user=user,
        content_type="",
        date="",
        json_string="",
        options=[],
    )
    message.text = network_ssid
    manage_network_devices(message=message, edit_mode=False)

    response_data = {
        "message": f"{network_ssid} devices statuses updated",
        "status_code": 200,
    }

    return jsonify(response_data)


@bot.message_handler(commands=["start"])
def start_handler(message: Message):
    data = {
        "telegram_user_id": message.from_user.id,
        "nickname": message.from_user.username,
        "chat": message.chat.id,
    }

    url = get_url(endpoint="telegram-account")
    res = send_data(url=url, data=data, headers=HEADERS)
    print(f"endpoint {url} response: {res.json()}")

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(
            text="Subscribe network",
            callback_data="subscribe_network"),
        InlineKeyboardButton(
            text="Network devices",
            callback_data="network_devices"),
    )

    bot.send_message(chat_id=message.chat.id, text="Options:", reply_markup=kb)


@bot.callback_query_handler(lambda call: call.data == "subscribe_network")
def subscribe_network_btn_handler(cq: CallbackQuery):
    text = "To subscribe network enter Network Secret Key."
    msg = bot.send_message(chat_id=cq.from_user.id, text=text)
    bot.register_next_step_handler(message=msg, callback=subscribe_network_handler)


@bot.callback_query_handler(lambda call: call.data == "network_devices")
def network_devices_btn_handler(cq: CallbackQuery):
    text = "To manage network devices enter subscribed Network SSID"
    msg = bot.send_message(chat_id=cq.from_user.id, text=text)
    bot.register_next_step_handler(message=msg, callback=manage_network_devices)


@bot.callback_query_handler(lambda call: call.data.startswith("edit_devices"))
def edit_devices_btn_handler(cq: CallbackQuery):
    manage_network_devices(message=cq, edit_mode=True)


@bot.callback_query_handler(lambda call: call.data.startswith("view_devices"))
def view_devices_btn_handler(cq: CallbackQuery):
    manage_network_devices(message=cq, edit_mode=False)


@bot.callback_query_handler(lambda call: call.data.startswith("follow_dev"))
def follow_devices_btn_handler(cq: CallbackQuery):
    cq = follow_unfollow_device(cq=cq, prefix="follow_dev", is_follow=True)
    manage_network_devices(message=cq, edit_mode=True)


@bot.callback_query_handler(lambda call: call.data.startswith("unfollow_dev"))
def unfollow_devices_btn_handler(cq: CallbackQuery):
    cq = follow_unfollow_device(cq=cq, prefix="unfollow_dev", is_follow=False)
    manage_network_devices(message=cq, edit_mode=True)


def subscribe_network_handler(message: Message):
    network_key = message.text.strip()
    data = {"network_key": network_key, "telegram_user_id": message.from_user.id}
    url = get_url(endpoint="subscribe-network")
    res = send_data(url=url, data=data, headers=HEADERS)
    msg = res.json().get("msg", "")
    bot.reply_to(message, msg)


def manage_network_devices(message: Union[Message, CallbackQuery], edit_mode=False):
    parser_map = {Message: parse_message, CallbackQuery: parse_callback}
    bottom_buttons_map = {True: create_view_mode_btn, False: create_edit_mode_btn}

    parser = parser_map[type(message)]
    create_bottom_button = bottom_buttons_map[edit_mode]

    network_ssid, user_id, chat_id = parser(message=message)

    data = {"network_ssid": network_ssid, "telegram_user_id": user_id}
    url = get_url(endpoint="manage-network-devices")
    res: Response = send_data(url=url, data=data, headers=HEADERS, http_method="get")
    res: dict = res.json()
    print(f"response from {url}: {res}")
    devices = res.get("devices")
    message_id = res.get("telegram_msg_id")

    kb = prepare_kb(network_ssid=network_ssid, devices=devices, edit_mode=edit_mode)
    bottom_btn = create_bottom_button(network_ssid=network_ssid)
    kb.add(bottom_btn)

    msg_data = {"chat_id": chat_id, "text": network_ssid, "reply_markup": kb}

    if message_id == 0:
        send_initial_message(bot, msg_data, data)
    else:
        try:
            bot.edit_message_text(message_id=message_id, **msg_data)
            print(f"message: {message_id} was edited in chat: {chat_id}")
        except ApiTelegramException as e:
            print(f"can not edit message: {message_id} - error: {e}")
            send_initial_message(bot, msg_data, data)


if __name__ == "__main__":
    print("bot is pooling ... ")
    Thread(target=bot.infinity_polling).start()

    print("flask is running ... ")
    Thread(target=app.run, kwargs={"host": "127.0.0.1", "port": 5000}).start()
