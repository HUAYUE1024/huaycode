
import time
from chronotrace.core import trace

@trace
def main():
    print("Starting Trace Test...")
    
    # Simple variables
    x = 10
    y = 20
    z = x + y
    
    # List operations
    data = []
    for i in range(5):
        data.append(i * i)
        time.sleep(0.1)
        
    # Dictionary
    config = {
        "mode": "test",
        "values": data,
        "nested": {
            "a": 1,
            "b": 2
        }
    }
    
    # Memory consumption simulation
    large_list = [0] * 100000
    print(f"Created large list of size {len(large_list)}")
    
    # Cleanup
    del large_list
    print("Deleted large list")
    
    return config

if __name__ == "__main__":
    main()
