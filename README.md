# Mô tả trò chơi


Trò chơi gồm có **2 người chơi**:  
- Người chạy chương trình (Player)  
- Bot  

Mỗi bên được cấp **$100** khi bắt đầu.  
Sau **5 ván**, ai **nhiều tiền hơn** sẽ là **người chiến thắng**.

---

## 🧩 Các giai đoạn phát triển

### **Phase 1: Thuật toán tìm kiếm MiniMax**

**Mục tiêu:**  
Bot có thể đưa ra các quyết định hợp lý trong trò chơi:
- **Theo (Call)**
- **Cược thêm (Raise)**
- **Bỏ (Fold)**

#### **Phase 1.1:** Thiết lập trò chơi
- Xây dựng các hàm cần thiết (khởi tạo, chia bài, xử lý lượt, cập nhật tiền, v.v.)
- Đảm bảo luồng chơi cơ bản giữa người và bot.

#### **Phase 1.2:** Thêm thuật toán tìm kiếm MiniMax
- Áp dụng MiniMax để giúp bot dự đoán và tối ưu hóa quyết định dựa trên trạng thái trò chơi.
- Có thể mở rộng với **alpha-beta pruning** để tối ưu hiệu suất.
- Nếu cược thêm, số  tiền là cố  định 

---

📌 **Kết quả mong đợi:**  
Sau khi hoàn thành cả hai giai đoạn, bot có khả năng:
- Đưa ra quyết định chiến lược (MiniMax)