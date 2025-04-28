
document.addEventListener('DOMContentLoaded', function() {
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadStatus = document.getElementById('uploadStatus');
    const receiptImage = document.getElementById('receiptImage');
    const apiKeyDisplay = document.getElementById('api_key');  // id สำหรับโชว์ API Key

    if (uploadBtn && uploadStatus && receiptImage && apiKeyDisplay) {
        uploadBtn.addEventListener('click', async function() {
            const file = receiptImage.files[0];
            if (!file) {
                uploadStatus.textContent = 'กรุณาเลือกไฟล์ใบเสร็จ';
                return;
            }

            const formData = new FormData();
            formData.append('receipt', file);

            try {
                const response = await fetch('http://localhost:5000/upload-receipt', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    uploadStatus.textContent = 'อัปโหลดสำเร็จ!';
                    apiKeyDisplay.textContent = data.api_key;  // <<< แสดง API Key ตรงนี้
                } else {
                    uploadStatus.textContent = 'เกิดข้อผิดพลาด: ' + (data.error || 'ไม่ทราบสาเหตุ');
                    apiKeyDisplay.textContent = '';  // ล้าง API Key ถ้า error
                }
            } catch (error) {
                console.error('เกิดข้อผิดพลาด:', error);
                uploadStatus.textContent = 'เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์';
                apiKeyDisplay.textContent = '';  // ล้าง API Key ถ้า error
            }
        });
    }
});

