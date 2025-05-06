import argparse
import requests
import json
import re
import sys
import signal
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
    """Extract keywords from error messages"""
    keywords = []
    pattern1 = r"`(.+?)`"
    match1 = re.search(pattern1, message)
    if match1:
        keywords.append(match1.group(1))
    
    pattern2 = r"field '(.+?)'"
    match2 = re.search(pattern2, message)
    if match2:
        keywords.append(match2.group(1))
    
    return keywords

def handle_http_error(status_code):
    """Handle HTTP errors and return appropriate messages"""
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
    """Clean exit handler for SIGINT (Ctrl+C)"""
    print(f"\n{Fore.YELLOW}[!]{Style.RESET_ALL} Scan stopped by user (Ctrl+C)")
    if 'output_file' in globals() and output_file:
        output_file.close()
    sys.exit(0)

def parse_header(header_string):
    """Parse header string into key-value pair"""
    try:
        key, value = header_string.split(':', 1)
        return key.strip(), value.strip()
    except ValueError:
        print(f"{Fore.RED}[X]{Style.RESET_ALL} Invalid header format: {header_string}. Use 'Header-Name: value' format")
        sys.exit(1)

def main():
    display_logo()
    signal.signal(signal.SIGINT, exit_cleanly)
    
    parser = argparse.ArgumentParser(description='GraphQL Wordlist Fuzzer')
    parser.add_argument('-u', '--url', required=True, help='GraphQL endpoint URL')
    parser.add_argument('-w', '--wordlist', required=True, help='Path to wordlist file')
    parser.add_argument('-c', '--count', type=int, default=200, help='Number of words per request (default: 200)')
    parser.add_argument('-o', '--output', help='Output file to save results')
    parser.add_argument('-H', '--header', action='append', help='Add custom header to requests (e.g., "Authorization: Bearer token")')
    
    args = parser.parse_args()

    # Read wordlist
    try:
        with open(args.wordlist, 'r') as f:
            words = [line.strip() for line in f if line.strip()]
        print(f"{Fore.CYAN}[*]{Style.RESET_ALL} Loaded {len(words)} words from wordlist")
    except FileNotFoundError:
        print(f"{Fore.RED}[X]{Style.RESET_ALL} Wordlist file not found: {args.wordlist}")
        sys.exit(1)

    # Prepare headers
    headers = {'Content-Type': 'application/json'}
    if args.header:
        for header in args.header:
            key, value = parse_header(header)
            headers[key] = value
            print(f"{Fore.CYAN}[*]{Style.RESET_ALL} Added header: {key}: {value}")

    global output_file, extracted_keywords
    output_file = None
    extracted_keywords = set()
    
    try:
        if args.output:
            try:
                output_file = open(args.output, 'w')
                print(f"{Fore.CYAN}[*]{Style.RESET_ALL} Output will be saved to: {args.output}")
            except IOError:
                print(f"{Fore.RED}[X]{Style.RESET_ALL} Error creating output file: {args.output}")
                sys.exit(1)

        print(f"{Fore.CYAN}[*]{Style.RESET_ALL} Starting fuzzing... (Press Ctrl+C to stop)")
        
        for i in range(0, len(words), args.count):
            batch = words[i:i + args.count]
            query_words = ' '.join(batch)
            
            payload = {"query": f"{{{query_words}}}"}
            
            try:
                response = requests.post(
                    args.url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code != 200:
                    error_msg = handle_http_error(response.status_code)
                    print(f"\n{Fore.RED}[X]{Style.RESET_ALL} HTTP Error {response.status_code}: {error_msg}")
                    print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} Operation stopped")
                    break
                
                try:
                    data = response.json()
                except ValueError:
                    continue
                
                if 'errors' in data:
                    for error in data['errors']:
                        message = error.get('message', '')
                        if ("Field must have selections" in message or 
                            "Field 'assume' doesn't exist on type 'Query'" in message or
                            "Did you mean" in message):
                            
                            keywords = extract_keywords(message)
                            if keywords:
                                for keyword in keywords:
                                    if keyword not in extracted_keywords:
                                        extracted_keywords.add(keyword)
                                        print(f"{Fore.GREEN}[+]{Style.RESET_ALL} Found keyword: {Fore.MAGENTA}{keyword}{Style.RESET_ALL}")
                                        if output_file:
                                            output_file.write(f"{keyword}\n")
            
            except requests.exceptions.RequestException as e:
                print(f"{Fore.RED}[X]{Style.RESET_ALL} Request error: {e}")
                continue
            
    except Exception as e:
        print(f"\n{Fore.RED}[X]{Style.RESET_ALL} Unexpected error: {e}")
        sys.exit(1)
    finally:
        if output_file:
            output_file.close()

    # Display final report
    print(f"\n{Fore.GREEN}{Style.BRIGHT}=== Final Report ===")
    print(f"{Fore.CYAN}{'-'*40}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Total words processed:{Style.RESET_ALL} {len(words)}")
    print(f"{Fore.YELLOW}Total requests sent:{Style.RESET_ALL} {len(words) // args.count + 1}")
    print(f"{Fore.YELLOW}Total unique keywords extracted:{Style.RESET_ALL} {len(extracted_keywords)}")
    
    if args.output:
        print(f"{Fore.YELLOW}Results saved to:{Style.RESET_ALL} {args.output}")

if __name__ == '__main__':
    main()
