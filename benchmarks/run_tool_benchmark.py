#!/usr/bin/env python3
"""
Benchmark: Kimi K2.7 Code vs MiniMax M3 vs MiMo-V2.5 on tool-use tasks.
Uses ollama-cloud provider via Hermes CLI.
"""
import json, subprocess, time, sys, os
from datetime import datetime

MODELS = [
    {"name": "Kimi K2.7 Code", "provider": "ollama-cloud", "model": "kimi-k2.7-code"},
    {"name": "MiniMax M3",     "provider": "ollama-cloud", "model": "minimax-m3"},
    {"name": "MiMo-V2.5",      "provider": "ollama-cloud", "model": "mimo-v2.5"},
]

# Tool-use test cases
# Each: {name, prompt, expected_keywords, description}
TEST_CASES = [
    {
        "name": "weather_tool",
        "prompt": "Call the get_weather function with city='Tokyo' and units='metric'. Return ONLY the function call in JSON format like {\"function\": \"get_weather\", \"args\": {\"city\": \"...\", \"units\": \"...\"}}",
        "checks": ["get_weather", "Tokyo", "metric"],
        "description": "Simple function call with 2 params"
    },
    {
        "name": "search_tool",
        "prompt": "Call the search_web function with query='latest AI news 2026' and max_results=5. Return ONLY the function call in JSON format like {\"function\": \"search_web\", \"args\": {\"query\": \"...\", \"max_results\": ...}}",
        "checks": ["search_web", "latest AI news", "5"],
        "description": "Search function with string + int params"
    },
    {
        "name": "complex_tool",
        "prompt": "Call the send_email function with to='user@example.com', subject='Meeting Reminder', body='Don\\'t forget our meeting at 3pm', priority='high'. Return ONLY the function call in JSON format like {\"function\": \"send_email\", \"args\": {\"to\": \"...\", \"subject\": \"...\", \"body\": \"...\", \"priority\": \"...\"}}",
        "checks": ["send_email", "user@example.com", "Meeting Reminder", "high"],
        "description": "Complex function with 4 params including special chars"
    },
    {
        "name": "nested_tool",
        "prompt": "Call the create_user function with name='Alice', age=30, settings={'theme': 'dark', 'notifications': True}. Return ONLY the function call in JSON format like {\"function\": \"create_user\", \"args\": {\"name\": \"...\", \"age\": ..., \"settings\": {...}}}",
        "checks": ["create_user", "Alice", "30", "dark", "notifications"],
        "description": "Nested object parameter"
    },
    {
        "name": "multi_tool",
        "prompt": "You need to call TWO functions in sequence. First call get_user(id=42) to get user data, then call send_notification(user_id=42, message='Welcome!'). Return ONLY the function calls as a JSON array like [{\"function\": \"get_user\", \"args\": {\"id\": ...}}, {\"function\": \"send_notification\", \"args\": {\"user_id\": ..., \"message\": \"...\"}}]",
        "checks": ["get_user", "42", "send_notification", "Welcome"],
        "description": "Multi-step function calling sequence"
    }
]

def run_hermes_query(model_name, provider, model_id, prompt, timeout=60):
    """Run a single query via Hermes CLI and return the response."""
    cmd = [
        "hermes", "chat", "-q", prompt,
        "--provider", provider,
        "--model", model_id,
        "-Q"  # quiet mode
    ]
    
    start = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - start
        output = result.stdout + result.stderr
        return {
            "success": True,
            "output": output[:2000],  # truncate for display
            "latency": round(elapsed, 2),
            "exit_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {
            "success": False,
            "output": f"TIMEOUT after {timeout}s",
            "latency": round(elapsed, 2),
            "exit_code": -1
        }
    except Exception as e:
        return {
            "success": False,
            "output": f"ERROR: {str(e)}",
            "latency": 0,
            "exit_code": -1
        }

def score_response(output, checks):
    """Score how many expected keywords appear in the output."""
    output_lower = output.lower()
    found = 0
    for check in checks:
        if check.lower() in output_lower:
            found += 1
    return found, len(checks)

def main():
    results = {}
    
    for model in MODELS:
        print(f"\n{'='*60}")
        print(f"Testing: {model['name']} ({model['provider']}/{model['model']})")
        print(f"{'='*60}")
        
        model_results = []
        total_score = 0
        total_possible = 0
        total_latency = 0
        
        for tc in TEST_CASES:
            print(f"\n  Test: {tc['name']} — {tc['description']}")
            print(f"  Prompt: {tc['prompt'][:80]}...")
            
            result = run_hermes_query(
                model['name'], model['provider'], model['model'],
                tc['prompt']
            )
            
            if result['success']:
                score, possible = score_response(result['output'], tc['checks'])
                total_score += score
                total_possible += possible
                total_latency += result['latency']
                
                print(f"  ✓ Latency: {result['latency']}s")
                print(f"  ✓ Score: {score}/{possible}")
                print(f"  Output preview: {result['output'][:200]}...")
                
                model_results.append({
                    "test": tc['name'],
                    "score": score,
                    "possible": possible,
                    "latency": result['latency'],
                    "output_preview": result['output'][:200]
                })
            else:
                print(f"  ✗ FAILED: {result['output'][:100]}")
                model_results.append({
                    "test": tc['name'],
                    "score": 0,
                    "possible": len(tc['checks']),
                    "latency": result['latency'],
                    "error": result['output'][:200]
                })
        
        accuracy = (total_score / total_possible * 100) if total_possible > 0 else 0
        avg_latency = total_latency / len(TEST_CASES) if TEST_CASES else 0
        
        results[model['name']] = {
            "total_score": total_score,
            "total_possible": total_possible,
            "accuracy_pct": round(accuracy, 1),
            "avg_latency_s": round(avg_latency, 2),
            "tests": model_results
        }
        
        print(f"\n  ─────────────────────────────────────")
        print(f"  Model: {model['name']}")
        print(f"  Accuracy: {total_score}/{total_possible} ({accuracy:.1f}%)")
        print(f"  Avg Latency: {avg_latency:.2f}s")
    
    # Summary table
    print(f"\n\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"{'Model':<20} {'Accuracy':<12} {'Avg Latency':<12} {'Score':<10}")
    print(f"{'-'*20} {'-'*12} {'-'*12} {'-'*10}")
    
    for model_name, data in sorted(
        results.items(),
        key=lambda x: x[1]['accuracy_pct'],
        reverse=True
    ):
        print(f"{model_name:<20} {data['accuracy_pct']:<8.1f}%  {data['avg_latency_s']:<8.2f}s  {data['total_score']}/{data['total_possible']}")
    
    # Save results
    output = {
        "timestamp": datetime.utcnow().isoformat(),
        "test_cases": [tc['name'] for tc in TEST_CASES],
        "results": results
    }
    
    out_path = f"/tmp/minibench/benchmarks/results/tool-use-benchmark-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {out_path}")

if __name__ == "__main__":
    main()
