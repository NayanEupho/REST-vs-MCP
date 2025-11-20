import subprocess
import time
import sys
import os
import argparse
import asyncio
from benchmarks.run_benchmark import run_benchmarks
from benchmarks.run_benchmark_advanced import run_all_benchmarks
from reporting.generate_report import generate_report

def start_server(script_path, port):
    print(f"Starting server: {script_path} on port {port}")
    process = subprocess.Popen(
        [sys.executable, script_path],
        # stdout=subprocess.PIPE,
        # stderr=subprocess.PIPE,
        text=True
    )
    return process

def main():
    parser = argparse.ArgumentParser(description="REST vs MCP Comparison Project")
    parser.add_argument("--gui", action="store_true", help="Launch Streamlit Dashboard")
    parser.add_argument("--cli", action="store_true", help="Run Advanced Benchmarks in CLI mode")
    parser.add_argument("--new_report", action="store_true", help="Create a new report file with timestamp instead of overwriting")
    args = parser.parse_args()

    print("Starting REST vs MCP Comparison Project...")
    
    # Paths
    rest_server_path = "servers/rest_server.py"
    mcp_server_path = "servers/mcp_server.py"
    
    # Start Servers
    rest_process = start_server(rest_server_path, 8000)
    mcp_process = start_server(mcp_server_path, 8001)
    
    try:
        # Wait for servers to start
        print("Waiting for servers to initialize...")
        time.sleep(5)
        
        if args.gui:
            print("\n--- Launching Streamlit Dashboard ---")
            # We need to keep the main process alive while streamlit runs
            # But streamlit run is a separate process usually.
            # We can run it via subprocess
            streamlit_process = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", "dashboard/app.py"],
                text=True
            )
            streamlit_process.wait()
            
        elif args.cli:
            print("\n--- Running Advanced Benchmarks (CLI) ---")
            
            output_file = "reports/advanced_benchmark_results.csv"
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            
            if args.new_report:
                file_timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_file = f"reports/advanced_benchmark_results_{file_timestamp}.csv"
                
            asyncio.run(run_all_benchmarks(output_file, timestamp))
            print(f"\nDone! Check '{output_file}' and its corresponding .md report for results.")
            
        else:
            # Default behavior (Basic Benchmarks)
            print("\n--- Running Basic Benchmarks ---")
            run_benchmarks(iterations=50)
            print("\n--- Generating Report ---")
            generate_report()
            print("\nDone! Check 'reports/' directory for results.")
            print("Tip: Run with --gui for interactive dashboard or --cli for advanced benchmarks.")
        
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"An error occurred: {e}")
        
    finally:
        # Cleanup
        print("\nStopping servers...")
        rest_process.terminate()
        mcp_process.terminate()
        rest_process.wait()
        mcp_process.wait()
        print("Servers stopped.")

if __name__ == "__main__":
    main()
