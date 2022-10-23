# TODO Move Tokens to environment and use them via `os.environ`
TELEGRAM_API_TOKEN = "<TELEGRAM_API_TOKEN>"
DRF_TOKEN = "<DRF_TOKEN>"

FULL_DRF_TOKEN_NAME = f"Token {DRF_TOKEN}"
HEADERS = {"Authorization": FULL_DRF_TOKEN_NAME}
PLUS_SIGN = "+"

DEVICE_ICONS = {
    "SM": '📱',
    "TV": '📺',
    "TB": '📓',
    "LP": '💻',
    "PC": '🖥',
    "WT": '⌚️',
    "RT": '📶',
    "PS": '🎮'
}
