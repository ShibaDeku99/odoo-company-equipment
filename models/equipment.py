from odoo import api, fields, models


class CompanyEquipment(models.Model):
    _name = "company.equipment"
    _description = "Thiết bị công ty"
    _rec_name = "name"

    # --- Thông tin cơ bản ---
    name = fields.Char(
        string="Tên thiết bị",
        required=True,
    )

    code = fields.Char(
        string="Mã thiết bị",
        required=True,
    )

    serial_number = fields.Char(
        string="Số serial",
    )

    category = fields.Char(
        string="Loại thiết bị",
    )

    purchase_date = fields.Date(
        string="Ngày mua",
    )

    purchase_price = fields.Float(
        string="Giá mua",
    )

    state = fields.Selection(
        [
            ("available", "Trong kho"),
            ("assigned", "Đang sử dụng"),
            ("maintenance", "Đang sửa chữa"),
            ("broken", "Hư hỏng"),
            ("liquidated", "Đã thanh lý"),
            ("lost", "Mất"),
        ],
        string="Trạng thái",
        default="available",
        required=True,
    )

    note = fields.Text(
        string="Ghi chú",
    )

    # --- Thông tin sử dụng (Chỉ cập nhật qua Cấp phát / Thu hồi) ---
    employee_id = fields.Many2one(
        'hr.employee',
        string="Người sử dụng",
        readonly=True,
    )

    allocation_date = fields.Date(
        string="Ngày bàn giao",
        readonly=True,
    )

    # --- Thông tin cấu hình khấu hao ---
    depreciation_start_date = fields.Date(
        string="Ngày bắt đầu khấu hao",
    )

    useful_life_years = fields.Integer(
        string="Thời gian khấu hao (năm)",
        default=5,
    )

    salvage_value = fields.Float(
        string="Giá trị thu hồi dự kiến",
        default=0,
    )

    # --- Các trường tính toán khấu hao tự động ---
    annual_depreciation = fields.Float(
        string="Khấu hao mỗi năm",
        compute="_compute_depreciation",
        store=True,
    )

    depreciation_rate = fields.Float(
        string="Tỷ lệ khấu hao/năm (%)",
        compute="_compute_depreciation",
        store=True,
    )

    accumulated_depreciation = fields.Float(
        string="Khấu hao lũy kế",
        compute="_compute_depreciation",
    )

    remaining_value = fields.Float(
        string="Giá trị còn lại",
        compute="_compute_depreciation",
    )

    @api.depends('purchase_price', 'salvage_value', 'useful_life_years', 'depreciation_start_date')
    def _compute_depreciation(self):
        """Tính toán tự động khấu hao hàng năm, tỷ lệ khấu hao, khấu hao lũy kế và giá trị còn lại."""
        today = fields.Date.context_today(self)
        for record in self:
            # 1. Tính mức khấu hao mỗi năm
            if record.useful_life_years > 0:
                record.annual_depreciation = (record.purchase_price - record.salvage_value) / record.useful_life_years
            else:
                record.annual_depreciation = 0.0
                
            # 2. Tính tỷ lệ khấu hao mỗi năm theo %
            if record.purchase_price > 0:
                record.depreciation_rate = (record.annual_depreciation / record.purchase_price) * 100
            else:
                record.depreciation_rate = 0.0
                
            # 3. Tính khấu hao lũy kế dựa trên số ngày trôi qua từ ngày bắt đầu tính khấu hao
            accumulated = 0.0
            if record.depreciation_start_date and record.depreciation_start_date <= today:
                days_passed = (today - record.depreciation_start_date).days
                years_passed = days_passed / 365.25
                accumulated = years_passed * record.annual_depreciation
                
            # Giới hạn khấu hao lũy kế không vượt quá (Giá mua - Giá trị thu hồi)
            max_depreciation = record.purchase_price - record.salvage_value
            record.accumulated_depreciation = min(max(accumulated, 0.0), max_depreciation)
            
            # 4. Giá trị còn lại của thiết bị
            record.remaining_value = max(record.purchase_price - record.accumulated_depreciation, record.salvage_value)

    # --- Lịch sử liên kết ---
    maintenance_ids = fields.One2many(
        'company.equipment.maintenance',
        'equipment_id',
        string="Lịch sử bảo trì"
    )

    liquidation_ids = fields.One2many(
        'company.equipment.liquidation',
        'equipment_id',
        string="Thông tin thanh lý"
    )