"""
Module scenario_mgr

Defines classes Choice and Scenario
Method `make_scenarios` iterates through legal configurations
for different scenarios of price and yield factor, evaluating the net cash flow
for each, then sorting and presenting the top 10 choices for each scenario.
"""
from collections import namedtuple
from datetime import datetime
from sys import argv

from ifbt import (CashFlow, NO, YES, AREA, ENT, RP, RPHPE, YO, NONE, PLC, ARC_CO)


INS = ['No', 'Yes']
PROG = ['PLC', 'ARC_CO']
UNIT = ['Area', 'Ent']
PROT = ['RP', 'RP-HPE', 'YO']

CHOICES = ('prog_c prog_s prog_w ins_c unit_c prot_c lvl_c sco_lvl_c ' +
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

    def evaluate_choices(self):
        """
        Evaluate net cashflow for each choice with the given sensitivity
        """
        for i, c in enumerate(self.choices):
            gp_ovr = {'program_corn': c.prog_c, 'program_soy': c.prog_s,
                      'program_wheat': c.prog_w}
            ci_ovr = {'insure_corn': c.ins_c, 'unit_corn': c.unit_c,
                      'protection_corn': c.prot_c, 'level_corn': c.lvl_c,
                      'sco_level_corn': c.sco_lvl_c, 'eco_level_corn': c.eco_lvl_c,
                      'selected_pmt_factor_sorn': 1, 'insure_soy': c.ins_s,
                      'unit_soy': c.unit_s, 'protection_soy': c.prot_s,
                      'level_soy': c.lvl_s, 'sco_level_soy': c.sco_lvl_s,
                      'eco_level_soy': c.eco_lvl_s, 'selected_pmt_factor_soy': 1}

            cf = CashFlow(2023, crop_ins_overrides=ci_ovr, gov_pmt_overrides=gp_ovr)
            self.results.append((i, cf.total_cash_flow(pf=self.pf, yf=self.yf)))
        self.results.sort(reverse=True, key=lambda pr: pr[1])


def choice1(prog_c, prog_s, prog_w, ins_c, unit_c,
            prot_c, lvl_c, sco_lvl_c, eco_lvl_c, choices):
    """
    Helper for make_feasible_choices, whose only purpose is to make the code
    easier to read.
    """
    for ins_s in [NO, YES]:
        for unit_s in ([AREA, ENT] if ins_s == YES else [AREA]):
            for prot_s in ([RP, RPHPE, YO] if ins_s == YES else [RP]):
                for lvl_s in (range(50, 90, 5)
                              if ins_s == YES and unit_s == ENT else
                              range(70, 91, 5)
                              if ins_s == YES and unit_s == AREA else [70]):
                    for sco_lvl_s in ([NONE] + list(range(lvl_s, 86, 5))
                                      if ins_s == YES and unit_s == ENT
                                      and prog_s == PLC
                                      else [NONE]):
                        for eco_lvl_s in ([NONE, 90, 95] if ins_s == YES
                                          and unit_s == ENT
                                          else [NONE]):
                            c = Choice(prog_c, prog_s, prog_w, ins_c, unit_c,
                                       prot_c, lvl_c, sco_lvl_c, eco_lvl_c, ins_s,
                                       unit_s, prot_s, lvl_s, sco_lvl_s, eco_lvl_s)
                            choices.append(c)


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
    for prog_c in [PLC, ARC_CO]:
        for prog_s in [PLC, ARC_CO]:
            for prog_w in [PLC, ARC_CO]:
                for ins_c in [NO, YES]:
                    for unit_c in ([AREA, ENT] if ins_c == YES else [0]):
                        for prot_c in ([RP, RPHPE, YO] if ins_c == YES else [RP]):
                            for lvl_c in (range(50, 90, 5)
                                          if ins_c == YES and unit_c == ENT
                                          else range(70, 91, 5)
                                          if ins_c == YES and unit_c == AREA else [70]):
                                for sco_lvl_c in ([NONE] +
                                                  list(range(lvl_c, 86, 5))
                                                  if ins_c == YES and unit_c == ENT
                                                  and prog_c == PLC else [NONE]):
                                    for eco_lvl_c in ([NONE, 90, 95] if ins_c == YES
                                                      and unit_c == ENT else [NONE]):
                                        choice1(prog_c, prog_s, prog_w, ins_c,
                                                unit_c, prot_c, lvl_c, sco_lvl_c,
                                                eco_lvl_c, choices)
    return choices


def make_scenarios(nbest=10):
    """
    Construct all 500,000 choices and put them in a list.
    Iterate through the 88 scenarios of price and yield factor,
    evaluating each choice.  Print the top nbest choices for each scenario
    """
    print(f"Starting at {datetime.now()}")
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
        print(f'Evaluating scenario {i+1}: pf={s.pf}, yf={s.yf}.')
        s.evaluate_choices()
        for j, (idx, val) in enumerate(s.results[:nbest]):
            ch = s.choices[idx]
            linestr = rowformat.format(
                i+1, s.pf, s.yf, val, PROG[ch.prog_c], PROG[ch.prog_s],
                PROG[ch.prog_w], INS[ch.ins_c], UNIT[ch.unit_c],
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
