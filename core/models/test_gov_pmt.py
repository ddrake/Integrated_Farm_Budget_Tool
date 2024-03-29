from django.test import TestCase

from core.models.gov_pmt import GovPmt


class GovPmtAllPLCMya4_80TestCase(TestCase):
    def setUp(self):
        # Somthing like Grandview corn.
        # For PLC, the only sensitivity is price sensitivity, which comes in via
        self.govpmt = GovPmt(
            plc_base_acres=4220, arcco_base_acres=0, plc_yield=160,
            estimated_county_yield=190, effective_ref_price=3.70,
            natl_loan_rate=2.20, sens_mya_price=4.80, benchmark_revenue=801.09)

    def test_with_default_values(self):
        pmt = self.govpmt.prog_pmt_pre_sequest()
        expected = 0
        self.assertEqual(pmt, expected)


class GovPmtAllPLCMya3_80TestCase(TestCase):
    def setUp(self):
        # Somthing like Grandview corn.  Note sens_mya_price.
        self.govpmt = GovPmt(
            plc_base_acres=4220, arcco_base_acres=0, plc_yield=160,
            estimated_county_yield=190, effective_ref_price=3.70,
            natl_loan_rate=2.20, sens_mya_price=3.80, benchmark_revenue=801.09)

    def test_with_default_values(self):
        pmt = self.govpmt.prog_pmt_pre_sequest()
        expected = 0
        self.assertEqual(pmt, expected)


class GovPmtAllPLCMya3_20TestCase(TestCase):
    def setUp(self):
        # Somthing like Grandview corn.  Note sens_mya_price.
        self.govpmt = GovPmt(
            plc_base_acres=4220, arcco_base_acres=0, plc_yield=160,
            estimated_county_yield=190, effective_ref_price=3.70,
            natl_loan_rate=2.20, sens_mya_price=3.20, benchmark_revenue=801.09)

    def test_with_default_values(self):
        pmt = self.govpmt.prog_pmt_pre_sequest()
        expected = 286960
        self.assertEqual(pmt, expected)


class GovPmtAllPLCMya2_80TestCase(TestCase):
    def setUp(self):
        # Somthing like Grandview corn.  Note sens_mya_price.
        self.govpmt = GovPmt(
            plc_base_acres=4220, arcco_base_acres=0, plc_yield=160,
            estimated_county_yield=190, effective_ref_price=3.70,
            natl_loan_rate=2.20, sens_mya_price=2.80, benchmark_revenue=801.09)

    def test_with_default_values(self):
        pmt = self.govpmt.prog_pmt_pre_sequest()
        expected = 516528.0
        self.assertEqual(pmt, expected)


class GovPmtAllARCCOTestCase(TestCase):
    def setUp(self):
        # Somthing like Grandview corn
        self.govpmt = GovPmt(
            plc_base_acres=0, arcco_base_acres=4220, plc_yield=160,
            estimated_county_yield=190, effective_ref_price=3.70,
            natl_loan_rate=2.20, sens_mya_price=4.80, benchmark_revenue=801.09)

    def test_with_default_values(self):
        pmt = self.govpmt.prog_pmt_pre_sequest()
        expected = 0
        self.assertEqual(pmt, expected)
