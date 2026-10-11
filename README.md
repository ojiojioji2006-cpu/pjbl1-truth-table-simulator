# Simulator Tabel Kebenaran & Verifikator Argumen (PJBL-1)

Aplikasi kompilator dan simulator logika proposisional berbasis **Shunting-Yard Algorithm** dan **Abstract Syntax Tree (AST)** untuk membangkitkan tabel kebenaran lengkap beserta sub-ekspresi, mengklasifikasikan proposisi, serta memverifikasi keabsahan argumen deduktif.

---

## Informasi Kelompok

* **Nama Kelompok:** [Isi Nama Kelompok]
* **Mata Kuliah:** Logika Matematika / Matematika Diskrit (PJBL-1)
* **Anggota Kelompok:**
1. Hasdan Fauji – 25210060
2. Riski Maulana – 25210051
3. Intan Farida – 25210212

---

## Fitur Utama

1. **Multi-Syntax Lexical Tokenizer:** Mendukung berbagai variasi penulisan simbol logika (`~`, `!`, `NOT`, `&`, `^`, `AND`, `|`, `v`, `OR`, `⊕`, `XOR`, `->`, `=>`, `<->`, `<=>`) beserta validasi kesalahan sintaks secara *real-time*.
2. **Ekstraksi Sub-Ekspresi Otomatis:** Membangun *Abstract Syntax Tree (AST)* dari notasi *Reverse Polish Notation (RPN)* untuk menampilkan kolom tahapan penyelesaian di dalam tabel kebenaran.
3. **Klasifikasi Proposisi Otomatis:** Mengidentifikasi hasil evaluasi akhir sebagai **Tautologi**, **Kontradiksi**, atau **Kontingensi**.
4. **Verifikator Argumen & Detektor Counterexample:** Mengevaluasi daftar premis $P_1, P_2, \dots, P_n$ dan konklusi $\therefore C$, menyorot **Baris Kritis**, serta menampilkan bukti penyangkal (*Counterexample*) jika argumen bersifat *Fallacy*.

---

## Arsitektur Sistem

Sistem dirancang menggunakan arsitektur kompilasi 4 tahap tanpa menggunakan fungsi `eval()` bawaan bahasa pemrograman:

```text
[Input String]
      │
      ▼
┌──────────────────────────────┐
│ 1. LogicLexer (Tokenizer)    │ ──► Normalisasi simbol & validasi sintaks kurung/operator
└──────────────┬───────────────┘
               │  Infix Tokens: ['(', 'p', '->', 'q', ')', '&', 'p']
               ▼
┌──────────────────────────────┐
│ 2. LogicParser (Shunting-Yard│ ──► Konversi Infix ke Postfix (RPN) sesuai presedensi
└──────────────┬───────────────┘
               │  Postfix RPN : ['p', 'q', '->', 'p', '&']
               ▼
┌──────────────────────────────┐
│ 3. AST & Sub-Expr Builder    │ ──► Konstruksi pohon sintaks & ekstraksi kolom perantara
└──────────────┬───────────────┘
               │  AST Root + Sub-expressions
               ▼
┌──────────────────────────────┐
│ 4. LogicEvaluator            │ ──► Evaluasi 2^n kombinasi, Klasifikasi, & Baris Kritis
└──────────────────────────────┘
```

### Tabel Presedensi Operator

| Operator | Nama Logika | Simbol Alternatif yang Didukung | Presedensi | Asosiatif | Arity |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `~` | Negasi (NOT) | `!`, `¬`, `NOT`, `not` | 5 (Tertinggi) | Kanan (`R`) | Uner (1) |
| `&` | Konjungsi (AND) | `^`, `∧`, `AND`, `and` | 4 | Kiri (`L`) | Biner (2) |
| `\|` | Disjungsi (OR) | `v`, `∨`, `OR`, `or` | 3 | Kiri (`L`) | Biner (2) |
| `⊕` | Exclusive OR (XOR) | `XOR`, `xor` | 2 | Kiri (`L`) | Biner (2) |
| `->` | Implikasi | `=>`, `→` | 1 | Kanan (`R`) | Biner (2) |
| `<->` | Biimplikasi | `<=>`, `↔` | 0 (Terendah) | Kiri (`L`) | Biner (2) |

---

## Struktur Repository

```text
pjbl1-truth-table-simulator/
├── README.md               # Dokumentasi arsitektur dan panduan penggunaan
├── logic_simulator.py      # Engine utama Python + CLI Tabel Unicode
├── index.html              # Aplikasi Web Interaktif (Single-File HTML/CSS/JS)
└── tests/
    └── test_cases.py       # Unit testing otomatis untuk validasi parser & evaluator
```

---

## Cara Menjalankan Aplikasi

### 1. Menjalankan Versi Web Interaktif (GUI)
Tidak memerlukan instalasi *library* atau *server* tambahan:
1. Unduh atau *clone* repository ini:
   ```bash
   git clone [https://github.com/USERNAME_ANDA/pjbl1-truth-table-simulator.git](https://github.com/USERNAME_ANDA/pjbl1-truth-table-simulator.git)
   ```
2. Buka file `index.html` langsung menggunakan browser modern (Chrome, Firefox, Edge, Safari).

### 2. Menjalankan Versi Python (CLI)
Pastikan Anda memiliki **Python 3.8+** terinstal di komputer Anda:
```bash
python logic_simulator.py
```

### 3. Mengimpor sebagai Modul di Skrip Python Lain
Anda juga dapat memanggil fungsi evaluator secara langsung melalui Python:
```python
from logic_simulator import LogicEvaluator, print_unicode_table

# 1. Uji Tabel Kebenaran
hasil = LogicEvaluator.generate_truth_table("~(p | q) <-> (~p & ~q)")
print_unicode_table(hasil["headers"], hasil["rows"])
print("Klasifikasi:", hasil["classification"])

# 2. Uji Validitas Argumen
argumen = LogicEvaluator.verify_argument(["p -> q", "~q"], "~p")
print_unicode_table(argumen["headers"], argumen["rows"])
print("Valid:", argumen["is_valid"])
```

---

## Lisensi
Proyek ini dikembangkan untuk memenuhi Tugas Proyek Mini #1 (PJBL-1) Mata Kuliah Logika Matematika / Matematika Diskrit.
