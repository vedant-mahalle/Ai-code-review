
import argparse
import os
import sys
import glob
import json
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
import google.generativeai as genai
import threading
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def animated_welcome():
    from rich.live import Live
    from rich.text import Text
    import time
    welcome = Text("Welcome to AI-Review Client! 🚀", style="bold magenta", justify="center")
    with Live(welcome, refresh_per_second=8, transient=True):
        for i in range(12):
            welcome.stylize(f"bold magenta on color({(i*20)%255})")
            time.sleep(0.07)
    console.print("[bold magenta]Let's make your code better, together![/bold magenta]", justify="center")

def print_logo():
    logo = '''\
   █████╗ ██╗      ██████╗ ███████╗██╗   ██╗██╗███████╗██╗    ██╗███████╗██████╗          ██████╗██╗     ██╗
██╔══██╗██║      ██╔══██╗██╔════╝██║   ██║██║██╔════╝██║    ██║██╔════╝██╔══██╗        ██╔════╝██║     ██║
███████║██║█████╗██████╔╝█████╗  ██║   ██║██║█████╗  ██║ █╗ ██║█████╗  ██████╔╝        ██║     ██║     ██║
██╔══██║██║╚════╝██╔══██╗██╔══╝  ╚██╗ ██╔╝██║██╔══╝  ██║███╗██║██╔══╝  ██╔══██╗        ██║     ██║     ██║
██║  ██║██║      ██║  ██║███████╗ ╚████╔╝ ██║███████╗╚███╔███╔╝███████╗██║  ██║        ╚██████╗███████╗██║
╚═╝  ╚═╝╚═╝      ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚═╝╚══════╝ ╚══╝╚══╝ ╚══════╝╚═╝  ╚═╝         ╚═════╝╚══════╝╚═╝
                                                                                                          
                                                                                                       
   [bold magenta]AI REVIEWER[/bold magenta]
'''
    console.print(logo, justify="center")

SUPPORTED_EXTENSIONS = ['.py', '.js', '.ts', '.java', '.cpp']
console = Console()

load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    console.print('[bold red]Error:[/bold red] GEMINI_API_KEY not found in environment.')
    sys.exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def get_code_files(path):
    IGNORE_DIRS = {'node_modules', '.next', '.git', 'dist', 'build', '__pycache__'}
    p = Path(path)
    if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS:
        return [str(p)]
    elif p.is_dir():
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            for f in p.rglob(f'*{ext}'):
                parts = set(f.parts)
                if any(part in IGNORE_DIRS for part in parts):
                    continue
                if any(part.startswith('.') and part != '.' for part in parts):
                    continue
                files.append(str(f))
        return files
    return []

def read_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        console.print(f'[yellow]Warning:[/yellow] Could not read {file_path}: {e}')
        return None

def review_code(code, filename):
    prompt = f"""
You are an expert code reviewer. Please review the following code file: {filename}

For each section below, respond in clear, concise bullet points. If you find a bug, provide a corrected code snippet for the buggy section. Make the output easy to scan and actionable for developers working on large, complex projects.

Sections:
- Bugs or logic issues (if any, provide corrected code)
- Best practices
- Security issues
- Readability and maintainability
- Suggestions for optimization

Format your response as:
---
File: {filename}

Bugs or logic issues:
- ...
Corrected code (if any):
```
...fixed code...
```

Best practices:
- ...

Security issues:
- ...

Readability and maintainability:
- ...

Suggestions for optimization:
- ...
---

Code:
```
{code}
```
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error reviewing {filename}: {e}"

def display_review(result, filename, mode):
    import re
    console.rule(f"[bold blue]� Reviewing: [bold white]{filename}[/bold white]")
    bugs_match = re.search(r'Bugs or logic issues:\n(-[\s\S]*?)(?:\n\n|Corrected code)', result)
    fixed_code_match = re.search(r'Corrected code \(if any\):\n```([\s\S]*?)```', result)
    bugs = bugs_match.group(1).strip() if bugs_match else None
    fixed_code = fixed_code_match.group(1).strip() if fixed_code_match else None

    # Show bugs first
    if bugs and ('No bugs' not in bugs and 'None' not in bugs):
        console.print(f"[bold red]🐞 Bugs or logic issues found:[/bold red]")
        for line in bugs.split('\n'):
            if line.strip():
                console.print(f"[red]• {line}[/red]")
                time.sleep(0.10)
    else:
        console.print(f"[bold green]✅ No bugs or logic issues found![/bold green]")
        time.sleep(0.10)

    # Show rest of review (best practices, security, etc.)
    other_sections = re.sub(r'Bugs or logic issues:\n(-[\s\S]*?)(?:\n\n|Corrected code)', '', result)
    console.print(Markdown(other_sections))

    # If there is a fix, always ask user if they want to apply it and rewrite the file
    if fixed_code and bugs and ('No bugs' not in bugs and 'None' not in bugs):
        console.rule(f"[bold yellow]🛠️ Gemini AI Suggested Fix for {filename}[/bold yellow]")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                old_code = f.read()
        except Exception as e:
            old_code = ''
        import difflib
        diff = difflib.unified_diff(
            old_code.splitlines(),
            fixed_code.splitlines(),
            fromfile='before.py',
            tofile='after.py',
            lineterm=''
        )
        diff_text = '\n'.join(diff)
        if diff_text:
            console.rule('[bold magenta]🔎 Diff: Proposed Changes[/bold magenta]')
            for line in diff_text.split('\n'):
                console.print(f'[white]{line}[/white]')
                time.sleep(0.05)
        # Always prompt for every file with bugs
        while True:
            console.print("\n[bold yellow]Would you like to apply the suggested fix to this file?[/bold yellow]", justify="center")
            console.print("[bold green][Y][/bold green]es    [bold red][N][/bold red]o", justify="center")
            apply = input("[?] Enter your choice: ").strip().lower()
            if apply in ('y', 'n'):
                break
            console.print("[red]Please enter 'y' or 'n'.[/red]", justify="center")
        if apply == 'y':
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            console.print(f'\n[bold green]✅ Applied Gemini AI bug fix to {filename}[/bold green]', justify="center")
        else:
            console.print(f'\n[bold yellow]⚠️ Skipped applying bug fix to {filename}[/bold yellow]', justify="center")
    console.rule("[dim]End of Review[/dim]")
    return None

def review_worker(file_path, results):
    code = read_file(file_path)
    if code is None:
        console.print(f'[yellow]⚠️ Skipping unreadable file: {file_path}[/yellow]')
        results[file_path] = None
        return
    review = review_code(code, file_path)
    results[file_path] = review

def main():
    clear_screen()
    print_logo()
    animated_welcome()
    parser = argparse.ArgumentParser(description='AI Code Reviewer using Gemini Pro')
    parser.add_argument('path', help='File or directory to review')
    parser.add_argument('--json', action='store_true', help='Export reviews as JSON')
    parser.add_argument('--md', action='store_true', help='Export reviews as Markdown')
    parser.add_argument('--thread', action='store_true', help='Run reviews in parallel using threads')
    args = parser.parse_args()

    files = get_code_files(args.path)
    if not files:
        console.print(f'[bold red]❌ No supported code files found at {args.path}[/bold red]')
        sys.exit(1)

    reviews = []
    console.rule(f"[bold magenta]🚀 Starting Code Review for {len(files)} file(s)[/bold magenta]")

    if args.thread:
        results = {}
        threads = []
        with console.status('[bold green]Reviewing code files in parallel...[/bold green]', spinner='dots'):
            for file_path in files:
                t = threading.Thread(target=review_worker, args=(file_path, results))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
        for idx, file_path in enumerate(files, 1):
            console.rule(f"[bold blue]🔹 Reviewing file {idx}/{len(files)}: {file_path}[/bold blue]")
            result = results[file_path]
            if result is None:
                continue
            display_review(result, file_path, 'json' if args.json else 'md' if args.md else None)
            if args.json or args.md:
                reviews.append({"file": file_path, "review": result})
    else:
        with console.status('[bold green]Reviewing code files...[/bold green]', spinner='dots') as status:
            for idx, file_path in enumerate(files, 1):
                console.rule(f"[bold blue]🔹 Reviewing file {idx}/{len(files)}: {file_path}[/bold blue]")
                status.update(f'[cyan]({idx}/{len(files)}) Reviewing [bold]{file_path}[/bold]...')
                code = read_file(file_path)
                if code is None:
                    console.print(f'[yellow]⚠️ Skipping unreadable file: {file_path}[/yellow]')
                    continue
                review = review_code(code, file_path)
                display_review(review, file_path, 'json' if args.json else 'md' if args.md else None)
                if args.json or args.md:
                    reviews.append({"file": file_path, "review": review})

    console.rule("[bold green]🎉 Review Process Complete[/bold green]")
    if args.json:
        out_path = 'reviews.json'
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(reviews, f, indent=2)
        console.print(f'[green]📦 Reviews exported to {out_path}[/green]')
    elif args.md:
        out_path = 'reviews.md'
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join([r['review'] for r in reviews]))
        console.print(f'[green]📦 Reviews exported to {out_path}[/green]')

if __name__ == '__main__':
    main()