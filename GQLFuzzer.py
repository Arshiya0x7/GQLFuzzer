import argparse
import requests
import json
import re
import sys
import signal
from itertools import islice
from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

def display_logo():
    logo = """
                                                                                            
  ▄████   █████   ██▓      █████▒█    ██ ▒███████▒▒███████▒▓█████  ██▀███  
 ██▒ ▀█▒▒██▓  ██▒▓██▒    ▓██   ▒ ██  ▓██▒▒ ▒ ▒ ▄▀░▒ ▒ ▒ ▄▀░▓█   ▀ ▓██ ▒ ██▒
▒██░▄▄▄░▒██▒  ██░▒██░    ▒████ ░▓██  ▒██░░ ▒ ▄▀▒░ ░ ▒ ▄▀▒░ ▒███   ▓██ ░▄█ ▒
░▓█  ██▓░██  █▀ ░▒██░    ░▓█▒  ░▓▓█  ░██░  ▄▀▒   ░  ▄▀▒   ░▒▓█  ▄ ▒██▀▀█▄  
░▒▓███▀▒░▒███▒█▄ ░██████▒░▒█░   ▒▒█████▓ ▒███████▒▒███████▒░▒████▒░██▓ ▒██▒
 ░▒   ▒ ░░ ▒▒░ ▒ ░ ▒░▓  ░ ▒ ░   ░▒▓▒ ▒ ▒ ░▒▒ ▓░▒░▒░▒▒ ▓░▒░▒░░ ▒░ ░░ ▒▓ ░▒▓░
  ░   ░  ░ ▒░  ░ ░ ░ ▒  ░ ░     ░░▒░ ░ ░ ░░▒ ▒ ░ ▒░░▒ ▒ ░ ▒ ░ ░  ░  ░▒ ░ ▒░
░ ░   ░    ░   ░   ░ ░    ░ ░    ░░░ ░ ░ ░ ░ ░ ░ ░░ ░ ░ ░ ░   ░     ░░   ░ 
      ░     ░        ░  ░          ░       ░ ░      ░ ░       ░  ░   ░     
                                         ░        ░                        

                                                                                               
╔══════════════════════════════╗
║         Arshiya 1.0          ║
╚══════════════════════════════╝
    """
    print(logo)

def extract_keywords(message):
    """
    Extract keywords from error messages
    """
    keywords = []
    
    # Pattern for words inside `...` in first message type
    pattern1 = r"`(.+?)`"
    match1 = re.search(pattern1, message)
    if match1:
        keywords.append(match1.group(1))
    
    # Pattern for first word inside '...' in second message type
    pattern2 = r"field '(.+?)'"
    match2 = re.search(pattern2, message)
    if match2:
        keywords.append(match2.group(1))
    
    return keywords

def handle_http_error(status_code):
    """
    Handle HTTP errors and return appropriate messages
    """
    error_messages = {
        400: f"{Fore.RED}Bad Request{Style.RESET_ALL} - Server cannot process the request",
        401: f"{Fore.YELLOW}Unauthorized{Style.RESET_ALL} - Authentication required",
        403: f"{Fore.RED}Forbidden{Style.RESET_ALL} - Access denied",
        404: f"{Fore.BLUE}Not Found{Style.RESET_ALL} - Resource not found",
        429: f"{Fore.YELLOW}Too Many Requests{Style.RESET_ALL} - Rate limit exceeded",
        500: f"{Fore.RED}Internal Server Error{Style.RESET_ALL}",
        502: f"{Fore.RED}Bad Gateway{Style.RESET_ALL}",
        503: f"{Fore.YELLOW}Service Unavailable{Style.RESET_ALL}"
    }
    
    return error_messages.get(status_code, f"{Fore.RED}Unknown error{Style.RESET_ALL} with code {status_code}")

def exit_cleanly(signum=None, frame=None):
    """
    Clean exit handler for SIGINT (Ctrl+C)
    """
    print(f"\n{Fore.YELLOW}[!]{Style.RESET_ALL} Scan stopped by user (Ctrl+C)")
    
    # Close output file if it exists
    if 'output_file' in globals() and output_file:
        output_file.close()
    
    sys.exit(0)

def print_status(message):
    """Print status messages in blue"""
    print(f"{Fore.CYAN}[*]{Style.RESET_ALL} {message}")

def print_success(message):
    """Print success messages in green"""
    print(f"{Fore.GREEN}[+]{Style.RESET_ALL} {message}")

def print_error(message):
    """Print error messages in red"""
    print(f"{Fore.RED}[X]{Style.RESET_ALL} {message}")

def print_warning(message):
    """Print warning messages in yellow"""
    print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {message}")

def main():
    display_logo()
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, exit_cleanly)

    # Set up command line argument parser
    parser = argparse.ArgumentParser(description='GraphQL Wordlist Fuzzer')
    parser.add_argument('-u', '--url', required=True, help='GraphQL endpoint URL')
    parser.add_argument('-w', '--wordlist', required=True, help='Path to wordlist file')
    parser.add_argument('-c', '--count', type=int, default=200, help='Number of words per request (default: 200)')
    parser.add_argument('-o', '--output', help='Output file to save results')
    args = parser.parse_args()

    # Print banner
    print(f"\n{Fore.GREEN}{Style.BRIGHT}GraphQL Wordlist Fuzzer{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'-'*40}{Style.RESET_ALL}")

    # Read wordlist file
    try:
        with open(args.wordlist, 'r') as f:
            words = [line.strip() for line in f if line.strip()]
        print_status(f"Loaded {len(words)} words from wordlist")
    except FileNotFoundError:
        print_error(f"Wordlist file not found: {args.wordlist}")
        sys.exit(1)

    total_words = len(words)
    total_requests = 0
    total_matches = 0
    extracted_keywords = set()  # Store unique extracted keywords

    # Make output_file global so exit_cleanly can access it
    global output_file
    output_file = None
    
    try:
        # Open output file if specified
        if args.output:
            try:
                output_file = open(args.output, 'w')
                print_status(f"Output will be saved to: {args.output}")
            except IOError:
                print_error(f"Error creating output file: {args.output}")
                sys.exit(1)

        print_status("Starting fuzzing... (Press Ctrl+C to stop)")
        
        # Process wordlist in batches
        for i in range(0, total_words, args.count):
            batch = words[i:i + args.count]
            query_words = ' '.join(batch)
            
            # Create request payload
            payload = {
                "query": f"{{{query_words}}}"
            }
            
            try:
                # Send POST request
                response = requests.post(
                    args.url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30  # Add timeout to prevent hanging
                )
                total_requests += 1
                
                # Check HTTP status code
                if response.status_code != 200:
                    error_msg = handle_http_error(response.status_code)
                    print_error(f"HTTP Error {response.status_code}: {error_msg}")
                    print_warning("Operation stopped")
                    break
                
                # Process response
                try:
                    data = response.json()
                except ValueError:
                    print_error("Invalid JSON response")
                    continue
                
                # Check for errors in response
                if 'errors' in data:
                    for error in data['errors']:
                        message = error.get('message', '')
                        
                        # Check for interesting error messages
                        if ("Field must have selections" in message or 
                            "Field 'assume' doesn't exist on type 'Query'" in message or
                            "Did you mean" in message):
                            
                            # Extract keywords
                            keywords = extract_keywords(message)
                            if keywords:
                                for keyword in keywords:
                                    if keyword not in extracted_keywords:
                                        print_success(f"Extracted keyword: {Fore.MAGENTA}{keyword}{Style.RESET_ALL}")
                                        extracted_keywords.add(keyword)
                                        total_matches += 1
                                        
                                        if output_file:
                                            output_file.write(f"{keyword}\n")
            
            except requests.exceptions.RequestException as e:
                print_error(f"Request error: {e}")
                continue  # Continue with next request instead of exiting
            
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
        
    finally:
        # Close output file if open
        if output_file:
            output_file.close()

    # Print final report
    print(f"\n{Fore.GREEN}{Style.BRIGHT}=== Final Report ===")
    print(f"{Fore.CYAN}{'-'*40}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Total words processed:{Style.RESET_ALL} {total_words}")
    print(f"{Fore.YELLOW}Total requests sent:{Style.RESET_ALL} {total_requests}")
    print(f"{Fore.YELLOW}Total unique keywords extracted:{Style.RESET_ALL} {len(extracted_keywords)}")
    
    if args.output:
        print(f"{Fore.YELLOW}Results saved to:{Style.RESET_ALL} {args.output}")

    # Print extracted keywords
    if extracted_keywords:
        print(f"\n{Fore.CYAN}Extracted keywords:{Style.RESET_ALL}")
        for keyword in extracted_keywords:
            print(f"- {Fore.MAGENTA}{keyword}{Style.RESET_ALL}")

if __name__ == '__main__':
    main()
