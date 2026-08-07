# -*- coding: utf-8 -*-
from datetime import date
from odoo.tests.common import TransactionCase, tagged
from odoo import fields


@tagged('post_install', '-at_install', 'equipment_phase3', 'equipment_all')
class TestEquipmentPhase3AutomationChatter(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Nguyễn Văn Tester P3',
        })
        cls.equipment = cls.env['company.equipment'].create({
            'name': 'Dell XPS 15 Phase 3',
            'code': 'EQ/P3/001',
            'serial_number': 'SN-DELL-P3-001',
            'purchase_price': 35000000.0,
            'useful_life_years': 3,
            'state': 'available',
        })

    def _allocate_equipment(self, equipment, employee):
        """Helper để cấp phát thiết bị cho nhân viên."""
        allocation = self.env['company.equipment.allocation'].create({
            'equipment_id': equipment.id,
            'employee_id': employee.id,
            'date': fields.Date.today(),
        })
        allocation.action_confirm()
        return allocation

    def test_01_auto_create_maintenance_on_return(self):
        """1. Kiểm tra tự động tạo Phiếu Bảo Trì khi thu hồi máy với tình trạng 'Cần bảo trì'"""
        allocation = self._allocate_equipment(self.equipment, self.employee)
        self.assertEqual(self.equipment.state, 'assigned')
        self.assertEqual(self.equipment.employee_id, self.employee)

        # Tạo phiếu thu hồi với tình trạng condition = 'maintenance'
        return_doc = self.env['company.equipment.return'].create({
            'allocation_id': allocation.id,
            'date': fields.Date.today(),
            'condition': 'maintenance',
            'note': 'Hỏng quạt tản nhiệt và bàn phím',
        })
        self.assertEqual(return_doc.state, 'draft')
        self.assertEqual(return_doc.maintenance_count, 0)

        # Bấm Xác nhận thu hồi
        return_doc.action_confirm()

        # Kiểm tra trạng thái sau thu hồi
        self.assertEqual(return_doc.state, 'returned')
        self.assertEqual(allocation.state, 'returned')
        self.assertEqual(self.equipment.state, 'maintenance')
        self.assertFalse(self.equipment.employee_id)

        # Kiểm tra tự động sinh phiếu bảo trì
        self.assertEqual(return_doc.maintenance_count, 1)
        maintenance = return_doc.maintenance_ids[0]
        self.assertEqual(maintenance.equipment_id, self.equipment)
        self.assertEqual(maintenance.return_id, return_doc)
        self.assertEqual(maintenance.state, 'draft')
        self.assertEqual(maintenance.company_id, return_doc.company_id)
        self.assertEqual(maintenance.currency_id, self.equipment.currency_id)
        self.assertIn('Hỏng quạt tản nhiệt và bàn phím', maintenance.description)

    def test_02_no_maintenance_on_good_return(self):
        """2. Kiểm tra KHÔNG tạo Phiếu Bảo Trì khi thu hồi máy với tình trạng 'Tốt'"""
        equip = self.env['company.equipment'].create({
            'name': 'Màn hình Dell Ultrasharp P3',
            'code': 'EQ/P3/002',
            'purchase_price': 10000000.0,
            'state': 'available',
        })
        allocation = self._allocate_equipment(equip, self.employee)

        # Thu hồi máy tình trạng 'Tốt'
        return_doc = self.env['company.equipment.return'].create({
            'allocation_id': allocation.id,
            'date': fields.Date.today(),
            'condition': 'good',
        })
        return_doc.action_confirm()

        # Trạng thái thiết bị về trong kho (available) và không có phiếu bảo trì
        self.assertEqual(equip.state, 'available')
        self.assertEqual(return_doc.maintenance_count, 0)
        self.assertFalse(return_doc.maintenance_ids)

    def test_03_smart_button_action(self):
        """3. Kiểm tra hàm điều hướng Smart Button từ Phiếu thu hồi sang Phiếu bảo trì"""
        equip = self.env['company.equipment'].create({
            'name': 'MacBook Pro P3 SmartBtn',
            'code': 'EQ/P3/003',
            'purchase_price': 40000000.0,
            'state': 'available',
        })
        allocation = self._allocate_equipment(equip, self.employee)

        return_doc = self.env['company.equipment.return'].create({
            'allocation_id': allocation.id,
            'date': fields.Date.today(),
            'condition': 'maintenance',
            'note': 'Lỗi nguồn',
        })
        return_doc.action_confirm()

        # Gọi action điều hướng từ Smart button
        action = return_doc.action_view_maintenance()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get('res_model'), 'company.equipment.maintenance')
        self.assertEqual(action.get('res_id'), return_doc.maintenance_ids[0].id)

    def test_04_maintenance_full_lifecycle_from_return(self):
        """4. Kiểm tra chu trình hoàn tất bảo trì xuất phát từ phiếu thu hồi"""
        equip = self.env['company.equipment'].create({
            'name': 'ThinkPad X1 Carbon P3',
            'code': 'EQ/P3/004',
            'purchase_price': 30000000.0,
            'state': 'available',
        })
        allocation = self._allocate_equipment(equip, self.employee)

        return_doc = self.env['company.equipment.return'].create({
            'allocation_id': allocation.id,
            'condition': 'maintenance',
        })
        return_doc.action_confirm()

        maintenance = return_doc.maintenance_ids[0]
        self.assertEqual(maintenance.state, 'draft')

        # Xác nhận bắt đầu bảo trì
        maintenance.action_confirm()
        self.assertEqual(maintenance.state, 'in_progress')
        self.assertEqual(equip.state, 'maintenance')

        # Hoàn tất bảo trì -> Thiết bị trở lại Trong kho (available)
        maintenance.write({'cost': 1500000.0})
        maintenance.action_done()
        self.assertEqual(maintenance.state, 'done')
        self.assertEqual(equip.state, 'available')

    def test_05_mail_chatter_models_inherited(self):
        """5. Kiểm tra tất cả 5 model đều kế thừa thành công mail.thread và mail.activity.mixin"""
        models_to_check = [
            'company.equipment',
            'company.equipment.allocation',
            'company.equipment.return',
            'company.equipment.maintenance',
            'company.equipment.liquidation',
        ]
        for model_name in models_to_check:
            model_cls = self.env[model_name]
            self.assertTrue(
                hasattr(model_cls, 'message_post'),
                f"Model {model_name} chưa kế thừa mail.thread!"
            )
            self.assertTrue(
                hasattr(model_cls, 'activity_schedule'),
                f"Model {model_name} chưa kế thừa mail.activity.mixin!"
            )
