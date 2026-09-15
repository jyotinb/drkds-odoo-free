# Changelog

## 19.0.1.0.0 - 2026-09-15

First release.

- Proforma invoice document with its own model, sequence and PDF.
- Create a proforma from a quotation or from a draft customer invoice.
- Dedicated `PRO/` sequence, independent of every invoice journal sequence.
- Draft, issued, cancelled and converted states, with a link to the real
  invoice once the source document is invoiced.
- Configurable disclaimer, printed prominently on the PDF.
- Portal view and PDF download for customers who can already see the source
  quotation.
- Mail template for sending the proforma with the PDF attached.
