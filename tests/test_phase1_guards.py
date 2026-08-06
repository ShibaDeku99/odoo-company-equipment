from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError
from odoo import fields

@tagged('post_install', '-at_install', 'equipment_phase1')
class TestEquipmentPhase1Guards(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Nguyễn Văn Test',
        })
        cls.equipment_available = cls.env['company.equipment'].create({
            'name': 'Laptop Dell Latitude Test',
            'code': 'EQ/TEST/001',
            'category': 'laptop',
            'state': 'available',
        })
        cls.equipment_assigned = cls.env['company.equipment'].create({
            'name': 'Màn hình Dell 27 Test',
            'code': 'EQ/TEST/002',
            'category': 'monitor',
            'state': 'assigned',
            'employee_id': cls.employee.id,
        })
        cls.equipment_liquidated = cls.env['company.equipment'].create({
            'name': 'Máy in cũ Test',
            'code': 'EQ/TEST/003',
            'category': 'printer',
            'state': 'liquidated',
        })

    def test_01_allocation_guards(self):
        """Kiểm tra guards trên phiếu cấp phát: không cho xóa/sửa khi đã confirm"""
        alloc = self.env['company.equipment.allocation'].create({
            'employee_id': self.employee.id,
            'equipment_id': self.equipment_available.id,
            'date': fields.Date.context_today(self),
        })
        # Xác nhận cấp phát
        alloc.action_confirm()
        self.assertEqual(self.equipment_available.state, 'assigned')
        self.assertEqual(alloc.state, 'confirmed')

        # 1. Thử xóa phiếu đã confirm -> Phải bị chặn với UserError
        with self.assertRaises(UserError):
            alloc.unlink()

        # 2. Thử sửa các trường bảo vệ -> Phải bị chặn với UserError
        other_emp = self.env['hr.employee'].create({'name': 'Trần Văn Khác'})
        with self.assertRaises(UserError):
            alloc.write({'employee_id': other_emp.id})

    def test_02_maintenance_input_validation(self):
        """Kiểm tra không cho bảo trì thiết bị đang cấp phát hoặc đã thanh lý"""
        # Không được bảo trì thiết bị đang assigned (phải thu hồi trước)
        maint_assigned = self.env['company.equipment.maintenance'].create({
            'equipment_id': self.equipment_assigned.id,
            'request_date': fields.Date.context_today(self),
        })
        with self.assertRaises(UserError):
            maint_assigned.action_confirm()

        # Không được tạo phiếu bảo trì cho thiết bị đã thanh lý
        with self.assertRaises(ValidationError):
            self.env['company.equipment.maintenance'].create({
                'equipment_id': self.equipment_liquidated.id,
                'request_date': fields.Date.context_today(self),
            })

    def test_03_maintenance_concurrency_and_guards(self):
        """Kiểm tra chống trùng lặp bảo trì, chống sửa/xóa khi đang bảo trì"""
        eq = self.env['company.equipment'].create({
            'name': 'Laptop Asus Test',
            'code': 'EQ/TEST/004',
            'category': 'laptop',
            'state': 'available',
        })
        maint1 = self.env['company.equipment.maintenance'].create({
            'equipment_id': eq.id,
            'request_date': fields.Date.context_today(self),
        })
        maint1.action_confirm()
        self.assertEqual(eq.state, 'maintenance')

        # Không thể tạo phiếu bảo trì thứ 2 khi phiếu 1 đang in_progress
        with self.assertRaises(ValidationError):
            self.env['company.equipment.maintenance'].create({
                'equipment_id': eq.id,
                'request_date': fields.Date.context_today(self),
            })

        # Không thể xóa phiếu đang bảo trì
        with self.assertRaises(UserError):
            maint1.unlink()

        # Không thể sửa thông tin bảo vệ khi đang bảo trì
        with self.assertRaises(UserError):
            maint1.write({'cost': 500000.0})

        # Hoàn thành bảo trì -> thiết bị về available
        maint1.action_done()
        self.assertEqual(eq.state, 'available')
        self.assertEqual(maint1.state, 'done')

    def test_04_liquidation_guards_and_maint_check(self):
        """Kiểm tra thanh lý: chặn khi đang bảo trì, không cho sửa/xóa khi đã duyệt"""
        eq = self.env['company.equipment'].create({
            'name': 'PC Văn Phòng Test',
            'code': 'EQ/TEST/005',
            'category': 'pc',
            'state': 'broken',
        })
        # Bắt đầu bảo trì
        maint = self.env['company.equipment.maintenance'].create({
            'equipment_id': eq.id,
            'request_date': fields.Date.context_today(self),
        })
        maint.action_confirm()

        # Thử thanh lý thiết bị đang bảo trì -> Phải bị chặn
        with self.assertRaises(ValidationError):
            self.env['company.equipment.liquidation'].create({
                'equipment_id': eq.id,
                'reason': 'broken',
            })

        # Hủy bảo trì
        maint.action_cancel()

        # Thanh lý hợp lệ
        liq = self.env['company.equipment.liquidation'].create({
            'equipment_id': eq.id,
            'reason': 'broken',
            'price': 1000000.0,
        })
        liq.action_approve()
        self.assertEqual(eq.state, 'liquidated')

        # Không cho xóa phiếu đã duyệt
        with self.assertRaises(UserError):
            liq.unlink()

        # Không cho sửa giá thanh lý đã duyệt
        with self.assertRaises(UserError):
            liq.write({'price': 2000000.0})

    def test_05_return_guards(self):
        """Kiểm tra phiếu thu hồi: không cho xóa hoặc sửa khi đã hoàn tất"""
        eq = self.env['company.equipment'].create({
            'name': 'Chuột không dây Test',
            'code': 'EQ/TEST/006',
            'category': 'other',
            'state': 'available',
        })
        alloc = self.env['company.equipment.allocation'].create({
            'employee_id': self.employee.id,
            'equipment_id': eq.id,
        })
        alloc.action_confirm()

        ret = self.env['company.equipment.return'].create({
            'allocation_id': alloc.id,
            'condition': 'good',
        })
        ret.action_confirm()
        self.assertEqual(eq.state, 'available')
        self.assertEqual(alloc.state, 'returned')
        self.assertEqual(ret.state, 'returned')

        # Không cho xóa phiếu đã thu hồi
        with self.assertRaises(UserError):
            ret.unlink()

        # Không cho sửa phiếu đã thu hồi
        with self.assertRaises(UserError):
            ret.write({'condition': 'broken'})
