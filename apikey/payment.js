document.addEventListener('DOMContentLoaded', function () {
  const amount = sessionStorage.getItem("selectedAmount");     // เช่น 2
  const quota = sessionStorage.getItem("selectedQuota");       // เช่น 200
  const email = sessionStorage.getItem("userEmail");           // เช่น user@example.com
  const analysisTypes = JSON.parse(sessionStorage.getItem("selectedAnalysis")); // เช่น ["porn", "weapon"]
  const amountSpan = document.getElementById('amount');
  const qrCodeImage = document.getElementById('qrCodeImage');
  const paymentStatus = document.getElementById('paymentStatus');

  amountSpan.innerText = amount;

  fetch('http://localhost:5000/generate_qr', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      email: email,              
      amount: parseFloat(amount),       
      quota: parseInt(quota),          
      analysis_types: analysisTypes,    
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.qr_code_url && data.ref_code) {
      qrCodeImage.src = data.qr_code_url;
      refCodeDisplay.textContent = data.ref_code;

      // ⭐ บันทึก ref_code ลงใน sessionStorage
      sessionStorage.setItem("currentRefCode", data.ref_code);
    } else {
      paymentStatus.textContent = "ไม่สามารถสร้าง QR Code ได้";
    }
  })
  .catch(err => {
    console.error("Error:", err);
    paymentStatus.textContent = "เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์";
  });
});

// ฟังก์ชันสำหรับปุ่มคัดลอก
function copyRefCode() {
const refCode = document.getElementById('refCodeDisplay').textContent;
navigator.clipboard.writeText(refCode)
  .then(() => {
    alert("คัดลอก Ref Code เรียบร้อยแล้ว!");
  })
  .catch(err => {
    alert("ไม่สามารถคัดลอก Ref Code ได้");
  });
}
