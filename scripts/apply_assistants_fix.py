#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_assistants_fix.py
- Inserta _get_assistants_api(self) si no existe.
- Reemplaza self.client.beta.assistants(.|) y self.client.assistants(.|)
  por self._get_assistants_api()(.|) preservando el punto si existe.
Idempotente: hace backup la primera vez.
"""
from pathlib import Path
import re
import sys

FILE = Path("deploy_gpt_assistant.py")
if not FILE.exists():
    print("ERROR: deploy_gpt_assistant.py no encontrado en la raíz del repo.", file=sys.stderr)
    sys.exit(2)

text = FILE.read_text(encoding="utf-8")

# 1) Insertar helper si no existe
if "_get_assistants_api" in text:
    print("Helper _get_assistants_api ya presente; no se insertará de nuevo.")
    helper_inserted = False
else:
    helper = '''
    # EXPORT_SEAL
    def _get_assistants_api(self):
        """
        Compat layer for OpenAI assistants API:
        - prefer: self.client.beta.assistants
        - fallback: self.client.assistants
        Raises AttributeError if none available with a helpful message.
        """
        beta = getattr(self.client, "beta", None)
        if beta is not None:
            a = getattr(beta, "assistants", None) or getattr(beta, "assistant", None)
            if a is not None:
                return a

        a = getattr(self.client, "assistants", None) or getattr(self.client, "assistant", None)
        if a is not None:
            return a

        raise AttributeError(
            "OpenAI client does not expose an assistants API (tried beta.assistants and assistants). "
            "Please upgrade the openai Python package in this environment (e.g. `pip install --upgrade openai`) "
            "or verify which OpenAI client you are using."
        )
'''
    # Intentar insertar en un lugar lógico: después de _get_vector_stores_api si existe,
    # sino antes create_or_update_vector_store, sino al final de la clase.
    insert_pos = None
    m_vec = re.search(r"def\s+_get_vector_stores_api\s*\(", text)
    if m_vec:
        # buscar la siguiente definición de función/top-level def después de _get_vector_stores_api
        rest = text[m_vec.end():]
        m_next = re.search(r"\n\n\s*def\s+\w+\s*\(", rest)
        if m_next:
            insert_pos = m_vec.end() + m_next.start()
        else:
            insert_pos = m_vec.end()
    else:
        m_anchor = re.search(r"\n\s*def\s+create_or_update_vector_store\s*\(", text)
        if m_anchor:
            insert_pos = m_anchor.start()

    if insert_pos is None:
        # fallback: buscar inicio de clase AssistantDeployer y meter después de la docstring
        m_class = re.search(r"class\s+\w+\s*:", text)
        if m_class:
            # insertar tras la primera línea siguiente
            next_nl = text.find("\n", m_class.end())
            insert_pos = next_nl + 1 if next_nl != -1 else len(text)
        else:
            insert_pos = len(text)

    text = text[:insert_pos] + helper + "\n" + text[insert_pos:]
    helper_inserted = True
    print("Inserted _get_assistants_api helper.")

# 2) Reemplazar occurrences de self.client(.beta).assistants[.] -> self._get_assistants_api()[.]
pattern = re.compile(r"(self\.client(?:\.beta)?\.assistants)(\.)?", flags=re.MULTILINE)

def _repl(m):
    base = "self._get_assistants_api()"
    return base + (m.group(2) or "")

new_text, nsub = pattern.subn(_repl, text)
if nsub > 0:
    text = new_text
    print(f"Replaced {nsub} occurrences of self.client(.beta).assistants -> self._get_assistants_api()")
else:
    print("No occurrences de self.client.beta.assistants / self.client.assistants encontradas (o ya reemplazadas).")

# 3) Sanity checks
leftover_beta = re.search(r"beta\.assistants\b", text)
leftover_top = re.search(r"\bself\.client(?:\.beta)?\.assistants\b", text)
if leftover_beta or leftover_top:
    print("WARNING: quedaron coincidencias con 'assistants' que quizá requieren revisión manual.")
    for m in re.finditer(r".{0,40}(self\.client(?:\.beta)?\.assistants.{0,80})", text):
        print("  ...", m.group(1)[:200].replace("\n","\\n"))
        break

# 4) Backup original (primera vez)
bak = FILE.with_suffix(FILE.suffix + ".bak")
if not bak.exists():
    bak.write_text(FILE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Backup creado: {bak}")

# 5) Write out
FILE.write_text(text, encoding="utf-8")
print("deploy_gpt_assistant.py actualizado. Revisa git diff antes de commitear.")
