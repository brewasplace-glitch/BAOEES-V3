import importlib
import unittest


mod = importlib.import_module("phoenix.autonomy.autonomous_calculix_results_v8_4")


class TestPhoenixAutonomousCalculixSupportSetWrappingV84R6(unittest.TestCase):
    def test_34_support_tags_wrap_to_16_16_2(self):
        lines = mod._calculix_set_data_lines(
            [1, 2, 3, 5, 6, 7, 9, 11, 13, 15, 17, 18, 19, 21, 23, 25,
             27, 29, 31, 32, 33, 35, 36, 38, 41, 44, 46, 48, 50, 52, 54, 56,
             58, 61]
        )
        self.assertEqual([len(line.split(",")) for line in lines], [16, 16, 2])

    def test_support_tag_order_is_preserved(self):
        values = [61, 2, 49, 5, 17, 3, 22, 11, 8, 7, 91, 15, 4, 6, 1, 30, 31]
        lines = mod._calculix_set_data_lines(values)
        flattened = [
            int(part.strip())
            for line in lines
            for part in line.split(",")
            if part.strip()
        ]
        self.assertEqual(flattened, values)

    def test_instrument_deck_wraps_support_set(self):
        base = (
            "*HEADING\n"
            "PHOENIX R6 TEST\n"
            "*NODE\n"
            "1, 0, 0, 0\n"
            "*ELEMENT, TYPE=B31, ELSET=E_M1\n"
            "1, 1, 1\n"
            "*STEP\n"
            "*STATIC\n"
            "*END STEP\n"
        )
        tags = list(range(1, 35))
        deck = mod._instrument_deck(base, support_tags=tags, element_ids=["M1"])
        rows = deck.splitlines()
        idx = rows.index("*NSET, NSET=PHX_SUPPORT_NODES")
        support_rows = rows[idx + 1:idx + 4]
        self.assertEqual([len(row.split(",")) for row in support_rows], [16, 16, 2])
        mod._validate_calculix_set_card_width(deck)

    def test_validator_rejects_wide_nset(self):
        bad = (
            "*NSET, NSET=BAD\n"
            + ", ".join(str(i) for i in range(1, 18))
            + "\n*STEP\n"
        )
        with self.assertRaisesRegex(
            mod.AutonomousCalculixBlocked,
            "CalculiX set-dataregel",
        ):
            mod._validate_calculix_set_card_width(bad)

    def test_validator_rejects_wide_elset(self):
        bad = (
            "*ELSET, ELSET=BAD\n"
            + ", ".join(str(i) for i in range(1, 19))
            + "\n*STEP\n"
        )
        with self.assertRaises(mod.AutonomousCalculixBlocked):
            mod._validate_calculix_set_card_width(bad)

    def test_validator_ignores_non_set_data_rows(self):
        text = (
            "*NODE\n"
            + ", ".join(str(i) for i in range(1, 30))
            + "\n*STEP\n"
        )
        mod._validate_calculix_set_card_width(text)


if __name__ == "__main__":
    unittest.main()