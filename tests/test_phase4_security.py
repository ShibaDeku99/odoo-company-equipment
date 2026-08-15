from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError

@tagged('post_install', '-at_install', 'equipment_phase4')
class TestEquipmentPhase4Security(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create users
        cls.user_employee = cls.env['res.users'].create({
            'name': 'User Employee',
            'login': 'employee_test',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        cls.user_manager = cls.env['res.users'].create({
            'name': 'User Manager',
            'login': 'manager_test',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('equipment_management.group_equipment_manager').id
            ])]
        })
        
        # Create employees
        cls.employee_1 = cls.env['hr.employee'].create({
            'name': 'Employee 1',
            'user_id': cls.user_employee.id
        })
        cls.employee_manager = cls.env['hr.employee'].create({
            'name': 'Manager',
            'user_id': cls.user_manager.id
        })
        
        # Create equipments
        cls.equipment_1 = cls.env['company.equipment'].create({
            'name': 'Laptop Employee 1',
            'code': 'EQ/SEC/001',
            'state': 'assigned',
            'employee_id': cls.employee_1.id
        })
        cls.equipment_2 = cls.env['company.equipment'].create({
            'name': 'Laptop Manager',
            'code': 'EQ/SEC/002',
            'state': 'assigned',
            'employee_id': cls.employee_manager.id
        })

    def test_01_employee_access_rights(self):
        """Nhân viên thường không thể tạo, sửa, xóa thiết bị"""
        Equipment = self.env['company.equipment'].with_user(self.user_employee)
        
        # Cannot create
        with self.assertRaises(AccessError):
            Equipment.create({
                'name': 'New Laptop',
                'code': 'EQ/NEW/001'
            })
            
        # Cannot write
        with self.assertRaises(AccessError):
            self.equipment_1.with_user(self.user_employee).write({'name': 'Hacked'})
            
        # Cannot unlink
        with self.assertRaises(AccessError):
            self.equipment_1.with_user(self.user_employee).unlink()

    def test_02_employee_record_rules(self):
        """Nhân viên thường chỉ thấy thiết bị của mình"""
        Equipment = self.env['company.equipment'].with_user(self.user_employee)
        equipments = Equipment.search([])
        
        self.assertIn(self.equipment_1, equipments)
        self.assertNotIn(self.equipment_2, equipments)

    def test_03_manager_access(self):
        """Quản lý có thể xem tất cả và sửa"""
        Equipment = self.env['company.equipment'].with_user(self.user_manager)
        equipments = Equipment.search([])
        
        self.assertIn(self.equipment_1, equipments)
        self.assertIn(self.equipment_2, equipments)
        
        # Manager can write
        self.equipment_1.with_user(self.user_manager).write({'name': 'Fixed Name'})
        self.assertEqual(self.equipment_1.name, 'Fixed Name')

    def test_04_employee_maintenance_rule(self):
        """Nhân viên thấy phiếu bảo trì sinh từ phiếu thu hồi của mình"""
        # Create a return ticket for employee 1
        return_ticket = self.env['company.equipment.return'].create({
            'allocation_id': self.env['company.equipment.allocation'].create({
                'equipment_id': self.equipment_1.id,
                'employee_id': self.employee_1.id,
                'date': '2026-01-01',
                'state': 'confirmed'
            }).id,
            'date': '2026-02-01',
            'condition': 'maintenance'
        })
        return_ticket.action_confirm()
        
        Maintenance = self.env['company.equipment.maintenance'].with_user(self.user_employee)
        maint_tickets = Maintenance.search([])
        
        self.assertEqual(len(maint_tickets), 1)
        self.assertEqual(maint_tickets[0].return_id.id, return_ticket.id)
