function generateApiKey() {
    // ดึงอีเมลจาก sessionStorage
    let email = sessionStorage.getItem('userEmail');
    if (!email) {
        alert("กรุณาล็อกอินก่อน");
        return;
    }

    // รับข้อมูลจาก checkbox สำหรับประเภทการวิเคราะห์
    let analysisTypes = [];
    document.querySelectorAll('.analysis-option:checked').forEach(option => {
        analysisTypes.push(option.value);
    });

    // รับค่าจำนวน quota จาก input
    let quota = parseInt(document.getElementById("quota").value);

    // ตรวจสอบข้อมูล
    if (analysisTypes.length === 0 || isNaN(quota) || quota < 100) {
        alert("กรุณากรอกข้อมูลทั้งหมดให้ถูกต้อง");
        return;
    }

    // คำนวณเงินที่ต้องจ่าย (100 เครดิต = 1 บาท)
    let amount = quota / 100;

    // บันทึกข้อมูลลง sessionStorage เพื่อใช้ต่อในหน้า payment.html
    sessionStorage.setItem("selectedQuota", quota);          // เช่น 200
    sessionStorage.setItem("selectedAmount", amount);        // เช่น 2
    sessionStorage.setItem("selectedAnalysis", JSON.stringify(analysisTypes));

    // แสดงข้อมูล (debug)
    console.log("Email: " + email);
    console.log("Analysis Types: " + analysisTypes.join(", "));
    console.log("Quota: " + quota);
    console.log("Amount (THB): " + amount);

    // ไปหน้าจ่ายเงิน
    window.location.href = "payment.html";
}
