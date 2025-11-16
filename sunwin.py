from flask import Flask, jsonify
import requests
import time
import threading
from collections import deque
from datetime import datetime
import json

app = Flask(__name__)

# ===================================
# 🔹 CLASS QUẢN LÝ DỰ ĐOÁN VÀ HIỆU SUẤT
# ===================================

class TaiXiuPredictor:
    def __init__(self):
        # Biến toàn cục (tối ưu hóa thành thuộc tính lớp)
        self.last_data = {
            "Phiên": None, "Xúc_xắc_1": 0, "Xúc_xắc_2": 0, "Xúc_xắc_3": 0,
            "Tổng": 0, "Dự_đoán": "Đang khởi động...",
            "Thuật_toán": "Meta-Adaptive", "Độ_tin_cậy": 50, "ID": "docquyen"
        }
        self.history = deque(maxlen=100)  # Lịch sử Tài/Xỉu (T/X)
        self.totals = deque(maxlen=100)   # Lịch sử Tổng điểm
        self.algorithm_names = []
        self.predictions_log = {}         # {phien_id: {algo_name: prediction, ...}}
        self.algo_performance = {}        # {algo_name: {'wins': 0, 'total': 0, 'rate': 0.0}}
        self.MAX_HISTORY_SIZE = 20        # Theo dõi hiệu suất trên 20 phiên gần nhất

        # Khởi tạo các thuật toán
        self._initialize_algorithms()

    # --- 15 THUẬT TOÁN ĐỊNH LƯỢNG (Không thay đổi, đảm bảo tính deterministic) ---
    def _algo_v1_bet_cung(self, h, t):
        if len(h) < 4: return {"du_doan": "Tài", "do_tin_cay": 84}
        if all(val == h[-1] for val in h[-4:]):
            return {"du_doan": h[-1], "do_tin_cay": 96} # 4 liên tiếp, bám cầu
        return {"du_doan": h[-1], "do_tin_cay": 78}

    def _algo_v2_dao_lien_tuc(self, h, t):
        if len(h) < 6: return {"du_doan": "Tài", "do_tin_cay": 50}
        pattern = "".join("T" if val == "Tài" else "X" for val in h[-4:])
        if pattern == "TXTX" or pattern == "XTXT":
            du_doan = "Tài" if pattern[-1] == "X" else "Xỉu" # Đảo ngược
            return {"du_doan": du_doan, "do_tin_cay": 99}
        return {"du_doan": h[-1], "do_tin_cay": 77}

    def _algo_v3_nhip212(self, h, t):
        if len(h) < 5: return {"du_doan": "Xỉu", "do_tin_cay": 60}
        tail = h[-3:] # [A, B, A] -> dự đoán B ngược lại
        if tail[0] == tail[2] and tail[1] != tail[0]:
            return {"du_doan": tail[1], "do_tin_cay": 89} # Dự đoán cái khác B
        return {"du_doan": h[-1], "do_tin_cay": 72}

    def _algo_v4_cau_gay(self, h, t):
        if len(h) < 6: return {"du_doan": "Tài", "do_tin_cay": 60}
        if all(val == h[-2] for val in h[-5:-1]) and h[-1] != h[-2]:
            return {"du_doan": h[-2], "do_tin_cay": 92} # Gãy 1 nhịp, dự đoán quay lại
        return {"du_doan": h[-1], "do_tin_cay": 70}

    def _algo_v5_tong_dong(self, h, t):
        if len(t) < 4: return {"du_doan": "Tài", "do_tin_cay": 80}
        mean_total = sum(t[-4:]) / 4
        if mean_total > 11.5: return {"du_doan": "Tài", "do_tin_cay": 87}
        elif mean_total < 9.5: return {"du_doan": "Xỉu", "do_tin_cay": 84}
        return {"du_doan": h[-1], "do_tin_cay": 57}

    def _algo_v6_chan_le(self, h, t):
        if len(t) < 5: return {"du_doan": "Tài", "do_tin_cay": 50}
        even = sum(1 for val in t[-5:] if val % 2 == 0)
        if even >= 4: return {"du_doan": "Xỉu", "do_tin_cay": 85} # Tổng chẵn nhiều -> Xỉu
        if 5 - even >= 4: return {"du_doan": "Tài", "do_tin_cay": 81} # Tổng lẻ nhiều -> Tài
        return {"du_doan": h[-1], "do_tin_cay": 78}

    def _algo_v7_xu_huong(self, h, t):
        if len(t) < 3: return {"du_doan": "Xỉu", "do_tin_cay": 60}
        trend = t[-1] - t[-3]
        if trend >= 3: return {"du_doan": "Tài", "do_tin_cay": 88}
        if trend <= -3: return {"du_doan": "Xỉu", "do_tin_cay": 89}
        return {"du_doan": h[-1], "do_tin_cay": 75}

    def _algo_v8_nguoc_cau(self, h, t):
        if len(h) < 5: return {"du_doan": "Tài", "do_tin_cay": 65}
        # Nếu đang có cầu dài (4+ liên tiếp), dự đoán ngược lại
        if all(val == h[-1] for val in h[-4:]):
            du_doan = "Xỉu" if h[-1] == "Tài" else "Tài"
            return {"du_doan": du_doan, "do_tin_cay": 90}
        return {"du_doan": h[-1], "do_tin_cay": 70}

    def _algo_v9_pattern_ai(self, h, t):
        if len(h) < 6: return {"du_doan": "Tài", "do_tin_cay": 50}
        p = "".join("T" if val == "Tài" else "X" for val in h[-6:])
        table = {"TTTTTX": "Xỉu", "XXXXX": "Tài", "TXTXTX": "Tài", "XTXTXT": "Xỉu"}
        for key, value in table.items():
            if p.endswith(key):
                 return {"du_doan": value, "do_tin_cay": 93}
        return {"du_doan": h[-1], "do_tin_cay": 74}

    def _algo_v10_realbalance(self, h, t):
        if len(h) < 5: return {"du_doan": "Tài", "do_tin_cay": 50}
        mean_total = sum(t[-5:]) / max(1, len(t[-5:]))
        if mean_total >= 11.5:
            base = "Tài"
        elif mean_total <= 9.5:
            base = "Xỉu"
        else:
            base = h[-1]
        return {"du_doan": base, "do_tin_cay": 85}

    def _algo_v11_hybrid_smart(self, h, t):
        if len(h) < 6: return {"du_doan": "Tài", "do_tin_cay": 50}
        mean_total = sum(t[-4:]) / 4
        even = sum(1 for val in t[-5:] if val % 2 == 0)
        last = h[-1]
        if even >= 4: base = "Xỉu"
        elif mean_total > 11: base = "Tài"
        elif mean_total < 10: base = "Xỉu"
        else: base = last
        return {"du_doan": base, "do_tin_cay": 88}

    def _algo_v12_momentum(self, h, t):
        if len(t) < 4: return {"du_doan": "Tài", "do_tin_cay": 60}
        delta = [t[i] - t[i-1] for i in range(1, len(t))]
        if len(delta) >= 2:
            if delta[-1] >= 2 and delta[-2] >= 1: return {"du_doan": "Tài", "do_tin_cay": 92}
            if delta[-1] <= -2 and delta[-2] <= -1: return {"du_doan": "Xỉu", "do_tin_cay": 92}
        return {"du_doan": h[-1], "do_tin_cay": 75}

    def _algo_v13_adaptive_ai(self, h, t):
        if len(h) < 5: return {"du_doan": "Tài", "do_tin_cay": 50}
        success_T = h[-5:].count("Tài")
        success_X = h[-5:].count("Xỉu")
        bias = "Tài" if success_T > success_X else "Xỉu"
        return {"du_doan": bias, "do_tin_cay": 80}

    def _algo_v14_pattern_deep(self, h, t):
        if len(h) < 8: return {"du_doan": "Tài", "do_tin_cay": 50}
        seq = "".join("T" if val == "Tài" else "X" for val in h[-8:])
        if "TTTTT" in seq: return {"du_doan": "Tài", "do_tin_cay": 94}
        if "XXXXX" in seq: return {"du_doan": "Xỉu", "do_tin_cay": 95}
        return {"du_doan": h[-1], "do_tin_cay": 78}

    def _algo_v15_hyperbalance_pro(self, h, t):
        if len(h) < 6: return {"du_doan": "Tài", "do_tin_cay": 50}
        mean_total = sum(t[-6:]) / 6
        seq = "".join("T" if val == "Tài" else "X" for val in h[-6:])
        if "TTTT" in seq: base = "Tài"
        elif "XXXX" in seq: base = "Xỉu"
        elif mean_total > 11: base = "Tài"
        elif mean_total < 10: base = "Xỉu"
        else: base = h[-1]
        return {"du_doan": base, "do_tin_cay": 85}
    # ------------------------------------------------------------------------

    def _initialize_algorithms(self):
        """Đăng ký các thuật toán và khởi tạo bộ theo dõi hiệu suất."""
        self.algorithms = {
            "v1_BetCung": self._algo_v1_bet_cung,
            "v2_DaoLienTuc": self._algo_v2_dao_lien_tuc,
            "v3_Nhip212": self._algo_v3_nhip212,
            "v4_CauGay": self._algo_v4_cau_gay,
            "v5_TongDong": self._algo_v5_tong_dong,
            "v6_ChanLe": self._algo_v6_chan_le,
            "v7_XuHuong": self._algo_v7_xu_huong,
            "v8_NguocCau": self._algo_v8_nguoc_cau,
            "v9_PatternAI": self._algo_v9_pattern_ai,
            "v10_RealBalance": self._algo_v10_realbalance,
            "v11_HybridSmart": self._algo_v11_hybrid_smart,
            "v12_Momentum": self._algo_v12_momentum,
            "v13_AdaptiveAI": self._algo_v13_adaptive_ai,
            "v14_PatternDeep": self._algo_v14_pattern_deep,
            "v15_HyperBalancePro": self._algo_v15_hyperbalance_pro,
        }
        self.algorithm_names = list(self.algorithms.keys())
        for name in self.algorithm_names:
            self.algo_performance[name] = {'wins': 0, 'total': 0, 'rate': 0.0}

    def _evaluate_previous_predictions(self, phien_id, actual_result):
        """Đánh giá và cập nhật hiệu suất dựa trên kết quả thực tế."""
        # Lấy dự đoán đã lưu của phiên trước
        predictions_of_prev_phien = self.predictions_log.get(phien_id - 1)
        if not predictions_of_prev_phien:
            return

        for algo_name in self.algorithm_names:
            if algo_name not in predictions_of_prev_phien:
                continue

            # Cập nhật Wins/Total cho thuật toán
            is_correct = (predictions_of_prev_phien[algo_name]["du_doan"] == actual_result)
            
            # Khởi tạo hoặc cập nhật trạng thái
            if algo_name not in self.algo_performance:
                 self.algo_performance[algo_name] = {'wins': 0, 'total': 0, 'rate': 0.0, 'log': deque(maxlen=self.MAX_HISTORY_SIZE)}
            
            if 'log' not in self.algo_performance[algo_name]:
                 self.algo_performance[algo_name]['log'] = deque(maxlen=self.MAX_HISTORY_SIZE)

            self.algo_performance[algo_name]['log'].append(is_correct)

            # Tính lại tỷ lệ thắng dựa trên log 20 phiên gần nhất
            log = self.algo_performance[algo_name]['log']
            total = len(log)
            wins = log.count(True)
            rate = (wins / total) * 100 if total > 0 else 50.0

            self.algo_performance[algo_name]['wins'] = wins
            self.algo_performance[algo_name]['total'] = total
            self.algo_performance[algo_name]['rate'] = round(rate, 2)


    def _get_best_prediction(self):
        """Chạy tất cả thuật toán và chọn ra dự đoán từ thuật toán có Win Rate cao nhất."""
        if len(self.history) < self.MAX_HISTORY_SIZE:
            # Nếu chưa đủ dữ liệu để đánh giá hiệu suất, dùng thuật toán có Conf. tĩnh cao nhất
            return self._run_all_and_select_by_confidence()

        # Bước 1: Chạy tất cả thuật toán cho phiên tiếp theo
        current_predictions = {}
        for name, func in self.algorithms.items():
            try:
                # Chạy thuật toán với history và totals hiện tại (cho phiên tiếp theo)
                current_predictions[name] = func(list(self.history), list(self.totals))
            except Exception as e:
                # Bỏ qua nếu có lỗi
                print(f"Lỗi chạy thuật toán {name}: {e}")

        # Bước 2: Ghép Win Rate thực tế vào các dự đoán
        weighted_predictions = []
        for name, pred_data in current_predictions.items():
            rate = self.algo_performance.get(name, {'rate': 50.0})['rate']
            weighted_predictions.append({
                "name": name,
                "prediction": pred_data["du_doan"],
                "confidence": round((pred_data["do_tin_cay"] + rate) / 2, 1),
                "win_rate": rate,
            })

        # Bước 3: Chọn dự đoán từ thuật toán có WIN RATE cao nhất
        if not weighted_predictions:
            return {"du_doan": "Tài", "do_tin_cay": 50, "Thuật_toán": "Lỗi hệ thống"}

        best_pred = max(weighted_predictions, key=lambda x: x["win_rate"])
        
        # Lưu lại tất cả dự đoán của phiên này để đánh giá khi có kết quả
        next_phien_id = self.last_data["Phiên"] + 1 if self.last_data["Phiên"] else 1
        self.predictions_log[next_phien_id] = {p['name']: {'du_doan': p['prediction']} for p in weighted_predictions}

        return {
            "du_doan": best_pred["prediction"],
            "do_tin_cay": best_pred["confidence"],
            "Thuật_toán": f"Meta: {best_pred['name']} (WinRate {best_pred['win_rate']}%)"
        }

    def _run_all_and_select_by_confidence(self):
        """Fallback: Nếu chưa đủ dữ liệu, chọn theo độ tin cậy tĩnh cao nhất."""
        results = []
        for name, func in self.algorithms.items():
            try:
                r = func(list(self.history), list(self.totals))
                results.append((name, r))
            except:
                continue
        
        best = max(results, key=lambda x: x[1]["do_tin_cay"]) if results else ("None", {"du_doan":"Tài","do_tin_cay":50})
        
        # Lưu lại tất cả dự đoán của phiên này để đánh giá khi có kết quả
        next_phien_id = self.last_data["Phiên"] + 1 if self.last_data["Phiên"] else 1
        self.predictions_log[next_phien_id] = {r[0]: {'du_doan': r[1]['du_doan']} for r in results}
        
        return {
            "du_doan": best[1]["du_doan"],
            "do_tin_cay": best[1]["do_tin_cay"],
            "Thuật_toán": f"Startup: {best[0]}"
        }

    # ===================================
    # 🔹 API GỐC (chỉ lấy xúc xắc, không lấy dự đoán)
    # ===================================
    def _get_taixiu_data(self):
        """Lấy dữ liệu thô từ API bên ngoài."""
        url = "https://sunwinsaygex-8616.onrender.com/api/taixiu/sunwin"
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
            print(f"[❌] Lỗi gọi API gốc: {e}")
        return None

    # ===================================
    # 🔹 Luồng cập nhật nền (Core Logic)
    # ===================================
    def background_updater(self):
        """Chạy nền để liên tục cập nhật dữ liệu và dự đoán."""
        last_phien = None
        while True:
            try:
                data = self._get_taixiu_data()
                if data:
                    phien, dice, tong = data
                    ket_qua = "Tài" if tong >= 11 else "Xỉu"
                    
                    if phien != last_phien and phien is not None:
                        print(f"--- KẾT QUẢ PHIÊN {last_phien} VỪA RA: {ket_qua} ---")
                        
                        # 1. Đánh giá hiệu suất của tất cả thuật toán cho phiên đã kết thúc (phien - 1)
                        if last_phien is not None:
                            self._evaluate_previous_predictions(last_phien, ket_qua)
                        
                        # 2. Cập nhật lịch sử và totals
                        self.totals.append(tong)
                        self.history.append(ket_qua)
                        
                        # 3. Chạy Meta-Algorithm để tìm dự đoán cho phiên tiếp theo (phien)
                        prediction_result = self._get_best_prediction()

                        # 4. Cập nhật dữ liệu trả về API
                        self.last_data.update({
                            "Phiên": phien,
                            "Xúc_xắc_1": dice[0],
                            "Xúc_xắc_2": dice[1],
                            "Xúc_xắc_3": dice[2],
                            "Tổng": tong,
                            "Dự_đoán": prediction_result["du_doan"],
                            "Độ_tin_cậy": prediction_result["do_tin_cay"],
                            "Thuật_toán": prediction_result["Thuật_toán"],
                        })

                        last_phien = phien
                        print(f"[✅] Phiên {phien} | 🎲 {dice} | Tổng {tong} | DỰ ĐOÁN KẾ TIẾP: {prediction_result['du_doan']} ({prediction_result['Thuật_toán']})")

                    elif phien == last_phien and self.last_data["Phiên"] is not None:
                        # Trường hợp đang chờ kết quả, cập nhật thời gian
                        now = datetime.now().strftime("%H:%M:%S")
                        current_phien = self.last_data["Phiên"]
                        print(f"[⏳] Chờ kết quả phiên {current_phien+1} | Giờ cập nhật: {now}", end='\r')


            except Exception as e:
                print(f"\n[❌] Lỗi trong luồng cập nhật chính: {e}")
                
            time.sleep(5) # Kiểm tra mỗi 5 giây

# ===================================
# 🔹 Khởi tạo và Chạy server
# ===================================

predictor = TaiXiuPredictor()

@app.route("/api/taixiu/sunwin", methods=["GET"])
def api_sunwin():
    """Endpoint trả về dữ liệu phiên mới nhất và dự đoán thông minh."""
    return jsonify(predictor.last_data)

if __name__ == "__main__":
    print("🚀 Đang chạy API /api/taixiu/sunwin với Thuật Toán Meta-Adaptive...")
    threading.Thread(target=predictor.background_updater, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)
