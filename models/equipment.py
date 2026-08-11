from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CompanyEquipment(models.Model):
    _name = "company.equipment"
    _description = "Thiết bị công ty"
    _rec_name = "name"

    _unique_equipment_code = models.Constraint('UNIQUE(code)', 'Mã thiết bị phải là duy nhất!')
    _unique_serial_number = models.Constraint('UNIQUE(serial_number)', 'Số Serial phải là duy nhất!')

    company_id = fields.Many2one(
        'res.company',
        string="Công ty",
        default=lambda self: self.env.company,
        required=True,
    )

    def _default_currency_id(self):
        vnd = self.env.ref('base.VND', raise_if_not_found=False) or self.env['res.currency'].search([('name', '=', 'VND')], limit=1)
        if vnd and not vnd.active:
            vnd.sudo().write({'active': True})
        return vnd or self.env.company.currency_id

    currency_id = fields.Many2one(
        'res.currency',
        string="Tiền tệ",
        default=_default_currency_id,
        required=True,
    )

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

    purchase_price = fields.Monetary(
        string="Giá mua",
        currency_field='currency_id',
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

    salvage_value = fields.Monetary(
        string="Giá trị thu hồi dự kiến",
        currency_field='currency_id',
        default=0,
    )

    # --- Các trường tính toán khấu hao tự động ---
    annual_depreciation = fields.Monetary(
        string="Khấu hao mỗi năm",
        currency_field='currency_id',
        compute="_compute_annual_depreciation",
        store=True,
        compute_sudo=True,
    )

    depreciation_rate = fields.Float(
        string="Tỷ lệ khấu hao/năm (%)",
        compute="_compute_annual_depreciation",
        store=True,
        compute_sudo=True,
    )

    accumulated_depreciation = fields.Monetary(
        string="Khấu hao lũy kế",
        currency_field='currency_id',
        compute="_compute_accumulated_depreciation",
    )

    remaining_value = fields.Monetary(
        string="Giá trị còn lại",
        currency_field='currency_id',
        compute="_compute_accumulated_depreciation",
    )

    @api.depends('purchase_price', 'salvage_value', 'useful_life_years')
    def _compute_annual_depreciation(self):
        """Tính mức khấu hao và tỷ lệ khấu hao cố định mỗi năm (lưu trữ DB)."""
        for record in self:
            if record.useful_life_years > 0:
                record.annual_depreciation = (record.purchase_price - record.salvage_value) / record.useful_life_years
            else:
                record.annual_depreciation = 0.0

            if record.purchase_price > 0:
                record.depreciation_rate = (record.annual_depreciation / record.purchase_price) * 100
            else:
                record.depreciation_rate = 0.0

    @api.depends('purchase_price', 'salvage_value', 'depreciation_start_date', 'annual_depreciation')
    def _compute_accumulated_depreciation(self):
        """Tính toán khấu hao lũy kế và giá trị còn lại theo thời gian thực (không lưu DB)."""
        today = fields.Date.context_today(self)
        for record in self:
            accumulated = 0.0
            if record.depreciation_start_date and record.depreciation_start_date <= today:
                days_passed = (today - record.depreciation_start_date).days
                years_passed = days_passed / 365.25
                accumulated = years_passed * record.annual_depreciation

            max_depreciation = max(record.purchase_price - record.salvage_value, 0.0)
            record.accumulated_depreciation = min(max(accumulated, 0.0), max_depreciation)
            record.remaining_value = max(record.purchase_price - record.accumulated_depreciation, record.salvage_value)

    @api.constrains('purchase_price', 'salvage_value', 'useful_life_years')
    def _check_financial_data(self):
        """Kiểm tra tính hợp lệ của các số liệu tài chính."""
        for record in self:
            if record.purchase_price < 0:
                raise ValidationError(_("Giá mua không được là số âm."))
            if record.salvage_value < 0:
                raise ValidationError(_("Giá trị thu hồi dự kiến không được là số âm."))
            if record.salvage_value > record.purchase_price:
                raise ValidationError(_("Giá trị thu hồi dự kiến không được lớn hơn Giá mua."))
            if record.useful_life_years <= 0:
                raise ValidationError(_("Thời gian khấu hao phải lớn hơn 0."))

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