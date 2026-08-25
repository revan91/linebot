import os
import random
import requests
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbw-XDg3u4YXXfQlPJWAfMupku38NKB_eg4PO-bglO2y1xGZHXhg6AFdaizIeKyqIY8sPA/exec"

# 讀取環境變數
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")

# 如果沒設定環境變數，避免直接 Crash，先給預設字串
handler = WebhookHandler(CHANNEL_SECRET or "dummy_secret")
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN or "dummy_token")


@app.route("/", methods=["GET"])
def health_check():
    return "LINE Bot is running!", 200


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_msg = event.message.text

    # 1. 優先判斷「推薦」 (避免包含「景點」二字時被後方區域攔截)
    if "推薦" in user_msg:
        reply_text = "🔥 熱門景點推薦 收到"
        try:
            # 向 GAS 請求 spot 工作表的前 5 個景點
            res = requests.get(f"{GAS_WEB_APP_URL}?type=hot_spots", timeout=3)
            hot_spots = res.json().get("hot_spots", [])

            if hot_spots:
                # 動態將前 5 個景點組裝成 1. 2. 3. 4. 5. 格式
                formatted_spots = "\n".join(
                    [f"{i+1}. {spot}" for i, spot in enumerate(hot_spots)]
                )
                reply_text = f"🔥 熱門景點推薦：\n{formatted_spots}"
            else:
                reply_text = "目前暫無推薦景點。"
        except Exception as e:
            print(f"抓取熱門景點失敗: {e}")
            reply_text = "🔥 熱門景點推薦：\n1. 台北 101\n2. 陽明山國家公園\n3. 逢甲夜市\n4. 駁二藝術特區\n5. 太魯閣國家公園"

        # 避免全域變數未定義當機，提供預設代入值
        city_label = "台北市"

        quick_reply_buttons = QuickReply(
            items=[
                QuickReplyItem(
                    action=MessageAction(label="看熱門景點 🏞️", text="推薦景點")
                ),
                QuickReplyItem(
                    action=MessageAction(
                        label=f"幫我挑{city_label}景點 🏞️",
                        text=f"{city_label}景點",
                    )
                ),
            ]
        )
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text=reply_text, quick_reply=quick_reply_buttons
                        )
                    ],
                )
            )

    # 2. 處理「出門」關鍵字
    elif "出門" in user_msg:
        try:
            res = requests.get(GAS_WEB_APP_URL, timeout=3)
            chosen_location = res.json().get("location", "台北市")
        except Exception:
            chosen_location = "台北市"

        quick_reply_buttons = QuickReply(
            items=[
                QuickReplyItem(
                    action=MessageAction(label="再抽一次 🎲", text="出門")
                ),
                QuickReplyItem(
                    action=MessageAction(
                        label="看熱門景點 🏞️", text="推薦景點"
                    )
                ),
                QuickReplyItem(
                    action=MessageAction(
                        label=f"幫我挑{chosen_location}景點 🏞️",
                        text=f"{chosen_location}景點",
                    )
                ),
            ]
        )

        reply_text = f"既然想出門，那就決定去【{chosen_location}】吧！🚗"

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text=reply_text, quick_reply=quick_reply_buttons
                        )
                    ],
                )
            )

    # 3. 處理「景點」關鍵字
    elif "景點" in user_msg:
        # 去掉「景點」兩個字，取出縣市名稱 (例如從 "台北市景點" 取出 "台北市")
        target_city = user_msg.replace("景點", "").strip()
        if not target_city:
            target_city = "台北市"

        reply_text = f"收到【{target_city}】！✨"
        try:
            # 發送 GET 請求並帶上參數 ?city=台北市
            res = requests.get(
                f"{GAS_WEB_APP_URL}?city={target_city}", timeout=3
            )
            data = res.json()
            chosen_spot = data.get("spot", f"{target_city}在地景點")
        except Exception:
            chosen_spot = f"{target_city}熱門景點"

        quick_reply_buttons = QuickReply(
            items=[
                QuickReplyItem(
                    action=MessageAction(label="換個地點 🎲", text="出門")
                ),
                QuickReplyItem(
                    action=MessageAction(
                        label="看熱門景點 🏞️", text="推薦景點"
                    )
                ),
                QuickReplyItem(
                    action=MessageAction(
                        label="再挑一次 🏞️", text=f"{target_city}景點"
                    )
                ),
            ]
        )
        reply_text = f"為你推薦私房景點：【{chosen_spot}】！✨"

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text=reply_text, quick_reply=quick_reply_buttons
                        )
                    ],
                )
            )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Server starting on port {port}...")
    app.run(host="0.0.0.0", port=port)