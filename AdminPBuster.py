#!/usr/bin/env python3

import requests
import subprocess
import signal
import sys
import os
import queue
import argparse
import time
import random
from threading import Thread, Lock
from urllib.parse import urlparse
import urllib3
from pathlib import Path
from termcolor import colored

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

VERSION = "3.1"
AUTHOR = "Chris 'SaintDruG' Abou-Chabke"
TEAM = "Black Hat Ethical Hacking"
PATHS_URL = "https://raw.githubusercontent.com/blackhatethicalhacking/AdminPBuster/refs/heads/main/magic_admin_paths.txt"

request_counter = 0
counter_lock = Lock()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0"
]

def handle_interrupt(signal, frame):
    print(colored("\n[!] Interrupted by user. Exiting...", "red", attrs=["bold"]))
    sys.exit(0)

signal.signal(signal.SIGINT, handle_interrupt)

def rainbow_text(text):
    colors = ['red', 'yellow', 'green', 'cyan', 'blue', 'magenta']
    return ''.join(colored(char, colors[i % len(colors)], attrs=["bold"]) if char != " " else " " for i, char in enumerate(text))

def print_ascii_and_quote():
    subprocess.run("curl --silent https://raw.githubusercontent.com/blackhatethicalhacking/Subdomain_Bruteforce_bheh/main/ascii.sh | lolcat", shell=True)
    print("")
    quotes = [
        "The supreme art of war is to subdue the enemy without fighting.",
        "All warfare is based on deception.",
        "He who knows when he can fight and when he cannot, will be victorious.",
        "The whole secret lies in confusing the enemy, so that he cannot fathom our real intent.",
        "To win one hundred victories in one hundred battles is not the acme of skill. To subdue the enemy without fighting is the acme of skill."
    ]
    random_quote = random.choice(quotes)
    subprocess.run(f'echo "Offensive Security Tip: {random_quote} - Sun Tzu" | lolcat', shell=True)
    time.sleep(1)
    subprocess.run('echo "MEANS, IT\'S ☕ 1337 ⚡ TIME, 369 ☯" | lolcat', shell=True)
    time.sleep(1)
    print("\n" + rainbow_text("Press any key to enter the Matrix"))
    input()

def print_toilet_banner_lolcat():
    subprocess.run("clear", shell=True)
    os.system("toilet -f smblock 'AdminPBuster' | lolcat")

def print_help_colored():
    print_ascii_and_quote()
    print_toilet_banner_lolcat()
    print(colored(f"\nVersion: {VERSION}", "yellow"))
    print(colored(f"Author: {AUTHOR}", "yellow"))
    print(colored(f"Team: {TEAM}\n", "yellow"))

    print(colored("Usage: ", "cyan", attrs=["bold"]) + colored("./AdminPBuster.py -t example.com", "white"))
    print(colored("(Give domain only without brackets or https)\n", "yellow"))

    print(colored("Options:", "cyan", attrs=["bold"]))
    print(colored("  -h, --help             ", "white") + "Show this help message and exit")
    print(colored("  -t, --target TARGET    ", "white") + "Target domain (e.g., example.com)")
    print(colored("  -th, --threads THREADS ", "white") + "Number of threads (default: 5)")
    print(colored("  -w, --www MODE         ", "white") + "www handling: both (default), force, no")
    print(colored("  -ua, --random-agent    ", "white") + "Use random realistic User-Agent")
    print(colored("  -v, --version          ", "white") + "Show version and exit\n")

    print(colored("Written by ", "green") + colored("Chris 'SaintDruG' Abou-Chabke", "magenta") + colored(" for Black Hat Ethical Hacking", "green"))
    print(colored("© All Rights Reserved 2025 — Use For Ethical Testing Only.", "yellow"))
    print(colored("BHEH is not responsible for misuse of this tool.", "red"))

def print_rainbow_banner():
    os.system("clear")
    print("\n" + rainbow_text("Admin Panel Buster"))
    print(colored(f"\nVersion: {VERSION}", "yellow"))
    print(colored(f"Author: {AUTHOR}", "yellow"))
    print(colored(f"Team: {TEAM}", "yellow"))

def countdown():
    print(colored("\nStarting the attack in:", "cyan", attrs=["bold"]))
    for i in range(5, 0, -1):
        print(colored(str(i), "cyan", attrs=["bold"]))
        time.sleep(1)
    print(colored("\n[+] Attack Started!\n", "green", attrs=["bold"]))

def fetch_admin_paths():
    try:
        response = requests.get(PATHS_URL, timeout=10)
        response.raise_for_status()
        return [line.strip() for line in response.text.splitlines() if line.strip()]
    except Exception as e:
        print(colored(f"[!] Failed to fetch admin paths: {e}", "red", attrs=["bold"]))
        sys.exit(1)

def check_internet_connection():
    try:
        requests.get("https://www.google.com", timeout=5)
    except:
        print(colored("[!] No internet connection!", "red", attrs=["bold"]))
        sys.exit(1)

def clean_domain(domain_url):
    parsed = urlparse(domain_url)
    domain = parsed.netloc or parsed.path
    return domain.replace(":", "_")

def clean_host(target):
    parsed = urlparse(target if "://" in target else f"https://{target}")
    return (parsed.netloc or parsed.path).strip("/")

def resolve_bases(target, www_mode):
    """Work out which base URLs actually answer, so an apex-only target is scanned instead of blindly forcing www.
    (the old behaviour broke any domain without a www host). 'both' tries the apex and the www form, 'force' keeps
    the old www-only behaviour, 'no' uses the apex only. Only reachable bases are kept."""
    host = clean_host(target)
    if www_mode == "no":
        candidates = [host]
    elif www_mode == "force":
        candidates = [host if host.startswith("www.") else "www." + host]
    else:  # both
        candidates = [host] + ([] if host.startswith("www.") else ["www." + host])

    bases = []
    for h in dict.fromkeys(candidates):
        url = f"https://{h}"
        try:
            requests.get(url, timeout=8, allow_redirects=True, verify=False)
            bases.append(url)
        except requests.RequestException:
            pass
    return bases

def color_for_status(code):
    if code == "200":
        return "green"
    elif code in ["301", "302"]:
        return "cyan"
    elif code == "403":
        return "yellow"
    elif code == "404":
        return "red"
    else:
        return "magenta"

def scan_url(url_queue, results, timeout=5, random_ua=False):
    global request_counter
    while not url_queue.empty():
        full_url = url_queue.get()

        with counter_lock:
            request_counter += 1
            number = request_counter

        if random_ua:
            user_agent = random.choice(USER_AGENTS)
            curl_cmd = ["curl", "-A", user_agent, "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", str(timeout), "-L", full_url]
        else:
            curl_cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", str(timeout), "-L", full_url]

        try:
            result = subprocess.check_output(curl_cmd)
            http_code = result.decode().strip()

            if http_code == "000":
                http_code = "Connection Failed"

            color = color_for_status(http_code)

            print(colored(f"[{number}] {full_url} -> (HTTP {http_code})", color, attrs=["bold"]))

            if http_code == "200":
                results.append(full_url)

        except subprocess.CalledProcessError:
            print(colored(f"[{number}] {full_url} -> (Connection Failed)", "red", attrs=["bold"]))

        url_queue.task_done()

def admin_panel_buster(target_domain, threads, random_ua, www_mode="both"):
    bases = resolve_bases(target_domain, www_mode)
    if not bases:
        print(colored(f"\n[!] {clean_host(target_domain)} is not reachable over HTTPS "
                      f"(tried apex and www). Nothing to scan.", "red", attrs=["bold"]))
        return
    print(colored(f"[*] Scanning: {', '.join(bases)}", "cyan", attrs=["bold"]))

    paths = fetch_admin_paths()
    q = queue.Queue()
    for base in bases:
        for path in paths:
            q.put(f"{base.rstrip('/')}/{path.lstrip('/')}")

    results = []
    thread_list = []

    domain_folder = f"results/{clean_domain(target_domain)}"
    os.makedirs(domain_folder, exist_ok=True)
    output_file = os.path.join(domain_folder, "found_panels.txt")

    for _ in range(threads):
        t = Thread(target=scan_url, args=(q, results, 5, random_ua))
        thread_list.append(t)
        t.start()

    for t in thread_list:
        t.join()

    if results:
        print(colored(f"\n[✓] Found {len(results)} possible admin panels!", "green", attrs=["bold"]))
        for url in results:
            print(colored(f" - {url}", "green"))
        with open(output_file, "w") as f:
            for url in results:
                f.write(url + "\n")
        print(colored(f"\n[+] Results saved to {output_file}", "cyan", attrs=["bold"]))
    else:
        print(colored("\n[!] No admin panels found.", "yellow"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-t", "--target", help="Target domain (e.g., example.com)")
    parser.add_argument("-th", "--threads", type=int, default=5, help="Number of threads (default: 5)")
    parser.add_argument("-w", "--www", choices=["both", "force", "no"], default="both",
                        help="www handling: both=try apex and www. (default), force=add www., no=apex only")
    parser.add_argument("-ua", "--random-agent", action="store_true", help="Use random realistic User-Agent")
    parser.add_argument("-v", "--version", action="store_true", help="Show version and exit")
    parser.add_argument("-h", "--help", action="store_true", help="Show help message and exit")
    ARGS = parser.parse_args()

    if ARGS.version:
        print(f"AdminPBuster {VERSION}")
        sys.exit(0)

    if ARGS.help or not ARGS.target:
        print_help_colored()
        sys.exit(0)

    print_rainbow_banner()
    check_internet_connection()
    countdown()
    admin_panel_buster(ARGS.target, ARGS.threads, ARGS.random_agent, ARGS.www)
