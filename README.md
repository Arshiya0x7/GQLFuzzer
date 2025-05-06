# GraphQL Wordlist Fuzzer

A tool for discovering GraphQL endpoints and fields through wordlist-based fuzzing.

![image](https://github.com/user-attachments/assets/ef072d49-e2ce-4163-a711-9508abd7c25d)

[![asciicast](https://asciinema.org/a/sCWJ8iZib5xXvDFXXkRa2O2NI.svg)](https://asciinema.org/a/sCWJ8iZib5xXvDFXXkRa2O2NI)

## Description

This script performs brute-force discovery of GraphQL fields and operations by:
- Sending POST requests with wordlist combinations to a target GraphQL endpoint
- Analyzing error responses to identify valid fields and operations
- Extracting potential field names from error messages
- Providing clean, color-coded output of discovered fields

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/graphql-fuzzer.git
cd graphql-fuzzer
```

# Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Basic Command

```bash
python graphql_fuzzer.py -u https://target.com/graphql -w wordlist.txt
```

## Parameters

```bash
Parameter                  
-u, --url  Target GraphQL endpoint URL
-w, --wordlist  Path to wordlist file	 
-c, --count  Number of words per request (Default: 200)
-o, --output  Output file to save results
-H HEADER, --header HEADER  Add custom header to requests (e.g., "Authorization: Bearer token")
```

## Example

```bash
python graphql_fuzzer.py -u https://api.example.com/graphql -w ./wordlists/graphql.txt -c 300 -o results.txt
```

## Contribution

We welcome contributions to improve this tool!
