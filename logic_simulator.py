"""
PJBL-1: Simulator Tabel Kebenaran & Verifikator Argumen
Arsitektur:
1. Lexer (Tokenizer) -> Memecah string menjadi token valid & normalisasi simbol.
2. Parser (Shunting-Yard Algorithm) -> Mengubah Infix menjadi Postfix (RPN) & AST.
3. Evaluator -> Mengekstrak sub-ekspresi, menghitung tabel kebenaran,
                mengklasifikasikan proposisi, dan memverifikasi argumen.
"""

from dataclasses import dataclass
from itertools import product
from typing import List, Dict, Tuple, Set


# ==========================================
# 1. DEFINISI TOKEN & OPERATOR
# ==========================================
@dataclass
class OperatorInfo:
    symbol: str
    precedence: int
    arity: int          # 1 = unary (~), 2 = binary (&, |, ^, ->, <->)
    associativity: str  # 'L' (Left) atau 'R' (Right)


OPERATORS: Dict[str, OperatorInfo] = {
    "~":   OperatorInfo("~",   5, 1, "R"),  # Negasi (NOT)
    "&":   OperatorInfo("&",   4, 2, "L"),  # Konjungsi (AND)
    "|":   OperatorInfo("|",   3, 2, "L"),  # Disjungsi (OR)
    "⊕":   OperatorInfo("⊕",   2, 2, "L"),  # Exclusive OR (XOR)
    "->":  OperatorInfo("->",  1, 2, "R"),  # Implikasi (IF-THEN)
    "<->": OperatorInfo("<->", 0, 2, "L"),  # Biimplikasi (IFF)
}


@dataclass
class ASTNode:
    token: str
    left: 'ASTNode | None' = None
    right: 'ASTNode | None' = None

    def to_infix(self) -> str:
        """Merekonstruksi ekspresi string standar untuk label kolom sub-ekspresi."""
        if self.left is None and self.right is None:
            return self.token
        if self.token == "~":
            inner = self.right.to_infix()
            if self.right.left is not None:
                return f"~({inner})"
            return f"~{inner}"
        left_str = self.left.to_infix()
        right_str = self.right.to_infix()
        if self.left.left is not None and OPERATORS[self.left.token].precedence < OPERATORS[self.token].precedence:
            left_str = f"({left_str})"
        if self.right.left is not None and OPERATORS[self.right.token].precedence <= OPERATORS[self.token].precedence:
            right_str = f"({right_str})"
        return f"{left_str} {self.token} {right_str}"


# ==========================================
# 2. LEXICAL ANALYZER (TOKENIZER)
# ==========================================
class LogicLexer:
    """Mengubah string input mentah menjadi daftar token standar."""

    @staticmethod
    def tokenize(expression: str) -> List[str]:
        expr = expression.strip()
        if not expr:
            raise ValueError("Ekspresi tidak boleh kosong.")

        # Normalisasi kata kunci ke simbol kanonik
        replacements = [
            ("<=>", "<->"), ("↔", "<->"),
            ("=>", "->"),   ("→", "->"),
            ("XOR", "⊕"),   ("xor", "⊕"),
            ("AND", "&"),   ("and", "&"), ("^", "&"), ("∧", "&"),
            ("OR", "|"),    ("or", "|"),  ("∨", "|"),
            ("NOT", "~"),   ("not", "~"), ("!", "~"), ("¬", "~"),
        ]
        for old, new in replacements:
            expr = expr.replace(old, f" {new} ")

        tokens: List[str] = []
        i = 0
        n = len(expr)

        while i < n:
            ch = expr[i]
            if ch.isspace():
                i += 1
                continue
            if expr.startswith("<->", i):
                tokens.append("<->")
                i += 3
            elif expr.startswith("->", i):
                tokens.append("->")
                i += 2
            elif ch in ("(", ")", "~", "&", "|", "⊕"):
                tokens.append(ch)
                i += 1
            elif ch.isalpha():
                # Tangani huruf 'v' sebagai operator OR jika berada di posisi operator biner
                if ch in ("v", "V") and tokens and (tokens[-1] == ")" or tokens[-1].isalpha()):
                    tokens.append("|")
                    i += 1
                else:
                    var_name = []
                    while i < n and (expr[i].isalnum() or expr[i] == "_"):
                        var_name.append(expr[i])
                        i += 1
                    tokens.append("".join(var_name).lower())
            else:
                raise ValueError(f"Karakter tidak dikenal pada posisi {i}: '{ch}'")

        LogicLexer._validate_syntax(tokens)
        return tokens

    @staticmethod
    def _validate_syntax(tokens: List[str]) -> None:
        balance = 0
        prev_type = "START"  # START, VAR, OP_UNARY, OP_BINARY, LPAREN, RPAREN

        for idx, tok in enumerate(tokens):
            if tok == "(":
                if prev_type in ("VAR", "RPAREN"):
                    raise ValueError(f"Sintaks tidak valid sebelum '(' pada token ke-{idx + 1}.")
                balance += 1
                prev_type = "LPAREN"
            elif tok == ")":
                if prev_type in ("OP_UNARY", "OP_BINARY", "LPAREN", "START"):
                    raise ValueError(f"Tanda kurung tutup ')' tidak valid pada token ke-{idx + 1}.")
                balance -= 1
                if balance < 0:
                    raise ValueError("Kurung tutup ')' berlebih tanpa pasangan '('.")
                prev_type = "RPAREN"
            elif tok == "~":
                if prev_type in ("VAR", "RPAREN"):
                    raise ValueError(f"Operator negasi '~' tidak bisa langsung setelah proposisi pada token ke-{idx + 1}.")
                prev_type = "OP_UNARY"
            elif tok in OPERATORS:
                if prev_type in ("START", "OP_UNARY", "OP_BINARY", "LPAREN"):
                    raise ValueError(f"Operator biner '{tok}' kehilangan operan kiri pada token ke-{idx + 1}.")
                prev_type = "OP_BINARY"
            else:
                if prev_type in ("VAR", "RPAREN"):
                    raise ValueError(f"Dua proposisi berurutan tanpa operator pada '{tok}'.")
                prev_type = "VAR"

        if balance != 0:
            raise ValueError("Tanda kurung '(' dan ')' tidak seimbang.")
        if prev_type in ("OP_UNARY", "OP_BINARY"):
            raise ValueError("Ekspresi berakhir secara menggantung pada sebuah operator.")


# ==========================================
# 3. SHUNTING-YARD PARSER & AST BUILDER
# ==========================================
class LogicParser:
    """Mengonversi token Infix ke Postfix (RPN) dan membangun pohon sintaks (AST)."""

    @staticmethod
    def to_postfix(tokens: List[str]) -> List[str]:
        output: List[str] = []
        op_stack: List[str] = []

        for tok in tokens:
            if tok == "(":
                op_stack.append(tok)
            elif tok == ")":
                while op_stack and op_stack[-1] != "(":
                    output.append(op_stack.pop())
                op_stack.pop()  # Buang '('
            elif tok in OPERATORS:
                cur_op = OPERATORS[tok]
                while op_stack and op_stack[-1] in OPERATORS:
                    top_op = OPERATORS[op_stack[-1]]
                    if (cur_op.associativity == "L" and cur_op.precedence <= top_op.precedence) or \
                       (cur_op.associativity == "R" and cur_op.precedence < top_op.precedence):
                        output.append(op_stack.pop())
                    else:
                        break
                op_stack.append(tok)
            else:
                output.append(tok)

        while op_stack:
            output.append(op_stack.pop())

        return output

    @staticmethod
    def build_ast_and_subexpressions(postfix: List[str]) -> Tuple[ASTNode, List[Tuple[str, ASTNode]]]:
        """Membangun AST sekaligus mencatat urutan sub-ekspresi untuk kolom tabel kebenaran."""
        stack: List[ASTNode] = []
        subexpressions: List[Tuple[str, ASTNode]] = []
        seen_labels: Set[str] = set()

        for tok in postfix:
            if tok not in OPERATORS:
                stack.append(ASTNode(tok))
            elif OPERATORS[tok].arity == 1:
                operand = stack.pop()
                node = ASTNode(tok, right=operand)
                label = node.to_infix()
                if label not in seen_labels:
                    seen_labels.add(label)
                    subexpressions.append((label, node))
                stack.append(node)
            else:
                right = stack.pop()
                left = stack.pop()
                node = ASTNode(tok, left=left, right=right)
                label = node.to_infix()
                if label not in seen_labels:
                    seen_labels.add(label)
                    subexpressions.append((label, node))
                stack.append(node)

        return stack[0], subexpressions


# ==========================================
# 4. EVALUATOR & VERIFIKATOR ARGUMEN
# ==========================================
class LogicEvaluator:
    """Mengevaluasi nilai kebenaran AST dan memverifikasi argumen."""

    @staticmethod
    def eval_node(node: ASTNode, env: Dict[str, bool]) -> bool:
        if node.left is None and node.right is None:
            if node.token in ("t", "true", "1"):
                return True
            if node.token in ("f", "false", "0"):
                return False
            return env[node.token]

        if node.token == "~":
            return not LogicEvaluator.eval_node(node.right, env)

        l_val = LogicEvaluator.eval_node(node.left, env)
        r_val = LogicEvaluator.eval_node(node.right, env)

        if node.token == "&":
            return l_val and r_val
        if node.token == "|":
            return l_val or r_val
        if node.token == "⊕":
            return l_val != r_val
        if node.token == "->":
            return (not l_val) or r_val
        if node.token == "<->":
            return l_val == r_val
        raise ValueError(f"Operator tidak dikenal: {node.token}")

    @staticmethod
    def extract_variables(tokens: List[str]) -> List[str]:
        reserved = set(OPERATORS.keys()) | {"(", ")", "t", "f", "true", "false", "1", "0"}
        vars_found = sorted({tok for tok in tokens if tok not in reserved})
        return vars_found

    @staticmethod
    def generate_truth_table(expression: str) -> Dict:
        tokens = LogicLexer.tokenize(expression)
        postfix = LogicParser.to_postfix(tokens)
        root, subexprs = LogicParser.build_ast_and_subexpressions(postfix)
        variables = LogicEvaluator.extract_variables(tokens)

        headers = variables + [label for label, _ in subexprs]
        if not subexprs and root.to_infix() not in headers:
            headers.append(root.to_infix())

        rows = []
        final_values = []

        # Urutan standar akademis: True (B) ke False (S)
        for combo in product([True, False], repeat=len(variables)):
            env = dict(zip(variables, combo))
            row_vals = [env[v] for v in variables]
            for _, sub_node in subexprs:
                row_vals.append(LogicEvaluator.eval_node(sub_node, env))

            final_val = row_vals[-1] if subexprs else LogicEvaluator.eval_node(root, env)
            final_values.append(final_val)
            rows.append(row_vals)

        if all(final_values):
            classification = "TAUTOLOGI (Selalu Benar pada setiap interpretasi)"
        elif not any(final_values):
            classification = "KONTRADIKSI (Selalu Salah pada setiap interpretasi)"
        else:
            t_count = sum(1 for v in final_values if v)
            f_count = len(final_values) - t_count
            classification = f"KONTINGENSI ({t_count} baris Benar, {f_count} baris Salah)"

        return {
            "tokens": tokens,
            "postfix": postfix,
            "variables": variables,
            "headers": headers,
            "rows": rows,
            "classification": classification,
        }

    @staticmethod
    def verify_argument(premises: List[str], conclusion: str) -> Dict:
        parsed_premises = []
        all_tokens = []

        for p in premises:
            toks = LogicLexer.tokenize(p)
            all_tokens.extend(toks)
            post = LogicParser.to_postfix(toks)
            ast, _ = LogicParser.build_ast_and_subexpressions(post)
            parsed_premises.append((ast.to_infix(), ast))

        c_toks = LogicLexer.tokenize(conclusion)
        all_tokens.extend(c_toks)
        c_post = LogicParser.to_postfix(c_toks)
        c_ast, _ = LogicParser.build_ast_and_subexpressions(c_post)
        c_label = c_ast.to_infix()

        variables = LogicEvaluator.extract_variables(all_tokens)
        headers = variables + [f"P{i+1}: {lbl}" for i, (lbl, _) in enumerate(parsed_premises)] + [f" ∴ {c_label}", "Status Baris"]

        rows = []
        critical_rows = []
        counterexamples = []

        for idx, combo in enumerate(product([True, False], repeat=len(variables)), start=1):
            env = dict(zip(variables, combo))
            p_vals = [LogicEvaluator.eval_node(ast, env) for _, ast in parsed_premises]
            c_val = LogicEvaluator.eval_node(c_ast, env)

            all_premises_true = all(p_vals)
            if all_premises_true and c_val:
                status = "KRITIS (Valid)"
                critical_rows.append(idx)
            elif all_premises_true and not c_val:
                status = "COUNTEREXAMPLE!"
                critical_rows.append(idx)
                counterexamples.append((idx, env))
            else:
                status = "-"

            rows.append([env[v] for v in variables] + p_vals + [c_val, status])

        is_valid = len(counterexamples) == 0
        return {
            "variables": variables,
            "headers": headers,
            "rows": rows,
            "is_valid": is_valid,
            "critical_rows": critical_rows,
            "counterexamples": counterexamples,
        }


# ==========================================
# 5. RENDERER TABEL UNICODE & CLI
# ==========================================
def format_bool(val) -> str:
    if isinstance(val, bool):
        return "B (T)" if val else "S (F)"
    return str(val)


def print_unicode_table(headers: List[str], rows: List[List]) -> None:
    str_rows = [[format_bool(cell) for cell in row] for row in rows]
    col_widths = [
        max(len(headers[i]), max((len(r[i]) for r in str_rows), default=0)) + 2
        for i in range(len(headers))
    ]

    def border(left: str, mid: str, right: str) -> str:
        return left + mid.join("─" * w for w in col_widths) + right

    print(border("┌", "┬", "┐"))
    header_line = "│" + "│".join(headers[i].center(col_widths[i]) for i in range(len(headers))) + "│"
    print(header_line)
    print(border("├", "┼", "┤"))
    for r in str_rows:
        print("│" + "│".join(r[i].center(col_widths[i]) for i in range(len(headers))) + "│")
    print(border("└", "┴", "┘"))


def run_demo():
    print("=" * 72)
    print("  SIMULATOR TABEL KEBENARAN & VERIFIKATOR ARGUMEN (PJBL-1)")
    print("=" * 72)

    # Demo 1: Simulator Tabel Kebenaran & Klasifikasi
    sample_expr = "((p -> q) & (q -> r)) -> (p -> r)"
    print(f"\n[UJI 1] Ekspresi Proposisi : {sample_expr}")
    res = LogicEvaluator.generate_truth_table(sample_expr)
    print(f"Token Infix                : {' '.join(res['tokens'])}")
    print(f"Notasi Postfix (RPN)       : {' '.join(res['postfix'])}")
    print_unicode_table(res["headers"], res["rows"])
    print(f"Hasil Klasifikasi          : {res['classification']}")

    # Demo 2: Verifikasi Argumen Valid (Modus Tollens)
    print("\n" + "=" * 72)
    print("[UJI 2] Verifikasi Argumen #1 (Modus Tollens)")
    premises_1 = ["p -> q", "~q"]
    conclusion_1 = "~p"
    print(f"Premis 1 : {premises_1[0]}  |  Premis 2 : {premises_1[1]}  |  Konklusi : ∴ {conclusion_1}")
    arg_res1 = LogicEvaluator.verify_argument(premises_1, conclusion_1)
    print_unicode_table(arg_res1["headers"], arg_res1["rows"])
    print(f"Baris Kritis               : Baris ke-{arg_res1['critical_rows']}")
    print(f"Kesimpulan Validitas       : {'VALID (Sah)' if arg_res1['is_valid'] else 'INVALID (Sesat Pikir)'}")

    # Demo 3: Verifikasi Argumen Invalid (Fallacy of Affirming the Consequent)
    print("\n" + "=" * 72)
    print("[UJI 3] Verifikasi Argumen #2 (Affirming the Consequent / Fallacy)")
    premises_2 = ["p -> q", "q"]
    conclusion_2 = "p"
    print(f"Premis 1 : {premises_2[0]}  |  Premis 2 : {premises_2[1]}  |  Konklusi : ∴ {conclusion_2}")
    arg_res2 = LogicEvaluator.verify_argument(premises_2, conclusion_2)
    print_unicode_table(arg_res2["headers"], arg_res2["rows"])
    print(f"Kesimpulan Validitas       : {'VALID (Sah)' if arg_res2['is_valid'] else 'INVALID (Tidak Sah / Fallacy)'}")
    for row_idx, env in arg_res2["counterexamples"]:
        env_str = ", ".join(f"{k}={'Benar' if v else 'Salah'}" for k, v in env.items())
        print(f"Bukti Penyangkal           : Baris ke-{row_idx} ({env_str}) membuat semua premis Benar tetapi konklusi Salah.")


if __name__ == "__main__":
    run_demo()