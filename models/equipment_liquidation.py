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
    
    equipment_id = fields.Many2one(
        'company.equipment', 
        string="Thiết bị", 
        required=True,
        domain=[('state', 'in', ['available', 'maintenance', 'broken'])]
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
    
    price = fields.Float(
        string="Giá thanh lý / Số tiền thu hồi"
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

    @api.constrains('equipment_id')
    def _check_equipment(self):
        """Kiểm tra tính hợp lệ của thiết bị đem thanh lý."""
        for record in self:
            if record.equipment_id:
                # 1. Không thể thanh lý thiết bị đang có người dùng hoặc đã thanh lý rồi
                if record.equipment_id.state in ['assigned', 'liquidated']:
                    raise ValidationError(_("Không thể thanh lý thiết bị đang sử dụng hoặc đã thanh lý rồi."))
                
                # 2. Tránh tạo nhiều phiếu thanh lý cùng lúc cho 1 thiết bị
                existing = self.search([
                    ('equipment_id', '=', record.equipment_id.id),
                    ('state', 'in', ['draft', 'approved']),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_("Thiết bị này đã có Phiếu thanh lý khác đang xử lý hoặc đã duyệt."))

    @api.model_create_multi
    def create(self, vals_list):
        """Tự động sinh mã phiếu thanh lý từ sequence khi tạo mới."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('company.equipment.liquidation') or _('New')
        return super().create(vals_list)

    def action_approve(self):
        """Phê duyệt thanh lý thiết bị:
        - Đổi trạng thái thiết bị sang 'Đã thanh lý' (liquidated).
        - Đổi trạng thái phiếu thanh lý sang 'Đã duyệt' (approved).
        """
        for record in self:
            if record.state != 'draft':
                continue
            
            if record.equipment_id.state in ['assigned', 'liquidated']:
                raise UserError(_("Thiết bị này không hợp lệ để thanh lý."))
            
            # Đổi trạng thái thiết bị thành Đã thanh lý
            record.equipment_id.write({
                'state': 'liquidated'
            })
            
            record.write({'state': 'approved'})

    def action_cancel(self):
        """Hủy phiếu thanh lý (chỉ áp dụng cho phiếu ở trạng thái Nháp)."""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Chỉ có thể hủy phiếu đang ở trạng thái Nháp."))
            record.write({'state': 'cancelled'})

    def unlink(self):
        """Ngăn chặn xóa phiếu thanh lý đã duyệt."""
        for record in self:
            if record.state != 'draft' and record.state != 'cancelled':
                raise UserError(_("Không thể xóa phiếu thanh lý đã duyệt."))
        return super().unlink()

