from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CompanyEquipmentAllocation(models.Model):
    _name = "company.equipment.allocation"
    _description = "Phiếu cấp phát thiết bị"
    _rec_name = "name"

    name = fields.Char(
        string="Mã phiếu",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string="Nhân viên nhận",
        required=True,
    )

    equipment_id = fields.Many2one(
        'company.equipment',
        string="Thiết bị",
        required=True,
        domain=[('state', '=', 'available')],
    )

    date = fields.Date(
        string="Ngày cấp",
        required=True,
        default=fields.Date.context_today,
    )

    state = fields.Selection(
        [
            ('draft', 'Nháp'),
            ('confirmed', 'Đã cấp phát'),
            ('returned', 'Đã thu hồi'),
        ],
        string="Trạng thái",
        default='draft',
        required=True,
    )

    note = fields.Text(
        string="Ghi chú",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Tự động sinh mã phiếu cấp phát từ sequence khi tạo mới."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('company.equipment.allocation') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        """Xác nhận cấp phát thiết bị cho nhân viên:
        - Kiểm tra thiết bị phải đang 'Trong kho' (available).
        - Đổi trạng thái thiết bị sang 'Đang sử dụng' (assigned).
        - Gán nhân viên và ngày bàn giao lên thiết bị.
        - Đổi trạng thái phiếu cấp phát sang 'Đã cấp phát' (confirmed).
        """
        for record in self:
            if record.state != 'draft':
                continue
            
            # Kiểm tra trạng thái thiết bị thực tế trước khi cấp phát
            if record.equipment_id.state != 'available':
                raise UserError(_("Thiết bị không ở trạng thái 'Trong kho'."))
            
            # Cập nhật thông tin lên thiết bị
            record.equipment_id.write({
                'state': 'assigned',
                'employee_id': record.employee_id.id,
                'allocation_date': record.date
            })
            
            # Chuyển trạng thái phiếu cấp phát
            record.write({'state': 'confirmed'})

