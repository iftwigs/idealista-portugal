#!/usr/bin/env python3
"""
Script to stop all running bot instances
"""
import subprocess
import sys

def stop_all_bots():
    """Stop all running bot instances"""
    try:
        # Find all processes with bot.py
        result = subprocess.run(
            ['pgrep', '-f', 'bot.py'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            pids = [pid for pid in pids if pid]  # Filter empty strings
            
            if pids:
                print(f"Found {len(pids)} bot processes: {', '.join(pids)}")
                
                # Kill each process
                for pid in pids:
                    try:
                        subprocess.run(['kill', pid], check=True)
                        print(f"✅ Stopped process {pid}")
                    except subprocess.CalledProcessError:
                        print(f"❌ Failed to stop process {pid}")
                
                print(f"✅ Stopped {len(pids)} bot processes")
            else:
                print("✅ No bot processes found")
        else:
            print("✅ No bot processes found")
            
    except Exception as e:
        print(f"❌ Error stopping bots: {e}")

if __name__ == "__main__":
    stop_all_bots()