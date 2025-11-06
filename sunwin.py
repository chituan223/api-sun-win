from flask import Flask, jsonify
import requests, time, threading
from datetime import datetime
from collections import deque

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
    "Thuật_toán": "tuấn đệ của cha phú",
    "Độ_tin_cậy": 0,
    "ID": "docquyen"
}

history = deque(maxlen=100)
totals = deque(maxlen=100)
win_log = deque(maxlen=100)

# ===================================
# 🔹 15 THUẬT TOÁN THÔNG MINH
# ===================================
def algo_v1_bet_cung(history, totals, win_log):
    if len(history) < 4: return {"du_doan": "Tài", "do_tin_cay": 84}
    if all(h == history[-1] for h in history[-4:]):
        return {"du_doan": history[-1], "do_tin_cay": 96}
    return {"du_doan": history[-1], "do_tin_cay": 78}

def algo_v2_dao_lien_tuc(history, totals, win_log):
    if len(history) < 6: return {"du_doan": "Tài", "do_tin_cay": 50}
    pattern = "".join("T" if h == "Tài" else "X" for h in history[-6:])
    if pattern.endswith(("TXTX", "XTXT")):
        du_doan = "Tài" if pattern[-1] == "X" else "Xỉu"
        return {"du_doan": du_doan, "do_tin_cay": 99}
    return {"du_doan": history[-1], "do_tin_cay": 77}

def algo_v3_nhip212(history, totals, win_log):
    if len(history) < 5: return {"du_doan": "Xỉu", "do_tin_cay": 60}
    tail = history[-3:]
    if tail[0] == tail[2] and tail[1] != tail[0]:
        return {"du_doan": tail[0], "do_tin_cay": 89}
    return {"du_doan": history[-1], "do_tin_cay": 72}

def algo_v4_cau_gay(history, totals, win_log):
    if len(history) < 6: return {"du_doan": "Tài", "do_tin_cay": 60}
    if all(h == history[-5] for h in history[-6:-1]) and history[-1] != history[-2]:
        return {"du_doan": history[-1], "do_tin_cay": 92}
    return {"du_doan": history[-1], "do_tin_cay": 70}

def algo_v5_tong_dong(history, totals, win_log):
    if len(totals) < 4: return {"du_doan": "Tài", "do_tin_cay": 80}
    mean_total = sum(totals[-4:]) / 4
    if mean_total > 10.8: return {"du_doan": "Tài", "do_tin_cay": 87}
    elif mean_total < 10.2: return {"du_doan": "Xỉu", "do_tin_cay": 84}
    return {"du_doan": history[-1], "do_tin_cay": 57}

def algo_v6_chan_le(history, totals, win_log):
    if len(totals) < 5: return {"du_doan": "Tài", "do_tin_cay": 50}
    even = sum(1 for t in totals[-6:] if t % 2 == 0)
    odd = 6 - even
    if even >= 4: return {"du_doan": "Xỉu", "do_tin_cay": 85}
    if odd >= 4: return {"du_doan": "Tài", "do_tin_cay": 81}
    return {"du_doan": history[-1], "do_tin_cay": 78}

def algo_v7_xu_huong(history, totals, win_log):
    if len(totals) < 3: return {"du_doan": "Xỉu", "do_tin_cay": 60}
    trend = totals[-1] - totals[-3]
    if trend >= 2: return {"du_doan": "Tài", "do_tin_cay": 88}
    if trend <= -2: return {"du_doan": "Xỉu", "do_tin_cay": 89}
    return {"du_doan": history[-1], "do_tin_cay": 100}

def algo_v8_winrate(history, totals, win_log):
    win_rate = win_log[-10:].count(True)/max(1,len(win_log[-10:]))
    return {"du_doan": "Tài" if win_rate < 0.5 else "Xỉu",
            "do_tin_cay": round(75 + win_rate*20,1)}

def algo_v9_pattern_ai(history, totals, win_log):
    if len(history) < 6: return {"du_doan": "Tài", "do_tin_cay": 50}
    p = "".join("T" if h=="Tài" else "X" for h in history[-6:])
    table = {"TTTTTX":"Xỉu","XXXXX":"Tài","TXTXTX":"Tài","XTXTXT":"Xỉu"}
    if p in table:
        return {"du_doan": table[p], "do_tin_cay": 90}
    return {"du_doan": history[-1], "do_tin_cay": 74}

def algo_v10_realbalance(history, totals, win_log):
    if len(history) < 5: return {"du_doan":"Tài","do_tin_cay":50}
    mean_total = sum(totals[-5:]) / max(1,len(totals[-5:]))
    last = history[-1]
    base = "Tài" if mean_total>=11 else "Xỉu" if mean_total<=10 else last
    win_rate = win_log[-20:].count(True)/max(1,len(win_log[-20:]))
    return {"du_doan": base, "do_tin_cay": round(80+win_rate*15,1)}

def algo_v11_hybrid_smart(history, totals, win_log):
    if len(history)<6: return {"du_doan":"Tài","do_tin_cay":50}
    mean_total=sum(totals[-4:])/4
    even=sum(1 for t in totals[-5:] if t%2==0)
    last=history[-1]
    if even>=4: base="Xỉu"
    elif mean_total>11: base="Tài"
    elif mean_total<10: base="Xỉu"
    else: base=last
    win_rate=win_log[-10:].count(True)/max(1,len(win_log[-10:]))
    return {"du_doan":base,"do_tin_cay":round(85+win_rate*10,1)}

def algo_v12_momentum(history, totals, win_log):
    if len(totals)<4: return {"du_doan":"Tài","do_tin_cay":60}
    delta=[totals[i]-totals[i-1] for i in range(1,len(totals))]
    if delta[-1]>1 and delta[-2]>1: return {"du_doan":"Tài","do_tin_cay":92}
    if delta[-1]<-1 and delta[-2]<-1: return {"du_doan":"Xỉu","do_tin_cay":92}
    return {"du_doan":history[-1],"do_tin_cay":75}

def algo_v13_adaptive_ai(history, totals, win_log):
    if len(history)<5: return {"du_doan":"Tài","do_tin_cay":50}
    success=win_log[-15:].count(True)
    fail=len(win_log[-15:])-success
    bias="Tài" if success<fail else "Xỉu"
    return {"du_doan":bias,"do_tin_cay":round(80+(abs(success-fail)/15)*15,1)}

def algo_v14_pattern_deep(history, totals, win_log):
    if len(history)<8: return {"du_doan":"Tài","do_tin_cay":50}
    seq="".join("T" if h=="Tài" else "X" for h in history[-8:])
    if "TTTT" in seq: return {"du_doan":"Tài","do_tin_cay":94}
    if "XXXX" in seq: return {"du_doan":"Xỉu","do_tin_cay":95}
    return {"du_doan":history[-1],"do_tin_cay":78}

def algo_v15_hyperbalance_pro(history, totals, win_log):
    if len(history)<6: return {"du_doan":"Tài","do_tin_cay":50}
    mean_total=sum(totals[-6:])/6
    win_rate=win_log[-15:].count(True)/max(1,len(win_log[-15:]))
    seq="".join("T" if h=="Tài" else "X" for h in history[-6:])
    if "TTTT" in seq: return {"du_doan":"Tài","do_tin_cay":round(95+win_rate*3,1)}
    if "XXXX" in seq: return {"du_doan":"Xỉu","do_tin_cay":round(95+win_rate*3,1)}
    base="Tài" if mean_total>11 else "Xỉu" if mean_total<10 else history[-1]
    return {"du_doan":base,"do_tin_cay":round(85+win_rate*10,1)}

algorithms = [
    algo_v1_bet_cung, algo_v2_dao_lien_tuc, algo_v3_nhip212, algo_v4_cau_gay,
    algo_v5_tong_dong, algo_v6_chan_le, algo_v7_xu_huong, algo_v8_winrate,
    algo_v9_pattern_ai, algo_v10_realbalance, algo_v11_hybrid_smart,
    algo_v12_momentum, algo_v13_adaptive_ai, algo_v14_pattern_deep,
    algo_v15_hyperbalance_pro
]

# ===================================
# 🔹 API GỐC (chỉ lấy xúc xắc, không lấy dự đoán)
# ===================================
def get_taixiu_data():
    url = "https://sunwinsaygex-ew87.onrender.com/api/taixiu/sunwin"
    try:
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            data = res.json()
            phien = data.get("phien")
            x1 = data.get("xuc_xac_1", 0)
            x2 = data.get("xuc_xac_2", 0)
            x3 = data.get("xuc_xac_3", 0)
            tong = data.get("tong", x1 + x2 + x3)
            return phien, [x1, x2, x3], tong
    except Exception as e:
        print(f"[❌] Lỗi gọi API: {e}")
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
                ket_qua = "Tài" if tong >= 11 else "Xỉu"
                totals.append(tong)
                history.append(ket_qua)
                if len(history) > 1:
                    win_log.append(history[-1] == history[-2])

                # ✅ Chạy qua 15 thuật toán và chọn cái có độ tin cậy cao nhất
                results = []
                for func in algorithms:
                    try:
                        r = func(list(history), list(totals), list(win_log))
                        results.append((func.__name__, r))
                    except:
                        continue

                best = max(results, key=lambda x: x[1]["do_tin_cay"]) if results else ("None", {"du_doan":"Tài","do_tin_cay":50})

                last_data.update({
                    "Phiên": phien,
                    "Xúc_xắc_1": dice[0],
                    "Xúc_xắc_2": dice[1],
                    "Xúc_xắc_3": dice[2],
                    "Tổng": tong,
                    "Dự_đoán": best[1]["du_doan"],
                    "Độ_tin_cậy": best[1]["do_tin_cay"],
                    "ID": "docquyen"
                })
                print(f"[✅] Phiên {phien} | 🎲 {dice} | Tổng {tong} → {best[1]['du_doan']} ({best[0]} {best[1]['do_tin_cay']}%)")
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
