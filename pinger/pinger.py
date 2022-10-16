import argparse
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from ipaddress import IPv4Interface, IPv4Address, IPv4Network

import scapy.all as scapy
import tzlocal
from apscheduler.schedulers.background import BackgroundScheduler
from netifaces import ifaddresses, AF_INET
from pythonping import ping
from pythonping.executor import Response as PythonpingResponse
from pythonping.executor import ResponseList, Message
from requests import Response as RequestResponse
from scapy.layers.l2 import ARP, Ether
from scapy.plist import SndRcvList, PacketList, QueryAnswer

from sender import get_url, send_data


def get_nic_ip_address(nic):
    net_iface = ifaddresses(nic)
    ip = net_iface[AF_INET][0]['addr']
    print(f"local ip-address: {ip}")
    return ip


def get_network(ip_addr, prefix=24):
    print(f"getting network for: {ip_addr} with prefix: {prefix}")
    ip_addr_with_prefix = f"{ip_addr}/{prefix}"
    interface = IPv4Interface(ip_addr_with_prefix)
    return interface.network


def secure_ping(kwargs):

    def func():
        try:
            res: ResponseList = ping(**kwargs)
            print(kwargs, res.success())
            return res
        except OSError as e:
            print(f"error: {e} while pinging: {kwargs}")
            return ResponseList()

    return func


def run_pinger(count, timeout, interval, threads, ssid, nic):
    print("pinger started")
    ip_addr = get_nic_ip_address(nic)
    net: IPv4Network = get_network(ip_addr)
    management_ips = (
        IPv4Address(ip_addr),
        net.broadcast_address,
        net.network_address)
    print(f"scanning network {net} exclude {management_ips}")

    with ThreadPoolExecutor(max_workers=threads) as executor:
        start_time = time.perf_counter()
        futures = []
        for ip in net:
            if ip in management_ips:
                continue
            kwargs = {
                "target": str(ip),
                "timeout": timeout,
                "interval": interval,
                "count": count
            }
            func = secure_ping(kwargs)
            futures.append(executor.submit(func))
            time.sleep(0.1)

    all_results = [future.result() for future in futures]
    ok_results = [res for res in all_results if res.success()]

    interval = time.perf_counter() - start_time
    print(f"devices was found: {len(ok_results)} it takes {interval} sec")
    data: list = prepare_data_to_send(ok_results=ok_results, ssid=ssid)
    url = get_url(endpoint="device-sessions")
    res: RequestResponse = send_data(url, data)
    print(f"Response: {res.json()}")


def prepare_data_to_send(ok_results, ssid):
    data = []

    for result in ok_results:
        cycle_pings_amount = len(result._responses)
        result: ResponseList

        for ping_index in range(cycle_pings_amount):
            response: PythonpingResponse = result._responses[ping_index]
            print(f"{ping_index} result from responses: {response}")
            message: Message = response.message
            if message is None:
                continue
            ip = message.source

            mac_addr = get_mac(ip)

            if mac_addr is None:
                continue

            device_data = {
                "network_ssid": ssid,
                "device_mac_addr": mac_addr,
                "device_ipv4_addr": ip,
            }

            data.append(device_data)
            break

    print(f"data form prepare_data_to_send: {data}")
    return data


def get_mac(ip):

    # Create ARP packet object.
    # pdst - destination host ip-address
    arp_request = ARP(pdst=ip)

    # Create ethernet packet object.
    # dst - broadcast MAC address
    broadcast_request = Ether(dst="ff:ff:ff:ff:ff:ff")

    # Combine two packets into one (encapsulate)
    arp_broadcast_request = broadcast_request / arp_request

    data: tuple[SndRcvList, PacketList] = scapy.srp(
        arp_broadcast_request,
        timeout=1,
        verbose=None,
    )

    print(f"SndRcvList: {data[0]}")
    print(f"PacketList: {data[1]}")

    # in our case snd_rev_list has only one object inside
    snd_rev_list = data[0]
    if len(snd_rev_list) == 0:
        print(f"warning: can not get MAC for ip:{ip}")
        return None
    query_answer: QueryAnswer = snd_rev_list[0]
    ether: Ether = query_answer.answer
    print(f"MAC address for {ip}: {ether.hwsrc}")
    return ether.hwsrc


def parse_arguments():
    parser = argparse.ArgumentParser(description="Pinger script")
    parser.add_argument(
        "--ssid",
        type=str,
        dest="ssid",
        help="Network Service Set Identifier",
        required=True,
    )
    parser.add_argument(
        "--nic",
        type=str,
        dest="nic",
        help="Network Interface Card name",
        required=True,
    )
    return parser.parse_args()


def main():
    parser_args = parse_arguments()
    pinger_kwargs = {
        "count": 3,
        "timeout": 2,
        "interval": 1,
        "threads": 100,
        "ssid": parser_args.ssid,
        "nic": parser_args.nic,
    }
    scheduler_kwargs = {
        "func": run_pinger,
        "kwargs": pinger_kwargs,
        "trigger": "interval",
        "seconds": 120,
        "next_run_time": datetime.now()
    }

    print("create scheduler")
    scheduler = BackgroundScheduler(timezone=str(tzlocal.get_localzone()))

    print("add jobs to the scheduler")
    scheduler.add_job(**scheduler_kwargs)

    print("start scheduler")
    scheduler.start()

    try:
        while True:
            time.sleep(3)
    except (KeyboardInterrupt, SystemExit):
        print("shutdown scheduler")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
