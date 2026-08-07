from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class CompanyEquipmentLiquidation(models.Model):
    _name = "company.equipment.liquidation"
    _description = "Phiếu thanh lý thiết bị"
    _rec_name = "name"

    name = fields.Char(
        string="Mã phiếu", 
        required=True, 
        copy=False, 
        readonly=True, 
        default=lambda self: _('New')
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
    
    equipment_id = fields.Many2one(
        'company.equipment', 
        string="Thiết bị", 
        required=True,
        domain=[('state', 'in', ['available', 'broken'])]
    )
    
    date = fields.Date(
        string="Ngày thanh lý", 
        required=True, 
        default=fields.Date.context_today
    )
    
    reason = fields.Selection(
        [
            ('broken', 'Hư hỏng nặng'),
            ('old', 'Cũ / Hết khấu hao'),
            ('other', 'Lý do khác'),
        ], 
        string="Lý do thanh lý", 
        required=True, 
        default='old'
    )
    
    price = fields.Monetary(
        string="Giá thanh lý / Số tiền thu hồi",
        currency_field='currency_id',
    )
    
    purchaser_name = fields.Char(
        string="Người / Đơn vị mua"
    )
    
    note = fields.Text(
        string="Ghi chú"
    )
    
    state = fields.Selection(
        [
            ('draft', 'Nháp'),
            ('approved', 'Đã duyệt'),
            ('cancelled', 'Đã hủy'),
        ], 
        string="Trạng thái", 
        default='draft', 
        required=True
    )

    @api.constrains('price')
    def _check_price(self):
        """Kiểm tra giá thanh lý không được là số âm."""
        for record in self:
            if record.price < 0:
                raise ValidationError(_("Giá thanh lý / Số tiền thu hồi không được là số âm."))

    @api.constrains('equipment_id', 'state')
    def _check_equipment(self):
        """Kiểm tra tính hợp lệ của thiết bị đem thanh lý."""
        for record in self:
            if not record.equipment_id:
                continue

            # 1. Không thể thanh lý thiết bị đang có người dùng, đã mất hoặc đã thanh lý rồi (kiểm tra ở trạng thái nháp)
            if record.state == 'draft' and record.equipment_id.state in ['assigned', 'liquidated', 'lost']:
                raise ValidationError(_(
                    "Không thể thanh lý thiết bị '%s' vì thiết bị đang ở trạng thái '%s'."
                ) % (record.equipment_id.display_name, record.equipment_id.state))
            
            # 2. Không cho phép thanh lý khi thiết bị đang có phiếu bảo trì đang xử lý
            active_maintenance = self.env['company.equipment.maintenance'].search([
                ('equipment_id', '=', record.equipment_id.id),
                ('state', '=', 'in_progress')
            ], limit=1)
            if active_maintenance:
                raise ValidationError(_(
                    "Thiết bị '%s' hiện đang có phiếu bảo trì '%s' đang xử lý. Vui lòng hoàn thành hoặc hủy bảo trì trước khi thanh lý."
                ) % (record.equipment_id.display_name, active_maintenance.name))

            # 3. Tránh tạo nhiều phiếu thanh lý cùng lúc cho 1 thiết bị
            existing = self.search([
                ('equipment_id', '=', record.equipment_id.id),
                ('state', 'in', ['draft', 'approved']),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(_(
                    "Thiết bị '%s' đã có Phiếu thanh lý khác đang xử lý hoặc đã duyệt."
                ) % record.equipment_id.display_name)

    @api.model_create_multi
    def create(self, vals_list):
        """Tự động sinh mã phiếu thanh lý từ sequence khi tạo mới."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('company.equipment.liquidation') or _('New')
        return super().create(vals_list)

    def action_approve(self):
        """Phê duyệt thanh lý thiết bị:
        - Kiểm tra thiết bị không được ở trạng thái đang sử dụng, đã mất, hoặc đã thanh lý.
        - Kiểm tra không có phiếu bảo trì đang xử lý.
        - Đổi trạng thái thiết bị sang 'Đã thanh lý' (liquidated).
        - Đổi trạng thái phiếu thanh lý sang 'Đã duyệt' (approved).
        """
        for record in self:
            if record.state != 'draft':
                continue
            
            equipment = record.equipment_id
            if equipment.state in ['assigned', 'liquidated', 'lost']:
                raise UserError(_(
                    "Thiết bị '%s' đang ở trạng thái '%s', không thể thực hiện thanh lý."
                ) % (equipment.display_name, equipment.state))
            
            # Kiểm tra bảo trì đang mở
            active_maint = self.env['company.equipment.maintenance'].search([
                ('equipment_id', '=', equipment.id),
                ('state', '=', 'in_progress')
            ], limit=1)
            if active_maint:
                raise UserError(_(
                    "Không thể phê duyệt thanh lý: Thiết bị '%s' đang có phiếu bảo trì '%s' đang thực hiện."
                ) % (equipment.display_name, active_maint.name))
            
            # Đổi trạng thái thiết bị thành Đã thanh lý
            equipment.write({
                'state': 'liquidated'
            })
            
            record.write({'state': 'approved'})

    def action_cancel(self):
        """Hủy phiếu thanh lý (chỉ áp dụng cho phiếu ở trạng thái Nháp)."""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Chỉ có thể hủy phiếu đang ở trạng thái Nháp."))
            record.write({'state': 'cancelled'})

    def write(self, vals):
        """Khóa không cho chỉnh sửa thông tin thanh lý khi phiếu đã duyệt hoặc đã hủy."""
        protected_fields = {'equipment_id', 'date', 'price', 'purchaser_name', 'reason'}
        for record in self:
            if record.state in ['approved', 'cancelled']:
                modified_protected = set(vals.keys()) & protected_fields
                if modified_protected:
                    raise UserError(_(
                        "Không thể chỉnh sửa thông tin thanh lý (%s) của phiếu đã được phê duyệt hoặc đã hủy."
                    ) % ", ".join(modified_protected))
        return super().write(vals)

    def unlink(self):
        """Ngăn chặn xóa phiếu thanh lý đã duyệt."""
        for record in self:
            if record.state not in ['draft', 'cancelled']:
                raise UserError(_("Không thể xóa phiếu thanh lý đã duyệt (%s).") % record.name)
        return super().unlink()
