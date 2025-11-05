from flask import Flask, jsonify
import requests, time, threading
from datetime import datetime

app = Flask(__name__)

# ===================================
# 🔹 Biến toàn cục
# ===================================
last_data = {
    "Phiên": None,
    "Xúc_xắc_1": 0,
    "Xúc_xắc_2": 0,
    "Xúc_xắc_3": 0,
    "Tổng": 0,
    "Dự_đoán": "Đang khởi động...",
    "ID": "biios2502"
}

# ===================================
# 🔹 Hàm dự đoán Tài / Xỉu
# ===================================
def du_doan_tai_xiu(tong):
    return "Tài" if tong >= 11 else "Xỉu"

# ===================================
# 🔹 Hàm lấy dữ liệu từ API gốc Sunwin
# ===================================
def get_taixiu_data():
    url = "https://sunwinsaygex-ew87.onrender.com/api/taixiu/sunwin"
    try:
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            data = res.json()
            # ✅ API gốc trả thẳng dạng JSON (không có key "data")
            if "phien" in data:
                phien = data.get("phien")
                x1 = data.get("xuc_xac_1", 0)
                x2 = data.get("xuc_xac_2", 0)
                x3 = data.get("xuc_xac_3", 0)
                tong = data.get("tong", x1 + x2 + x3)
                return phien, [x1, x2, x3], tong
    except Exception as e:
        print(f"[❌] Lỗi gọi API gốc: {e}")
    return None

# ===================================
# 🔹 Luồng cập nhật nền
# ===================================
def background_updater():
    global last_data
    last_phien = None

    while True:
        data = get_taixiu_data()
        if data:
            phien, dice, tong = data
            if phien != last_phien:
                du_doan = du_doan_tai_xiu(tong)
                last_data.update({
                    "Phiên": phien,
                    "Xúc_xắc_1": dice[0],
                    "Xúc_xắc_2": dice[1],
                    "Xúc_xắc_3": dice[2],
                    "Tổng": tong,
                    "Dự_đoán": du_doan,
                    "ID": "biios2502"
                })
                print(f"[✅] Phiên {phien} | 🎲 {dice} | Tổng {tong} → {du_doan}")
                last_phien = phien
        time.sleep(5)

# ===================================
# 🔹 API Endpoint
# ===================================
@app.route("/api/taixiu/sunwin", methods=["GET"])
def api_sunwin():
    return jsonify(last_data)

# ===================================
# 🔹 Chạy server
# ===================================
if __name__ == "__main__":
    print("🚀 Đang chạy API /api/taixiu/sunwin ...")
    threading.Thread(target=background_updater, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
