# 🏢 Module Quản Lý Thiết Bị Doanh Nghiệp (Equipment Management)

[![Odoo Version](https://img.shields.io/badge/Odoo-19.0-714B67.svg?style=flat&logo=odoo)](https://www.odoo.com)
[![Build Status](https://img.shields.io/badge/Tests-20%2F20%20Passed%20(100%25)-success.svg)](https://github.com/ShibaDeku99/odoo-company-equipment)
[![Version](https://img.shields.io/badge/Version-19.0.1.0.0-blue.svg)](https://github.com/ShibaDeku99/odoo-company-equipment)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-green.svg)](https://www.gnu.org/licenses/lgpl-3.0.html)

> **Hệ thống Quản lý Vòng đời, Cấp phát, Thu hồi, Bảo trì, Khấu hao & Thanh lý Thiết bị Doanh nghiệp chuẩn Enterprise trên nền tảng Odoo 19.**

---

## 📑 Mục Lục

1. [Tính Năng Nổi Bật](#-tính-năng-nổi-bật)
2. [Cấu Trúc Dữ Liệu & Vòng Đời Thiết Bị](#-cấu-trúc-dữ-liệu--vòng-đời-thiết-bị)
3. [Quy Trình & Luồng Hoạt Động (Workflows)](#-quy-trình--luồng-hoạt-động-workflows)
   - [1. Quản lý Hồ sơ & Khấu hao thiết bị](#1-quản-lý-hồ-sơ--khấu-hao-thiết-bị)
   - [2. Quy trình Cấp phát thiết bị](#2-quy-trình-cấp-phát-thiết-bị)
   - [3. Quy trình Thu hồi thiết bị & Tự động hóa](#3-quy-trình-thu-hồi-thiết-bị--tự-động-hóa)
   - [4. Quy trình Bảo trì & Sửa chữa](#4-quy-trình-bảo-trì--sửa-chữa)
   - [5. Quy trình Thanh lý tài sản](#5-quy-trình-thanh-lý-tài-sản)
4. [Tích Hợp Chatter & Audit Trail](#-tích-hợp-chatter--audit-trail)
5. [Hệ Thống Phân Quyền & Bảo Mật](#-hệ-thống-phân-quyền--bảo-mật)
6. [Hướng Dẫn Cài Đặt & Chạy Kiểm Thử Tự Động](#-hướng-dẫn-cài-đặt--chạy-kiểm-thử-tự-động)

---

## ⭐ Tính Năng Nổi Bật

* **Khóa Chặt Vòng Đời ở Backend**: Ngăn chặn 100% các hành vi thao tác sai logic, bảo vệ chứng từ gốc khi đã xác nhận.
* **Tự Động Hóa Nghiệp Vụ**: Khi thu hồi thiết bị báo hỏng (`broken` / `maintenance`), hệ thống tự động sinh phiếu Bảo trì ở trạng thái Nháp kèm liên kết Smart Button.
* **Toàn Vẹn Dữ Liệu & Khấu Hao**: Ràng buộc duy nhất Mã thiết bị (`models.Constraint`), Số serial (`@api.constrains`), tính toán khấu hao đường thẳng tự động.
* **Chuẩn Tiền Tệ & Đa Công Ty**: Áp dụng `fields.Monetary` theo đơn vị tiền tệ công ty (VND) và cách ly dữ liệu Multi-Company độc lập.
* **Audit Trail & Chatter**: Kế thừa `mail.thread` và `mail.activity.mixin`, theo dõi biến động trạng thái (`tracking=True`) trên mọi mô hình.
* **Bộ Test Tự Động 100%**: 20 kịch bản kiểm thử tự động toàn diện bao phủ toàn bộ vòng đời và phân quyền.

---

## 🔄 Cấu Trúc Dữ Liệu & Vòng Đời Thiết Bị

Thiết bị (`company.equipment`) trải qua các trạng thái xuyên suốt vòng đời:

```mermaid
flowchart TD
    Start([⚡ Tạo mới]) --> Avail["📦 TRONG KHO (available)"]

    subgraph Operation [" VẬN HÀNH & SỬ DỤNG "]
        Avail -->|1. Cấp phát| Assign["👤 ĐANG SỬ DỤNG (assigned)"]
        Assign -->|Thu hồi: Tốt| Avail
    end

    subgraph Incident [" SỰ CỐ & BẢO TRÌ "]
        Avail -->|Gửi bảo trì| Maint["🔧 ĐANG SỬA CHỮA (maintenance)"]
        Assign -->|Thu hồi: Cần bảo dưỡng / Hỏng (Tự động sinh phiếu)| Maint
        Maint -->|Bảo dưỡng xong| Avail
        Assign -->|Thu hồi: Báo hỏng| Broken["⚠️ HƯ HỎNG (broken)"]
        Assign -->|Thu hồi: Báo mất| Lost["❌ MẤT (lost)"]
    end

    subgraph EndLife [" KẾT THÚC VÒNG ĐỜI "]
        Avail -->|Thanh lý kho| Liq["💰 ĐÃ THANH LÝ (liquidated)"]
        Maint -->|Không thể sửa| Liq
        Broken -->|Thanh lý xác| Liq
        Liq --> Finish([🏁 Kết thúc])
        Lost --> Finish
    end

    style Avail fill:#2ecc71,stroke:#27ae60,stroke-width:2px,color:#fff,font-weight:bold
    style Assign fill:#3498db,stroke:#2980b9,stroke-width:2px,color:#fff,font-weight:bold
    style Maint fill:#f39c12,stroke:#d35400,stroke-width:2px,color:#fff,font-weight:bold
    style Broken fill:#e67e22,stroke:#d35400,stroke-width:2px,color:#fff,font-weight:bold
    style Lost fill:#e74c3c,stroke:#c0392b,stroke-width:2px,color:#fff,font-weight:bold
    style Liq fill:#95a5a6,stroke:#7f8c8d,stroke-width:2px,color:#fff,font-weight:bold
    style Start fill:#f1c40f,stroke:#f39c12,stroke-width:2px,color:#333
    style Finish fill:#34495e,stroke:#2c3e50,stroke-width:2px,color:#fff
```

### Các trạng thái thiết bị (`state`):

| Mã trạng thái | Tên hiển thị            | Ý nghĩa                                                |
| :--------------- | :------------------------- | :------------------------------------------------------- |
| `available`    | **Trong kho**        | Thiết bị sẵn sàng để cấp phát cho nhân viên    |
| `assigned`     | **Đang sử dụng**  | Đang được giao cho một nhân sự phụ trách        |
| `maintenance`  | **Đang sửa chữa** | Đang gửi bảo trì/sửa chữa tại đơn vị cung cấp |
| `broken`       | **Hư hỏng**        | Thiết bị gặp lỗi, hỏng hóc chờ xử lý/thanh lý  |
| `liquidated`   | **Đã thanh lý**   | Đã bán thanh lý hoặc hủy bỏ tài sản             |
| `lost`         | **Mất**             | Bị thất lạc trong quá trình sử dụng               |

---

## 🚀 Quy Trình & Luồng Hoạt Động (Workflows)

### 1. Quản lý Hồ sơ & Khấu hao thiết bị

Hệ thống tự động tính toán giá trị tài sản dựa trên phương pháp đường thẳng:

- **Khấu hao mỗi năm** = $\frac{\text{Giá mua} - \text{Giá trị thu hồi dự kiến}}{\text{Thời gian khấu hao (năm)}}$
- **Tỷ lệ khấu hao/năm (%)** = $\frac{\text{Khấu hao mỗi năm}}{\text{Giá mua}} \times 100$
- **Khấu hao lũy kế** = $\text{Số năm đã sử dụng} \times \text{Khấu hao mỗi năm}$ (không vượt quá Nguyên giá - Giá trị thu hồi).
- **Giá trị còn lại** = $\max(\text{Giá mua} - \text{Khấu hao lũy kế}, \text{Giá trị thu hồi})$.

---

### 2. Quy trình Cấp phát thiết bị (`company.equipment.allocation`)

```mermaid
sequenceDiagram
    autonumber
    actor NV as Nhân viên quản lý thiết bị
    participant CP as Phiếu Cấp Phát
    participant TB as Thiết Bị (company.equipment)

    NV->>CP: Tạo phiếu cấp phát (Chọn Nhân viên nhận, Thiết bị)
    Note over CP: Hệ thống lọc domain chỉ cho chọn thiết bị "Trong kho" (available)
    NV->>CP: Bấm "Xác nhận" (action_confirm)
    CP->>TB: Kiểm tra thiết bị có đang "available" không?
    CP->>TB: Đổi trạng thái sang "Đang sử dụng" (assigned)
    CP->>TB: Gán Người sử dụng (employee_id) & Ngày bàn giao
    CP->>CP: Chuyển trạng thái phiếu sang "Đã cấp phát" (confirmed)
```

---

### 3. Quy trình Thu hồi thiết bị & Tự động hóa (`company.equipment.return`)

```mermaid
sequenceDiagram
    autonumber
    actor NV as Quản lý thiết bị
    participant TH as Phiếu Thu Hồi
    participant CP as Phiếu Cấp Phát Gốc
    participant TB as Thiết Bị
    participant BT as Phiếu Bảo Trì

    NV->>TH: Tạo phiếu thu hồi (Chọn Phiếu cấp phát đã confirmed)
    NV->>TH: Chọn Tình trạng: "Cần bảo trì" hoặc "Hư hỏng"
    NV->>TH: Bấm "Xác nhận thu hồi" (action_confirm)
    TH->>TB: Gỡ người sử dụng & Cập nhật trạng thái mới
    TH->>CP: Chuyển trạng thái phiếu cấp phát sang "Đã thu hồi"
    TH->>BT: TỰ ĐỘNG tạo Phiếu Bảo Trì (Nháp) kèm Smart Button
    TH->>TH: Chuyển trạng thái phiếu sang "Đã thu hồi"
```

---

### 4. Quy trình Bảo trì & Sửa chữa (`company.equipment.maintenance`)

```mermaid
flowchart LR
    A[Nháp - draft] -->|action_confirm| B[Đang bảo trì - in_progress]
    B -->|action_done| C[Đã hoàn thành - done]
    A -->|action_cancel| D[Đã hủy - cancelled]
    B -->|action_cancel| D

    style A fill:#f9f9f9,stroke:#333
    style B fill:#ffeaa7,stroke:#fdcb6e
    style C fill:#55efc4,stroke:#00b894
    style D fill:#ff7675,stroke:#d63031
```

- **Tạo phiếu**: Chọn thiết bị trong kho/hư hỏng, đơn vị sửa chữa (`res.partner`), chi phí dự kiến.
- **Xác nhận (Bắt đầu sửa)**: Phiếu sang `in_progress`, thiết bị chuyển sang `maintenance` (Đang sửa chữa). Chống tạo phiếu bảo trì thứ 2 trùng lặp.
- **Hoàn thành**: Phiếu sang `done`, thiết bị chuyển trạng thái về `available` (Trong kho) để sẵn sàng cấp phát.
- **Hủy phiếu**: Nếu hủy trong khi đang sửa chữa, thiết bị tự động được hoàn trả về `available`.

---

### 5. Quy trình Thanh lý tài sản (`company.equipment.liquidation`)

```mermaid
flowchart TD
    Start[Thiết bị hỏng / Hết khấu hao] --> Create[Tạo Phiếu Thanh Lý]
    Create --> Check{Kiểm tra hợp lệ}
    Check -- Thiết bị đang dùng hoặc đang bảo trì --> Reject[Báo lỗi ValidationError]
    Check -- Thiết bị trong kho / hỏng / sửa chữa --> Draft[Lưu phiếu ở trạng thái Nháp]
    Draft -->|Chỉ Manager có quyền| Approve[Phê duyệt thanh lý - action_approve]
    Approve --> UpdateState[Đổi trạng thái thiết bị sang 'Đã thanh lý' liquidated]
    Approve --> DoneState[Đổi phiếu sang 'Đã duyệt' approved]
```

---

## 💬 Tích Hợp Chatter & Audit Trail

Toàn bộ 5 mô hình đều được kế thừa:
* `mail.thread`: Ghi log tự động khi thay đổi trạng thái, gửi tin nhắn trao đổi nội bộ.
* `mail.activity.mixin`: Lên lịch hoạt động (Call, Meeting, To-do) nhắc nhở việc bảo trì hoặc thu hồi.
* `tracking=True`: Theo dõi nhật ký lịch sử các trường trọng yếu (`state`, `employee_id`, `cost`, `price`, `vendor_id`).

---

## 🔒 Hệ Thống Phân Quyền & Bảo Mật

Áp dụng cơ chế bảo mật 3 lớp chặt chẽ: **User Groups (RBAC)**, **Access Control Lists (ACL)**, và **Record Rules (Quy tắc bản ghi)**:

### Bảng phân quyền ma trận

| Nghiệp vụ | Nhân viên thông thường (`base.group_user`) | Nhân viên Quản lý Thiết bị (`group_equipment_user`) | Trưởng phòng / Quản lý (`group_equipment_manager`) |
| :--- | :---: | :---: | :---: |
| **Xem thiết bị của chính mình** | ✅ Có | ✅ Có | ✅ Có |
| **Xem toàn bộ thiết bị công ty** | ❌ Không | ✅ Có | ✅ Có |
| **Tạo, sửa, xóa Thiết bị** | ❌ Không | ✅ Toàn quyền | ✅ Toàn quyền |
| **Tạo & Xác nhận Cấp phát** | ❌ Không (chỉ xem của mình) | ✅ Toàn quyền | ✅ Toàn quyền |
| **Tạo & Xác nhận Thu hồi** | ❌ Không (chỉ xem của mình) | ✅ Toàn quyền | ✅ Toàn quyền |
| **Tạo & Thực hiện Bảo trì** | ❌ Không | ✅ Toàn quyền | ✅ Toàn quyền |
| **Xem Phiếu Thanh lý** | ❌ Không | ✅ Chỉ xem (Read-only) | ✅ Toàn quyền |
| **Phê duyệt Thanh lý** | ❌ Không | ❌ Không | ✅ **Toàn quyền phê duyệt** |
| **Cách ly Đa công ty (Multi-Company)** | ✅ Tự động | ✅ Tự động | ✅ Tự động |

---

## 🧪 Hướng Dẫn Cài Đặt & Chạy Kiểm Thử Tự Động

### 1. Cài đặt / Nâng cấp module
```powershell
.\.venv\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u equipment_management --stop-after-init
```

### 2. Chạy toàn bộ 20 bài Test tự động
```powershell
.\.venv\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19 -u equipment_management --test-tags=equipment_all --stop-after-init
```

### 3. Chạy kiểm thử theo từng Giai đoạn:
* **Phase 1 (Backend Guards)**: `--test-tags=equipment_phase1`
* **Phase 2 (Constraints & Tiền tệ)**: `--test-tags=equipment_phase2`
* **Phase 3 (Automation & Chatter)**: `--test-tags=equipment_phase3`
* **Phase 4 (Security & Multi-Company)**: `--test-tags=equipment_security`
