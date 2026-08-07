# -*- coding: utf-8 -*-
from datetime import date, timedelta
from psycopg2 import IntegrityError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger
from odoo.exceptions import UserError, ValidationError
from odoo import fields


@tagged('post_install', '-at_install', 'equipment_phase2', 'equipment_all')
class TestEquipmentPhase2Constraints(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Trần Văn Tester P2',
        })
        cls.equipment_valid = cls.env['company.equipment'].create({
            'name': 'MacBook Pro M3 Max P2',
            'code': 'EQ/P2/001',
            'serial_number': 'SN-MAC-001',
            'purchase_price': 50000000.0,
            'salvage_value': 5000000.0,
            'useful_life_years': 3,
            'state': 'available',
        })

    def test_01_unique_code_and_serial(self):
        """1. Kiểm tra ràng buộc duy nhất cho Mã thiết bị và Số serial"""
        # Thử tạo thiết bị trùng số serial -> Phải chặn bởi @api.constrains
        with self.assertRaises(ValidationError):
            self.env['company.equipment'].create({
                'name': 'Laptop trùng serial',
                'code': 'EQ/P2/999',
                'serial_number': 'SN-MAC-001',  # Trùng serial với equipment_valid
            })

        # Thử tạo thiết bị trùng mã code -> Phải chặn bởi @api.constrains / _sql_constraints
        with self.assertRaises(ValidationError):
            self.env['company.equipment'].create({
                'name': 'Laptop trùng mã code',
                'code': 'EQ/P2/001',  # Trùng code với equipment_valid
                'serial_number': 'SN-UNIQUE-999',
            })

    def test_02_equipment_value_constraints(self):
        """2. Kiểm tra ràng buộc giá trị tiền và thời gian khấu hao hợp lệ trên thiết bị"""
        # a) Giá mua âm -> Chặn
        with self.assertRaises(ValidationError):
            self.env['company.equipment'].create({
                'name': 'Thiết bị giá âm',
                'code': 'EQ/NEG/01',
                'purchase_price': -1000000.0,
            })

        # b) Giá trị thu hồi âm -> Chặn
        with self.assertRaises(ValidationError):
            self.env['company.equipment'].create({
                'name': 'Thiết bị thu hồi âm',
                'code': 'EQ/NEG/02',
                'purchase_price': 10000000.0,
                'salvage_value': -500000.0,
            })

        # c) Giá trị thu hồi lớn hơn giá mua -> Chặn
        with self.assertRaises(ValidationError):
            self.env['company.equipment'].create({
                'name': 'Thiết bị thu hồi > giá mua',
                'code': 'EQ/NEG/03',
                'purchase_price': 10000000.0,
                'salvage_value': 15000000.0,
            })

        # d) Thời gian khấu hao <= 0 năm -> Chặn
        with self.assertRaises(ValidationError):
            self.env['company.equipment'].create({
                'name': 'Thiết bị khấu hao 0 năm',
                'code': 'EQ/NEG/04',
                'useful_life_years': 0,
            })

    def test_03_maintenance_constraints(self):
        """3. Kiểm tra ràng buộc chi phí và ngày tháng trên phiếu bảo trì"""
        today = fields.Date.context_today(self)
        yesterday = today - timedelta(days=1)

        # a) Chi phí sửa chữa âm -> Chặn
        with self.assertRaises(ValidationError):
            self.env['company.equipment.maintenance'].create({
                'equipment_id': self.equipment_valid.id,
                'cost': -200000.0,
                'request_date': today,
            })

        # b) Ngày hoàn thành trước ngày gửi yêu cầu -> Chặn
        with self.assertRaises(ValidationError):
            self.env['company.equipment.maintenance'].create({
                'equipment_id': self.equipment_valid.id,
                'request_date': today,
                'completion_date': yesterday,
            })

    def test_04_liquidation_constraints(self):
        """4. Kiểm tra ràng buộc giá thu hồi trên phiếu thanh lý không được âm"""
        with self.assertRaises(ValidationError):
            self.env['company.equipment.liquidation'].create({
                'equipment_id': self.equipment_valid.id,
                'price': -500000.0,
            })

    def test_05_equipment_unlink_protection(self):
        """5. Kiểm tra bảo vệ không cho phép xóa thiết bị khi đang sử dụng/bảo trì/thanh lý hoặc có lịch sử"""
        # a) Thiết bị đang sử dụng (assigned) -> Cấm xóa
        eq_assigned = self.env['company.equipment'].create({
            'name': 'Thiết bị đang gán',
            'code': 'EQ/UNLINK/01',
            'state': 'assigned',
        })
        with self.assertRaises(UserError):
            eq_assigned.unlink()

        # b) Thiết bị đang sửa chữa (maintenance) -> Cấm xóa
        eq_maintenance = self.env['company.equipment'].create({
            'name': 'Thiết bị đang sửa',
            'code': 'EQ/UNLINK/02',
            'state': 'maintenance',
        })
        with self.assertRaises(UserError):
            eq_maintenance.unlink()

        # c) Thiết bị đã thanh lý (liquidated) -> Cấm xóa
        eq_liquidated = self.env['company.equipment'].create({
            'name': 'Thiết bị đã thanh lý',
            'code': 'EQ/UNLINK/03',
            'state': 'liquidated',
        })
        with self.assertRaises(UserError):
            eq_liquidated.unlink()

        # d) Thiết bị có phiếu bảo trì liên kết -> Cấm xóa
        eq_with_history = self.env['company.equipment'].create({
            'name': 'Thiết bị có lịch sử',
            'code': 'EQ/UNLINK/04',
            'state': 'available',
        })
        self.env['company.equipment.maintenance'].create({
            'equipment_id': eq_with_history.id,
            'cost': 100000.0,
        })
        with self.assertRaises(UserError):
            eq_with_history.unlink()

        # e) Thiết bị mới tạo nháp không có lịch sử -> Cho phép xóa bình thường
        eq_clean = self.env['company.equipment'].create({
            'name': 'Thiết bị sạch',
            'code': 'EQ/UNLINK/05',
            'state': 'available',
        })
        clean_id = eq_clean.id
        eq_clean.unlink()
        self.assertFalse(self.env['company.equipment'].search([('id', '=', clean_id)]))
