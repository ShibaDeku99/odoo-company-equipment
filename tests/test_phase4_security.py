from odoo.tests import common, tagged
from odoo.exceptions import AccessError
from odoo import fields, Command

@tagged('post_install', '-at_install', 'equipment_security', 'equipment_all')
class TestEquipmentSecurity(common.TransactionCase):
    """Bộ kiểm thử phân quyền & bảo mật dữ liệu Giai đoạn 4 (Phase 4)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_1 = cls.env.company
        cls.company_2 = cls.env['res.company'].create({'name': 'Chi Nhánh 2'})

        # Group refs
        cls.group_base_user = cls.env.ref('base.group_user')
        cls.group_equip_user = cls.env.ref('equipment_management.group_equipment_user')
        cls.group_equip_manager = cls.env.ref('equipment_management.group_equipment_manager')

        # 1. Nhân viên A
        cls.user_employee_a = cls.env['res.users'].create({
            'name': 'Nhân viên A',
            'login': 'employee_a',
            'email': 'employee_a@test.com',
            'group_ids': [Command.set([cls.group_base_user.id])],
            'company_id': cls.company_1.id,
            'company_ids': [Command.set([cls.company_1.id])],
        })
        cls.employee_a = cls.env['hr.employee'].create({
            'name': 'Nhân viên A (HR)',
            'user_id': cls.user_employee_a.id,
            'company_id': cls.company_1.id,
        })

        # 2. Nhân viên B
        cls.user_employee_b = cls.env['res.users'].create({
            'name': 'Nhân viên B',
            'login': 'employee_b',
            'email': 'employee_b@test.com',
            'group_ids': [Command.set([cls.group_base_user.id])],
            'company_id': cls.company_1.id,
            'company_ids': [Command.set([cls.company_1.id])],
        })
        cls.employee_b = cls.env['hr.employee'].create({
            'name': 'Nhân viên B (HR)',
            'user_id': cls.user_employee_b.id,
            'company_id': cls.company_1.id,
        })

        # 3. Quản lý thiết bị
        cls.user_manager = cls.env['res.users'].create({
            'name': 'Quản lý thiết bị IT',
            'login': 'manager_it',
            'email': 'manager_it@test.com',
            'group_ids': [Command.set([cls.group_base_user.id, cls.group_equip_user.id, cls.group_equip_manager.id])],
            'company_id': cls.company_1.id,
            'company_ids': [Command.set([cls.company_1.id])],
        })

        # Tạo thiết bị mẫu
        cls.equipment_a = cls.env['company.equipment'].create({
            'name': 'Laptop của NV A',
            'code': 'SEC-TB01',
            'category': 'laptop',
            'purchase_price': 15000000.0,
            'state': 'assigned',
            'employee_id': cls.employee_a.id,
            'company_id': cls.company_1.id,
        })

        cls.equipment_b = cls.env['company.equipment'].create({
            'name': 'Laptop của NV B',
            'code': 'SEC-TB02',
            'category': 'laptop',
            'purchase_price': 20000000.0,
            'state': 'assigned',
            'employee_id': cls.employee_b.id,
            'company_id': cls.company_1.id,
        })

    def test_01_employee_only_sees_own_equipment(self):
        """Test Record Rule: Nhân viên thường chỉ nhìn thấy thiết bị đang bàn giao cho mình."""
        equipments_user_a = self.env['company.equipment'].with_user(self.user_employee_a).search([])
        self.assertIn(self.equipment_a, equipments_user_a, "Nhân viên A phải nhìn thấy thiết bị của mình.")
        self.assertNotIn(self.equipment_b, equipments_user_a, "Nhân viên A KHÔNG ĐƯỢC nhìn thấy thiết bị của Nhân viên B.")

        equipments_user_b = self.env['company.equipment'].with_user(self.user_employee_b).search([])
        self.assertIn(self.equipment_b, equipments_user_b, "Nhân viên B phải nhìn thấy thiết bị của mình.")
        self.assertNotIn(self.equipment_a, equipments_user_b, "Nhân viên B KHÔNG ĐƯỢC nhìn thấy thiết bị của Nhân viên A.")

    def test_02_employee_cannot_create_or_modify_or_delete(self):
        """Test ACL: Nhân viên thường không có quyền tạo mới, sửa đổi hoặc xóa thiết bị."""
        # 1. Chặn tạo mới thiết bị
        with self.assertRaises(AccessError):
            self.env['company.equipment'].with_user(self.user_employee_a).create({
                'name': 'Máy in hack',
                'code': 'HACK-01',
                'purchase_price': 5000000.0,
            })

        # 2. Chặn sửa đổi thiết bị
        with self.assertRaises(AccessError):
            self.equipment_a.with_user(self.user_employee_a).write({
                'name': 'Laptop đã bị sửa tên trái phép'
            })

        # 3. Chặn xóa thiết bị
        test_eq = self.env['company.equipment'].create({
            'name': 'Thiết bị test xóa',
            'code': 'SEC-DEL-01',
            'state': 'available',
            'employee_id': self.employee_a.id,
            'company_id': self.company_1.id,
        })
        with self.assertRaises(AccessError):
            test_eq.with_user(self.user_employee_a).unlink()

    def test_03_manager_sees_and_manages_all(self):
        """Test Quản lý thiết bị có toàn quyền xem và quản lý thiết bị của mọi nhân viên."""
        all_equipments = self.env['company.equipment'].with_user(self.user_manager).search([])
        self.assertIn(self.equipment_a, all_equipments, "Quản lý phải xem được thiết bị của NV A.")
        self.assertIn(self.equipment_b, all_equipments, "Quản lý phải xem được thiết bị của NV B.")

        # Quản lý tạo mới thiết bị thành công
        new_device = self.env['company.equipment'].with_user(self.user_manager).create({
            'name': 'Màn hình Dell 27 inch',
            'code': 'MGR-NEW-01',
            'category': 'monitor',
            'purchase_price': 6000000.0,
        })
        self.assertTrue(new_device.id, "Quản lý phải tạo mới được thiết bị.")

    def test_04_liquidation_access_restricted_for_normal_employee(self):
        """Test Nhân viên thường không được truy cập module Thanh lý tài sản."""
        with self.assertRaises(AccessError):
            self.env['company.equipment.liquidation'].with_user(self.user_employee_a).search([])

    def test_05_multi_company_security_isolation(self):
        """Test Multi-Company Rule: Cách ly dữ liệu thiết bị giữa các công ty/chi nhánh."""
        # Tạo thiết bị tại Chi nhánh 2
        equipment_branch_2 = self.env['company.equipment'].create({
            'name': 'Server Chi Nhánh 2',
            'code': 'BRANCH2-SRV-01',
            'category': 'other',
            'purchase_price': 50000000.0,
            'company_id': self.company_2.id,
        })

        # User Manager chỉ thuộc công ty 1
        equipments_company_1 = self.env['company.equipment'].with_user(self.user_manager).search([])
        self.assertIn(self.equipment_a, equipments_company_1)
        self.assertNotIn(equipment_branch_2, equipments_company_1, "Quản lý Công ty 1 không được nhìn thấy thiết bị của Chi nhánh 2.")
