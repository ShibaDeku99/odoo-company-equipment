from odoo.tests.common import TransactionCase, tagged
from odoo import fields

@tagged('post_install', '-at_install', 'equipment_lifecycle')
class TestEquipmentLifecycle(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Lifecycle Employee',
        })
        cls.equipment = cls.env['company.equipment'].create({
            'name': 'MacBook Pro M3',
            'code': 'EQ/MAC/001',
            'purchase_price': 50000000,
            'state': 'available'
        })

    def test_01_full_lifecycle(self):
        # 1. Create Allocation
        alloc = self.env['company.equipment.allocation'].create({
            'equipment_id': self.equipment.id,
            'employee_id': self.employee.id,
            'date': fields.Date.context_today(self)
        })
        alloc.action_confirm()
        self.assertEqual(self.equipment.state, 'assigned')
        
        # 2. Return with maintenance
        return_ticket = self.env['company.equipment.return'].create({
            'allocation_id': alloc.id,
            'date': fields.Date.context_today(self),
            'condition': 'maintenance'
        })
        return_ticket.action_confirm()
        self.assertEqual(self.equipment.state, 'maintenance')
        
        # Check if maintenance was created
        maint = self.env['company.equipment.maintenance'].search([('return_id', '=', return_ticket.id)])
        self.assertTrue(maint)
        self.assertEqual(maint.state, 'draft')
        
        # 3. Confirm maintenance
        maint.action_confirm()
        self.assertEqual(maint.state, 'in_progress')
        
        # 4. Done maintenance
        maint.action_done()
        self.assertEqual(maint.state, 'done')
        self.assertEqual(self.equipment.state, 'available')
        
        # 5. Liquidation
        liquidation = self.env['company.equipment.liquidation'].create({
            'equipment_id': self.equipment.id,
            'date': fields.Date.context_today(self),
            'price': 10000000
        })
        liquidation.action_approve()
        self.assertEqual(self.equipment.state, 'liquidated')

    def test_02_draft_maintenance_cancel(self):
        """Test hủy phiếu bảo trì nháp sinh từ phiếu thu hồi thì thiết bị phải về Trong kho"""
        equipment = self.env['company.equipment'].create({
            'name': 'Dell XPS',
            'code': 'EQ/DELL/001',
            'state': 'available'
        })
        alloc = self.env['company.equipment.allocation'].create({
            'equipment_id': equipment.id,
            'employee_id': self.employee.id,
            'date': fields.Date.context_today(self)
        })
        alloc.action_confirm()
        
        return_ticket = self.env['company.equipment.return'].create({
            'allocation_id': alloc.id,
            'date': fields.Date.context_today(self),
            'condition': 'maintenance'
        })
        return_ticket.action_confirm()
        
        self.assertEqual(equipment.state, 'maintenance')
        
        maint = self.env['company.equipment.maintenance'].search([('return_id', '=', return_ticket.id)])
        self.assertEqual(maint.state, 'draft')
        
        # Cancel the draft maintenance
        maint.action_cancel()
        
        # Validate equipment state changed back to available
        self.assertEqual(equipment.state, 'available')
        self.assertEqual(maint.state, 'cancelled')
