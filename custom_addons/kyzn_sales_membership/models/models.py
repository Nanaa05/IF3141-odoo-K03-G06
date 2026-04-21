from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import date

class ResUsers(models.Model):
    _inherit = 'res.users'
    cabang_tugas = fields.Char(string='Cabang Tempat Bertugas')
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    is_membership = fields.Boolean(string='Is Membership Package', default=False)
    durasi_hari = fields.Integer(string='Durasi (Hari)')

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_member = fields.Boolean(string='Is a Member', default=False)
    join_date = fields.Date(string='Tanggal Join Pertama', tracking=True)
    
    membership_age_months = fields.Integer(
        string='Umur Member (Bulan)',
        compute='_compute_membership_age'
    )

    @api.depends('join_date')
    def _compute_membership_age(self):
        for partner in self:
            if partner.join_date:
                delta = relativedelta(date.today(), partner.join_date)
                partner.membership_age_months = delta.years * 12 + delta.months
            else:
                partner.membership_age_months = 0

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    jenis_transaksi = fields.Selection([
        ('baru', 'Baru'),
        ('renewal', 'Renewal')
    ], string='Jenis Transaksi', required=True, default='baru', tracking=True)
    
    tanggal_mulai = fields.Date(
        string='Tanggal Mulai Membership', 
        required=True, 
        default=fields.Date.context_today
    )
    
    metode_pembayaran = fields.Selection([
        ('transfer', 'Bank Transfer'),
        ('qris', 'QRIS'),
        ('cc', 'Credit Card'),
        ('cash', 'Cash')
    ], string='Metode Pembayaran')
    
    status_validasi = fields.Selection([
        ('draft', 'Draft'),
        ('to_validate', 'To Validate'),
        ('validated', 'Validated'),
        ('need_revision', 'Need Revision')
    ], string='Status Validasi', default='draft', tracking=True)
    
    catatan_koreksi = fields.Text(
        string='Catatan Koreksi (Dari Admin)', 
        tracking=True,
        help="Diisi oleh Admin Sales jika status diubah menjadi Need Revision"
    )

    follow_up_status = fields.Selection([
        ('pending', 'Pending Follow-up'),
        ('done', 'Followed Up')
    ], string='Status Follow-up', default='pending', tracking=True)

    next_follow_up_date = fields.Date(
        string='Tanggal Follow-up Selanjutnya',
        compute='_compute_next_follow_up_date',
        store=True
    )

    @api.depends('tanggal_mulai', 'jenis_transaksi')
    def _compute_next_follow_up_date(self):
        for rec in self:
            if rec.tanggal_mulai and rec.jenis_transaksi == 'baru':
                rec.next_follow_up_date = rec.tanggal_mulai + relativedelta(months=1)
            else:
                rec.next_follow_up_date = False

    def action_submit_validation(self):
        for rec in self:
            rec.status_validasi = 'to_validate'

    def action_validate(self):
        for rec in self:
            rec.status_validasi = 'validated'
            if rec.jenis_transaksi == 'baru' and rec.partner_id:
                rec.partner_id.is_member = True
                if not rec.partner_id.join_date:
                    rec.partner_id.join_date = rec.tanggal_mulai

    def action_need_revision(self):
        for rec in self:
            rec.message_post(body=f"Transaksi membutuhkan revisi. Catatan: {rec.catatan_koreksi}")
            rec.status_validasi = 'need_revision'
            
    def action_mark_followed_up(self):
        for rec in self:
            rec.follow_up_status = 'done'
