// ฟังก์ชันในการดึงข้อมูล API Keys ของผู้ใช้
function fetchApiKeys() {
    // ดึงอีเมลจาก sessionStorage ที่เก็บไว้ในระหว่างการ login
    const email = sessionStorage.getItem('userEmail');

    if (!email) {
        // หากไม่มีอีเมลแสดงว่าไม่สามารถเข้าถึงข้อมูลได้
        document.getElementById("apiKeysList").innerHTML = "<p>กรุณาเข้าสู่ระบบก่อน</p>";
        return;
    }

    // ส่งคำขอ GET ไปยัง /get-api-keys โดยใช้ email เป็นพารามิเตอร์
    fetch(`http://localhost:5000/get-api-keys?email=${email}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                // แสดงข้อผิดพลาดหากไม่พบ API Keys
                document.getElementById("apiKeysList").innerHTML = `<p>${data.error}</p>`;
            } else {
                // แสดง API Keys ที่ได้รับจากฐานข้อมูล
                let apiKeysHtml = "";
                data.api_keys.forEach(key => {
                    apiKeysHtml += `
                        <div class="api-key">
                            <p><strong>Email:</strong> ${email}</p>
                            <p><strong>API Key:</strong> ${key.api_key}</p>
                            <p><strong>Analysis Types:</strong> ${key.analysis_types.join(", ")}</p>
                            <p><strong>Quota:</strong> ${key.quota}</p>
                        </div>
                    `;
                });
                document.getElementById("apiKeysList").innerHTML = apiKeysHtml;
            }
        })
        .catch(error => {
            console.error("Error fetching API keys:", error);
            document.getElementById("apiKeysList").innerHTML = "<p>เกิดข้อผิดพลาดในการดึงข้อมูล API Keys</p>";
        });
}

// เรียกใช้งานฟังก์ชันเมื่อโหลดหน้า
window.onload = function() {
    fetchApiKeys();
};
