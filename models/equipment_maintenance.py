from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class CompanyEquipmentMaintenance(models.Model):
    _name = "company.equipment.maintenance"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Phiếu bảo trì thiết bị"
    _rec_name = "name"

    return_id = fields.Many2one('company.equipment.return', string="Phiếu thu hồi gốc", readonly=True)

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

    currency_id = fields.Many2one(
        'res.currency',
        string="Tiền tệ",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    
    equipment_id = fields.Many2one(
        'company.equipment', 
        string="Thiết bị", 
        required=True,
        domain=[('state', 'in', ['available', 'broken'])]
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
    
    cost = fields.Monetary(
        string="Chi phí sửa chữa", tracking=True,
        currency_field='currency_id',
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
        string="Trạng thái", tracking=True,
        default='draft', 
        required=True
    )

    @api.constrains('cost', 'request_date', 'completion_date')
    def _check_maintenance_data(self):
        for record in self:
            if record.cost < 0:
                raise ValidationError(_("Chi phí sửa chữa không được là số âm."))
            if record.completion_date and record.request_date and record.completion_date < record.request_date:
                raise ValidationError(_("Ngày hoàn thành không được nhỏ hơn Ngày yêu cầu."))

    @api.constrains('equipment_id', 'state')
    def _check_equipment_state(self):
        """Kiểm tra tính hợp lệ của thiết bị và chống trùng lặp phiếu bảo trì."""
        for record in self:
            if not record.equipment_id:
                continue

            # 1. Chống tạo/xác nhận nhiều phiếu bảo trì cùng lúc cho 1 thiết bị
            if record.state in ['draft', 'in_progress']:
                active_maintenance = self.search([
                    ('equipment_id', '=', record.equipment_id.id),
                    ('state', '=', 'in_progress'),
                    ('id', '!=', record.id)
                ], limit=1)
                if active_maintenance:
                    raise ValidationError(_(
                        "Thiết bị '%s' đang có phiếu bảo trì '%s' đang xử lý. Không thể tạo thêm phiếu bảo trì khác."
                    ) % (record.equipment_id.display_name, active_maintenance.name))

            # 2. Không cho phép tạo bảo trì đối với thiết bị đã thanh lý hoặc đã mất
            if record.state in ['draft', 'in_progress'] and record.equipment_id.state in ['liquidated', 'lost']:
                raise ValidationError(_(
                    "Không thể đưa thiết bị '%s' vào bảo trì vì thiết bị đã ở trạng thái '%s'."
                ) % (record.equipment_id.display_name, record.equipment_id.state))

    @api.model_create_multi
    def create(self, vals_list):
        """Tự động sinh mã phiếu bảo trì từ sequence khi tạo mới."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('company.equipment.maintenance') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        """Bắt đầu bảo trì:
        - Kiểm tra trạng thái đầu vào hợp lệ: chỉ cho phép bảo trì thiết bị trong kho (available) hoặc hư hỏng (broken).
        - Nếu thiết bị đang cấp phát (assigned), yêu cầu thu hồi trước.
        - Đổi trạng thái thiết bị sang 'Đang sửa chữa' (maintenance).
        - Đổi trạng thái phiếu bảo trì sang 'Đang bảo trì' (in_progress).
        """
        for record in self:
            if record.state != 'draft':
                continue

            equipment = record.equipment_id
            if equipment.state == 'assigned':
                raise UserError(_(
                    "Thiết bị '%s' đang được giao cho nhân viên sử dụng. Vui lòng tạo phiếu thu hồi trước khi gửi bảo trì."
                ) % equipment.display_name)
            
            if equipment.state in ['liquidated', 'lost']:
                raise UserError(_(
                    "Không thể bảo trì thiết bị '%s' vì thiết bị đã ở trạng thái '%s'."
                ) % (equipment.display_name, equipment.state))

            # Kiểm tra chống trùng lặp bảo trì
            active_maint = self.search([
                ('equipment_id', '=', equipment.id),
                ('state', '=', 'in_progress'),
                ('id', '!=', record.id)
            ], limit=1)
            if active_maint:
                raise UserError(_(
                    "Thiết bị '%s' đang có phiếu bảo trì '%s' đang thực hiện."
                ) % (equipment.display_name, active_maint.name))
            
            # Đổi trạng thái thiết bị thành Đang sửa chữa
            equipment.write({
                'state': 'maintenance'
            })
            
            record.write({'state': 'in_progress'})

    def action_done(self):
        """Hoàn thành bảo trì:
        - Ghi nhận ngày hoàn thành nếu chưa nhập.
        - Kiểm tra chống 'hồi sinh' thiết bị: nếu thiết bị đã bị thanh lý/mất thì không đổi về available.
        - Đổi trạng thái thiết bị trở lại 'Trong kho' (available).
        - Đổi trạng thái phiếu sang 'Đã hoàn thành' (done).
        """
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_("Chỉ có thể hoàn thành phiếu đang ở trạng thái 'Đang bảo trì'."))
            
            equipment = record.equipment_id
            if equipment.state != 'maintenance':
                raise UserError(_(
                    "Không thể hoàn thành bảo trì: Thiết bị '%s' hiện không ở trạng thái 'Đang sửa chữa' (Trạng thái hiện tại: '%s')."
                ) % (equipment.display_name, equipment.state))
            
            if not record.completion_date:
                record.completion_date = fields.Date.context_today(self)
                
            # Đổi trạng thái thiết bị về Trong kho
            equipment.write({
                'state': 'available'
            })
            
            record.write({'state': 'done'})

    def action_cancel(self):
        """Hủy phiếu bảo trì:
        - Ngăn không cho hủy phiếu đã hoàn thành.
        - Nếu đang bảo trì mà hủy, trả thiết bị về 'Trong kho' (available) nếu thiết bị vẫn đang ở maintenance.
        - Đổi trạng thái phiếu sang 'Đã hủy' (cancelled).
        """
        for record in self:
            if record.state == 'done':
                raise UserError(_("Không thể hủy phiếu bảo trì đã hoàn thành."))
            
            # Nếu đang bảo trì mà hủy, trả thiết bị về Trong kho nếu vẫn đang ở maintenance
            if record.state == 'in_progress' and record.equipment_id.state == 'maintenance':
                record.equipment_id.write({
                    'state': 'available'
                })
                
            record.write({'state': 'cancelled'})

    def write(self, vals):
        """Khóa không cho chỉnh sửa các trường cốt lõi khi phiếu đã xác nhận hoặc hoàn thành."""
        protected_fields = {'equipment_id', 'vendor_id', 'request_date', 'cost'}
        for record in self:
            if record.state in ['in_progress', 'done', 'cancelled']:
                modified_protected = set(vals.keys()) & protected_fields
                if modified_protected:
                    raise UserError(_(
                        "Không thể chỉnh sửa các thông tin bảo trì (%s) khi phiếu đã xác nhận hoặc hoàn thành."
                    ) % ", ".join(modified_protected))
        return super().write(vals)

    def unlink(self):
        """Ngăn chặn xóa phiếu bảo trì đã xác nhận (chỉ cho phép xóa khi là Nháp hoặc Đã hủy)."""
        for record in self:
            if record.state not in ['draft', 'cancelled']:
                raise UserError(_("Bạn không thể xóa phiếu bảo trì đã xác nhận (%s). Vui lòng hủy phiếu nếu cần.") % record.name)
        return super().unlink()
