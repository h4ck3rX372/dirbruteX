import requests
import pyfiglet
from colorama import init, Fore, Style
import os
import threading
from queue import Queue
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.styles import Style as PromptStyle
from urllib.parse import urlparse
import socket

lock = threading.Lock()
progress_lock = threading.Lock()
progress = 0
total = 0


def show_banner():
    init(autoreset=True)
    os.system('cls' if os.name == 'nt' else 'clear')
    ascii_banner = pyfiglet.figlet_format("H4CK3R-X", font="ANSI_Shadow")
    print(ascii_banner)
    print(Fore.YELLOW + Style.BRIGHT + "Version --> 1.0\n")


import subprocess


def is_host_reachable(url):
    try:
        # Parse base URL
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Try HEAD request to the base URL
        response = requests.head(base_url, timeout=5, allow_redirects=True)

        # Accept only 200, 301, 302, 403, etc., but reject things like 404
        if response.status_code == 404:
            return False
        return True

    except requests.RequestException:
        return False


def worker(queue, target_url, wordlist, output_file, extensions, recursive):
    global progress
    while not queue.empty():
        word = queue.get()
        paths_to_try = [word]

        if extensions:
            for ext in extensions:
                paths_to_try.append(f"{word}{ext}")

        for path in paths_to_try:
            url = f"{target_url.rstrip('/')}/{path}"
            try:
                response = requests.get(url, timeout=5)
                if response.status_code != 404:
                    msg = f"[+] {url} ({response.status_code})"
                    print(Fore.GREEN + msg)
                    if output_file:
                        with lock:
                            with open(output_file, "a") as f:
                                f.write(url + "\n")

                    # Recursive logic
                    if recursive and response.status_code in [200, 301, 302, 403] and url.endswith('/'):
                        for subword in wordlist:
                            queue.put(f"{path}/{subword}")
            except requests.RequestException:
                continue

        with progress_lock:
            progress += 1
            print(Fore.CYAN + f"[✓] Progress: ({progress}/{total})", end='\r', flush=True)
        queue.task_done()


def dir_bruteforce(target_url, wordlist_path, thread_count=10, output_file=None, extensions=None, recursive=False):
    global total

    if not os.path.exists(wordlist_path):
        print(Fore.RED + f"[!] Wordlist not found: {wordlist_path}")
        return

    if not is_host_reachable(target_url):
        print(Fore.RED + "[!] Host unreachable or invalid. Please check the hostname.")
        return

    with open(wordlist_path, 'r') as file:
        words = file.read().splitlines()

    total = len(words)

    print(Fore.CYAN + "\n┌──────────────────────────────────────────────┐")
    print(Fore.CYAN + "│               Scan Configuration             │")
    print(Fore.CYAN + "├────────────────────────┬─────────────────────┤")
    print(Fore.CYAN + f"│ Target URL             │ {target_url.ljust(20)}│")
    print(Fore.CYAN + f"│ Wordlist Path          │ {wordlist_path.ljust(20)}│")
    print(Fore.CYAN + f"│ Threads                │ {str(thread_count).ljust(20)}│")
    if extensions:
        print(Fore.CYAN + f"│ Extensions             │ {', '.join(extensions).ljust(20)}│")
    if output_file:
        print(Fore.CYAN + f"│ Output File            │ {output_file.ljust(20)}│")
    if recursive:
        print(Fore.CYAN + f"│ Recursive              │ {'Enabled'.ljust(20)}│")
    print(Fore.CYAN + "└────────────────────────┴─────────────────────┘\n")

    print(Fore.CYAN + "[*] Starting directory brute-force...\n")

    queue = Queue()
    for word in words:
        queue.put(word)

    threads = []
    for _ in range(thread_count):
        t = threading.Thread(target=worker, args=(queue, target_url, words, output_file, extensions, recursive))
        t.daemon = True
        threads.append(t)
        t.start()

    queue.join()

    print(Fore.YELLOW + f"\n[+] Scan completed. Checked {total} base paths.")
    if output_file:
        print(Fore.GREEN + f"[+] Results saved to: {output_file}\n")


if __name__ == "__main__":
    try:
        show_banner()

        print(Fore.LIGHTCYAN_EX + "┌───────────────────────────────┐")
        print(Fore.LIGHTCYAN_EX + "│    Configure Scan Options     │")
        print(Fore.LIGHTCYAN_EX + "└───────────────────────────────┘\n")

        cli_style = PromptStyle.from_dict({'prompt': 'ansiblue bold'})

        target_url = prompt([('class:prompt', "🔗 Enter Target URL: ")], style=cli_style).strip()

        wordlist_input = prompt([('class:prompt', "📄 Wordlist File: ")], completer=PathCompleter(), style=cli_style).strip()
        wordlist_path = wordlist_input if os.path.isabs(wordlist_input) else os.path.join(os.getcwd(), wordlist_input)

        thread_input = prompt([('class:prompt', "⚙️  Threads (default = 10): ")], style=cli_style).strip()
        thread_count = int(thread_input) if thread_input.isdigit() else 10

        output_input = prompt([('class:prompt', "💾 Output File (optional): ")], completer=PathCompleter(), style=cli_style).strip()
        output_file = os.path.join(os.getcwd(), output_input) if output_input else None

        extensions_input = prompt([('class:prompt', "📄 Add file extensions to try (optional)? (.php,.html,.bak): ")], style=cli_style).strip()
        extensions = [ext if ext.startswith('.') else f".{ext}" for ext in extensions_input.split(',') if ext]

        recursive_input = prompt([('class:prompt', "🔁 Enable recursive scan? (y/N): ")], style=cli_style).strip().lower()
        recursive = recursive_input == 'y'

        dir_bruteforce(target_url, wordlist_path, thread_count, output_file, extensions, recursive)

    except KeyboardInterrupt:
        print(Fore.RED + "\n[!] Program terminated by user.")

