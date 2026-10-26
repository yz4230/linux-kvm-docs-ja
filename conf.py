# Sphinx configuration for the Japanese translation of Linux KVM documentation.
project = 'KVM ドキュメント（日本語訳）'
copyright = ''
author = 'Linux カーネル Documentation/virt/kvm の日本語訳'
release = ''
version = ''

extensions = []

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'venv', '.venv']

language = 'ja'
locale_dirs = ['locale']
gettext_compact = False

master_doc = 'index'
root_doc = 'index'

# 原文は他のカーネルドキュメントを参照する :ref: を含むため、
# 未解決ラベルと外部リンク切れの警告は抑制する。
suppress_warnings = ['ref.ref', 'ref.label', 'ref.any', 'docutils']
nitpicky = False

html_theme = 'sphinx_rtd_theme'
html_title = 'KVM ドキュメント（日本語訳）'
html_short_title = 'KVM 日本語訳'
html_static_path = ['_static']
html_show_sourcelink = False
html_show_sphinx = False
html_copy_source = False
html_search_language = 'ja'
htmlhelp_basename = 'KVMja'

html_theme_options = {
    'navigation_depth': 3,
    'collapse_navigation': False,
    'titles_only': False,
    'prev_next_buttons_location': 'both',
}

rst_prolog = ''
rst_epilog = ''
