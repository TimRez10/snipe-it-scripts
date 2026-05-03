"""
Automatic Snipe-IT Updater (Interactive)
Prompts user to update assets or licenses from various vendors.
Author: Timur Reziapov
"""

import importlib
import sys
from pathlib import Path
from modules.logging import setup_logger
import argparse
import os

logger = setup_logger()


def get_scripts_from_folder(path):
    """Discover all available scripts in a folder."""
    scripts_dir = Path(path)
    script_list = []
    
    if not scripts_dir.exists():
        logger.warning("Scripts directory does not exist: %s", scripts_dir)
        return script_list
    
    for script in scripts_dir.iterdir():
        if script.is_file() and script.suffix == ".py" and script.name != "__init__.py":
            script_name = script.stem.replace("_", " ").title()
            script_list.append(script_name)
    
    return sorted(script_list)


def _import_module(module_path):
    """Import or reload a module."""
    if module_path in sys.modules:
        return importlib.reload(sys.modules[module_path])
    else:
        return importlib.import_module(module_path)


def _execute_module(module, script_name):
    """Execute a module's main() or run() function."""
    if hasattr(module, 'main'):
        return module.main()
    else:
        logger.error(f"No main() function found in module for '{script_name}'")
        print(f"✗ {script_name} script has no main() or run() function")
        return False


def _handle_result(result, script_name):
    """Handle the return value from a script execution."""
    if result is None or result is True:
        print(f"✓ {script_name} update completed successfully")
        return True
    else:
        logger.warning("Script '%s' returned: %s", script_name, result)
        print(f"✗ {script_name} update failed")
        return False


def _run_script_as_module(module_path, display_name):
    """
    Generic function to run a script as a module.
    """
    logger.debug(f"Running script: {display_name}")
    
    print(f"\nRunning {display_name} update...")
    print("-" * 50)
    
    try:
        module = _import_module(module_path)
        result = _execute_module(module, display_name)
        return _handle_result(result, display_name)
            
    except ModuleNotFoundError:
        logger.error("Module not found for '%s': %s", display_name, module_path)
        print(f"Error: Script not found for '{display_name}'")
        return False
    except Exception as e:
        logger.exception("Error running script '%s': %s", display_name, str(e))
        print(f"✗ Error running {display_name} script: {e}")
        return False


def run_scripts(script_name, script_folder):
    module_name = script_name.replace(" ", "_").lower()
    module_path = f"{script_folder}.{module_name}"
    return _run_script_as_module(module_path, script_name)


def handle_script_selection(folder_name, allow_multiple=False):
    """
    Helper function to list scripts, get user input, and run the selection.
    """
    available_scripts = get_scripts_from_folder(folder_name)
    
    if not available_scripts:
        print(f"No scripts found in {folder_name}/")
        return

    print("\nAvailable scripts:")
    if allow_multiple:
        print("(Select multiple by space-separating, e.g., '1 3')")
        
    for i, script in enumerate(available_scripts, start=1):
        print(f"{i}) {script}")

    user_input = input("> ").strip()

    # Normalize input: always treat as a list of choices
    if allow_multiple:
        choices = user_input.split()
    else:
        choices = [user_input]

    # Filter for valid unique integers
    valid_indices = []
    for c in choices:
        if c.isdigit():
            idx = int(c)
            if 1 <= idx <= len(available_scripts):
                valid_indices.append(idx)
            else:
                print(f"Invalid number: {c}")
        else:
            print(f"Invalid input: {c}")

    # Remove duplicates if allowing multiple, just in case
    valid_indices = list(dict.fromkeys(valid_indices))

    if not valid_indices:
        print("No valid scripts selected.")
        return

    # Run
    for idx in valid_indices:
        script_name = available_scripts[idx - 1]
        run_scripts(script_name, folder_name)
        print()


def run_interactive_menu():
    while True:
        print("1) Update Assets")
        print("2) Update Licenses")
        print("3) Custom Script")
        print("q) Quit")

        choice = input("> ").strip().lower()

        if choice == "1":
            handle_script_selection("asset_scripts", allow_multiple=False)
        elif choice == "2":
            handle_script_selection("license_scripts", allow_multiple=True)
        elif choice == "3":
            handle_script_selection("custom_scripts", allow_multiple=False)
        elif choice == "q":
            print("Exiting.")
            sys.exit()
        else:
            print("Invalid selection.")


def parse_args():
    parser = argparse.ArgumentParser(description="Automatic Snipe-IT Updater. By: Timur Reziapov. Run without arguments for interactive mode.")
    parser.add_argument(
        "--script", 
        type=str, 
        help="Run a specific script directly"
    )
    
    return parser.parse_args()


def main():
    args = parse_args()

    # Check if running in CLI mode
    if args.script:
        # Split "folder/script.py" into "folder" and "script.py"
        folder, script_name = os.path.split(args.script)
        if "." in script_name:
            script_name = script_name.split('.')[0]
        
        if not folder or not script_name:
            print("Error: Please provide the full path including folder and filename.")
            return

        print(f"Running single script: {script_name} from {folder}...")
        run_scripts(script_name, folder)
        return

    # Run Interactive Menu (if no arguments provided)
    run_interactive_menu()


if __name__ == "__main__":
    main()