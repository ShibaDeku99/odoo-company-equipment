from odoo.tests.common import TransactionCase
from datetime import date

class TestPhase3Automation(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.user.company_id
        
        # Lấy employee có sẵn để tránh lỗi tạo mới với res.partner constraints
        cls.employee = cls.env['hr.employee'].search([], limit=1)
        if not cls.employee:
            # Fallback nếu không có employee nào
            cls.employee = cls.env['hr.employee'].with_context(tracking_disable=True).create({
                'name': 'Test Employee Phase 3',
            })
        
        cls.equipment = cls.env['company.equipment'].create({
            'name': 'Laptop Dell Latitude 7420 (Test)',
            'code': 'TEST-LT-003',
            'serial_number': 'SN-PHASE3-001',
            'state': 'available',
            'company_id': cls.company.id,
            'purchase_price': 25000000,
        })
        
        cls.allocation = cls.env['company.equipment.allocation'].create({
            'employee_id': cls.employee.id,
            'equipment_id': cls.equipment.id,
            'date': date.today(),
            'state': 'draft',
        })
        cls.allocation.action_confirm()

    def test_01_auto_create_maintenance_on_return(self):
        """Test: Khi thu hồi với tình trạng 'Cần bảo trì', hệ thống tự động sinh phiếu bảo trì."""
        self.assertEqual(self.equipment.state, 'assigned', "Thiết bị phải ở trạng thái Đang sử dụng")
        
        equipment_return = self.env['company.equipment.return'].create({
            'allocation_id': self.allocation.id,
            'date': date.today(),
            'condition': 'maintenance',
            'state': 'draft',
        })
        
        self.assertEqual(equipment_return.maintenance_count, 0, "Lúc nháp không được có phiếu bảo trì")
        
        equipment_return.action_confirm()
        
        self.assertEqual(equipment_return.state, 'returned', "Phiếu thu hồi phải ở trạng thái Đã thu hồi")
        self.assertEqual(self.equipment.state, 'maintenance', "Trạng thái thiết bị phải tự chuyển sang Bảo trì")
        self.assertEqual(equipment_return.maintenance_count, 1, "Hệ thống phải sinh ra đúng 1 phiếu bảo trì")
        
        maintenance_record = equipment_return.maintenance_ids[0]
        self.assertEqual(maintenance_record.state, 'draft', "Phiếu bảo trì tự động sinh ra phải ở trạng thái Nháp")
        self.assertEqual(maintenance_record.equipment_id.id, self.equipment.id, "Phiếu bảo trì phải gán đúng thiết bị")
        self.assertEqual(maintenance_record.return_id.id, equipment_return.id, "Phiếu bảo trì phải liên kết đúng phiếu thu hồi gốc")

    def test_02_no_maintenance_created_if_good_condition(self):
        """Test: Thu hồi bình thường (Tốt) thì KHÔNG tạo phiếu bảo trì."""
        equipment2 = self.env['company.equipment'].create({
            'name': 'Monitor LG 24 inch',
            'code': 'TEST-MON-001',
            'state': 'available',
        })
        allocation2 = self.env['company.equipment.allocation'].create({
            'employee_id': self.employee.id,
            'equipment_id': equipment2.id,
            'date': date.today(),
        })
        allocation2.action_confirm()
        
        return2 = self.env['company.equipment.return'].create({
            'allocation_id': allocation2.id,
            'date': date.today(),
            'condition': 'good',
        })
        
        return2.action_confirm()
        
        self.assertEqual(return2.maintenance_count, 0, "Không được tạo phiếu bảo trì nếu máy trả về bình thường")
        self.assertEqual(equipment2.state, 'available', "Thiết bị phải về trạng thái Trong kho")

    def test_03_chatter_message_tracking(self):
        """Test: Đảm bảo mail.thread hoạt động và lưu vết khi đổi trạng thái thiết bị."""
        self.assertTrue(hasattr(self.equipment, 'message_post'), "Model phải được kế thừa mail.thread")
        self.assertTrue(hasattr(self.equipment, 'activity_schedule'), "Model phải được kế thừa mail.activity.mixin")
