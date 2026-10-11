"""
Unit Testing Otomatis PJBL-1: Simulator Tabel Kebenaran & Verifikator Argumen
Menguji 4 komponen utama sesuai rubrik penilaian:
1. Lexical Analyzer & Validasi Sintaks Error
2. Shunting-Yard Parser (Infix ke Postfix/RPN)
3. Evaluasi Tabel Kebenaran & Klasifikasi (Tautologi, Kontradiksi, Kontingensi)
4. Verifikasi Validitas Argumen & Deteksi Counterexample (Fallacy)
"""

import os
import sys
import unittest

# Menambahkan folder induk (root) ke sys.path agar logic_simulator.py bisa diimpor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic_simulator import LogicLexer, LogicParser, LogicEvaluator


class TestLogicSimulator(unittest.TestCase):

    # ==========================================================
    # 1. PENGUJIAN LEXER & VALIDASI SINTAKS (BOBOT 25%)
    # ==========================================================
    def test_01_lexer_normalization(self):
        """Menguji normalisasi berbagai variasi simbol operator logika."""
        tokens = LogicLexer.tokenize("NOT p AND (q OR r) => (p <=> r)")
        self.assertEqual(tokens, ["~", "p", "&", "(", "q", "|", "r", ")", "->", "(", "p", "<->", "r", ")"])

    def test_02_syntax_error_detection(self):
        """Memastikan ekspresi cacat sintaks ditolak dengan ValueError."""
        invalid_expressions = [
            "",                 # Ekspresi kosong
            "(p -> q",          # Kurung tidak seimbang
            "p & | q",          # Dua operator biner berurutan
            "p q -> r",         # Dua proposisi tanpa operator
            "p ->",             # Berakhir menggantung pada operator
            "p ~ q",            # Negasi di posisi operator biner
        ]
        for expr in invalid_expressions:
            with self.subTest(expr=expr):
                with self.assertRaises(ValueError):
                    LogicLexer.tokenize(expr)

    # ==========================================================
    # 2. PENGUJIAN SHUNTING-YARD PARSER & PRESEDENSI (BOBOT 25%)
    # ==========================================================
    def test_03_shunting_yard_precedence(self):
        """Menguji urutan presedensi: ~ (5) di atas & (4) di atas | (3) di atas -> (1)."""
        tokens = LogicLexer.tokenize("~p & q | r -> s")
        postfix = LogicParser.to_postfix(tokens)
        # Urutan evaluasi yang benar: ((~p & q) | r) -> s
        self.assertEqual(postfix, ["p", "~", "q", "&", "r", "|", "s", "->"])

    def test_04_implication_right_associativity(self):
        """Memastikan implikasi p -> q -> r dievaluasi sebagai p -> (q -> r)."""
        tokens = LogicLexer.tokenize("p -> q -> r")
        postfix = LogicParser.to_postfix(tokens)
        self.assertEqual(postfix, ["p", "q", "r", "->", "->"])

    # ==========================================================
    # 3. PENGUJIAN KLASIFIKASI PROPOSISI (BOBOT 25%)
    # ==========================================================
    def test_05_classification_tautology(self):
        """Menguji Hukum De Morgan dan Silogisme Hipotetis sebagai Tautologi."""
        res1 = LogicEvaluator.generate_truth_table("~(p | q) <-> (~p & ~q)")
        res2 = LogicEvaluator.generate_truth_table("((p -> q) & (q -> r)) -> (p -> r)")
        self.assertTrue(res1["classification"].startswith("TAUTOLOGI"))
        self.assertTrue(res2["classification"].startswith("TAUTOLOGI"))
        self.assertEqual(len(res2["rows"]), 8)  # 3 variabel = 2^3 = 8 baris

    def test_06_classification_contradiction(self):
        """Menguji ekspresi p & ~p sebagai Kontradiksi."""
        res = LogicEvaluator.generate_truth_table("(p & ~p) | (q & ~q)")
        self.assertTrue(res["classification"].startswith("KONTRADIKSI"))

    def test_07_classification_contingency(self):
        """Menguji ekspresi kontingensi dan menghitung jumlah barisnya."""
        res = LogicEvaluator.generate_truth_table("p -> q")
        self.assertTrue(res["classification"].startswith("KONTINGENSI"))
        self.assertIn("3 baris Benar, 1 baris Salah", res["classification"])

    # ==========================================================
    # 4. PENGUJIAN VERIFIKATOR ARGUMEN & FALLACY (BOBOT 25%)
    # ==========================================================
    def test_08_valid_arguments(self):
        """Menguji argumen sah: Modus Ponens, Modus Tollens, dan Silogisme Disjungtif."""
        # Modus Ponens: p -> q, p |- q
        mp = LogicEvaluator.verify_argument(["p -> q", "p"], "q")
        self.assertTrue(mp["is_valid"])
        self.assertEqual(len(mp["counterexamples"]), 0)

        # Modus Tollens: p -> q, ~q |- ~p
        mt = LogicEvaluator.verify_argument(["p -> q", "~q"], "~p")
        self.assertTrue(mt["is_valid"])
        self.assertEqual(mt["critical_rows"], [4])  # Baris ke-4 (p=False, q=False)

        # Silogisme Disjungtif: p | q, ~p |- q
        ds = LogicEvaluator.verify_argument(["p | q", "~p"], "q")
        self.assertTrue(ds["is_valid"])

    def test_09_invalid_arguments_fallacy(self):
        """Menguji deteksi Counterexample pada argumen sesat pikir (Fallacy)."""
        # Affirming the Consequent: p -> q, q |- p (Penyangkal: p=False, q=True)
        ac = LogicEvaluator.verify_argument(["p -> q", "q"], "p")
        self.assertFalse(ac["is_valid"])
        self.assertEqual(len(ac["counterexamples"]), 1)
        row_idx, env = ac["counterexamples"][0]
        self.assertEqual(row_idx, 3)
        self.assertEqual(env, {"p": False, "q": True})

        # Denying the Antecedent: p -> q, ~p |- ~q (Penyangkal: p=False, q=True)
        da = LogicEvaluator.verify_argument(["p -> q", "~p"], "~q")
        self.assertFalse(da["is_valid"])
        self.assertEqual(len(da["counterexamples"]), 1)


if __name__ == "__main__":
    print("=" * 70)
    print("  MENJALANKAN AUTOMATED UNIT TEST SUITE — PJBL-1 LOGIC SIMULATOR")
    print("=" * 70)
    unittest.main(verbosity=2)