
import random
import time

def bubble_sort(arr):
    n = len(arr)
    print(f"Original array: {arr}")
    
    for i in range(n):
        swapped = False
        print(f"--- Pass {i+1} ---")
        
        for j in range(0, n - i - 1):
            # Compare elements
            print(f"Comparing indices {j} and {j+1}: {arr[j]} vs {arr[j+1]}")
            
            if arr[j] > arr[j + 1]:
                # Swap elements
                print(f"Swapping {arr[j]} and {arr[j+1]}")
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
                
        if not swapped:
            print("Array is sorted early!")
            break
            
    print(f"Sorted array: {arr}")
    return arr

# Create a random array
data = [random.randint(10, 100) for _ in range(8)]
bubble_sort(data)
