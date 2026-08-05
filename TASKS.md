# 📋 Danh Sách Nhiệm Vụ Hoàn Thiện Module (Task List Từ A Đến Z)

> **Tài liệu theo dõi tiến độ nâng cấp module Equipment Management theo yêu cầu từ `REVIEW.md`**
> *Mục tiêu: Đạt chuẩn Production-Ready trên Odoo 19.0, toàn vẹn dữ liệu ở Backend, bảo mật chặt chẽ và có bộ Unit Test tự động.*

---

## 🎯 Tổng Hợp Tiến Độ

- [ ] **Giai đoạn 1: Khóa Vòng Đời & Toàn Vẹn Dữ Liệu ở Backend (Ưu tiên P0)**
- [ ] **Giai đoạn 2: Ràng Buộc Dữ Liệu & Chuẩn Tiền Tệ (Ưu tiên P1)**
- [ ] **Giai đoạn 3: Tự Động Hóa Nghiệp Vụ & Audit Trail Chatter (Ưu tiên P1)**
- [ ] **Giai đoạn 4: Chuẩn Hóa Phân Quyền & Cú Pháp Odoo 19**
- [ ] **Giai đoạn 5: Xây Dựng Bộ Test Tự Động Toàn Diện (Automated Unit Tests)**
- [ ] **Giai đoạn 6: Kiểm Thử Thực Tế, Đồng Bộ Tài Liệu & Git Push**

---

## 🚀 Chi Tiết Từng Hạng Mục Thực Hiện

### Giai đoạn 1: Khóa Vòng Đời & Toàn Vẹn Dữ Liệu ở Backend (P0)

- [ ] **1.1 Khóa chặt Model Phiếu Bảo Trì (`models/equipment_maintenance.py`)**

  - [ ] Thêm validation kiểm tra trạng thái đầu vào của thiết bị: Chỉ cho phép tạo bảo trì khi thiết bị ở trạng thái `available` (Trong kho) hoặc `broken` (Hư hỏng).
  - [ ] Chặn đưa thiết bị đang `assigned` (Đang sử dụng), `liquidated` (Đã thanh lý) hoặc `lost` (Mất) vào phiếu bảo trì.
  - [ ] Chống trùng lặp: Ngăn chặn tạo/xác nhận nhiều phiếu bảo trì đang chạy (`in_progress`) cho cùng 1 thiết bị.
  - [ ] Chống "hồi sinh" thiết bị: Khi hoàn thành bảo trì (`action_done`), kiểm tra nếu thiết bị đã bị chuyển trạng thái khác ngoài `maintenance` (như đã thanh lý) thì báo lỗi và dừng thực thi.
  - [ ] Bổ sung Backend Guard `unlink()`: Chỉ cho phép xóa phiếu ở trạng thái `draft` hoặc `cancelled`.
  - [ ] Bổ sung Backend Guard `write()`: Khóa không cho sửa các trường `equipment_id`, `vendor_id`, `request_date`, `cost` khi phiếu không còn là `draft`.
- [ ] **1.2 Khóa chặt Model Phiếu Thanh Lý (`models/equipment_liquidation.py`)**

  - [ ] Thêm validation chặn thanh lý nếu thiết bị đang có phiếu bảo trì mở (`in_progress`). Bắt buộc phải hoàn tất hoặc hủy bảo trì trước.
  - [ ] Bổ sung Backend Guard `unlink()`: Ngăn xóa phiếu đã duyệt (`approved`).
  - [ ] Bổ sung Backend Guard `write()`: Khóa không cho sửa thông tin thiết bị, ngày thanh lý, giá bán khi phiếu đã ở trạng thái `approved`.
- [ ] **1.3 Khóa chặt Model Phiếu Cấp Phát (`models/allocation.py`)**

  - [ ] Bổ sung Backend Guard `unlink()`: Chỉ cho phép xóa phiếu `draft`. Nghiêm cấm xóa phiếu đã xác nhận (`confirmed`) hoặc đã thu hồi (`returned`) để bảo vệ chứng từ gốc.
  - [ ] Bổ sung Backend Guard `write()`: Chặn chỉnh sửa `equipment_id`, `employee_id`, `date` khi phiếu đã xác nhận (`confirmed`).
- [ ] **1.4 Khóa chặt Model Phiếu Thu Hồi (`models/equipment_return.py`)**

  - [ ] Bổ sung Backend Guard `write()`: Chặn chỉnh sửa dữ liệu khi phiếu đã xác nhận hoàn thành (`returned`) hoặc `cancelled`.

---

### Giai đoạn 2: Ràng Buộc Dữ Liệu & Chuẩn Tiền Tệ (P1)

- [ ] **2.1 Chuẩn hóa Model Thiết Bị (`models/equipment.py`)**

  - [ ] Thêm `_sql_constraints`:
    - `unique_equipment_code`: Ràng buộc Unique cho Mã thiết bị (`code`).
    - `unique_serial_number`: Ràng buộc Unique cho Số Serial (`serial_number`).
  - [ ] Thêm `@api.constrains`:
    - Giá mua không âm (`purchase_price >= 0`).
    - Giá trị thu hồi hợp lệ (`salvage_value >= 0` và `salvage_value <= purchase_price`).
    - Thời gian khấu hao hợp lệ (`useful_life_years > 0`).
  - [ ] Thêm trường `currency_id` (`res.currency`) mặc định theo công ty hiện tại.
  - [ ] Chuyển các trường tiền tệ từ `Float` sang `Monetary`: `purchase_price`, `salvage_value`, `annual_depreciation`, `accumulated_depreciation`, `remaining_value`.
- [ ] **2.2 Chuẩn hóa Model Bảo Trì & Thanh Lý**

  - [ ] `equipment_maintenance.py`: Thêm ràng buộc `cost >= 0` và `completion_date >= request_date`. Thêm `currency_id` và đổi `cost` sang `Monetary`.
  - [ ] `equipment_liquidation.py`: Thêm ràng buộc `price >= 0`. Thêm `currency_id` và đổi `price` sang `Monetary`.

---

### Giai đoạn 3: Tự Động Hóa Nghiệp Vụ & Audit Trail Chatter (P1)

- [ ] **3.1 Tự động tạo Phiếu Bảo Trì từ Phiếu Thu Hồi**

  - [ ] Khi xác nhận thu hồi (`action_confirm`) với tình trạng `condition == 'maintenance'`, tự động tạo 1 phiếu `company.equipment.maintenance` ở trạng thái Nháp.
  - [ ] Ghi nhận liên kết giữa phiếu Thu hồi và phiếu Bảo trì vừa tạo.
  - [ ] Thêm Smart button trên Form Thu hồi để điều hướng nhanh đến Phiếu bảo trì tương ứng.
- [ ] **3.2 Kế thừa Module Mail & Tích Hợp Chatter**

  - [ ] Cập nhật `__manifest__.py`: Thêm `"mail"` vào danh sách `"depends"`.
  - [ ] Thêm kế thừa `_inherit = ['mail.thread', 'mail.activity.mixin']` cho tất cả 5 models.
  - [ ] Bật tính năng `tracking=True` cho các trường quan trọng (`state`, `employee_id`, `cost`, `price`, `vendor_id`).
  - [ ] Cập nhật toàn bộ các file Form view trong `views/*.xml`: Thêm component `<chatter/>` chuẩn Odoo 19.

---

### Giai đoạn 4: Chuẩn Hóa Phân Quyền & Cú Pháp Odoo 19

- [ ] **4.1 Cập nhật Phân Quyền XML (`security/equipment_security.xml`)**

  - [ ] Đổi toàn bộ cú pháp Many2many tuple cũ `[(4, ref(...))]` sang chuẩn Odoo 19: `eval="[Command.link(ref(...))]"` (với `from odoo import Command`).
  - [ ] Rà soát Record Rules của nhân viên (`base.group_user`) đảm bảo chỉ lọc đúng bản ghi của chính mình: `[('employee_id.user_id', '=', user.id)]`.
- [ ] **4.2 Chuẩn hóa Menu & Access Rights**

  - [ ] Đảm bảo phân cấp Menu rõ ràng giữa Nhân viên (`group_equipment_user`) và Quản lý (`group_equipment_manager`).

---

### Giai đoạn 5: Xây Dựng Bộ Test Tự Động Toàn Diện (Automated Unit Tests)

- [ ] **5.1 Khởi tạo thư mục và cấu trúc test**
  - [ ] Tạo file `tests/__init__.py`.
- [ ] **5.2 Viết các kịch bản test chi tiết:**
  - [ ] `tests/test_equipment_lifecycle.py`: Test toàn bộ vòng đời (Tạo -> Cấp phát -> Thu hồi -> Bảo trì -> Thanh lý), kiểm tra chuyển trạng thái hợp lệ/không hợp lệ.
  - [ ] `tests/test_guards_and_integrity.py`: Test các hàm guard `write()` và `unlink()` ngăn chặn chỉnh sửa/xóa trái phép khi chứng từ đã hoàn thành.
  - [ ] `tests/test_constraints.py`: Test bắt lỗi Unique mã/serial, bắt lỗi số âm, bắt lỗi logic ngày tháng.
  - [ ] `tests/test_depreciation.py`: Test tính toán tự động khấu hao năm, tỷ lệ khấu hao, khấu hao lũy kế và giá trị còn lại.
  - [ ] `tests/test_security_rules.py`: Test quyền truy cập theo từng nhóm người dùng và Record Rules.

---
