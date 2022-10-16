import requests


collector_ip_address = "127.0.0.1"
collector_port = "8000"
collector_http_socket = f"http://{collector_ip_address}:{collector_port}"
collector_api_prefix = "collector/api/v1"


def get_url(endpoint):
    endpoint = f"{collector_api_prefix}/{endpoint}/"
    url = f"{collector_http_socket}/{endpoint}"
    return url


def send_data(url, data, headers=None, http_method="post"):
    request_methods = {"post": requests.post, "get": requests.get}
    request_method = request_methods.get(http_method)
    print(f"method: {request_method}, data: {data}, headers: {headers}")
    res = request_method(url=url, json=data, headers=headers)
    return res
