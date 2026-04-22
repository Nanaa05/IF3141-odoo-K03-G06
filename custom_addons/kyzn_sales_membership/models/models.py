from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import date
from odoo.exceptions import ValidationError

class User(models.Model):
    _inherit = 'res.users'

    cabang_tugas = fields.Char(string='Cabang Tempat Bertugas')
    
class MembershipType(models.Model):
    _inherit = 'product.template'

    membership_duration_days = fields.Integer(
        string='Durasi Membership (Hari)',
        default=30,
    )

    @api.constrains('membership_duration_days')
    def _check_membership_duration_days(self):
        for rec in self:
            if rec.membership_duration_days <= 0:
                raise ValidationError('Durasi membership harus lebih besar dari 0.')
            
class Member(models.Model):
    _inherit = 'res.partner'

    join_date = fields.Date(
        string='Tanggal Join Pertama Kali',
        tracking=True,
        copy=False,
    )

    birthdate = fields.Date(string='Tanggal Lahir')

    emergency_contact = fields.Char(string='Emergency Contact')

    age = fields.Integer(
        string='Usia',
        compute='_compute_age',
    )

    @api.depends('birthdate')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.birthdate:
                rec.age = (
                    today.year
                    - rec.birthdate.year
                    - ((today.month, today.day) < (rec.birthdate.month, rec.birthdate.day))
                )
            else:
                rec.age = 0

    @api.constrains('birthdate')
    def _check_birthdate(self):
        today = fields.Date.today()
        for rec in self:
            if rec.birthdate and rec.birthdate > today:
                raise ValidationError('Tanggal lahir tidak boleh melebihi hari ini.')
            
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

    membership_type_id = fields.Many2one(
        'product.template',
        string='Membership Type',
        tracking=True,
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

    is_active = fields.Boolean(
        string='Is Active Membership',
        compute='_compute_is_active',
        store=True,
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
            ('to_validate', 'To Validate'),
            ('need_revision', 'Need Revision'),
            ('validated', 'Validated'),
        ],
        string='Status Validasi',
        compute='_compute_status_validasi',
        store=True,
    )
    
    validation_ids = fields.One2many(
        'sale.order.validation',
        'sale_order_id',
        string='Riwayat Validasi',
    )

    @api.depends('validation_ids.status_validasi')
    def _compute_status_validasi(self):
        for rec in self:
            if not rec.validation_ids:
                rec.status_validasi = 'to_validate'
                continue

            statuses = rec.validation_ids.mapped('status_validasi')

            if 'open' in statuses:
                rec.status_validasi = 'need_revision'
            else:
                rec.status_validasi = 'validated'
    
    @api.onchange('membership_type_id')
    def _onchange_membership_type_id(self):
        for rec in self:
            if rec.membership_type_id and not rec.nilai_pembayaran:
                rec.nilai_pembayaran = rec.membership_type_id.list_price
    
    @api.depends(
        'tanggal_mulai',
        'membership_type_id',
        'membership_type_id.membership_duration_days',
    )
    def _compute_tanggal_expiry(self):
        for rec in self:
            rec.tanggal_expiry = False
            if rec.tanggal_mulai and rec.membership_type_id:
                duration_days = rec.membership_type_id.membership_duration_days or 0
                if duration_days > 0:
                    rec.tanggal_expiry = rec.tanggal_mulai + relativedelta(days=duration_days)    

    @api.depends('tanggal_mulai', 'tanggal_expiry')
    def _compute_is_active(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_active = bool(
                rec.tanggal_mulai
                and rec.tanggal_expiry
                and rec.tanggal_mulai <= today <= rec.tanggal_expiry
            )

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

    @api.constrains('nilai_pembayaran')
    def _check_nilai_pembayaran(self):
        for rec in self:
            if rec.nilai_pembayaran < 0:
                raise ValidationError('Nilai pembayaran tidak boleh negatif.')


    @api.constrains('tanggal_mulai', 'tanggal_expiry')
    def _check_membership_dates(self):
        for rec in self:
            if (
                rec.tanggal_mulai
                and rec.tanggal_expiry
                and rec.tanggal_expiry < rec.tanggal_mulai
            ):
                raise ValidationError(
                    'Tanggal expiry tidak boleh lebih awal dari tanggal mulai.'
                )

    def action_submit_validation(self):
        for rec in self:
            rec.message_post(
                body='Sales Order diajukan untuk validasi.'
            )

    def action_validate(self):
        for rec in self:
            if not rec.partner_id:
                raise ValidationError('Sales Order harus memiliki Member / Customer.')
            if not rec.membership_type_id:
                raise ValidationError('Membership Type wajib diisi sebelum validasi.')

            self.env['sale.order.validation'].create({
                'sale_order_id': rec.id,
                'sales_admin_id': self.env.user.id,
                'status_validasi': 'confirmed',
            })

            if rec.partner_id and not rec.partner_id.join_date:
                rec.partner_id.join_date = rec.tanggal_mulai or rec.tanggal_pembayaran
            
    def action_need_revision(self):
        for rec in self:
            raise ValidationError(
                'Buat record baru pada Riwayat Validasi dengan status Open dan isi catatan koreksi.'
            )
                
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


class ValidationRecord(models.Model):
    _name = 'sale.order.validation'
    _description = 'Relasi Memvalidasi antara SalesAdmin dan Sales Order'
    _order = 'create_date desc, id desc'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        ondelete='cascade',
    )

    sales_admin_id = fields.Many2one(
        'res.users',
        string='Sales Admin',
        required=True,
        ondelete='restrict',
    )

    status_validasi = fields.Selection(
        [
            ('open', 'Open'),
            ('resolved', 'Resolved'),
            ('confirmed', 'Confirmed'),
        ],
        string='Status Validasi',
        required=True,
        default='open',
)

    catatan_koreksi = fields.Text(
        string='Catatan Koreksi',
    )
    
    @api.constrains('status_validasi', 'catatan_koreksi')
    def _check_catatan_koreksi(self):
        for rec in self:
            if rec.status_validasi == 'open' and not (rec.catatan_koreksi or '').strip():
                raise ValidationError(
                    'Catatan koreksi wajib diisi ketika status validasi adalah Open.'
                )
