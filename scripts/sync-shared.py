import os
import shutil
import yaml
import difflib
import argparse
import fnmatch
from pathlib import Path
from termcolor import colored

# ASCII Art Banner


def print_banner():
    banner = r"""============================================================================
 _____                    _       _         _____                           
|_   _|                  | |     | |       /  ___|                          
  | | ___ _ __ ___  _ __ | | __ _| |_ ___  \ `--. _   _ _ __   ___ ___ _ __ 
  | |/ _ \ '_ ` _ \| '_ \| |/ _` | __/ _ \  `--. \ | | | '_ \ / __/ _ \ '__|
  | |  __/ | | | | | |_) | | (_| | ||  __/ /\__/ / |_| | | | | (_|  __/ |   
  \_/\___|_| |_| |_| .__/|_|\__,_|\__\___| \____/ \__, |_| |_|\___\___|_|   
                   | |                             __/ |                    
by Rubos           |_|                            |___/                 v1.0
============================================================================"""
    print(colored(banner, "green"))
    print(colored("Welcome to Template-Syncer!", "green"))

# Load sync.yml configuration


debug = False


def dlog(msg):
    if debug:
        print(colored(f"[DEBUG] {msg}", "yellow"))


def difflog(msg):
    if debug:
        print(colored(f"[DIFF] {msg}", "green"))


def ilog(msg):
    print(colored(f"[INFO] {msg}", "blue"))


def wlog(msg):
    print(colored(f"[WARNING] {msg}", "yellow"))


def elog(msg):
    print(colored(f"[ERROR] {msg}", "red"))


def load_config(config_path):
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

# Get the list of files to copy based on overwrites


def get_files_to_copy(overwrite_config, overwrite_dir):
    files_to_copy = []
    for root, _, files in os.walk(overwrite_dir):
        for file in files:
            file_path = os.path.relpath(
                os.path.join(root, file), overwrite_dir)
            include = True

            # Check exclusion rules
            if 'exclude' in overwrite_config:
                for pattern in overwrite_config['exclude']:
                    if Path(file_path).match(pattern):
                        include = False
                        break

            if 'glob' in overwrite_config and not Path(file_path).match(overwrite_config['glob']):
                include = False

            if include:
                files_to_copy.append(file_path)
    return files_to_copy

# Copy files to the template directory


def copy_files(files, src_dir, dest_dir, dry_run=False, show_diff=False, max_diff_chars=None):
    dlog(f"Copying files from {src_dir} to {dest_dir}")
    for file in files:
        src_path = os.path.join(src_dir, file)
        dest_path = os.path.join(dest_dir, file)

        # Ensure destination directory exists
        if not dry_run:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        if show_diff:
            # Show diff if the file exists
            if os.path.exists(dest_path):
                with open(src_path, 'r') as src_file, open(dest_path, 'r') as dest_file:
                    src_content = src_file.read()
                    dest_content = dest_file.read()
                    if src_content != dest_content:
                        diff = difflib.unified_diff(
                            dest_content.splitlines(keepends=True),
                            src_content.splitlines(keepends=True),
                            fromfile=dest_path,
                            tofile=src_path
                        )
                        diff_output = ''.join(diff)
                        if max_diff_chars and len(diff_output) > max_diff_chars:
                            diff_output = diff_output[:max_diff_chars] + \
                                "\n... (truncated)"
                        difflog(diff_output)
                    else:
                        difflog(f"No changes in {file}")
            else:
                difflog(f"New file: {file}")
        if not dry_run:
            # Copy the file
            shutil.copy2(src_path, dest_path)

# Process templates based on sync.yml


def process_templates(config, overwrite_dir, templates_dir, specific_templates=None, dry_run=False, show_diff=False, max_diff_chars=None):
    dlog(f"Processing templates with config: {config}")
    for template in config['templates']:
        template_name = template['name']
        if specific_templates and template_name not in specific_templates:
            continue

        ilog(f"Processing template: {template_name}, {template}")
        template_dir = os.path.join(templates_dir, template_name)
        if not os.path.exists(template_dir) and not dry_run:
            wlog(
                f"Template directory '{template_name}' does not exist, creating it.")
            os.makedirs(template_dir, exist_ok=True)

        overwrites = template.get('overwrites', {})
        dlog(f"Overwrites for {template_name}: {overwrites}")
        # if overwrites does not explicitly contain "default", add it
        if 'default' not in overwrites:
            overwrites['default'] = True
        for overwrite_name, overwrite_config in overwrites.items():
            if isinstance(overwrite_config, bool):
                if not overwrite_config:
                    continue
                overwrite_config = {}

            overwrite_path = os.path.join(overwrite_dir, overwrite_name)
            if not os.path.exists(overwrite_path):
                wlog(
                    f"Overwrite directory '{overwrite_name}' does not exist.")
                continue

            files_to_copy = get_files_to_copy(overwrite_config, overwrite_path)
            copy_files(
                files_to_copy,
                overwrite_path,
                template_dir,
                dry_run=dry_run,
                show_diff=show_diff,
                max_diff_chars=max_diff_chars
            )

# Main function


def main():
    global debug
    # Print banner and debug information
    print_banner()
    parser = argparse.ArgumentParser(
        description="Sync shared overwrites to templates.")
    parser.add_argument("-c", "--config", default="shared/sync.yml",
                        help="Path to the sync.yml configuration file.")
    parser.add_argument("-w", "--overwrite-dir", default="shared/overwrites",
                        help="Path to the overwrites directory.")
    parser.add_argument("-t", "--templates-dir", default="templates",
                        help="Path to the templates directory.")
    parser.add_argument("-o", "--only", nargs="*",
                        help="Specific templates to process.")
    parser.add_argument("-d", "--dry-run", action="store_true",
                        help="Perform a dry run without applying changes.")
    parser.add_argument("-s", "--show-diff", action="store_true",
                        help="Show differences in the terminal. Can be used with --dry-run.")
    parser.add_argument("-m", "--max-diff-chars", type=int,
                        help="Maximum number of characters to show in diffs.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose output.")
    args = parser.parse_args()

    # ensure cwd is repo root, assuming we are in scripts/
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

    if args.verbose:
        print(
            "----------------------------------------------------------------------------")
        print("Debug Information")
        print(
            "----------------------------------------------------------------------------")
        print(f"> Config Path: {os.path.abspath(args.config)}")
        print(f"> Overwrite Directory: {os.path.abspath(args.overwrite_dir)}")
        print(f"> Templates Directory: {os.path.abspath(args.templates_dir)}")
        print(f"> Specific Templates Only: {args.only}")
        print(f"> Dry run: {args.dry_run}")
        print(f"> Show diff: {args.show_diff}")
        print(f"> Max Diff Characters: {args.max_diff_chars}")
        print(
            "----------------------------------------------------------------------------")
        debug = True

    config = load_config(args.config)
    process_templates(
        config, args.overwrite_dir,
        args.templates_dir,
        specific_templates=args.only,
        dry_run=args.dry_run,
        show_diff=args.show_diff,
        max_diff_chars=args.max_diff_chars
    )


if __name__ == "__main__":
    main()
