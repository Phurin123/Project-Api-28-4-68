import cv2
import pytesseract
import numpy as np
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# กำหนด path ของ tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_info(image_path):
    image = cv2.imread(image_path)
    text = pytesseract.image_to_string(image, lang='tha+eng')
    text_cleaned = ' '.join(text.split())

    # เอาช่องว่างออกจากทุกตัวแปรในข้อความ
    text_cleaneds = re.sub(r'\s+', '', text_cleaned)

    # หาข้อมูลต่าง ๆ
    uuid_pattern = r'\b(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{21,}\b'
    uuid_matches = re.findall(uuid_pattern, text_cleaned)
    time_pattern = r'\d{2}:\d{2}:\d{2}'
    time_match = re.search(time_pattern, text_cleaneds)
    date_pattern = r'\d{2}/\d{2}/\d{4}'
    date_match = re.search(date_pattern, text_cleaneds)
    amount_pattern = r'จํานวน(?:เงิน)?[:\s]*([\d,\.]+)\s*บาท'
    amount_matches = re.findall(amount_pattern, text_cleaneds)
    name_pattern = r'นาย\s([ก-๙]+)\s([ก-๙]+)'
    name_matches = re.findall(name_pattern, text_cleaned)
    time_receipts_pattern = r'([01]?[0-9]|2[0-3]):([0-5]?[0-9])'
    time_receipts_match = re.search(time_receipts_pattern, text_cleaneds)

    # ชื่อจริงที่คาดว่าเป็นชื่อที่ถูกต้อง
    correct_name = "ภูรินทร์สุขมั่น"
    
    # ตรวจสอบชื่อที่ OCR อ่านได้
    ocr_name = f"{name_matches[0][0]}{name_matches[0][1]}" if name_matches else None

    # คำนวณความคล้ายคลึง
    if ocr_name:
        similarity_score = fuzz.ratio(correct_name, ocr_name)

        # ถ้าค่าความคล้ายคลึงสูงพอ (เช่น มากกว่า 80%)
        if similarity_score > 80:
            ocr_name = correct_name  # ปรับชื่อให้เป็นชื่อที่ถูกต้อง

    result = {
        "uuids": uuid_matches,
        "time": time_match.group(0) if time_match else None,
        "date": date_match.group(0) if date_match else None,
        "amount": amount_matches[0] if amount_matches else None,
        "full_name": ocr_name,
        "time_receipts": time_receipts_match.group(0) if time_receipts_match else None,
        "full_text": text_cleaneds,
    }

    return result

# # เรียกใช้ฟังก์ชัน แล้วเก็บผลลัพธ์
# e = r"C:\Users\lovew\Downloads\retest 4.png"

# info = extract_info(e)

# # พิมพ์ข้อมูลออกมาแบบแนวตั้ง
# for key, value in info.items():
#     print(f"{key}: {value}")
