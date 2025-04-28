from flask import Flask, request, jsonify, send_from_directory
import uuid
import os
from PIL import Image
from werkzeug.utils import secure_filename
from ultralytics import YOLO
from flask_cors import CORS
from urllib.parse import quote
import cv2
import numpy as np
import threading
from functools import wraps
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash
from promptpay import qrcode
import base64
from io import BytesIO
import hashlib
import json
import requests
import pytesseract
import re
from PIL import Image, ImageEnhance, ImageFilter
from flask import Flask, redirect, url_for
from flask_dance.contrib.google import make_google_blueprint, google
from dotenv import load_dotenv
from flask import render_template  
import smtplib
import secrets
from email.message import EmailMessage
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail, Message
import random
from ocr_receipt import extract_info

 
 
# การตั้งค่า Flask
app = Flask(__name__)
CORS(app)
 
load_dotenv()
 
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv("EMAIL_USER"),
    MAIL_PASSWORD=os.getenv("EMAIL_PASS"),
    MAIL_DEFAULT_SENDER='Phurinsukman3@gmail.com'  # ตั้งค่าอีเมลผู้ส่ง
)
 
mail = Mail(app)
 
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = "http://localhost:5000/auth/google/callback"
 
# ตั้งค่า Tesseract OCR path (เปลี่ยนตามที่ติดตั้งในเครื่อง)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
 
# เชื่อมต่อ MongoDB
MONGO_URI = "mongodb://localhost:27017"  # เปลี่ยนตามการตั้งค่าของคุณ
client = MongoClient(MONGO_URI)
db = client["api_database"]
users_collection = db["users"]
api_keys_collection = db["api_keys"]
orders_collection = db["orders"]
otp_collection = db["otp_reset"]
 
 
# หน้าแรก
@app.route('/')
def home():
    # ใช้ relative path ไปยังโฟลเดอร์ 'home page'
    return send_from_directory(os.path.join(os.getcwd(), 'homepage'), 'index.html')
 
# เพิ่ม route สำหรับไฟล์อื่นๆ ที่อยู่ในโปรเจกต์
@app.route('/<path:filename>')
def serve_other_files(filename):
    # ให้ Flask สามารถเข้าถึงไฟล์จากทุกโฟลเดอร์ในโปรเจกต์
    return send_from_directory(os.getcwd(), filename)
 
# เพิ่ม route สำหรับไฟล์ CSS, JS ที่อยู่ในโฟลเดอร์ 'home page'
@app.route('/homepage/<path:filename>')
def serve_home_page_files(filename):
    # ให้ Flask สามารถเข้าถึงไฟล์ CSS และ JS ในโฟลเดอร์ 'home page'
    return send_from_directory(os.path.join(os.getcwd(), 'homepage'), filename)
 
# ฟังก์ชันสำหรับสมัครสมาชิก
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json  # รับข้อมูล JSON
    email = data.get("email")
    username = data.get("username")
    password = data.get("password")
 
    # ตรวจสอบว่าอีเมล, ชื่อผู้ใช้, และรหัสผ่านไม่ว่าง
    if not email or not username or not password:
        return jsonify({"message": "All fields are required"}), 400
 
    # ตรวจสอบว่าอีเมลนี้เคยลงทะเบียนแล้วหรือไม่
    if users_collection.find_one({"email": email}):
        return jsonify({"message": "Email already exists"}), 400
 
    # แฮชรหัสผ่าน
    hashed_password = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)
   
    # เพิ่มข้อมูลผู้ใช้ใหม่
    users_collection.insert_one({"email": email, "username": username, "password": hashed_password})
 
    return jsonify({"message": "Signup successful"}), 201
 
# ฟังก์ชันสำหรับล็อกอิน
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()  # รับข้อมูลจาก request body
    email = data.get('email')
    password = data.get('password')
 
    # ตรวจสอบว่าอีเมลและรหัสผ่านไม่ได้ว่าง
    if not email:
        return jsonify({'error': 'Email is required'}), 400
 
    # ค้นหาผู้ใช้ในฐานข้อมูลตาม email
    user = users_collection.find_one({"email": email})
 
    # หากผู้ใช้ไม่พบ
    if not user:
        return jsonify({'error': 'User not found'}), 404
 
    # ตรวจสอบผู้ใช้ที่ล็อกอินด้วย Google (ผู้ที่ไม่มีรหัสผ่าน)
    if user.get('password') is None:
        # ผู้ใช้ล็อกอินด้วย Google ให้ข้ามการตรวจสอบรหัสผ่าน
        return jsonify({'message': 'Login successful with Google'}), 200
 
    # ตรวจสอบรหัสผ่าน
    if not password:
        return jsonify({'error': 'Password is required'}), 400
 
    # ตรวจสอบรหัสผ่าน
    if not check_password_hash(user['password'], password):
        return jsonify({'error': 'Incorrect password'}), 400
 
    return jsonify({'message': 'Login successful'}), 200
 
# โฟลเดอร์สำหรับอัปโหลด
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
 
# โหลดโมเดลสำหรับการทำนาย (ต้องโหลดโมเดลให้ถูกต้อง)
def load_model(model_name):  
    return YOLO(os.path.join(os.path.dirname(__file__), 'models', model_name))
 
# โมเดล
models = {
    "porn": load_model('best-porn.pt'),
    "weapon": load_model('best-weapon.pt'),
    "cigarette": load_model('best-cigarette.pt'),
    "violence": load_model('best-violence.pt')
}
 
# รายการของ labels ที่ไม่เหมาะสม
INAPPROPRIATE_LABELS = {}
WEAPON_LABELS = {}
CIGARETTE_LABELS = {}
VIOLENCE_LABELS = {}
 
# กำหนดค่า confidence threshold สำหรับแต่ละโมเดล
CONFIDENCE_THRESHOLDS = {
    "porn": 0.5,
    "weapon": 0.5,
    "cigarette": 0.5,
    "violence": 0.5
}
 
# ฟังก์ชันสำหรับการวิเคราะห์ภาพ
def analyze_model(image_path, model, results_dict, label, threshold):
    # วิเคราะห์ภาพและเก็บผลลัพธ์ใน dictionary
    results = model.predict(source=image_path)
    filtered_results = []
    for result in results:
        for box in result.boxes:
            confidence = float(box.conf)
            if confidence >= threshold:
                label_name = model.names[int(box.cls)].lower()
                bbox = box.xyxy.tolist()[0]
                filtered_results.append({
                    "label": label_name,
                    "confidence": confidence,
                    "bbox": bbox
                })
    results_dict[label] = filtered_results
 
# ฟังก์ชันตรวจสอบประเภทไฟล์ (รองรับทุกประเภท)
def allowed_file(filename):
    return '.' in filename  # ตรวจสอบว่ามี "." ในชื่อไฟล์
 
# ฟังก์ชันตรวจสอบว่าเป็นไฟล์ภาพจริง
def is_image(file_path):
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except (IOError, SyntaxError):
        return False
 
# ฟังก์ชันแปลง .jfif เป็น .jpg
def convert_jfif_to_jpg(input_path):
    output_path = input_path.rsplit('.', 1)[0] + '.jpg'
    with Image.open(input_path) as img:
        img.convert('RGB').save(output_path, 'JPEG')
    os.remove(input_path)  # ลบไฟล์เดิม
    return output_path
 
# ฟังก์ชันวาด Bounding Box
def draw_bounding_boxes(image_path, detections, output_path):
    image = cv2.imread(image_path)
   
    for detection in detections:
        x1, y1, x2, y2 = map(int, detection["bbox"])  # แปลงพิกัดจาก float เป็น int
        label = detection["label"]
        confidence = detection["confidence"]
 
        # ตรวจสอบขนาดของ Bounding Box เพื่อให้ไม่เกินขนาดของภาพ
        image_height, image_width = image.shape[:2]
        x1 = max(0, min(x1, image_width - 1))
        y1 = max(0, min(y1, image_height - 1))
        x2 = max(0, min(x2, image_width - 1))
        y2 = max(0, min(y2, image_height - 1))
 
        # วาด Bounding Box
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)  # สีเขียว
 
        # สร้างข้อความที่ต้องการแสดง
        text = f"{label} ({confidence:.2f})"
       
        # วัดขนาดข้อความ
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
       
        # วาดพื้นหลังข้อความ
        background_rect = (x1, y1 - text_size[1] - 10, x1 + text_size[0], y1)
        cv2.rectangle(image, (background_rect[0], background_rect[1]),
                      (background_rect[2], background_rect[3]), (0, 255, 0), -1)  # สีเขียวทึบ
 
        # วาดข้อความ
        cv2.putText(image, text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
 
    cv2.imwrite(output_path, image)
 
# ฟังก์ชันสำหรับลบไฟล์
def delete_file(file_path):
    try:
        os.remove(file_path)
        print(f"Deleted file: {file_path}")
    except Exception as e:
        print(f"Error deleting file: {e}")
 
# Decorator ตรวจสอบ API Key จาก MongoDB
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('x-api-key')
        if not api_key or not api_keys_collection.find_one({"api_key": api_key}):
            return jsonify({'error': 'Invalid or missing API key'}), 403
        return f(*args, **kwargs)
    return decorated_function
 
# ฟังก์ชันสำหรับตรวจสอบ Referer
def check_referer(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        referer = request.headers.get('Referer')
        # ตรวจสอบว่า referer มาจากเว็บของคุณหรือไม่
        if referer and "http://localhost:5500/Project-api-5-3-68/home%20page/index.html" in referer:
            # ถ้ามาจากเว็บของคุณจะไม่ต้องใช้ API Key
            return f(*args, **kwargs)
        # ถ้าไม่มาจากเว็บของคุณ ให้ใช้ require_api_key
        return require_api_key(f)(*args, **kwargs)
    return decorated_function
 
# API วิเคราะห์ภาพ
@app.route('/analyze-image', methods=['POST'])
@check_referer    # ตรวจสอบ Referer ก่อนเรียกใช้งาน
@require_api_key  # ตรวจสอบ API Key ก่อนเรียกใช้งาน
def analyze_image():
    try:
        # ดึง api_key จาก MongoDB เพื่อใช้งาน
        api_key = request.headers.get('x-api-key')
        api_key_data = api_keys_collection.find_one({"api_key": api_key})
       
        # แปลง quota เป็น integer
        quota = int(api_key_data['quota'])  # แปลง quota เป็น integer
        if quota <= 0:
            return jsonify({'error': 'Quota exceeded'}), 400
 
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
 
        file = request.files['image']
        ext = file.filename.rsplit('.', 1)[-1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
 
        if not is_image(file_path):
            os.remove(file_path)
            return jsonify({'error': 'File is not a valid image'}), 400
 
        # ใช้ Dictionary เก็บผลลัพธ์
        results_dict = {}
 
        # สร้างและเริ่ม Thread สำหรับการวิเคราะห์แต่ละโมเดล
        models_info = [
            {"name": "porn", "model": models["porn"]},
            {"name": "weapon", "model": models["weapon"]},
            {"name": "cigarette", "model": models["cigarette"]},
            {"name": "violence", "model": models["violence"]}
        ]
       
        threads = []
        for model_info in models_info:
            # ตรวจสอบว่า analysis_types ใน API Key มีประเภทนี้หรือไม่
            if model_info["name"] in api_key_data['analysis_types']:
                thread = threading.Thread(target=analyze_model, args=(file_path, model_info["model"], results_dict, model_info["name"], 0.5))
                threads.append(thread)
                thread.start()
 
        # รอให้ทุก Thread เสร็จ
        for thread in threads:
            thread.join()
 
        # รวมผลลัพธ์จากโมเดลทั้งหมด
        detections = []
        for model_info in models_info:
            if model_info["name"] in api_key_data['analysis_types']:  # ตรวจสอบประเภทที่เลือก
                detections.extend(results_dict[model_info["name"]])
 
        # วาด Bounding Box
        result_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_' + filename)
        draw_bounding_boxes(file_path, detections, result_image_path)
 
        # กำหนดสถานะ
        status = "passed"
        for d in detections:
            model_type = d.get("model_type", "")
            threshold = CONFIDENCE_THRESHOLDS.get(model_type, 0.5)  # เอาค่าจาก CONFIDENCE_THRESHOLDS หรือใช้ค่าเริ่มต้น 0.5
            if d["confidence"] >= threshold:
                status = "failed"
                break  # ถ้าเจอกรณีที่ confidence สูงกว่าหรือเท่ากับ threshold ให้หยุดลูปทันที
 
        # ลบไฟล์ที่อัปโหลด
        os.remove(file_path)
        # ตั้งค่าให้ลบไฟล์ภาพที่ประมวลผลหลังจาก 5 วินาที
        threading.Timer(10, delete_file, args=[result_image_path]).start()
 
        # ลด quota ของ API Key ลง 1
        api_keys_collection.update_one({"api_key": api_key}, {"$set": {"quota": quota - 1}})
 
        return jsonify({
            'status': status,
            'detections': detections,
            'processed_image_url': f'http://127.0.0.1:5000/uploads/{quote("processed_" + filename)}'
        })
 
    except Exception as e:
        return jsonify({'error': f'Error during analysis: {e}'}), 500
 
# API สำหรับขอ API Key
@app.route('/request-api-key', methods=['POST'])
def request_api_key():
    data = request.get_json()
    email = data.get('email')
    analysis_types = data.get('analysis_types', [])
    quota = data.get('quota', 100)
    plan = data.get('plan', 'free')  # ถ้าไม่ส่งมา จะถือว่าเป็น free plan
 
    if not email:
        return jsonify({'error': 'Email is required'}), 400
 
    if not analysis_types:
        return jsonify({'error': 'At least one analysis type is required'}), 400
 
    if plan == 'free':
        # ถ้าเป็นแผนฟรี และเคยขอไปแล้ว
        existing_free_key = api_keys_collection.find_one({"email": email, "plan": "free"})
        if existing_free_key:
            return jsonify({'error': 'คุณได้ขอ API Key ฟรีไปแล้ว'}), 400
 
    # สร้าง API Key ใหม่
    api_key = str(uuid.uuid4())
 
    # บันทึกข้อมูลใหม่
    api_keys_collection.insert_one({
        "email": email,
        "api_key": api_key,
        "analysis_types": analysis_types,
        "quota": quota,
        "plan": plan  # บันทึกว่าแผนอะไร (free, pro, premium)
    })
 
    return jsonify({'apiKey': api_key})
 
 
# API สำหรับรายงานปัญหา
@app.route('/report-issue', methods=['POST'])
def report_issue():
    issue = request.json.get('issue')
    category = request.json.get('category')
 
    # ล็อกค่า issue และ category เพื่อตรวจสอบ
    print(f"Received issue: {issue}, category: {category}")
 
    if issue and category:
        folder = 'report-issues'
        if not os.path.exists(folder):
            os.makedirs(folder)
 
        # ใช้เวลาปัจจุบันในการตั้งชื่อไฟล์ (formatted)
        filename = f"report-issues/report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
 
        with open(filename, 'w') as file:
            file.write(f"หมวดหมู่: {category}\n")
            file.write(f"รายละเอียดปัญหา: {issue}\n")
       
        return jsonify({'success': True}), 200
    return jsonify({'success': False}), 400
 
# ดูข้อมูล database
@app.route('/get-api-keys', methods=['GET'])
def get_api_keys():
    email = request.args.get('email')
 
    if not email:
        return jsonify({'error': 'Email is required'}), 400
 
    # ตรวจสอบการเชื่อมต่อฐานข้อมูล
    try:
        user = api_keys_collection.find({"email": email})
        api_keys = list(user)  # แปลง cursor เป็น list
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500
 
    if not api_keys:
        return jsonify({'error': 'No API keys found for this email'}), 404
 
    # ส่งคืนข้อมูล API Keys ทั้งหมดของผู้ใช้
    return jsonify({
        'api_keys': [{
            'api_key': key.get('api_key', 'ไม่พบ API Key'),
            'analysis_types': key.get('analysis_types', []),
            'quota': key.get('quota', 0)
        } for key in api_keys]
    })
 
# API สำหรับดาวน์โหลดเอกสารคู่มือ
@app.route('/download-manual', methods=['GET'])
def download_manual():
    manual_path = os.path.join(os.getcwd(), 'manual.pdf')  # ใช้เส้นทางที่ถูกต้อง
    if os.path.exists(manual_path):
        return send_from_directory(os.getcwd(), 'manual.pdf', as_attachment=True)
    return jsonify({'error': 'ไม่พบไฟล์เอกสารคู่มือ'}), 404
 
# ให้บริการไฟล์ที่อัปโหลด
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)
 
# API สำหรับสร้าง QR Code
def generate_qr_code(promptpay_id, amount=0):
    # สร้าง payload ด้วยหมายเลข PromptPay และจำนวนเงิน
    if amount > 0:
        payload = qrcode.generate_payload(promptpay_id, amount)
    else:
        payload = qrcode.generate_payload(promptpay_id)
 
    # สร้าง QR Code จาก payload
    img = qrcode.to_image(payload)
 
    # แปลงภาพ QR Code เป็น Base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
 
    return f"data:image/png;base64,{img_str}"
 
# เพิ่มตอนสร้าง QR ให้สร้าง ref_code และบันทึก order
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.get_json()
    amount = float(data.get('amount', 0))
    promptpay_id = data.get('promptpay_id', '66882884744')
    email = data.get('email', '')
    quota = int(data.get('quota', 100))
    plan = data.get('plan', 'paid')
    analysis_types = data.get('analysis_types', [])  # ต้องเป็น list
 
   # ใช้เวลาปัจจุบันในรูปแบบ วันที่/เดือน/ปี ชั่วโมง:นาที:วินาที
    current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
 
    # สร้าง UUID และลบเครื่องหมาย "-" ออก
    uuid_value = uuid.uuid4().hex  # .hex จะได้ UUID ที่ไม่มีเครื่องหมาย "-"
    ref_code = f"{current_time} {uuid_value}"  # ใช้ช่องว่างแทนที่เครื่องหมาย "-"
 
 
    # บันทึกออร์เดอร์ลงฐานข้อมูล สถานะยังไม่ชำระ
    orders_collection.insert_one({
        "ref_code": ref_code,              
        "email": email,                    
        "amount": amount,                  
        "quota": quota,                    
        "plan": plan,                      
        "analysis_types": analysis_types,  
        "paid": False,                      
        "created_at": datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    })
 
    # สร้าง QR
    qr_base64 = generate_qr_code(promptpay_id, amount)
 
    # ส่งกลับ QR + ref_code
    return jsonify({
        "qr_code_url": qr_base64,
        "ref_code": ref_code
    })
 
# ฟังก์ชันตรวจสอบว่ามี QR Code หรือไม่
def check_qrcode(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return False
    detector = cv2.QRCodeDetector()
    retval, points = detector.detect(image)  # ใช้ detect() แทน detectAndDecode()
    
    if retval:  # ถ้าคืนค่า True แสดงว่ามี QR code ในภาพ
        return True
    return False


@app.route('/upload-receipt', methods=['POST'])
def upload_receipt():
    if 'receipt' not in request.files:
        return jsonify({'error': 'No receipt file provided'}), 400

    file = request.files['receipt']
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(save_path)

    if not is_image(save_path):
        os.remove(save_path)
        return jsonify({'error': 'ไฟล์ไม่ใช่รูปภาพ'}), 400

    # ตรวจสอบว่าภาพมี QR Code หรือไม่
    if not check_qrcode(save_path):
        os.remove(save_path)
        return jsonify({'error': 'รูปเเบบใบเสร็จไม่ถูกต้อง'}), 400

    # ดึงข้อมูลจาก OCR
    ocr_data = extract_info(save_path)
    
    # ตรวจสอบข้อมูลที่จำเป็นต้องมี
    required_fields = ['full_text', 'date', 'time', 'uuids', 'amount', 'full_name', 'time_receipts']
    for field in required_fields:
        if not ocr_data.get(field):
            os.remove(save_path)
            return jsonify({'error': f"ข้อมูล {field} ขาดหายไปหรือเป็นค่าว่าง"}), 400

    # รับข้อมูลที่ได้จาก OCR
    text = ocr_data['full_text']
    uuid_list = ocr_data['date'] + " " + ocr_data['time'] + " " + " ".join(ocr_data['uuids'])
    date_text = ocr_data['date']
    time = ocr_data['time']
    amount = ocr_data['amount']
    full_name = ocr_data['full_name']
    time_receipts = ocr_data["time_receipts"]

    # แสดงค่าของตัวแปรที่ได้รับ
    print("OCR Full Text: ", text)
    print("UUID List: ", uuid_list)
    print("Date from OCR: ", date_text)
    print("Time from OCR: ", time)
    print("Amount from OCR: ", amount)
    print("full_name: ", full_name)
    print("time_receipts: ", time_receipts)

    # ตรวจสอบ UUID กับฐานข้อมูล
    matched_order = orders_collection.find_one({"ref_code": uuid_list})  # ใช้ uuid_list ค้นหาโดยตรง
    if not matched_order:
        os.remove(save_path)  # ลบไฟล์ที่ไม่ได้ใช้งาน
        return jsonify({
            'error': 'ไม่พบรหัสอ้างอิงในฐานข้อมูล', 
            'ocr_data': {
                'full_text': text,
                'uuids': uuid_list,
                'date': date_text,
                'time': time,
                'amount': amount,
                'fullname': full_name
            }
        }), 404

    # ตรวจสอบชื่อ
    full_name = ocr_data.get("full_name", "")
    if "ภูรินทร์สุขมั่น" not in full_name:
        os.remove(save_path)
        return jsonify({'error': 'ชื่อผู้โอนไม่ถูกต้อง'}), 400

    # ตรวจสอบวันที่
    try:
        created_datetime = datetime.strptime(matched_order["created_at"], '%d/%m/%Y %H:%M:%S')
    except:
        os.remove(save_path)
        return jsonify({'error': 'ข้อมูลวันที่ในฐานข้อมูลผิดพลาด'}), 500

    if date_text:
        try:
            date_from_ocr = datetime.strptime(date_text, '%d/%m/%Y').date()
            if date_from_ocr != created_datetime.date():
                os.remove(save_path)
                return jsonify({'error': 'วันที่ในสลิปไม่ตรงกับวันที่สร้างออร์เดอร์'}), 400
        except:
            os.remove(save_path)
            return jsonify({'error': 'รูปแบบวันที่ในสลิปผิด'}), 400

    # ตรวจสอบเวลา
    if time_receipts:
        try:
            time_from_ocr = datetime.strptime(time_receipts, '%H:%M')
            time_from_ocr_full = datetime.combine(created_datetime.date(), time_from_ocr.time())
            time_diff = abs((created_datetime - time_from_ocr_full).total_seconds())

            if time_diff > 300:
                os.remove(save_path)
                return jsonify({'error': 'เวลาในสลิปห่างกันเกิน 5 นาที'}), 400
        except:
            os.remove(save_path)
            return jsonify({'error': 'รูปแบบเวลาในสลิปผิด'}), 400

    # ตรวจสอบยอดเงิน
    if amount:
        try:
            amount = float(amount.replace(',', ''))
            if float(matched_order.get('amount', 0)) != amount:
                os.remove(save_path)
                return jsonify({'error': 'ยอดเงินไม่ตรงกัน'}), 400
        except:
            os.remove(save_path)
            return jsonify({'error': 'ยอดเงินไม่สามารถแปลงได้'}), 400

    # สร้าง API Key และอัปเดตสถานะการชำระเงิน
    orders_collection.update_one({"_id": matched_order["_id"]}, {
        "$set": {"paid": True, "paid_at": datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    })

    api_key = str(uuid.uuid4())
    api_keys_collection.insert_one({
        "email": matched_order.get('email', ''),
        "api_key": api_key,
        "analysis_types": matched_order.get('analysis_types', []),
        "quota": matched_order.get('quota', 100),
        "plan": matched_order.get('plan', 'paid'),
        "created_at": datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    })

    # ลบออร์เดอร์ออกจากฐานข้อมูลหลังจากสร้าง API Key แล้ว
    orders_collection.delete_one({"ref_code": uuid_list})
    os.remove(save_path)

    return jsonify({
        'success': True,
        'message': 'อัปโหลดสำเร็จ',
        'api_key': api_key,
        'ocr_data': {
            'uuids': uuid_list,
            'date': date_text,
            'time': time,
            'amount': amount,
            'fullname': full_name,
            'full_text': text,
        }
    }), 200

@app.route('/auth/google')
def auth_google():
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid email profile"
    )
    return redirect(google_auth_url)
 
@app.route('/auth/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'Authorization code not found'}), 400
 
    # แลกเปลี่ยน code เป็น access token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    token_response = requests.post(token_url, data=token_data)
    token_json = token_response.json()
 
    access_token = token_json.get('access_token')
    id_token = token_json.get('id_token')
 
    # ดึงข้อมูลโปรไฟล์ผู้ใช้
    user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    user_info_response = requests.get(user_info_url, headers={'Authorization': f'Bearer {access_token}'})
    user_info = user_info_response.json()
 
    # ตรวจสอบว่าผู้ใช้อยู่ในระบบหรือยัง
    email = user_info.get('email')
    user = users_collection.find_one({"email": email})
    if not user:
        # หากผู้ใช้ยังไม่มีในระบบ ให้เพิ่มเข้าไป
        users_collection.insert_one({
            "email": email,
            "username": user_info.get('name'),
            "password": None  # ไม่มีรหัสผ่านเพราะล็อกอินด้วย Google
        })
 
    # เปลี่ยนเส้นทางไปยัง plan.html
    return redirect('/apikey/mainapikey.html')
 
# สร้าง OTP และส่งอีเมล
@app.route('/reset-request', methods=['POST'])
def reset_request():
    email = request.json.get('email')
    if not users_collection.find_one({'email': email}):
        return jsonify({'message': 'ไม่พบอีเมลนี้'}), 404
 
    otp = str(random.randint(100000, 999999))
    expiration = datetime.utcnow() + timedelta(minutes=5)
 
    otp_collection.update_one(
        {'email': email},
        {'$set': {'otp': otp, 'otp_expiration': expiration, 'used': False}},
        upsert=True
    )
 
    msg = Message('OTP สำหรับรีเซ็ตรหัสผ่าน', recipients=[email])
    msg.body = f'รหัส OTP ของคุณคือ: {otp}'
    mail.send(msg)
 
    return jsonify({'message': 'ส่ง OTP แล้ว'}), 200
 
# ตรวจสอบ OTP
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
 
    record = otp_collection.find_one({'email': email, 'otp': otp, 'used': False})
    if not record:
        return jsonify({'message': 'OTP ไม่ถูกต้อง'}), 400
 
    if record['otp_expiration'] < datetime.utcnow():
        return jsonify({'message': 'OTP หมดอายุแล้ว'}), 400
 
    return jsonify({'message': 'OTP ถูกต้อง'}), 200
 
# ตั้งรหัสผ่านใหม่
@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
 
    if password != confirm_password:
        return jsonify({'message': 'รหัสผ่านไม่ตรงกัน'}), 400
 
    record = otp_collection.find_one({'email': email, 'otp': otp, 'used': False})
    if not record or record['otp_expiration'] < datetime.utcnow():
        return jsonify({'message': 'OTP ไม่ถูกต้องหรือหมดอายุ'}), 400
 
    # แฮชรหัสผ่านใหม่ก่อนอัปเดตในฐานข้อมูล
    hashed_password = generate_password_hash(password, method="pbkdf2:sha256", salt_length=8)
 
    users_collection.update_one({'email': email}, {'$set': {'password': hashed_password}})
    otp_collection.update_one({'email': email}, {'$set': {'used': True}})
 
    return jsonify({'message': 'รีเซ็ตรหัสผ่านเรียบร้อยแล้ว'}), 200
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)