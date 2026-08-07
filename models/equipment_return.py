from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class CompanyEquipmentReturn(models.Model):
    _name = "company.equipment.return"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Phiếu thu hồi thiết bị"
    _rec_name = "name"

    name = fields.Char(
        string="Mã phiếu", 
        required=True, 
        copy=False, 
        readonly=True, 
        tracking=True,
        default=lambda self: _('New')
    )

    company_id = fields.Many2one(
        'res.company',
        string="Công ty",
        default=lambda self: self.env.company,
        required=True,
    )
    
    allocation_id = fields.Many2one(
        'company.equipment.allocation', 
        string="Phiếu cấp phát", 
        required=True,
        tracking=True,
        domain=[('state', '=', 'confirmed')]
    )
    
    equipment_id = fields.Many2one(
        'company.equipment',
        related='allocation_id.equipment_id',
        string="Thiết bị",
        store=True,
        readonly=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        related='allocation_id.employee_id',
        string="Nhân viên trả",
        store=True,
        readonly=True
    )
    
    allocation_date = fields.Date(
        string="Ngày cấp phát",
        related='allocation_id.date',
        readonly=True
    )
    
    date = fields.Date(
        string="Ngày thu hồi", 
        required=True, 
        tracking=True,
        default=fields.Date.context_today
    )
    
    condition = fields.Selection(
        [
            ('good', 'Tốt'),
            ('maintenance', 'Cần bảo trì'),
            ('broken', 'Hư hỏng'),
            ('lost', 'Mất'),
        ], 
        string="Tình trạng khi thu hồi", 
        required=True, 
        tracking=True,
        default='good'
    )
    
    note = fields.Text(string="Ghi chú")
    
    state = fields.Selection(
        [
            ('draft', 'Nháp'),
            ('returned', 'Đã thu hồi'),
            ('cancelled', 'Đã hủy'),
        ], 
        string="Trạng thái", 
        default='draft', 
        required=True,
        tracking=True
    )

    maintenance_ids = fields.One2many(
        'company.equipment.maintenance',
        'return_id',
        string="Phiếu bảo trì liên quan"
    )

    maintenance_count = fields.Integer(
        string="Số phiếu bảo trì",
        compute='_compute_maintenance_count'
    )

    @api.depends('maintenance_ids')
    def _compute_maintenance_count(self):
        for record in self:
            record.maintenance_count = len(record.maintenance_ids)

    def action_view_maintenance(self):
        """Hàm điều hướng Smart Button từ Phiếu thu hồi sang Phiếu bảo trì liên quan."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("equipment_management.action_company_equipment_maintenance")
        if len(self.maintenance_ids) == 1:
            form_view_id = self.env.ref('equipment_management.view_company_equipment_maintenance_form').id
            action['views'] = [(form_view_id, 'form')]
            action['res_id'] = self.maintenance_ids[0].id
        else:
            action['domain'] = [('id', 'in', self.maintenance_ids.ids)]
        return action

    @api.constrains('date', 'allocation_id')
    def _check_date(self):
        """Kiểm tra ngày thu hồi không được xảy ra trước ngày cấp phát."""
        for record in self:
            if record.date and record.allocation_id and record.allocation_id.date:
                if record.date < record.allocation_id.date:
                    raise ValidationError(_("Ngày thu hồi không được nhỏ hơn ngày cấp phát."))

    @api.constrains('allocation_id')
    def _check_allocation(self):
        """Kiểm tra phiếu cấp phát phải hợp lệ và chưa từng bị thu hồi trước đó."""
        for record in self:
            # 1. Chỉ thu hồi từ phiếu cấp phát đã xác nhận
            if record.allocation_id and record.allocation_id.state != 'confirmed':
                raise ValidationError(_("Chỉ được thu hồi từ phiếu cấp phát đã xác nhận."))
            
            # 2. Chống thu hồi lặp lại nhiều lần cho cùng 1 phiếu cấp phát
            existing_return = self.search([
                ('allocation_id', '=', record.allocation_id.id),
                ('state', '=', 'returned'),
                ('id', '!=', record.id)
            ])
            if existing_return:
                raise ValidationError(_("Thiết bị này đã được thu hồi trong một phiếu khác (%s).") % existing_return[0].name)

    @api.model_create_multi
    def create(self, vals_list):
        """Tự động sinh mã phiếu thu hồi từ sequence khi tạo mới."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('company.equipment.return') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        """Xác nhận thu hồi thiết bị:
        - Kiểm tra thiết bị phải đang 'Đang sử dụng' (assigned).
        - Cập nhật trạng thái mới của thiết bị theo tình trạng thực tế nhận lại (Tốt -> Trong kho, Hỏng/Mất/Bảo trì).
        - Gỡ thông tin người dùng và ngày bàn giao trên thiết bị.
        - Đổi trạng thái phiếu cấp phát sang 'Đã thu hồi' (returned).
        - Tự động tạo 1 Phiếu Bảo Trì (draft) nếu tình trạng là 'Cần bảo trì' (maintenance).
        - Đổi trạng thái phiếu thu hồi này sang 'Đã thu hồi' (returned).
        """
        for record in self:
            if record.state != 'draft':
                continue
            
            if record.equipment_id.state != 'assigned':
                raise UserError(_("Thiết bị '%s' hiện không ở trạng thái 'Đang sử dụng'.") % record.equipment_id.display_name)
            
            # Xác định trạng thái mới của thiết bị
            new_equipment_state = 'available'
            if record.condition == 'maintenance':
                new_equipment_state = 'maintenance'
            elif record.condition == 'broken':
                new_equipment_state = 'broken'
            elif record.condition == 'lost':
                new_equipment_state = 'lost'

            # 1. Cập nhật thiết bị
            record.equipment_id.write({
                'state': new_equipment_state,
                'employee_id': False,
                'allocation_date': False
            })
            
            # 2. Cập nhật phiếu cấp phát gốc
            record.allocation_id.write({
                'state': 'returned'
            })

            # 3. Tự động sinh Phiếu Bảo Trì nếu cần bảo trì
            if record.condition == 'maintenance':
                desc_text = _("Tự động tạo từ phiếu thu hồi %s.") % record.name
                if record.note:
                    desc_text += _(" Ghi chú lỗi: %s") % record.note
                
                self.env['company.equipment.maintenance'].create({
                    'equipment_id': record.equipment_id.id,
                    'request_date': record.date or fields.Date.context_today(record),
                    'description': desc_text,
                    'company_id': record.company_id.id,
                    'currency_id': record.equipment_id.currency_id.id,
                    'return_id': record.id,
                    'state': 'draft',
                })
            
            # 4. Cập nhật phiếu thu hồi
            record.write({'state': 'returned'})

    def action_cancel(self):
        """Hủy phiếu thu hồi (chỉ áp dụng cho phiếu ở trạng thái Nháp)."""
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Chỉ có thể hủy phiếu thu hồi đang ở trạng thái Nháp."))
            record.write({'state': 'cancelled'})

    def write(self, vals):
        """Khóa không cho chỉnh sửa thông tin khi phiếu đã thu hồi hoặc đã hủy."""
        protected_fields = {'allocation_id', 'date', 'condition'}
        for record in self:
            if record.state in ['returned', 'cancelled']:
                modified_protected = set(vals.keys()) & protected_fields
                if modified_protected:
                    raise UserError(_(
                        "Không thể chỉnh sửa thông tin (%s) của phiếu thu hồi đã hoàn tất hoặc đã hủy."
                    ) % ", ".join(modified_protected))
        return super().write(vals)

    def unlink(self):
        """Ngăn chặn người dùng xóa phiếu thu hồi đã xác nhận hoàn tất."""
        for record in self:
            if record.state not in ['draft', 'cancelled']:
                raise UserError(_("Bạn không thể xóa phiếu thu hồi đã xác nhận (%s). Vui lòng hủy phiếu nếu cần.") % record.name)
        return super().unlink()
