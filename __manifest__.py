{
    "name": "Equipment Management",
    "version": "19.0.1.0.0",
    "author": "ShibaDeku",
    "website": "https://github.com/ShibaDeku99/odoo-company-equipment",
    "category": "Human Resources/Equipment",
    "summary": "Hệ thống quản lý, cấp phát, thu hồi, bảo trì và thanh lý thiết bị công ty chuẩn Enterprise",
    "description": """
Module Quản Lý Thiết Bị Doanh Nghiệp (Company Equipment Management)
===================================================================
Tính năng chính:
----------------
* Quản lý vòng đời toàn diện thiết bị: Trong kho, Đang sử dụng, Bảo trì, Hư hỏng, Đã thanh lý, Mất.
* Cấp phát và Thu hồi tài sản cho nhân viên với lịch sử rõ ràng.
* Tự động hóa quy trình: Khi thu hồi máy hỏng, tự động sinh phiếu Bảo trì và liên kết Smart Button.
* Kiểm toán & Trao đổi (Audit Trail): Tích hợp sẵn Chatter (Log note, Send message, Activities, Tracking).
* Tính toán khấu hao tài sản và chuẩn hóa tiền tệ Đa công ty (Multi-Company & Multi-Currency).
* Bảo mật chặt chẽ: Phân quyền cá nhân hóa theo vai trò (RBAC) & Record Rules cách ly dữ liệu.
* Bộ kiểm thử tự động 100% (Automated Unit Tests).
    """,
    "depends": ["base", "hr", "mail"],
    "data": [
        "security/equipment_security.xml",
        "security/ir.model.access.csv",
        "data/equipment_sequence.xml",
        "views/equipment_views.xml",
        "views/allocation_views.xml",
        "views/return_views.xml",
        "views/maintenance_views.xml",
        "views/liquidation_views.xml",
        "views/equipment_menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
