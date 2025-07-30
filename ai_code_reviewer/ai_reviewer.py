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

SUPPORTED_EXTENSIONS = ['.py', '.js', '.ts', '.java', '.cpp']
console = Console()

load_dotenv()
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    console.print('[bold red]Error:[/bold red] GEMINI_API_KEY not found in environment.')
    sys.exit(1)

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

def get_code_files(path):
    p = Path(path)
    if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS:
        return [str(p)]
    elif p.is_dir():
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend([str(f) for f in p.rglob(f'*{ext}')])
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

For each section below, respond in clear, concise bullet points. Make the output easy to scan and actionable for developers working on large, complex projects.

Sections:
- Bugs or logic issues
- Best practices
- Security issues
- Readability and maintainability
- Suggestions for optimization

Format your response as:
---
File: {filename}

Bugs or logic issues:
- ...

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
    if mode == 'json':
        return {"file": filename, "review": result}
    elif mode == 'md':
        return f"## Review for `{filename}`\n\n{result}"
    else:
        console.rule(f"Review: {filename}")
        # Print each section as Markdown for clarity
        console.print(Markdown(result))
        console.rule()
        return None

def main():
    parser = argparse.ArgumentParser(description='AI Code Reviewer using Gemini Pro')
    parser.add_argument('path', help='File or directory to review')
    parser.add_argument('--json', action='store_true', help='Export reviews as JSON')
    parser.add_argument('--md', action='store_true', help='Export reviews as Markdown')
    args = parser.parse_args()

    files = get_code_files(args.path)
    if not files:
        console.print(f'[bold red]No supported code files found at {args.path}[/bold red]')
        sys.exit(1)

    reviews = []
    with console.status('[bold green]Reviewing code files...[/bold green]', spinner='dots') as status:
        for idx, file_path in enumerate(files, 1):
            status.update(f'[cyan]({idx}/{len(files)}) Reviewing [bold]{file_path}[/bold]...')
            code = read_file(file_path)
            if code is None:
                continue
            review = review_code(code, file_path)
            result = display_review(review, file_path, 'json' if args.json else 'md' if args.md else None)
            if args.json or args.md:
                reviews.append(result)

    if args.json:
        out_path = 'reviews.json'
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(reviews, f, indent=2)
        console.print(f'[green]Reviews exported to {out_path}[/green]')
    elif args.md:
        out_path = 'reviews.md'
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(reviews))
        console.print(f'[green]Reviews exported to {out_path}[/green]')

if __name__ == '__main__':
    main()
