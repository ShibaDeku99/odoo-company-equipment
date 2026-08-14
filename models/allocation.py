from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class CompanyEquipmentAllocation(models.Model):
    _name = "company.equipment.allocation"
    _inherit = ['mail.thread', 'mail.activity.mixin']
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
        string="Nhân viên nhận", tracking=True,
        required=True,
    )

    equipment_id = fields.Many2one(
        'company.equipment',
        string="Thiết bị", tracking=True,
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
        string="Trạng thái", tracking=True,
        default='draft',
        required=True,
    )

    note = fields.Text(
        string="Ghi chú",
    )

    @api.constrains('equipment_id', 'state')
    def _check_equipment_availability(self):
        """Kiểm tra chống cấp phát trùng lặp cho cùng 1 thiết bị."""
        for record in self:
            if record.state == 'confirmed' and record.equipment_id:
                # Kiểm tra xem có phiếu cấp phát nào khác đang confirmed cho thiết bị này không
                existing_active = self.search([
                    ('equipment_id', '=', record.equipment_id.id),
                    ('state', '=', 'confirmed'),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing_active:
                    raise ValidationError(_(
                        "Thiết bị '%s' đã được cấp phát trong phiếu '%s'. Không thể cấp phát cùng lúc."
                    ) % (record.equipment_id.display_name, existing_active.name))

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
                raise UserError(_(
                    "Thiết bị '%s' đang ở trạng thái '%s', không thể cấp phát. Thiết bị phải ở trạng thái 'Trong kho'."
                ) % (record.equipment_id.display_name, record.equipment_id.state))
            
            # Cập nhật thông tin lên thiết bị
            record.equipment_id.write({
                'state': 'assigned',
                'employee_id': record.employee_id.id,
                'allocation_date': record.date
            })
            
            # Chuyển trạng thái phiếu cấp phát
            record.write({'state': 'confirmed'})

    def write(self, vals):
        """Khóa không cho sửa thiết bị, nhân viên nhận, ngày cấp khi phiếu đã xác nhận hoặc đã thu hồi."""
        protected_fields = {'equipment_id', 'employee_id', 'date'}
        for record in self:
            if record.state in ['confirmed', 'returned']:
                modified_protected = set(vals.keys()) & protected_fields
                if modified_protected:
                    raise UserError(_(
                        "Không thể thay đổi thông tin cấp phát (%s) khi phiếu đã xác nhận hoặc đã thu hồi."
                    ) % ", ".join(modified_protected))
        return super().write(vals)

    def unlink(self):
        """Chỉ cho phép xóa phiếu cấp phát ở trạng thái Nháp (draft).
        Nghiêm cấm xóa phiếu đã cấp phát hoặc đã thu hồi để bảo toàn dữ liệu lịch sử.
        """
        for record in self:
            if record.state != 'draft':
                raise UserError(_(
                    "Không thể xóa phiếu cấp phát đã xác nhận (%s). Chứng từ này cần được lưu giữ để theo dõi lịch sử tài sản."
                ) % record.name)
        return super().unlink()
