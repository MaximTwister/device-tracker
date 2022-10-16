from django.urls import path
from collector.views import (
    NetworkView,
    UpdateCreateSessionView,
    TelegramAccountView,
    SubscribeNetworkView,
    NetworkDevicesView,
    RegisterMessageView,
    DeviceFollowView,
)


urlpatterns = [
    path("networks/", NetworkView.as_view(), name="network_view"),
    path("device-sessions/", UpdateCreateSessionView.as_view(), name="device_sessions"),
    path("telegram-account/", TelegramAccountView.as_view(), name="telegram_account"),
    path("subscribe-network/", SubscribeNetworkView.as_view(), name="subscribe_network"),
    path("manage-network-devices/", NetworkDevicesView.as_view(), name="network_devices"),
    path("register-message/", RegisterMessageView.as_view(), name="register_message"),
    path("device-follow/", DeviceFollowView.as_view(), name="device_follow"),
]
