"""
Tipos e aliases para o sistema de importação flexível.

Define estruturas de dados compartilhadas entre services de importação.
"""

from typing import Dict, Any, TypeAlias

# Type alias para o preview de importação
# Representa a estrutura completa do preview enviado ao frontend
PreviewImportacao: TypeAlias = Dict[str, Any]
