#!/usr/bin/env python3
import subprocess
import os
import sys
import platform
import importlib.util

def is_package_installed(package_name):
    return importlib.util.find_spec(package_name) is not None

def install_packages():
    needs_install = []

    if not is_package_installed("requests"):
        needs_install.append("requests")
    if not is_package_installed("dotenv") and not is_package_installed("python_dotenv"):
        needs_install.append("python-dotenv")

    if not needs_install:
        return True

    print(f"Installing: {', '.join(needs_install)}")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", *needs_install], check=True)
        print("Packages installed successfully.")
        return True
    except subprocess.CalledProcessError:
        print("Failed to install packages. Please install them manually.")
        return False


try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda: None  # fallback

def get_system_env_var(key):
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["reg", "query", "HKCU\\Environment", "/v", key],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if key in line:
                        return line.split()[-1].strip()
        except Exception as e:
            print(f"Could not read system env var: {e}")
    else:
        return os.getenv(key)
    return None

def get_or_set_api_key(key_name):
    load_dotenv()
    api_key = get_system_env_var(key_name) or os.getenv(key_name)

    if api_key:
        return False  # not newly set

    print(f"{key_name} not found.")
    user_input = input(f"Enter your {key_name}: ").strip()

    if not user_input:
        print(f"{key_name} is required to proceed.")
        return False

    os.environ[key_name] = user_input
    print(f"{key_name} set for the current session.")

    if platform.system() == "Windows":
        try:
            subprocess.run(f'setx {key_name} "{user_input}"', check=True, shell=True)
            print(f"{key_name} set permanently in system environment variables (Windows).")
        except subprocess.CalledProcessError as e:
            print(f"Failed to set {key_name} permanently: {e}")
            return False
    else:
        shell_config_file = os.path.expanduser("~/.bashrc")
        if os.path.exists(os.path.expanduser("~/.zshrc")):
            shell_config_file = os.path.expanduser("~/.zshrc")

        try:
            with open(shell_config_file, "a") as file:
                file.write(f"\nexport {key_name}={user_input}\n")
            print(f"{key_name} set permanently in {shell_config_file}.")
            print(f"Please run `source {shell_config_file}` or restart your terminal to apply.")
        except Exception as e:
            print(f"Failed to write to shell config file: {e}")
            return False

    return True  # newly set

def setup():
    newly_set = False

    gemini_key = get_system_env_var("GEMINI_API_KEY")
    openai_key = get_system_env_var("OPENAI_API_KEY")

    if gemini_key and openai_key:
        return False  # No need to restart

    print("Setting up AI Task Agent...\n")

    if not install_packages():
        return False

    if get_or_set_api_key("GEMINI_API_KEY"):
        newly_set = True
    if get_or_set_api_key("OPENAI_API_KEY"):
        newly_set = True

    if newly_set:
        print("\nSetup complete! \n\nPlease restart your terminal for environment variable changes to take effect!!!\n")
        return True  # Needs restart

    return False  # Already set before

def run_setup_if_needed():
    return setup()
