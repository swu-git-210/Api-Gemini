from google import genai
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, MessageEvent, TextMessage
from flask import Flask, request, abort, render_template_string

# LINE API Access Token และ Channel Secret
CHANNEL_ACCESS_TOKEN = 'Oz6x3Zse8dmKO5HWmiRy3aCa26v1aiRJWAFIcGXp/kvSE58NBWARFg1AUf0beFKgqj/+KavL0VJU6wtGOwc3Zf0UfgnAOLJnEBmUwExf6rbCBPz2wplzFtOUVDxo8HJ7RM7En2r4qYg9eBnQeeeWvQdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = 'c9810af033f3b71c3575127651aa3045'

# สร้าง client สำหรับเชื่อมต่อกับ Gemini API
client = genai.Client(api_key="AIzaSyDo2U64Wt4Kwcq7ei1U1TjeTkmmVaaYz1I")

# สร้าง LineBotApi และ WebhookHandler
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# สร้าง Flask app
app = Flask(__name__)

latest_messages = []  # สำหรับเก็บข้อความล่าสุดไว้แสดงในหน้าเว็บ

# ฟังก์ชันหลักในการใช้ Gemini API
def generate_answer(question):
    prompt = f"คุณคือผู้ให้คำแนะนำ เกี่ยวกับเพลง โดยค้นหาและแนะนำเพลง พร้อมลิ้งyoutubeด้วย ได้ทั้งไทยและสากล {question}"
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt]
    )
    return response.text

# ฟังก์ชันจัดการข้อความที่ได้รับจากผู้ใช้
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    user_id = event.source.user_id

    print(f"Received message: {user_message} from {user_id}")
    answer = generate_answer(user_message)
    
    # ส่งข้อความกลับไปที่ LINE
    response_message = f"คำถาม: {user_message}\nคำตอบ: {answer}"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_message))
    
    # บันทึกไว้แสดงในหน้าเว็บ
    latest_messages.append({'user': user_message, 'bot': answer})
    if len(latest_messages) > 5:
        latest_messages.pop(0)

# หน้า Web UI สวย ๆ
@app.route('/')
def index():
    return render_template_string("""
    <html>
    <head>
        <title>Music Bot Status</title>
        <style>
            body {
                font-family: 'Segoe UI', sans-serif;
                background: #f0f2f5;
                color: #333;
                padding: 40px;
            }
            h1 {
                color: #4CAF50;
            }
            .chat {
                background: white;
                border-radius: 10px;
                padding: 20px;
                max-width: 600px;
                box-shadow: 0 0 15px rgba(0,0,0,0.1);
                margin-top: 20px;
            }
            .msg {
                margin-bottom: 15px;
            }
            .user { color: #2196F3; }
            .bot { color: #E91E63; }
        </style>
    </head>
    <body>
        <h1>🎵 LINE Music Bot - Status Page</h1>
        <p>ดูข้อความล่าสุดที่บอทได้รับและตอบกลับ:</p>
        <div class="chat">
            {% for item in messages %}
                <div class="msg"><b class="user">คุณ:</b> {{ item.user }}</div>
                <div class="msg"><b class="bot">บอท:</b> {{ item.bot }}</div>
                <hr>
            {% endfor %}
        </div>
    </body>
    </html>
    """, messages=latest_messages)

# Webhook URL สำหรับรับข้อความจาก LINE
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print("Error:", e)
        abort(400)

    return 'OK'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
