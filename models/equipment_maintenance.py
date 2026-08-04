from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CompanyEquipmentMaintenance(models.Model):
    _name = "company.equipment.maintenance"
    _description = "Phiếu bảo trì thiết bị"
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
        required=True
    )
    
    vendor_id = fields.Many2one(
        'res.partner',
        string="Đơn vị sửa chữa"
    )
    
    request_date = fields.Date(
        string="Ngày yêu cầu", 
        required=True, 
        default=fields.Date.context_today
    )
    
    completion_date = fields.Date(
        string="Ngày hoàn thành"
    )
    
    cost = fields.Float(
        string="Chi phí sửa chữa"
    )
    
    description = fields.Text(
        string="Mô tả lỗi / Hạng mục bảo trì"
    )
    
    state = fields.Selection(
        [
            ('draft', 'Nháp'),
            ('in_progress', 'Đang bảo trì'),
            ('done', 'Đã hoàn thành'),
            ('cancelled', 'Đã hủy'),
        ], 
        string="Trạng thái", 
        default='draft', 
        required=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Tự động sinh mã phiếu bảo trì từ sequence khi tạo mới."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('company.equipment.maintenance') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        """Bắt đầu bảo trì:
        - Đổi trạng thái thiết bị sang 'Đang sửa chữa' (maintenance).
        - Đổi trạng thái phiếu bảo trì sang 'Đang bảo trì' (in_progress).
        """
        for record in self:
            if record.state != 'draft':
                continue
            
            # Đổi trạng thái thiết bị thành Đang sửa chữa
            record.equipment_id.write({
                'state': 'maintenance'
            })
            
            record.write({'state': 'in_progress'})

    def action_done(self):
        """Hoàn thành bảo trì:
        - Ghi nhận ngày hoàn thành nếu chưa nhập.
        - Đổi trạng thái thiết bị trở lại 'Trong kho' (available).
        - Đổi trạng thái phiếu sang 'Đã hoàn thành' (done).
        """
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_("Chỉ có thể hoàn thành phiếu đang ở trạng thái 'Đang bảo trì'."))
            
            if not record.completion_date:
                record.completion_date = fields.Date.context_today(self)
                
            # Đổi trạng thái thiết bị về Trong kho
            record.equipment_id.write({
                'state': 'available'
            })
            
            record.write({'state': 'done'})

    def action_cancel(self):
        """Hủy phiếu bảo trì:
        - Ngăn không cho hủy phiếu đã hoàn thành.
        - Nếu đang bảo trì mà hủy, trả thiết bị về 'Trong kho' (available).
        - Đổi trạng thái phiếu sang 'Đã hủy' (cancelled).
        """
        for record in self:
            if record.state == 'done':
                raise UserError(_("Không thể hủy phiếu bảo trì đã hoàn thành."))
            
            # Nếu đang bảo trì mà hủy, trả thiết bị về Trong kho
            if record.state == 'in_progress':
                record.equipment_id.write({
                    'state': 'available'
                })
                
            record.write({'state': 'cancelled'})

    def unlink(self):
        """Ngăn chặn xóa phiếu bảo trì đã xác nhận (chỉ cho phép xóa khi là Nháp hoặc Đã hủy)."""
        for record in self:
            if record.state not in ['draft', 'cancelled']:
                raise UserError(_("Bạn không thể xóa phiếu bảo trì đã xác nhận. Vui lòng hủy phiếu nếu cần."))
        return super().unlink()

