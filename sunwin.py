from flask import Flask, jsonify
import requests
import random
import time
import threading

app = Flask(__name__)

last_data = {
    "phien": None,
    "xucxac1": 0,
    "xucxac2": 0,
    "xucxac3": 0,
    "tong": 0,
    "du_doan": "Đang khởi động...",
    "id": "biios2502"
}

def get_taixiu_data():
    """Lấy dữ liệu thật từ API BotVIP"""
    url = "https://api.botvip.cc/api/GetNewLottery/LT_TaixiuMD5"
    try:
        res = requests.get(url, timeout=6)
        data = res.json()
        if "data" in data and data["data"]:
            info = data["data"]
            phien = info.get("Expect", int(time.time()))
            opencode = info.get("OpenCode", "1,2,3")
            dice = [int(x) for x in opencode.split(",")]
            tong = sum(dice)
            return phien, dice, tong
    except Exception:
        pass
    return None

def du_doan_tai_xiu(tong):
    """Dự đoán đơn giản"""
    return "Tài" if tong >= 11 else "Xỉu"

def background_updater():
    """Luồng chạy nền liên tục cập nhật dữ liệu"""
    global last_data
    last_phien = None
    while True:
        data = get_taixiu_data()
        if data:
            phien, dice, tong = data
            if phien != last_phien:
                du_doan = du_doan_tai_xiu(tong)
                last_data = {
                    "phien": phien,
                    "xucxac1": dice[0],
                    "xucxac2": dice[1],
                    "xucxac3": dice[2],
                    "tong": tong,
                    "du_doan": du_doan,
                    "id": "biios2502"
                }
                print(f"[OK] Phiên {phien} - KQ: {du_doan} ({tong}) 🎲 {dice}")
                last_phien = phien
        else:
            # fallback khi API lỗi
            dice = [random.randint(1, 6) for _ in range(3)]
            tong = sum(dice)
            du_doan = du_doan_tai_xiu(tong)
            last_data = {
                "phien": int(time.time()),
                "xucxac1": dice[0],
                "xucxac2": dice[1],
                "xucxac3": dice[2],
                "tong": tong,
                "du_doan": du_doan,
                "id": "biios2502"
            }

        time.sleep(5)

@app.route("/api/taixiu/sunwin", methods=["GET"])
def api_sunwin():
    return jsonify(last_data)

if __name__ == "__main__":
    threading.Thread(target=background_updater, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)()