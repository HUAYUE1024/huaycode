import sys
import os
import random

# Add parent directory to path so we can import chronotrace
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chronotrace import trace

@trace
def quicksort_demo():
    print("Starting QuickSort Demo...")
    
    # Generate random numbers
    arr = [random.randint(1, 100) for _ in range(10)]
    print(f"Original array: {arr}")
    
    def quicksort(arr):
        if len(arr) <= 1:
            return arr
        else:
            pivot = arr[0]
            less = [x for x in arr[1:] if x <= pivot]
            greater = [x for x in arr[1:] if x > pivot]
            return quicksort(less) + [pivot] + quicksort(greater)

    sorted_arr = quicksort(arr)
    print(f"Sorted array: {sorted_arr}")
    
    # Let's also do some object manipulation to show off serialization
    class Particle:
        def __init__(self, x, y):
            self.x = x
            self.y = y
            
        def move(self):
            self.x += random.choice([-1, 1])
            self.y += random.choice([-1, 1])
            
    particles = [Particle(0, 0) for _ in range(3)]
    for _ in range(5):
        for p in particles:
            p.move()
            
    return sorted_arr

if __name__ == "__main__":
    quicksort_demo()
