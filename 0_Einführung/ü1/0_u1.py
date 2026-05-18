# Beispielprogramm
import numpy as np

print(np.pi)

variable1 = 10
variable2 = [variable1, variable1 + 10, variable1 + 20]

print(variable2[0])
print(variable2[1])
print(variable2[2])

for var in variable2:
    if (var / 10)  % 2 == 1:
        print("Die erste Ziffer Zahl %s ist ungerade!" % var)