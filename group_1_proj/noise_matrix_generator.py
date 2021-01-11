import random
import numpy as np

def generate_random_factors():
    e0 = random.random()
    e1 = random.random()
    e2 = random.random()
    e3 = random.random()

    norm = e0**2 + e1**2 + e2**2 + e3**2
    e0 /= norm
    e1 /= norm
    e2 /= norm
    e3 /= norm

    return e0, e1, e2, e3


def get_random_noise_matrix():
    e0, e1, e2, e3 = generate_random_factors()
    print(e0, e1, e2, e3)
    matrix = np.array([[e0 + e2, e1 - e3],
                       [e1 + e3, e0 - e2]])
    q, r = np.linalg.qr(matrix)
    return q.tolist()
