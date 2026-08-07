# 📋 Danh Sách Nhiệm Vụ Hoàn Thiện Module (Task List Từ A Đến Z)

> **Tài liệu theo dõi tiến độ nâng cấp module Equipment Management theo yêu cầu từ `REVIEW.md`**
> *Mục tiêu: Đạt chuẩn Production-Ready trên Odoo 19.0, toàn vẹn dữ liệu ở Backend, bảo mật chặt chẽ và có bộ Unit Test tự động.*

---

## 🎯 Tổng Hợp Tiến Độ

- [X] **Giai đoạn 1: Khóa Vòng Đời & Toàn Vẹn Dữ Liệu ở Backend (Ưu tiên P0)**
- [X] **Giai đoạn 2: Ràng Buộc Dữ Liệu & Chuẩn Tiền Tệ (Ưu tiên P1)**
- [ ] **Giai đoạn 3: Tự Động Hóa Nghiệp Vụ & Audit Trail Chatter (Ưu tiên P1)**
- [ ] **Giai đoạn 4: Chuẩn Hóa Phân Quyền & Cú Pháp Odoo 19**
- [ ] **Giai đoạn 5: Xây Dựng Bộ Test Tự Động Toàn Diện (Automated Unit Tests)**

---

## 🚀 Chi Tiết Từng Hạng Mục Thực Hiện

### Giai đoạn 1: Khóa Vòng Đời & Toàn Vẹn Dữ Liệu ở Backend (P0)

- [X] **1.1 Khóa chặt Model Phiếu Bảo Trì (`models/equipment_maintenance.py`)**

  - [X] Thêm validation kiểm tra trạng thái đầu vào của thiết bị: Chỉ cho phép tạo bảo trì khi thiết bị ở trạng thái `available` (Trong kho) hoặc `broken` (Hư hỏng).
  - [X] Chặn đưe st thiết bị đang `assigned` (Đang sử dụng), `liquidated` (Đã thanh lý) hoặc `lost` (Mất) vào phiếu bảo trì.
  - [X] Chống trùng lặp: Ngăn chặn tạo/xác nhận nhiều phiếu bảo trì đang chạy (`in_progress`) cho cùng 1 thiết bị.
  - [X] Chống "hồi sinh" thiết bị: Khi hoàn thành bảo trì (`action_done`), kiểm tra nếu thiết bị đã bị chuyển trạng thái khác ngoài `maintenance` (như đã thanh lý) thì báo lỗi và dừng thực thi.
  - [X] Bổ sung Backend Guard `unlink()`: Chỉ cho phép xóa phiếu ở trạng thái `draft` hoặc `cancelled`.
  - [X] Bổ sung Backend Guard `write()`: Khóa không cho sửa các trường `equipment_id`, `vendor_id`, `request_date`, `cost` khi phiếu không còn là `draft`.
- [X] **1.2 Khóa chặt Model Phiếu Thanh Lý (`models/equipment_liquidation.py`)**

  - [X] Thêm validation chặn thanh lý nếu thiết bị đang có phiếu bảo trì mở (`in_progress`). Bắt buộc phải hoàn tất hoặc hủy bảo trì trước.
  - [X] Bổ sung Backend Guard `unlink()`: Ngăn xóa phiếu đã duyệt (`approved`).
  - [X] Bổ sung Backend Guard `write()`: Khóa không cho sửa thông tin thiết bị, ngày thanh lý, giá bán khi phiếu đã ở trạng thái `approved`.
- [X] **1.3 Khóa chặt Model Phiếu Cấp Phát (`models/allocation.py`)**

  - [X] Bổ sung Backend Guard `unlink()`: Chỉ cho phép xóa phiếu `draft`. Nghiêm cấm xóa phiếu đã xác nhận (`confirmed`) hoặc đã thu hồi (`returned`) để bảo vệ chứng từ gốc.
  - [X] Bổ sung Backend Guard `write()`: Chặn chỉnh sửa `equipment_id`, `employee_id`, `date` khi phiếu đã xác nhận (`confirmed`).
- [X] **1.4 Khóa chặt Model Phiếu Thu Hồi (`models/equipment_return.py`)**

  - [X] Bổ sung Backend Guard `write()`: Chặn chỉnh sửa dữ liệu khi phiếu đã xác nhận hoàn thành (`returned`) hoặc `cancelled`.

---

### Giai đoạn 2: Ràng Buộc Dữ Liệu & Chuẩn Tiền Tệ (P1)

- [X] **2.1 Chuẩn hóa Model Thiết Bị (`models/equipment.py`)**

  - [X] Thêm `_sql_constraints`:
    - `unique_code`: Ràng buộc Unique cho Mã thiết bị (`code`).
  - [X] Thêm `@api.constrains`:
    - Ràng buộc Unique cho Số Serial (`serial_number`) nếu có nhập.
    - Giá mua không âm (`purchase_price >= 0`).
    - Giá trị thu hồi hợp lệ (`salvage_value >= 0` và `salvage_value <= purchase_price`).
    - Thời gian khấu hao hợp lệ (`useful_life_years > 0`).
  - [X] Thêm hàm bảo vệ `unlink()`: Chặn xóa thiết bị khi đang sử dụng (`assigned`), đang sửa chữa (`maintenance`), đã thanh lý (`liquidated`) hoặc đã có lịch sử giao dịch.
  - [X] Thêm trường `currency_id` (`res.currency`) và `company_id`.
  - [X] Chuyển các trường tiền tệ từ `Float` sang `Monetary`: `purchase_price`, `salvage_value`, `annual_depreciation`, `accumulated_depreciation`, `remaining_value`.
- [X] **2.2 Chuẩn hóa Model Bảo Trì & Thanh Lý**

  - [X] `equipment_maintenance.py`: Thêm ràng buộc `cost >= 0` và `completion_date >= request_date`. Thêm `company_id`, `currency_id` và đổi `cost` sang `Monetary`.
  - [X] `equipment_liquidation.py`: Thêm ràng buộc `price >= 0`. Thêm `company_id`, `currency_id` và đổi `price` sang `Monetary`.
- [X] **2.3 Chuẩn hóa Giao Diện XML Views**

  - [X] Thêm `currency_id` vào Form View, List View và Sub-lists của `equipment_views.xml`, `maintenance_views.xml`, `liquidation_views.xml`.
- [X] **2.4 Xây Dựng Bộ Test Tự Động Giai Đoạn 2**

  - [X] `tests/test_phase2_constraints.py`: Bộ kiểm thử tự động toàn diện cho Unique, Constraints số học & ngày tháng, Unlink protection.

---

### Giai đoạn 3: Tự Động Hóa Nghiệp Vụ & Audit Trail Chatter (P1)

- [X] **3.1 Tự động tạo Phiếu Bảo Trì từ Phiếu Thu Hồi**

  - [X] Khi xác nhận thu hồi (`action_confirm`) với tình trạng `condition == 'maintenance'`, tự động tạo 1 phiếu `company.equipment.maintenance` ở trạng thái Nháp.
  - [X] Ghi nhận liên kết giữa phiếu Thu hồi và phiếu Bảo trì vừa tạo (`return_id`, `maintenance_ids`).
  - [X] Thêm Smart button trên Form Thu hồi (`action_view_maintenance`) để điều hướng nhanh đến Phiếu bảo trì tương ứng.
- [X] **3.2 Kế thừa Module Mail & Tích Hợp Chatter**

  - [X] Cập nhật `__manifest__.py`: Thêm `"mail"` vào danh sách `"depends"`.
  - [X] Thêm kế thừa `_inherit = ['mail.thread', 'mail.activity.mixin']` cho tất cả 5 models.
  - [X] Bật tính năng `tracking=True` cho các trường quan trọng (`state`, `employee_id`, `cost`, `price`, `vendor_id`).
  - [X] Cập nhật toàn bộ các file Form view trong `views/*.xml`: Thêm component `<chatter/>` chuẩn Odoo 19.
- [X] **3.3 Xây dựng Bộ Test Tự Động Giai Đoạn 3**

  - [X] `tests/test_phase3_automation_chatter.py`: Test tự động sinh phiếu bảo trì, Smart button và kiểm tra kế thừa mail.thread & mail.activity.mixin.

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
