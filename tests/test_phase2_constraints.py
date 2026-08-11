from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger
from odoo import fields
from datetime import timedelta

@tagged('equipment_all', 'post_install', '-at_install')
class TestPhase2Constraints(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Equipment = cls.env['company.equipment']
        cls.Maintenance = cls.env['company.equipment.maintenance']
        cls.Liquidation = cls.env['company.equipment.liquidation']
        
        # Tạo thiết bị chuẩn để test
        cls.equipment = cls.Equipment.create({
            'name': 'Test Equipment Phase 2',
            'code': 'EQ-P2-001',
            'serial_number': 'SN-P2-001',
            'purchase_price': 1000000,
            'salvage_value': 200000,
            'useful_life_years': 5,
        })

    def test_01_equipment_unique_code_and_serial(self):
        """Test ràng buộc duy nhất cho Mã thiết bị và Số Serial (SQL Constraints)"""
        
        # Cố tình tạo thiết bị trùng mã Code
        with mute_logger('odoo.sql_db'), self.assertRaises(Exception):
            self.Equipment.create({
                'name': 'Duplicate Code',
                'code': 'EQ-P2-001',
                'serial_number': 'SN-NEW-001',
            })
            self.env.flush_all()

        # Cố tình tạo thiết bị trùng Serial
        with mute_logger('odoo.sql_db'), self.assertRaises(Exception):
            self.Equipment.create({
                'name': 'Duplicate Serial',
                'code': 'EQ-NEW-001',
                'serial_number': 'SN-P2-001',
            })
            self.env.flush_all()

    def test_02_equipment_financial_constraints(self):
        """Test ràng buộc giá trị tài chính của thiết bị (api.constrains)"""
        
        # 1. Giá mua âm
        with self.assertRaises(ValidationError):
            self.Equipment.create({
                'name': 'Negative Purchase',
                'code': 'EQ-N1',
                'purchase_price': -100,
                'salvage_value': 0,
                'useful_life_years': 5,
            })
            
        # 2. Giá trị thu hồi âm
        with self.assertRaises(ValidationError):
            self.Equipment.create({
                'name': 'Negative Salvage',
                'code': 'EQ-N2',
                'purchase_price': 1000,
                'salvage_value': -100,
                'useful_life_years': 5,
            })
            
        # 3. Giá trị thu hồi > Giá mua
        with self.assertRaises(ValidationError):
            self.Equipment.create({
                'name': 'Salvage > Purchase',
                'code': 'EQ-N3',
                'purchase_price': 1000,
                'salvage_value': 2000,
                'useful_life_years': 5,
            })
            
        # 4. Thời gian khấu hao <= 0
        with self.assertRaises(ValidationError):
            self.Equipment.create({
                'name': 'Zero Life',
                'code': 'EQ-N4',
                'purchase_price': 1000,
                'salvage_value': 100,
                'useful_life_years': 0,
            })

    def test_03_maintenance_constraints(self):
        """Test ràng buộc của phiếu bảo trì (api.constrains)"""
        
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        
        # 1. Chi phí sửa chữa âm
        with self.assertRaises(ValidationError):
            self.Maintenance.create({
                'equipment_id': self.equipment.id,
                'request_date': today,
                'cost': -500,
            })
            
        # 2. Ngày hoàn thành < Ngày yêu cầu
        with self.assertRaises(ValidationError):
            self.Maintenance.create({
                'equipment_id': self.equipment.id,
                'request_date': today,
                'completion_date': yesterday,
                'cost': 1000,
            })

    def test_04_liquidation_constraints(self):
        """Test ràng buộc của phiếu thanh lý (api.constrains)"""
        
        # 1. Giá thanh lý âm
        with self.assertRaises(ValidationError):
            self.Liquidation.create({
                'equipment_id': self.equipment.id,
                'date': fields.Date.today(),
                'reason': 'old',
                'price': -1000,
            })
