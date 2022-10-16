from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from collector.models import (
    Network,
    TelegramAccount,
    Device,
)
from collector.serializers import (
    NetworkSerializer,
    UpdateCreateSessionSerializer,
    TelegramAccountSerializer,
    NetworkDevicesSerializer,
    RegisterMessageSerializer,
    DeviceFollowSerializer,
)
from collector.utils import (
    get_or_create_device,
    maintain_device_sessions,
    maintain_missed_pings,
    notify_device_statuses,
    get_telegram_account_status,
    get_telegram_msg_for_network,
)


class NetworkView(APIView):

    def post(self, request):
        serializer = NetworkSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(
            data=serializer.errors,
            status=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class UpdateCreateSessionView(APIView):

    def post(self, request: Request):
        print(f"Request: {request.data}")
        serializer = UpdateCreateSessionSerializer(data=request.data, many=True)

        if serializer.is_valid():
            live_mac_addresses = []
            ssid = ""

            for data in serializer.data:
                mac_addr = data.get("device_mac_addr")
                ipv4 = data.get("device_ipv4_addr")
                ssid = data.get("network_ssid")

                device = get_or_create_device(mac_addr, ipv4)
                maintain_device_sessions(ssid, device)
                live_mac_addresses.append(mac_addr)

            maintain_missed_pings(ssid, live_mac_addresses)
            notify_device_statuses(ssid, live_mac_addresses)

            return Response(data=serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TelegramAccountView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request: Request):

        user = Token.objects.get(key=request.auth.key).user
        print(f"user was found: {user}")
        serializer = TelegramAccountSerializer(data=request.data)
        if serializer.is_valid():
            account_status = get_telegram_account_status(serializer.data, user)
            data = {"account_status": account_status}
            return Response(data=data, status=status.HTTP_200_OK)

        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubscribeNetworkView(APIView):

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request: Request):

        network_key = request.data.get("network_key")
        telegram_user_id = request.data.get("telegram_user_id")

        try:
            network = Network.objects.get(network_key=network_key)
            acc = TelegramAccount.objects.get(telegram_user_id=telegram_user_id)
        except ObjectDoesNotExist:
            data = {"msg": "no such network key or telegram account"}
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        else:
            network.subscribers.add(acc)
            data = {"msg": f"{acc.nickname} added as {network.ssid} network subscriber"}
            return Response(data=data, status=status.HTTP_200_OK)


class NetworkDevicesView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request: Request):
        print(f"NetworkDevicesView request data: {request.data}")
        ssid = request.data.get("network_ssid")
        telegram_id = request.data.get("telegram_user_id")
        devices = (
            Device.objects.filter(sessions__status="A", sessions__network__ssid=ssid)
        )
        print(f"NetworkDevicesView found devices: {devices}")
        context = {"telegram_id": telegram_id}
        telegram_msg_id = get_telegram_msg_for_network(
            telegram_id=telegram_id,
            network_ssid=ssid
        )
        serializer = NetworkDevicesSerializer(devices, many=True, context=context)
        data = {"devices": serializer.data, "telegram_msg_id": telegram_msg_id}
        return Response(data=data, status=status.HTTP_200_OK)


class RegisterMessageView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request: Request):
        serializer = RegisterMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeviceFollowView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request: Request):
        serializer = DeviceFollowSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
