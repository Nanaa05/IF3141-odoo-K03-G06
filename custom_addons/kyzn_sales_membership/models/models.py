from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import date


class ResUsers(models.Model):
    _inherit = 'res.users'

    cabang_tugas = fields.Char(string='Cabang Tempat Bertugas')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_membership = fields.Boolean(
        string='Is Membership Type',
        default=False,
    )

    membership_type = fields.Selection(
        [
            ('adult', 'Adult'),
            ('academy', 'Academy'),
        ],
        string='Tipe Membership',
    )

    membership_duration_days = fields.Integer(
        string='Durasi Membership (Hari)',
        default=30,
    )


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_member = fields.Boolean(
        string='Is a Member',
        default=False,
    )

    join_date = fields.Date(
        string='Tanggal Join Pertama Kali',
        tracking=True,
    )

    birthdate = fields.Date(
        string='Tanggal Lahir',
    )

    emergency_contact = fields.Char(
        string='Emergency Contact',
    )

    age = fields.Integer(
        string='Usia',
        compute='_compute_age',
    )

    @api.depends('birthdate')
    def _compute_age(self):
        today = date.today()
        for partner in self:
            if partner.birthdate:
                partner.age = (
                    today.year
                    - partner.birthdate.year
                    - ((today.month, today.day) < (partner.birthdate.month, partner.birthdate.day))
                )
            else:
                partner.age = 0


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    jenis_transaksi = fields.Selection(
        [
            ('baru', 'New Member'),
            ('renewal', 'Renewal'),
        ],
        string='Jenis Transaksi',
        required=True,
        default='baru',
        tracking=True,
    )

    metode_pembayaran = fields.Selection(
        [
            ('transfer', 'Bank Transfer'),
            ('qris', 'QRIS'),
            ('cc', 'Credit Card'),
            ('cash', 'Cash'),
        ],
        string='Metode Pembayaran / Transaksi',
        tracking=True,
    )

    tanggal_pembayaran = fields.Date(
        string='Tanggal Pembayaran / Transaksi',
        default=fields.Date.context_today,
        tracking=True,
    )

    promo_code = fields.Char(
        string='Kupon / Promo Code',
        help='Diisi jika customer menggunakan promo code',
    )

    nilai_pembayaran = fields.Monetary(
        string='Nilai Pembayaran / Transaksi',
        currency_field='currency_id',
        tracking=True,
    )

    membership_product_id = fields.Many2one(
        'product.product',
        string='Membership Type',
        domain="[('product_tmpl_id.is_membership', '=', True)]",
        tracking=True,
    )

    membership_type = fields.Selection(
        related='membership_product_id.product_tmpl_id.membership_type',
        string='Tipe Membership',
        store=True,
        readonly=True,
    )

    tanggal_mulai = fields.Date(
        string='Tanggal Mulai Membership',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    tanggal_expiry = fields.Date(
        string='Tanggal Expiry Membership',
        compute='_compute_tanggal_expiry',
        store=True,
        tracking=True,
    )

    follow_up_1_date = fields.Date(
        string='Tanggal Follow Up Pertama',
        compute='_compute_follow_up_dates',
        store=True,
    )

    follow_up_2_date = fields.Date(
        string='Tanggal Follow Up Kedua',
        compute='_compute_follow_up_dates',
        store=True,
    )

    follow_up_3_date = fields.Date(
        string='Tanggal Follow Up Ketiga',
        compute='_compute_follow_up_dates',
        store=True,
    )

    follow_up_status = fields.Selection(
        [
            ('pending', 'Pending Follow-up'),
            ('follow_up_1_done', 'Follow Up 1 Done'),
            ('follow_up_2_done', 'Follow Up 2 Done'),
            ('follow_up_3_done', 'Follow Up 3 Done'),
            ('done', 'All Follow-up Done'),
        ],
        string='Status Follow-up',
        default='pending',
        tracking=True,
    )

    status_validasi = fields.Selection(
        [
            ('draft', 'Draft'),
            ('to_validate', 'To Validate'),
            ('validated', 'Validated'),
            ('need_revision', 'Need Revision'),
        ],
        string='Status Validasi',
        default='draft',
        tracking=True,
    )

    catatan_koreksi = fields.Text(
        string='Catatan Koreksi (Dari Admin)',
        tracking=True,
        help='Diisi oleh Admin Sales jika status diubah menjadi Need Revision',
    )

    @api.onchange('membership_product_id')
    def _onchange_membership_product_id(self):
        for rec in self:
            if rec.membership_product_id and not rec.nilai_pembayaran:
                rec.nilai_pembayaran = rec.membership_product_id.lst_price

    @api.depends(
        'tanggal_mulai',
        'membership_product_id',
        'membership_product_id.product_tmpl_id.membership_duration_days',
    )
    def _compute_tanggal_expiry(self):
        for rec in self:
            rec.tanggal_expiry = False
            if rec.tanggal_mulai and rec.membership_product_id:
                duration_days = rec.membership_product_id.product_tmpl_id.membership_duration_days or 0
                if duration_days > 0:
                    rec.tanggal_expiry = rec.tanggal_mulai + relativedelta(days=duration_days)

    @api.depends('tanggal_pembayaran', 'jenis_transaksi')
    def _compute_follow_up_dates(self):
        for rec in self:
            rec.follow_up_1_date = False
            rec.follow_up_2_date = False
            rec.follow_up_3_date = False

            base_date = rec.tanggal_pembayaran
            if base_date and rec.jenis_transaksi == 'baru':
                rec.follow_up_1_date = base_date + relativedelta(months=1)
                rec.follow_up_2_date = base_date + relativedelta(months=2)
                rec.follow_up_3_date = base_date + relativedelta(months=3)

    def action_submit_validation(self):
        for rec in self:
            rec.status_validasi = 'to_validate'

    def action_validate(self):
        for rec in self:
            rec.status_validasi = 'validated'

            if rec.partner_id:
                rec.partner_id.is_member = True
                if not rec.partner_id.join_date:
                    rec.partner_id.join_date = rec.tanggal_mulai or rec.tanggal_pembayaran

    def action_need_revision(self):
        for rec in self:
            rec.message_post(
                body=f"Transaksi membutuhkan revisi. Catatan: {rec.catatan_koreksi or '-'}"
            )
            rec.status_validasi = 'need_revision'

    def action_mark_follow_up_1_done(self):
        for rec in self:
            rec.follow_up_status = 'follow_up_1_done'

    def action_mark_follow_up_2_done(self):
        for rec in self:
            rec.follow_up_status = 'follow_up_2_done'

    def action_mark_follow_up_3_done(self):
        for rec in self:
            rec.follow_up_status = 'follow_up_3_done'

    def action_mark_followed_up(self):
        for rec in self:
            rec.follow_up_status = 'done'
