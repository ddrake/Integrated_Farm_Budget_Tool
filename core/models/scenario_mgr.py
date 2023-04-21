"""
Module scenario_mgr

Defines classes Choice and Scenario
Method `make_scenarios` iterates through legal configurations
for different scenarios of price and yield factor, evaluating the net cash flow
for each, then sorting and presenting the top 10 choices for each scenario.
"""
from collections import namedtuple
from datetime import datetime
import reprlib
from sys import argv

from util import Crop, Ins, Unit, Prot, Lvl
from cash_flow import CashFlow
from premium import Premium

p = Premium()

INS = ['No', 'Yes']
PROG = ['PLC', 'ARC_CO']
UNIT = ['Area', 'Ent']
PROT = ['RP', 'RP-HPE', 'YO']

CHOICES = ('ac_arc_c ac_arc_s ac_arc_w ac_plc_c ac_plc_s ac_plc_w '
           'ins_c unit_c prot_c lvl_c sco_lvl_c ' +
           'eco_lvl_c ins_s unit_s prot_s lvl_s sco_lvl_s eco_lvl_s')
Choice = namedtuple('Choice', CHOICES)


class Scenario(object):
    """
    Each scenario is for a specific price/yield factor combination
    All use the same list of precomputed choices and return a sorted list of
    results, where each result is an (index, value) pair, the index into the
    choices list and the value the net total cash flow.
    """
    def __init__(self, pf, yf, choices):
        self.pf = pf
        self.yf = yf
        self.choices = choices
        self.results = []

    def __repr__(self):
        class_name = type(self).__name__
        choices = reprlib.repr(self.choices)
        return '{}({!r}, {!r}, {})'.format(class_name, self.pf, self.yf, choices)

    def __len__(self):
        return len(self.choices)

    def __getitem__(self, position):
        return self.choices[position]

    def evaluate_choices(self):
        """
        Evaluate net cashflow for each choice with the given sensitivity
        """
        for i, c in enumerate(self.choices):
            gp_ovr = {'farm_base_acres_arc': {Crop.CORN: c.ac_arc_c,
                                              Crop.SOY: c.ac_arc_s,
                                              Crop.WHEAT: c.ac_arc_w},
                      'farm_base_acres_plc': {Crop.CORN: c.ac_plc_c,
                                              Crop.SOY: c.ac_plc_s,
                                              Crop.WHEAT: c.ac_plc_w}, }
            ci_ovr = {'insure': {Crop.CORN: c.ins_c, Crop.FULL_SOY: c.ins_s},
                      'unit': {Crop.CORN: c.unit_c, Crop.FULL_SOY: c.unit_s},
                      'protection': {Crop.CORN: c.prot_c, Crop.FULL_SOY: c.prot_s},
                      'level': {Crop.CORN: c.lvl_c, Crop.FULL_SOY: c.lvl_s},
                      'sco_level': {Crop.CORN: c.sco_lvl_c, Crop.FULL_SOY: c.sco_lvl_s},
                      'eco_level': {Crop.CORN: c.eco_lvl_c, Crop.FULL_SOY: c.eco_lvl_s},
                      'prot_factor': {Crop.CORN: 1, Crop.FULL_SOY: 1}, }

            cf = CashFlow(2023, crop_ins_overrides=ci_ovr, gov_pmt_overrides=gp_ovr,
                          prem=p)
            self.results.append((i, cf.total_cash_flow(pf=self.pf, yf=self.yf)))
        self.results.sort(reverse=True, key=lambda pr: pr[1])


def make_feasible_choices():
    """
    Construct a list of all feasible choices of crop insurance choices, including
    the choice not to ensure any crop.  The following rules are applied:
    1. SCO cannot be selected unless both the farm program is PLC and the unit
    is Enterprise
    2. The SCO level must be greater than or equal to the base level
    3. ECO may be applied for either farm program but only for Enterprise unit
    """
    choices = []
    for ac_c in [0, 1]:
        for ac_s in [0, 1]:
            for ac_w in [0, 1]:
                for ins_c in [Ins.NO, Ins.YES]:
                    for unit_c in ([Unit.AREA, Unit.ENT] if ins_c else [0]):
                        for prot_c in ([Prot.RP, Prot.RPHPE, Prot.YO]
                                       if ins_c else [Prot.RP]):
                            for lvl_c in (range(50, 90, 5)
                                          if ins_c and unit_c == Unit.ENT
                                          else range(70, 91, 5)
                                          if ins_c and unit_c == Unit.AREA else [70]):
                                for sco_lvl_c in ([Lvl.NONE] +
                                                  list(range(lvl_c, 86, 5))
                                                  if ins_c and unit_c == Unit.ENT
                                                  and ac_c == 0
                                                  else [Lvl.NONE]):
                                    for eco_lvl_c in ([Lvl.NONE, 90, 95]
                                                      if ins_c and unit_c == Unit.ENT
                                                      else [Lvl.NONE]):
                                        choice1(4220 if ac_c == 1 else 0,
                                                4150 if ac_s == 1 else 0,
                                                317 if ac_w == 1 else 0,
                                                4220 if ac_c == 0 else 0,
                                                4150 if ac_s == 0 else 0,
                                                317 if ac_w == 0 else 0,
                                                ins_c, unit_c, prot_c, lvl_c,
                                                sco_lvl_c, eco_lvl_c, choices)
    return choices


def choice1(ac_arc_c, ac_arc_s, ac_arc_w, ac_plc_c, ac_plc_s, ac_plc_w,
            ins_c, unit_c, prot_c, lvl_c, sco_lvl_c, eco_lvl_c, choices):
    """
    Helper for make_feasible_choices, whose only purpose is to make the code
    easier to read.
    """
    for ins_s in [Ins.NO, Ins.YES]:
        for unit_s in ([Unit.AREA, Unit.ENT] if ins_s else [Unit.AREA]):
            for prot_s in ([Prot.RP, Prot.RPHPE, Prot.YO]
                           if ins_s else [Prot.RP]):
                for lvl_s in (range(50, 90, 5)
                              if ins_s and unit_s == Unit.ENT else
                              range(70, 91, 5)
                              if ins_s and unit_s == Unit.AREA else [70]):
                    for sco_lvl_s in ([Lvl.NONE] + list(range(lvl_s, 86, 5))
                                      if ins_s and unit_s == Unit.ENT
                                      and ac_arc_s == 0
                                      else [Lvl.NONE]):
                        for eco_lvl_s in ([Lvl.NONE, 90, 95] if ins_s
                                          and unit_s == Unit.ENT
                                          else [Lvl.NONE]):
                            c = Choice(ac_arc_c, ac_arc_s, ac_arc_w,
                                       ac_plc_c, ac_plc_s, ac_plc_w, ins_c, unit_c,
                                       prot_c, lvl_c, sco_lvl_c, eco_lvl_c, ins_s,
                                       unit_s, prot_s, lvl_s, sco_lvl_s, eco_lvl_s)
                            choices.append(c)


def make_scenarios(nbest=10):
    """
    Construct all 500,000 choices and put them in a list.
    Iterate through the 88 scenarios of price and yield factor,
    evaluating each choice.  Print the top nbest choices for each scenario
    """
    choices = make_feasible_choices()
    price_factors = [.6, .75, .9, .95, 1, 1.05, 1.1, 1.25, 1.4, 1.65, 1.8]
    yield_factors = [.4, .55, .7, .8, .9, .95, 1, 1.05]
    scenarios = [Scenario(pf, yf, choices) for pf in price_factors
                 for yf in yield_factors]
    print(f'Created {len(scenarios)} scenarios, each with {len(choices)} choices')
    header = '\t'.join(('scenario pf yf cashflow ' + CHOICES).split())
    rslt = [header]
    rowformat = '\t'.join(['{}'] + ['{:0.2f}']*2 + ['{}']*16)
    for i, s in enumerate(scenarios):
        print(f'Evaluating scenario {i+1}: pf={s.pf}, yf={s.yf} at {datetime.now()}.')
        s.evaluate_choices()
        for j, (idx, val) in enumerate(s.results[:nbest]):
            ch = s.choices[idx]
            linestr = rowformat.format(
                i+1, s.pf, s.yf, val,  PROG[0 if ch.ac_arc_c == 0 else 1],
                PROG[0 if ch.ac_arc_s == 0 else 1],
                PROG[0 if ch.ac_arc_w == 0 else 1], INS[ch.ins_c], UNIT[ch.unit_c],
                PROT[ch.prot_c], ch.lvl_c, ch.sco_lvl_c, ch.eco_lvl_c,
                INS[ch.ins_s], UNIT[ch.unit_s], PROT[ch.prot_s], ch.lvl_s,
                ch.sco_lvl_s, ch.eco_lvl_s)
            rslt.append(linestr)
            if j == 0:
                print(f'Best is: {linestr}')
    with open('bestcases.txt', 'w') as f:
        f.write('\n'.join(rslt))
    print(f"Ending at {datetime.now()}")


if __name__ == '__main__':
    if len(argv) == 2:
        nbest = int(argv[1])
        if nbest <= 0:
            raise ValueError('nbest (number of top choices to save) must be positive')
        make_scenarios(nbest=nbest)
    else:
        make_scenarios()
