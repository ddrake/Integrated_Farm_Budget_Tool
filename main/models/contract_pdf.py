import io
from itertools import chain, zip_longest
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.platypus.flowables import Spacer, KeepTogether
from reportlab.platypus.tables import Table

# Global constants
FS = 10            # regular fontsize
HFS = 12           # header fontsize
BP = 1             # default bottom padding
HBP = 1            # header bottom padding
ULBP = 2           # bottom padding for underlined cells
HBP = 4            # header bottom padding
LRBP = 4           # last row bottom padding
HP = 4             # default horizontal padding
NRM = FS+2*BP      # height of normal row
HH = HFS+2*HBP     # height of header row
BORD = 0.75        # border width for table border
UL = 0.25          # border width for grid
BK = colors.black
FONT = 'Helvetica'
FONTBOLD = 'Helvetica-Bold'


def mergeTwo(l1, l2):
    return [x for x in chain(*zip_longest(l1, l2)) if x is not None]


def fmtprice(price):
    if price is None:
        return ''
    price = f'{price:.2f}'
    return '-$' + price[1:] if price[0] == '-' else '$' + price


class ContractPdf(object):
    def __init__(self, farm_year):
        self.farm_year = farm_year
        self.market_crops = [mc for mc in farm_year.market_crops.all()
                             if mc.planted_acres() > 0]
        self.contracts = [(i, list(mc.get_contracts()))
                          for i, mc in enumerate(self.market_crops)]
        self.tables = []

    def create(self):
        buffer = io.BytesIO()
        self.get_tables()
        objects_to_draw = (
            [Spacer(1*inch, 1*inch)] +
            mergeTwo([KeepTogether([t]) for t in self.tables],
                     [Spacer(.25*inch, .25*inch)]*(len(self.tables)-1)))
        doc_template = SimpleDocTemplate(
            buffer, pagesize=(11*inch, 8.5*inch),
            leftMargin=0.25*inch, rightMargin=0.25*inch,
            topMargin=0.325*inch, bottomMargin=0.5*inch,
            title='Grain Contracts', author='IFBT')

        doc_template.build(objects_to_draw, onFirstPage=self.first_page_header())
        buffer.seek(0)
        return buffer

    def get_tables(self):
        for i, c in self.contracts:
            self.tables.append(self.get_table(i, c))

    def get_table(self, mcidx, contracts):
        """ Given a marketcrop index and a list of contract objects,
            construct a formatted table
        """
        mc = self.market_crops[mcidx]
        expected_total_bu = mc.expected_total_bushels()
        futures_total_bu = mc.contracted_bu()
        basis_total_bu = mc.basis_bu_locked()
        remaining_futures_bu = expected_total_bu - futures_total_bu
        remaining_basis_bu = expected_total_bu - basis_total_bu
        futures_pct_of_expected = mc.futures_pct_of_expected()
        basis_pct_of_expected = mc.basis_pct_of_expected()
        avg_futures_price = mc.avg_contract_price()
        avg_basis_price = mc.avg_locked_basis()
        crop = str(mc)
        title = f'{crop} Contracts'
        rows = [[title, '', '', '', '', '', '', ''],
                ['Contract Date', 'Bushels', 'Futures Price', 'Basis Price',
                 'Terminal', 'Contract #', 'Delivery Start', 'Delivery End']]
        for ct in contracts:
            rows.append(
                [ct.contract_date, f'{ct.bushels:,.0f}',
                 fmtprice(ct.futures_price), fmtprice(ct.basis_price),
                 ct.terminal, ct.contract_number, ct.delivery_start_date,
                 ct.delivery_end_date])
        rows.append(['Futures Totals', f'{futures_total_bu:,.0f}',
                     fmtprice(avg_futures_price), '', '', '', '', ''])
        rows.append(['Total Estimated Bu.', f'{expected_total_bu:,.0f}',
                     '', '', '', '', '', ''])
        rows.append(['Futures % of Expected', f'{futures_pct_of_expected:.0%}',
                     '', '', '', '', '', ''])
        rows.append(['Remaining Futures Bu.', f'{remaining_futures_bu:,.0f}',
                     '', '', '', '', '', ''])
        rows.append(['Basis Totals', f'{basis_total_bu:,.0f}',
                     fmtprice(avg_basis_price), '', '', '', '', ''])
        rows.append(['Total Estimated Bu.', f'{expected_total_bu:,.0f}',
                     '', '', '', '', '', ''])
        rows.append(['Basis % of Expected', f'{basis_pct_of_expected:.0%}',
                     '', '', '', '', '', ''])
        rows.append(['Remaining Basis Bu.', f'{remaining_basis_bu:,.0f}',
                     '', '', '', '', '', ''])

        return Table(rows, hAlign='CENTER', style=self.get_styles(),
                     rowHeights=self.get_rowheights(len(rows)))

    def get_styles(self):
        """
        Get all styles for table
        """
        styles = [
            # Table title
            ('FONT', (0, 0), (-1, 0), FONT, HFS, HFS),
            ('SPAN', (0, 0), (-1, 0)),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Column headers
            ('FONT', (0, 1), (-1, 1), FONTBOLD, FS, FS),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            # Data
            ('FONT', (0, 2), (-1, -1), FONT, FS, FS),
            ('GRID', (0, 1), (-1, -1), UL, BK),
            ('RIGHTPADDING', (0, 0), (-1, -1), HP),
            ('LEFTPADDING', (0, 0), (-1, -1), HP),
            # Contract Date
            ('ALIGN', (0, 2), (0, -1), 'LEFT'),
            # Bushels, Price
            ('ALIGN', (1, 2), (2, -1), 'RIGHT'),
            # Terminal, Contract #, Delivery Start, Delivery End
            ('ALIGN', (3, 2), (6, -1), 'LEFT'),
            # Table border
            ('LINEABOVE', (0, 0), (-1, 0), BORD, BK),
            ('LINEBELOW', (0, -1), (-1, -1), BORD, BK),
            ('LINEBEFORE', (0, 0), (0, -1), BORD, BK),
            ('LINEAFTER', (-1, 0), (-1, -1), BORD, BK),
            ('FONT', (0, -8), (-1, -1), FONTBOLD, FS, FS),
        ]
        return styles

    def get_rowheights(self, nrows):
        return [HH] + [NRM] * (nrows - 1)

    def get_title(self):
        return 'Grain Contracts'

    def first_page_header(self):
        farm_name = self.farm_year.farm_name
        crop_year = self.farm_year.crop_year
        base_title = self.get_title()

        def make_header(canvas, doc):
            title = f'IFBT {base_title}'
            today = datetime.now().strftime('%m/%d/%Y')
            subtitle = f'For {farm_name}, {crop_year} crop year'
            footer = f'Printed {today}'
            page_height, page_width = canvas._pagesize
            canvas.saveState()
            canvas.setLineWidth(5)
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawCentredString(page_height/2, page_width-(.5*inch+14), title)
            canvas.setFont('Helvetica', 12)
            canvas.drawCentredString(page_height/2, page_width-(.5*inch+28), subtitle)
            canvas.setFont('Helvetica', 10)
            canvas.drawString(50, 25, footer)
            canvas.restoreState()
        return make_header
