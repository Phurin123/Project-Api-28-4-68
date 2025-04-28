function generateApiKey() {
    // ดึงอีเมลจาก sessionStorage
    let email = sessionStorage.getItem('userEmail'); // ดึงอีเมลจาก sessionStorage

    // ตรวจสอบว่ามีอีเมลหรือไม่
    if (!email) {
        alert("กรุณาล็อกอินก่อน");
        return;  // ถ้าไม่มีก็หยุดการทำงานของฟังก์ชัน
    }

    // รับข้อมูลจาก checkbox และ input สำหรับประเภทการวิเคราะห์
    let analysisTypes = [];
    document.querySelectorAll('.analysis-option:checked').forEach(option => {
        analysisTypes.push(option.value);
    });

    // รับค่าจำนวน quota จาก input
    let quota = document.getElementById("quota").value;

    // ตรวจสอบว่ามีการเลือกประเภทการวิเคราะห์หรือไม่
    if (analysisTypes.length === 0) {
        alert("กรุณากรอกข้อมูลทั้งหมด");
        return;  // ถ้าไม่เลือกประเภทการวิเคราะห์ก็หยุดการทำงาน
    }

    // ส่งข้อมูลไปที่ back-end
    fetch('http://localhost:5000/request-api-key', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            email: email,
            analysis_types: analysisTypes,
            quota: quota,
            plan: 'free'  // ระบุว่าเป็นแผนฟรี
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            // ถ้ามี error (เช่น token หมดแล้ว)
            alert(data.error);  // แสดงข้อความ "Token หมดแล้ว"
        } else if (data.apiKey) {
            // ถ้าสร้าง API Key สำเร็จ
            document.getElementById("apiKey").textContent = data.apiKey;  // แสดง API Key บนหน้าเว็บ
        } else {
            alert("เกิดข้อผิดพลาดในการสร้าง API Key");
        }
    })
    .catch(error => {
        console.error("เกิดข้อผิดพลาดในการเชื่อมต่อ:", error);
        alert("เกิดข้อผิดพลาดในการเชื่อมต่อกับ server");
    });
}




