import subprocess
import sys
from pathlib import Path


MINIMAL_PDF_BYTES = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 24 Tf 50 50 Td (Hello from Sparse PDF) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000062 00000 n 
0000000119 00000 n 
0000000207 00000 n 
0000000307 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF
"""


def test_minimal_script_extracts_expected_text(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(MINIMAL_PDF_BYTES)

    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "pdf_parse_script.py"

    result = subprocess.run(
        [sys.executable, str(script_path), str(pdf_path)],
        capture_output=True,
        text=True,
        check=True,
        cwd=repo_root,
    )

    assert result.stdout.strip() == "Hello from Sparse PDF"
