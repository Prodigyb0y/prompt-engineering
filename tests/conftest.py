import os
import sys
from pathlib import Path

# Os testes sempre rodam sobre a v1 (padrão), mesmo que PE_VERSAO esteja definida no terminal.
os.environ.pop("PE_VERSAO", None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
