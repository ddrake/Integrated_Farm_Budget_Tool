import io
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus.flowables import PageBreak, Spacer
from reportlab.platypus.doctemplate import (PageTemplate, BaseDocTemplate,
                                            FrameBreak, NextPageTemplate)
from reportlab.platypus.frames import Frame
from reportlab.platypus.tables import Table

# Global constants
FS = 8             # regular fontsize
HFS = FS+2           # header fontsize
BP = 1             # default bottom padding
ULBP = 2           # bottom padding for underlined cells
HBP = 4            # header bottom padding
LRBP = 4           # last row bottom padding
HP = 3             # default horizontal padding
BLNK = FS-2        # height of 'blank row'
NRM = FS+2*BP      # height of normal row
BORD = 0.75        # border width for table border
UL = 0.375         # border width for cell underline
BK = colors.black


class BudgetPdf(object):
    def __init__(self, farm_year, budget_type):
        self.farm_year = farm_year
        self.budget_type = budget_type

        budget_text = self.farm_year.budget_text[budget_type]

        self.rev_table = budget_text['rev']
        self.rev_format = budget_text['revfmt']

        budget_tables = budget_text['tables']

        self.bt_kd = budget_tables['kd']
        self.bt_pb = budget_tables['pb']
        self.bt_pa = budget_tables['pa']
        self.bt_wheatdc = budget_tables.get('wheatdc', None)
        self.budget_format = budget_text['info']

        keydata = budget_text['keydata']

        self.key_cropins = keydata['cropins']['rows']
        self.key_yield = keydata['yield']['rows']
        self.key_title = keydata['title']['rows']
        self.key_futctr = keydata['futctr']['rows']
        self.key_price = keydata['price']['rows']
        self.key_modelrun = keydata['modelrun']['rows']
        self.font = 'Helvetica'
        self.fontbold = 'Helvetica-Bold'
        self.fontitalic = 'Helvetica-Oblique'

    def create(self):
        """
        Main Method: Returns BytesIO buffer with rendered budget
        """
        buffer = io.BytesIO()

        objects_to_draw = []

        rev_table = self.get_rev_table()
        rev_table._calc(8*inch, 10*inch)
        rev_width = rev_table._width
        key_table = self.get_keydata_table()
        key_table._calc(8*inch, 10*inch)
        key_width = key_table._width
        bud_table = self.get_budget_table()
        objects_to_draw.append(Spacer(1*inch, 1*inch))
        objects_to_draw.append(rev_table)
        objects_to_draw.append(FrameBreak())
        objects_to_draw.append(Spacer(1*inch, 1*inch))
        objects_to_draw.append(key_table)
        objects_to_draw.append(NextPageTemplate('Second'))
        objects_to_draw.append(PageBreak())
        objects_to_draw.append(bud_table)

        doctemplate = BudgetDocTemplate(
            buffer, pagesize=(11*inch, 8.5*inch),
            leftMargin=0.25*inch, rightMargin=0.25*inch,
            topMargin=0.325*inch, bottomMargin=0.25*inch,
            title='Detailed Budget', author='IFBT',
            leftwidth=rev_width, rightwidth=key_width)

        make_header = self.first_page_header()
        doctemplate.build(objects_to_draw, onFirstPage=make_header)

        buffer.seek(0)
        return buffer

    def first_page_header(self):
        farm_name = self.farm_year.farm_name
        crop_year = self.farm_year.crop_year
        budget_type = ("Current Budget" if self.budget_type == 'cur' else
                       "Baseline Budget" if self.budget_type == 'base' else
                       "Budget Variance")

        def make_header(canvas, doc):
            title = f'IFBT {budget_type}'
            today = datetime.now().strftime('%m/%d/%Y')
            subtitle = f'For {farm_name}, {crop_year} crop year'
            footer = f'Printed {today}'
            page_height, page_width = canvas._pagesize
            canvas.saveState()
            canvas.setLineWidth(5)
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawCentredString(page_height/2, page_width-(.5*inch+14), title)
            # canvas.drawCentredString(page_height/2, (.5*inch+14), title)
            canvas.setFont('Helvetica', 12)
            canvas.drawCentredString(page_height/2, page_width-(.5*inch+28), subtitle)
            canvas.setFont('Helvetica', 10)
            canvas.drawString(50, 25, footer)
            # canvas.drawCentredString(page_height/2, (.5*inch+28), subtitle)
            # canvas.line(66, 72, 66, page_height-72)
            canvas.restoreState()
        return make_header

    # -------------
    # REVENUE TABLE
    # -------------
    def make_rev_sty(self, cropcols):
        boldheader = self.rev_format['bh']
        bolddata = self.rev_format['bd']
        overline = self.rev_format['ol']
        revsty = [
            # header
            ('FONT', (0, 0), (-1, 0), self.fontbold, HFS, HFS),
            ('SPAN', (0, 0), (-1, 0)),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), HBP),
            # column headers font, align
            ('FONT', (1, 1), (-1, 2), self.fontbold, FS, FS),
            ('ALIGN', (1, 1), (-1, 2), 'CENTER'),
            # rest of table default font (overridden below)
            ('FONT', (0, 3), (-1, -1), self.font, FS, FS),
            # first column alignment
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            # other columns
            ('ALIGN', (1, 2), (-1, -1), 'RIGHT'),
            # bottom padding for non-header
            ('BOTTOMPADDING', (0, 1), (-1, -2), BP),
            # bottom padding for last row
            ('BOTTOMPADDING', (0, -1), (-1, -1), LRBP),
            # horizontal padding for all
            ('RIGHTPADDING', (0, 0), (-1, -1), HP),
            ('LEFTPADDING', (0, 0), (-1, -1), HP),
            # table border
            ('LINEABOVE', (0, 1), (-1, 1), BORD, BK),
            ('LINEBELOW', (0, -1), (-1, -1), BORD, BK),
            ('LINEBEFORE', (0, 1), (0, -1), BORD, BK),
            ('LINEAFTER', (-1, 1), (-1, -1), BORD, BK),
        ]
        for r in boldheader:
            revsty.append(('FONT', (0, r+3), (0, r+3), self.fontbold, FS, FS))
        for r in bolddata:
            revsty.append(('FONT', (1, r+3), (-1, r+3), self.fontbold, FS, FS))
        for r in overline:
            revsty.append(('LINEBELOW', (1, r+3), (cropcols, r+3), UL, BK))
            revsty.append(('BOTTOMPADDING', (1, r+3), (cropcols, r+3), ULBP))
            revsty.append(('LINEBELOW', (cropcols+2, r+3), (cropcols+2, r+3), UL, BK))
            revsty.append(('BOTTOMPADDING', (cropcols+2, r+3), (cropcols+2, r+3), ULBP))
        return revsty

    def get_rev_rowheights(self):
        blankrows = [3, 7, 11, 15, 18, 21, 26, 31]
        heights = [HFS+BP+HBP if row == 0 else FS+LRBP if row == 33 else
                   BLNK if row in blankrows else NRM
                   for row in range(34)]
        return heights

    def get_rev_table(self):
        # insert extra row for spanned header (Crop Revenue)
        headers = self.rev_table[0]
        body = self.rev_table[1]
        table = headers + body
        datacols = len(headers[0][1])
        rows = [[lbl] + data[:]
                for lbl, data in table]
        # control width of blank column with spaces
        rows[0][-2] = '    '
        # insert row for spanned header (Crop Revenue)
        rows = [['Crop Revenue'] + ['']*(datacols)] + rows
        heights = self.get_rev_rowheights()
        revsty = self.make_rev_sty(datacols - 2)
        return Table(rows, hAlign='LEFT', style=revsty, rowHeights=heights)

    # --------------
    # KEY DATA TABLE
    # --------------
    def get_keydata_table(self):
        widths = []
        tables = [
            self.get_key_modelrun_table(),
            self.get_key_yield_table(),
            self.get_key_price_table(),
            self.get_key_futctr_table(),
            self.get_key_cropins_table(),
            self.get_key_title_table(),
        ]
        for table in tables:
            table._calc(8*inch, 10*inch)
            widths.append(table._width)

        rows = [['Key Assumptions']] + [[table] for table in tables]

        keysty = [
            # header
            ('FONT', (0, 0), (0, 0), self.fontbold, HFS, HFS),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (0, 0), HBP)
        ]
        return Table(rows, hAlign='LEFT', style=keysty, colWidths=[max(widths)])

    def get_common_key_sty(self):
        """ Get styles which are common to most key data tables """
        return [
            # padding for all
            ('BOTTOMPADDING', (0, 0), (-1, -2), BP),
            ('RIGHTPADDING', (0, 0), (-1, -1), HP),
            ('LEFTPADDING', (0, 0), (-1, -1), HP),
            # last row bottom padding
            ('BOTTOMPADDING', (0, -1), (-1, -1), LRBP),
            # header
            ('SPAN', (0, 0), (-1, 0)),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('LINEBELOW', (0, 0), (-1, 0), UL, BK),
            ('BOTTOMPADDING', (0, 0), (-1, 0), ULBP),
            # bold, left-aligned row labels
            ('FONT', (0, 0), (0, -1), self.fontbold, FS, FS),
            ('ALIGN', (1, 0), (0, -1), 'LEFT'),
            # bold, center-aligned col labels
            ('FONT', (1, 1), (-1, 2), self.fontbold, FS, FS),
            ('ALIGN', (1, 1), (-1, 2), 'CENTER'),
            # regular, right-aligned data
            ('FONT', (1, 3), (-1, -1), self.font, FS, FS),
            ('ALIGN', (1, 3), (-1, -1), 'RIGHT'),
            # table border
            ('LINEABOVE', (0, 0), (-1, 0), BORD, BK),
            ('LINEBELOW', (0, -1), (-1, -1), BORD, BK),
            ('LINEBEFORE', (0, 0), (0, -1), BORD, BK),
            ('LINEAFTER', (-1, 0), (-1, -1), BORD, BK),
        ]

    def get_key_title_sty(self):
        """ Get styles for title key table """
        return [
            # padding for all
            ('BOTTOMPADDING', (0, 0), (-1, -2), BP),
            ('RIGHTPADDING', (0, 0), (-1, -1), HP),
            ('LEFTPADDING', (0, 0), (-1, -1), HP),
            # last row bottom padding
            ('BOTTOMPADDING', (0, -1), (-1, -1), LRBP),
            # header
            ('SPAN', (0, 0), (-1, 0)),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('LINEBELOW', (0, 0), (-1, 0), UL, BK),
            ('BOTTOMPADDING', (0, 0), (-1, 0), ULBP),
            # bold, left-aligned row labels
            ('FONT', (0, 0), (0, -1), self.fontbold, FS, FS),
            ('ALIGN', (1, 0), (0, -1), 'LEFT'),
            # bold, center-aligned col labels
            ('FONT', (1, 1), (-1, 1), self.fontbold, FS, FS),
            ('ALIGN', (1, 1), (-1, 1), 'CENTER'),
            # regular, right-aligned data
            ('FONT', (1, 2), (-1, -1), self.font, FS, FS),
            ('ALIGN', (1, 2), (-1, -1), 'RIGHT'),
            # table border
            ('LINEABOVE', (0, 0), (-1, 0), BORD, BK),
            ('LINEBELOW', (0, -1), (-1, -1), BORD, BK),
            ('LINEBEFORE', (0, 0), (0, -1), BORD, BK),
            ('LINEAFTER', (-1, 0), (-1, -1), BORD, BK),
        ]

    def get_key_rowheights(self, rows):
        return [NRM]*(len(rows)-1) + [FS+LRBP]

    def get_key_modelrun_table(self):
        rows = []
        rows.append([self.key_modelrun[0][0]] + self.key_modelrun[0][1])
        style = [
            # bold, left-aligned labels
            ('FONT', (0, 0), (0, 0), self.fontbold, FS, FS),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            # regular, right-aligned data
            ('FONT', (1, 0), (1, 0), self.font, FS, FS),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            # padding
            ('BOTTOMPADDING', (0, 0), (-1, -1), LRBP),
            ('RIGHTPADDING', (0, 0), (-1, -1), HP),
            ('LEFTPADDING', (0, 0), (-1, -1), HP),
            # table border
            ('LINEABOVE', (0, 0), (-1, 0), BORD, BK),
            ('LINEBELOW', (0, -1), (-1, -1), BORD, BK),
            ('LINEBEFORE', (0, 0), (0, -1), BORD, BK),
            ('LINEAFTER', (-1, 0), (-1, -1), BORD, BK),
        ]
        return Table(rows, hAlign='CENTER', style=style, rowHeights=[LRBP+FS])

    def get_key_yield_table(self):
        rows = []
        rows.append([self.key_yield[0][0]] + ([''] * len(self.key_yield[1][1])))
        rows += [[lbl] + data for lbl, data in self.key_yield[1:]]
        return Table(rows, hAlign='CENTER', style=self.get_common_key_sty(),
                     rowHeights=self.get_key_rowheights(rows))

    def get_key_price_table(self):
        rows = []
        rows.append([self.key_price[0][0]] + ([''] * len(self.key_price[1][1])))
        rows += [[lbl] + data for lbl, data in self.key_price[1:]]
        return Table(rows, hAlign='CENTER', style=self.get_common_key_sty(),
                     rowHeights=self.get_key_rowheights(rows))

    def get_key_futctr_table(self):
        rows = []
        rows.append([self.key_futctr[0][0]] + ([''] * len(self.key_futctr[1][1])))
        rows += [[lbl] + data for lbl, data in self.key_futctr[1:]]
        return Table(rows, hAlign='CENTER', style=self.get_common_key_sty(),
                     rowHeights=self.get_key_rowheights(rows))

    def get_key_cropins_table(self):
        rows = []
        rows.append([self.key_cropins[0][0]] + ([''] * len(self.key_cropins[0][1])))
        rows += [[lbl] + data for lbl, data in self.key_cropins[1:]]
        style = self.get_common_key_sty()
        style.append(('LINEBELOW', (-1, -2), (-1, -2), UL, BK))
        style.append(('BOTTOMPADDING', (-1, -2), (-1, -2), ULBP))
        return Table(rows, hAlign='CENTER', style=style,
                     rowHeights=self.get_key_rowheights(rows))

    def get_key_title_table(self):
        rows = []
        rows.append([self.key_title[0][0]] + ([''] * len(self.key_title[1][1])))
        rows += [[lbl] + data for lbl, data in self.key_title[1:]]
        return Table(rows, hAlign='CENTER', style=self.get_key_title_sty(),
                     rowHeights=self.get_key_rowheights(rows))

    # --------------
    # BUDGET TABLE
    # --------------
    def get_budget_table(self):
        nsub = 3 if self.bt_wheatdc is None else 4
        rows = []
        rows.append(['PRE-TAX CASH FLOW BUDGET'] + ['']*(nsub-1))
        headers = ['Budget $(000)', 'Budget $/acre', 'Budget $/bushel']
        tables = [self.get_kd_table(), self.get_pa_table(), self.get_pb_table()]
        if self.bt_wheatdc is not None:
            headers.append('Wheat/DC')
            tables.append(self.get_wheatdc_table())
        widths = []
        for table in tables:
            table._calc(8*inch, 10*inch)
            widths.append(table._width)
        rows.append(headers)
        rows.append(tables)

        style = [
            # title
            ('FONT', (0, 0), (0, 0), self.fontbold, HFS, HFS),
            ('SPAN', (0, 0), (-1, 0)),
            ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
            ('FONT', (0, 1), (-1, 1), self.fontbold, HFS, HFS),
            ('BOTTOMPADDING', (0, 0), (-1, -2), HBP),
            ('LINEBELOW', (0, 0), (-1, 0), UL, BK),
            ('BOTTOMPADDING', (0, -1), (-1, -1), BP),
        ]
        return Table(rows, hAlign='CENTER', style=style,
                     rowHeights=[HFS+BP+HBP, None, None],
                     colWidths=[w+8 for w in widths])

    def get_common_bt_sty(self):
        return [
            # padding
            ('BOTTOMPADDING', (0, 0), (-1, -2), BP),
            ('BOTTOMPADDING', (0, -1), (-1, -1), LRBP),
            ('RIGHTPADDING', (0, 0), (-1, -1), HP),
            ('LEFTPADDING', (0, 0), (-1, -1), HP),
            # regular, right-aligned data
            ('FONT', (0, 2), (-1, -1), self.font, FS, FS),
            ('ALIGN', (0, 2), (-1, -1), 'RIGHT'),
            # table border
            ('LINEABOVE', (0, 0), (-1, 0), BORD, BK),
            ('LINEBELOW', (0, -1), (-1, -1), BORD, BK),
            ('LINEBEFORE', (0, 0), (0, -1), BORD, BK),
            ('LINEAFTER', (-1, 0), (-1, -1), BORD, BK),
        ]

    def get_bt_rowheights(self):
        blankrows = [2, 4, 10, 19, 27, 36, 40, 42, 46, 49, 51, 53]
        heights = [FS+LRBP if row == 55 else
                   BLNK if row in blankrows else NRM
                   for row in range(56)]
        return heights

    def get_kd_table(self):
        headers = self.bt_kd[0]
        body = self.bt_kd[1]
        table = headers + body
        rows = [[label] + data for label, data in table]
        style = self.get_common_bt_sty()
        # crop labels
        style += [
            ('FONT', (1, 0), (-1, 1), self.fontbold, FS, FS),
            ('ALIGN', (1, 0), (-1, 1), 'CENTER'),
            # ('LINEBELOW', (1, 1), (-1, 1), UL, BK),
        ]
        # override to align labels left
        style.append(('ALIGN', (0, 0), (0, -1), 'LEFT'))
        # add special formatting
        for r in self.budget_format['ol']:
            style.append(('LINEBELOW', (1, r+1), (-1, r+1), UL, BK))
            style.append(('BOTTOMPADDING', (1, r+1), (-1, r+1), ULBP))
        for r in self.budget_format['bh']:
            style.append(('FONT', (0, r+2), (0, r+2), self.fontbold, FS, FS))
        for r in self.budget_format['bd']:
            style.append(('FONT', (1, r+2), (-1, r+2), self.fontbold, FS, FS))
        return Table(rows, hAlign='LEFT', style=style,
                     rowHeights=self.get_bt_rowheights())

    def get_pa_table(self):
        headers = self.bt_pa[0]
        body = self.bt_pa[1]
        rows = headers + body
        style = self.get_common_bt_sty()
        # crop labels
        style += [
            ('FONT', (0, 0), (-1, 1), self.fontbold, FS, FS),
            ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
            # ('LINEBELOW', (0, 1), (-1, 1), UL, BK),
        ]
        for r in self.budget_format['ol']:
            style.append(('LINEBELOW', (0, r+1), (-1, r+1), UL, BK))
            style.append(('BOTTOMPADDING', (0, r+1), (-1, r+1), ULBP))
        return Table(rows, hAlign='LEFT', style=style,
                     rowHeights=self.get_bt_rowheights())

    def get_pb_table(self):
        headers = self.bt_pb[0]
        body = self.bt_pb[1]
        rows = headers + body
        style = self.get_common_bt_sty()
        style += [
            ('FONT', (0, 0), (-1, 1), self.fontbold, FS, FS),
            ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
            # ('LINEBELOW', (0, 1), (-1, 1), UL, BK),
        ]
        for r in self.budget_format['ol']:
            style.append(('LINEBELOW', (0, r+1), (-1, r+1), UL, BK))
            style.append(('BOTTOMPADDING', (0, r+1), (-1, r+1), ULBP))
        return Table(rows, hAlign='LEFT', style=style,
                     rowHeights=self.get_bt_rowheights())

    def get_wheatdc_table(self):
        headers = self.bt_wheatdc[0]
        body = self.bt_wheatdc[1]
        rows = headers + body
        style = self.get_common_bt_sty()
        style += [
            ('FONT', (0, 0), (-1, 1), self.fontbold, FS, FS),
            ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
            # ('LINEBELOW', (0, 1), (-1, 1), UL, BK),
        ]
        for r in self.budget_format['ol']:
            style.append(('LINEBELOW', (0, r+1), (-1, r+1), UL, BK))
            style.append(('BOTTOMPADDING', (0, r+1), (-1, r+1), ULBP))
        return Table(rows, hAlign='LEFT', style=style,
                     rowHeights=self.get_bt_rowheights())


class BudgetDocTemplate(BaseDocTemplate):
    """A document template for the Detailed budget and friends.
    """
    def __init__(self, filename, **kwargs):
        self.leftwidth = kwargs.pop('leftwidth')
        self.rightwidth = kwargs.pop('rightwidth')
        super().__init__(filename, **kwargs)

    def build(self, flowables, canvasmaker=canvas.Canvas, onFirstPage=None):
        """build the document using the flowables.  Annotate the first page using the
               onFirstPage function and later pages using the onLaterPages function.
               The onXXX pages should follow the signature

                  def myOnFirstPage(canvas, document):
                      # do annotations and modify the document
                      ...

               The functions can do things like draw logos, page numbers,
               footers, etcetera. They can use external variables to vary
               the look (for example providing page numbering or section names).
        """
        self._calc()    # in case we changed margins sizes etc
        framefull = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                          leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0,
                          id='full', showBoundary=0)

        sep = .5*inch  # separation between left and right frames

        # Compute the widths of the left table and the widest right table
        # then set frame positions and widths for equal space left and right.
        # leftwidth (width of left table) and
        # maxrightwidth (width of widest right table) are module level variables
        totwidth = self.leftwidth + self.rightwidth + sep
        space = (self.width - totwidth) / 2

        frameleft = Frame(space, self.bottomMargin,
                          self.leftwidth, self.height,
                          leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0,
                          id='left', showBoundary=0)
        frameright = Frame(space + self.leftwidth + sep, self.bottomMargin,
                           self.rightwidth, self.height,
                           leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0,
                           id='right', showBoundary=0)
        self.addPageTemplates([
            PageTemplate(id='First', frames=[frameleft, frameright],
                         pagesize=self.pagesize),
            PageTemplate(id='Second', frames=[framefull],
                         pagesize=self.pagesize)])

        if onFirstPage is not None:
            self.pageTemplates[0].beforeDrawPage = onFirstPage
        BaseDocTemplate.build(self, flowables, canvasmaker=canvasmaker)
