import argparse
import requests
import json
import re
import sys
import signal
from itertools import islice

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
        400: "Bad Request - Server cannot process the request",
        401: "Unauthorized - Authentication required",
        403: "Forbidden - Access denied",
        404: "Not Found - Resource not found",
        429: "Too Many Requests - Rate limit exceeded",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable"
    }
    
    return error_messages.get(status_code, f"Unknown error with code {status_code}")

def exit_cleanly(signum=None, frame=None):
    """
    Clean exit handler for SIGINT (Ctrl+C)
    """
    print("\n[!] Scan stopped by user (Ctrl+C)")
    
    # Close output file if it exists
    if 'output_file' in globals() and output_file:
        output_file.close()
    
    sys.exit(0)

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

    # Read wordlist file
    try:
        with open(args.wordlist, 'r') as f:
            words = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[X] Wordlist file not found: {args.wordlist}")
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
            except IOError:
                print(f"[X] Error creating output file: {args.output}")
                sys.exit(1)

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
                    print(f"\n[X] HTTP Error {response.status_code}: {error_msg}")
                    print("[!] Operation stopped")
                    break
                
                # Process response
                try:
                    data = response.json()
                except ValueError:
                    print("\n[X] Invalid JSON response")
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
                                        print(f"[+] Extracted keyword: {keyword}")
                                        extracted_keywords.add(keyword)
                                        total_matches += 1
                                        
                                        if output_file:
                                            output_file.write(f"{keyword}\n")
            
            except requests.exceptions.RequestException as e:
                print(f"\n[X] Request error: {e}")
                continue  # Continue with next request instead of exiting
            
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        sys.exit(1)
        
    finally:
        # Close output file if open
        if output_file:
            output_file.close()

    # Print final report
    print("\n=== Final Report ===")
    print(f"Total words processed: {total_words}")
    print(f"Total requests sent: {total_requests}")
    print(f"Total unique keywords extracted: {len(extracted_keywords)}")
    
    if args.output:
        print(f"Results saved to: {args.output}")

    # Print extracted keywords
    if extracted_keywords:
        print("\nExtracted keywords:")
        for keyword in extracted_keywords:
            print(f"- {keyword}")

if __name__ == '__main__':
    main()
