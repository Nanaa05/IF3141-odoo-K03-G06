from odoo import models, fields
from odoo.exceptions import ValidationError

class WizardNeedRevision(models.TransientModel):
    _name = 'kyzn.wizard.need.revision'
    _description = 'Wizard Need Revision - Input Catatan Koreksi'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        readonly=True,
    )

    catatan_koreksi = fields.Text(
        string='Catatan Koreksi',
        required=True,
    )

    def action_confirm(self):
        self.ensure_one()

        if not (self.catatan_koreksi or '').strip():
            raise ValidationError('Catatan koreksi wajib diisi.')

        self.env['sale.order.validation'].create({
            'sale_order_id': self.sale_order_id.id,
            'sales_admin_id': self.env.user.id,
            'status_validasi': 'open',
            'catatan_koreksi': self.catatan_koreksi,
        })

        self.sale_order_id.message_post(
            body=f'Sales Order perlu revisi: {self.catatan_koreksi}'
        )

        return {'type': 'ir.actions.act_window_close'}
