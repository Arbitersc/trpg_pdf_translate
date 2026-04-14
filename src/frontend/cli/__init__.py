"""
TRPG PDF Translator CLI Module

This module provides the command-line interface for the TRPG PDF Translator.
"""

from .main import main
from .interactive import show_main_menu
from .workflow import WorkflowManager
from .config import ConfigManager

__all__ = ['main', 'show_main_menu', 'WorkflowManager', 'ConfigManager']