# Review Module Quản lý Thiết bị Công ty

## Tổng quan

Module đã có bộ khung nghiệp vụ cơ bản: quản lý thiết bị, cấp phát, thu hồi, bảo trì và thanh lý. Tuy nhiên, trước khi dùng cho vận hành thực tế, cần ưu tiên khóa chặt vòng đời thiết bị và tính toàn vẹn chứng từ. Một số ràng buộc hiện mới nằm ở giao diện, nên vẫn có thể bị bỏ qua qua RPC/import.

## Ưu tiên P0 — Cần xử lý trước khi triển khai

### 1. Vòng đời thiết bị có thể bị sai hoặc "hồi sinh"

- Phiếu bảo trì không kiểm tra trạng thái đầu vào. Người dùng có thể đưa thiết bị đang cấp phát, đã mất hoặc đã thanh lý vào bảo trì.
- Thiết bị đang `maintenance` vẫn có thể được thanh lý. Sau đó, phiếu bảo trì đang xử lý có thể được hoàn thành và đổi thiết bị từ `liquidated` về `available`.
- Một thiết bị có thể có nhiều phiếu bảo trì đang xử lý cùng lúc.

**Đề xuất:** định nghĩa rõ state machine trên server và chỉ cho phép các chuyển trạng thái hợp lệ. Không được thanh lý khi còn phiếu bảo trì mở. Với thiết bị đang cấp phát, cần chọn một trong hai chính sách:

1. Bắt buộc thu hồi rồi mới tạo bảo trì; hoặc
2. Lưu trạng thái/người giữ trước bảo trì và hoàn trả đúng trạng thái `assigned` sau khi sửa xong.

### 2. Luồng nghiệp vụ chỉ bị khóa ở giao diện

Các trường như `state`, thiết bị, nhân viên nhận và ngày cấp phát được readonly/invisible trên view, nhưng nhóm quản lý vẫn có quyền `write`/`unlink`. RPC hoặc import có thể sửa phiếu đã xác nhận, đổi trực tiếp trạng thái thiết bị hoặc xóa chứng từ mà không đi qua action nghiệp vụ.

**Đề xuất:** thêm guard ở `write()` và `unlink()` theo state; chỉ cho phép thay đổi trạng thái bằng action. Đặc biệt, không được sửa/xóa phiếu cấp phát, thu hồi, bảo trì hoặc thanh lý đã hoàn tất.

### 3. Phiếu cấp phát đã xác nhận vẫn bị xóa

`company.equipment.allocation` chưa có `unlink()` guard. Khi xóa phiếu đã confirmed/returned, lịch sử bị mất và thiết bị có thể còn trạng thái `assigned` nhưng không còn chứng từ gốc để thu hồi.

**Đề xuất:** chỉ cho phép xóa phiếu nháp; các phiếu còn lại chỉ được hủy theo luồng có kiểm soát.

## Ưu tiên P1 — Hoàn thiện nghiệp vụ và dữ liệu

### 4. Thu hồi và bảo trì chưa liên kết hoàn chỉnh

Nếu thu hồi với tình trạng `maintenance`, thiết bị được chuyển sang bảo trì nhưng hệ thống không tạo hoặc yêu cầu một phiếu bảo trì. Thiết bị có thể nằm vĩnh viễn ở trạng thái `maintenance`.

**Đề xuất:** tạo tự động phiếu bảo trì, hoặc có nút bắt buộc "Tạo phiếu bảo trì" liên kết với phiếu thu hồi.

### 5. Thiếu ràng buộc dữ liệu quan trọng

- Chưa unique mã thiết bị và serial number.
- Chưa kiểm tra giá trị âm, `salvage_value <= purchase_price`, ngày hoàn thành không trước ngày yêu cầu, hoặc giá thanh lý không âm.
- Các trường giá tiền đang dùng `Float`; nên dùng `Monetary` cùng `currency_id`.
- Constraint kiểm tra chứng từ dùng `search()` theo từng record, dễ tạo N+1 khi xử lý nhiều bản ghi và chưa giải quyết hoàn toàn race condition.

**Đề xuất:** thêm SQL constraint/validation phù hợp; thiết kế cơ chế khóa hoặc constraint cho chứng từ đang mở của cùng một thiết bị.

### 6. Audit trail và phân quyền chưa đầy đủ

Nên thêm `mail.thread`, `mail.activity.mixin` và `tracking=True` cho trạng thái, người giữ, thiết bị, chi phí và các mốc phê duyệt. Khi thêm cần bổ sung dependency `mail` và Chatter trong view.

Tài liệu phân quyền cũng chưa khớp hoàn toàn với giao diện: nhóm quản lý thiết bị được nói là xem thanh lý read-only nhưng menu thanh lý chỉ hiển thị cho Manager; trong khi nhiều menu cha chưa giới hạn group rõ ràng.

### 7. Multi-company và quan hệ xóa

Multi-company là cần thiết nếu module dùng cho nhiều pháp nhân, nhưng không bắt buộc nếu scope hiện tại chỉ một công ty. Khi mở rộng cần thêm `company_id`, `check_company`, record rule theo công ty và sequence theo công ty.

Không nên áp dụng `ondelete='restrict'` cho mọi `Many2one` một cách máy móc. Cần quyết định theo chính sách dữ liệu: chứng từ lịch sử thường cần restrict; dữ liệu tham chiếu không trọng yếu có thể set null. Riêng việc xóa/archiving nhân viên không được làm thiết bị `assigned` rơi vào trạng thái không còn người giữ.

## Khấu hao và Cronjob

Hàm `_compute_depreciation` đã có `@api.depends`. `annual_depreciation` và `depreciation_rate` đã được lưu; `accumulated_depreciation` và `remaining_value` là computed field không lưu nên khi đọc form vẫn được tính theo ngày hiện tại.

Vì vậy, **Cronjob không phải yêu cầu bắt buộc chỉ để hiển thị khấu hao hiện tại**. Cron chỉ cần khi nghiệp vụ yêu cầu chốt số liệu theo tháng, lọc/nhóm/báo cáo theo giá trị còn lại hoặc tạo bút toán kế toán. Khi đó cần thiết kế dòng khấu hao theo kỳ/snapshot và Cron chốt kỳ; chỉ thêm `store=True` không tự làm số liệu thay đổi khi sang ngày mới.

Quy tắc tính theo ngày hay tròn tháng phải được BA/Kế toán thống nhất trước. Nếu có yêu cầu hạch toán chính thức, nên ưu tiên tích hợp tính năng tài sản của Accounting thay vì tự xây engine khấu hao đơn giản.

## Tính năng nên làm theo phase

### Phase 1 — Giá trị vận hành cao

1. Cấp phát/thu hồi nhiều thiết bị trên một phiếu, phục vụ onboarding/offboarding.
2. Quét QR/barcode để nhận diện nhanh thiết bị và tự tìm phiếu cấp phát còn hiệu lực.
3. Lưu vị trí, phòng ban, cost center, người chịu trách nhiệm và lịch sử cấp phát trên thiết bị.
4. Biên bản bàn giao/thu hồi có checklist, ảnh hiện trạng và xác nhận điện tử.
5. Quy trình báo mất/hư hỏng có biên bản và phê duyệt.

### Phase 2 — Kiểm soát tài sản

1. Kiểm kê định kỳ, xử lý chênh lệch và báo cáo thiết bị theo trạng thái/vị trí.
2. Quản lý bảo hành, nhắc bảo trì định kỳ và đánh giá chi phí sửa chữa.
3. Phân loại tài sản quản lý theo serial và vật tư tiêu hao quản lý theo số lượng.
4. Phê duyệt thanh lý nhiều bước, tách người lập và người duyệt, kèm biên bản/bằng chứng.

### Phase 3 — Kế toán và mở rộng

1. Lịch khấu hao theo kỳ và tích hợp Accounting để hạch toán khấu hao/thanh lý.
2. Multi-company đầy đủ.

## Chuẩn Odoo 19 và chất lượng mã

- Đổi các M2M command XML cũ `(4, ref(...))` sang `Command.link(ref(...))` theo chuẩn đang áp dụng của Odoo 19.
- Bổ sung test cho state transition, phân quyền/record rule, chống sửa/xóa chứng từ đã hoàn tất, validation và khấu hao.
- Không có lỗi UTF-8, XML parse và Python compile tại thời điểm review.

## Thứ tự thực hiện khuyến nghị

1. Chốt state machine và quyền chuyển trạng thái.
2. Khóa `write`/`unlink`, sửa luồng maintenance–liquidation và return–maintenance.
3. Bổ sung ràng buộc dữ liệu, audit trail và test.
4. Sau đó mới triển khai cấp phát hàng loạt, QR và kiểm kê.
