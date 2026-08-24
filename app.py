import os
import random
import sys
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

# 讀取環境變數
CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

# 印出檢查訊息至控制台 (Render Logs)
print("=== Starting App Initialization ===")
print(f"Token Status: {'FOUND' if CHANNEL_ACCESS_TOKEN else 'MISSING!'}")
print(f"Secret Status: {'FOUND' if CHANNEL_SECRET else 'MISSING!'}")

# 如果沒設定環境變數，避免直接 Crash，先給預設字串
handler = WebhookHandler(CHANNEL_SECRET or "dummy_secret")
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN or "dummy_token")

LOCATIONS = [
    "台北 101", "陽明山國家公園", "淡水老街", "九份老街",
    "宜蘭礁溪溫泉", "台中逢甲夜市", "日月潭", "清境農場",
    "台南奇美博物館", "高雄駁二藝術特區", "墾丁國家公園", "花蓮太魯閣"
]

@app.route("/", methods=['GET'])
def health_check():
    return "LINE Bot is running!", 200

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_msg = event.message.text

    if "出門" in user_msg:
        chosen_location = random.choice(LOCATIONS)
        reply_text = f"既然想出門，那就決定去【{chosen_location}】吧！🚗"

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Server starting on port {port}...")
    # host='0.0.0.0' 是 Render 能否連線的關鍵
    app.run(host='0.0.0.0', port=port)