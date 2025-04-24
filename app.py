from google import genai
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    TextSendMessage, MessageEvent, TextMessage,
    FlexSendMessage
)
from flask import Flask, request, abort
from datetime import datetime
import random

# LINE API Access Token และ Channel Secret
CHANNEL_ACCESS_TOKEN = 'Oz6x3Zse8dmKO5HWmiRy3aCa26v1aiRJWAFIcGXp/kvSE58NBWARFg1AUf0beFKgqj/+KavL0VJU6wtGOwc3Zf0UfgnAOLJnEBmUwExf6rbCBPz2wplzFtOUVDxo8HJ7RM7En2r4qYg9eBnQeeeWvQdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = 'c9810af033f3b71c3575127651aa3045'

# Gemini API
client = genai.Client(api_key="AIzaSyDo2U64Wt4Kwcq7ei1U1TjeTkmmVaaYz1I")

# LINE Bot
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# Flask app
app = Flask(__name__)

# เรียก Gemini
def generate_answer(question):
    prompt = (
        f"แนะนำเพลง 3 เพลง ที่เหมาะกับคำว่า: '{question}' "
        f"ให้ตอบกลับเป็น format ต่อไปนี้เท่านั้น (ห้ามเขียนอย่างอื่น):\n\n"
        f"เพลง: <ชื่อเพลง>\nเหตุผล: <สั้นๆ 1-2 บรรทัด>\n\n"
        f"ทำแบบนี้ 3 ชุด ห้ามตอบเกิน และห้ามใส่ prefix หรือข้อความอื่นนอกจาก format นี้"
    )
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt]
    )
    return response.text

# แปลงข้อความ Gemini → list เพลง (แบบ robust)
def parse_gemini_response(text):
    songs = []
    for block in text.strip().split("\n\n"):
        lines = block.strip().split("\n")
        if len(lines) >= 2 and "เพลง:" in lines[0] and "เหตุผล:" in lines[1]:
            try:
                title = lines[0].split("เพลง:")[1].strip()
                desc = lines[1].split("เหตุผล:")[1].strip()
                query = title.replace(" ", "+")
                url = f"https://www.youtube.com/results?search_query={query}"
                songs.append({"title": title, "desc": desc, "url": url})
            except Exception as e:
                print("❌ Parse error:", e)
                continue
        else:
            print("⚠️ Block format not matched:", block)
    return songs

# สร้าง carousel จาก list เพลง พร้อม fallback ถ้า Gemini ตอบผิด
def create_carousel_message(answer_text):
    song_list = parse_gemini_response(answer_text)
    if not song_list:
        return TextSendMessage(text="ขออภัยครับ ผมไม่สามารถแนะนำเพลงได้ในตอนนี้ ลองพิมพ์ใหม่อีกครั้งนะครับ 🎧")
    
    bubbles = [build_song_bubble(song) for song in song_list]
    return FlexSendMessage(
        alt_text="แนะนำเพลง",
        contents={"type": "carousel", "contents": bubbles}
    )

# สร้าง bubble card
def build_song_bubble(song):
    return {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": song["title"],
                    "weight": "bold",
                    "size": "lg",
                    "wrap": True,
                    "color": "#1DB954"
                },
                {
                    "type": "text",
                    "text": song["desc"],
                    "wrap": True,
                    "size": "sm",
                    "color": "#666666"
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "uri",
                        "label": "🔗 เปิดใน YouTube",
                        "uri": song["url"]
                    }
                }
            ]
        }
    }

# สร้าง carousel จาก list เพลง
def create_carousel_message(answer_text):
    song_list = parse_gemini_response(answer_text)
    bubbles = [build_song_bubble(song) for song in song_list]
    return FlexSendMessage(
        alt_text="แนะนำเพลง",
        contents={"type": "carousel", "contents": bubbles}
    )

# รับข้อความจากผู้ใช้
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text.lower()
    user_id = event.source.user_id
    print(f"📨 Message from {user_id}: {user_message}")

    # ตรวจว่าผู้ใช้ทักทายหรือไม่
    greetings = ['สวัสดี', 'hello', 'hi', 'หวัดดี', 'เฮลโหล', 'ไง']
    if any(greet in user_message for greet in greetings):
        hour = datetime.now().hour
        if 5 <= hour < 12:
            time_greeting = "สวัสดีตอนเช้าครับ ☀️"
        elif 12 <= hour < 17:
            time_greeting = "สวัสดีตอนบ่ายครับ 🌤"
        elif 17 <= hour < 21:
            time_greeting = "สวัสดีตอนเย็นครับ 🌇"
        else:
            time_greeting = "สวัสดีตอนกลางคืนครับ 🌙"

        intro_options = [
            "ผมคือบอทแนะนำเพลง 🎧",
            "ผมช่วยเลือกเพลงให้เหมาะกับอารมณ์ของคุณได้ครับ 🎶",
            "พิมพ์ความรู้สึกของคุณมา แล้วผมจะหาเพลงให้เองครับ 😊",
            "อยากฟังเพลงแนวไหน บอกผมมาได้เลยครับ 🎼"
        ]
        intro = random.choice(intro_options)
        reply_text = f"{time_greeting}\n{intro}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return

    # ถ้าไม่ใช่คำทักทาย → ใช้ Gemini แนะนำเพลง
    answer = generate_answer(user_message)
    print("🤖 Gemini response:\n", answer)
    flex_msg = create_carousel_message(answer)
    line_bot_api.reply_message(event.reply_token, flex_msg)

# Webhook
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception as e:
        print("❌ Error:", e)
        abort(400)
    return 'OK'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
