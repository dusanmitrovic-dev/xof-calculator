import random
import time

def generate_id():
    timestamp = int(time.time() * 1000)  # Millisecond precision
    random_digits = random.randint(1000, 9999)  # 4 digits is sufficient for your volume
    
    return f"{timestamp}-{random_digits}"