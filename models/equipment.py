from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class CompanyEquipment(models.Model):
    _name = "company.equipment"
    _description = "Thiết bị công ty"
    _rec_name = "name"

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Mã thiết bị phải là duy nhất trong hệ thống!'),
    ]

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

    @api.constrains('code')
    def _check_unique_code(self):
        """Đảm bảo mã thiết bị không bị trùng lặp trong hệ thống."""
        for record in self:
            if record.code:
                existing = self.search([
                    ('code', '=', record.code),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing:
                    raise ValidationError(_(
                        "Mã thiết bị '%s' đã tồn tại trong hệ thống. Vui lòng sử dụng mã khác."
                    ) % record.code)

    @api.constrains('serial_number')
    def _check_unique_serial_number(self):
        """Đảm bảo số Serial không bị trùng lặp (nếu có nhập)."""
        for record in self:
            if record.serial_number:
                existing = self.search([
                    ('serial_number', '=', record.serial_number),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing:
                    raise ValidationError(_(
                        "Số serial '%s' đã được sử dụng cho thiết bị '%s'."
                    ) % (record.serial_number, existing.display_name))

    @api.constrains('purchase_price', 'salvage_value', 'useful_life_years')
    def _check_depreciation_values(self):
        """Kiểm tra tính hợp lệ của giá mua, giá trị thu hồi và thời gian khấu hao."""
        for record in self:
            if record.purchase_price < 0:
                raise ValidationError(_("Giá mua thiết bị không được là số âm."))
            if record.salvage_value < 0:
                raise ValidationError(_("Giá trị thu hồi dự kiến không được là số âm."))
            if record.salvage_value > record.purchase_price:
                raise ValidationError(_("Giá trị thu hồi dự kiến không được lớn hơn giá mua thiết bị."))
            if record.useful_life_years <= 0:
                raise ValidationError(_("Thời gian khấu hao phải lớn hơn 0 năm."))

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

    def unlink(self):
        """Ngăn chặn xóa thiết bị khi đang sử dụng, đang bảo trì, đã thanh lý hoặc đã có lịch sử giao dịch."""
        for record in self:
            if record.state in ['assigned', 'maintenance', 'liquidated']:
                raise UserError(_(
                    "Không thể xóa thiết bị '%s' vì thiết bị đang ở trạng thái '%s'."
                ) % (record.display_name, record.state))
            if record.maintenance_ids or record.liquidation_ids:
                raise UserError(_(
                    "Không thể xóa thiết bị '%s' vì đã phát sinh lịch sử bảo trì hoặc thanh lý."
                ) % record.display_name)
        return super().unlink()

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

    def init(self):
        """Tự động kích hoạt tiền tệ VND và chuyển đổi toàn bộ thiết bị cũ sang VND."""
        super().init()
        vnd = self.env.ref('base.VND', raise_if_not_found=False) or self.env['res.currency'].search([('name', '=', 'VND')], limit=1)
        if vnd:
            if not vnd.active:
                vnd.sudo().write({'active': True})
            self.env.cr.execute("""
                UPDATE company_equipment 
                SET currency_id = %s;
                UPDATE company_equipment_maintenance 
                SET currency_id = %s;
                UPDATE company_equipment_liquidation 
                SET currency_id = %s;
            """, [vnd.id, vnd.id, vnd.id])