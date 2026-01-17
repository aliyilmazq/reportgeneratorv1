"""
Rules modülü - Rapor üretim kurallarını yönetir.

KULLANIM:
    Uygulama başlangıcında kurallar yüklenir ve bellekte tutulur.
    Diğer modüller get_global_rules() ile kurallara erişebilir.

    from src.rules import get_global_rules, rules_are_loaded

    if rules_are_loaded():
        rules = get_global_rules()
        print(rules.min_words_per_section)
"""

from .rules_loader import (
    RulesLoader,
    RuleFile,
    RuleSection,
    LoadedRules,
    RulesLoadError,
    get_rules_loader,
    ensure_rules_loaded,
    # Global kural erişimi
    set_global_rules,
    get_global_rules,
    rules_are_loaded,
    get_rules_summary,
    get_rules_for_claude
)

__all__ = [
    'RulesLoader',
    'RuleFile',
    'RuleSection',
    'LoadedRules',
    'RulesLoadError',
    'get_rules_loader',
    'ensure_rules_loaded',
    # Global kural erişimi
    'set_global_rules',
    'get_global_rules',
    'rules_are_loaded',
    'get_rules_summary',
    'get_rules_for_claude'
]
