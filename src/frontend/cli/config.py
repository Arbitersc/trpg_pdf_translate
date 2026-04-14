"""
Configuration Manager for TRPG PDF Translator CLI

This module handles configuration management including API keys, model settings,
and parser options.
"""

import os
import json
import copy
from pathlib import Path
from typing import Dict, Any, Optional
from utils import print_error, print_success, print_warning


class ConfigManager:
    """Manages application configuration and settings."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            config_dir: Directory for configuration files. If None, uses default.
        """
        if config_dir is None:
            # Use ~/.trpg_pdf_translator as default config directory
            self.config_dir = Path.home() / ".trpg_pdf_translator"
        else:
            self.config_dir = Path(config_dir)

        self.config_file = self.config_dir / "config.json"
        self.env_file = self.config_dir / ".env"

        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True, parents=True)

        # Default configuration
        self.default_config = {
            "api": {
                "provider": "siliconflow",
                "base_url": "https://api.siliconflow.cn/v1",
                "model": "Pro/moonshotai/Kimi-K2.5",
                "timeout": 300
            },
            "parser": {
                "type": "mineru",
                "timeout": 300,
                "poll_interval": 5
            },
            "translation": {
                "default_source_language": "English",
                "default_target_language": "中文",
                "window_size": 30,
                "overlap_ratio": 0.5
            },
            "output": {
                "default_format": "markdown",
                "create_backup": True,
                "timestamp_files": True
            }
        }

        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default.

        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)

                # Merge with default config (preserve user settings)
                # Use deep copy of default to prevent mutations
                config = self._merge_configs(copy.deepcopy(self.default_config), loaded_config)
                print_success("配置已加载")
                return config

            except (json.JSONDecodeError, IOError) as e:
                print_error(f"配置加载失败: {e}")
                print("使用默认配置...")
                return copy.deepcopy(self.default_config)
        else:
            print("配置文件不存在，使用默认配置")
            return copy.deepcopy(self.default_config)

    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Merge default and user configurations recursively.

        Args:
            default: Default configuration
            user: User configuration

        Returns:
            Dict[str, Any]: Merged configuration
        """
        result = default.copy()

        for key, value in user.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def save_config(self) -> bool:
        """Save current configuration to file.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            print_success("配置已保存")
            return True

        except IOError as e:
            print_error(f"配置保存失败: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.

        Args:
            key: Configuration key (e.g., 'api.model')
            default: Default value if key not found

        Returns:
            Any: Configuration value
        """
        keys = key.split('.')
        current = self.config

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def set(self, key: str, value: Any, auto_save: bool = True) -> bool:
        """Set configuration value.

        Args:
            key: Configuration key (e.g., 'api.model')
            value: Value to set
            auto_save: If True, automatically save configuration after setting

        Returns:
            bool: True if successful, False otherwise
        """
        keys = key.split('.')
        current = self.config

        # Navigate to parent level
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        # Set the value
        current[keys[-1]] = value

        # Auto-save if enabled
        if auto_save:
            self.save_config()

        return True

    def set_api_key(self, provider: str, api_key: str, auto_save: bool = True) -> bool:
        """Set API key for a specific provider.

        Args:
            provider: API provider (e.g., 'siliconflow', 'openai')
            api_key: API key value
            auto_save: If True, automatically save configuration after setting

        Returns:
            bool: True if successful, False otherwise
        """
        # Store in environment file for security
        self._set_env_variable(f"{provider.upper()}_API_KEY", api_key)

        # Also update config (disable auto_save here since we handle .env separately)
        self.set(f"api.{provider}_api_key", "[已设置]", auto_save=False)

        # Auto-save config if enabled
        if auto_save:
            self.save_config()

        print_success(f"{provider} API密钥已设置")
        return True

    def _set_env_variable(self, key: str, value: str, reload_backend: bool = True) -> bool:
        """Set environment variable in .env file.

        Args:
            key: Environment variable name
            value: Environment variable value
            reload_backend: If True, reload backend configuration after setting

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read existing .env file
            env_lines = []
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()

            # Update or add the variable
            variable_found = False
            for i, line in enumerate(env_lines):
                if line.startswith(f"{key}="):
                    env_lines[i] = f"{key}={value}\n"
                    variable_found = True
                    break

            if not variable_found:
                env_lines.append(f"{key}={value}\n")

            # Write back to file
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.writelines(env_lines)

            # Reload backend configuration if requested
            if reload_backend:
                self._reload_backend_config()

            return True

        except IOError as e:
            print_error(f"环境变量设置失败: {e}")
            return False

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider.

        Args:
            provider: API provider

        Returns:
            Optional[str]: API key if found, None otherwise
        """
        # First try environment variable
        env_key = f"{provider.upper()}_API_KEY"
        api_key = os.getenv(env_key)

        if api_key:
            return api_key

        # Then try .env file
        try:
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith(f"{env_key}="):
                            return line.split('=', 1)[1].strip()
        except IOError:
            pass

        return None

    def list_config(self) -> Dict[str, Any]:
        """List all configuration settings.

        Returns:
            Dict[str, Any]: Complete configuration
        """
        return self.config.copy()

    def reset_config(self) -> bool:
        """Reset configuration to defaults.

        Returns:
            bool: True if successful, False otherwise
        """
        self.config = copy.deepcopy(self.default_config)

        # Also remove .env file
        if self.env_file.exists():
            try:
                self.env_file.unlink()
                print_success("环境配置文件已删除")
            except IOError as e:
                print_error(f"环境配置文件删除失败: {e}")

        return self.save_config()

    def validate_config(self) -> Dict[str, Any]:
        """Validate current configuration.

        Returns:
            Dict[str, Any]: Validation results
        """
        validation = {
            "api": {"valid": True, "issues": []},
            "parser": {"valid": True, "issues": []},
            "translation": {"valid": True, "issues": []},
            "output": {"valid": True, "issues": []}
        }

        # Validate API configuration
        api_key = self.get_api_key(self.config["api"]["provider"])
        if not api_key:
            validation["api"]["valid"] = False
            validation["api"]["issues"].append("API密钥未设置")

        # Validate parser configuration
        parser_type = self.config["parser"]["type"]
        if parser_type not in ["mineru", "pdfplumber", "pymupdf"]:
            validation["parser"]["valid"] = False
            validation["parser"]["issues"].append(f"不支持的解析器类型: {parser_type}")

        # Validate translation settings
        window_size = self.config["translation"]["window_size"]
        if not isinstance(window_size, int) or window_size <= 0:
            validation["translation"]["valid"] = False
            validation["translation"]["issues"].append("窗口大小必须为正整数")

        return validation

    def show_config_status(self) -> None:
        """Display current configuration status."""
        print("\n当前配置状态:")
        print("-" * 40)

        # API status
        api_provider = self.get("api.provider", "未设置")
        api_key = self.get_api_key(api_provider)
        api_status = "✅ 已设置" if api_key else "❌ 未设置"
        print(f"API密钥 ({api_provider}): {api_status}")

        # Model status
        model = self.get("api.model", "未设置")
        print(f"模型设置: {model}")

        # Parser status
        parser = self.get("parser.type", "未设置")
        print(f"解析器: {parser}")

        # Translation settings
        source_lang = self.get("translation.default_source_language", "English")
        target_lang = self.get("translation.default_target_language", "中文")
        print(f"默认语言: {source_lang} → {target_lang}")

        print("-" * 40)

        # Show validation results
        validation = self.validate_config()
        if all(section["valid"] for section in validation.values()):
            print_success("配置验证通过")
        else:
            print_error("配置存在问题:")
            for section, result in validation.items():
                if not result["valid"]:
                    for issue in result["issues"]:
                        print(f"  - {section}: {issue}")

    def import_config(self, config_path: str, merge: bool = False) -> bool:
        """Import configuration from specified file path.

        Args:
            config_path: Path to configuration file (JSON or .env)
            merge: If True, merge with existing config. If False, replace all config.

        Returns:
            bool: True if successful, False otherwise
        """
        config_path = Path(config_path)

        if not config_path.exists():
            print_error(f"配置文件不存在: {config_path}")
            return False

        try:
            if config_path.suffix == '.json':
                # Load JSON config
                with open(config_path, 'r', encoding='utf-8') as f:
                    imported_config = json.load(f)

                if merge:
                    # Merge with existing config
                    self.config = self._merge_configs(self.config, imported_config)
                    print(f"配置已从 {config_path} 导入并合并")
                else:
                    # Replace existing config
                    self.config = self._merge_configs(self.default_config, imported_config)
                    print(f"配置已从 {config_path} 导入并替换")

                # Auto-save to default path
                self.save_config()
                return True

            elif config_path.name == '.env' or config_path.suffix == '.env':
                # Load .env file
                with open(config_path, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()

                env_vars = {}
                for line in env_lines:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

                if env_vars:
                    self._import_env_vars(env_vars)
                    print(f"环境变量已从 {config_path} 导入")
                    # Auto-save to default .env
                    self._save_env_vars_to_default()
                else:
                    print_error(f"未找到有效的环境变量: {config_path}")
                    return False

                return True

            else:
                print_error(f"不支持的配置文件格式: {config_path.suffix}")
                print("支持的格式: .json, .env")
                return False

        except json.JSONDecodeError as e:
            print_error(f"JSON格式错误: {e}")
            return False
        except IOError as e:
            print_error(f"文件读取失败: {e}")
            return False

    def export_config(self, export_path: str, include_env: bool = True) -> bool:
        """Export current configuration to specified file path.

        Args:
            export_path: Path to export configuration file (JSON or .env)
            include_env: For .env export, include all environment variables
                         For JSON export, this parameter is ignored

        Returns:
            bool: True if successful, False otherwise
        """
        export_path = Path(export_path)

        # Create parent directories if needed
        export_path.parent.mkdir(exist_ok=True, parents=True)

        try:
            if export_path.suffix == '.json':
                # Export as JSON (hide sensitive data)
                export_config = self.config.copy()
                export_config["api"]["siliconflow_api_key"] = "[已设置]" if self.get_api_key("siliconflow") else ""
                export_config["api"]["openai_api_key"] = "[已设置]" if self.get_api_key("openai") else ""
                export_config["api"]["mineru_api_token"] = "[已设置]" if self.get_api_key("mineru") else ""

                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_config, f, indent=2, ensure_ascii=False)

                print_success(f"配置已导出到: {export_path}")
                return True

            elif export_path.name == '.env' or export_path.suffix == '.env':
                # Export as .env
                self._export_env_vars_to_file(export_path, include_all=include_env)
                print_success(f"环境变量已导出到: {export_path}")
                return True

            else:
                print_error(f"不支持的导出格式: {export_path.suffix}")
                print("支持的格式: .json, .env")
                return False

        except IOError as e:
            print_error(f"文件写入失败: {e}")
            return False

    def _import_env_vars(self, env_vars: Dict[str, str]) -> None:
        """Import environment variables into config.

        Args:
            env_vars: Dictionary of environment variables
        """
        # Map environment variables to config keys
        env_mapping = {
            "SILICONFLOW_API_KEY": "api.siliconflow_api_key",
            "SILICONFLOW_BASE_URL": "api.base_url",
            "SILICONFLOW_MODEL": "api.model",
            "PDF_PARSER_TYPE": "parser.type",
            "MINERU_API_TOKEN": "api.mineru_api_token",
            "MINERU_API_URL": "parser.api_url",
            "MINERU_MODEL_VERSION": "parser.model_version",
            "MINERU_TIMEOUT": "parser.timeout",
            "MINERU_POLL_INTERVAL": "parser.poll_interval",
        }

        for env_key, value in env_vars.items():
            if env_key in env_mapping:
                config_key = env_mapping[env_key]
                self.set(config_key, value)

            # Also store API keys in .env
            if "API_KEY" in env_key or "API_TOKEN" in env_key:
                self._set_env_variable(env_key, value)

    def _save_env_vars_to_default(self) -> None:
        """Save all relevant environment variables to default .env file."""
        # Read existing .env file if it exists
        existing_environ = {}
        if self.env_file.exists():
            existing_environ = {}
            try:
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.split('=', 1)
                            existing_environ[key.strip()] = value.strip()
            except IOError:
                pass

        # Build env variables from existing values and config
        env_vars = {}

        # Use existing values for API keys (don't override with defaults)
        if "SILICONFLOW_API_KEY" in existing_environ:
            env_vars["SILICONFLOW_API_KEY"] = existing_environ["SILICONFLOW_API_KEY"]

        if "MINERU_API_TOKEN" in existing_environ:
            env_vars["MINERU_API_TOKEN"] = existing_environ["MINERU_API_TOKEN"]

        # Get other values from config
        env_vars["SILICONFLOW_BASE_URL"] = self.get("api.base_url", "https://api.siliconflow.cn/v1")
        env_vars["SILICONFLOW_MODEL"] = self.get("api.model", "Pro/moonshotai/Kimi-K2.5")
        env_vars["PDF_PARSER_TYPE"] = self.get("parser.type", "mineru")
        env_vars["MINERU_API_URL"] = self.get("parser.api_url", "https://mineru.net/api/v4")
        env_vars["MINERU_MODEL_VERSION"] = self.get("parser.model_version", "vlm")
        env_vars["MINERU_TIMEOUT"] = str(self.get("parser.timeout", 300))
        env_vars["MINERU_POLL_INTERVAL"] = str(self.get("parser.poll_interval", 5))

        # Write to .env file
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write("# SiliconFlow API Configuration\n")
                f.write(f"SILICONFLOW_API_KEY={env_vars['SILICONFLOW_API_KEY']}\n")
                f.write(f"SILICONFLOW_BASE_URL={env_vars['SILICONFLOW_BASE_URL']}\n")
                f.write(f"SILICONFLOW_MODEL={env_vars['SILICONFLOW_MODEL']}\n")
                f.write("\n")
                f.write("# PDF Parser Configuration\n")
                f.write(f"PDF_PARSER_TYPE={env_vars['PDF_PARSER_TYPE']}\n")
                f.write("\n")
                f.write("# MinerU API Configuration\n")
                f.write(f"MINERU_API_TOKEN={env_vars['MINERU_API_TOKEN']}\n")
                f.write(f"MINERU_API_URL={env_vars['MINERU_API_URL']}\n")
                f.write(f"MINERU_MODEL_VERSION={env_vars['MINERU_MODEL_VERSION']}\n")
                f.write(f"MINERU_TIMEOUT={env_vars['MINERU_TIMEOUT']}\n")
                f.write(f"MINERU_POLL_INTERVAL={env_vars['MINERU_POLL_INTERVAL']}\n")
        except IOError as e:
            print_error(f"保存环境变量失败: {e}")

    def _export_env_vars_to_file(self, export_path: Path, include_all: bool = True) -> None:
        """Export environment variables to specified file.

        Args:
            export_path: Path to export file
            include_all: If True, export all variables including empty ones.
                        If False, only export non-empty values.
        """
        env_vars = {
            "SILICONFLOW_API_KEY": self.get_api_key("siliconflow") or "",
            "SILICONFLOW_BASE_URL": self.get("api.base_url", "https://api.siliconflow.cn/v1"),
            "SILICONFLOW_MODEL": self.get("api.model", "Pro/moonshotai/Kimi-K2.5"),
            "PDF_PARSER_TYPE": self.get("parser.type", "mineru"),
            "MINERU_API_TOKEN": self.get_api_key("mineru") or "",
            "MINERU_API_URL": self.get("parser.api_url", "https://mineru.net/api/v4"),
            "MINERU_MODEL_VERSION": self.get("parser.model_version", "vlm"),
            "MINERU_TIMEOUT": str(self.get("parser.timeout", 300)),
            "MINERU_POLL_INTERVAL": str(self.get("parser.poll_interval", 5)),
        }

        with open(export_path, 'w', encoding='utf-8') as f:
            f.write("# SiliconFlow API Configuration\n")
            if include_all or env_vars["SILICONFLOW_API_KEY"]:
                f.write(f"SILICONFLOW_API_KEY={env_vars['SILICONFLOW_API_KEY']}\n")
            f.write(f"SILICONFLOW_BASE_URL={env_vars['SILICONFLOW_BASE_URL']}\n")
            f.write(f"SILICONFLOW_MODEL={env_vars['SILICONFLOW_MODEL']}\n")
            f.write("\n")
            f.write("# PDF Parser Configuration\n")
            f.write(f"PDF_PARSER_TYPE={env_vars['PDF_PARSER_TYPE']}\n")
            f.write("\n")
            f.write("# MinerU API Configuration\n")
            if include_all or env_vars["MINERU_API_TOKEN"]:
                f.write(f"MINERU_API_TOKEN={env_vars['MINERU_API_TOKEN']}\n")
            f.write(f"MINERU_API_URL={env_vars['MINERU_API_URL']}\n")
            f.write(f"MINERU_MODEL_VERSION={env_vars['MINERU_MODEL_VERSION']}\n")
            f.write(f"MINERU_TIMEOUT={env_vars['MINERU_TIMEOUT']}\n")
            f.write(f"MINERU_POLL_INTERVAL={env_vars['MINERU_POLL_INTERVAL']}\n")

    def get_config_paths(self) -> Dict[str, str]:
        """Get paths to configuration files.

        Returns:
            Dict[str, str]: Dictionary with paths to config.json and .env
        """
        return {
            "config": str(self.config_file),
            "env": str(self.env_file),
            "config_dir": str(self.config_dir)
        }

    def reload_config(self, reload_backend: bool = True) -> bool:
        """Reload configuration from file.

        Args:
            reload_backend: If True, also reload backend configuration

        Returns:
            bool: True if successful, False otherwise
        """
        if self.config_file.exists():
            self.config = self._load_config()
            print_success("配置已重新加载")

            # Reload backend configuration if available
            if reload_backend:
                self._reload_backend_config()

            return True
        else:
            print_error("配置文件不存在")
            return False

    def _reload_backend_config(self) -> bool:
        """Reload backend environment configuration.

        Notifies backend modules to reload environment variables from .env file.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Import the backend config reload function
            import sys
            from pathlib import Path as P

            # Add project root to path
            project_root = P(__file__).parent.parent.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            from src.backend import reload_environment_config

            # Reload from the .env file managed by this ConfigManager
            if self.env_file.exists():
                reload_environment_config(self.env_file)
                print_success("Backend 配置已重新加载")
                return True
            else:
                # Reload from default locations
                reload_environment_config()
                print_success("Backend 配置已重新加载 (使用默认路径)")
                return True
        except ImportError as e:
            print_warning(f"Backend 配置重新加载失败 (函数不可用): {e}")
            return False
        except Exception as e:
            print_error(f"Backend 配置重新加载失败: {e}")
            return False