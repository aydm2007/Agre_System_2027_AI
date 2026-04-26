import json
import sys

def parse_suite(suite):
    failures = []
    if 'suites' in suite:
        for s in suite['suites']:
            failures.extend(parse_suite(s))
    
    if 'specs' in suite:
        for spec in suite['specs']:
            for test in spec['tests']:
                # Check the last result as it's the most relevant (retries)
                if test['results']:
                    last_result = test['results'][-1]
                    if last_result['status'] != 'passed' and last_result['status'] != 'skipped':
                        error_msg = "Unknown error"
                        if 'error' in last_result:
                            error_msg = last_result['error'].get('message', 'No message')
                            # Clean up ANSI codes if possible or just take first few lines
                            error_msg = error_msg.split('\n')[0][:200]
                        
                        failures.append(f"FAIL: {spec['title']}\n  Error: {error_msg}")
    return failures

try:
    with open('test-results.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        failures = parse_suite(data)
        print(f"Total Failures: {len(failures)}")
        for fail in failures:
            print(fail)
except Exception as e:
    print(f"Error parsing json: {e}")
