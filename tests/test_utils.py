from unittest import TestCase
from imu_api.utils import clean_broken_json_text


class ImuUtilsTests(TestCase):
    def test_clean_broken_json_text_handles_new_line_breaking_strings(self):
        test_input = '{\r\n\t"test" : {\r\n\t\t"AcqCreditLine" : "Private collection\ncourtesy the artist and "\r\n\t}\r\n}\r\n'
        expected = '{\r\n\t"test" : {\r\n\t\t"AcqCreditLine" : "Private collection\\ncourtesy the artist and "\r\n\t}\r\n}\r\n'
        self.assertEqual(clean_broken_json_text(test_input), expected)

    def test_clean_broken_json_text_handles_1_quotation_mark_within_strings(self):
        test_input = '{\r\n\t"test" : {\r\n\t\t"AcqCreditLine" : "Private \\"collection courtesy the artist and "\r\n\t}\r\n}\r\n'
        self.assertEqual(clean_broken_json_text(test_input), test_input)

    def test_clean_broken_json_text_handles_2_quotation_marks_within_strings(self):
        test_input = '{\r\n\t"test" : {\r\n\t\t"AcqCreditLine" : "Private \\"collection\\" courtesy the artist and "\r\n\t}\r\n}\r\n'
        self.assertEqual(clean_broken_json_text(test_input), test_input)

    def test_clean_broken_json_text_handles_3_quotation_marks_within_strings(self):
        test_input = '{\r\n\t"test" : {\r\n\t\t"AcqCreditLine" : "Private \\"colle\\"ction\\" courtesy the artist and "\r\n\t}\r\n}\r\n'
        self.assertEqual(clean_broken_json_text(test_input), test_input)

    def test_clean_broken_json_does_not_mangle_newlines_after_escaped_quotation_marks(
        self
    ):
        test_input = '{\r\n\t"PhyMedium" : "3/4\\" V-matic, colour 38 mins",\r\n}\r\n'
        self.assertEqual(clean_broken_json_text(test_input), test_input)

    def test_clean_broken_json_text_handles_escaped_new_lines_in_strings(self):
        test_input = '{\r\n\t"test" : {\r\n\t\t"AcqCreditLine" : "Private collection\\ncourtesy the artist and "\r\n\t}\r\n}\r\n'
        self.assertEqual(clean_broken_json_text(test_input), test_input)

    def test_handles_escaped_backslashes_in_strings(self):
        test_input = '{\r\n\t"MulTitle" : "Sydney from Parramarra Road\\\\"\r\n}\r\n'
        self.assertEqual(clean_broken_json_text(test_input), test_input)

    def test_escapes_tabs_and_newlines(self):
        test_input = '{"TitTitleNotes" : "The Falls of Niagara\t\t\t\t\nScenery on the Lower Amazon\t\t\t\nThe Pampas\t\t\t\t\t"}'
        expected = '{"TitTitleNotes" : "The Falls of Niagara\\t\\t\\t\\t\\nScenery on the Lower Amazon\\t\\t\\t\\nThe Pampas\\t\\t\\t\\t\\t"}'
        self.assertEqual(clean_broken_json_text(test_input), expected)

    def test_handles_standard_newlines(self):
        test_input = '{"test1": "test1",\n\t"test2": "test2"\n}'
        self.assertEqual(clean_broken_json_text(test_input), test_input)

    def test_handles_escaped_quotations_that_resemble_string_separators(self):
        # The escaped quotation mark followed by ` :` was breaking our detection of when we are within a string
        test_input = '{"SummaryData" : "Enzo Cucchi, \\"La disegna\\" : Zeichnungen 1975 bis 1988.",\r\n}'
        self.assertEqual(clean_broken_json_text(test_input), test_input)
