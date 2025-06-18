# -*- coding: utf-8 -*-

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)
class Account_payment_methods(models.Model):
    _name = 'account.payment.group'
    
    def action_reconcile_payments(self):
        self.ensure_one()
        
        # 1. Obtener TODAS las líneas no reconciliadas primero
        all_unreconciled_lines = self.to_pay_move_line_ids.filtered(lambda line: not line.reconciled)
        
        # 2. Filtrar FACTURAS (documentos originales por cobrar/pagar)
        invoices = all_unreconciled_lines.filtered(
            lambda line: line.move_id.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
        ).sorted(key=lambda line: line.date)
        
        # 3. Filtrar LÍNEAS DE CRÉDITO (notas de crédito, pagos anticipados)
        credit_lines = all_unreconciled_lines.filtered(
            lambda line: (self.partner_type == 'customer' and line.amount_residual < 0) or  # Créditos de cliente
             (self.partner_type == 'supplier' and line.amount_residual > 0)   # Créditos de proveedor
        )
        
        payments = self.to_pay_payment_ids.filtered(lambda payment: payment.state == 'draft')
        
        if self.is_advanced_payment:
            for payment in payments:
                if payment == payments[0] and self.withholding_line_ids:
                    payment.l10n_ar_withholding_line_ids = [(6, 0, self.withholding_line_ids.ids)]
                payment.action_post()
        else:
            if not invoices or not payments:
                raise UserError("No hay facturas o pagos pendientes para conciliar.")
            
            # 1. Primero conciliar créditos con facturas
            self._reconcile_credits_first(credit_lines, invoices)
            
            # 2. Obtener facturas NO RECONCILIADAS después de aplicar créditos
            remaining_invoices = invoices.filtered(lambda line: not line.reconciled)
            _logger.info(f"Facturas pendientes después de créditos: {remaining_invoices.mapped('amount_residual')}")
            
            # 3. Procesar pagos solo con facturas no reconciliadas
            for payment in payments:
                remaining_amount = payment.amount
                
                if payment == payments[0] and self.withholding_line_ids:
                    payment.l10n_ar_withholding_line_ids = [(6, 0, self.withholding_line_ids.ids)]
                
                # Lista temporal para líneas a conciliar con ESTE pago
                payment_lines = self.env['account.move.line']
                
                for invoice in remaining_invoices.filtered(lambda inv: not inv.reconciled):
                    if remaining_amount <= 0:
                        break
                        
                    if self.partner_type == 'customer' and payment.payment_type == 'inbound':
                        if invoice.amount_residual > 0:
                            amount = min(remaining_amount, invoice.amount_residual)
                            payment_lines |= invoice
                            remaining_amount -= amount
                            
                    elif self.partner_type == 'supplier' and payment.payment_type == 'outbound':
                        if invoice.amount_residual < 0:
                            amount = min(remaining_amount, abs(invoice.amount_residual))
                            payment_lines |= invoice
                            remaining_amount -= amount
                # Asignar TODAS las líneas de una vez al pago
                if payment_lines:
                    payment.to_pay_move_line_ids = [(6, 0, payment_lines.ids)]
                
                payment.action_post()
        
        # Asignar número de documento
        if not self.name:
            seq_code = 'recibo_de_pagos' if self.payment_type == 'inbound' else 'reporte_de_pagos'
            self.name = self.env['ir.sequence'].next_by_code(seq_code) or 'New'
        
        self.state = 'posted'
        return True
    
    def _reconcile_credits_first(self, credit_lines, invoices):
        """Aplica créditos a facturas y evita reconciliación doble"""
        for credit in credit_lines.filtered(lambda l: not l.reconciled):
            remaining_credit = abs(credit.amount_residual)
            
            for invoice in invoices.filtered(lambda inv: not inv.reconciled):
                if remaining_credit <= 0:
                    break
                    
                if self.partner_type == 'customer':
                    if invoice.amount_residual > 0:
                        amount = min(remaining_credit, invoice.amount_residual)
                        (credit + invoice).reconcile()
                        remaining_credit -= amount
                else:
                    if invoice.amount_residual < 0:
                        amount = min(remaining_credit, abs(invoice.amount_residual))
                        (credit + invoice).reconcile()
                        remaining_credit -= amount
                
                _logger.info(f"Conciliado crédito {credit.id} con factura {invoice.id} - Monto: {amount}")