import io
from datetime import datetime
# from time import perf_counter

import numpy as np
from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.units import inch
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.platypus.flowables import Spacer
from reportlab.platypus.tables import Table

# Global constants
FS = 10             # regular fontsize
BP = 1             # default bottom padding
ULBP = 2           # bottom padding for underlined cells
HBP = 4            # header bottom padding
LRBP = 4           # last row bottom padding
HP = 4             # default horizontal padding
NRM = FS+2*BP      # height of normal row
BORD = 0.75        # border width for table border
UL = 0.25         # border width for cell underline
BK = colors.black
GRAY = Color(.5, .5, .5, .25)
RED = Color(1, 0, 0, .25)
GREEN = Color(0, 1, 0, .25)
FONT = 'Helvetica'
FONTBOLD = 'Helvetica-Bold'
# Controls the algorithm used in self.get_styles()
# If True, styles are set individually for each cell, otherwise
# we identify runs of consecutive cells for each style.
# Compared performance but the time to compute was approx 9-12 ms with either.
# Default to the simpler approach.
ALL = True


class SensPdf(object):
    def __init__(self, farm_year, senstag):
        self.farm_year = farm_year
        self.senstag = senstag
        self.sens_text = np.array(self.farm_year.sensitivity_text[senstag])
        self.rows = self.sens_text[..., 0].tolist()
        self.spans = self.sens_text[..., 1].tolist()
        self.styles = self.sens_text[..., 2].tolist()

    def create(self):
        # start = perf_counter()
        buffer = io.BytesIO()
        objects_to_draw = [Spacer(1*inch, 1*inch), self.get_table()]

        doc_template = SimpleDocTemplate(
            buffer, pagesize=(11*inch, 8.5*inch),
            leftMargin=0.25*inch, rightMargin=0.25*inch,
            topMargin=0.325*inch, bottomMargin=0.25*inch,
            title='Sensitivity Table', author='IFBT')

        doc_template.build(objects_to_draw, onFirstPage=self.first_page_header())
        buffer.seek(0)
        # print(f'With {ALL=}, {perf_counter()-start}')
        return buffer

    def get_table(self):
        return Table(self.rows, hAlign='CENTER', style=self.get_styles())

    def get_pairs_all(self, coordlists):
        """ specify each style for each cell and make reportlab do all the work """
        result = {}
        for k, pairs in coordlists.items():
            result[k] = [[pair, pair] for pair in pairs]
        return result

    def get_pairs_runs(self, coordlists):
        """ identify runs of consecutive cells to lighten the load on reportlab """
        def get_runs(pldict, colwise=False):
            ix0, ix1 = (1, 0) if colwise else (0, 1)
            rundict = {}
            pldict1 = {}
            for k, prs in pldict.items():
                runs = []
                singles = []
                run = []
                for pr in prs:
                    if (len(run) == 0 or
                            run[-1][ix0] == pr[ix0] and run[-1][ix1] + 1 == pr[ix1]):
                        # starting or continuing a run
                        run.append(pr)
                    else:
                        # run has terminated
                        if len(run) > 1:
                            runs.append(run)
                        elif len(run) > 0:
                            singles.append(run[0])
                        run = [pr]
                if len(run) > 1:
                    runs.append(run)
                elif len(run) > 0:
                    singles.append(run[0])
                pldict1[k] = singles
                rundict[k] = runs
            return rundict, pldict1

        rundict1, singlesdict = get_runs(coordlists)
        rundict2, singlesdict = get_runs(singlesdict, colwise=True)
        result = {}
        for k, v in rundict1.items():
            mergelist = rundict1[k] + rundict2[k]
            result[k] = ([[lst[0], lst[-1]] for lst in mergelist] +
                         [[sng, sng] for sng in singlesdict[k]])
        return result

    def get_spans(self):
        """
        Get span styles for table
        """
        spans = []
        for r, row in enumerate(self.spans):
            for c, col in enumerate(row):
                if col != '':
                    spans.append(('SPAN', (c, r), (c+int(col)-1, r)))
        return spans

    def get_styles(self):
        """
        Get all styles for table
        """
        # map the tailwindcss tags to simple styles
        csstags = {
            'bg-slate-100': ['bg-gray'], 'bg-green-100': ['bg-green'],
            'bg-red-100': ['bg-red'],
            'border': ['bord-t', 'bord-b', 'bord-l', 'bord-r'],
            'border-x': ['bord-l', 'bord-r'],
            'border-y': ['bord-t', 'bord-b'],
            'border-t': ['bord-t'],
            'border-b': ['bord-b'],
            'border-l': ['bord-l'],
            'border-r': ['bord-r'],
            'underline': ['bord-b'],
            'font-bold': ['bold'], 'text-left': ['left'],
            'text-right': ['right'], 'text-center': ['center'],
        }
        # map simple styles to sets of (row, col) pairs
        coordlists = {'bg-gray': [], 'bg-green': [], 'bg-red': [],
                      'bord-t': [], 'bord-b': [], 'bord-l': [], 'bord-r': [],
                      'bold': [], 'left': [], 'right': [], 'center': []}

        # populate the coordlists with (row, col) pairs
        styles = [[item.split() for item in row] for row in self.styles]
        for r, row in enumerate(styles):
            for c, col in enumerate(row):
                for sty in col:
                    simple = csstags.get(sty, None)
                    if simple is not None:
                        for sub in simple:
                            # Note: reportlab uses (c, r) like (x, y)
                            coordlists[sub].append((c, r))

        result = (self.get_pairs_all(coordlists) if ALL else
                  self.get_pairs_runs(coordlists))
        styles = [
            ('FONT', (0, 0), (-1, -1), FONT, FS, FS),
            ('RIGHTPADDING', (0, 0), (-1, -1), HP),
            ('LEFTPADDING', (0, 0), (-1, -1), HP),
            ('LINEABOVE', (0, 0), (-1, 0), BORD, BK),
            ('LINEBELOW', (0, -1), (-1, -1), BORD, BK),
            ('LINEBEFORE', (0, 0), (0, -1), BORD, BK),
            ('LINEAFTER', (-1, 0), (-1, -1), BORD, BK),
        ]
        styles += self.get_spans()
        for k, v in result.items():
            if k in 'bg-gray bg-red bg-green'.split():
                colr = k.split('-')[1]
                for sub in v:
                    styles.append(('BACKGROUND', sub[0], sub[1],
                                   (GRAY if colr == 'gray' else
                                    RED if colr == 'red' else GREEN)))
            if k == 'bold':
                for sub in v:
                    styles.append(('FONT', sub[0], sub[1], FONTBOLD, FS, FS))
            if k in 'left right center'.split():
                for sub in v:
                    styles.append(('ALIGN', sub[0], sub[1], k.upper()))
            if k in 'bord-t bord-b bord-l bord-r'.split():
                edge = k.split('-')[1]
                for sub in v:
                    styles.append((('LINEABOVE' if edge == 't' else
                                    'LINEBELOW' if edge == 'b' else
                                    'LINEBEFORE' if edge == 'l' else 'LINEAFTER'),
                                   sub[0], sub[1], UL, BK))
        return styles

    def get_rowheights(self):
        return [NRM] * 34

    def get_title(self):
        return 'Sensitivity Table' + (' Differences' if 'diff' in self.senstag else '')

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
